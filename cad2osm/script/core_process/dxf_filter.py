# Last edited by Jiajie Zhang 2024.12.06
# 该脚本用于将全图层dxf过滤为保留固定图层的dxf，在机理上已经成功了，但由于CAD文件图层的命名不规则性，用 hard-coded的方式是无法实现的
# 25.5.06 在过滤前实现：把所有 INSERT 展平到 modelspace，保证输出的 DXF 里真正只有几何实体，不再依赖 BLOCK 定义
import ezdxf
import os
from datetime import datetime
import re
from collections import Counter

# --- 移除旧的 LAYER_RULES ---
# LAYER_RULES = { ... }

# --- 新增：定义关键词分数 ---
TOKEN_SCORES = {
    # 强保留信号 (正分)
    'WALL': 5, 'COLS': 5, 'SLAB': 4, 'WINDOW': 3, 'GLAZ': 3, 'CWMG': 3, 'HOLE': 2, 'EVTR': 3, '柱': 5, '墙体': 5, '结构柱': 5, '板': 4, '窗': 3, '玻璃': 3, '门': 1, # 门给较低正分
    'EQPM': 1, # 设备给较低正分
    'AUDIT': 0, # 审计标记 (之前为1)
    'STUCCO': 1, # 灰泥/粉刷 (新添加)
    'STAIR': 1, '楼梯': 1, # 楼梯 (之前为-3)

    # 强舍弃信号 (负分)
    'SYMB': -5, 'DIMS': -5, 'TEXT': -4, 'FIXT': -4, 'HATCH': -4, 'STRS': -3, 'FLOR': -3, 'CASE': -3, 'FURN': -3, 'TEMP': -10,
    '符号': -5, '尺寸': -5, '文字': -4, '标注': -4, '索引': -4, '填充': -4, '家具': -3, '洁具': -4, '楼梯': -3, '地面': -3, '临时': -10,
    'PLAN': -2, 'GRID': -2, '轴号': -2, '标高': -2, 'NOTE': -4,

    # 中性或弱信号 (0分或接近0)
    'A': 0, 'E': 0, 'S': 0, 'I': 0, 'B': 0, 'C': 0, 'D': 0, 'G': 0, # 常用字母前缀
    'E1': 0, 'E2': 0, 'F': 0, '1F': 0, '2F': 0, '3F': 0, '4F': 0, '5F': 0, # 楼层/区域代码
    'RD': 0, 'RI': 0, 'RV': 0, 'RW': 0, # 区域代码
    '0S': 0, '0P': -1, # 0P倾向于舍弃 (P可能代表管道Pipe?)
    'LINE': 0, 'OTLN': 0, 'FRAM': -1, # 框架倾向于舍弃
    'DETL': -1, # 细节倾向于舍弃
    'AREA': 0, 'NAME': 0, 'VOID': 0, 'DRAN': -1, # 排水倾向舍弃
    'TILE': -1, # 瓷砖倾向舍弃
    'SCRE': -1, # Screen/剖面线?
    
    # 特殊处理
    'DOOR': 1, # 门给较低正分
    '门窗': 1, 
}

# 绝对排除模式 (检查是否 *包含* 这些词)
ABSOLUTE_EXCLUDE_TOKENS = ['TEMP', '临时', 'DIMS', '尺寸', '标注', '家具', '填充', '文字', '符号', '索引', '标高', '轴号', 'NOTE', 'PLAN', 'GRID', 'HATCH', 'FIXT', '洁具']
# 绝对保留图层 (检查是否 *完全匹配*)
ABSOLUTE_INCLUDE_LAYERS = ['0', 'Defpoints', 'A—墙体', 'A—门窗', 'A-WALL'] # 新增三个必须保留的图层
# 评分阈值
SCORE_THRESHOLD = 2 # 总分 >= 2 才保留

# --- 新增：从 dxf_layer_info.py 复制过来的解码函数 (移除调试打印) ---
def decode_dxf_unicode(text):
    r"""解码 DXF 文件中的 \M+XXXX Unicode 转义序列"""
    def replace_match(match):
        unicode_hex = match.group(1)
        try:
            unicode_int = int(unicode_hex, 16)
            char = ""
            decoded_from_gbk = False
            if unicode_int > 0xFFFF: # 仅对大数尝试 GBK 解码
                try:
                    lower_16 = unicode_int & 0xFFFF
                    gbk_bytes = lower_16.to_bytes(2, byteorder='big')
                    potential_char = gbk_bytes.decode('gbk')
                    if len(potential_char) == 1 and potential_char != '\ufffd':
                         char = potential_char
                         decoded_from_gbk = True
                except (UnicodeDecodeError, ValueError):
                    pass # GBK 解码失败，继续
            if not decoded_from_gbk:
                 char = chr(unicode_int)
            return char
        except ValueError:
            return match.group(0)
            
    pattern = r'\\M\+([0-9A-Fa-f]{4,5})' # 注意Python字符串中反斜杠需要转义
    return re.sub(pattern, replace_match, text)
# --------------------------------------------------------------

def tokenize_layer_name(layer_name):
    """
    分词函数，处理中英文混合，按常见分隔符分割
    """
    # 替换中文标点为英文，统一处理
    layer_name = layer_name.replace('—', '-').replace('、', '-')
    # 按 '-', '_', '$', ' ' 分割，并处理驼峰命名 (简单处理：在大写字母前加分隔符)
    layer_name_spaced = re.sub(r'(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])', '-', layer_name)
    tokens = re.split(r'[-_$ ]+', layer_name_spaced)
    # 转换为大写并去除空字符串，同时保留原始中文词
    final_tokens = []
    raw_tokens = re.split(r'[-_$ ]+', layer_name) # 保留原始大小写和中文
    for token in raw_tokens:
        if token:
            # 检查是否包含中文字符
            if re.search(r'[一-鿿]', token):
                final_tokens.append(token) # 保留原始中文词
            else:
                final_tokens.append(token.upper()) # 其他转大写
                
    # 补充一个全大写的版本用于匹配规则库
    upper_tokens = [t.upper() for t in tokens if t]
    return list(set(final_tokens + upper_tokens)) # 合并去重

def should_keep_layer(layer_name):
    """
    根据关键词评分判断是否保留图层
    """
    # 1. 检查是否为绝对包含的图层名
    if layer_name in ABSOLUTE_INCLUDE_LAYERS:
        return True

    # 2. 新增：检查图层名是否包含'WALL' (不区分大小写)
    if 'WALL' in layer_name.upper():
        return True

    # 解码并分词
    decoded_name = decode_dxf_unicode(layer_name)
    tokens = tokenize_layer_name(decoded_name)

    # 3. 检查是否包含绝对排除的token
    if any(token in ABSOLUTE_EXCLUDE_TOKENS for token in tokens):
        return False

    # 4. 计算得分
    score = 0
    matched_tokens = set() # 防止同一token重复计分
    for token in tokens:
        if token in TOKEN_SCORES and token not in matched_tokens:
            score += TOKEN_SCORES[token]
            matched_tokens.add(token)

    # 5. 根据阈值判断
    return score >= SCORE_THRESHOLD

def filter_dxf_layers(input_file, output_file):
    """
    根据预定义规则过滤DXF文件图层，并返回保留图层的解码后名称列表
    
    返回:
        (bool, str, list or None): (处理是否成功, 消息, 保留图层的解码后名称列表或None)
    """
    try:
        # 读取源DXF文件
        doc = ezdxf.readfile(input_file)
        
        # 创建新的DXF文档
        new_doc = ezdxf.new()
        
        # 复制原文件的设置
        new_doc.header = doc.header
        # 尝试保留原始ACADVER，如果不存在则不设置
        try:
            new_doc.header['$ACADVER'] = doc.header['$ACADVER']
        except KeyError:
            print("警告: 源文件未找到 $ACADVER 头变量。")
            pass
            
        # 获取模型空间
        msp = doc.modelspace()
        # --- 新增：展开所有块引用到 modelspace ---
        for insert in list(msp.query('INSERT')):
            try:
                for sub in insert.virtual_entities():
                    msp.add_entity(sub)
            except Exception as e:
                print(f"警告: 无法展开块引用 {insert.dxf.name}: {e}")
        # --- 结束新增 ---
        new_msp = new_doc.modelspace()
        
        # 获取要保留的图层 (使用原始名称)
        layers_to_keep = set() # 使用集合提高查找效率
        decoded_kept_names = [] # 用于日志记录
        original_layer_count = 0
        for layer in doc.layers:
            original_layer_count += 1
            raw_name = layer.dxf.name
            decoded_name = decode_dxf_unicode(raw_name)
            # 使用解码后的名称进行判断
            if should_keep_layer(decoded_name):
                layers_to_keep.add(raw_name) # 保留原始名称
                decoded_kept_names.append(decoded_name) # 记录解码后的名称用于日志
            # else: # 调试用：打印被丢弃的图层
                # print(f"[Discarded] Raw: '{raw_name}', Decoded: '{decoded_name}'")

        # 创建日志内容 (使用解码后的名称列表)
        log_content = [
            f"DXF文件图层过滤报告",
            f"处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"输入文件: {os.path.basename(input_file)}",
            f"原始图层数: {original_layer_count}",
            f"保留图层数: {len(layers_to_keep)}",
            "\n保留的图层列表 (解码后):",
        ]
        # 对解码后的名称排序并添加到日志
        log_content.extend([f"- {name}" for name in sorted(decoded_kept_names)])
        
        # 复制需要保留的图层定义 (使用原始名称匹配)
        for layer in doc.layers:
            layer_name = layer.dxf.name # 使用原始名称
            if layer_name in layers_to_keep:
                # 获取原始图层的属性
                color = layer.dxf.color
                linetype = layer.dxf.linetype
                
                # 检查图层是否已存在
                if layer_name == '0':
                    # 对于 "0" 图层，修改现有的属性
                    new_layer = new_doc.layers.get('0')
                    new_layer.dxf.color = color
                    new_layer.dxf.linetype = linetype
                else:
                    # 对于其他图层，检查是否存在，不存在则创建
                    if layer_name not in new_doc.layers:
                        new_layer = new_doc.layers.new(name=layer_name)
                        new_layer.dxf.color = color
                        new_layer.dxf.linetype = linetype
        
        # 复制指定图层的实体 (使用原始名称匹配)
        copied_entity_count = 0
        for entity in msp:
            # 确保实体有关联的图层属性
            if hasattr(entity, 'dxf') and hasattr(entity.dxf, 'layer'):
                entity_layer_name = entity.dxf.layer # 获取实体的图层名 (原始名称)
                if entity_layer_name in layers_to_keep:
                    try:
                        new_msp.add_entity(entity.copy())
                        copied_entity_count += 1
                    except Exception as copy_e:
                        print(f"警告: 复制实体时出错 (图层: {entity_layer_name}): {copy_e}")
            # else: # 调试用：打印没有图层属性的实体
                # print(f"[Skipped Entity] Type: {entity.dxftype()}, No layer attribute")
        
        print(f"信息: 共复制 {copied_entity_count} 个实体到新文件。")
        
        # 保存新文件
        new_doc.saveas(output_file)
        
        # --- 移除日志文件写入 --- 
        # # 保存日志文件
        # log_file = os.path.splitext(output_file)[0] + '_report.txt'
        # with open(log_file, 'w', encoding='utf-8') as f:
        #     f.write('\n'.join(log_content))
        # ------------------------
        
        # 返回成功状态、消息和解码后的保留图层名列表
        return True, "文件处理成功", sorted(decoded_kept_names)
        
    except ezdxf.DXFError as e:
        return False, f"DXF文件错误: {str(e)}", None
    except Exception as e:
        return False, f"处理出错: {str(e)}", None

def main():
    """
    主函数 - 批量处理DXF文件
    """
    # --- 定义输入输出目录 --- 
    input_dir = "/home/jay/AGSeg_ws/AGSeg/cad2osm/data/SEM/dxf"
    output_dxf_dir = "/home/jay/AGSeg_ws/AGSeg/cad2osm/data/SEM/dxf/auto_filter"
    output_layer_info_dir = "/home/jay/AGSeg_ws/AGSeg/cad2osm/data/SEM/layer_info/auto_filter"
    # -------------------------
    
    # 确保输出目录存在
    os.makedirs(output_dxf_dir, exist_ok=True)
    os.makedirs(output_layer_info_dir, exist_ok=True)
    
    # 查找输入目录下的所有dxf文件
    dxf_files = [f for f in os.listdir(input_dir) if f.lower().endswith('.dxf')]
    
    if not dxf_files:
        print(f"错误: 在 '{input_dir}' 目录下未找到任何 .dxf 文件。")
        return
        
    print(f"找到 {len(dxf_files)} 个 DXF 文件，开始处理...")
    success_count = 0
    fail_count = 0
    
    for filename in dxf_files:
        input_file_path = os.path.join(input_dir, filename)
        output_dxf_file_path = os.path.join(output_dxf_dir, filename)
        base_name = os.path.splitext(filename)[0]
        output_layer_info_file_path = os.path.join(output_layer_info_dir, f"layer-info-filtered-{base_name}.txt")
        
        print(f"\n--- 正在处理: {filename} ---")
        
        # 调用过滤函数
        success, message, kept_decoded_layers = filter_dxf_layers(input_file_path, output_dxf_file_path)
        
        if success:
            success_count += 1
            print(f"  -> 过滤后的DXF已保存至: {output_dxf_file_path}")
            
            # 将保留的解码后图层名写入文件
            try:
                with open(output_layer_info_file_path, 'w', encoding='utf-8') as f_info:
                    if kept_decoded_layers:
                         f_info.write('\n'.join(kept_decoded_layers))
                         f_info.write('\n') # 确保末尾有换行符
                    else:
                         f_info.write('') # 如果没有保留图层，则写入空文件
                print(f"  -> 保留图层信息已保存至: {output_layer_info_file_path}")
            except IOError as io_err:
                print(f"  -> 错误: 无法写入图层信息文件 '{output_layer_info_file_path}': {io_err}")
                # 即使写入图层信息失败，也算DXF处理成功
        else:
            fail_count += 1
            print(f"  -> 错误: 处理文件 '{filename}' 失败: {message}")

    # 打印总结
    print("\n--- 批量处理完成 --- ")
    print(f"成功处理文件数: {success_count}")
    print(f"失败文件数: {fail_count}")
    print(f"过滤后的DXF文件保存在: {output_dxf_dir}")
    print(f"保留图层信息文件保存在: {output_layer_info_dir}")
    

if __name__ == "__main__":
    main()
import ezdxf
import os
from datetime import datetime

# 定义过滤规则
LAYER_RULES = {
    'keywords_en': [
        'WALL', 'DOOR', 'WINDOW', 'STRS', 'STAIR',  # 基础构件
        'GLAZ', 'SLAB', 'EVTR',                     # 玻璃、楼板、电梯
        'FRAM', 'FIXT'                              # 框架、固定装置
    ],
    'keywords_cn': [
        '墙体', '门窗', '楼梯', '电梯'
    ],
    'system_layers': [
        '0',
        'Defpoints'
    ],
    'area_prefixes': [
        'E1-RD', 'E1-RI', 'E1-RV', 'E1-RW',
        'E2-RD', 'E2-RI', 'E2-RV', 'E2-RW'
    ],
    'exclude_patterns': [
        'TEMP',
        'DIMS'
    ],
    'special_include': [
        '$TD_AUDIT_GENERATED_'  # 新增特殊包含规则
    ]
}

def should_keep_layer(layer_name):
    """
    根据规则判断是否保留图层
    """
    # 检查是否是系统图层
    if layer_name in LAYER_RULES['system_layers']:
        return True
        
    # 检查是否包含特殊需要包含的模式
    for pattern in LAYER_RULES['special_include']:
        if pattern in layer_name.upper():
            return True
            
    # 检查是否包含需要排除的模式
    for pattern in LAYER_RULES['exclude_patterns']:
        if pattern in layer_name.upper():
            return False
            
    # 检查英文关键词
    for keyword in LAYER_RULES['keywords_en']:
        if keyword in layer_name.upper():
            return True
            
    # 检查中文关键词
    for keyword in LAYER_RULES['keywords_cn']:
        if keyword in layer_name:
            return True
            
    # 检查区域前缀
    for prefix in LAYER_RULES['area_prefixes']:
        if prefix in layer_name and any(kw in layer_name.upper() for kw in LAYER_RULES['keywords_en']):
            return True
            
    return False

def filter_dxf_layers(input_file, output_file):
    """
    根据预定义规则过滤DXF文件图层
    """
    try:
        # 读取源DXF文件
        doc = ezdxf.readfile(input_file)
        
        # 创建新的DXF文档
        new_doc = ezdxf.new()
        
        # 复制原文件的设置
        new_doc.header = doc.header
        new_doc.header['$ACADVER'] = doc.header['$ACADVER']
        
        # 获取模型空间
        msp = doc.modelspace()
        new_msp = new_doc.modelspace()
        
        # 获取要保留的图层
        layers_to_keep = [layer.dxf.name for layer in doc.layers if should_keep_layer(layer.dxf.name)]
        
        # 创建日志内容
        log_content = [
            f"DXF文件图层过滤报告",
            f"处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"输入文件: {os.path.basename(input_file)}",
            f"原始图层数: {len(list(doc.layers))}",
            f"保留图层数: {len(layers_to_keep)}",
            "\n保留的图层列表:",
        ]
        log_content.extend([f"- {layer}" for layer in sorted(layers_to_keep)])
        
        # 复制需要保留的图层定义
        for layer in doc.layers:
            layer_name = layer.dxf.name
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
        
        # 复制指定图层的实体
        for entity in msp:
            if entity.dxf.layer in layers_to_keep:
                new_msp.add_entity(entity.copy())
        
        # 保存新文件
        new_doc.saveas(output_file)
        
        # 保存日志文件
        log_file = os.path.splitext(output_file)[0] + '_report.txt'
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(log_content))
        
        return True, "文件处理成功", log_file
        
    except ezdxf.DXFError as e:
        return False, f"DXF文件错误: {str(e)}", None
    except Exception as e:
        return False, f"处理出错: {str(e)}", None

def main():
    """
    主函数
    """
    # 设置输入输出文件路径
    input_file = input("请输入DXF文件路径: ").strip('"')
    if not os.path.exists(input_file):
        print("错误: 输入文件不存在")
        return
        
    # 生成输出文件名
    output_dir = os.path.dirname(input_file) or '.'
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(output_dir, f"{base_name}_filtered_{timestamp}.dxf")
    
    print(f"\n正在处理文件: {os.path.basename(input_file)}")
    success, message, log_file = filter_dxf_layers(input_file, output_file)
    
    if success:
        print(f"\n{message}")
        print(f"输出文件已保存至: {output_file}")
        print(f"过滤报告已保存至: {log_file}")
    else:
        print(f"\n错误: {message}")

if __name__ == "__main__":
    main()
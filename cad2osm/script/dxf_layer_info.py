# dxf_layer_info.py，用以获悉转换后的dxf的图层的信息
import ezdxf
import os
import re # 导入 re 模块
from datetime import datetime

def decode_dxf_unicode(text):
    r"""解码 DXF 文件中的 \M+XXXX Unicode 转义序列"""
    def replace_match(match):
        unicode_hex = match.group(1)
        try:
            unicode_int = int(unicode_hex, 16)
            char = ""
            
            # --- 尝试 GBK 解码 --- 
            decoded_from_gbk = False
            if unicode_int > 0xFFFF: # 仅对大数尝试 GBK 解码
                try:
                    # 提取低 16 位，尝试 big-endian
                    lower_16 = unicode_int & 0xFFFF
                    gbk_bytes = lower_16.to_bytes(2, byteorder='big')
                    potential_char = gbk_bytes.decode('gbk')
                    # 检查解码结果是否合理 (例如，不是空字符串或单个奇怪字符)
                    # 简单的检查：长度为1且不是典型的替换字符
                    if len(potential_char) == 1 and potential_char != '\ufffd':
                         char = potential_char
                         decoded_from_gbk = True
                         print(f"    [Debug] GBK Decode SUCCESS: \\M+{unicode_hex} -> {hex(lower_16)} -> '{char}'")
                except (UnicodeDecodeError, ValueError) as e:
                    print(f"    [Debug] GBK Decode failed for \\M+{unicode_hex} (low 16: {hex(lower_16)}): {e}")
                    pass # GBK 解码失败，继续
            # -----------------------

            # 如果 GBK 解码不成功，则回退到原始 chr() 方法
            if not decoded_from_gbk:
                 char = chr(unicode_int)
                 print(f"  [Debug] Fallback chr() Decode: \\M+{unicode_hex} -> {unicode_int} -> '{char}'")

            return char
        except ValueError:
            # 如果转换失败，返回原始匹配项
            return match.group(0)
            
    # 正则表达式查找 \M+ followed by 4 or 5 hex digits
    # 使用 re.escape(r'\M+') 可能更安全，但这里直接写出
    pattern = r'\\M\+([0-9A-Fa-f]{4,5})' 
    return re.sub(pattern, replace_match, text)

def extract_layer_info(dxf_file, output_file):
    """
    从DXF文件中提取图层信息并保存到文本文件
    
    参数:
    dxf_file (str): DXF文件路径
    output_file (str): 输出文本文件路径
    """
    try:
        # 读取DXF文件
        doc = ezdxf.readfile(dxf_file)
        
        # 获取所有图层名，并进行解码
        layers = []
        for layer in doc.layers:
            raw_name = layer.dxf.name
            # --- 添加调试打印 ---
            if r'\M+' in raw_name:
                 print(f"[Debug] Processing raw layer name: '{raw_name}'")
            # -------------------
            decoded_name = decode_dxf_unicode(raw_name)
            # --- 添加调试打印 ---
            if r'\M+' in raw_name: # 只有当发生解码时才打印解码结果
                 print(f"[Debug]   Decoded to: '{decoded_name}'")
            # -------------------
            layers.append(decoded_name)
        
        # 准备输出信息
        output_text = [
            f"DXF文件图层信息报告",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"DXF文件: {os.path.basename(dxf_file)}",
            f"图层总数: {len(layers)}",
            "\n图层列表:",
        ]
        
        # 添加图层信息
        for i, layer_name in enumerate(sorted(layers), 1):
            output_text.append(f"{i}. {layer_name}")
        
        # 写入文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(output_text))
            
        return True, "图层信息已成功导出"
        
    except ezdxf.DXFError as e:
        return False, f"DXF文件错误: {str(e)}"
    except Exception as e:
        return False, f"处理出错: {str(e)}"

def main():
    # --- 在这里指定固定的输入DXF和输出TXT路径 ---
    hardcoded_dxf_path = "/home/jay/AGSeg_ws/AGSeg/cad2osm/data/data_dxf/SIST-F1.dxf"  # <--- 修改这里
    hardcoded_output_path = "/home/jay/AGSeg_ws/AGSeg/cad2osm/data/data_info/SIST-F1_layer_info.txt" # <--- 修改这里
    # -------------------------------------------

    print(f"\n正在处理文件: {os.path.basename(hardcoded_dxf_path)}")
    # 使用硬编码路径调用函数
    success, message = extract_layer_info(hardcoded_dxf_path, hardcoded_output_path)
    
    if success:
        print(f"\n{message}")
        print(f"输出文件已保存至: {hardcoded_output_path}")
    else:
        print(f"\n错误: {message}")

if __name__ == "__main__":
    main()
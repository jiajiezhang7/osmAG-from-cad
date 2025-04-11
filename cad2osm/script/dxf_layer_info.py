import ezdxf
import os
import re # 导入 re 模块
import argparse # 导入 argparse 模块
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
        for layer_name in sorted(layers):
            output_text.append(layer_name) # 只输出图层名称

        # 写入文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(output_text))
            
        return True, "图层信息已成功导出"
        
    except ezdxf.DXFError as e:
        return False, f"DXF文件错误: {str(e)}"
    except Exception as e:
        return False, f"Processing error: {str(e)}"

def main():
    # --- 硬编码输入输出路径 ---
    input_dir = "/home/jay/AGSeg_ws/AGSeg/cad2osm/data/data_dxf/us-standard-download"
    output_dir = "/home/jay/AGSeg_ws/AGSeg/cad2osm/data/data_info/us-standard-download-original"

    # --- 检查输入目录是否存在 --- 
    if not os.path.isdir(input_dir):
        print(f"Error: Input directory not found: {input_dir}")
        return

    # --- 确保输出目录存在 --- 
    os.makedirs(output_dir, exist_ok=True)

    print(f"Starting DXF layer info extraction...")
    print(f"Input Directory: {input_dir}")
    print(f"Output Directory: {output_dir}")

    processed_count = 0
    error_count = 0

    # --- 递归遍历输入目录 --- 
    for root, _, files in os.walk(input_dir):
        for filename in files:
            # 检查文件扩展名 (忽略大小写)
            if filename.lower().endswith(".dxf"):
                dxf_path = os.path.join(root, filename)
                
                # 构建相对路径和输出路径
                relative_path = os.path.relpath(dxf_path, input_dir)
                base_rel_path, _ = os.path.splitext(relative_path)
                output_filename = base_rel_path + "_layer_info.txt"
                output_path = os.path.join(output_dir, output_filename)

                # 确保输出文件的目录存在
                output_file_dir = os.path.dirname(output_path)
                os.makedirs(output_file_dir, exist_ok=True)

                print(f"\nProcessing file: {dxf_path}")
                # 调用提取函数
                success, message = extract_layer_info(dxf_path, output_path)
                
                if success:
                    print(f"  -> Success: Layer info saved to {output_path}")
                    processed_count += 1
                else:
                    print(f"  -> Error: {message}")
                    error_count += 1

    print(f"\n--- Processing Complete ---")
    print(f"Successfully processed: {processed_count} files")
    print(f"Errors encountered: {error_count} files")

if __name__ == "__main__":
    main()
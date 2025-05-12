# 输入：
    # DXF文件（CAD格式文件）
    # 目标图层名称（默认为'I—平面—文字'）

# 输出：
    # JSON文件，包含提取的文本内容和它们在DXF中的坐标

# 工作原理：
    # 使用ezdxf库读取DXF文件
    # 解码DXF中的Unicode转义序列（特别是处理中文字符）
    # 提取指定图层中的TEXT、MTEXT实体和INSERT实体的属性文本
    # 过滤掉不需要的文本元素（如特级防火卷帘、排风井等非房间名称）
    # 保存文本内容及其插入点坐标

import ezdxf
import os
import json
import argparse
from pathlib import Path
import re # Import re module for decoding function
import yaml

# 定义需要过滤的文本列表
FILTER_TEXT_LIST = [
    "特级防火卷帘", 
    "防火卷帘",
    "排风井", 
    "暖水", 
    "残疾人出入口",
    "特级",
    "防火",
    "送风",
    "排风",
    "风井",
    "水井",
    "挡烟垂壁",
    "上",
    "下",
    "自动玻璃门",
    "入口",
    "弱电间",
    "排烟井",

]

# --- Copied decoding function from dxf_layer_info.py ---
def decode_dxf_unicode(text):
    r"""解码 DXF 文件中的 \M+XXXX Unicode 转义序列"""
    if text is None:
        return ""
    # Simple check if decoding is likely needed
    if r'\M+' not in text:
        return text

    def replace_match(match):
        unicode_hex = match.group(1)
        try:
            unicode_int = int(unicode_hex, 16)
            char = ""

            # --- 尝试 GBK 解码 --- 
            decoded_from_gbk = False
            if unicode_int > 0xFFFF: # 仅对大数尝试 GBK 解码
                try:
                    lower_16 = unicode_int & 0xFFFF
                    gbk_bytes = lower_16.to_bytes(2, byteorder='big')
                    potential_char = gbk_bytes.decode('gbk')
                    if len(potential_char) == 1 and potential_char != '\ufffd':
                         char = potential_char
                         decoded_from_gbk = True
                         # print(f"    [Debug] GBK Decode SUCCESS: \\M+{unicode_hex} -> {hex(lower_16)} -> '{char}'") # Keep debug prints commented out for normal use
                except (UnicodeDecodeError, ValueError):
                    # print(f"    [Debug] GBK Decode failed for \\M+{unicode_hex} (low 16: {hex(lower_16)}): {e}")
                    pass
            # -----------------------

            if not decoded_from_gbk:
                 try:
                     char = chr(unicode_int)
                     # print(f"  [Debug] Fallback chr() Decode: \\M+{unicode_hex} -> {unicode_int} -> '{char}'")
                 except ValueError: # Handle cases where unicode_int is out of range for chr()
                     return match.group(0) # Return original if chr() fails

            return char
        except ValueError:
            return match.group(0)

    pattern = r'\\M\+([0-9A-Fa-f]{4,5})' # Corrected pattern
    # Perform substitution
    decoded_text = re.sub(pattern, replace_match, text)
    # Also handle potential standard escapes like \U+XXXX if necessary, though \M+ is primary focus here
    # Example (optional): decoded_text = decoded_text.encode().decode('unicode_escape')
    return decoded_text
# --- End of copied function ---

def should_filter_text(text):
    """检查文本是否应该被过滤掉"""
    # 如果文本完全匹配过滤列表中的任何一项，则过滤掉
    for filter_text in FILTER_TEXT_LIST:
        if filter_text in text:
            return True
    return False

def extract_text_from_dxf(dxf_path, output_dir, target_layer):
    """Extracts text from entities on a specific layer, decoding names and content."""
    try:
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()
    except IOError:
        print(f"Error: Cannot open DXF file: {dxf_path}")
        return
    except ezdxf.DXFStructureError:
        print(f"Error: Invalid or corrupted DXF file: {dxf_path}")
        return

    extracted_data = []
    filtered_count = 0
    # Process INSERT entities
    for entity in msp.query('INSERT'):
        # Decode the layer name before comparison
        decoded_layer_name = decode_dxf_unicode(entity.dxf.layer)
        if decoded_layer_name == target_layer:
            insert_point = entity.dxf.insert
            block_name = decode_dxf_unicode(entity.dxf.name) # Also decode block name

            for attrib in entity.attribs:
                # Decode attribute text content and tag
                text_content = decode_dxf_unicode(attrib.dxf.text)
                attrib_tag = decode_dxf_unicode(attrib.dxf.tag)

                cleaned_text = text_content.strip()

                if cleaned_text and not should_filter_text(cleaned_text):
                    extracted_data.append({
                        "block_name": block_name,
                        "attribute_tag": attrib_tag,
                        "text": cleaned_text,
                        "insert_point": [insert_point.x, insert_point.y, insert_point.z]
                    })
                elif cleaned_text:
                    filtered_count += 1

    # Process TEXT and MTEXT entities
    for entity in msp.query('TEXT MTEXT'):
        # Decode the layer name before comparison
        decoded_layer_name = decode_dxf_unicode(entity.dxf.layer)
        if decoded_layer_name == target_layer:
            text_content = ""
            if entity.dxftype() == 'TEXT':
                text_content = decode_dxf_unicode(entity.dxf.text)
            elif entity.dxftype() == 'MTEXT':
                 # MTEXT's .text property usually returns decoded text, but apply anyway for consistency or edge cases
                text_content = decode_dxf_unicode(entity.text)

            insert_point = entity.dxf.insert
            entity_type = entity.dxftype()

            cleaned_text = text_content.strip()

            if cleaned_text and not should_filter_text(cleaned_text):
                extracted_data.append({
                    "entity_type": entity_type,
                    "text": cleaned_text,
                    "insert_point": [insert_point.x, insert_point.y, insert_point.z]
                })
            elif cleaned_text:
                filtered_count += 1

    if not extracted_data:
        print(f"No relevant text entities (decoded layer '{target_layer}') found in {Path(dxf_path).name}")
        return
        
    print(f"提取了 {len(extracted_data)} 个文本元素，过滤掉 {filtered_count} 个不相关文本元素")

    # Prepare output JSON file path
    output_filename = Path(dxf_path).stem + ".json"
    output_path = Path(output_dir) / output_filename

    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Save data to JSON
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(extracted_data, f, ensure_ascii=False, indent=4)
        print(f"成功从图层 '{target_layer}' 提取文本并保存到: {output_path}")
        print(f"总共提取了 {len(extracted_data)} 个文本元素，过滤掉 {filtered_count} 个不相关文本元素")
    except IOError:
        print(f"Error: Cannot write JSON file: {output_path}")
    except Exception as e:
        print(f"An unexpected error occurred while writing JSON for {dxf_path}: {e}")

def load_yaml_config(config_path):
    """加载YAML配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        print(f"已加载配置文件: {config_path}")
        return config
    except Exception as e:
        print(f"警告: 无法加载配置文件 {config_path}: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Extract decoded TEXT, MTEXT, or ATTRIB text from a specific layer in DXF files.')
    parser.add_argument('--input-dir', type=str, default='/home/jay/AGSeg_ws/AGSeg/cad2osm/data/SIST/dxf/original',
                        help='Directory containing the input DXF files.')
    parser.add_argument('--output-dir', type=str, default='/home/jay/AGSeg_ws/AGSeg/cad2osm/data/SIST/extract_text',
                        help='Directory to save the output JSON files.')
    parser.add_argument('--layer', type=str, default='I—平面—文字',
                        help='The specific layer to extract text from.')
    parser.add_argument('--config', type=str, default='/home/jay/AGSeg_ws/AGSeg/area_graph_segment/config/params.yaml',
                        help='配置文件路径')

    args = parser.parse_args()

    input_directory = args.input_dir
    output_directory = args.output_dir
    target_layer_name = args.layer

    if not os.path.isdir(input_directory):
        print(f"Error: Input directory not found: {input_directory}")
        return

    print(f"Starting decoded text extraction from DXF files in: {input_directory}")
    print(f"Output will be saved to: {output_directory}")
    print(f"Target layer: {target_layer_name}")

    for filename in os.listdir(input_directory):
        if filename.lower().endswith('.dxf'):
            dxf_file_path = os.path.join(input_directory, filename)
            print(f"\nProcessing file: {filename}")
            extract_text_from_dxf(dxf_file_path, output_directory, target_layer_name)

    print("\nText extraction process finished.")

if __name__ == "__main__":
    # Ensure ezdxf is installed: pip install ezdxf
    main()

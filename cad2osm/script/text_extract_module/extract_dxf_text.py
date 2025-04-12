import ezdxf
import os
import json
import argparse
from pathlib import Path
import re # Import re module for decoding function

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

                if cleaned_text:
                    extracted_data.append({
                        "block_name": block_name,
                        "attribute_tag": attrib_tag,
                        "text": cleaned_text,
                        "insert_point": [insert_point.x, insert_point.y, insert_point.z]
                    })

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

            if cleaned_text:
                extracted_data.append({
                    "entity_type": entity_type,
                    "text": cleaned_text,
                    "insert_point": [insert_point.x, insert_point.y, insert_point.z]
                })

    if not extracted_data:
        print(f"No relevant text entities (decoded layer '{target_layer}') found in {Path(dxf_path).name}")
        return

    # Prepare output JSON file path
    output_filename = Path(dxf_path).stem + ".json"
    output_path = Path(output_dir) / output_filename

    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Save data to JSON
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(extracted_data, f, ensure_ascii=False, indent=4)
        print(f"Successfully extracted decoded text from layer '{target_layer}' to: {output_path}")
    except IOError:
        print(f"Error: Cannot write JSON file: {output_path}")
    except Exception as e:
        print(f"An unexpected error occurred while writing JSON for {dxf_path}: {e}")

def main():
    parser = argparse.ArgumentParser(description='Extract decoded TEXT, MTEXT, or ATTRIB text from a specific layer in DXF files.')
    parser.add_argument('--input-dir', type=str, default='/home/jay/AGSeg_ws/AGSeg/cad2osm/data/data_dxf/original',
                        help='Directory containing the input DXF files.')
    parser.add_argument('--output-dir', type=str, default='/home/jay/AGSeg_ws/AGSeg/cad2osm/data/extracted_text',
                        help='Directory to save the output JSON files.')
    parser.add_argument('--layer', type=str, default='I—平面—文字',
                        help='The specific layer to extract text from.')

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

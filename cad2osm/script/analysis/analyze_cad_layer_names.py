import os
import re
from collections import Counter
import argparse

def analyze_layer_names(data_dir):
    """
    Analyzes layer names from .txt files in the specified directory.

    Args:
        data_dir (str): The directory containing the layer info .txt files.
    """
    all_layers = []
    layer_files = [f for f in os.listdir(data_dir) if f.endswith('_layer_info.txt')]

    if not layer_files:
        print(f"错误：在目录 '{data_dir}' 中未找到任何 *_layer_info.txt 文件。")
        return

    print(f"在目录 '{data_dir}' 中找到 {len(layer_files)} 个图层信息文件。")

    for filename in layer_files:
        filepath = os.path.join(data_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                # Read lines, strip whitespace, and filter out empty lines and metadata
                layers_in_file = []
                for line in f:
                    stripped_line = line.strip()
                    if not stripped_line: # Skip empty lines
                        continue
                    # Skip known metadata lines
                    if "DXF文件图层信息报告" in stripped_line or \
                       "图层列表:" in stripped_line or \
                       stripped_line.startswith("生成时间:") or \
                       stripped_line.startswith("图层总数:") or \
                       stripped_line.startswith("DXF文件:"):
                        continue
                    layers_in_file.append(stripped_line)
                all_layers.extend(layers_in_file)
        except Exception as e:
            print(f"读取文件 '{filename}' 时出错: {e}")

    if not all_layers:
        print("未从任何文件中成功读取图层名称。")
        return

    print(f"\n共收集到 {len(all_layers)} 个图层名称（包含重复）。")
    unique_layers = sorted(list(set(all_layers)))
    print(f"共有 {len(unique_layers)} 个唯一的图层名称。")

    # --- 分析 ---
    print("\n--- 图层名称分析 ---")

    # 1. 常见图层名称 Top 10
    layer_counts = Counter(all_layers)
    print("\n出现频率最高的 10 个图层名称:")
    for layer, count in layer_counts.most_common(10):
        print(f"- '{layer}': {count} 次")

    # 2. 分隔符分析
    separators = ['-', '_', ' ', '|', ':'] # Add more if needed
    separator_counts = Counter()
    segmented_layers = {} # {separator: [ [part1, part2], ... ]}

    for sep in separators:
        segmented_layers[sep] = []
        for layer in unique_layers:
            if sep in layer:
                separator_counts[sep] += 1
                parts = layer.split(sep)
                # Filter out empty parts that might result from double separators
                parts = [part for part in parts if part]
                if parts:
                    segmented_layers[sep].append(parts)

    print("\n图层名称中分隔符的使用情况:")
    if not separator_counts:
         print("- 未检测到常见分隔符。")
    else:
        for sep, count in separator_counts.items():
            print(f"- 分隔符 '{sep}': 在 {count} 个唯一图层名称中使用")

    # 3. 基于分隔符的结构分析
    print("\n基于分隔符的结构分析 (Top 分隔符):")
    top_separator = separator_counts.most_common(1)[0][0] if separator_counts else None

    if top_separator and segmented_layers.get(top_separator):
        print(f"使用最常见的分隔符 '{top_separator}' 进行分析:")
        part_counts = {} # {index: Counter()}
        segment_lengths = Counter()

        for parts in segmented_layers[top_separator]:
            segment_lengths[len(parts)] += 1
            for i, part in enumerate(parts):
                if i not in part_counts:
                    part_counts[i] = Counter()
                part_counts[i][part.upper()] += 1 # Normalize case for analysis

        print("\n  按分隔符分割后的段数分布:")
        for length, count in segment_lengths.most_common():
             print(f"  - {length} 段: {count} 个图层")

        print("\n  各段常见内容 (Top 5):")
        for index in sorted(part_counts.keys()):
            print(f"    第 {index + 1} 段:")
            for content, count in part_counts[index].most_common(5):
                print(f"      - '{content}': {count} 次")
    elif separator_counts:
        print("- 最常见的分隔符没有有效的分割结果可供分析。")
    else:
         print("- 没有足够的分隔符数据进行结构分析。")

    # 4. 常见前缀/后缀分析 (示例，可扩展)
    prefix_counter = Counter()
    suffix_counter = Counter()
    for layer in unique_layers:
         if '-' in layer:
             parts = layer.split('-')
             if len(parts) > 1:
                 prefix_counter[parts[0]] += 1
                 suffix_counter[parts[-1]] += 1

    if prefix_counter:
        print("\n常见前缀 (基于 '-') (Top 5):")
        for prefix, count in prefix_counter.most_common(5):
             print(f"- '{prefix}-': {count} 次")

    if suffix_counter:
        print("\n常见后缀 (基于 '-') (Top 5):")
        for suffix, count in suffix_counter.most_common(5):
             print(f"- '-{suffix}': {count} 次")

    print("\n--- 分析结束 ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="分析CAD图层名称文件目录中的规律。")
    parser.add_argument("data_dir", type=str, help="包含 *_layer_info.txt 文件的目录路径。")
    args = parser.parse_args()

    if not os.path.isdir(args.data_dir):
        print(f"错误：目录 '{args.data_dir}' 不存在或不是一个有效的目录。")
    else:
        analyze_layer_names(args.data_dir)

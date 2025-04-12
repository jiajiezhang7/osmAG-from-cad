import os
import re
from collections import Counter

# 定义数据目录路径
ORIGINAL_DIR = '../data/SIST-layer-info-original'
FILTERED_DIR = '../data/SIST-layer-info-filtered'

# 获取文件对
def get_file_pairs(original_dir, filtered_dir):
    pairs = {}
    try:
        original_files = {f for f in os.listdir(original_dir) if f.endswith('.txt')}
        filtered_files = {f for f in os.listdir(filtered_dir) if f.endswith('.txt')}

        for orig_file in original_files:
            # 尝试匹配文件名，例如 layer-info-sist-f1.txt -> layer-info-filtered-sist-f1.txt
            base_name = orig_file.replace('layer-info-', '')
            expected_filtered_name = f'layer-info-filtered-{base_name}'
            if expected_filtered_name in filtered_files:
                pairs[orig_file] = expected_filtered_name
            else:
                print(f"警告: 找不到与 {orig_file} 匹配的过滤文件，跳过该对。")

    except FileNotFoundError as e:
        print(f"错误: 找不到目录 {e.filename}")
        return None
    return pairs

# 从文件读取图层名称 (跳过标题行)
def read_layers_from_file(filepath):
    layers = set()
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            next(f) # 跳过标题行 '名称'
            for line in f:
                layer_name = line.strip()
                if layer_name: # 忽略空行
                    layers.add(layer_name)
    except FileNotFoundError:
        print(f"错误: 文件未找到 {filepath}")
    except Exception as e:
        print(f"读取文件时出错 {filepath}: {e}")
    return layers

# 分词函数
def tokenize_layer_name(layer_name):
    # 使用 '-', '_', '$', ' ' 作为分隔符，并将结果转为大写
    tokens = re.split(r'[-_$ ]+', layer_name)
    return [token.upper() for token in tokens if token] # 过滤空字符串

# 主分析逻辑
def analyze_layers():
    original_dir_abs = os.path.abspath(os.path.join(os.path.dirname(__file__), ORIGINAL_DIR))
    filtered_dir_abs = os.path.abspath(os.path.join(os.path.dirname(__file__), FILTERED_DIR))

    file_pairs = get_file_pairs(original_dir_abs, filtered_dir_abs)
    if not file_pairs:
        return

    all_kept_layers = set()
    all_discarded_layers = set()

    for orig_file, filtered_file in file_pairs.items():
        print(f"处理文件对: {orig_file} 和 {filtered_file}")
        original_layers = read_layers_from_file(os.path.join(original_dir_abs, orig_file))
        kept_layers = read_layers_from_file(os.path.join(filtered_dir_abs, filtered_file))

        if not original_layers or not kept_layers:
            print(f"跳过文件对 {orig_file}，因为无法读取图层数据。")
            continue

        discarded_layers = original_layers - kept_layers

        all_kept_layers.update(kept_layers)
        all_discarded_layers.update(discarded_layers)

    print(f"\n--- 数据聚合结果 ---")
    print(f"总共分析了 {len(file_pairs)} 对文件。")
    print(f"所有样本中唯一保留的图层总数: {len(all_kept_layers)}")
    print(f"所有样本中唯一舍弃的图层总数: {len(all_discarded_layers)}")

    # Token频率分析
    kept_tokens = Counter()
    for layer in all_kept_layers:
        kept_tokens.update(tokenize_layer_name(layer))

    discarded_tokens = Counter()
    for layer in all_discarded_layers:
        discarded_tokens.update(tokenize_layer_name(layer))

    print("\n--- Token 频率分析 (Top 30) ---")
    print("\n在 '保留' 图层中最常见的 Tokens:")
    for token, count in kept_tokens.most_common(30):
        print(f"- '{token}': {count} 次")

    print("\n在 '舍弃' 图层中最常见的 Tokens:")
    for token, count in discarded_tokens.most_common(30):
        print(f"- '{token}': {count} 次")

    # 可以进一步分析只在保留/舍弃中出现的Tokens等

if __name__ == "__main__":
    analyze_layers()

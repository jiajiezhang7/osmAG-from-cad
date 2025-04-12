import os
import re

# --- 配置 ---
MANUAL_FILTER_DIR = '/home/jay/AGSeg_ws/AGSeg/cad2osm/data/SIST-layer-info-filtered/'
SCRIPT_FILTER_DIR = '/home/jay/AGSeg_ws/AGSeg/cad2osm/data/SIST-layer-info-filtered-trial/'
FLOORS = ['F1', 'F2', 'F3', 'F4', 'F5']
MANUAL_FILE_PREFIX = 'layer-info-filtered-sist-'
SCRIPT_FILE_PREFIX = 'layer-info-filtered-SIST-'
FILE_EXT = '.txt'

# --- 函数 ---
def read_layers_from_file(filepath):
    """从文件中读取图层名称，忽略标题和空行。"""
    layers = set()
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            # 跳过标题行（假设是第一行，并且可能包含 '名称' 或其他标识）
            next(f)
            for line in f:
                layer_name = line.strip()
                # 忽略空行和特定分隔符
                if layer_name and not re.match(r'^[A-Z]---+$', layer_name):
                    layers.add(layer_name)
    except FileNotFoundError:
        print(f"警告：文件未找到 {filepath}")
    except Exception as e:
        print(f"读取文件时出错 {filepath}: {e}")
    return layers

# --- 主逻辑 ---
def main():
    print("开始比较手动过滤和脚本过滤结果...")

    for floor in FLOORS:
        manual_file = os.path.join(MANUAL_FILTER_DIR, f"{MANUAL_FILE_PREFIX}{floor.lower()}{FILE_EXT}")
        script_file = os.path.join(SCRIPT_FILTER_DIR, f"{SCRIPT_FILE_PREFIX}{floor}{FILE_EXT}")

        print(f"\n--- 比较楼层: {floor} ---")
        print(f"手动文件: {manual_file}")
        print(f"脚本文件: {script_file}")

        manual_layers = read_layers_from_file(manual_file)
        script_layers = read_layers_from_file(script_file)

        if not manual_layers and not script_layers:
            print("两个文件都无法读取或为空，跳过此楼层。")
            continue

        common_layers = manual_layers.intersection(script_layers)
        missed_by_script = manual_layers.difference(script_layers) # 手动有，脚本无
        extra_in_script = script_layers.difference(manual_layers)  # 脚本有，手动无

        print(f"统计:")
        print(f"  手动过滤层数: {len(manual_layers)}")
        print(f"  脚本过滤层数: {len(script_layers)}")
        print(f"  共同保留层数: {len(common_layers)}")
        print(f"  脚本遗漏层数 (手动有，脚本无): {len(missed_by_script)}")
        print(f"  脚本多余层数 (脚本有，手动无): {len(extra_in_script)}")

        if missed_by_script:
            print("\n  脚本遗漏的图层:")
            for layer in sorted(list(missed_by_script)):
                print(f"    - {layer}")

        if extra_in_script:
            print("\n  脚本额外保留的图层:")
            for layer in sorted(list(extra_in_script)):
                print(f"    - {layer}")

    print("\n比较完成。")

if __name__ == "__main__":
    main()

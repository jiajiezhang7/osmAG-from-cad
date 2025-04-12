# 此脚本用以整合 dxf_text_to_pixel.py, extract_room_polygons.py, match_text_to_rooms.py

import json
import os
from pathlib import Path
import argparse
import xml.etree.ElementTree as ET
import yaml
import numpy as np
import math
from shapely.geometry import Point, Polygon
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon
from matplotlib.collections import PatchCollection
import matplotlib.colors as mcolors
import random
import sys
import os

# 添加父目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from text_extract_module.dxf_text_to_pixel import load_json_file, save_json_file, dxf_to_pixel_coordinates, convert_text_coordinates
from text_extract_module.extract_room_polygons import load_osm_file, load_yaml_config, latlon_to_pixel, extract_room_polygons
from text_extract_module.match_text_to_rooms import point_in_polygon, distance_to_polygon, match_text_to_rooms

# TODO 整合后的输入和输出
    # 整合后的输入：
    # osmAG.osm文件：AreaGraph生成的OSM文件，包含房间多边形信息
    # extracted_text.json文件：包含DXF文本信息
    # .bounds.json文件：包含DXF到SVG/PNG的转换参数
    # 可选的配置文件：params.yaml，包含坐标转换参数

    # 整合后的输出：
    # 更新后的osmAG.osm文件：包含匹配到的房间名称的OSM文件（最主要的输出）
    # 可选的中间结果：
    # 房间多边形JSON文件
    # 文本像素坐标JSON文件
    # 匹配关系JSON文件
# 整合方案
# 整合后的脚本将执行以下流程：

# 从osmAG.osm文件中提取房间多边形信息
# 将DXF文本坐标转换为像素坐标
# 将文本标签匹配到房间
# 更新osmAG.osm文件中的房间名称
# 整合后的脚本将只需要以下输入：

# osmAG.osm文件路径
# extracted_text.json文件路径
# .bounds.json文件路径
# 可选的配置文件路径


def load_osm_file(file_path):
    """加载OSM XML文件并返回根元素和树对象"""
    try:
        tree = ET.parse(file_path)
        return tree.getroot(), tree
    except Exception as e:
        print(f"Error loading OSM file {file_path}: {e}")
        return None, None

def visualize_matching(rooms_data, text_data, mapping_result, output_path):
    """
    可视化房间多边形和文本标签的匹配结果

    参数:
        rooms_data: 包含房间多边形的数据列表
        text_data: 包含文本坐标的数据列表
        mapping_result: 匹配结果字典
        output_path: 输出图像的路径
    """
    # 创建图形和坐标轴
    fig = plt.figure(figsize=(16, 12))
    ax = plt.gca()

    # 设置坐标轴范围
    all_x = []
    all_y = []
    for room in rooms_data:
        for point in room['polygon']:
            all_x.append(point[0])
            all_y.append(point[1])

    # 添加一些边距
    margin = 100
    if all_x and all_y:  # 确保列表不为空
        ax.set_xlim(min(all_x) - margin, max(all_x) + margin)
        ax.set_ylim(min(all_y) - margin, max(all_y) + margin)

    # 为每个房间ID分配一个随机颜色
    room_colors = {}
    for room in rooms_data:
        room_id = room['id']
        room_colors[room_id] = np.random.rand(3,)  # 随机RGB颜色

    # 绘制所有房间多边形
    for room in rooms_data:
        room_id = room['id']
        polygon = room['polygon']

        # 创建matplotlib多边形对象
        poly = MplPolygon(polygon, closed=True, alpha=0.4,
                         facecolor=room_colors.get(room_id, (0.5, 0.5, 0.5)))
        ax.add_patch(poly)

        # 在多边形中心添加房间ID标签
        if polygon:  # 确保多边形有点
            center_x = sum(p[0] for p in polygon) / len(polygon)
            center_y = sum(p[1] for p in polygon) / len(polygon)
            ax.text(center_x, center_y, f"ID:{room_id}", ha='center', va='center',
                   fontsize=8, color='black', fontweight='bold')

    # 绘制所有文本标签
    for text_item in text_data:
        x, y = text_item['pixel_point']
        text = text_item['text']
        ax.plot(x, y, 'ro', markersize=4)  # 红色点表示文本位置
        ax.text(x, y+10, text, ha='center', va='bottom', fontsize=8, color='red')

    # 绘制匹配关系
    for room_id, texts in mapping_result['matches'].items():
        for text_match in texts:
            text_point = text_match['pixel_point']
            match_type = text_match['match_type']

            # 找到对应的房间多边形中心
            room_polygon = None
            for room in rooms_data:
                if room['id'] == room_id:
                    room_polygon = room['polygon']
                    break

            if room_polygon:
                center_x = sum(p[0] for p in room_polygon) / len(room_polygon)
                center_y = sum(p[1] for p in room_polygon) / len(room_polygon)

                # 绘制从文本到房间中心的连线
                line_style = '-' if match_type == 'inside' else '--'  # 实线表示inside，虚线表示nearby
                line_color = 'green' if match_type == 'inside' else 'blue'
                ax.plot([text_point[0], center_x], [text_point[1], center_y],
                       line_style, color=line_color, linewidth=0.5, alpha=0.7)

    # 添加图例
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color='green', linestyle='-', lw=2, label='Inside Match'),
        Line2D([0], [0], color='blue', linestyle='--', lw=2, label='Nearby Match'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='r', markersize=8, label='Text Position'),
    ]
    ax.legend(handles=legend_elements, loc='upper right')

    # 添加标题和轴标签
    ax.set_title('Room Polygons and Text Matching Visualization')
    ax.set_xlabel('Pixel X')
    ax.set_ylabel('Pixel Y')

    # 保存图像
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Visualization saved to: {output_path}")


def update_osm_tree(osm_tree, matches):
    """
    在内存中更新OSM XML树的房间名称

    参数:
        osm_tree: ElementTree对象
        matches: 匹配结果字典，键为房间ID，值为匹配到的文本列表

    返回:
        更新成功的房间数量
    """
    root = osm_tree.getroot()
    updated_count = 0
    updated_ids = set()

    # 遍历所有way元素
    for way in root.findall('.//way'):
        way_id = way.get('id')

        # 检查这个way是否是房间 (有 indoor=room 标签)
        is_room = False
        for tag in way.findall('./tag'):
            if tag.get('k') == 'indoor' and tag.get('v') == 'room':
                is_room = True
                break

        if not is_room:
            continue

        # 检查这个房间是否有匹配的文本
        if way_id in matches and matches[way_id]:
            # 优先使用'inside'匹配，其次是'nearby'
            # 获取匹配到的第一个合适的文本（如果有多个匹配，简单地使用第一个）

            target_text = None
            inside_matches = [m for m in matches[way_id] if m['match_type'] == 'inside']
            nearby_matches = [m for m in matches[way_id] if m['match_type'] == 'nearby']

            if inside_matches:
                target_text = inside_matches[0]['text'] # 取第一个内部匹配
            elif nearby_matches:
                # 可以根据距离排序，这里简单取第一个附近匹配
                target_text = nearby_matches[0]['text']

            if target_text:
                # 查找或创建name标签
                name_tag = None
                for tag in way.findall('./tag'):
                    if tag.get('k') == 'name':
                        name_tag = tag
                        break

                # 如果找到name标签，更新其值（如果不同）
                if name_tag is not None:
                    if name_tag.get('v') != target_text:
                        print(f"Updating name for room {way_id}: '{name_tag.get('v')}' -> '{target_text}'")
                        name_tag.set('v', target_text)
                        if way_id not in updated_ids:
                             updated_count += 1
                             updated_ids.add(way_id)
                # 如果没有name标签，创建一个
                else:
                    print(f"Adding name tag for room {way_id}: '{target_text}'")
                    new_tag = ET.SubElement(way, 'tag')
                    new_tag.set('k', 'name')
                    new_tag.set('v', target_text)
                    if way_id not in updated_ids:
                        updated_count += 1
                        updated_ids.add(way_id)
            else:
                print(f"Warning: Room {way_id} has matches but no suitable text found.")


    print(f"OSM tree update check complete. {updated_count} room names added or modified.")
    return updated_count

def main():
    parser = argparse.ArgumentParser(description='Integrate text-to-room matching and update OSM file.')
    parser.add_argument('--text-json', type=str, required=True,
                        help='Path to the input JSON file with extracted DXF text data (e.g., extracted_text.json)')
    parser.add_argument('--bounds-json', type=str, required=True,
                        help='Path to the bounds JSON file from dxf2svg.py (e.g., file.bounds.json)')
    parser.add_argument('--input-osm', type=str, required=True,
                        help='Path to the input osmAG.osm file from AreaGraph')
    parser.add_argument('--output-osm', type=str, required=True,
                        help='Path to save the updated OSM file with room names')
    parser.add_argument('--config', type=str, default=None,
                        help='(Optional) Path to the configuration file (params.yaml) for coordinate conversion')
    parser.add_argument('--output-mapping-json', type=str, default=None,
                        help='(Optional) Path to save the detailed matching results JSON file for debugging')
    parser.add_argument('--nearby-threshold', type=float, default=50.0,
                         help='(Optional) Maximum distance (pixels) to consider a text "nearby" a room if not inside.')
    parser.add_argument('--visualize', action='store_true',
                        help='Generate visualization of room polygons and text matching')
    parser.add_argument('--visualization-output', type=str, default=None,
                        help='Path to save the visualization image (default: same directory as output-osm with .png extension)')


    args = parser.parse_args()

    # --- 1. Validate Inputs ---
    if not os.path.isfile(args.text_json):
        print(f"Error: Text JSON file not found: {args.text_json}")
        return
    if not os.path.isfile(args.bounds_json):
        print(f"Error: Bounds JSON file not found: {args.bounds_json}")
        return
    if not os.path.isfile(args.input_osm):
        print(f"Error: Input OSM file not found: {args.input_osm}")
        return

    # --- 2. Load Data ---
    print("Loading input files...")
    text_data_raw = load_json_file(args.text_json)
    bounds_data = load_json_file(args.bounds_json)
    osm_root, osm_tree = load_osm_file(args.input_osm) # Modified to get tree
    config = None
    if args.config:
        if os.path.isfile(args.config):
            config = load_yaml_config(args.config)
            if config:
                print(f"Loaded custom config from: {args.config}")
            else:
                 print(f"Warning: Failed to load custom config file {args.config}. Using defaults.")
        else:
            print(f"Warning: Config file not found: {args.config}. Using defaults.")


    if text_data_raw is None or bounds_data is None or osm_root is None:
        print("Error: Failed to load one or more essential input files.")
        return

    # --- 3. Convert DXF Text Coordinates to Pixel Coordinates ---
    print("\nConverting DXF text coordinates to pixel coordinates...")
    text_data_pixel = convert_text_coordinates(text_data_raw, bounds_data)
    print(f"Converted coordinates for {len(text_data_pixel)} text items.")

    # --- 4. Extract Room Polygons and Convert to Pixel Coordinates ---
    print("\nExtracting room polygons and converting to pixel coordinates...")
    rooms_data_pixel_raw = extract_room_polygons(osm_root, config) # Store raw extraction result
    print(f"Extracted and converted coordinates for {len(rooms_data_pixel_raw)} potential room polygons.")
    if not rooms_data_pixel_raw:
        print("Warning: No rooms found or extracted from the OSM file.")
        # Decide whether to proceed or exit if no rooms are found
        # For now, we'll proceed but matching will likely yield no results.

    # --- Filter out invalid polygons for Shapely ---
    rooms_data_pixel = []
    invalid_room_count = 0
    unclosed_fixed_count = 0
    for room in rooms_data_pixel_raw:
        room_id = room.get('id', 'N/A') # Get room ID for logging
        if 'polygon' in room and isinstance(room['polygon'], list):
            points = room['polygon']
            num_points = len(points)

            if num_points >= 4:
                if points[0] == points[-1]:
                    # Valid closed polygon with enough points
                    rooms_data_pixel.append(room)
                else:
                    # Enough points, but not closed. Try closing it.
                    print(f"Warning: Auto-closing polygon for room ID {room_id}. First and last points differed.")
                    room['polygon'].append(points[0]) # Append first point to close
                    rooms_data_pixel.append(room)
                    unclosed_fixed_count += 1
            elif num_points == 3:
                 # Exactly 3 points, needs closing.
                 print(f"Warning: Auto-closing polygon for room ID {room_id} (had 3 points).")
                 room['polygon'].append(points[0]) # Append first point to close
                 rooms_data_pixel.append(room)
                 unclosed_fixed_count += 1
            else:
                # Less than 3 points, cannot form a valid LinearRing/Polygon
                invalid_room_count += 1
                print(f"Warning: Filtering out room ID {room_id} due to insufficient points ({num_points} < 3).")
        else:
            # Polygon data missing or not a list
            invalid_room_count += 1
            print(f"Warning: Filtering out room ID {room_id} due to missing or invalid 'polygon' data.")

    if invalid_room_count > 0:
        print(f"Filtered out {invalid_room_count} invalid/degenerate room polygons.")
    if unclosed_fixed_count > 0:
        print(f"Auto-closed {unclosed_fixed_count} polygons that had sufficient points but weren't closed.")
    print(f"Processing {len(rooms_data_pixel)} valid room polygons for matching.")


    # --- 5. Match Text Labels to Rooms ---
    print("\nMatching text labels to rooms...")
    # Note: match_text_to_rooms currently doesn't use the threshold, update if needed
    # Adjusting the call signature if the function was updated:
    # mapping_result = match_text_to_rooms(text_data_pixel, rooms_data_pixel, args.nearby_threshold)
    mapping_result = match_text_to_rooms(text_data_pixel, rooms_data_pixel) # Using filtered data now

    matched_count = sum(len(texts) for texts in mapping_result['matches'].values())
    unmatched_count = len(mapping_result['unmatched'])
    total_texts = len(text_data_pixel)
    match_rate = (matched_count / total_texts * 100) if total_texts > 0 else 0
    print(f"Matching complete:")
    print(f"  - Matched texts: {matched_count}/{total_texts} ({match_rate:.2f}%)")
    print(f"  - Unmatched texts: {unmatched_count}")
    print(f"  - Rooms with matches: {len(mapping_result['matches'])}")

    # --- 6. Update OSM File (in memory) ---
    print("\nUpdating OSM tree in memory with matched room names...")
    updated_osm_count = update_osm_tree(osm_tree, mapping_result['matches']) # Use the modified function

    # --- 7. Save Outputs ---
    # Save the updated OSM file
    print(f"\nSaving updated OSM file to: {args.output_osm}")
    try:
        # Ensure output directory exists
        output_osm_dir = os.path.dirname(args.output_osm)
        if output_osm_dir and not os.path.exists(output_osm_dir):
            os.makedirs(output_osm_dir, exist_ok=True)
            print(f"Created output directory: {output_osm_dir}")

        osm_tree.write(args.output_osm, encoding='utf-8', xml_declaration=True)
        print(f"Successfully saved updated OSM file.")
    except Exception as e:
        print(f"Error saving updated OSM file: {e}")

    # Save the optional mapping details JSON
    if args.output_mapping_json:
        print(f"\nSaving detailed mapping results to: {args.output_mapping_json}")
        # Add statistics to the mapping result before saving
        mapping_result['statistics'] = {
            'total_texts': total_texts,
            'matched_texts': matched_count,
            'unmatched_texts': unmatched_count,
            'match_rate': f"{match_rate:.2f}%",
            'rooms_with_matches': len(mapping_result['matches']),
            'rooms_updated_in_osm': updated_osm_count
        }
        save_json_file(mapping_result, args.output_mapping_json)

    # --- 8. Generate Visualization (if requested) ---
    if args.visualize:
        # Determine visualization output path if not specified
        vis_output_path = args.visualization_output
        if not vis_output_path:
            # Use the same directory and base name as output OSM, but with .png extension
            output_base = os.path.splitext(args.output_osm)[0]
            vis_output_path = f"{output_base}_visualization.png"

        print(f"\nGenerating visualization of room polygons and text matching...")
        try:
            # Ensure visualization output directory exists
            vis_output_dir = os.path.dirname(vis_output_path)
            if vis_output_dir and not os.path.exists(vis_output_dir):
                os.makedirs(vis_output_dir, exist_ok=True)

            # Call visualization function
            visualize_matching(rooms_data_pixel, text_data_pixel, mapping_result, vis_output_path)
        except Exception as e:
            print(f"Error generating visualization: {e}")

    print("\nProcessing finished.")

if __name__ == "__main__":
    main()
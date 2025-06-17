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
import matplotlib
# 设置matplotlib支持中文显示
matplotlib.rcParams['font.sans-serif'] = ['Noto Sans CJK SC', 'AR PL UMing CN', 'Droid Sans Fallback', 'DejaVu Sans', 'sans-serif']  # 使用系统中已有的中文字体
matplotlib.rcParams['axes.unicode_minus'] = False  # 解决保存图像时负号'-'显示为方块的问题

# 由于文件已经在同一目录下，直接导入模块
from dxf_text_to_pixel import load_json_file, save_json_file, dxf_to_pixel_coordinates, convert_text_coordinates
from extract_room_polygons import load_osm_file, load_yaml_config, latlon_to_pixel, extract_room_polygons
from match_text_to_rooms import point_in_polygon, distance_to_polygon, match_text_to_rooms, calculate_center_point

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

    # 为每个房间ID分配一个随机颜色（更深的颜色）
    room_colors = {}
    for room in rooms_data:
        room_id = room['id']
        # 生成更深的颜色，减小RGB值的范围
        # 生成与 Qt QColor(rand()%255) 一致的随机色调（0~1 归一化）
        room_colors[room_id] = np.random.rand(3)  # 随机RGB颜色，0~1 全范围

    # 绘制所有房间多边形
    for room in rooms_data:
        room_id = room['id']
        polygon = room['polygon']

        # 创建matplotlib多边形对象
        poly = MplPolygon(polygon, closed=True, alpha=0.7,
                         facecolor=room_colors.get(room_id, (0.3, 0.3, 0.3)),
                         edgecolor='black', linewidth=0.5)  # 添加细边框线
        ax.add_patch(poly)

        # 计算并显示多边形中心点（使用最大内接圆中心）
        if polygon:  # 确保多边形有点
            # 计算简单平均值作为ID标签位置
            # avg_center_x = sum(p[0] for p in polygon) / len(polygon)
            # avg_center_y = sum(p[1] for p in polygon) / len(polygon)
            
            # 计算最大内接圆中心
            center_point = calculate_center_point(polygon)
            center_x, center_y = center_point
            
            # 绘制中心点
            ax.plot(center_x, center_y, 'bx', markersize=4)  # 蓝色x表示中心点
            
            # # 在多边形中心添加房间ID标签（使用平均值位置）
            # ax.text(avg_center_x, avg_center_y, f"ID:{room_id}", ha='center', va='center',
            #        fontsize=6, color='black', fontweight='bold')  # 减小字体大小

    # 处理一对多的文本匹配情况，将多个文本整合成一个完整的字符串
    # 首先按房间ID对文本进行分组和合并
    merged_matches = {}
    
    for room_id, texts in mapping_result['matches'].items():
        # 按匹配类型分组
        inside_matches = [m for m in texts if m['match_type'] == 'inside']
        nearby_matches = [m for m in texts if m['match_type'] == 'nearby']
        
        # 选择优先级更高的匹配组
        selected_matches = inside_matches if inside_matches else nearby_matches
        
        if not selected_matches:
            continue
            
        # 检查是否有已经合并的文本
        has_merged = False
        for match in selected_matches:
            if 'merged' in match and match['merged']:
                # 如果有已经合并的文本，直接使用它
                merged_matches[room_id] = match
                has_merged = True
                break
        
        if not has_merged:
            # 如果没有已经合并的文本，手动合并
            all_texts = [m['text'] for m in selected_matches]
            
            # 过滤掉子字符串
            unique_texts = []
            for text in all_texts:
                is_substring = False
                for other_text in all_texts:
                    if text != other_text and text in other_text:
                        is_substring = True
                        break
                if not is_substring:
                    unique_texts.append(text)
            
            if not unique_texts:
                unique_texts = all_texts
                
            merged_text = " ".join(unique_texts)
            
            # 创建合并后的匹配信息
            merged_match = selected_matches[0].copy()
            merged_match['text'] = merged_text
            merged_match['original_texts'] = all_texts
            merged_match['merged'] = len(all_texts) > 1
            
            merged_matches[room_id] = merged_match
    
    # 创建一个集合，存储所有已合并文本的原始文本ID
    merged_text_ids = set()
    for match in merged_matches.values():
        if 'merged' in match and match['merged']:
            # 收集原始文本的ID
            for original_match in match.get('original_matches', []):
                if 'id' in original_match:
                    merged_text_ids.add(original_match['id'])
    
    # 创建一个集合，用于跟踪已经处理过的文本，避免重复显示
    processed_texts = set()
    
    # 存储已绘制文本的边界框，用于检测重叠
    text_boxes = []



    
    # 绘制所有文本和匹配关系
    # 首先绘制所有匹配的文本
    for room_id, match in merged_matches.items():
        text_point = match['pixel_point']
        match_type = match['match_type']
        text = match['text']
        
        # 将这个文本标记为已处理
        processed_texts.add(text)
        
        # 找到对应的房间多边形中心
        room_polygon = None
        for room in rooms_data:
            if room['id'] == room_id:
                room_polygon = room['polygon']
                break
        
        if room_polygon:
            # 使用最大内接圆中心
            center_point = calculate_center_point(room_polygon)
            center_x, center_y = center_point
            
            # 绘制从文本到房间中心的连线
            line_style = '-' if match_type == 'inside' else '--'  # 实线表示inside，虚线表示nearby
            line_color = 'green' if match_type == 'inside' else 'blue'
            ax.plot([text_point[0], center_x], [text_point[1], center_y],
                   line_style, color=line_color, linewidth=0.5, alpha=0.7)
            
            # 绘制文本
            fontsize = 10  # 增大字体大小以提高可读性
            
            # 计算文本边界框
            text_width = len(text) * fontsize * 0.6
            text_height = fontsize * 1.2
            
            # 文本位置
            text_x, text_y = text_point[0], text_point[1] + 5
            
            # 检查是否与现有文本重叠
            box = [text_x - text_width/2, text_y - text_height, text_x + text_width/2, text_y + text_height]
            overlap = True
            offset = 0
            
            # 尝试不同位置直到找到无重叠位置
            while overlap and offset < 40:  # 限制尝试次数
                overlap = False
                for existing_box in text_boxes:
                    # 检查是否重叠
                    if (box[0] < existing_box[2] and box[2] > existing_box[0] and
                        box[1] < existing_box[3] and box[3] > existing_box[1]):
                        overlap = True
                        break
                
                if overlap:
                    # 尝试向下移动
                    offset += 5
                    text_y = text_point[1] + 5 + offset
                    box = [text_x - text_width/2, text_y - text_height, text_x + text_width/2, text_y + text_height]
            
            # 如果是合并的文本，使用紫色和星号标记
            if 'merged' in match and match['merged']:
                # 添加合并后的文本
                ax.text(text_x, text_y, text, ha='center', va='bottom', fontsize=fontsize, color='purple', fontweight='bold')
                # 添加一个特殊标记表示这是合并后的文本
                ax.plot(text_point[0], text_point[1], '*', color='purple', markersize=8, alpha=0.7)  # 紫色星号表示合并文本
                
                # 如果是合并文本，将所有原始文本也标记为已处理，避免重复显示
                if 'original_texts' in match:
                    for original_text in match['original_texts']:
                        processed_texts.add(original_text)
            else:
                # 添加普通文本
                ax.plot(text_point[0], text_point[1], 'ro', markersize=3)  # 红色点表示文本位置
                ax.text(text_x, text_y, text, ha='center', va='bottom', fontsize=fontsize, color='red')
            
            # 记录文本边界框
            text_boxes.append(box)
    
    # 然后绘制未匹配的文本（那些不在processed_texts中的文本）
    for text_item in text_data:
        text = text_item['text']
        
        # 如果这个文本已经处理过了，就跳过
        if text in processed_texts:
            continue
            
        # 绘制未匹配的文本
        x, y = text_item['pixel_point']
        ax.plot(x, y, 'ro', markersize=3)  # 红色点表示文本位置
        
        # 计算文本边界框的初始位置
        fontsize = 8  # 增大字体大小以提高可读性
        text_width = len(text) * fontsize * 0.6
        text_height = fontsize * 1.2
        
        # 初始文本位置
        text_x, text_y = x, y + 5
        
        # 检查是否与现有文本重叠
        box = [text_x - text_width/2, text_y - text_height, text_x + text_width/2, text_y + text_height]
        overlap = True
        offset = 0
        
        # 尝试不同位置直到找到无重叠位置
        while overlap and offset < 40:  # 限制尝试次数
            overlap = False
            for existing_box in text_boxes:
                # 检查是否重叠
                if (box[0] < existing_box[2] and box[2] > existing_box[0] and
                    box[1] < existing_box[3] and box[3] > existing_box[1]):
                    overlap = True
                    break
            
            if overlap:
                # 尝试向下移动
                offset += 5
                text_y = y + 5 + offset
                box = [text_x - text_width/2, text_y - text_height, text_x + text_width/2, text_y + text_height]
        
        # 添加文本并记录其边界框
        ax.text(text_x, text_y, text, ha='center', va='bottom', fontsize=fontsize, color='red')
        text_boxes.append(box)

    # 添加图例
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color='green', linestyle='-', lw=4, label='Inside Match'),
        Line2D([0], [0], color='blue', linestyle='--', lw=4, label='Nearby Match'),
        Line2D([0], [0], marker='o', color='w', markerfacecolor='r', markersize=12, label='Text Position'),
        Line2D([0], [0], marker='x', color='blue', markersize=12, label='Room Center'),
        Line2D([0], [0], marker='*', color='purple', markersize=16, label='Merged Text'),
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=16, markerscale=1.5, frameon=True, fancybox=True, shadow=True)

    # 添加标题和轴标签
    ax.set_title('Room Polygons and Text Matching Visualization', fontsize=18)
    ax.set_xlabel('Pixel X', fontsize=14)
    ax.set_ylabel('Pixel Y', fontsize=14)
    
    # 设置等比例坐标，确保横纵比例一致
    ax.set_aspect('equal')
    
    # 上下翻转Y轴，确保与其他可视化图像方向一致
    ax.invert_yaxis()
    
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
            # 使用评分机制选择最佳匹配
            # 根据匹配质量评分排序所有匹配，选择评分最高的
            
            # 处理一对多的文本匹配情况，将多个文本整合成一个完整的字符串
            # 首先按匹配类型和评分分组
            inside_matches = [m for m in matches[way_id] if m['match_type'] == 'inside']
            nearby_matches = [m for m in matches[way_id] if m['match_type'] == 'nearby']
            
            # 如果有评分信息，按评分排序
            if inside_matches and 'score' in inside_matches[0]:
                inside_matches = sorted(inside_matches, key=lambda m: m.get('score', 0), reverse=True)
            if nearby_matches and 'score' in nearby_matches[0]:
                nearby_matches = sorted(nearby_matches, key=lambda m: m.get('score', 0), reverse=True)
            
            # 先使用inside匹配，如果没有再使用nearby匹配
            all_matches = inside_matches if inside_matches else nearby_matches
            
            # 如果没有匹配，跳过
            if not all_matches:
                print(f"Warning: Room {way_id} has matches but no suitable text found.")
                continue
                
            # 将所有匹配的文本合并成一个字符串
            # 先收集所有文本
            all_texts = [m['text'] for m in all_matches]
            
            # 为了避免重复，我们可能需要进行一些处理
            # 例如，如果一个文本是另一个文本的子字符串，我们可能只需要保留较长的那个
            unique_texts = []
            for text in all_texts:
                # 检查这个文本是否是其他文本的子字符串
                is_substring = False
                for other_text in all_texts:
                    if text != other_text and text in other_text:
                        is_substring = True
                        break
                if not is_substring:
                    unique_texts.append(text)
            
            # 如果过滤后没有文本，使用原始列表
            if not unique_texts:
                unique_texts = all_texts
            
            # 将所有文本按空格连接成一个字符串
            target_text = " ".join(unique_texts)
            
            # 保存匹配信息供可视化使用
            match_info = all_matches[0].copy()
            match_info['text'] = target_text
            match_info['original_texts'] = all_texts
            match_info['merged'] = len(all_texts) > 1
            match_type = match_info['match_type']

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
    result = extract_room_polygons(osm_root, config) # 获取包含房间和边界信息的结果
    rooms_data_pixel_raw = result['rooms'] # 从结果中获取房间列表
    boundary_info = result['boundary'] # 从结果中获取边界信息
    
    print(f"Extracted and converted coordinates for {len(rooms_data_pixel_raw)} potential room polygons.")
    if not rooms_data_pixel_raw:
        print("Warning: No rooms found or extracted from the OSM file.")
        # Decide whether to proceed or exit if no rooms are found
        # For now, we'll proceed but matching will likely yield no results.
        
    # 如果有边界信息，输出边界信息
    if boundary_info:
        print(f"Using boundary information with {boundary_info['padding_ratio']*100:.1f}% padding.")
        print(f"This ensures consistent coordinate transformation with dxf2svg.py.")

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
    # 使用改进的匹配函数，传递附近匹配阈值和中心距离比例阈值
    mapping_result = match_text_to_rooms(
        text_data_pixel, 
        rooms_data_pixel, 
        nearby_threshold=args.nearby_threshold,
        max_center_distance_ratio=0.7  # 这个参数控制内部匹配的质量评估
    )

    # 从匹配结果中获取统计信息
    if 'match_statistics' in mapping_result:
        stats = mapping_result['match_statistics']
        matched_count = stats['matched_texts']
        unmatched_count = stats['unmatched_texts']
        total_texts = stats['total_texts']
    else:
        # 兼容旧版本的返回结果格式
        matched_count = sum(len(texts) for texts in mapping_result['matches'].values())
        unmatched_count = len(mapping_result['unmatched'])
        total_texts = len(text_data_pixel)
    
    match_rate = (matched_count / total_texts * 100) if total_texts > 0 else 0
    print(f"Matching complete:")
    print(f"  - Matched texts: {matched_count}/{total_texts} ({match_rate:.2f}%)")
    print(f"  - Unmatched texts: {unmatched_count}")
    print(f"  - Rooms with matches: {len(mapping_result['matches'])}")
    
    # 打印高评分匹配的信息
    high_quality_matches = 0
    for room_id, matches in mapping_result['matches'].items():
        for match in matches:
            if 'score' in match and match['score'] >= 70:
                high_quality_matches += 1
    
    if high_quality_matches > 0:
        print(f"  - High quality matches (score >= 70): {high_quality_matches}")

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
        
        # 如果有边界信息，也添加到映射结果中
        if boundary_info:
            mapping_result['boundary_info'] = boundary_info
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
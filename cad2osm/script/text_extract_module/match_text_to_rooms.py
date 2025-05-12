#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
匹配文本标签到房间脚本

输入：
    包含像素坐标的文本JSON文件
    包含房间多边形的JSON文件
    可选的osmAG.osm文件（用于更新）

输出：
    文本到房间的映射关系JSON文件
    可选的更新后的osmAG.osm文件

工作原理：
    使用Shapely库判断文本点是否在房间多边形内
    如果不在多边形内，计算点到多边形的最小距离
    根据位置关系（内部或附近）建立映射
    可选择直接更新OSM文件，将匹配到的文本设置为房间的name标签

用法:
    python match_text_to_rooms.py --text-json <pixel_text.json> --rooms-json <rooms.json> --output-json <mapping.json> [--osm-file <osmAG.osm>] [--update-osm]

参数:
    --text-json: 包含像素坐标的文本JSON文件路径
    --rooms-json: 包含房间多边形的JSON文件路径
    --output-json: 输出的映射关系JSON文件路径
    --osm-file: 可选的osmAG.osm文件路径，用于更新房间名称
    --update-osm: 是否更新osmAG.osm文件，默认为否
"""

import json
import argparse
import os
import math
import xml.etree.ElementTree as ET
from shapely.geometry import Point, Polygon


def load_json_file(file_path):
    """加载JSON文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading JSON file {file_path}: {e}")
        return None


def save_json_file(data, file_path):
    """保存JSON文件"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f"Successfully saved to: {file_path}")
        return True
    except Exception as e:
        print(f"Error saving JSON file {file_path}: {e}")
        return False


def point_in_polygon(point, polygon):
    """
    判断点是否在多边形内

    参数:
        point: [x, y]格式的点坐标
        polygon: [[x1, y1], [x2, y2], ...]格式的多边形顶点列表

    返回:
        布尔值，表示点是否在多边形内
    """
    # 使用Shapely库判断点是否在多边形内
    point_obj = Point(point[0], point[1])
    polygon_obj = Polygon(polygon)
    return polygon_obj.contains(point_obj)


def distance_to_polygon(point, polygon):
    """
    计算点到多边形的最小距离

    参数:
        point: [x, y]格式的点坐标
        polygon: [[x1, y1], [x2, y2], ...]格式的多边形顶点列表

    返回:
        点到多边形的最小距离
    """
    # 使用Shapely库计算点到多边形的距离
    point_obj = Point(point[0], point[1])
    polygon_obj = Polygon(polygon)
    return point_obj.distance(polygon_obj)


def match_text_to_rooms(text_data, rooms_data):
    """
    将文本标签匹配到房间

    参数:
        text_data: 包含像素坐标的文本数据列表
        rooms_data: 包含房间多边形的数据列表

    返回:
        包含匹配关系的字典
    """
    matches = {}
    unmatched_texts = []

    # 遍历所有文本标签
    for text_item in text_data:
        text = text_item['text']
        pixel_point = text_item['pixel_point']

        # 初始化最佳匹配
        best_match = None
        best_distance = float('inf')
        is_inside = False

        # 遍历所有房间
        for room in rooms_data:
            room_id = room['id']
            polygon = room['polygon']

            # 检查点是否在多边形内
            if point_in_polygon(pixel_point, polygon):
                is_inside = True
                best_match = room_id
                break

            # 如果不在多边形内，计算距离
            distance = distance_to_polygon(pixel_point, polygon)
            if distance < best_distance:
                best_distance = distance
                best_match = room_id

        # 记录匹配结果
        if is_inside:
            # 点在多边形内，直接匹配
            if best_match not in matches:
                matches[best_match] = []
            matches[best_match].append({
                'text': text,
                'pixel_point': pixel_point,
                'match_type': 'inside'
            })
        elif best_distance < 50:  # 设置一个合理的阈值，例如50像素
            # 点不在多边形内，但距离很近
            if best_match not in matches:
                matches[best_match] = []
            matches[best_match].append({
                'text': text,
                'pixel_point': pixel_point,
                'match_type': 'nearby',
                'distance': best_distance
            })
        else:
            # 未找到合适的匹配
            unmatched_texts.append({
                'text': text,
                'pixel_point': pixel_point,
                'best_candidate': best_match,
                'distance': best_distance
            })

    # 返回匹配结果和未匹配的文本
    return {
        'matches': matches,
        'unmatched': unmatched_texts
    }


def update_osm_file(osm_file_path, matches):
    """
    更新osmAG.osm文件中房间的name标签

    参数:
        osm_file_path: osmAG.osm文件路径
        matches: 匹配结果字典，键为房间ID，值为匹配到的文本列表

    返回:
        更新成功的房间数量
    """
    try:
        # 解析XML文件
        tree = ET.parse(osm_file_path)
        root = tree.getroot()

        # 记录更新数量
        updated_count = 0

        # 遍历所有way元素
        for way in root.findall('.//way'):
            way_id = way.get('id')

            # 检查这个way是否有匹配的文本
            if way_id in matches and matches[way_id]:
                # 获取匹配到的第一个文本（如果有多个匹配，只使用第一个）
                text = matches[way_id][0]['text']

                # 查找name标签
                name_tag = None
                for tag in way.findall('./tag'):
                    if tag.get('k') == 'name':
                        name_tag = tag
                        break

                # 如果找到name标签，更新其值
                if name_tag is not None:
                    name_tag.set('v', text)
                    updated_count += 1
                # 如果没有name标签，创建一个
                else:
                    new_tag = ET.SubElement(way, 'tag')
                    new_tag.set('k', 'name')
                    new_tag.set('v', text)
                    updated_count += 1

        # 保存更新后的XML文件
        tree.write(osm_file_path, encoding='utf-8', xml_declaration=True)
        print(f"Successfully updated {updated_count} room names in {osm_file_path}")
        return updated_count

    except Exception as e:
        print(f"Error updating OSM file: {e}")
        return 0


def main():
    parser = argparse.ArgumentParser(description='Match text labels to rooms.')
    parser.add_argument('--text-json', type=str, required=True,
                        help='Path to the JSON file with text pixel coordinates')
    parser.add_argument('--rooms-json', type=str, required=True,
                        help='Path to the JSON file with room polygons')
    parser.add_argument('--output-json', type=str, required=True,
                        help='Path to save the output mapping JSON file')
    parser.add_argument('--osm-file', type=str, default=None,
                        help='Path to the osmAG.osm file to update room names')
    parser.add_argument('--update-osm', action='store_true',
                        help='Update room names in the osmAG.osm file')

    args = parser.parse_args()

    # 检查输入文件是否存在
    if not os.path.isfile(args.text_json):
        print(f"Error: Text JSON file not found: {args.text_json}")
        return

    if not os.path.isfile(args.rooms_json):
        print(f"Error: Rooms JSON file not found: {args.rooms_json}")
        return

    # 检查OSM文件（如果需要更新）
    if args.update_osm:
        if args.osm_file is None:
            print("Error: --osm-file must be specified when --update-osm is used.")
            return
        if not os.path.isfile(args.osm_file):
            print(f"Error: OSM file not found: {args.osm_file}")
            return

    # 创建输出目录（如果不存在）
    output_dir = os.path.dirname(args.output_json)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # 加载输入文件
    text_data = load_json_file(args.text_json)
    rooms_data = load_json_file(args.rooms_json)

    if text_data is None or rooms_data is None:
        print("Error: Failed to load input files.")
        return

    # 匹配文本到房间
    mapping_result = match_text_to_rooms(text_data, rooms_data)

    # 添加统计信息
    total_texts = len(text_data)
    matched_count = sum(len(texts) for texts in mapping_result['matches'].values())
    unmatched_count = len(mapping_result['unmatched'])

    mapping_result['statistics'] = {
        'total_texts': total_texts,
        'matched_texts': matched_count,
        'unmatched_texts': unmatched_count,
        'match_rate': f"{(matched_count / total_texts * 100):.2f}%"
    }

    # 保存结果
    success = save_json_file(mapping_result, args.output_json)

    if success:
        print(f"Successfully matched {matched_count} out of {total_texts} text items.")
        print(f"Match rate: {(matched_count / total_texts * 100):.2f}%")
        print(f"Unmatched texts: {unmatched_count}")

    # 如果需要，更新OSM文件
    if args.update_osm and args.osm_file:
        print(f"\nUpdating room names in {args.osm_file}...")
        updated_count = update_osm_file(args.osm_file, mapping_result['matches'])
        print(f"Updated {updated_count} out of {len(mapping_result['matches'])} matched rooms.")


if __name__ == "__main__":
    main()

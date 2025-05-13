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


def calculate_polygon_area(polygon):
    """
    计算多边形面积

    参数:
        polygon: [[x1, y1], [x2, y2], ...] 格式的多边形顶点列表

    返回:
        多边形面积
    """
    polygon_obj = Polygon(polygon)
    return polygon_obj.area


def calculate_largest_inscribed_circle(polygon):
    """
    计算多边形的最大内接圆

    参数:
        polygon: [[x1, y1], [x2, y2], ...] 格式的多边形顶点列表

    返回:
        (center_x, center_y, radius) 内接圆的中心点和半径
    """
    from shapely.geometry import Polygon
    from scipy.spatial import distance
    import numpy as np
    
    # 创建Shapely多边形对象
    polygon_obj = Polygon(polygon)
    
    # 如果多边形无效或太小，返回质心
    if not polygon_obj.is_valid or polygon_obj.area < 1:
        centroid = polygon_obj.centroid
        return centroid.x, centroid.y, 0
    
    # 生成多边形内部的网格点
    bounds = polygon_obj.bounds
    width = bounds[2] - bounds[0]
    height = bounds[3] - bounds[1]
    
    # 计算适当的网格分辨率
    # 对于大多边形使用更精细的网格，对于小多边形使用更粗糙的网格
    grid_size = min(max(width, height) / 20, 10)  # 限制网格大小以提高效率
    
    x = np.arange(bounds[0], bounds[2], grid_size)
    y = np.arange(bounds[1], bounds[3], grid_size)
    xx, yy = np.meshgrid(x, y)
    points = np.vstack([xx.ravel(), yy.ravel()]).T
    
    # 过滤出多边形内部的点
    mask = np.array([polygon_obj.contains(Point(p[0], p[1])) for p in points])
    interior_points = points[mask]
    
    # 如果没有内部点，返回质心
    if len(interior_points) == 0:
        centroid = polygon_obj.centroid
        return centroid.x, centroid.y, 0
    
    # 对每个内部点，计算到多边形边界的最小距离
    boundary = np.array(polygon_obj.exterior.coords)
    min_distances = []
    
    for point in interior_points:
        # 计算点到多边形边界的最小距离
        dist = polygon_obj.boundary.distance(Point(point))
        min_distances.append(dist)
    
    # 找到最大距离对应的点（内接圆中心）
    max_index = np.argmax(min_distances)
    center = interior_points[max_index]
    radius = min_distances[max_index]
    
    return center[0], center[1], radius

def calculate_center_point(polygon):
    """
    计算多边形中心点，使用最大内接圆的中心

    参数:
        polygon: [[x1, y1], [x2, y2], ...] 格式的多边形顶点列表

    返回:
        [x, y] 格式的中心点坐标
    """
    try:
        # 尝试计算最大内接圆的中心
        center_x, center_y, radius = calculate_largest_inscribed_circle(polygon)
        
        # 如果内接圆计算成功（半径大于0），使用内接圆中心
        if radius > 0:
            return [center_x, center_y]
    except Exception as e:
        print(f"Warning: Failed to calculate largest inscribed circle: {e}")
    
    # 如果内接圆计算失败，回退到使用质心
    polygon_obj = Polygon(polygon)
    centroid = polygon_obj.centroid
    return [centroid.x, centroid.y]


def distance_between_points(point1, point2):
    """
    计算两点之间的欧氏距离

    参数:
        point1: [x1, y1] 格式的点坐标
        point2: [x2, y2] 格式的点坐标

    返回:
        两点之间的距离
    """
    return math.sqrt((point1[0] - point2[0])**2 + (point1[1] - point2[1])**2)


def match_text_to_rooms(text_data, rooms_data, nearby_threshold=50, max_center_distance_ratio=0.7):
    """
    将文本标签匹配到房间，使用改进的匹配质量评分机制

    参数:
        text_data: 包含像素坐标的文本数据列表
        rooms_data: 包含房间多边形的数据列表
        nearby_threshold: 考虑附近匹配的最大距离阈值（像素）
        max_center_distance_ratio: 内部匹配时，文本到中心距离与房间特征尺寸的比例阈值

    返回:
        包含匹配关系的字典
    """
    matches = {}
    unmatched_texts = []
    
    # 预计算房间的面积和中心点
    room_properties = {}
    for room in rooms_data:
        room_id = room['id']
        polygon = room['polygon']
        area = calculate_polygon_area(polygon)
        center = calculate_center_point(polygon)
        # 计算房间的特征尺寸（近似为半径）
        characteristic_size = math.sqrt(area / math.pi)
        
        room_properties[room_id] = {
            'area': area,
            'center': center,
            'characteristic_size': characteristic_size
        }

    # 遍历所有文本标签
    for text_item in text_data:
        text = text_item['text']
        pixel_point = text_item['pixel_point']
        
        # 存储所有可能的匹配及其评分
        candidates = []

        # 遍历所有房间
        for room in rooms_data:
            room_id = room['id']
            polygon = room['polygon']
            room_props = room_properties[room_id]
            
            # 计算文本到房间中心的距离
            center_distance = distance_between_points(pixel_point, room_props['center'])
            
            # 检查点是否在多边形内
            if point_in_polygon(pixel_point, polygon):
                # 内部匹配，但需要评估质量
                # 计算文本到中心的距离与房间特征尺寸的比例
                distance_ratio = center_distance / room_props['characteristic_size']
                
                # 如果文本离中心太远（相对于房间大小），可能是错误匹配
                if distance_ratio <= max_center_distance_ratio:
                    # 高质量内部匹配
                    score = 100 - (distance_ratio * 50)  # 分数范围：50-100
                else:
                    # 低质量内部匹配
                    score = 50 - (distance_ratio - max_center_distance_ratio) * 25
                
                candidates.append({
                    'room_id': room_id,
                    'match_type': 'inside',
                    'score': score,
                    'center_distance': center_distance,
                    'distance_ratio': distance_ratio,
                    'area': room_props['area']
                })
            else:
                # 计算点到多边形的距离
                distance = distance_to_polygon(pixel_point, polygon)
                
                # 只考虑距离在阈值内的附近匹配
                if distance < nearby_threshold:
                    # 附近匹配的评分，考虑距离和房间大小
                    # 小房间的附近匹配应该有更高的权重
                    size_factor = 1.0 / (1.0 + math.log10(1 + room_props['area'] / 10000))
                    distance_factor = 1.0 - (distance / nearby_threshold)
                    score = 40 + (size_factor * 30) + (distance_factor * 20)  # 分数范围：约40-90
                    
                    candidates.append({
                        'room_id': room_id,
                        'match_type': 'nearby',
                        'score': score,
                        'distance': distance,
                        'center_distance': center_distance,
                        'area': room_props['area']
                    })
        
        # 根据评分排序候选匹配
        candidates.sort(key=lambda x: x['score'], reverse=True)
        
        # 选择最佳匹配
        if candidates:
            best_candidate = candidates[0]
            best_match = best_candidate['room_id']
            match_type = best_candidate['match_type']
            
            # 记录匹配结果
            if best_match not in matches:
                matches[best_match] = []
                
            match_info = {
                'text': text,
                'pixel_point': pixel_point,
                'match_type': match_type,
                'score': best_candidate['score']
            }
            
            # 添加匹配类型特定的信息
            if match_type == 'inside':
                match_info['center_distance'] = best_candidate['center_distance']
                match_info['distance_ratio'] = best_candidate['distance_ratio']
            else:  # nearby
                match_info['distance'] = best_candidate['distance']
                match_info['center_distance'] = best_candidate['center_distance']
            
            matches[best_match].append(match_info)
        else:
            # 未找到合适的匹配
            unmatched_texts.append({
                'text': text,
                'pixel_point': pixel_point,
                'reason': 'No candidates within threshold'
            })

    # 返回匹配结果和未匹配的文本
    return {
        'matches': matches,
        'unmatched': unmatched_texts,
        'match_statistics': {
            'total_texts': len(text_data),
            'matched_texts': sum(len(texts) for texts in matches.values()),
            'unmatched_texts': len(unmatched_texts)
        }
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

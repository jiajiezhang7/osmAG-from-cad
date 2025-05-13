#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合并两张osmAG文件

此脚本用于合并两张属于同一栋楼的osmAG文件，通过识别同名的电梯和楼梯区域，(因此在执行该脚本前,你应该确保不同楼层具有同名同形的电梯或楼梯)
计算它们之间的相对位置偏差，然后整体移动待校正图，最终生成合并后的osmAG文件。

用法：
    python merge_osm.py --reference <参照OSM文件路径> --target <待校正OSM文件路径> --output <输出OSM文件路径>
"""

import argparse
import xml.etree.ElementTree as ET
import numpy as np
import json
import os
from pathlib import Path
import yaml
import copy
import statistics
from collections import defaultdict


def load_yaml_config(file_path):
    """加载YAML配置文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading YAML file {file_path}: {e}")
        return None


def load_osm_file(file_path):
    """加载OSM XML文件并返回根元素和树对象"""
    try:
        tree = ET.parse(file_path)
        return tree.getroot(), tree
    except Exception as e:
        print(f"Error loading OSM file {file_path}: {e}")
        return None, None


def save_osm_file(tree, file_path):
    """保存OSM XML文件"""
    try:
        tree.write(file_path, encoding='utf-8', xml_declaration=True)
        print(f"Successfully saved to: {file_path}")
        return True
    except Exception as e:
        print(f"Error saving OSM file {file_path}: {e}")
        return False


def find_root_node(osm_root):
    """
    查找OSM文件中的root节点
    
    参数：
        osm_root: OSM XML根元素
        
    返回：
        root节点元素，如果没有找到则返回None
    """
    for node in osm_root.findall('.//node'):
        for tag in node.findall('./tag'):
            if tag.get('k') == 'name' and tag.get('v') == 'root':
                return node
    return None

def find_matching_areas(osm_root, area_type):
    """
    查找特定类型的区域（电梯或楼梯）
    
    参数：
        osm_root: OSM XML根元素
        area_type: 区域类型，'elevator'或'stairs'
        
    返回：
        字典，键为区域名称，值为包含区域信息的字典列表
    """
    areas = defaultdict(list)
    
    # 查找所有way元素
    for way in osm_root.findall('.//way'):
        area_type_tag = None
        name_tag = None
        level_tag = None
        
        # 查找相关标签
        for tag in way.findall('./tag'):
            k = tag.get('k')
            v = tag.get('v')
            
            if k == 'osmAG:areaType' and v == area_type:
                area_type_tag = v
            elif k == 'name':
                name_tag = v
            elif k == 'level':
                level_tag = v
        
        # 如果找到了所需的所有标签
        if area_type_tag and name_tag and level_tag:
            # 收集节点引用
            nodes = []
            for nd in way.findall('./nd'):
                ref = nd.get('ref')
                nodes.append(ref)
            
            # 收集节点坐标
            coordinates = []
            for ref in nodes:
                node = osm_root.find(f".//node[@id='{ref}']")
                if node is not None:
                    lat = float(node.get('lat'))
                    lon = float(node.get('lon'))
                    coordinates.append((lat, lon))
            
            # 添加到区域字典
            areas[name_tag].append({
                'id': way.get('id'),
                'level': level_tag,
                'nodes': nodes,
                'coordinates': coordinates,
                'way_element': way
            })
    
    return areas


def calculate_centroid(coordinates):
    """
    计算多边形的质心，使用更精确的方法
    
    参数：
        coordinates: 多边形顶点坐标列表 [(lat, lon), ...]
        
    返回：
        质心坐标 (lat, lon)
    """
    if not coordinates:
        return None
    
    # 对于经纬度坐标，简单的算术平均可能更稳定
    # 特别是对于小区域（如单个房间）
    n = len(coordinates)
    lat_sum = sum(lat for lat, _ in coordinates)
    lon_sum = sum(lon for _, lon in coordinates)
    
    return (lat_sum / n, lon_sum / n)


def calculate_offset(ref_areas, target_areas):
    """
    计算参照图和待校正图之间的相对位置偏差，使用更精确的方法
    
    参数：
        ref_areas: 参照图中的区域字典
        target_areas: 待校正图中的区域字典
        
    返回：
        (lat_offset, lon_offset): 纬度和经度的偏移量
    """
    offsets = []
    offset_details = []  # 用于调试
    
    # 遍历所有同名区域
    for name, ref_list in ref_areas.items():
        if name in target_areas:
            target_list = target_areas[name]
            
            # 对每对同名区域计算偏移量
            for ref_area in ref_list:
                for target_area in target_list:
                    # 确保不是同一层
                    if ref_area['level'] != target_area['level']:
                        # 计算每个顶点的偏移量，而不仅仅是质心
                        vertex_offsets = []
                        
                        # 如果顶点数量相同，直接计算对应顶点的偏移量
                        if len(ref_area['coordinates']) == len(target_area['coordinates']):
                            for i in range(len(ref_area['coordinates'])):
                                ref_lat, ref_lon = ref_area['coordinates'][i]
                                target_lat, target_lon = target_area['coordinates'][i]
                                lat_offset = ref_lat - target_lat
                                lon_offset = ref_lon - target_lon
                                vertex_offsets.append((lat_offset, lon_offset))
                        else:
                            # 如果顶点数量不同，使用质心
                            ref_centroid = calculate_centroid(ref_area['coordinates'])
                            target_centroid = calculate_centroid(target_area['coordinates'])
                            
                            if ref_centroid and target_centroid:
                                lat_offset = ref_centroid[0] - target_centroid[0]
                                lon_offset = ref_centroid[1] - target_centroid[1]
                                vertex_offsets.append((lat_offset, lon_offset))
                        
                        if vertex_offsets:
                            # 计算这对区域的平均偏移量
                            avg_lat_offset = sum(offset[0] for offset in vertex_offsets) / len(vertex_offsets)
                            avg_lon_offset = sum(offset[1] for offset in vertex_offsets) / len(vertex_offsets)
                            offsets.append((avg_lat_offset, avg_lon_offset))
                            
                            # 保存详细信息用于调试
                            ref_centroid = calculate_centroid(ref_area['coordinates'])
                            target_centroid = calculate_centroid(target_area['coordinates'])
                            offset_details.append({
                                'name': name,
                                'ref_level': ref_area['level'],
                                'target_level': target_area['level'],
                                'ref_centroid': ref_centroid,
                                'target_centroid': target_centroid,
                                'vertex_count': len(vertex_offsets),
                                'lat_offset': avg_lat_offset,
                                'lon_offset': avg_lon_offset
                            })
    
    if not offsets:
        print("警告：没有找到匹配的区域来计算偏移量")
        return 0, 0
    
    # 打印详细的偏移信息用于调试
    print("\n详细偏移量信息：")
    for detail in offset_details:
        print(f"  区域: {detail['name']}, 参照层: {detail['ref_level']}, 目标层: {detail['target_level']}, 顶点数: {detail['vertex_count']}")
        print(f"    参照质心: ({detail['ref_centroid'][0]:.10f}, {detail['ref_centroid'][1]:.10f})")
        print(f"    目标质心: ({detail['target_centroid'][0]:.10f}, {detail['target_centroid'][1]:.10f})")
        print(f"    偏移量: 纬度={detail['lat_offset']:.10f}, 经度={detail['lon_offset']:.10f}")
    
    # 计算偏移量的标准差，用于识别异常值
    lat_offsets = [offset[0] for offset in offsets]
    lon_offsets = [offset[1] for offset in offsets]
    
    lat_mean = sum(lat_offsets) / len(lat_offsets)
    lon_mean = sum(lon_offsets) / len(lon_offsets)
    
    lat_std = (sum((x - lat_mean) ** 2 for x in lat_offsets) / len(lat_offsets)) ** 0.5
    lon_std = (sum((x - lon_mean) ** 2 for x in lon_offsets) / len(lon_offsets)) ** 0.5
    
    print(f"\n偏移量统计：")
    print(f"  纬度: 平均值={lat_mean:.10f}, 标准差={lat_std:.10f}")
    print(f"  经度: 平均值={lon_mean:.10f}, 标准差={lon_std:.10f}")
    
    # 过滤掉异常值（超过2个标准差的偏移量）
    filtered_offsets = []
    for offset in offsets:
        lat_offset, lon_offset = offset
        if (abs(lat_offset - lat_mean) < 2 * lat_std and 
            abs(lon_offset - lon_mean) < 2 * lon_std):
            filtered_offsets.append(offset)
    
    # 如果过滤后没有足够的数据，使用原始数据
    if len(filtered_offsets) < len(offsets) / 2:
        print("警告：过滤异常值后数据不足，使用原始数据")
        filtered_offsets = offsets
    else:
        print(f"过滤后保留了 {len(filtered_offsets)} 个偏移量数据（共 {len(offsets)} 个）")
    
    # 按区域类型分组并加权
    area_weights = {
        'elevator': 2.0,  # 电梯区域权重更高
        'stairs': 1.5,    # 楼梯区域权重次之
        'default': 1.0    # 默认权重
    }
    
    # 按区域名称分组
    grouped_offsets = {}
    for i, offset in enumerate(filtered_offsets):
        name = offset_details[i]['name']
        if name not in grouped_offsets:
            grouped_offsets[name] = []
        grouped_offsets[name].append(offset)
    
    # 对每个区域计算加权平均偏移量
    weighted_offsets = []
    total_weight = 0
    
    for name, area_offset_list in grouped_offsets.items():
        # 确定区域类型和权重
        area_type = 'default'
        if 'E' in name and ('S' in name or 'P' in name):  # 电梯命名规则
            area_type = 'elevator'
        elif 'ST' in name:  # 楼梯命名规则
            area_type = 'stairs'
        
        weight = area_weights.get(area_type, area_weights['default'])
        total_weight += weight
        
        # 计算该区域的平均偏移量
        avg_lat = sum(offset[0] for offset in area_offset_list) / len(area_offset_list)
        avg_lon = sum(offset[1] for offset in area_offset_list) / len(area_offset_list)
        
        weighted_offsets.append((avg_lat, avg_lon, weight))
        print(f"区域 {name} (类型: {area_type}): 权重={weight}, 偏移量=(纬度:{avg_lat:.10f}, 经度:{avg_lon:.10f})")
    
    # 计算加权平均偏移量
    final_lat_offset = sum(offset[0] * offset[2] for offset in weighted_offsets) / total_weight
    final_lon_offset = sum(offset[1] * offset[2] for offset in weighted_offsets) / total_weight
    
    print(f"\n计算得到的最终加权偏移量：纬度 {final_lat_offset:.10f}, 经度 {final_lon_offset:.10f}")
    print(f"共找到 {len(offsets)} 对匹配区域，涉及 {len(grouped_offsets)} 个不同名称的区域")
    
    return final_lat_offset, final_lon_offset


def apply_offset(osm_root, lat_offset, lon_offset):
    """
    对OSM文件中的所有节点应用偏移量，使用更高精度
    
    参数：
        osm_root: OSM XML根元素
        lat_offset: 纬度偏移量
        lon_offset: 经度偏移量
        
    返回：
        更新后的OSM根元素
    """
    # 遍历所有节点并应用偏移量
    node_count = 0
    
    # 使用更高精度的浮点数处理
    lat_offset = float(f"{lat_offset:.12f}")
    lon_offset = float(f"{lon_offset:.12f}")
    
    for node in osm_root.findall('.//node'):
        lat = float(node.get('lat'))
        lon = float(node.get('lon'))
        
        # 应用偏移量，保持高精度
        new_lat = lat + lat_offset
        new_lon = lon + lon_offset
        
        # 更新节点坐标，使用足够的小数位数保证精度
        node.set('lat', f"{new_lat:.12f}")
        node.set('lon', f"{new_lon:.12f}")
        node_count += 1
    
    print(f"已应用偏移量到 {node_count} 个节点，使用12位小数精度")
    return osm_root


def update_ids(target_root, ref_max_ids):
    """
    更新待校正图中的ID，确保与参照图中的ID不冲突
    
    参数：
        target_root: 待校正图的根元素
        ref_max_ids: 参照图中各类元素的最大ID
        
    返回：
        更新后的根元素和ID映射字典
    """
    # 创建ID映射字典
    id_mapping = {}
    
    # 更新节点ID
    for node in target_root.findall('.//node'):
        old_id = node.get('id')
        new_id = str(int(ref_max_ids['node']) + int(old_id.replace('-', ''))) if old_id.startswith('-') else old_id
        id_mapping[old_id] = new_id
        node.set('id', new_id)
    
    # 更新way ID和引用的节点ID
    for way in target_root.findall('.//way'):
        old_id = way.get('id')
        new_id = str(int(ref_max_ids['way']) + int(old_id.replace('-', ''))) if old_id.startswith('-') else old_id
        id_mapping[old_id] = new_id
        way.set('id', new_id)
        
        # 更新引用的节点ID
        for nd in way.findall('./nd'):
            old_ref = nd.get('ref')
            if old_ref in id_mapping:
                nd.set('ref', id_mapping[old_ref])
    
    # 更新relation ID和引用的成员ID
    for relation in target_root.findall('.//relation'):
        old_id = relation.get('id')
        new_id = str(int(ref_max_ids['relation']) + int(old_id.replace('-', ''))) if old_id.startswith('-') else old_id
        id_mapping[old_id] = new_id
        relation.set('id', new_id)
        
        # 更新引用的成员ID
        for member in relation.findall('./member'):
            old_ref = member.get('ref')
            if old_ref in id_mapping:
                member.set('ref', id_mapping[old_ref])
    
    return target_root, id_mapping


def find_max_ids(osm_root):
    """
    查找OSM文件中各类元素的最大ID
    
    参数：
        osm_root: OSM XML根元素
        
    返回：
        包含各类元素最大ID的字典
    """
    max_ids = {
        'node': -1,
        'way': -1,
        'relation': -1
    }
    
    # 查找最大节点ID
    for node in osm_root.findall('.//node'):
        node_id = node.get('id')
        if node_id.startswith('-'):
            node_id = int(node_id.replace('-', ''))
            max_ids['node'] = max(max_ids['node'], node_id)
    
    # 查找最大way ID
    for way in osm_root.findall('.//way'):
        way_id = way.get('id')
        if way_id.startswith('-'):
            way_id = int(way_id.replace('-', ''))
            max_ids['way'] = max(max_ids['way'], way_id)
    
    # 查找最大relation ID
    for relation in osm_root.findall('.//relation'):
        relation_id = relation.get('id')
        if relation_id.startswith('-'):
            relation_id = int(relation_id.replace('-', ''))
            max_ids['relation'] = max(max_ids['relation'], relation_id)
    
    return max_ids


def ensure_version_attribute(element, default_version='1'):
    """
    确保元素有version属性
    
    参数：
        element: XML元素
        default_version: 默认版本号
    """
    if 'version' not in element.attrib:
        element.set('version', default_version)

def merge_osm_files(ref_root, ref_tree, target_root, target_tree):
    """
    合并两个OSM文件
    
    参数：
        ref_root: 参照图的根元素
        ref_tree: 参照图的树对象
        target_root: 待校正图的根元素
        target_tree: 待校正图的树对象
        
    返回：
        合并后的树对象
    """
    # 查找参照图中的最大ID
    ref_max_ids = find_max_ids(ref_root)
    
    # 更新待校正图中的ID
    target_root, id_mapping = update_ids(target_root, ref_max_ids)
    
    # 创建合并后的树对象（深拷贝参照图）
    merged_tree = copy.deepcopy(ref_tree)
    merged_root = merged_tree.getroot()
    
    # 确保参照图中的所有元素都有version属性
    for node in merged_root.findall('.//node'):
        ensure_version_attribute(node)
    for way in merged_root.findall('.//way'):
        ensure_version_attribute(way)
    for relation in merged_root.findall('.//relation'):
        ensure_version_attribute(relation)
    
    # 查找待校正图中的root节点，以便在合并时排除
    target_root_node = find_root_node(target_root)
    target_root_node_id = target_root_node.get('id') if target_root_node is not None else None
    
    if target_root_node is not None:
        print(f"找到待校正图中的root节点，ID: {target_root_node_id}，将在合并时排除")
    
    # 将待校正图中的节点添加到合并后的树中，并确保有version属性，但排除root节点
    for node in target_root.findall('.//node'):
        # 跳过root节点
        if target_root_node is not None and node.get('id') == target_root_node_id:
            continue
            
        ensure_version_attribute(node)
        merged_root.append(copy.deepcopy(node))
    
    # 将待校正图中的way添加到合并后的树中，并确保有version属性
    for way in target_root.findall('.//way'):
        ensure_version_attribute(way)
        merged_root.append(copy.deepcopy(way))
    
    # 将待校正图中的relation添加到合并后的树中，并确保有version属性
    for relation in target_root.findall('.//relation'):
        ensure_version_attribute(relation)
        merged_root.append(copy.deepcopy(relation))
    
    return merged_tree


def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='合并两张osmAG文件')
    parser.add_argument('--reference', required=True, help='参照OSM文件路径')
    parser.add_argument('--target', required=True, help='待校正OSM文件路径')
    parser.add_argument('--output', required=True, help='输出OSM文件路径')
    parser.add_argument('--config', default=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config', 'params.yaml'), help='配置文件路径')
    parser.add_argument('--debug', action='store_true', help='启用调试模式，输出更多信息')
    parser.add_argument('--precision', type=int, default=12, help='坐标精度（小数位数）')
    parser.add_argument('--elevator-weight', type=float, default=2.0, help='电梯区域权重')
    parser.add_argument('--stairs-weight', type=float, default=1.5, help='楼梯区域权重')
    parser.add_argument('--keep-target-root', action='store_true', help='保留待校正图中的root节点（默认删除）')
    args = parser.parse_args()
    
    # 加载配置文件
    config_path = Path(args.config)
    config = load_yaml_config(config_path)
    
    # 加载OSM文件
    ref_root, ref_tree = load_osm_file(args.reference)
    target_root, target_tree = load_osm_file(args.target)
    
    if ref_root is None or target_root is None:
        print("错误：无法加载OSM文件")
        return
        
    # 查找参照图和待校正图中的root节点
    ref_root_node = find_root_node(ref_root)
    target_root_node = find_root_node(target_root)
    
    if ref_root_node is not None:
        print(f"找到参照图中的root节点，ID: {ref_root_node.get('id')}")
    else:
        print("警告：参照图中没有找到root节点")
        
    if target_root_node is not None:
        print(f"找到待校正图中的root节点，ID: {target_root_node.get('id')}")
    else:
        print("警告：待校正图中没有找到root节点")
    
    # 查找电梯区域
    ref_elevators = find_matching_areas(ref_root, 'elevator')
    target_elevators = find_matching_areas(target_root, 'elevator')
    
    # 查找楼梯区域
    ref_stairs = find_matching_areas(ref_root, 'stairs')
    target_stairs = find_matching_areas(target_root, 'stairs')
    
    # 合并区域字典
    ref_areas = defaultdict(list)
    target_areas = defaultdict(list)
    
    for name, areas in ref_elevators.items():
        ref_areas[name].extend(areas)
    for name, areas in ref_stairs.items():
        ref_areas[name].extend(areas)
    
    for name, areas in target_elevators.items():
        target_areas[name].extend(areas)
    for name, areas in target_stairs.items():
        target_areas[name].extend(areas)
    
    # 计算偏移量
    lat_offset, lon_offset = calculate_offset(ref_areas, target_areas)
    
    # 应用偏移量
    target_root = apply_offset(target_root, lat_offset, lon_offset)
    
    # 合并OSM文件
    merged_tree = merge_osm_files(ref_root, ref_tree, target_root, target_tree)
    
    # 保存合并后的OSM文件
    save_osm_file(merged_tree, args.output)
    
    print(f"成功合并OSM文件并保存到: {args.output}")


if __name__ == "__main__":
    main()
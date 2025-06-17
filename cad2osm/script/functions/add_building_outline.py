#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为osmAG.xml文件添加建筑外轮廓

此脚本读取osmAG.xml文件，计算所有房间的外轮廓，并添加一个包含外轮廓的way，
该way具有building=Architecture标签。

用法:
    python add_building_outline.py --input <input.osm> --output <output.osm>

参数:
    --input: 输入的osmAG.xml文件路径
    --output: 输出的OSM文件路径
"""

import argparse
import xml.etree.ElementTree as ET
import numpy as np
from scipy.spatial import ConvexHull
from shapely.geometry import Polygon, Point, MultiPolygon
from shapely.ops import unary_union
import sys
import os


def load_osm_file(file_path):
    """加载OSM XML文件并返回根元素和树对象"""
    try:
        tree = ET.parse(file_path)
        return tree.getroot(), tree
    except Exception as e:
        print(f"加载OSM文件出错 {file_path}: {e}")
        return None, None


def save_osm_file(tree, file_path):
    """保存OSM XML文件"""
    try:
        tree.write(file_path, encoding='utf-8', xml_declaration=True)
        print(f"成功保存到: {file_path}")
        return True
    except Exception as e:
        print(f"保存OSM文件出错 {file_path}: {e}")
        return False


def get_room_polygons(osm_root):
    """
    从OSM文件中提取所有房间的多边形
    
    参数:
        osm_root: OSM XML根元素
        
    返回:
        房间多边形列表，每个多边形是(lat, lon)坐标点的列表
    """
    # 构建节点ID到坐标的映射
    node_map = {}
    for node in osm_root.findall('.//node'):
        node_id = node.get('id')
        lat = float(node.get('lat'))
        lon = float(node.get('lon'))
        node_map[node_id] = (lat, lon)
    
    room_polygons = []
    
    # 查找所有房间way
    for way in osm_root.findall('.//way'):
        is_room = False
        
        # 检查是否是房间
        for tag in way.findall('./tag'):
            k = tag.get('k')
            v = tag.get('v')
            
            if k == 'osmAG:areaType' and v == 'room':
                is_room = True
                break
        
        if not is_room:
            continue
        
        # 获取房间的节点坐标
        room_coords = []
        for nd in way.findall('./nd'):
            node_ref = nd.get('ref')
            if node_ref in node_map:
                lat, lon = node_map[node_ref]
                room_coords.append((lat, lon))
        
        # 确保多边形是闭合的
        if len(room_coords) >= 3:
            if room_coords[0] != room_coords[-1]:
                room_coords.append(room_coords[0])
            room_polygons.append(room_coords)
    
    return room_polygons


def calculate_building_outline(room_polygons, method='boundary'):
    """
    计算建筑外轮廓 - 获取所有房间的真实外边界
    
    参数:
        room_polygons: 房间多边形列表
        method: 计算方法，'boundary'（联合边界）、'convex_hull'（凸包）或 'alpha_shape'（Alpha形状）
        
    返回:
        外轮廓坐标点列表 [(lat, lon), ...]
    """
    if not room_polygons:
        return []
    
    try:
        # 创建有效的Shapely多边形
        valid_polygons = []
        for room_coords in room_polygons:
            if len(room_coords) >= 4:  # 至少需要3个不同点+1个闭合点
                try:
                    # 移除重复的闭合点
                    coords = room_coords[:-1] if room_coords[0] == room_coords[-1] else room_coords
                    
                    # 创建多边形
                    poly = Polygon(coords)
                    
                    # 如果多边形无效，尝试修复
                    if not poly.is_valid:
                        poly = poly.buffer(0)  # 尝试修复无效几何
                    
                    if poly.is_valid and poly.area > 0:
                        valid_polygons.append(poly)
                        
                except Exception as e:
                    print(f"创建多边形时出错: {e}")
                    continue
        
        if not valid_polygons:
            print("没有找到有效的房间多边形")
            return []
        
        print(f"找到 {len(valid_polygons)} 个有效房间多边形")
        
        if method == 'boundary':
            # 计算所有房间多边形的联合
            print("正在计算房间多边形的联合...")
            union_geom = unary_union(valid_polygons)
            
            # 获取外边界
            if isinstance(union_geom, Polygon):
                exterior_coords = list(union_geom.exterior.coords)
                print(f"获得单个多边形外边界，包含 {len(exterior_coords)} 个顶点")
                
            elif isinstance(union_geom, MultiPolygon):
                # 如果是多个不连通的多边形，选择面积最大的
                largest_poly = max(union_geom.geoms, key=lambda p: p.area)
                exterior_coords = list(largest_poly.exterior.coords)
                print(f"从多个多边形中选择最大的，外边界包含 {len(exterior_coords)} 个顶点")
                
            else:
                print(f"意外的几何类型: {type(union_geom)}")
                return []
            
            # 确保顺序正确（逆时针）
            exterior_coords = ensure_counterclockwise(exterior_coords)
            
            return exterior_coords
            
        elif method == 'convex_hull':
            # 凸包方法（作为备选）
            all_points = []
            for poly in valid_polygons:
                coords = list(poly.exterior.coords[:-1])  # 排除重复的闭合点
                all_points.extend(coords)
            
            if len(all_points) < 3:
                return []
            
            points_array = np.array(all_points)
            hull = ConvexHull(points_array)
            hull_points = points_array[hull.vertices]
            hull_coords = [(float(pt[0]), float(pt[1])) for pt in hull_points]
            hull_coords = ensure_counterclockwise(hull_coords)
            hull_coords.append(hull_coords[0])  # 闭合多边形
            
            return hull_coords
            
        elif method == 'alpha_shape':
            # Alpha形状 - 如果需要更精确的凹包
            try:
                from alphashape import alphashape
                all_points = []
                for poly in valid_polygons:
                    coords = list(poly.exterior.coords[:-1])
                    all_points.extend(coords)
                
                if len(all_points) < 3:
                    return []
                
                # 计算alpha形状
                alpha_shape = alphashape(all_points, alpha=0.1)
                
                if isinstance(alpha_shape, Polygon):
                    exterior_coords = list(alpha_shape.exterior.coords)
                    exterior_coords = ensure_counterclockwise(exterior_coords)
                    return exterior_coords
                else:
                    # 如果alpha形状失败，回退到边界方法
                    return calculate_building_outline(room_polygons, method='boundary')
                    
            except ImportError:
                print("alphashape库未安装，使用边界方法")
                return calculate_building_outline(room_polygons, method='boundary')
            except Exception as e:
                print(f"计算alpha形状时出错: {e}，使用边界方法")
                return calculate_building_outline(room_polygons, method='boundary')
    
    except Exception as e:
        print(f"计算建筑外轮廓时出错: {e}")
        return []


def ensure_counterclockwise(coords):
    """
    确保多边形顶点按逆时针顺序排列（OSM标准）
    """
    if len(coords) < 3:
        return coords
    
    # 计算有向面积
    area = 0
    n = len(coords)
    for i in range(n):
        j = (i + 1) % n
        area += coords[i][0] * coords[j][1]
        area -= coords[j][0] * coords[i][1]
    
    # 如果面积为负，说明是顺时针，需要反转
    if area < 0:
        coords = coords[::-1]
    
    return coords


def get_next_id(osm_root, element_type='way'):
    """
    获取下一个可用的ID
    
    参数:
        osm_root: OSM XML根元素
        element_type: 元素类型 ('node' 或 'way')
        
    返回:
        下一个可用的负数ID（字符串）
    """
    existing_ids = set()
    
    for element in osm_root.findall(f'.//{element_type}'):
        element_id = element.get('id')
        if element_id:
            try:
                existing_ids.add(int(element_id))
            except ValueError:
                pass
    
    # 找到最小的负数ID，然后减1
    min_id = min(existing_ids) if existing_ids else 0
    return str(min_id - 1)


def add_building_outline_to_osm(osm_root, outline_coords):
    """
    向OSM文件添加建筑外轮廓
    
    参数:
        osm_root: OSM XML根元素
        outline_coords: 外轮廓坐标点列表 [(lat, lon), ...]
        
    返回:
        成功返回True，失败返回False
    """
    if not outline_coords or len(outline_coords) < 4:
        print("外轮廓坐标不足，无法创建建筑轮廓")
        return False
    
    try:
        # 为外轮廓的每个点创建节点
        node_refs = []
        
        for lat, lon in outline_coords:
            node_id = get_next_id(osm_root, 'node')
            
            # 创建节点元素
            node_elem = ET.Element('node')
            node_elem.set('id', node_id)
            node_elem.set('action', 'modify')
            node_elem.set('visible', 'true')
            node_elem.set('lat', f'{lat:.11f}')
            node_elem.set('lon', f'{lon:.11f}')
            
            # 添加到OSM根元素
            osm_root.append(node_elem)
            node_refs.append(node_id)
        
        # 创建建筑轮廓way
        way_id = get_next_id(osm_root, 'way')
        way_elem = ET.Element('way')
        way_elem.set('id', way_id)
        way_elem.set('action', 'modify')
        way_elem.set('visible', 'true')
        
        # 添加节点引用
        for node_ref in node_refs:
            nd_elem = ET.SubElement(way_elem, 'nd')
            nd_elem.set('ref', node_ref)
        
        # 添加标签
        building_tag = ET.SubElement(way_elem, 'tag')
        building_tag.set('k', 'building')
        building_tag.set('v', 'Architecture')
        
        # 添加其他有用的标签
        outline_tag = ET.SubElement(way_elem, 'tag')
        outline_tag.set('k', 'name')
        outline_tag.set('v', 'Building Outline')
        
        type_tag = ET.SubElement(way_elem, 'tag')
        type_tag.set('k', 'osmAG:type')
        type_tag.set('v', 'building_outline')
        
        # 添加到OSM根元素
        osm_root.append(way_elem)
        
        print(f"成功添加建筑外轮廓，包含 {len(outline_coords)} 个节点")
        return True
        
    except Exception as e:
        print(f"添加建筑外轮廓时出错: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='为osmAG.xml文件添加建筑外轮廓')
    parser.add_argument('--input', '-i', required=True, help='输入的osmAG.xml文件路径')
    parser.add_argument('--output', '-o', required=True, help='输出的OSM文件路径')
    parser.add_argument('--method', '-m', choices=['boundary', 'convex_hull', 'alpha_shape'], 
                       default='boundary', help='轮廓计算方法：联合边界(boundary)、凸包(convex_hull)或Alpha形状(alpha_shape)')
    
    args = parser.parse_args()
    
    # 检查输入文件是否存在
    if not os.path.exists(args.input):
        print(f"错误：输入文件不存在: {args.input}")
        sys.exit(1)
    
    # 加载OSM文件
    print(f"正在加载OSM文件: {args.input}")
    osm_root, osm_tree = load_osm_file(args.input)
    
    if osm_root is None:
        print("加载OSM文件失败")
        sys.exit(1)
    
    # 提取房间多边形
    print("正在提取房间多边形...")
    room_polygons = get_room_polygons(osm_root)
    
    if not room_polygons:
        print("警告：未找到任何房间，无法计算建筑外轮廓")
        sys.exit(1)
    
    print(f"找到 {len(room_polygons)} 个房间")
    
    # 计算建筑外轮廓
    print(f"正在使用 {args.method} 方法计算建筑外轮廓...")
    outline_coords = calculate_building_outline(room_polygons, method=args.method)
    
    if not outline_coords:
        print("计算建筑外轮廓失败")
        sys.exit(1)
    
    print(f"计算得到外轮廓，包含 {len(outline_coords)} 个顶点")
    
    # 添加建筑外轮廓到OSM文件
    print("正在添加建筑外轮廓到OSM文件...")
    success = add_building_outline_to_osm(osm_root, outline_coords)
    
    if not success:
        print("添加建筑外轮廓失败")
        sys.exit(1)
    
    # 保存修改后的OSM文件
    print(f"正在保存文件到: {args.output}")
    if save_osm_file(osm_tree, args.output):
        print("操作完成！")
    else:
        print("保存文件失败")
        sys.exit(1)


if __name__ == '__main__':
    main() 
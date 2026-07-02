#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
为osmAG.xml文件添加楼层外轮廓

此脚本读取osmAG.xml文件，计算指定楼层所有房间的外轮廓，并添加一个包含外轮廓的way，
该way具有楼层相关的标签。

用法:
    python add_level_parent.py --input <input.osm> --output <output.osm> --level <level_number>

参数:
    --input: 输入的osmAG.xml文件路径
    --output: 输出的OSM文件路径
    --level: 楼层编号（默认为2）
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


def indent_xml(elem, level=0):
    """为XML元素添加缩进和换行"""
    indent_str = "  "  # 2个空格缩进
    i = "\n" + level * indent_str
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + indent_str
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for child in elem:
            indent_xml(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i


def save_osm_file(tree, file_path):
    """保存OSM XML文件"""
    try:
        # 格式化XML
        root = tree.getroot()
        indent_xml(root)

        tree.write(file_path, encoding='utf-8', xml_declaration=True)
        print(f"成功保存到: {file_path}")
        return True
    except Exception as e:
        print(f"保存OSM文件出错 {file_path}: {e}")
        return False


def get_room_polygons_by_level(osm_root, level):
    """
    从OSM文件中提取指定楼层所有房间的多边形

    参数:
        osm_root: OSM XML根元素
        level: 楼层编号

    返回:
        元组 (room_polygons, room_ids):
        - room_polygons: 房间多边形列表，每个多边形是(lat, lon)坐标点的列表
        - room_ids: 对应的房间way ID列表
    """
    # 构建节点ID到坐标的映射
    node_map = {}
    for node in osm_root.findall('.//node'):
        node_id = node.get('id')
        lat = float(node.get('lat'))
        lon = float(node.get('lon'))
        node_map[node_id] = (lat, lon)

    room_polygons = []
    room_ids = []

    # 查找指定楼层的所有房间way
    for way in osm_root.findall('.//way'):
        is_room = False
        has_level_tag = False
        is_target_level = False

        # 检查是否是房间且在指定楼层
        for tag in way.findall('./tag'):
            k = tag.get('k')
            v = tag.get('v')

            if k == 'osmAG:areaType' and v == 'room':
                is_room = True

            if k == 'level':
                has_level_tag = True
                if v == str(level):
                    is_target_level = True

        # 如果是房间，且（没有level标签 或 level标签匹配），则处理
        if not is_room:
            continue
        if has_level_tag and not is_target_level:
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
            room_ids.append(way.get('id'))

    return room_polygons, room_ids


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


def add_parent_tags_to_rooms(osm_root, room_ids, level_outline_name, level):
    """
    为房间添加osmAG:parent标签，指向楼层外轮廓
    同时为没有level标签的房间添加level标签

    参数:
        osm_root: OSM XML根元素
        room_ids: 房间way ID列表
        level_outline_name: 楼层外轮廓的name值
        level: 楼层编号

    返回:
        成功添加标签的房间数量
    """
    if not room_ids or not level_outline_name:
        print("房间ID列表或楼层轮廓name为空，无法添加父子关系")
        return 0

    success_count = 0
    added_level_count = 0

    try:
        # 遍历所有way元素
        for way in osm_root.findall('.//way'):
            way_id = way.get('id')

            # 检查是否是需要添加标签的房间
            if way_id not in room_ids:
                continue

            # 检查是否已经有osmAG:parent标签和level标签
            has_parent_tag = False
            has_level_tag = False

            for tag in way.findall('./tag'):
                if tag.get('k') == 'osmAG:parent':
                    # 更新现有标签
                    tag.set('v', level_outline_name)
                    has_parent_tag = True
                elif tag.get('k') == 'level':
                    has_level_tag = True

            # 如果没有osmAG:parent标签，添加新标签
            if not has_parent_tag:
                parent_tag = ET.SubElement(way, 'tag')
                parent_tag.set('k', 'osmAG:parent')
                parent_tag.set('v', level_outline_name)

            # 如果没有level标签，根据parent的level添加
            if not has_level_tag:
                level_tag = ET.SubElement(way, 'tag')
                level_tag.set('k', 'level')
                level_tag.set('v', str(level))
                added_level_count += 1

            success_count += 1

        print(f"成功为 {success_count} 个房间添加 osmAG:parent 标签")
        if added_level_count > 0:
            print(f"为 {added_level_count} 个房间添加了 level 标签")
        return success_count

    except Exception as e:
        print(f"添加父子关系标签时出错: {e}")
        return success_count


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


def add_level_outline_to_osm(osm_root, outline_coords, level):
    """
    向OSM文件添加楼层外轮廓

    参数:
        osm_root: OSM XML根元素
        outline_coords: 外轮廓坐标点列表 [(lat, lon), ...]
        level: 楼层编号

    返回:
        成功返回楼层轮廓的name（字符串），失败返回None
    """
    if not outline_coords or len(outline_coords) < 4:
        print("外轮廓坐标不足，无法创建楼层轮廓")
        return None

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

        # 创建楼层轮廓way
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
        # height = 3.2 * level
        height_value = 3.2 * level
        height_tag = ET.SubElement(way_elem, 'tag')
        height_tag.set('k', 'height')
        height_tag.set('v', str(height_value))

        # indoor = room
        indoor_tag = ET.SubElement(way_elem, 'tag')
        indoor_tag.set('k', 'indoor')
        indoor_tag.set('v', 'room')

        # level = *
        level_tag = ET.SubElement(way_elem, 'tag')
        level_tag.set('k', 'level')
        level_tag.set('v', str(level))

        # name = F*
        level_name = f'F{level}'
        name_tag = ET.SubElement(way_elem, 'tag')
        name_tag.set('k', 'name')
        name_tag.set('v', level_name)

        # osmAG:areaType = structure
        area_type_tag = ET.SubElement(way_elem, 'tag')
        area_type_tag.set('k', 'osmAG:areaType')
        area_type_tag.set('v', 'structure')

        # osmAG:type = area
        type_tag = ET.SubElement(way_elem, 'tag')
        type_tag.set('k', 'osmAG:type')
        type_tag.set('v', 'area')

        # 添加到OSM根元素
        osm_root.append(way_elem)

        print(f"成功添加楼层外轮廓，包含 {len(outline_coords)} 个节点，ID: {way_id}, Name: {level_name}")
        return level_name

    except Exception as e:
        print(f"添加楼层外轮廓时出错: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(description='为osmAG.xml文件添加楼层外轮廓')
    parser.add_argument('--input', '-i', required=True, help='输入的osmAG.xml文件路径')
    parser.add_argument('--output', '-o', required=True, help='输出的OSM文件路径')
    parser.add_argument('--level', '-l', type=int, default=2, help='楼层编号（默认为2）')
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

    # 提取指定楼层的房间多边形
    print(f"正在提取楼层 {args.level} 的房间多边形...")
    room_polygons, room_ids = get_room_polygons_by_level(osm_root, args.level)

    if not room_polygons:
        print(f"警告：未找到楼层 {args.level} 的任何房间，无法计算楼层外轮廓")
        sys.exit(1)

    print(f"找到 {len(room_polygons)} 个房间")

    # 计算楼层外轮廓
    print(f"正在使用 {args.method} 方法计算楼层外轮廓...")
    outline_coords = calculate_building_outline(room_polygons, method=args.method)

    if not outline_coords:
        print("计算楼层外轮廓失败")
        sys.exit(1)

    print(f"计算得到外轮廓，包含 {len(outline_coords)} 个顶点")

    # 添加楼层外轮廓到OSM文件
    print("正在添加楼层外轮廓到OSM文件...")
    level_outline_name = add_level_outline_to_osm(osm_root, outline_coords, args.level)

    if not level_outline_name:
        print("添加楼层外轮廓失败")
        sys.exit(1)

    # 为房间添加父子关系标签
    print("正在为房间添加 osmAG:parent 标签...")
    tagged_count = add_parent_tags_to_rooms(osm_root, room_ids, level_outline_name, args.level)

    if tagged_count == 0:
        print("警告：未能为任何房间添加父子关系标签")
    else:
        print(f"已为 {tagged_count}/{len(room_ids)} 个房间建立父子关系")

    # 保存修改后的OSM文件
    print(f"正在保存文件到: {args.output}")
    if save_osm_file(osm_tree, args.output):
        print("操作完成！")
    else:
        print("保存文件失败")
        sys.exit(1)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从osmAG.osm文件中提取房间多边形

此脚本读取AreaGraph生成的osmAG.osm文件，提取其中的房间多边形信息，
并将其转换为简单的JSON格式，便于后续处理。

用法:
    python extract_room_polygons.py --input-osm <osmAG.osm> --output-json <rooms.json> [--config <params.yaml>]

参数:
    --input-osm: AreaGraph生成的osmAG.osm文件路径
    --output-json: 输出的房间多边形JSON文件路径
    --config: 配置文件路径，用于获取root_node坐标和分辨率信息
"""

import json
import argparse
import os
import xml.etree.ElementTree as ET
import yaml
import numpy as np


def load_osm_file(file_path):
    """加载OSM XML文件"""
    try:
        tree = ET.parse(file_path)
        return tree.getroot()
    except Exception as e:
        print(f"Error loading OSM file {file_path}: {e}")
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


def load_yaml_config(file_path):
    """加载YAML配置文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading YAML file {file_path}: {e}")
        return None


def latlon_to_pixel(lat, lon, root_lat, root_lon, root_pixel_x, root_pixel_y, resolution):
    """
    将经纬度坐标转换为像素坐标（GeometryUtils::cartesianToLatLon的逆向操作）

    参数:
        lat, lon: 经纬度坐标
        root_lat, root_lon: root_node的经纬度坐标
        root_pixel_x, root_pixel_y: root_node在PNG中的像素位置
        resolution: 分辨率（米/像素）

    返回:
        (pixel_x, pixel_y): 像素坐标
    """
    # 实现基于WGS84toCartesian.h的经纬度到笛卡尔坐标的转换
    # 定义常量
    DEG_TO_RAD = 17.45329252e-3  # 角度转弧度的因子（等于π/180）
    EQUATOR_RADIUS = 6378137.0  # 地球赤道半径（米）
    SQUARED_ECCENTRICITY = 6.69437999e-3  # 偏心率的平方

    # 将经纬度转换为弧度
    lat_rad = lat * DEG_TO_RAD
    lon_rad = lon * DEG_TO_RAD
    ref_lat_rad = root_lat * DEG_TO_RAD
    ref_lon_rad = root_lon * DEG_TO_RAD

    # 定义常数（与WGS84toCartesian.h中相同）
    C00 = 1.0
    C02 = 0.25
    C04 = 0.046875
    C06 = 0.01953125
    C08 = 0.01068115234375
    C22 = 0.75
    C44 = 0.46875
    C46 = 0.01302083333333333333
    C48 = 0.00712076822916666666
    C66 = 0.36458333333333333333
    C68 = 0.00569661458333333333
    C88 = 0.3076171875

    # 计算R系数
    R0 = C00 - SQUARED_ECCENTRICITY * (C02 + SQUARED_ECCENTRICITY * (C04 + SQUARED_ECCENTRICITY * (C06 + SQUARED_ECCENTRICITY * C08)))
    R1 = SQUARED_ECCENTRICITY * (C22 - SQUARED_ECCENTRICITY * (C04 + SQUARED_ECCENTRICITY * (C06 + SQUARED_ECCENTRICITY * C08)))
    R2T = SQUARED_ECCENTRICITY * SQUARED_ECCENTRICITY
    R2 = R2T * (C44 - SQUARED_ECCENTRICITY * (C46 + SQUARED_ECCENTRICITY * C48))
    R3T = R2T * SQUARED_ECCENTRICITY
    R3 = R3T * (C66 - SQUARED_ECCENTRICITY * C68)
    R4 = R3T * SQUARED_ECCENTRICITY * C88

    # 定义mlfn函数（与WGS84toCartesian.h中相同）
    def mlfn(lat):
        sin_phi = np.sin(lat)
        cos_phi = np.cos(lat) * sin_phi
        squared_sin_phi = sin_phi * sin_phi
        return (R0 * lat - cos_phi * (R1 + squared_sin_phi * (R2 + squared_sin_phi * (R3 + squared_sin_phi * R4))))

    # 计算ML0
    ML0 = mlfn(ref_lat_rad)

    # 定义msfn函数
    def msfn(sin_phi, cos_phi, es):
        return cos_phi / np.sqrt(1.0 - es * sin_phi * sin_phi)

    # 定义project函数
    def project(lat, lon):
        EPSILON10 = 1.0e-10
        if abs(lat) < EPSILON10:
            return [lon, -1.0 * ML0]

        sin_lat = np.sin(lat)
        if abs(sin_lat) > EPSILON10:
            ms = msfn(sin_lat, np.cos(lat), SQUARED_ECCENTRICITY) / sin_lat
        else:
            ms = 0.0

        lon_sin_lat = lon * sin_lat
        x = ms * np.sin(lon_sin_lat)
        y = (mlfn(lat) - ML0) + ms * (1.0 - np.cos(lon_sin_lat))
        return [x, y]

    # 定义fwd函数
    def fwd(lat, lon):
        HALF_PI = 1.570796327
        EPSILON12 = 1.0e-12

        D = abs(lat) - HALF_PI
        if (D > EPSILON12) or (abs(lon) > 10.0):
            return [0.0, 0.0]

        if abs(D) < EPSILON12:
            lat = -HALF_PI if lat < 0.0 else HALF_PI

        lon = lon - ref_lon_rad
        projected = project(lat, lon)
        return [EQUATOR_RADIUS * projected[0], EQUATOR_RADIUS * projected[1]]

    # 计算笛卡尔坐标（米）
    cartesian = fwd(lat_rad, lon_rad)

    # 将米转换为像素
    # 注意：在GeometryUtils::cartesianToLatLon中，y轴被翻转了，这里需要反向操作
    pixel_x = root_pixel_x + (cartesian[0] / resolution)
    pixel_y = root_pixel_y - (cartesian[1] / resolution)  # 注意这里是减法，因为y轴方向相反

    return pixel_x, pixel_y


def extract_room_polygons(osm_root, config=None):
    """
    从OSM XML中提取房间多边形

    参数:
        osm_root: OSM XML根元素
        config: 配置信息，包含root_node坐标和分辨率

    返回:
        包含房间多边形的列表
    """
    # 设置默认的坐标转换参数
    root_lat = 31.17947960435
    root_lon = 121.59139728509
    root_pixel_x = 3804.0
    root_pixel_y = 2801.0
    resolution = 0.044

    # 如果提供了配置文件，从配置文件中读取参数
    if config:
        if 'root_node' in config:
            root_lat = config['root_node'].get('latitude', root_lat)
            root_lon = config['root_node'].get('longitude', root_lon)
            root_pixel_x = config['root_node'].get('pixel_x', root_pixel_x)
            root_pixel_y = config['root_node'].get('pixel_y', root_pixel_y)

        if 'png_dimensions' in config and 'resolution' in config['png_dimensions']:
            resolution = config['png_dimensions'].get('resolution', resolution)

    print(f"Using coordinate conversion parameters:")
    print(f"  root_lat: {root_lat}, root_lon: {root_lon}")
    print(f"  root_pixel_x: {root_pixel_x}, root_pixel_y: {root_pixel_y}")
    print(f"  resolution: {resolution} meters/pixel")

    # 存储所有节点的坐标
    nodes = {}
    for node in osm_root.findall(".//node"):
        node_id = node.get('id')
        lat = float(node.get('lat'))
        lon = float(node.get('lon'))
        nodes[node_id] = (lat, lon)

    # 存储所有房间信息
    rooms = []

    # 查找所有way元素
    for way in osm_root.findall(".//way"):
        way_id = way.get('id')

        # 检查是否是房间
        is_room = False
        room_name = None
        room_type = None

        for tag in way.findall("./tag"):
            k = tag.get('k')
            v = tag.get('v')

            if k == 'indoor' and v == 'room':
                is_room = True
            elif k == 'name':
                room_name = v
            elif k == 'room':
                room_type = v

        if not is_room:
            continue

        # 收集房间的节点引用
        node_refs = []
        for nd in way.findall("./nd"):
            node_refs.append(nd.get('ref'))

        # 收集多边形顶点并转换为像素坐标
        polygon = []
        latlon_polygon = []  # 保存原始经纬度坐标

        for node_ref in node_refs:
            if node_ref in nodes:
                lat, lon = nodes[node_ref]
                # 保存原始经纬度坐标
                latlon_polygon.append([lat, lon])

                # 将经纬度转换为像素坐标
                pixel_x, pixel_y = latlon_to_pixel(
                    lat, lon, root_lat, root_lon,
                    root_pixel_x, root_pixel_y, resolution
                )

                polygon.append([pixel_x, pixel_y])

        # 添加房间信息
        rooms.append({
            'id': way_id,
            'name': room_name,
            'type': room_type,
            'polygon': polygon,
            'latlon_polygon': latlon_polygon  # 保存原始经纬度坐标以便参考
        })

    return rooms


def main():
    parser = argparse.ArgumentParser(description='Extract room polygons from osmAG.osm file.')
    parser.add_argument('--input-osm', type=str, required=True,
                        help='Path to the input osmAG.osm file')
    parser.add_argument('--output-json', type=str, required=True,
                        help='Path to save the output room polygons JSON file')
    parser.add_argument('--config', type=str, default=None,
                        help='Path to the configuration file (params.yaml)')

    args = parser.parse_args()

    # 检查输入文件是否存在
    if not os.path.isfile(args.input_osm):
        print(f"Error: OSM file not found: {args.input_osm}")
        return

    # 创建输出目录（如果不存在）
    output_dir = os.path.dirname(args.output_json)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # 首先尝试加载默认的area_graph_segment/config/params.yaml配置文件
    config = None
    default_config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                                     'area_graph_segment', 'config', 'params.yaml')

    if os.path.isfile(default_config_path):
        config = load_yaml_config(default_config_path)
        if config is not None:
            print(f"Loaded default config from: {default_config_path}")

    # 如果提供了自定义配置文件，则使用自定义配置
    if args.config and os.path.isfile(args.config):
        custom_config = load_yaml_config(args.config)
        if custom_config is not None:
            config = custom_config  # 完全替换默认配置
            print(f"Loaded custom config from: {args.config}")
        else:
            print(f"Warning: Failed to load custom config file {args.config}.")
            if config is None:
                print("No valid configuration found. Using hardcoded default parameters.")
    elif config is None:
        print(f"Warning: Default config file not found at {default_config_path}. Using hardcoded default parameters.")

    # 加载OSM文件
    osm_root = load_osm_file(args.input_osm)

    if osm_root is None:
        print("Error: Failed to load OSM file.")
        return

    # 提取房间多边形
    rooms = extract_room_polygons(osm_root, config)

    # 保存结果
    success = save_json_file(rooms, args.output_json)

    if success:
        print(f"Successfully extracted {len(rooms)} room polygons.")
        print(f"Each room contains both pixel coordinates ('polygon') and original lat/lon coordinates ('latlon_polygon').")


if __name__ == "__main__":
    main()

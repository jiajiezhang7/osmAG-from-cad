#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DXF文本坐标到像素坐标转换脚本

此脚本读取extract_dxf_text.py生成的JSON文件和对应的.bounds.json文件，
将DXF文本坐标转换为PNG像素坐标，便于与AreaGraph处理的房间坐标进行匹配。

用法:
    python dxf_text_to_pixel.py --input-json <extracted_text.json> --bounds-json <file.bounds.json> --output-json <output.json>

参数:
    --input-json: extract_dxf_text.py生成的文本JSON文件路径
    --bounds-json: dxf2svg.py生成的边界信息JSON文件路径
    --output-json: 输出的像素坐标JSON文件路径
"""

import json
import argparse
import os
from pathlib import Path
import yaml


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


def dxf_to_pixel_coordinates(dxf_x, dxf_y, bounds_data):
    """
    将DXF坐标转换为像素坐标
    
    参数:
        dxf_x, dxf_y: DXF坐标
        bounds_data: 边界信息数据
        
    返回:
        (pixel_x, pixel_y): 像素坐标
    """
    # 提取边界信息（已包含边缘空隙）
    min_x = bounds_data['min_x_padded']  # 带有边缘空隙的最小X坐标
    min_y = bounds_data['min_y_padded']  # 带有边缘空隙的最小Y坐标
    max_x = bounds_data['max_x_padded']  # 带有边缘空隙的最大X坐标
    max_y = bounds_data['max_y_padded']  # 带有边缘空隙的最大Y坐标
    svg_width = bounds_data['svg_width_px']
    svg_height = bounds_data['svg_height_px']
    
    # 获取原始边界（不带边缘空隙）用于计算边缘空隙比例
    if 'min_x' in bounds_data and 'max_x' in bounds_data:
        original_width = bounds_data['max_x'] - bounds_data['min_x']
        padded_width = max_x - min_x
        padding_ratio = (padded_width - original_width) / (2 * original_width) if original_width > 0 else 0
        # 确保与extract_room_polygons.py和dxf2svg.py使用相同的边缘空隙比例
        # 通常为0.03（3%）
    
    # 计算缩放因子
    width = max_x - min_x
    height = max_y - min_y
    
    if width > height:
        scale = svg_width / width
    else:
        scale = svg_height / height
    
    # 应用与dxf2svg.py相同的变换
    pixel_x = (dxf_x - min_x) * scale
    # 注意y轴翻转: SVG/PNG坐标系y轴向下，DXF坐标系y轴向上
    pixel_y = svg_height - (dxf_y - min_y) * scale
    
    return pixel_x, pixel_y


def load_yaml_config(config_path):
    """加载YAML配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        print(f"已加载配置文件: {config_path}")
        return config
    except Exception as e:
        print(f"警告: 无法加载配置文件 {config_path}: {e}")
        return None

def convert_text_coordinates(text_data, bounds_data, config=None):
    """
    转换文本数据中的所有坐标
    
    参数:
        text_data: 文本数据列表
        bounds_data: 边界信息数据
        config: 配置文件数据（可选）
        
    返回:
        转换后的文本数据列表
    """
    converted_data = []
    
    # 设置默认边缘空隙比例
    default_padding_ratio = 0.03  # 默认为3%
    
    # 如果提供了配置，从配置中读取边缘空隙比例
    config_padding_ratio = None
    if config and 'coordinate_conversion' in config and 'padding_ratio' in config['coordinate_conversion']:
        config_padding_ratio = config['coordinate_conversion'].get('padding_ratio', default_padding_ratio)
        print(f"从配置文件中读取边缘空隙比例: {config_padding_ratio:.2%}")
    
    # 检查并输出边缘空隙信息
    if 'min_x' in bounds_data and 'max_x' in bounds_data:
        original_width = bounds_data['max_x'] - bounds_data['min_x']
        original_height = bounds_data['max_y'] - bounds_data['min_y']
        padded_width = bounds_data['max_x_padded'] - bounds_data['min_x_padded']
        padded_height = bounds_data['max_y_padded'] - bounds_data['min_y_padded']
        
        # 计算边缘空隙比例
        padding_ratio_width = (padded_width - original_width) / (2 * original_width) if original_width > 0 else 0
        padding_ratio_height = (padded_height - original_height) / (2 * original_height) if original_height > 0 else 0
        bounds_padding_ratio = max(padding_ratio_width, padding_ratio_height)
        
        # 比较bounds.json中的边缘空隙比例与配置文件中的比例
        if config_padding_ratio is not None and abs(bounds_padding_ratio - config_padding_ratio) > 0.005:
            print(f"警告: bounds.json中的边缘空隙比例({bounds_padding_ratio:.2%})与配置文件中的比例({config_padding_ratio:.2%})不一致")
        
        print(f"应用了{bounds_padding_ratio:.1%}的边缘空隙到文本坐标转换（与dxf2svg.py相同）")
        print(f"原始边界: ({bounds_data['min_x']:.2f}, {bounds_data['min_y']:.2f}) 到 ({bounds_data['max_x']:.2f}, {bounds_data['max_y']:.2f})")
        print(f"添加空隙后边界: ({bounds_data['min_x_padded']:.2f}, {bounds_data['min_y_padded']:.2f}) 到 ({bounds_data['max_x_padded']:.2f}, {bounds_data['max_y_padded']:.2f})")
    
    for item in text_data:
        # 复制原始数据
        converted_item = item.copy()
        
        # 获取原始DXF坐标
        dxf_x, dxf_y, dxf_z = item['insert_point']
        
        # 转换为像素坐标
        pixel_x, pixel_y = dxf_to_pixel_coordinates(dxf_x, dxf_y, bounds_data)
        
        # 添加像素坐标
        converted_item['pixel_point'] = [pixel_x, pixel_y]
        
        # 保留原始DXF坐标
        converted_item['dxf_point'] = [dxf_x, dxf_y, dxf_z]
        
        converted_data.append(converted_item)
    
    return converted_data


def main():
    parser = argparse.ArgumentParser(description='Convert DXF text coordinates to pixel coordinates.')
    parser.add_argument('--input-json', type=str, required=True,
                        help='Path to the input JSON file with extracted text data')
    parser.add_argument('--bounds-json', type=str, required=True,
                        help='Path to the bounds JSON file generated by dxf2svg.py')
    parser.add_argument('--output-json', type=str, required=True,
                        help='Path to save the output JSON file with pixel coordinates')
    parser.add_argument('--config', type=str, default='/home/jay/AGSeg_ws/AGSeg/cad2osm/config/params.yaml',
                        help='配置文件路径')

    args = parser.parse_args()
    
    # 检查输入文件是否存在
    if not os.path.isfile(args.input_json):
        print(f"Error: Input JSON file not found: {args.input_json}")
        return
    
    if not os.path.isfile(args.bounds_json):
        print(f"Error: Bounds JSON file not found: {args.bounds_json}")
        return
    
    # 创建输出目录（如果不存在）
    output_dir = os.path.dirname(args.output_json)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # 加载配置文件
    config = None
    if os.path.exists(args.config):
        config = load_yaml_config(args.config)
    
    # 加载输入文件
    text_data = load_json_file(args.input_json)
    bounds_data = load_json_file(args.bounds_json)
    
    if text_data is None or bounds_data is None:
        print("Error: Failed to load input files.")
        return
    
    print("\n转换DXF文本坐标到像素坐标...")
    print(f"使用边界信息文件: {args.bounds_json}")
    if config:
        print(f"使用配置文件: {args.config}")
    
    # 转换坐标
    converted_data = convert_text_coordinates(text_data, bounds_data, config=config)
    
    # 保存结果
    success = save_json_file(converted_data, args.output_json)
    
    if success:
        print(f"Successfully converted {len(converted_data)} text items.")
        print(f"Original DXF coordinates are preserved in 'dxf_point' field.")
        print(f"Pixel coordinates are added in 'pixel_point' field.")


if __name__ == "__main__":
    main()

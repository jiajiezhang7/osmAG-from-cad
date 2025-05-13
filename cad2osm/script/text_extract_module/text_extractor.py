#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAD2OSM 文本提取模块统一入口脚本

此脚本整合了文本提取模块的所有功能，提供一站式处理流程：
1. 从DXF文件提取文本
2. 将DXF文本坐标转换为像素坐标
3. 从OSM文件提取房间多边形
4. 匹配文本到房间
5. 更新OSM文件

用法:
    python text_extractor.py --mode full --dxf <dxf_file> --bounds <bounds_json> --osm <osmAG.osm> --output <output_osm> [--config <params.yaml>]
    
    或者分步执行:
    python text_extractor.py --mode extract_text --dxf <dxf_file> --output <output_json>
    python text_extractor.py --mode match_text --text <text_json> --bounds <bounds_json> --osm <osmAG.osm> --output <output_osm>

参数:
    --mode: 执行模式，可选值: full, extract_text, convert_coordinates, extract_rooms, match_text, update_osm
    --dxf: DXF文件路径
    --text: 文本JSON文件路径
    --bounds: 边界JSON文件路径
    --osm: OSM文件路径
    --output: 输出文件路径
    --config: 配置文件路径
    --layer: DXF文本图层名称，默认为'I—平面—文字'
    --visualize: 是否生成可视化图像
    --nearby-threshold: 附近匹配的距离阈值
"""

import os
import sys
import argparse
import json
from pathlib import Path

# 导入各个模块的功能
# 由于所有文件已经在同一目录下，直接导入模块
from extract_dxf_text import extract_text_from_dxf, decode_dxf_unicode, load_yaml_config as load_config_extract
from dxf_text_to_pixel import load_json_file, save_json_file, convert_text_coordinates, dxf_to_pixel_coordinates
from extract_room_polygons import extract_room_polygons, load_osm_file, load_yaml_config
from match_text_to_rooms import match_text_to_rooms, point_in_polygon, distance_to_polygon, calculate_center_point
from add_text_to_osm import update_osm_tree, visualize_matching


def extract_text(dxf_path, output_path, layer_name, config_path=None):
    """
    从DXF文件提取文本
    
    参数:
        dxf_path: DXF文件路径
        output_path: 输出JSON文件路径
        layer_name: 文本图层名称
        config_path: 配置文件路径
        
    返回:
        提取的文本数据
    """
    print(f"\n===== 步骤1: 从DXF文件提取文本 =====")
    print(f"DXF文件: {dxf_path}")
    print(f"目标图层: {layer_name}")
    
    # 确保输出目录存在
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
    
    # 提取文本
    extract_text_from_dxf(dxf_path, os.path.dirname(output_path), layer_name)
    
    # 加载提取的文本数据
    output_filename = Path(dxf_path).stem + ".json"
    actual_output_path = os.path.join(os.path.dirname(output_path), output_filename)
    text_data = load_json_file(actual_output_path)
    
    # 如果指定了具体的输出路径，复制到指定路径
    if output_path != actual_output_path:
        save_json_file(text_data, output_path)
    
    print(f"文本提取完成，保存到: {output_path}")
    return text_data


def convert_coordinates_step(text_data, bounds_data, output_path=None, config_path=None):
    """
    将DXF文本坐标转换为像素坐标
    
    参数:
        text_data: 文本数据
        bounds_data: 边界数据
        output_path: 输出JSON文件路径
        config_path: 配置文件路径
        
    返回:
        转换后的文本数据
    """
    print(f"\n===== 步骤2: 将DXF文本坐标转换为像素坐标 =====")
    
    # 加载配置
    config = None
    if config_path and os.path.exists(config_path):
        config = load_yaml_config(config_path)
    
    # 转换坐标
    text_data_pixel = convert_text_coordinates(text_data, bounds_data, config)
    print(f"转换了 {len(text_data_pixel)} 个文本项的坐标")
    
    # 保存转换后的数据
    if output_path:
        save_json_file(text_data_pixel, output_path)
        print(f"转换后的坐标保存到: {output_path}")
    
    return text_data_pixel


def extract_rooms_step(osm_path, output_path=None, config_path=None):
    """
    从OSM文件提取房间多边形
    
    参数:
        osm_path: OSM文件路径
        output_path: 输出JSON文件路径
        config_path: 配置文件路径
        
    返回:
        提取的房间数据和边界信息
    """
    print(f"\n===== 步骤3: 从OSM文件提取房间多边形 =====")
    print(f"OSM文件: {osm_path}")
    
    # 加载OSM文件
    osm_root = load_osm_file(osm_path)
    if not osm_root:
        print(f"错误: 无法加载OSM文件 {osm_path}")
        return None
    
    # 加载配置
    config = None
    if config_path and os.path.exists(config_path):
        config = load_yaml_config(config_path)
    
    # 提取房间多边形
    result = extract_room_polygons(osm_root, config)
    rooms_data = result['rooms']
    boundary_info = result['boundary']
    
    print(f"提取了 {len(rooms_data)} 个房间多边形")
    
    # 保存房间数据
    if output_path:
        save_json_file({
            'rooms': rooms_data,
            'boundary': boundary_info
        }, output_path)
        print(f"房间多边形保存到: {output_path}")
    
    return result


def match_text_step(text_data, rooms_data, output_path=None, nearby_threshold=50, max_center_distance_ratio=0.7):
    """
    匹配文本到房间
    
    参数:
        text_data: 文本数据
        rooms_data: 房间数据
        output_path: 输出JSON文件路径
        nearby_threshold: 附近匹配的距离阈值
        max_center_distance_ratio: 内部匹配时，文本到中心距离与房间特征尺寸的比例阈值
        
    返回:
        匹配结果
    """
    print(f"\n===== 步骤4: 匹配文本到房间 =====")
    
    # --- 过滤和修复无效的房间多边形 ---
    rooms_data_filtered = []
    invalid_room_count = 0
    unclosed_fixed_count = 0
    
    for room in rooms_data:
        room_id = room.get('id', 'N/A')  # 获取房间ID用于日志记录
        if 'polygon' in room and isinstance(room['polygon'], list):
            points = room['polygon']
            num_points = len(points)
            
            if num_points >= 4:
                if points[0] == points[-1]:
                    # 有效的闭合多边形，点数足够
                    rooms_data_filtered.append(room)
                else:
                    # 点数足够但未闭合，尝试闭合
                    print(f"警告: 自动闭合房间ID {room_id} 的多边形。首尾点不同。")
                    room['polygon'].append(points[0])  # 附加第一个点以闭合
                    rooms_data_filtered.append(room)
                    unclosed_fixed_count += 1
            elif num_points == 3:
                # 正好3个点，需要闭合
                print(f"警告: 自动闭合房间ID {room_id} 的多边形（只有3个点）。")
                room['polygon'].append(points[0])  # 附加第一个点以闭合
                rooms_data_filtered.append(room)
                unclosed_fixed_count += 1
            else:
                # 少于3个点，无法形成有效的LinearRing/Polygon
                invalid_room_count += 1
                print(f"警告: 过滤掉房间ID {room_id} 因为点数不足（{num_points} < 3）。")
        else:
            # 多边形数据缺失或不是列表
            invalid_room_count += 1
            print(f"警告: 过滤掉房间ID {room_id} 因为缺少或无效的'polygon'数据。")
    
    if invalid_room_count > 0:
        print(f"过滤了 {invalid_room_count} 个无效/退化的房间多边形。")
    if unclosed_fixed_count > 0:
        print(f"自动闭合了 {unclosed_fixed_count} 个有足够点数但未闭合的多边形。")
    print(f"处理 {len(rooms_data_filtered)} 个有效房间多边形进行匹配。")
    
    # 匹配文本到房间
    mapping_result = match_text_to_rooms(
        text_data, 
        rooms_data_filtered, 
        nearby_threshold=nearby_threshold,
        max_center_distance_ratio=max_center_distance_ratio
    )
    
    # --- 输出详细的匹配统计信息 ---
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
        total_texts = len(text_data)
    
    match_rate = (matched_count / total_texts * 100) if total_texts > 0 else 0
    print(f"匹配完成:")
    print(f"  - 匹配的文本: {matched_count}/{total_texts} ({match_rate:.2f}%)")
    print(f"  - 未匹配的文本: {unmatched_count}")
    print(f"  - 有匹配的房间数: {len(mapping_result['matches'])}")
    
    # 打印高评分匹配的信息
    high_quality_matches = 0
    for room_id, matches in mapping_result['matches'].items():
        for match in matches:
            if 'score' in match and match['score'] >= 70:
                high_quality_matches += 1
    
    if high_quality_matches > 0:
        print(f"  - 高质量匹配（评分 >= 70）: {high_quality_matches}")
    
    # 保存匹配结果
    if output_path:
        # 添加统计信息到匹配结果中再保存
        mapping_result['statistics'] = {
            'total_texts': total_texts,
            'matched_texts': matched_count,
            'unmatched_texts': unmatched_count,
            'match_rate': f"{match_rate:.2f}%",
            'rooms_with_matches': len(mapping_result['matches'])
        }
        save_json_file(mapping_result, output_path)
        print(f"匹配结果保存到: {output_path}")
    
    return mapping_result


def update_osm_step(osm_path, mapping_result, output_path, visualize=False, visualization_path=None):
    """
    更新OSM文件
    
    参数:
        osm_path: OSM文件路径
        mapping_result: 匹配结果
        output_path: 输出OSM文件路径
        visualize: 是否生成可视化图像
        visualization_path: 可视化图像保存路径
        
    返回:
        更新的房间数量
    """
    print(f"\n===== 步骤5: 更新OSM文件 =====")
    print(f"OSM文件: {osm_path}")
    print(f"输出OSM文件: {output_path}")
    
    # --- 1. 加载OSM文件 ---
    import xml.etree.ElementTree as ET
    try:
        tree = ET.parse(osm_path)
        osm_root = tree.getroot()
        print(f"成功加载OSM文件，准备更新房间名称")
    except Exception as e:
        print(f"错误: 无法加载OSM文件 {osm_path}: {e}")
        return 0
    
    # --- 2. 更新OSM文件 ---
    print(f"正在更新OSM树中的房间名称...")
    updated_count = update_osm_tree(tree, mapping_result['matches'])
    
    # 获取更多统计信息
    rooms_with_matches = len(mapping_result['matches'])
    total_rooms = len([way for way in osm_root.findall('.//way') 
                       if any(tag.get('k') == 'indoor' and tag.get('v') == 'room' 
                              for tag in way.findall('./tag'))])
    
    match_rate = (updated_count / total_rooms * 100) if total_rooms > 0 else 0
    print(f"更新完成:")
    print(f"  - 更新了 {updated_count}/{total_rooms} 个房间的名称 ({match_rate:.2f}%)")
    
    # --- 3. 保存更新后的OSM文件 ---
    try:
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
            print(f"创建输出目录: {output_dir}")
        
        tree.write(output_path, encoding='utf-8', xml_declaration=True)
        print(f"成功保存更新后的OSM文件到: {output_path}")
    except Exception as e:
        print(f"错误: 无法保存OSM文件 {output_path}: {e}")
        return updated_count  # 返回更新计数，即使保存失败
    
    # --- 4. 生成可视化图像 ---
    if visualize:
        # 确定可视化输出路径
        if not visualization_path:
            visualization_path = f"{os.path.splitext(output_path)[0]}_visualization.png"
        
        print(f"\n正在生成房间多边形和文本匹配的可视化图像...")
        try:
            # 确保可视化输出目录存在
            vis_output_dir = os.path.dirname(visualization_path)
            if vis_output_dir and not os.path.exists(vis_output_dir):
                os.makedirs(vis_output_dir, exist_ok=True)
            
            # 从 OSM 文件重新提取房间多边形数据
            try:
                tree = ET.parse(osm_path)
                osm_root_for_viz = tree.getroot()
                rooms_result = extract_room_polygons(osm_root_for_viz, None)
                rooms_data = rooms_result['rooms']
                print(f"为可视化提取了 {len(rooms_data)} 个房间多边形")
            except Exception as e:
                print(f"警告: 无法加载 OSM 文件进行可视化: {e}")
                return updated_count
                
            # 从匹配结果中提取文本数据
            text_data = []
            matched_text_count = 0
            
            # 处理已匹配的文本
            for room_id, matches in mapping_result['matches'].items():
                for match in matches:
                    if 'pixel_point' in match:
                        text_data.append({
                            'text': match['text'],
                            'pixel_point': match['pixel_point'],
                            'match_type': match.get('match_type', 'unknown'),
                            'score': match.get('score', 0)
                        })
                        matched_text_count += 1
            
            # 添加未匹配的文本
            unmatched_text_count = 0
            for text in mapping_result['unmatched']:
                if 'pixel_point' in text:
                    text_data.append(text)
                    unmatched_text_count += 1
            
            print(f"准备可视化 {matched_text_count} 个已匹配文本和 {unmatched_text_count} 个未匹配文本")
            
            # 调用可视化函数
            visualize_matching(rooms_data, text_data, mapping_result, visualization_path)
            print(f"可视化图像已保存到: {visualization_path}")
        except Exception as e:
            print(f"警告: 生成可视化图像失败: {e}")
    
    return updated_count


def full_process(args):
    """
    执行完整的文本提取和匹配流程
    
    参数:
        args: 命令行参数
    """
    print("\n开始执行完整的文本提取和匹配流程...")
    
    # 检查必要的输入文件
    if not os.path.isfile(args.dxf):
        print(f"错误: DXF文件不存在: {args.dxf}")
        return
    
    if not os.path.isfile(args.bounds):
        print(f"错误: 边界JSON文件不存在: {args.bounds}")
        return
    
    if not os.path.isfile(args.osm):
        print(f"错误: OSM文件不存在: {args.osm}")
        return
    
    # 创建临时文件路径
    temp_dir = os.path.join(os.path.dirname(args.output), "temp")
    os.makedirs(temp_dir, exist_ok=True)
    
    text_json_path = os.path.join(temp_dir, f"{Path(args.dxf).stem}_text.json")
    text_pixel_json_path = os.path.join(temp_dir, f"{Path(args.dxf).stem}_text_pixel.json")
    rooms_json_path = os.path.join(temp_dir, f"{Path(args.osm).stem}_rooms.json")
    mapping_json_path = os.path.join(temp_dir, f"{Path(args.osm).stem}_mapping.json")
    
    # 步骤1: 从DXF文件提取文本
    text_data = extract_text(args.dxf, text_json_path, args.layer, args.config)
    if not text_data:
        print("错误: 文本提取失败")
        return
    
    # 步骤2: 加载边界数据并转换坐标
    bounds_data = load_json_file(args.bounds)
    if not bounds_data:
        print(f"错误: 无法加载边界数据 {args.bounds}")
        return
    
    text_data_pixel = convert_coordinates_step(text_data, bounds_data, text_pixel_json_path, args.config)
    
    # 步骤3: 从OSM文件提取房间多边形
    rooms_result = extract_rooms_step(args.osm, rooms_json_path, args.config)
    if not rooms_result:
        print("错误: 房间多边形提取失败")
        return
    
    # 步骤4: 匹配文本到房间
    mapping_result = match_text_step(
        text_data_pixel, 
        rooms_result['rooms'], 
        mapping_json_path,
        args.nearby_threshold,
        args.max_center_distance_ratio
    )
    
    # 步骤5: 更新OSM文件
    update_osm_step(
        args.osm, 
        mapping_result, 
        args.output,
        args.visualize,
        args.visualization_output
    )
    
    print("\n完整流程处理完成!")
    print(f"最终输出文件: {args.output}")
    if args.visualize and args.visualization_output:
        print(f"可视化图像: {args.visualization_output}")


def main():
    parser = argparse.ArgumentParser(description='CAD2OSM 文本提取模块统一入口脚本')
    
    # 基本参数
    parser.add_argument('--mode', type=str, choices=['full', 'extract_text', 'convert_coordinates', 'extract_rooms', 'match_text', 'update_osm'],
                        default='full', help='执行模式')
    parser.add_argument('--config', type=str, default=None, help='配置文件路径')
    
    # 输入输出参数
    parser.add_argument('--dxf', type=str, default=None, help='DXF文件路径')
    parser.add_argument('--text', type=str, default=None, help='文本JSON文件路径')
    parser.add_argument('--bounds', type=str, default=None, help='边界JSON文件路径')
    parser.add_argument('--osm', type=str, default=None, help='OSM文件路径')
    parser.add_argument('--output', type=str, default=None, help='输出文件路径')
    
    # 其他参数
    parser.add_argument('--layer', type=str, default='I—平面—文字', help='DXF文本图层名称')
    parser.add_argument('--visualize', action='store_true', help='是否生成可视化图像')
    parser.add_argument('--visualization-output', type=str, default=None, help='可视化图像保存路径')
    parser.add_argument('--nearby-threshold', type=float, default=50.0, help='附近匹配的距离阈值')
    parser.add_argument('--max-center-distance-ratio', type=float, default=0.7, help='内部匹配时，文本到中心距离与房间特征尺寸的比例阈值')
    
    args = parser.parse_args()
    
    # 根据模式执行相应的功能
    if args.mode == 'full':
        # 检查必要的参数
        if not args.dxf or not args.bounds or not args.osm or not args.output:
            print("错误: 完整模式需要指定 --dxf, --bounds, --osm 和 --output 参数")
            return
        
        full_process(args)
    
    elif args.mode == 'extract_text':
        # 检查必要的参数
        if not args.dxf or not args.output:
            print("错误: 文本提取模式需要指定 --dxf 和 --output 参数")
            return
        
        extract_text(args.dxf, args.output, args.layer, args.config)
    
    elif args.mode == 'convert_coordinates':
        # 检查必要的参数
        if not args.text or not args.bounds or not args.output:
            print("错误: 坐标转换模式需要指定 --text, --bounds 和 --output 参数")
            return
        
        text_data = load_json_file(args.text)
        bounds_data = load_json_file(args.bounds)
        if text_data and bounds_data:
            convert_coordinates_step(text_data, bounds_data, args.output, args.config)
    
    elif args.mode == 'extract_rooms':
        # 检查必要的参数
        if not args.osm or not args.output:
            print("错误: 房间提取模式需要指定 --osm 和 --output 参数")
            return
        
        extract_rooms_step(args.osm, args.output, args.config)
    
    elif args.mode == 'match_text':
        # 检查必要的参数
        if not args.text or not args.osm or not args.output:
            print("错误: 文本匹配模式需要指定 --text, --osm 和 --output 参数")
            return
        
        text_data = load_json_file(args.text)
        
        # 从OSM文件提取房间多边形
        rooms_result = extract_rooms_step(args.osm, None, args.config)
        
        if text_data and rooms_result:
            match_text_step(text_data, rooms_result['rooms'], args.output, args.nearby_threshold, args.max_center_distance_ratio)
    
    elif args.mode == 'update_osm':
        # 检查必要的参数
        if not args.text or not args.osm or not args.output:
            print("错误: OSM更新模式需要指定 --text, --osm 和 --output 参数")
            return
        
        # 加载匹配结果
        mapping_result = load_json_file(args.text)
        
        if mapping_result:
            update_osm_step(args.osm, mapping_result, args.output, args.visualize, args.visualization_output)


if __name__ == "__main__":
    main()

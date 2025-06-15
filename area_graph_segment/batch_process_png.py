#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量处理PNG文件的脚本
自动调用area_graph_segmentation处理指定目录下的所有PNG文件
根据文件名自动识别建筑类型并设置相应参数
支持多alpha值测试功能
"""

import os
import subprocess
import glob
import json
import argparse
import shutil
from PIL import Image
import sys
import math
from datetime import datetime

# 建筑类型配置
BUILDING_CONFIGS = {
    "apartment": {
        "resolution": 0.04,
        "door_width": 0.9,
        "corridor_width": 1.2,
        "noise_percent": 1.5,
        "simplify_tolerance": 1.0,
        "spike_angle": 15.0,
        "spike_distance": 0.25,
        "min_room_area": 8.0
    },
    "office": {
        "resolution": 0.035,
        "door_width": 1.0,
        "corridor_width": 1.5,
        "noise_percent": 1.2,
        "simplify_tolerance": 1.2,
        "spike_angle": 12.0,
        "spike_distance": 0.20,
        "min_room_area": 12.0
    },
    "hotel": {
        "resolution": 0.04,
        "door_width": 0.9,
        "corridor_width": 1.8,
        "noise_percent": 1.5,
        "simplify_tolerance": 1.0,
        "spike_angle": 15.0,
        "spike_distance": 0.25,
        "min_room_area": 6.0
    },
    "school": {
        "resolution": 0.045,
        "door_width": 1.2,
        "corridor_width": 2.5,
        "noise_percent": 1.0,
        "simplify_tolerance": 1.5,
        "spike_angle": 10.0,
        "spike_distance": 0.15,
        "min_room_area": 20.0
    },
    "gym": {
        "resolution": 0.05,
        "door_width": 1.5,
        "corridor_width": 3.0,
        "noise_percent": 1.0,
        "simplify_tolerance": 2.0,
        "spike_angle": 8.0,
        "spike_distance": 0.15,
        "min_room_area": 50.0
    },
    "residential": {
        "resolution": 0.04,
        "door_width": 0.8,
        "corridor_width": 1.0,
        "noise_percent": 1.8,
        "simplify_tolerance": 0.8,
        "spike_angle": 18.0,
        "spike_distance": 0.30,
        "min_room_area": 5.0
    },
    "museum": {
        "resolution": 0.04,
        "door_width": 1.2,
        "corridor_width": 2.0,
        "noise_percent": 1.0,
        "simplify_tolerance": 1.5,
        "spike_angle": 10.0,
        "spike_distance": 0.20,
        "min_room_area": 15.0
    },
    "monastery": {
        "resolution": 0.05,
        "door_width": 1.0,
        "corridor_width": 1.8,
        "noise_percent": 1.2,
        "simplify_tolerance": 1.3,
        "spike_angle": 12.0,
        "spike_distance": 0.25,
        "min_room_area": 10.0
    },
    "default": {
        "resolution": 0.044,
        "door_width": 1.0,
        "corridor_width": 1.5,
        "noise_percent": 1.5,
        "simplify_tolerance": 1.3,
        "spike_angle": 15.0,
        "spike_distance": 0.30,
        "min_room_area": 10.0
    }
}

def identify_building_type(filename):
    """根据文件名识别建筑类型"""
    filename_lower = filename.lower()
    
    # 检查各种建筑类型关键词
    if any(keyword in filename_lower for keyword in ['apartment', 'residential', '住宅']):
        return 'apartment'
    elif any(keyword in filename_lower for keyword in ['office', 'ufficio', 'schema-ufficio', '办公']):
        return 'office'
    elif any(keyword in filename_lower for keyword in ['hotel', '酒店']):
        return 'hotel'
    elif any(keyword in filename_lower for keyword in ['school', 'scuola', 'aule', 'universita', '学校', '大学']):
        return 'school'
    elif any(keyword in filename_lower for keyword in ['gym', 'gymnasium', '体育馆']):
        return 'gym'
    elif any(keyword in filename_lower for keyword in ['museum', '博物馆']):
        return 'museum'
    elif any(keyword in filename_lower for keyword in ['monastery', '修道院']):
        return 'monastery'
    elif any(keyword in filename_lower for keyword in ['centro', 'cultural', '文化中心']):
        return 'museum'  # 文化中心按博物馆处理
    else:
        return 'default'

def get_image_dimensions(image_path):
    """获取图片尺寸"""
    try:
        with Image.open(image_path) as img:
            return img.size  # (width, height)
    except Exception as e:
        print(f"警告: 无法获取图片 {image_path} 的尺寸: {e}")
        return None

def calculate_resolution_from_size(width, height, building_type):
    """根据图片尺寸和建筑类型计算合适的分辨率"""
    base_config = BUILDING_CONFIGS[building_type]
    base_resolution = base_config["resolution"]
    
    # 根据图片大小调整分辨率
    # 大图片通常需要更高的分辨率(更小的米/像素值)
    if width > 4000 or height > 4000:
        return base_resolution * 0.8  # 大图片，提高分辨率
    elif width < 2000 or height < 2000:
        return base_resolution * 1.2  # 小图片，降低分辨率
    else:
        return base_resolution

def calculate_door_corridor_from_alpha(alpha_value, resolution):
    """
    根据目标alpha值和分辨率反推door_width和corridor_width
    
    根据C++代码中的逻辑：
    a = min(door_wide, corridor_wide) + 0.1 (或 -0.1)
    alpha_value = ceil(a^2 * 0.25 / res^2)
    
    反推：
    a = sqrt(alpha_value * 4 * res^2)
    """
    # 从alpha值反推a值（考虑到ceil函数，我们取中间值）
    a = math.sqrt(alpha_value * 4 * resolution * resolution)
    
    # 设置door_width稍小，corridor_width稍大，确保min()选择door_width
    door_width = a - 0.1
    corridor_width = a + 0.5  # 设置更大的差值确保逻辑正确
    
    # 确保值为正且合理
    door_width = max(0.5, door_width)
    corridor_width = max(door_width + 0.2, corridor_width)
    
    return door_width, corridor_width

def build_command(executable_path, png_path, building_type, image_dimensions=None, alpha_override=None):
    """构建命令行"""
    config = BUILDING_CONFIGS[building_type].copy()
    
    # 如果有图片尺寸信息，调整分辨率
    if image_dimensions:
        width, height = image_dimensions
        config["resolution"] = calculate_resolution_from_size(width, height, building_type)
        
        # 添加图片尺寸参数
        config["png_width"] = width
        config["png_height"] = height
    
    # 如果指定了alpha值，重新计算door_width和corridor_width
    if alpha_override is not None:
        door_width, corridor_width = calculate_door_corridor_from_alpha(alpha_override, config["resolution"])
        config["door_width"] = door_width
        config["corridor_width"] = corridor_width
        print(f"Alpha值 {alpha_override} -> door_width: {door_width:.3f}, corridor_width: {corridor_width:.3f}")
    
    cmd = [executable_path, png_path]
    
    # 添加所有参数
    cmd.extend([
        "--resolution", str(config["resolution"]),
        "--door-width", str(config["door_width"]),
        "--corridor-width", str(config["corridor_width"]),
        "--noise-percent", str(config["noise_percent"]),
        "--simplify-tolerance", str(config["simplify_tolerance"]),
        "--spike-angle", str(config["spike_angle"]),
        "--spike-distance", str(config["spike_distance"]),
        "--min-room-area", str(config["min_room_area"]),
        "--clean-input", "0",  # 通常不需要清理
        "--remove-furniture", "1",  # 通常需要移除家具
    ])
    
    # 如果有图片尺寸，添加尺寸参数
    if image_dimensions:
        cmd.extend([
            "--png-width", str(config["png_width"]),
            "--png-height", str(config["png_height"])
        ])
    
    return cmd

def save_parameters_json(alpha_output_dir, png_path, building_type, image_dimensions, alpha_value, config, cmd):
    """保存当前实验的所有参数到JSON文件"""
    filename = os.path.basename(png_path)
    base_name = os.path.splitext(filename)[0]
    
    # 构建参数记录
    parameters = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "input_file": png_path,
            "filename": filename,
            "base_name": base_name,
            "building_type": building_type,
            "alpha_value": alpha_value,
            "processing_mode": "multi_alpha_test" if alpha_value is not None else "single_run"
        },
        "image_info": {
            "width": image_dimensions[0] if image_dimensions else None,
            "height": image_dimensions[1] if image_dimensions else None,
            "dimensions": f"{image_dimensions[0]}x{image_dimensions[1]}" if image_dimensions else None
        },
        "algorithm_parameters": {
            "resolution": config["resolution"],
            "door_width": config["door_width"],
            "corridor_width": config["corridor_width"],
            "noise_percent": config["noise_percent"],
            "simplify_tolerance": config["simplify_tolerance"],
            "spike_angle": config["spike_angle"],
            "spike_distance": config["spike_distance"],
            "min_room_area": config["min_room_area"],
            "clean_input": 0,
            "remove_furniture": 1
        },
        "command_line": {
            "full_command": " ".join(cmd),
            "arguments": cmd[1:]  # 去掉可执行文件路径
        },
        "building_type_config": BUILDING_CONFIGS[building_type],
        "output_directory": alpha_output_dir
    }
    
    # 根据处理模式添加不同的信息
    if alpha_value is not None:
        # 多alpha值测试模式
        parameters["derived_info"] = {
            "alpha_calculation": {
                "formula": "alpha = ceil((min(door_width, corridor_width) + offset)^2 * 0.25 / resolution^2)",
                "calculated_from_alpha": True,
                "target_alpha": alpha_value,
                "min_width": min(config["door_width"], config["corridor_width"]),
                "a_value": math.sqrt(alpha_value * 4 * config["resolution"] * config["resolution"])
            }
        }
        json_filename = f"{base_name}_alpha_{alpha_value}_parameters.json"
    else:
        # 单次处理模式
        parameters["derived_info"] = {
            "alpha_calculation": {
                "formula": "alpha = ceil((min(door_width, corridor_width) + offset)^2 * 0.25 / resolution^2)",
                "calculated_from_alpha": False,
                "door_width_source": "building_type_config",
                "corridor_width_source": "building_type_config",
                "min_width": min(config["door_width"], config["corridor_width"]),
                "expected_alpha": math.ceil((min(config["door_width"], config["corridor_width"]) - 0.1) ** 2 * 0.25 / (config["resolution"] ** 2))
            }
        }
        json_filename = f"{base_name}_parameters.json"
    
    # 如果有PNG尺寸参数，添加到算法参数中
    if image_dimensions:
        parameters["algorithm_parameters"]["png_width"] = config.get("png_width", image_dimensions[0])
        parameters["algorithm_parameters"]["png_height"] = config.get("png_height", image_dimensions[1])
    
    # 保存JSON文件
    json_path = os.path.join(alpha_output_dir, json_filename)
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(parameters, f, indent=2, ensure_ascii=False)
        print(f"    参数记录已保存: {os.path.basename(json_path)}")
        return json_path
    except Exception as e:
        print(f"    警告: 无法保存参数JSON文件: {e}")
        return None

def process_single_png_alpha(executable_path, png_path, unified_output_dir, alpha_value, building_type, image_dimensions, dry_run=False):
    """处理单个PNG文件的单个alpha值"""
    filename = os.path.basename(png_path)
    
    print(f"\n    处理Alpha值: {alpha_value}")
    
    # 获取配置并计算参数
    config = BUILDING_CONFIGS[building_type].copy()
    
    # 如果有图片尺寸信息，调整分辨率
    if image_dimensions:
        width, height = image_dimensions
        config["resolution"] = calculate_resolution_from_size(width, height, building_type)
        config["png_width"] = width
        config["png_height"] = height
    
    # 根据alpha值重新计算door_width和corridor_width
    door_width, corridor_width = calculate_door_corridor_from_alpha(alpha_value, config["resolution"])
    config["door_width"] = door_width
    config["corridor_width"] = corridor_width
    print(f"    Alpha值 {alpha_value} -> door_width: {door_width:.3f}, corridor_width: {corridor_width:.3f}")
    
    if dry_run:
        cmd = build_command(executable_path, png_path, building_type, image_dimensions, alpha_value)
        base_name = os.path.splitext(filename)[0]
        file_output_dir = os.path.join(unified_output_dir, base_name, f"alpha_{alpha_value}")
        print(f"    >>> 预览模式，会创建目录: {file_output_dir}")
        print(f"    >>> 预览模式，执行命令: {' '.join(cmd)}")
        print(f"    >>> 预览模式，会生成参数JSON文件")
        return True
    
    try:
        # 为每个alpha值创建单独的子目录
        base_name = os.path.splitext(filename)[0]
        alpha_output_dir = os.path.join(unified_output_dir, base_name, f"alpha_{alpha_value}")
        os.makedirs(alpha_output_dir, exist_ok=True)
        
        # 将PNG文件复制到该alpha值的子目录中
        copied_png_path = os.path.join(alpha_output_dir, filename)
        if not os.path.exists(copied_png_path):
            shutil.copy2(png_path, copied_png_path)
            print(f"    复制文件到: {copied_png_path}")
        
        # 使用复制后的文件路径构建命令
        cmd = build_command(executable_path, copied_png_path, building_type, image_dimensions, alpha_value)
        
        # 保存参数JSON文件
        save_parameters_json(alpha_output_dir, png_path, building_type, image_dimensions, alpha_value, config, cmd)
        
        print(f"    执行命令: {' '.join(cmd)}")
        
        # 在该alpha值的子目录中执行命令
        original_cwd = os.getcwd()
        os.chdir(alpha_output_dir)
        
        try:
            # 执行命令 (使用相对路径)
            relative_executable = os.path.relpath(os.path.abspath(os.path.join(original_cwd, executable_path)), alpha_output_dir)
            cmd[0] = relative_executable  # 更新可执行文件路径为相对路径
            cmd[1] = filename  # 更新输入文件为相对路径
            
            print(f"    在目录 {alpha_output_dir} 中执行")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)  # 20分钟超时
            
            if result.returncode == 0:
                print(f"    ✓ Alpha {alpha_value} 处理成功")
                return True
            else:
                print(f"    ✗ Alpha {alpha_value} 处理失败")
                print(f"    错误输出: {result.stderr}")
                if result.stdout:
                    print(f"    标准输出: {result.stdout}")
                return False
        finally:
            # 恢复原始工作目录
            os.chdir(original_cwd)
            
    except subprocess.TimeoutExpired:
        print(f"    ✗ Alpha {alpha_value} 处理超时")
        os.chdir(original_cwd)  # 确保恢复目录
        return False
    except Exception as e:
        print(f"    ✗ Alpha {alpha_value} 处理异常: {e}")
        if 'original_cwd' in locals():
            os.chdir(original_cwd)  # 确保恢复目录
        return False

def process_single_png(executable_path, png_path, unified_output_dir, dry_run=False, alpha_values=None):
    """处理单个PNG文件"""
    filename = os.path.basename(png_path)
    building_type = identify_building_type(filename)
    
    print(f"\n处理文件: {filename}")
    print(f"识别的建筑类型: {building_type}")
    
    # 获取图片尺寸
    image_dimensions = get_image_dimensions(png_path)
    if image_dimensions:
        print(f"图片尺寸: {image_dimensions[0]} x {image_dimensions[1]}")
    
    # 如果指定了alpha值列表，进行多alpha值测试
    if alpha_values:
        print(f"多Alpha值测试模式，测试 {len(alpha_values)} 个Alpha值: {alpha_values}")
        success_count = 0
        
        for alpha_value in alpha_values:
            if process_single_png_alpha(executable_path, png_path, unified_output_dir, 
                                       alpha_value, building_type, image_dimensions, dry_run):
                success_count += 1
        
        print(f"Alpha值测试完成: {success_count}/{len(alpha_values)} 成功")
        return success_count > 0
    
    # 原有的单次处理逻辑
    # 获取配置
    config = BUILDING_CONFIGS[building_type].copy()
    
    # 如果有图片尺寸信息，调整分辨率
    if image_dimensions:
        width, height = image_dimensions
        config["resolution"] = calculate_resolution_from_size(width, height, building_type)
        config["png_width"] = width
        config["png_height"] = height
    
    if dry_run:
        # 在预览模式下，仍然使用原始路径构建命令用于显示
        cmd = build_command(executable_path, png_path, building_type, image_dimensions)
        base_name = os.path.splitext(filename)[0]
        file_output_dir = os.path.join(unified_output_dir, base_name)
        print(f"使用的配置: {config}")
        print(f"执行命令: {' '.join(cmd)}")
        print(f">>> 预览模式，实际运行时会创建子目录: {file_output_dir}")
        print(f">>> 预览模式，所有输出文件都会在该子目录中")
        print(f">>> 预览模式，会生成参数JSON文件")
        print(">>> 预览模式，不执行实际命令")
        return True

    try:
        # 为每个PNG文件创建单独的子目录
        base_name = os.path.splitext(filename)[0]
        file_output_dir = os.path.join(unified_output_dir, base_name)
        os.makedirs(file_output_dir, exist_ok=True)
        
        # 将PNG文件复制到该文件的子目录中
        copied_png_path = os.path.join(file_output_dir, filename)
        if not os.path.exists(copied_png_path):
            shutil.copy2(png_path, copied_png_path)
            print(f"复制文件到: {copied_png_path}")
        
        # 使用复制后的文件路径构建命令
        cmd = build_command(executable_path, copied_png_path, building_type, image_dimensions)
        
        # 保存参数JSON文件（为单次处理添加alpha_value=None）
        save_parameters_json(file_output_dir, png_path, building_type, image_dimensions, None, config, cmd)
        
        print(f"使用的配置: {config}")
        print(f"执行命令: {' '.join(cmd)}")
        
        # 在该文件的子目录中执行命令
        original_cwd = os.getcwd()
        os.chdir(file_output_dir)
        
        try:
            # 执行命令 (使用相对路径)
            relative_executable = os.path.relpath(os.path.abspath(os.path.join(original_cwd, executable_path)), file_output_dir)
            cmd[0] = relative_executable  # 更新可执行文件路径为相对路径
            cmd[1] = filename  # 更新输入文件为相对路径
            
            print(f"在目录 {file_output_dir} 中执行: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=1200)  # 20分钟超时
            
            if result.returncode == 0:
                print(f"✓ 成功处理: {filename}")
                print(f"所有输出都在: {file_output_dir}")
                return True
            else:
                print(f"✗ 处理失败: {filename}")
                print(f"错误输出: {result.stderr}")
                if result.stdout:
                    print(f"标准输出: {result.stdout}")
                return False
        finally:
            # 恢复原始工作目录
            os.chdir(original_cwd)
            
    except subprocess.TimeoutExpired:
        print(f"✗ 处理超时: {filename}")
        os.chdir(original_cwd)  # 确保恢复目录
        return False
    except Exception as e:
        print(f"✗ 处理异常: {filename}, 错误: {e}")
        if 'original_cwd' in locals():
            os.chdir(original_cwd)  # 确保恢复目录
        return False

def parse_alpha_values(alpha_str):
    """解析alpha值字符串"""
    if not alpha_str:
        return None
    
    try:
        # 支持逗号分隔的列表和范围语法
        values = []
        parts = alpha_str.split(',')
        
        for part in parts:
            part = part.strip()
            if '-' in part and not part.startswith('-'):
                # 范围语法: 100-500
                start, end = map(int, part.split('-'))
                # 生成范围内的值（等差数列）
                step = max(1, (end - start) // 7)  # 最多7个值
                values.extend(range(start, end + 1, step))
            else:
                # 单个值
                values.append(int(part))
        
        # 去重并排序
        values = sorted(list(set(values)))
        return values
        
    except ValueError as e:
        print(f"错误: 无法解析alpha值 '{alpha_str}': {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description='批量处理PNG文件，支持多Alpha值测试')
    parser.add_argument('input_dir', help='包含PNG文件的输入目录')
    parser.add_argument('--executable', '-e', 
                        default='./build/bin/area_graph_segmentation',
                        help='area_graph_segmentation可执行文件路径')
    parser.add_argument('--output-dir', '-o', 
                        default='./output',
                        help='统一输出目录 (默认: ./output)')
    parser.add_argument('--pattern', '-p', 
                        default='*.png', 
                        help='文件匹配模式 (默认: *.png)')
    parser.add_argument('--dry-run', '-n', 
                        action='store_true',
                        help='预览模式，只显示命令不执行')
    parser.add_argument('--filter', '-f',
                        help='只处理包含指定关键词的文件')
    parser.add_argument('--skip', '-s',
                        help='跳过包含指定关键词的文件')
    parser.add_argument('--alpha-values', '-a',
                        help='多Alpha值测试，用逗号分隔 (例如: "100,200,500" 或 "100-1000")')
    parser.add_argument('--alpha-preset',
                        choices=['small', 'medium', 'large', 'comprehensive'],
                        help='使用预设的Alpha值范围')
    
    args = parser.parse_args()
    
    # 检查输入目录
    if not os.path.isdir(args.input_dir):
        print(f"错误: 输入目录不存在: {args.input_dir}")
        sys.exit(1)
    
    # 检查可执行文件
    if not args.dry_run and not os.path.isfile(args.executable):
        print(f"错误: 可执行文件不存在: {args.executable}")
        sys.exit(1)
    
    # 处理Alpha值参数
    alpha_values = None
    if args.alpha_values:
        alpha_values = parse_alpha_values(args.alpha_values)
    elif args.alpha_preset:
        # 预设的Alpha值范围
        presets = {
            'small': [50, 100, 200, 500],
            'medium': [100, 200, 500, 1000, 2000],
            'large': [500, 1000, 2000, 5000],
            'comprehensive': [50, 100, 200, 500, 1000, 2000, 5000, 10000]
        }
        alpha_values = presets[args.alpha_preset]
    
    if alpha_values:
        print(f"多Alpha值测试模式启用，测试Alpha值: {alpha_values}")
    
    # 设置统一输出目录
    unified_output_dir = os.path.abspath(args.output_dir)
    if not args.dry_run:
        os.makedirs(unified_output_dir, exist_ok=True)
        print(f"统一输出目录: {unified_output_dir}")
    else:
        print(f"预览模式 - 统一输出目录将是: {unified_output_dir}")
    
    # 查找PNG文件
    pattern = os.path.join(args.input_dir, args.pattern)
    png_files = glob.glob(pattern)
    
    if not png_files:
        print(f"警告: 在 {args.input_dir} 中未找到匹配 {args.pattern} 的文件")
        sys.exit(1)
    
    # 应用过滤器
    if args.filter:
        png_files = [f for f in png_files if args.filter.lower() in os.path.basename(f).lower()]
        print(f"应用过滤器 '{args.filter}': 找到 {len(png_files)} 个文件")
    
    if args.skip:
        png_files = [f for f in png_files if args.skip.lower() not in os.path.basename(f).lower()]
        print(f"跳过包含 '{args.skip}' 的文件: 剩余 {len(png_files)} 个文件")
    
    if not png_files:
        print("没有文件需要处理")
        sys.exit(1)
    
    print(f"找到 {len(png_files)} 个PNG文件")
    
    # 统计信息
    success_count = 0
    total_count = len(png_files)
    
    # 处理每个文件
    for i, png_path in enumerate(png_files, 1):
        print(f"\n{'='*60}")
        print(f"进度: {i}/{total_count}")
        
        if process_single_png(args.executable, png_path, unified_output_dir, args.dry_run, alpha_values):
            success_count += 1
    
    # 总结
    print(f"\n{'='*60}")
    print(f"处理完成!")
    print(f"总文件数: {total_count}")
    print(f"成功: {success_count}")
    print(f"失败: {total_count - success_count}")
    
    if not args.dry_run and success_count > 0:
        print(f"\n所有输出文件都保存在: {unified_output_dir}")
        if alpha_values:
            print("多Alpha值测试目录结构: output/<png文件名>/alpha_<值>/<输出文件>")
            print("参数记录文件: <png文件名>_alpha_<值>_parameters.json")
        else:
            print("每个PNG文件的所有输出都在对应的 <filename>/ 子目录中")
            print("目录结构: output/<png文件名>/<png文件> + <png文件名>_output/ + 其他输出文件")
            print("参数记录文件: <png文件名>_parameters.json")
        print("\n参数JSON文件包含:")
        print("- 完整的算法参数（分辨率、门宽、走廊宽等）")
        print("- 图片信息（尺寸、文件名等）")
        print("- 建筑类型配置")
        print("- 完整的命令行")
        print("- Alpha值计算信息（如适用）")
        print("- 时间戳和元数据")
    
    if args.dry_run:
        print("\n>>> 这是预览模式，没有执行实际命令")
        print(">>> 实际运行时，每个处理都会生成对应的参数JSON文件")

if __name__ == "__main__":
    main() 
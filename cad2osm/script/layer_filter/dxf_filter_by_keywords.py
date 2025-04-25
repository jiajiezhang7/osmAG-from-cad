#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DXF图层过滤脚本
基于JSON配置文件中的图层列表过滤CAD图层

该脚本接收DXF文件作为输入，并根据配置文件中的图层列表过滤图层，输出过滤后的DXF文件
支持NCS和GB/T两种标准
"""

import ezdxf
import os
import sys
import json
import argparse
from datetime import datetime
import logging
from pathlib import Path


def load_filter_config(config_file, standard):
    """
    从JSON配置文件加载过滤规则
    
    参数:
        config_file (str): JSON配置文件路径
        standard (str): 使用的标准，'NCS'或'GB/T'
    
    返回:
        dict: 过滤参数字典
    """
    try:
        # 读取JSON配置文件
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 检查配置格式是否正确
        if not isinstance(config, dict):
            logging.warning("配置文件格式错误，使用默认配置")
            return get_default_config()
        
        # 检查是否包含指定的标准
        if standard not in config:
            logging.warning(f"配置文件中未找到标准 '{standard}'，使用默认配置")
            return get_default_config()
        
        # 获取指定标准的图层列表
        standard_config = config[standard]
        
        # 提取图层列表
        exact_match_layers = []
        
        # NCS标准只有一个layers列表
        if standard == 'NCS':
            if 'layers' in standard_config:
                exact_match_layers.extend(standard_config['layers'])
        # GB/T标准有中英文两个列表
        elif standard == 'GB/T':
            if 'layers_chinese' in standard_config:
                exact_match_layers.extend(standard_config['layers_chinese'])
            if 'layers_english' in standard_config:
                exact_match_layers.extend(standard_config['layers_english'])
        
        # 添加必须保留的基本图层
        exact_match_layers.extend(['0', 'Defpoints'])
        
        return {
            'exact_match_layers': exact_match_layers,
            'case_sensitive': False
        }
    except Exception as e:
        logging.error(f"读取配置文件 {config_file} 时发生错误: {e}")
        return get_default_config()


def get_default_config():
    """
    获取默认配置
    
    返回:
        dict: 默认过滤参数字典
    """
    return {
        'exact_match_layers': [
            # 基本图层
            '0', 'Defpoints', 
            # 英文标准图层
            'A-WALL', 'A-COLS', 'A-SLAB', 'A-WINDOW', 'A-DOOR', 'A-STAIR',
            # 中文标准图层
            '建-墙', '建-柱', '建-板', '建-窗', '建-门', '建-梯'
        ],
        'case_sensitive': False
    }


def should_keep_layer(layer_name, params=None):
    """
    基于精确匹配图层名判断是否保留图层
    
    参数:
        layer_name (str): 图层名称
        params (dict): 过滤参数，包含以下键:
            - exact_match_layers (list): 完全匹配这些名称的图层将被保留
            - case_sensitive (bool): 是否区分大小写，默认为False
    
    返回:
        bool: 是否保留该图层
    """
    # 默认参数
    if params is None:
        params = get_default_config()
    
    # 提取参数
    exact_match_layers = params.get('exact_match_layers', [])
    case_sensitive = params.get('case_sensitive', False)
    
    # 检查是否为绝对包含的图层名（完全匹配）
    if layer_name in exact_match_layers:
        return True
    
    # 如果不区分大小写，则转换为大写进行比较
    if not case_sensitive:
        layer_name_upper = layer_name.upper()
        exact_match_layers_upper = [layer.upper() for layer in exact_match_layers]
        if layer_name_upper in exact_match_layers_upper:
            return True
    
    # 默认不保留
    return False


def filter_dxf_layers(input_file, output_file, filter_params=None):
    """
    根据预定义规则过滤DXF文件图层，并返回保留图层的名称列表
    
    参数:
        input_file (str): 输入DXF文件路径
        output_file (str): 输出DXF文件路径
        filter_params (dict): 过滤参数字典，传递给should_keep_layer函数
    
    返回:
        tuple: (处理是否成功, 消息, 保留图层名称列表或None)
    """
    try:
        # 读取源DXF文件
        logging.info(f"正在读取文件: {input_file}")
        doc = ezdxf.readfile(input_file)
        
        # 创建新的DXF文档
        new_doc = ezdxf.new()
        
        # 复制原文件的设置
        new_doc.header = doc.header
        # 尝试保留原始ACADVER，如果不存在则不设置
        try:
            new_doc.header['$ACADVER'] = doc.header['$ACADVER']
        except KeyError:
            logging.warning("警告: 源文件未找到 $ACADVER 头变量。")
            pass
            
        # 获取模型空间
        msp = doc.modelspace()
        new_msp = new_doc.modelspace()
        
        # 获取要保留的图层名称
        layers_to_keep = set()  # 使用集合提高查找效率
        kept_layer_names = []   # 用于日志记录
        original_layer_count = 0
        
        for layer in doc.layers:
            original_layer_count += 1
            layer_name = layer.dxf.name
            
            if should_keep_layer(layer_name, filter_params):
                layers_to_keep.add(layer_name)
                kept_layer_names.append(layer_name)
                logging.debug(f"保留图层: {layer_name}")
            else:
                logging.debug(f"排除图层: {layer_name}")
        
        # 创建日志内容
        log_content = [
            f"DXF文件图层过滤报告",
            f"处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"输入文件: {os.path.basename(input_file)}",
            f"原始图层数: {original_layer_count}",
            f"保留图层数: {len(layers_to_keep)}",
            "\n保留的图层列表:",
        ]
        # 对名称排序并添加到日志
        log_content.extend([f"- {name}" for name in sorted(kept_layer_names)])
        
        # 复制需要保留的图层定义
        for layer in doc.layers:
            layer_name = layer.dxf.name
            if layer_name in layers_to_keep:
                # 获取原始图层的属性
                color = layer.dxf.color
                linetype = layer.dxf.linetype
                
                # 检查图层是否已存在
                if layer_name == '0':
                    # 对于 "0" 图层，修改现有的属性
                    new_layer = new_doc.layers.get('0')
                    new_layer.dxf.color = color
                    new_layer.dxf.linetype = linetype
                else:
                    # 创建新图层
                    try:
                        # 尝试设置完整属性
                        new_doc.layers.add(
                            name=layer_name,
                            color=color,
                            linetype=linetype
                        )
                    except Exception as e:
                        logging.warning(f"警告: 创建图层 '{layer_name}' 时出错: {e}")
                        # 尝试最简单的添加方式
                        new_doc.layers.add(name=layer_name)
        
        # 复制仅属于保留图层的实体
        entity_count = 0
        for entity in msp:
            # 获取实体所在图层，如果没有图层属性则假定为'0'图层
            entity_layer = getattr(entity.dxf, 'layer', '0')
            
            if entity_layer in layers_to_keep:
                # 复制实体到新文档
                try:
                    entity_copy = new_msp.add_entity(entity)
                    entity_count += 1
                except Exception as e:
                    logging.warning(f"警告: 复制实体时出错 (图层 '{entity_layer}'): {e}")
        
        # 保存新DXF文件
        logging.info(f"正在保存过滤后的文件: {output_file}")
        new_doc.saveas(output_file)
        
        # 将日志内容附加到结果
        log_content.append(f"\n总共复制了 {entity_count} 个实体到新文件。")
        log_content.append(f"输出文件: {os.path.basename(output_file)}")
        
        # 打印日志
        log_text = "\n".join(log_content)
        logging.info(log_text)
        
        # 保存日志文件
        log_file = os.path.splitext(output_file)[0] + "_filter_log.txt"
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(log_text)
        
        return True, "DXF文件图层过滤成功", kept_layer_names
        
    except Exception as e:
        error_msg = f"处理DXF文件时出错: {str(e)}"
        logging.error(error_msg)
        return False, error_msg, None


def process_dxf_file(input_file, output_file=None, filter_params=None):
    """
    处理单个DXF文件
    
    参数:
        input_file (str): 输入DXF文件路径
        output_file (str): 输出DXF文件路径，如为None则自动生成
        filter_params (dict): 过滤参数
    
    返回:
        bool: 处理是否成功
    """
    # 如果未指定输出文件，则生成默认名称
    if output_file is None:
        input_path = Path(input_file)
        output_dir = input_path.parent
        output_name = f"{input_path.stem}_filtered{input_path.suffix}"
        output_file = str(output_dir / output_name)
    
    logging.info(f"处理文件: {input_file} -> {output_file}")
    
    # 过滤图层
    success, message, kept_layers = filter_dxf_layers(input_file, output_file, filter_params)
    
    # 打印结果消息
    if success:
        logging.info(f"成功: {message}")
        logging.info(f"保留了 {len(kept_layers)} 个图层")
        return True
    else:
        logging.error(f"失败: {message}")
        return False


def process_directory(input_dir, output_dir=None, filter_params=None, recursive=False):
    """
    处理目录中的所有DXF文件
    
    参数:
        input_dir (str): 输入目录路径
        output_dir (str): 输出目录路径，如为None则与输入目录相同
        filter_params (dict): 过滤参数
        recursive (bool): 是否递归处理子目录
    
    返回:
        tuple: (成功处理的文件数, 总文件数)
    """
    # 确保输出目录存在
    if output_dir is None:
        output_dir = input_dir
    else:
        os.makedirs(output_dir, exist_ok=True)
    
    # 获取所有DXF文件
    input_path = Path(input_dir)
    pattern = "**/*.dxf" if recursive else "*.dxf"
    dxf_files = list(input_path.glob(pattern))
    
    # 处理每个文件
    success_count = 0
    total_count = len(dxf_files)
    
    for file_path in dxf_files:
        # 计算相对路径并创建输出目录结构
        rel_path = file_path.relative_to(input_path)
        output_path = Path(output_dir) / rel_path.parent
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 生成输出文件名
        output_file = str(output_path / f"{file_path.stem}_filtered{file_path.suffix}")
        
        # 处理文件
        if process_dxf_file(str(file_path), output_file, filter_params):
            success_count += 1
    
    return success_count, total_count


def main():
    """主函数 - 解析命令行参数并执行过滤"""
    # 配置命令行参数解析
    parser = argparse.ArgumentParser(description='基于标准图层名称过滤DXF文件图层')
    
    # 输入/输出参数
    parser.add_argument('input', help='输入DXF文件或目录路径')
    parser.add_argument('-o', '--output', help='输出DXF文件或目录路径')
    parser.add_argument('-r', '--recursive', action='store_true', help='递归处理子目录中的DXF文件')
    
    # 配置文件参数
    parser.add_argument('-c', '--config', 
                    default='/home/jay/AGSeg_ws/AGSeg/cad2osm/script/layer_filter/cad_layers_to_keep.json',
                    help='JSON配置文件路径 (默认: cad_layers_to_keep.json)')
    
    # 标准选择参数
    parser.add_argument('-s', '--standard', choices=['NCS', 'GB/T'], default='NCS',
                    help='使用的CAD标准: NCS(美国标准) 或 GB/T(中国标准)')
    
    # 日志参数
    parser.add_argument('-v', '--verbose', action='store_true', help='显示详细日志')
    
    # 解析参数
    args = parser.parse_args()
    
    # 配置日志
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 加载配置文件
    filter_params = load_filter_config(args.config, args.standard)
    
    # 处理输入路径
    input_path = Path(args.input)
    
    if input_path.is_file():
        # 单个文件处理
        output_file = args.output
        success = process_dxf_file(str(input_path), output_file, filter_params)
        print(f"处理结果: {'成功' if success else '失败'}")
    
    elif input_path.is_dir():
        # 目录处理
        output_dir = args.output
        success_count, total_count = process_directory(str(input_path), output_dir, filter_params, args.recursive)
        print(f"处理完成: 成功 {success_count}/{total_count} 个文件")
    
    else:
        print(f"错误: 输入路径不存在 - {args.input}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
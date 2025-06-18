#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 集成CAD预处理流程脚本 - 增强计时版本
# 作者: Cascade AI 辅助 Jiajie Zhang
# 创建日期: 2025-05-13
# 修改日期: 2025-01-27 - 添加详细计时功能

import os
import sys
import argparse
import yaml
import logging
import time
from pathlib import Path
from datetime import datetime
import statistics

# 导入各个处理模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from dwg2dxf_oda import ODAConverter
from dxf_filter import filter_dxf_layers
from dxf2svg import dxf_to_svg, load_yaml_config
from svg2png import svg_to_occupancy_grid, save_occupancy_grid

class CADPreprocessor:
    def __init__(self, config_path=None, log_level=logging.INFO):
        """初始化CAD预处理器"""
        self.setup_logging(log_level)
        self.load_config(config_path)
        self.oda_converter = ODAConverter(log_level=log_level)
        
        # 添加计时统计变量
        self.processing_stats = {
            'total_files': 0,
            'successful_files': 0,
            'failed_files': 0,
            'step_times': {
                'dwg_to_dxf': [],
                'dxf_filter': [],
                'dxf_to_svg': [],
                'svg_to_png': []
            },
            'file_times': [],
            'file_sizes': [],
            'start_time': None,
            'end_time': None
        }
        
    def setup_logging(self, log_level):
        """设置日志配置"""
        self.logger = logging.getLogger('CADPreprocessor')
        self.logger.setLevel(log_level)
        
        # 创建日志目录
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        # 设置日志文件
        log_file = log_dir / f'preprocessing_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        
        # 创建处理器
        console_handler = logging.StreamHandler()
        file_handler = logging.FileHandler(log_file)
        
        # 设置格式
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        # 添加处理器
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
    
    def load_config(self, config_path):
        """加载配置文件"""
        self.config = None
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    self.config = yaml.safe_load(f)
                self.logger.info(f"已加载配置文件: {config_path}")
            except Exception as e:
                self.logger.warning(f"无法加载配置文件 {config_path}: {e}")
                self.logger.warning("将使用默认配置")
        else:
            self.logger.info("未指定配置文件或文件不存在，将使用默认配置")
    
    def process_dwg_to_dxf(self, input_file, output_file):
        """步骤1: 将DWG转换为DXF"""
        step_start = time.time()
        self.logger.info(f"步骤1: 将DWG转换为DXF - {os.path.basename(input_file)}")
        success, message = self.oda_converter.convert_file(input_file, output_file)
        step_time = time.time() - step_start
        self.processing_stats['step_times']['dwg_to_dxf'].append(step_time)
        
        if success:
            self.logger.info(f"DWG转换DXF成功: {message} (耗时: {step_time:.2f}秒)")
            return True
        else:
            self.logger.error(f"DWG转换DXF失败: {message} (耗时: {step_time:.2f}秒)")
            return False
    
    def process_dxf_filter(self, input_file, output_file):
        """步骤2: 过滤DXF图层"""
        step_start = time.time()
        self.logger.info(f"步骤2: 过滤DXF图层 - {os.path.basename(input_file)}")
        success, message, _ = filter_dxf_layers(input_file, output_file)
        step_time = time.time() - step_start
        self.processing_stats['step_times']['dxf_filter'].append(step_time)
        
        if success:
            self.logger.info(f"DXF图层过滤成功: {message} (耗时: {step_time:.2f}秒)")
            return True
        else:
            self.logger.error(f"DXF图层过滤失败: {message} (耗时: {step_time:.2f}秒)")
            return False
    
    def process_dxf_to_svg(self, input_file, output_file):
        """步骤3: 将DXF转换为SVG"""
        step_start = time.time()
        self.logger.info(f"步骤3: 将DXF转换为SVG - {os.path.basename(input_file)}")
        target_size = 4000  # 默认分辨率
        success, message = dxf_to_svg(input_file, output_file, target_size, self.config)
        step_time = time.time() - step_start
        self.processing_stats['step_times']['dxf_to_svg'].append(step_time)
        
        if success:
            self.logger.info(f"DXF转换SVG成功: {message} (耗时: {step_time:.2f}秒)")
            return True
        else:
            self.logger.error(f"DXF转换SVG失败: {message} (耗时: {step_time:.2f}秒)")
            return False
    
    def process_svg_to_png(self, input_file, output_file):
        """步骤4: 将SVG转换为PNG"""
        step_start = time.time()
        self.logger.info(f"步骤4: 将SVG转换为PNG - {os.path.basename(input_file)}")
        try:
            target_output_size = (4000, 4000)  # 默认目标PNG尺寸
            line_thickness = 1  # 线条粗细
            
            grid = svg_to_occupancy_grid(
                input_file,
                output_size=target_output_size,
                line_thickness=line_thickness
            )
            save_occupancy_grid(grid, output_file)
            step_time = time.time() - step_start
            self.processing_stats['step_times']['svg_to_png'].append(step_time)
            self.logger.info(f"SVG转换PNG成功: {output_file} (耗时: {step_time:.2f}秒)")
            return True
        except Exception as e:
            step_time = time.time() - step_start
            self.processing_stats['step_times']['svg_to_png'].append(step_time)
            self.logger.error(f"SVG转换PNG失败: {str(e)} (耗时: {step_time:.2f}秒)")
            return False
    
    def get_file_size_mb(self, file_path):
        """获取文件大小（MB）"""
        try:
            size_bytes = os.path.getsize(file_path)
            return size_bytes / (1024 * 1024)
        except:
            return 0
    
    def process_single_file(self, dwg_file, output_dir, skip_steps=None):
        """处理单个DWG文件的完整流程"""
        if skip_steps is None:
            skip_steps = []
            
        filename = os.path.basename(dwg_file)
        basename = os.path.splitext(filename)[0]
        
        # 记录文件大小
        file_size = self.get_file_size_mb(dwg_file)
        self.processing_stats['file_sizes'].append(file_size)
        
        # 创建必要的目录
        dxf_dir = os.path.join(output_dir, "dxf/original")
        filtered_dxf_dir = os.path.join(output_dir, "dxf/auto_filter")
        svg_dir = os.path.join(output_dir, "img/svg_auto_filter")
        png_dir = os.path.join(output_dir, "img/png_auto_filter")
        
        os.makedirs(dxf_dir, exist_ok=True)
        os.makedirs(filtered_dxf_dir, exist_ok=True)
        os.makedirs(svg_dir, exist_ok=True)
        os.makedirs(png_dir, exist_ok=True)
        
        # 定义各步骤的输入输出文件
        dxf_file = os.path.join(dxf_dir, f"{basename}.dxf")
        filtered_dxf_file = os.path.join(filtered_dxf_dir, f"{basename}.dxf")
        svg_file = os.path.join(svg_dir, f"{basename}.svg")
        png_file = os.path.join(png_dir, f"{basename}.png")
        
        # 记录开始时间
        start_time = time.time()
        self.logger.info(f"开始处理文件: {filename} (大小: {file_size:.2f}MB)")
        
        success = True
        
        # 步骤1: DWG -> DXF
        if 1 not in skip_steps:
            if not self.process_dwg_to_dxf(dwg_file, dxf_file):
                success = False
        else:
            self.logger.info("跳过步骤1: DWG -> DXF")
        
        # 步骤2: DXF -> 过滤后的DXF
        if success and 2 not in skip_steps:
            if not self.process_dxf_filter(dxf_file, filtered_dxf_file):
                success = False
        elif 2 in skip_steps:
            self.logger.info("跳过步骤2: DXF过滤")
        
        # 步骤3: 过滤后的DXF -> SVG
        if success and 3 not in skip_steps:
            if not self.process_dxf_to_svg(filtered_dxf_file, svg_file):
                success = False
        elif 3 in skip_steps:
            self.logger.info("跳过步骤3: DXF -> SVG")
        
        # 步骤4: SVG -> PNG
        if success and 4 not in skip_steps:
            if not self.process_svg_to_png(svg_file, png_file):
                success = False
        elif 4 in skip_steps:
            self.logger.info("跳过步骤4: SVG -> PNG")
        
        # 记录处理时间
        elapsed_time = time.time() - start_time
        self.processing_stats['file_times'].append(elapsed_time)
        
        if success:
            self.logger.info(f"文件 {filename} 处理完成，耗时: {elapsed_time:.2f} 秒")
            self.processing_stats['successful_files'] += 1
        else:
            self.logger.error(f"文件 {filename} 处理失败，耗时: {elapsed_time:.2f} 秒")
            self.processing_stats['failed_files'] += 1
            
        self.processing_stats['total_files'] += 1
        return success
    
    def print_statistics(self):
        """打印详细的处理统计信息"""
        stats = self.processing_stats
        
        self.logger.info("=" * 80)
        self.logger.info("处理统计报告")
        self.logger.info("=" * 80)
        
        # 总体统计
        total_time = stats['end_time'] - stats['start_time'] if stats['end_time'] and stats['start_time'] else 0
        self.logger.info(f"总处理时间: {total_time:.2f} 秒 ({total_time/60:.2f} 分钟)")
        self.logger.info(f"总文件数: {stats['total_files']}")
        self.logger.info(f"成功处理: {stats['successful_files']}")
        self.logger.info(f"处理失败: {stats['failed_files']}")
        self.logger.info(f"成功率: {(stats['successful_files']/stats['total_files']*100):.1f}%")
        
        # 平均处理时间
        if stats['file_times']:
            avg_time = statistics.mean(stats['file_times'])
            min_time = min(stats['file_times'])
            max_time = max(stats['file_times'])
            median_time = statistics.median(stats['file_times'])
            
            self.logger.info(f"\n单文件处理时间统计:")
            self.logger.info(f"  平均时间: {avg_time:.2f} 秒")
            self.logger.info(f"  中位数时间: {median_time:.2f} 秒")
            self.logger.info(f"  最快处理: {min_time:.2f} 秒")
            self.logger.info(f"  最慢处理: {max_time:.2f} 秒")
        
        # 各步骤平均时间
        self.logger.info(f"\n各步骤平均处理时间:")
        for step, times in stats['step_times'].items():
            if times:
                avg_step_time = statistics.mean(times)
                self.logger.info(f"  {step}: {avg_step_time:.2f} 秒")
        
        # 文件大小统计
        if stats['file_sizes']:
            avg_size = statistics.mean(stats['file_sizes'])
            min_size = min(stats['file_sizes'])
            max_size = max(stats['file_sizes'])
            
            self.logger.info(f"\n文件大小统计:")
            self.logger.info(f"  平均大小: {avg_size:.2f} MB")
            self.logger.info(f"  最小文件: {min_size:.2f} MB")
            self.logger.info(f"  最大文件: {max_size:.2f} MB")
        
        self.logger.info("=" * 80)
    
    def batch_process(self, input_dir, output_dir, skip_steps=None):
        """批量处理目录中的所有DWG文件"""
        if skip_steps is None:
            skip_steps = []
            
        # 记录开始时间
        self.processing_stats['start_time'] = time.time()
            
        # 查找所有DWG文件
        dwg_files = list(Path(input_dir).glob("*.dwg")) + list(Path(input_dir).glob("*.DWG"))
        total_files = len(dwg_files)
        
        if total_files == 0:
            self.logger.warning(f"在目录 {input_dir} 中未找到任何DWG文件")
            return
        
        self.logger.info(f"找到 {total_files} 个DWG文件，开始批量处理...")
        self.logger.info(f"输出目录: {output_dir}")
        
        for i, dwg_file in enumerate(dwg_files, 1):
            self.logger.info(f"\n处理文件 {i}/{total_files}: {dwg_file.name}")
            
            self.process_single_file(str(dwg_file), output_dir, skip_steps)
            
            # 显示进度和当前统计
            progress = (i / total_files) * 100
            current_avg = statistics.mean(self.processing_stats['file_times']) if self.processing_stats['file_times'] else 0
            self.logger.info(f"进度: {progress:.1f}% ({i}/{total_files}) | 当前平均耗时: {current_avg:.2f}秒")
        
        # 记录结束时间
        self.processing_stats['end_time'] = time.time()
        
        # 打印统计信息
        self.print_statistics()


def main():
    parser = argparse.ArgumentParser(description='CAD预处理集成工具 - 从DWG到PNG的完整流程')
    parser.add_argument('--input', type=str, required=True,
                        help='输入DWG文件或包含DWG文件的目录')
    parser.add_argument('--output-dir', type=str, required=True,
                        help='输出目录，将在此目录下创建dxf和img子目录')
    parser.add_argument('--config', type=str, default=None,
                        help='配置文件路径，默认使用项目配置')
    parser.add_argument('--skip-steps', type=str, default='',
                        help='跳过的步骤，用逗号分隔，例如"1,2"表示跳过步骤1和2')
    parser.add_argument('--log-level', type=str, default='INFO',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                        help='日志级别')
    
    args = parser.parse_args()
    
    # 设置日志级别
    log_level = getattr(logging, args.log_level)
    
    # 解析跳过的步骤
    skip_steps = [int(s) for s in args.skip_steps.split(',') if s.strip().isdigit()]
    
    # 创建预处理器
    preprocessor = CADPreprocessor(config_path=args.config, log_level=log_level)
    
    # 检查输入是文件还是目录
    input_path = Path(args.input)
    if input_path.is_file() and input_path.suffix.lower() == '.dwg':
        # 处理单个文件
        preprocessor.process_single_file(str(input_path), args.output_dir, skip_steps)
    elif input_path.is_dir():
        # 批量处理目录
        preprocessor.batch_process(str(input_path), args.output_dir, skip_steps)
    else:
        print(f"错误: 输入 {args.input} 不是有效的DWG文件或目录")
        sys.exit(1)


if __name__ == "__main__":
    main()

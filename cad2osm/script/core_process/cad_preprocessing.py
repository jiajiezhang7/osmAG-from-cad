#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 集成CAD预处理流程脚本
# 作者: Cascade AI 辅助 Jiajie Zhang
# 创建日期: 2025-05-13

import os
import sys
import argparse
import yaml
import logging
import time
from pathlib import Path
from datetime import datetime

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
        self.logger.info(f"步骤1: 将DWG转换为DXF - {os.path.basename(input_file)}")
        success, message = self.oda_converter.convert_file(input_file, output_file)
        if success:
            self.logger.info(f"DWG转换DXF成功: {message}")
            return True
        else:
            self.logger.error(f"DWG转换DXF失败: {message}")
            return False
    
    def process_dxf_filter(self, input_file, output_file):
        """步骤2: 过滤DXF图层"""
        self.logger.info(f"步骤2: 过滤DXF图层 - {os.path.basename(input_file)}")
        success, message, _ = filter_dxf_layers(input_file, output_file)
        if success:
            self.logger.info(f"DXF图层过滤成功: {message}")
            return True
        else:
            self.logger.error(f"DXF图层过滤失败: {message}")
            return False
    
    def process_dxf_to_svg(self, input_file, output_file):
        """步骤3: 将DXF转换为SVG"""
        self.logger.info(f"步骤3: 将DXF转换为SVG - {os.path.basename(input_file)}")
        target_size = 4000  # 默认分辨率
        success, message = dxf_to_svg(input_file, output_file, target_size, self.config)
        if success:
            self.logger.info(f"DXF转换SVG成功: {message}")
            return True
        else:
            self.logger.error(f"DXF转换SVG失败: {message}")
            return False
    
    def process_svg_to_png(self, input_file, output_file):
        """步骤4: 将SVG转换为PNG"""
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
            self.logger.info(f"SVG转换PNG成功: {output_file}")
            return True
        except Exception as e:
            self.logger.error(f"SVG转换PNG失败: {str(e)}")
            return False
    
    def process_single_file(self, dwg_file, output_dir, skip_steps=None):
        """处理单个DWG文件的完整流程"""
        if skip_steps is None:
            skip_steps = []
            
        filename = os.path.basename(dwg_file)
        basename = os.path.splitext(filename)[0]
        
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
        self.logger.info(f"开始处理文件: {filename}")
        
        # 步骤1: DWG -> DXF
        if 1 not in skip_steps:
            if not self.process_dwg_to_dxf(dwg_file, dxf_file):
                return False
        else:
            self.logger.info("跳过步骤1: DWG -> DXF")
        
        # 步骤2: DXF -> 过滤后的DXF
        if 2 not in skip_steps:
            if not self.process_dxf_filter(dxf_file, filtered_dxf_file):
                return False
        else:
            self.logger.info("跳过步骤2: DXF过滤")
        
        # 步骤3: 过滤后的DXF -> SVG
        if 3 not in skip_steps:
            if not self.process_dxf_to_svg(filtered_dxf_file, svg_file):
                return False
        else:
            self.logger.info("跳过步骤3: DXF -> SVG")
        
        # 步骤4: SVG -> PNG
        if 4 not in skip_steps:
            if not self.process_svg_to_png(svg_file, png_file):
                return False
        else:
            self.logger.info("跳过步骤4: SVG -> PNG")
        
        # 记录处理时间
        elapsed_time = time.time() - start_time
        self.logger.info(f"文件 {filename} 处理完成，耗时: {elapsed_time:.2f} 秒")
        
        return True
    
    def batch_process(self, input_dir, output_dir, skip_steps=None):
        """批量处理目录中的所有DWG文件"""
        if skip_steps is None:
            skip_steps = []
            
        # 查找所有DWG文件
        dwg_files = list(Path(input_dir).glob("*.dwg"))
        total_files = len(dwg_files)
        
        if total_files == 0:
            self.logger.warning(f"在目录 {input_dir} 中未找到任何DWG文件")
            return
        
        self.logger.info(f"找到 {total_files} 个DWG文件，开始批量处理...")
        
        success_count = 0
        fail_count = 0
        
        for i, dwg_file in enumerate(dwg_files, 1):
            self.logger.info(f"处理文件 {i}/{total_files}: {dwg_file.name}")
            
            if self.process_single_file(str(dwg_file), output_dir, skip_steps):
                success_count += 1
            else:
                fail_count += 1
            
            # 显示进度
            progress = (i / total_files) * 100
            self.logger.info(f"进度: {progress:.1f}% ({i}/{total_files})")
        
        self.logger.info("批量处理完成")
        self.logger.info(f"成功处理: {success_count}/{total_files}")
        self.logger.info(f"处理失败: {fail_count}/{total_files}")


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

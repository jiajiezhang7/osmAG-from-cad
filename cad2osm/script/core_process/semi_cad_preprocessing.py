#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# filtered_dxf.dxf到PNG的转换脚本
# 作者: Jiajie Zhang
# 创建日期: 2025-05-14

import os
import sys
import argparse
import yaml
import logging
import time
from pathlib import Path
from datetime import datetime

# 导入所需的处理模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from dxf2svg import dxf_to_svg, load_yaml_config
from svg2png import svg_to_occupancy_grid, save_occupancy_grid

class FilteredDxfToPngConverter:
    def __init__(self, config_path=None, log_level=logging.INFO):
        """初始化转换器"""
        self.setup_logging(log_level)
        self.load_config(config_path)

    def setup_logging(self, log_level):
        """设置日志配置"""
        self.logger = logging.getLogger('FilteredDxfToPngConverter')
        self.logger.setLevel(log_level)

        # 创建日志目录
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)

        # 设置日志文件
        log_file = log_dir / f'filtered_dxf_to_png_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

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

    def process_dxf_to_svg(self, input_file, output_file):
        """步骤1: 将DXF转换为SVG"""
        self.logger.info(f"步骤1: 将DXF转换为SVG - {os.path.basename(input_file)}")
        target_size = 4000  # 默认分辨率
        success, message = dxf_to_svg(input_file, output_file, target_size, self.config)
        if success:
            self.logger.info(f"DXF转换SVG成功: {message}")
            return True
        else:
            self.logger.error(f"DXF转换SVG失败: {message}")
            return False

    def process_svg_to_png(self, input_file, output_file):
        """步骤2: 将SVG转换为PNG"""
        self.logger.info(f"步骤2: 将SVG转换为PNG - {os.path.basename(input_file)}")
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

    def process_file(self, dxf_file, output_dir):
        """处理单个filtered_dxf.dxf文件的完整流程"""
        filename = os.path.basename(dxf_file)
        basename = os.path.splitext(filename)[0]

        # 创建标准的目录结构，与完整流程保持一致
        # 在用户指定的输出目录下创建子目录
        svg_dir = os.path.join(output_dir, "img", "svg_manual_filter")
        png_dir = os.path.join(output_dir, "img", "png_manual_filter")

        # 创建必要的目录
        os.makedirs(svg_dir, exist_ok=True)
        os.makedirs(png_dir, exist_ok=True)

        # 定义各步骤的输出文件
        svg_file = os.path.join(svg_dir, f"{basename}.svg")
        png_file = os.path.join(png_dir, f"{basename}.png")

        # 记录开始时间
        start_time = time.time()
        self.logger.info(f"开始处理文件: {filename}")

        # 步骤1: DXF -> SVG
        if not self.process_dxf_to_svg(dxf_file, svg_file):
            return False

        # 步骤2: SVG -> PNG
        if not self.process_svg_to_png(svg_file, png_file):
            return False

        # 记录处理时间
        elapsed_time = time.time() - start_time
        self.logger.info(f"文件 {filename} 处理完成，耗时: {elapsed_time:.2f} 秒")

        return True

    def batch_process(self, input_dir, output_dir):
        """批量处理目录中的所有filtered_dxf.dxf文件"""
        # 查找所有DXF文件
        dxf_files = list(Path(input_dir).glob("*.dxf"))
        total_files = len(dxf_files)

        if total_files == 0:
            self.logger.warning(f"在目录 {input_dir} 中未找到任何DXF文件")
            return

        self.logger.info(f"找到 {total_files} 个DXF文件，开始批量处理...")

        success_count = 0
        fail_count = 0

        for i, dxf_file in enumerate(dxf_files, 1):
            self.logger.info(f"处理文件 {i}/{total_files}: {dxf_file.name}")

            if self.process_file(str(dxf_file), output_dir):
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
    parser = argparse.ArgumentParser(description='filtered_dxf.dxf到PNG转换工具')
    parser.add_argument('--input', type=str, required=True,
                        help='输入filtered_dxf.dxf文件或包含filtered_dxf.dxf文件的目录')
    parser.add_argument('--output-dir', type=str, required=True,
                        help='输出根目录，将在此目录下创建img/png_manual_filter和img/svg_manual_filter子目录')
    parser.add_argument('--config', type=str, default=None,
                        help='配置文件路径，默认使用项目配置')
    parser.add_argument('--log-level', type=str, default='INFO',
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                        help='日志级别')

    args = parser.parse_args()

    # 设置日志级别
    log_level = getattr(logging, args.log_level)

    # 创建转换器
    converter = FilteredDxfToPngConverter(config_path=args.config, log_level=log_level)

    # 检查输入是文件还是目录
    input_path = Path(args.input)
    if input_path.is_file() and input_path.suffix.lower() == '.dxf':
        # 处理单个文件
        converter.process_file(str(input_path), args.output_dir)
    elif input_path.is_dir():
        # 批量处理目录
        converter.batch_process(str(input_path), args.output_dir)
    else:
        print(f"错误: 输入 {args.input} 不是有效的DXF文件或目录")
        sys.exit(1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAD预处理模块

此模块负责实现CAD预处理功能，包括DWG到DXF的转换、DXF过滤、DXF到SVG的转换和SVG到PNG的转换。
"""

import os
import sys
import yaml
import logging
from pathlib import Path
from PyQt5.QtCore import QObject, pyqtSignal, QThread

# 添加核心处理脚本路径
sys.path.append(str(Path(__file__).parent.parent.parent / 'script' / 'core_process'))

# 导入核心处理模块
try:
    from compact_cad_preprocessing import CADPreprocessor
    from semi_cad_preprocessing import FilteredDxfToPngConverter
except ImportError as e:
    print(f"导入核心处理模块失败: {e}")

class ProcessWorker(QThread):
    """
    处理工作线程，用于在后台执行CAD预处理任务
    """
    progress_updated = pyqtSignal(int, str)  # 进度更新信号
    step_progress_updated = pyqtSignal(int, str)  # 步骤进度更新信号
    process_completed = pyqtSignal(bool, str)  # 处理完成信号
    log_message = pyqtSignal(str)  # 日志消息信号

    def __init__(self, mode, input_path, output_dir, config_path=None, params=None):
        super().__init__()
        self.mode = mode  # 'full' 或 'semi'
        self.input_path = input_path
        self.output_dir = output_dir
        self.config_path = config_path
        self.params = params or {}
        self.is_cancelled = False

    def run(self):
        """
        执行处理任务
        """
        try:
            if self.mode == 'full':
                self.run_full_process()
            elif self.mode == 'semi':
                self.run_semi_process()
            else:
                self.process_completed.emit(False, f"未知的处理模式: {self.mode}")
        except Exception as e:
            self.log_message.emit(f"处理过程中发生错误: {str(e)}")
            self.process_completed.emit(False, f"处理失败: {str(e)}")

    def run_full_process(self):
        """
        执行完整处理流程
        """
        self.log_message.emit("开始执行完整CAD预处理流程...")

        # 创建自定义日志处理器，将日志消息转发到GUI
        log_handler = GUILogHandler(self.log_message)
        log_handler.setLevel(logging.INFO)

        # 创建CAD预处理器
        preprocessor = CADPreprocessor(config_path=self.config_path, log_level=logging.INFO)

        # 添加自定义日志处理器
        preprocessor.logger.addHandler(log_handler)

        # 添加进度回调
        def progress_callback(progress, step_name=None):
            self.progress_updated.emit(progress, step_name)

        def step_progress_callback(progress, step_name=None):
            self.step_progress_updated.emit(progress, step_name)

        # 获取跳过步骤列表
        skip_steps = []
        if self.params.get('skip_dwg_to_dxf', False):
            skip_steps.append(1)
        if self.params.get('skip_dxf_filter', False):
            skip_steps.append(2)
        if self.params.get('skip_dxf_to_svg', False):
            skip_steps.append(3)
        if self.params.get('skip_svg_to_png', False):
            skip_steps.append(4)

        # 自定义进度监控
        total_steps = 4 - len(skip_steps)
        current_step = 0
        result_files = []

        # 监控处理步骤的进度
        def monitor_step_progress(step_name, step_index):
            nonlocal current_step
            current_step = step_index
            self.progress_updated.emit(int((current_step / total_steps) * 100), step_name)
            self.step_progress_updated.emit(0, step_name)

        # 执行处理
        if os.path.isfile(self.input_path):
            # 单文件处理
            self.log_message.emit(f"处理单个文件: {os.path.basename(self.input_path)}")

            # 处理步骤名称
            step_names = {
                1: "DWG转DXF",
                2: "DXF过滤",
                3: "DXF转SVG",
                4: "SVG转PNG"
            }

            # 处理前发送初始进度
            self.progress_updated.emit(0, "准备处理")

            # 修改process_single_file方法的调用，添加进度监控
            filename = os.path.basename(self.input_path)
            basename = os.path.splitext(filename)[0]

            # 创建必要的目录
            dxf_dir = os.path.join(self.output_dir, "dxf/original")
            filtered_dxf_dir = os.path.join(self.output_dir, "dxf/auto_filter")
            svg_dir = os.path.join(self.output_dir, "img/svg_auto_filter")
            png_dir = os.path.join(self.output_dir, "img/png_auto_filter")

            os.makedirs(dxf_dir, exist_ok=True)
            os.makedirs(filtered_dxf_dir, exist_ok=True)
            os.makedirs(svg_dir, exist_ok=True)
            os.makedirs(png_dir, exist_ok=True)

            # 定义各步骤的输入输出文件
            dxf_file = os.path.join(dxf_dir, f"{basename}.dxf")
            filtered_dxf_file = os.path.join(filtered_dxf_dir, f"{basename}.dxf")
            svg_file = os.path.join(svg_dir, f"{basename}.svg")
            png_file = os.path.join(png_dir, f"{basename}.png")

            success = True
            step_count = 0

            # 步骤1: DWG -> DXF
            if 1 not in skip_steps:
                monitor_step_progress("DWG转DXF", step_count)
                if not preprocessor.process_dwg_to_dxf(self.input_path, dxf_file):
                    success = False
                else:
                    result_files.append(dxf_file)
                    step_count += 1
                    self.progress_updated.emit(int((step_count / total_steps) * 100), None)

            # 步骤2: DXF -> 过滤后的DXF
            if success and 2 not in skip_steps:
                monitor_step_progress("DXF过滤", step_count)
                if not preprocessor.process_dxf_filter(dxf_file, filtered_dxf_file):
                    success = False
                else:
                    result_files.append(filtered_dxf_file)
                    step_count += 1
                    self.progress_updated.emit(int((step_count / total_steps) * 100), None)

            # 步骤3: 过滤后的DXF -> SVG
            if success and 3 not in skip_steps:
                monitor_step_progress("DXF转SVG", step_count)
                if not preprocessor.process_dxf_to_svg(filtered_dxf_file, svg_file):
                    success = False
                else:
                    result_files.append(svg_file)
                    step_count += 1
                    self.progress_updated.emit(int((step_count / total_steps) * 100), None)

            # 步骤4: SVG -> PNG
            if success and 4 not in skip_steps:
                monitor_step_progress("SVG转PNG", step_count)
                if not preprocessor.process_svg_to_png(svg_file, png_file):
                    success = False
                else:
                    result_files.append(png_file)
                    step_count += 1
                    self.progress_updated.emit(int((step_count / total_steps) * 100), None)

            # 处理完成
            if success:
                self.progress_updated.emit(100, "处理完成")
                self.step_progress_updated.emit(100, "")
                self.process_completed.emit(True, "处理完成")
            else:
                self.process_completed.emit(False, "处理失败")

        elif os.path.isdir(self.input_path):
            # 批量处理目录
            self.log_message.emit(f"批量处理目录: {self.input_path}")

            # 查找所有DWG文件
            dwg_files = list(Path(self.input_path).glob("*.dwg"))
            total_files = len(dwg_files)

            if total_files == 0:
                self.log_message.emit(f"在目录 {self.input_path} 中未找到任何DWG文件")
                self.process_completed.emit(False, "未找到DWG文件")
                return

            self.log_message.emit(f"找到 {total_files} 个DWG文件，开始批量处理...")

            success_count = 0
            fail_count = 0

            for i, dwg_file in enumerate(dwg_files, 1):
                if self.is_cancelled:
                    self.log_message.emit("处理已取消")
                    self.process_completed.emit(False, "处理已取消")
                    return

                self.log_message.emit(f"处理文件 {i}/{total_files}: {dwg_file.name}")

                # 更新总进度
                progress = int(((i - 1) / total_files) * 100)
                self.progress_updated.emit(progress, f"处理文件 {i}/{total_files}")

                # 处理单个文件
                if preprocessor.process_single_file(str(dwg_file), self.output_dir, skip_steps):
                    success_count += 1
                else:
                    fail_count += 1

                # 更新进度
                progress = int((i / total_files) * 100)
                self.progress_updated.emit(progress, f"进度: {progress}% ({i}/{total_files})")

            self.log_message.emit("批量处理完成")
            self.log_message.emit(f"成功处理: {success_count}/{total_files}")
            self.log_message.emit(f"处理失败: {fail_count}/{total_files}")

            self.process_completed.emit(True, f"批量处理完成，成功: {success_count}，失败: {fail_count}")
        else:
            self.process_completed.emit(False, f"输入路径不存在: {self.input_path}")

    def run_semi_process(self):
        """
        执行半自动处理流程
        """
        self.log_message.emit("开始执行半自动CAD预处理流程...")

        # 创建自定义日志处理器，将日志消息转发到GUI
        log_handler = GUILogHandler(self.log_message)
        log_handler.setLevel(logging.INFO)

        # 创建DXF到PNG转换器
        converter = FilteredDxfToPngConverter(config_path=self.config_path, log_level=logging.INFO)

        # 添加自定义日志处理器
        converter.logger.addHandler(log_handler)

        # 获取参数
        resolution = self.params.get('resolution', 4000)
        padding_ratio = self.params.get('padding_ratio', 0.03)
        line_thickness = self.params.get('line_thickness', 1)
        is_batch = self.params.get('is_batch', False)

        # 执行处理
        if os.path.isfile(self.input_path):
            # 单文件处理
            self.log_message.emit(f"处理单个文件: {os.path.basename(self.input_path)}")

            # 处理前发送初始进度
            self.progress_updated.emit(0, "准备处理")

            # 定义处理步骤
            total_steps = 2  # DXF转SVG和SVG转PNG
            result_files = []

            # 获取文件名
            filename = os.path.basename(self.input_path)
            basename = os.path.splitext(filename)[0]

            # 创建必要的目录，与脚本保持一致
            svg_dir = os.path.join(self.output_dir, "img", "svg_manual_filter")
            png_dir = os.path.join(self.output_dir, "img", "png_manual_filter")

            os.makedirs(svg_dir, exist_ok=True)
            os.makedirs(png_dir, exist_ok=True)

            # 定义输出文件
            svg_file = os.path.join(svg_dir, f"{basename}.svg")
            png_file = os.path.join(png_dir, f"{basename}.png")

            # 步骤1: DXF -> SVG
            self.progress_updated.emit(0, "DXF转SVG")
            self.step_progress_updated.emit(0, "DXF转SVG")

            success = converter.dxf_to_svg(self.input_path, svg_file, resolution, padding_ratio)
            if success:
                result_files.append(svg_file)
                self.progress_updated.emit(50, None)
                self.step_progress_updated.emit(100, None)
            else:
                self.process_completed.emit(False, "DXF转SVG失败")
                return

            # 步骤2: SVG -> PNG
            self.progress_updated.emit(50, "SVG转PNG")
            self.step_progress_updated.emit(0, "SVG转PNG")

            success = converter.svg_to_png(svg_file, png_file, line_thickness)
            if success:
                result_files.append(png_file)
                self.progress_updated.emit(100, "处理完成")
                self.step_progress_updated.emit(100, None)
                self.process_completed.emit(True, "处理完成")
            else:
                self.process_completed.emit(False, "SVG转PNG失败")

        elif os.path.isdir(self.input_path):
            # 批量处理目录
            self.log_message.emit(f"批量处理目录: {self.input_path}")

            # 查找所有DXF文件
            dxf_files = list(Path(self.input_path).glob("*.dxf"))
            total_files = len(dxf_files)

            if total_files == 0:
                self.log_message.emit(f"在目录 {self.input_path} 中未找到任何DXF文件")
                self.process_completed.emit(False, "未找到DXF文件")
                return

            self.log_message.emit(f"找到 {total_files} 个DXF文件，开始批量处理...")

            success_count = 0
            fail_count = 0

            for i, dxf_file in enumerate(dxf_files, 1):
                if self.is_cancelled:
                    self.log_message.emit("处理已取消")
                    self.process_completed.emit(False, "处理已取消")
                    return

                self.log_message.emit(f"处理文件 {i}/{total_files}: {dxf_file.name}")

                # 更新总进度
                progress = int(((i - 1) / total_files) * 100)
                self.progress_updated.emit(progress, f"处理文件 {i}/{total_files}")

                # 处理单个文件
                if converter.process_file(str(dxf_file), self.output_dir):
                    success_count += 1
                else:
                    fail_count += 1

                # 更新进度
                progress = int((i / total_files) * 100)
                self.progress_updated.emit(progress, f"进度: {progress}% ({i}/{total_files})")

            self.log_message.emit("批量处理完成")
            self.log_message.emit(f"成功处理: {success_count}/{total_files}")
            self.log_message.emit(f"处理失败: {fail_count}/{total_files}")

            self.process_completed.emit(True, f"批量处理完成，成功: {success_count}，失败: {fail_count}")
        else:
            self.process_completed.emit(False, f"输入路径不存在: {self.input_path}")

    def cancel(self):
        """
        取消处理任务
        """
        self.is_cancelled = True
        self.log_message.emit("正在取消处理任务...")

class GUILogHandler(logging.Handler):
    """
    自定义日志处理器，将日志消息转发到GUI
    """
    def __init__(self, log_signal):
        super().__init__()
        self.log_signal = log_signal

    def emit(self, record):
        log_message = self.format(record)
        self.log_signal.emit(log_message)

class ProcessModule(QObject):
    """
    CAD预处理模块，负责协调GUI和处理逻辑
    """
    # 定义信号
    progress_updated = pyqtSignal(int, str)  # 进度更新信号
    step_progress_updated = pyqtSignal(int, str)  # 步骤进度更新信号
    process_completed = pyqtSignal(bool, str)  # 处理完成信号
    log_message = pyqtSignal(str)  # 日志消息信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None

    def start_full_process(self, input_path, output_dir, config_path=None, params=None):
        """
        启动完整处理流程

        参数:
            input_path: 输入文件或目录路径
            output_dir: 输出目录路径
            config_path: 配置文件路径
            params: 处理参数字典
        """
        # 创建并启动工作线程
        self.worker = ProcessWorker('full', input_path, output_dir, config_path, params)
        self.connect_worker_signals()
        self.worker.start()

    def start_semi_process(self, input_path, output_dir, config_path=None, params=None):
        """
        启动半自动处理流程

        参数:
            input_path: 输入文件或目录路径
            output_dir: 输出目录路径
            config_path: 配置文件路径
            params: 处理参数字典
        """
        # 创建并启动工作线程
        self.worker = ProcessWorker('semi', input_path, output_dir, config_path, params)
        self.connect_worker_signals()
        self.worker.start()

    def connect_worker_signals(self):
        """
        连接工作线程的信号
        """
        if self.worker:
            self.worker.progress_updated.connect(self.progress_updated)
            self.worker.step_progress_updated.connect(self.step_progress_updated)
            self.worker.process_completed.connect(self.process_completed)
            self.worker.log_message.connect(self.log_message)

    def cancel_processing(self):
        """
        取消处理任务
        """
        if self.worker and self.worker.isRunning():
            self.worker.is_cancelled = True
            self.log_message.emit("正在取消处理任务...")
            self.worker.wait()  # 等待线程结束

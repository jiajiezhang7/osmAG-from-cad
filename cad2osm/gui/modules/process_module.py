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
        
        # 执行处理
        if os.path.isfile(self.input_path):
            # 单文件处理
            self.log_message.emit(f"处理单个文件: {os.path.basename(self.input_path)}")
            success = preprocessor.process_single_file(self.input_path, self.output_dir, skip_steps)
            if success:
                self.process_completed.emit(True, "处理完成")
            else:
                self.process_completed.emit(False, "处理失败")
        elif os.path.isdir(self.input_path):
            # 批量处理目录
            self.log_message.emit(f"批量处理目录: {self.input_path}")
            preprocessor.batch_process(self.input_path, self.output_dir, skip_steps)
            self.process_completed.emit(True, "批量处理完成")
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
        
        # 执行处理
        if os.path.isfile(self.input_path):
            # 单文件处理
            self.log_message.emit(f"处理单个文件: {os.path.basename(self.input_path)}")
            success = converter.process_file(self.input_path, self.output_dir)
            if success:
                self.process_completed.emit(True, "处理完成")
            else:
                self.process_completed.emit(False, "处理失败")
        elif os.path.isdir(self.input_path):
            # 批量处理目录
            self.log_message.emit(f"批量处理目录: {self.input_path}")
            converter.batch_process(self.input_path, self.output_dir)
            self.process_completed.emit(True, "批量处理完成")
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
    
    def cancel_process(self):
        """
        取消处理任务
        """
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()  # 等待线程结束

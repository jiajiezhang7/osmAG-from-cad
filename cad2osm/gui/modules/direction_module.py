#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
方向校正模块

此模块负责实现方向校正功能，用于校正OSM文件中多边形的方向。
"""

import os
import sys
import logging
from pathlib import Path
from PyQt5.QtCore import QObject, pyqtSignal, QThread

# 添加方向校正脚本路径
sys.path.append(str(Path(__file__).parent.parent.parent / 'script' / 'functions'))

# 导入方向校正模块
try:
    from direction_correct import correct_way_direction
except ImportError as e:
    print(f"导入方向校正模块失败: {e}")

class DirectionWorker(QThread):
    """
    方向校正工作线程，用于在后台执行方向校正任务
    """
    progress_updated = pyqtSignal(int, str)  # 进度更新信号
    process_completed = pyqtSignal(bool, str)  # 处理完成信号
    log_message = pyqtSignal(str)  # 日志消息信号
    stats_updated = pyqtSignal(dict)  # 统计信息更新信号

    def __init__(self, osm_path, output_path):
        super().__init__()
        self.osm_path = osm_path
        self.output_path = output_path
        self.is_cancelled = False

    def run(self):
        """
        执行方向校正任务
        """
        try:
            self.correct_direction()
        except Exception as e:
            self.log_message.emit(f"处理过程中发生错误: {str(e)}")
            self.process_completed.emit(False, f"处理失败: {str(e)}")

    def correct_direction(self):
        """
        校正OSM文件中多边形的方向
        """
        self.log_message.emit("开始执行方向校正流程...")
        self.progress_updated.emit(10, "正在加载OSM文件...")

        # 创建输出目录（如果不存在）
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

        # 自定义处理函数，用于捕获原始函数的输出并发送日志消息
        def process_callback(message):
            self.log_message.emit(message)

            # 提取统计信息
            if "共处理" in message and "反转了" in message:
                try:
                    parts = message.split("共处理")[1].split("个way")[0].strip()
                    processed_ways = int(parts)

                    parts = message.split("反转了")[1].split("个way")[0].strip()
                    reversed_ways = int(parts)

                    stats = {
                        'processed_ways': processed_ways,
                        'reversed_ways': reversed_ways
                    }
                    self.stats_updated.emit(stats)
                except Exception:
                    pass

        # 执行方向校正
        self.progress_updated.emit(30, "正在校正方向...")

        # 修改correct_way_direction函数，使其支持回调函数
        original_print = print
        try:
            # 替换print函数，将输出重定向到回调函数
            def custom_print(*args, **kwargs):
                message = " ".join(str(arg) for arg in args)
                process_callback(message)
                original_print(*args, **kwargs)

            # 替换全局print函数
            import builtins
            builtins.print = custom_print

            # 执行方向校正
            correct_way_direction(self.osm_path, self.output_path)

            self.progress_updated.emit(100, "方向校正完成")
            self.process_completed.emit(True, "方向校正完成")
        finally:
            # 恢复原始print函数
            builtins.print = original_print

    def cancel(self):
        """
        取消处理任务
        """
        self.is_cancelled = True
        self.log_message.emit("正在取消方向校正任务...")

class DirectionModule(QObject):
    """
    方向校正模块，负责协调GUI和处理逻辑
    """
    # 定义信号
    progress_updated = pyqtSignal(int, str)  # 进度更新信号
    process_completed = pyqtSignal(bool, str)  # 处理完成信号
    log_message = pyqtSignal(str)  # 日志消息信号
    stats_updated = pyqtSignal(dict)  # 统计信息更新信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None

    def start_correction(self, osm_path, output_path, progress_callback=None, completion_callback=None):
        """
        启动方向校正流程

        参数:
            osm_path: OSM文件路径
            output_path: 输出OSM文件路径
            progress_callback: 进度回调函数
            completion_callback: 完成回调函数
        """
        # 创建并启动工作线程
        self.worker = DirectionWorker(osm_path, output_path)
        self.connect_worker_signals()
        self.worker.start()

    def connect_worker_signals(self):
        """
        连接工作线程的信号
        """
        if self.worker:
            self.worker.progress_updated.connect(self.progress_updated)
            self.worker.process_completed.connect(self.process_completed)
            self.worker.log_message.connect(self.log_message)
            self.worker.stats_updated.connect(self.stats_updated)

    def cancel_correction(self):
        """
        取消方向校正任务
        """
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()  # 等待线程结束

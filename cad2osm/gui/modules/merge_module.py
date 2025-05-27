#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSM合并模块

此模块负责实现OSM合并功能，用于合并多个OSM文件。
"""

import os
import sys
import logging
from pathlib import Path
from PyQt5.QtCore import QObject, pyqtSignal, QThread

# 添加合并脚本路径
sys.path.append(str(Path(__file__).parent.parent.parent / 'script' / 'functions'))

# 导入合并模块
try:
    from merge_osm import merge_osm_files, find_matching_areas, calculate_offset, apply_offset, find_max_ids, update_ids, load_osm_file, save_osm_file
except ImportError as e:
    print(f"导入合并模块失败: {e}")

class MergeWorker(QThread):
    """
    合并工作线程，用于在后台执行OSM合并任务
    """
    progress_updated = pyqtSignal(int, str)  # 进度更新信号
    process_completed = pyqtSignal(bool, str)  # 处理完成信号
    log_message = pyqtSignal(str)  # 日志消息信号
    stats_updated = pyqtSignal(dict)  # 统计信息更新信号

    def __init__(self, ref_path, target_paths, output_path, params=None):
        super().__init__()
        self.ref_path = ref_path
        self.target_paths = target_paths
        self.output_path = output_path
        self.params = params or {}
        self.is_cancelled = False

    def run(self):
        """
        执行OSM合并任务
        """
        try:
            self.merge_osm_files()
        except Exception as e:
            self.log_message.emit(f"处理过程中发生错误: {str(e)}")
            self.process_completed.emit(False, f"处理失败: {str(e)}")

    def merge_osm_files(self):
        """
        合并OSM文件
        """
        self.log_message.emit("开始执行OSM合并流程...")

        # 获取参数
        area_type = self.params.get('area_type', '两者')
        offset_method = self.params.get('offset_method', '顶点平均')
        min_matches = self.params.get('min_matches', 2)

        # 转换区域类型参数
        if area_type == '电梯':
            area_type_param = 'elevator'
        elif area_type == '楼梯':
            area_type_param = 'stairs'
        else:  # '两者'
            area_type_param = 'both'

        # 加载参照文件
        self.log_message.emit(f"加载参照OSM文件: {os.path.basename(self.ref_path)}")
        ref_root, ref_tree = load_osm_file(self.ref_path)
        if not ref_root:
            self.process_completed.emit(False, "无法加载参照OSM文件")
            return

        # 查找参照文件中的最大ID
        ref_max_ids = find_max_ids(ref_root)

        # 更新进度
        self.progress_updated.emit(10, "参照文件加载完成")

        # 创建输出目录（如果不存在）
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

        # 依次处理每个目标文件
        current_tree = ref_tree
        total_files = len(self.target_paths)
        matched_areas_total = 0

        for i, target_path in enumerate(self.target_paths):
            if self.is_cancelled:
                self.process_completed.emit(False, "处理已取消")
                return

            # 更新进度
            progress = 10 + (i / total_files) * 80
            self.progress_updated.emit(int(progress), f"处理目标文件 {i+1}/{total_files}")

            # 加载目标文件
            self.log_message.emit(f"加载目标OSM文件: {os.path.basename(target_path)}")
            target_root, target_tree = load_osm_file(target_path)
            if not target_root:
                self.log_message.emit(f"警告: 无法加载目标OSM文件: {target_path}，跳过此文件")
                continue

            # 查找匹配区域
            self.log_message.emit(f"查找匹配区域 (类型: {area_type})...")

            # 查找参照文件中的区域
            if area_type_param == 'both':
                ref_elevators = find_matching_areas(ref_root, 'elevator')
                ref_stairs = find_matching_areas(ref_root, 'stairs')
                ref_areas = {**ref_elevators, **ref_stairs}
            else:
                ref_areas = find_matching_areas(ref_root, area_type_param)

            # 查找目标文件中的区域
            if area_type_param == 'both':
                target_elevators = find_matching_areas(target_root, 'elevator')
                target_stairs = find_matching_areas(target_root, 'stairs')
                target_areas = {**target_elevators, **target_stairs}
            else:
                target_areas = find_matching_areas(target_root, area_type_param)

            # 计算偏移量
            self.log_message.emit(f"计算偏移量 (方法: {offset_method})...")
            lat_offset, lon_offset, offset_details = calculate_offset(ref_areas, target_areas)

            # 检查是否有足够的匹配区域
            matched_areas = len(offset_details)
            matched_areas_total += matched_areas

            if matched_areas < min_matches:
                self.log_message.emit(f"警告: 匹配区域数量 ({matched_areas}) 小于最小要求 ({min_matches})，跳过此文件")
                continue

            # 更新统计信息
            stats = {
                'matched_areas': matched_areas_total,
                'lat_offset': lat_offset,
                'lon_offset': lon_offset
            }
            self.stats_updated.emit(stats)

            # 应用偏移量
            self.log_message.emit(f"应用偏移量 (纬度: {lat_offset:.8f}, 经度: {lon_offset:.8f})...")
            apply_offset(target_root, lat_offset, lon_offset)

            # 更新ID
            self.log_message.emit("更新ID以避免冲突...")
            target_root, id_mapping = update_ids(target_root, ref_max_ids)

            # 更新最大ID
            for element_type, max_id in find_max_ids(target_root).items():
                if max_id > ref_max_ids.get(element_type, 0):
                    ref_max_ids[element_type] = max_id

            # 合并文件
            self.log_message.emit("合并文件...")
            current_tree = merge_osm_files(ref_root, current_tree, target_root, target_tree)

            # 更新参照根节点
            ref_root = current_tree.getroot()

        # 保存最终结果
        if self.is_cancelled:
            self.process_completed.emit(False, "处理已取消")
            return

        self.log_message.emit(f"保存合并后的OSM文件: {self.output_path}")
        success = save_osm_file(current_tree, self.output_path)

        # 更新进度
        self.progress_updated.emit(100, "合并完成")

        if success:
            self.process_completed.emit(True, "OSM文件合并完成")
        else:
            self.process_completed.emit(False, "保存合并后的OSM文件失败")

    def cancel(self):
        """
        取消处理任务
        """
        self.is_cancelled = True
        self.log_message.emit("正在取消合并任务...")

class MergeModule(QObject):
    """
    OSM合并模块，负责协调GUI和处理逻辑
    """
    # 定义信号
    progress_updated = pyqtSignal(int, str)  # 进度更新信号
    process_completed = pyqtSignal(bool, str)  # 处理完成信号
    log_message = pyqtSignal(str)  # 日志消息信号
    stats_updated = pyqtSignal(dict)  # 统计信息更新信号

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None

    def start_merging(self, ref_path, target_files, output_path, area_type='两者',
                     offset_method='顶点平均', min_matches=2,
                     progress_callback=None, completion_callback=None):
        """
        启动OSM合并流程

        参数:
            ref_path: 参照OSM文件路径
            target_files: 目标OSM文件路径列表
            output_path: 输出OSM文件路径
            area_type: 匹配区域类型
            offset_method: 偏移计算方法
            min_matches: 最小匹配区域数量
            progress_callback: 进度回调函数
            completion_callback: 完成回调函数
        """
        params = {
            'area_type': area_type,
            'offset_method': offset_method,
            'min_matches': min_matches
        }

        # 创建并启动工作线程
        self.worker = MergeWorker(ref_path, target_files, output_path, params)
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

    def cancel_merging(self):
        """
        取消合并任务
        """
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()  # 等待线程结束

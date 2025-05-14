#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本提取模块

此模块负责实现文本提取功能，包括从DXF文件提取文本、将文本坐标转换为像素坐标、从OSM文件提取房间多边形、匹配文本到房间和更新OSM文件。
"""

import os
import sys
import json
import logging
from pathlib import Path
from PyQt5.QtCore import QObject, pyqtSignal, QThread

# 添加文本提取脚本路径
sys.path.append(str(Path(__file__).parent.parent.parent / 'script' / 'text_extract_module'))

# 导入文本提取模块
try:
    from text_extractor import extract_text, convert_coordinates_step, extract_rooms_step, match_text_step, update_osm_step
except ImportError as e:
    print(f"导入文本提取模块失败: {e}")

class TextWorker(QThread):
    """
    文本提取工作线程，用于在后台执行文本提取任务
    """
    progress_updated = pyqtSignal(int, str)  # 进度更新信号
    step_progress_updated = pyqtSignal(int, str)  # 步骤进度更新信号
    process_completed = pyqtSignal(bool, str)  # 处理完成信号
    log_message = pyqtSignal(str)  # 日志消息信号
    visualization_ready = pyqtSignal(str)  # 可视化图像就绪信号
    
    def __init__(self, mode, params):
        super().__init__()
        self.mode = mode  # 'full', 'extract_only', 'match_only'
        self.params = params
        self.is_cancelled = False
    
    def run(self):
        """
        执行文本提取任务
        """
        try:
            if self.mode == 'full':
                self.run_full_process()
            elif self.mode == 'extract_only':
                self.run_extract_only()
            elif self.mode == 'match_only':
                self.run_match_only()
            else:
                self.process_completed.emit(False, f"未知的处理模式: {self.mode}")
        except Exception as e:
            self.log_message.emit(f"处理过程中发生错误: {str(e)}")
            self.process_completed.emit(False, f"处理失败: {str(e)}")
    
    def run_full_process(self):
        """
        执行完整的文本提取流程
        """
        self.log_message.emit("开始执行完整文本提取流程...")
        
        # 获取参数
        dxf_path = self.params.get('dxf_path')
        bounds_path = self.params.get('bounds_path')
        osm_path = self.params.get('osm_path')
        output_path = self.params.get('output_path')
        config_path = self.params.get('config_path')
        layer_name = self.params.get('layer_name', 'I—平面—文字')
        visualize = self.params.get('visualize', False)
        nearby_threshold = self.params.get('nearby_threshold', 50)
        max_center_distance_ratio = self.params.get('max_center_distance_ratio', 0.7)
        filter_text_list = self.params.get('filter_text_list', [])
        
        # 验证必要参数
        if not dxf_path or not bounds_path or not osm_path or not output_path:
            self.process_completed.emit(False, "缺少必要参数")
            return
        
        # 步骤1: 从DXF文件提取文本
        self.log_message.emit("步骤1: 从DXF文件提取文本")
        self.step_progress_updated.emit(0, "提取文本中...")
        
        # 创建临时文件路径
        temp_dir = os.path.dirname(output_path)
        temp_text_path = os.path.join(temp_dir, "temp_text.json")
        temp_text_pixel_path = os.path.join(temp_dir, "temp_text_pixel.json")
        temp_rooms_path = os.path.join(temp_dir, "temp_rooms.json")
        temp_mapping_path = os.path.join(temp_dir, "temp_mapping.json")
        
        # 提取文本
        try:
            text_data = extract_text(dxf_path, temp_text_path, layer_name, config_path)
            self.step_progress_updated.emit(25, "文本提取完成")
            self.log_message.emit(f"提取了 {len(text_data)} 个文本项")
        except Exception as e:
            self.process_completed.emit(False, f"文本提取失败: {str(e)}")
            return
        
        # 步骤2: 将DXF文本坐标转换为像素坐标
        self.log_message.emit("步骤2: 将DXF文本坐标转换为像素坐标")
        self.step_progress_updated.emit(25, "转换坐标中...")
        
        # 加载边界数据
        try:
            with open(bounds_path, 'r', encoding='utf-8') as f:
                bounds_data = json.load(f)
        except Exception as e:
            self.process_completed.emit(False, f"加载边界数据失败: {str(e)}")
            return
        
        # 转换坐标
        try:
            text_data_pixel = convert_coordinates_step(text_data, bounds_data, temp_text_pixel_path, config_path)
            self.step_progress_updated.emit(50, "坐标转换完成")
            self.log_message.emit(f"转换了 {len(text_data_pixel)} 个文本项的坐标")
        except Exception as e:
            self.process_completed.emit(False, f"坐标转换失败: {str(e)}")
            return
        
        # 步骤3: 从OSM文件提取房间多边形
        self.log_message.emit("步骤3: 从OSM文件提取房间多边形")
        self.step_progress_updated.emit(50, "提取房间多边形中...")
        
        # 提取房间多边形
        try:
            rooms_result = extract_rooms_step(osm_path, temp_rooms_path, config_path)
            rooms_data = rooms_result['rooms']
            self.step_progress_updated.emit(75, "房间多边形提取完成")
            self.log_message.emit(f"提取了 {len(rooms_data)} 个房间多边形")
        except Exception as e:
            self.process_completed.emit(False, f"房间多边形提取失败: {str(e)}")
            return
        
        # 步骤4: 匹配文本到房间
        self.log_message.emit("步骤4: 匹配文本到房间")
        self.step_progress_updated.emit(75, "匹配文本到房间中...")
        
        # 匹配文本到房间
        try:
            mapping_result = match_text_step(
                text_data_pixel, 
                rooms_data, 
                temp_mapping_path, 
                nearby_threshold, 
                max_center_distance_ratio
            )
            self.step_progress_updated.emit(90, "文本匹配完成")
            self.log_message.emit(f"匹配了 {len(mapping_result['matched_rooms'])} 个房间的文本")
        except Exception as e:
            self.process_completed.emit(False, f"文本匹配失败: {str(e)}")
            return
        
        # 步骤5: 更新OSM文件
        self.log_message.emit("步骤5: 更新OSM文件")
        self.step_progress_updated.emit(90, "更新OSM文件中...")
        
        # 可视化路径
        visualization_path = None
        if visualize:
            visualization_path = os.path.join(temp_dir, "text_matching_visualization.png")
        
        # 更新OSM文件
        try:
            updated_count = update_osm_step(
                osm_path, 
                mapping_result, 
                output_path, 
                visualize, 
                visualization_path
            )
            self.step_progress_updated.emit(100, "OSM文件更新完成")
            self.log_message.emit(f"更新了 {updated_count} 个房间的文本信息")
            
            # 如果生成了可视化图像，发送信号
            if visualize and visualization_path and os.path.exists(visualization_path):
                self.visualization_ready.emit(visualization_path)
        except Exception as e:
            self.process_completed.emit(False, f"OSM文件更新失败: {str(e)}")
            return
        
        # 处理完成
        self.process_completed.emit(True, "文本提取和匹配完成")
    
    def run_extract_only(self):
        """
        仅执行文本提取步骤
        """
        self.log_message.emit("开始执行文本提取步骤...")
        
        # 获取参数
        dxf_path = self.params.get('dxf_path')
        output_path = self.params.get('output_path')
        config_path = self.params.get('config_path')
        layer_name = self.params.get('layer_name', 'I—平面—文字')
        
        # 验证必要参数
        if not dxf_path or not output_path:
            self.process_completed.emit(False, "缺少必要参数")
            return
        
        # 提取文本
        try:
            text_data = extract_text(dxf_path, output_path, layer_name, config_path)
            self.log_message.emit(f"提取了 {len(text_data)} 个文本项")
            self.process_completed.emit(True, "文本提取完成")
        except Exception as e:
            self.process_completed.emit(False, f"文本提取失败: {str(e)}")
    
    def run_match_only(self):
        """
        仅执行文本匹配步骤
        """
        self.log_message.emit("开始执行文本匹配步骤...")
        
        # 获取参数
        text_path = self.params.get('text_path')
        bounds_path = self.params.get('bounds_path')
        osm_path = self.params.get('osm_path')
        output_path = self.params.get('output_path')
        config_path = self.params.get('config_path')
        visualize = self.params.get('visualize', False)
        nearby_threshold = self.params.get('nearby_threshold', 50)
        max_center_distance_ratio = self.params.get('max_center_distance_ratio', 0.7)
        
        # 验证必要参数
        if not text_path or not bounds_path or not osm_path or not output_path:
            self.process_completed.emit(False, "缺少必要参数")
            return
        
        # 创建临时文件路径
        temp_dir = os.path.dirname(output_path)
        temp_text_pixel_path = os.path.join(temp_dir, "temp_text_pixel.json")
        temp_rooms_path = os.path.join(temp_dir, "temp_rooms.json")
        temp_mapping_path = os.path.join(temp_dir, "temp_mapping.json")
        
        # 加载文本数据
        try:
            with open(text_path, 'r', encoding='utf-8') as f:
                text_data = json.load(f)
            self.log_message.emit(f"加载了 {len(text_data)} 个文本项")
        except Exception as e:
            self.process_completed.emit(False, f"加载文本数据失败: {str(e)}")
            return
        
        # 加载边界数据
        try:
            with open(bounds_path, 'r', encoding='utf-8') as f:
                bounds_data = json.load(f)
        except Exception as e:
            self.process_completed.emit(False, f"加载边界数据失败: {str(e)}")
            return
        
        # 转换坐标
        try:
            text_data_pixel = convert_coordinates_step(text_data, bounds_data, temp_text_pixel_path, config_path)
            self.log_message.emit(f"转换了 {len(text_data_pixel)} 个文本项的坐标")
        except Exception as e:
            self.process_completed.emit(False, f"坐标转换失败: {str(e)}")
            return
        
        # 提取房间多边形
        try:
            rooms_result = extract_rooms_step(osm_path, temp_rooms_path, config_path)
            rooms_data = rooms_result['rooms']
            self.log_message.emit(f"提取了 {len(rooms_data)} 个房间多边形")
        except Exception as e:
            self.process_completed.emit(False, f"房间多边形提取失败: {str(e)}")
            return
        
        # 匹配文本到房间
        try:
            mapping_result = match_text_step(
                text_data_pixel, 
                rooms_data, 
                temp_mapping_path, 
                nearby_threshold, 
                max_center_distance_ratio
            )
            self.log_message.emit(f"匹配了 {len(mapping_result['matched_rooms'])} 个房间的文本")
        except Exception as e:
            self.process_completed.emit(False, f"文本匹配失败: {str(e)}")
            return
        
        # 可视化路径
        visualization_path = None
        if visualize:
            visualization_path = os.path.join(temp_dir, "text_matching_visualization.png")
        
        # 更新OSM文件
        try:
            updated_count = update_osm_step(
                osm_path, 
                mapping_result, 
                output_path, 
                visualize, 
                visualization_path
            )
            self.log_message.emit(f"更新了 {updated_count} 个房间的文本信息")
            
            # 如果生成了可视化图像，发送信号
            if visualize and visualization_path and os.path.exists(visualization_path):
                self.visualization_ready.emit(visualization_path)
        except Exception as e:
            self.process_completed.emit(False, f"OSM文件更新失败: {str(e)}")
            return
        
        # 处理完成
        self.process_completed.emit(True, "文本匹配完成")
    
    def cancel(self):
        """
        取消处理任务
        """
        self.is_cancelled = True
        self.log_message.emit("正在取消处理任务...")

class TextModule(QObject):
    """
    文本提取模块，负责协调GUI和处理逻辑
    """
    # 定义信号
    progress_updated = pyqtSignal(int, str)  # 进度更新信号
    step_progress_updated = pyqtSignal(int, str)  # 步骤进度更新信号
    process_completed = pyqtSignal(bool, str)  # 处理完成信号
    log_message = pyqtSignal(str)  # 日志消息信号
    visualization_ready = pyqtSignal(str)  # 可视化图像就绪信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
    
    def start_full_process(self, params):
        """
        启动完整文本提取流程
        
        参数:
            params: 处理参数字典
        """
        # 创建并启动工作线程
        self.worker = TextWorker('full', params)
        self.connect_worker_signals()
        self.worker.start()
    
    def start_extract_only(self, params):
        """
        启动仅提取文本流程
        
        参数:
            params: 处理参数字典
        """
        # 创建并启动工作线程
        self.worker = TextWorker('extract_only', params)
        self.connect_worker_signals()
        self.worker.start()
    
    def start_match_only(self, params):
        """
        启动仅匹配文本流程
        
        参数:
            params: 处理参数字典
        """
        # 创建并启动工作线程
        self.worker = TextWorker('match_only', params)
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
            self.worker.visualization_ready.connect(self.visualization_ready)
    
    def cancel_process(self):
        """
        取消处理任务
        """
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait()  # 等待线程结束

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本提取标签页

此模块实现了文本提取标签页，用于从DXF文件提取文本并添加到OSM文件。
"""

import os
import sys
from pathlib import Path

# 导入PyQt5组件
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QFileDialog, QComboBox, QCheckBox,
    QSpinBox, QDoubleSpinBox, QProgressBar, QGroupBox,
    QFormLayout, QRadioButton, QButtonGroup, QMessageBox,
    QTextEdit, QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QSettings
from PyQt5.QtGui import QPixmap, QImage

# 导入文本提取模块
from modules.text_module import TextModule

class TextTab(QWidget):
    """
    文本提取标签页，用于从DXF文件提取文本并添加到OSM文件
    """
    
    # 定义信号，用于向主窗口发送日志消息
    log_message = pyqtSignal(str)
    
    def __init__(self, project_manager):
        super().__init__()
        
        # 保存项目管理器引用
        self.project_manager = project_manager
        
        # 初始化文本提取模块
        self.text_module = TextModule(self)
        
        # u521du59cbu5316UI
        self.init_ui()
    
    def init_ui(self):
        """初始化用户界面"""
        # 创建主布局
        main_layout = QVBoxLayout(self)
        
        # 创建模式选择区域
        mode_group = QGroupBox("处理模式")
        mode_layout = QHBoxLayout()
        
        self.mode_group = QButtonGroup(self)
        self.full_mode_radio = QRadioButton("完整流程")
        self.extract_only_radio = QRadioButton("仅提取文本")
        self.match_only_radio = QRadioButton("仅匹配文本")
        
        self.mode_group.addButton(self.full_mode_radio, 1)
        self.mode_group.addButton(self.extract_only_radio, 2)
        self.mode_group.addButton(self.match_only_radio, 3)
        
        self.full_mode_radio.setChecked(True)
        
        mode_layout.addWidget(self.full_mode_radio)
        mode_layout.addWidget(self.extract_only_radio)
        mode_layout.addWidget(self.match_only_radio)
        
        mode_group.setLayout(mode_layout)
        main_layout.addWidget(mode_group)
        
        # 创建输入区域
        input_group = QGroupBox("输入设置")
        input_layout = QFormLayout()
        
        # DXF文件选择
        self.dxf_path_edit = QLineEdit()
        self.browse_dxf_btn = QPushButton("浏览...")
        self.browse_dxf_btn.clicked.connect(self.browse_dxf)
        
        dxf_path_layout = QHBoxLayout()
        dxf_path_layout.addWidget(self.dxf_path_edit)
        dxf_path_layout.addWidget(self.browse_dxf_btn)
        input_layout.addRow("DXF文件:", dxf_path_layout)
        
        # 边界文件选择
        self.bounds_path_edit = QLineEdit()
        self.browse_bounds_btn = QPushButton("浏览...")
        self.browse_bounds_btn.clicked.connect(self.browse_bounds)
        
        bounds_path_layout = QHBoxLayout()
        bounds_path_layout.addWidget(self.bounds_path_edit)
        bounds_path_layout.addWidget(self.browse_bounds_btn)
        input_layout.addRow("边界文件:", bounds_path_layout)
        
        # OSM文件选择
        self.osm_path_edit = QLineEdit()
        self.browse_osm_btn = QPushButton("浏览...")
        self.browse_osm_btn.clicked.connect(self.browse_osm)
        
        osm_path_layout = QHBoxLayout()
        osm_path_layout.addWidget(self.osm_path_edit)
        osm_path_layout.addWidget(self.browse_osm_btn)
        input_layout.addRow("OSM文件:", osm_path_layout)
        
        # 文本文件选择（仅匹配模式使用）
        self.text_path_edit = QLineEdit()
        self.browse_text_btn = QPushButton("浏览...")
        self.browse_text_btn.clicked.connect(self.browse_text)
        
        text_path_layout = QHBoxLayout()
        text_path_layout.addWidget(self.text_path_edit)
        text_path_layout.addWidget(self.browse_text_btn)
        input_layout.addRow("文本文件:", text_path_layout)
        
        # 输出文件路径
        self.output_path_edit = QLineEdit()
        self.browse_output_btn = QPushButton("浏览...")
        self.browse_output_btn.clicked.connect(self.browse_output)
        
        output_path_layout = QHBoxLayout()
        output_path_layout.addWidget(self.output_path_edit)
        output_path_layout.addWidget(self.browse_output_btn)
        input_layout.addRow("输出文件:", output_path_layout)
        
        # 配置文件选择
        self.config_path_edit = QLineEdit()
        self.browse_config_btn = QPushButton("浏览...")
        self.browse_config_btn.clicked.connect(self.browse_config)
        
        config_path_layout = QHBoxLayout()
        config_path_layout.addWidget(self.config_path_edit)
        config_path_layout.addWidget(self.browse_config_btn)
        input_layout.addRow("配置文件(可选):", config_path_layout)
        
        input_group.setLayout(input_layout)
        main_layout.addWidget(input_group)
        
        # 创建参数设置区域
        params_group = QGroupBox("参数设置")
        params_layout = QFormLayout()
        
        # 文本图层名称
        self.layer_name_edit = QLineEdit("——平面——文字")
        params_layout.addRow("文本图层名称:", self.layer_name_edit)
        
        # 附近匹配偏移阈值
        self.nearby_threshold_spin = QSpinBox()
        self.nearby_threshold_spin.setRange(1, 500)
        self.nearby_threshold_spin.setValue(50)
        params_layout.addRow("附近匹配偏移阈值:", self.nearby_threshold_spin)
        
        # 中心偏移比例阈值
        self.center_distance_ratio_spin = QDoubleSpinBox()
        self.center_distance_ratio_spin.setRange(0.1, 1.0)
        self.center_distance_ratio_spin.setValue(0.7)
        self.center_distance_ratio_spin.setSingleStep(0.1)
        params_layout.addRow("中心偏移比例阈值:", self.center_distance_ratio_spin)
        
        # 可视化选项
        self.visualize_check = QCheckBox("生成可视化图像")
        params_layout.addRow("", self.visualize_check)
        
        params_group.setLayout(params_layout)
        main_layout.addWidget(params_group)
        
        # 创建文本过滤区域
        filter_group = QGroupBox("文本过滤设置")
        filter_layout = QVBoxLayout()
        
        filter_layout.addWidget(QLabel("要过滤的文本列表（每行一个）："))
        self.filter_text_edit = QTextEdit()
        self.filter_text_edit.setPlaceholderText("输入要过滤的文本，每行一个。例如：\n卫生间\n电梯\n楼梯")
        filter_layout.addWidget(self.filter_text_edit)
        
        filter_group.setLayout(filter_layout)
        main_layout.addWidget(filter_group)
        
        # 创建进度显示区域
        progress_group = QGroupBox("进度")
        progress_layout = QVBoxLayout()
        
        # 总体进度条
        progress_layout.addWidget(QLabel("总体进度:"))
        self.total_progress_bar = QProgressBar()
        progress_layout.addWidget(self.total_progress_bar)
        
        # 当前步骤进度条
        progress_layout.addWidget(QLabel("当前步骤:"))
        self.step_progress_bar = QProgressBar()
        progress_layout.addWidget(self.step_progress_bar)
        
        # 处理状态文本
        self.status_label = QLabel("就绪")
        progress_layout.addWidget(self.status_label)
        
        progress_group.setLayout(progress_layout)
        main_layout.addWidget(progress_group)
        
        # 创建结果预览区域
        preview_group = QGroupBox("结果预览")
        preview_layout = QVBoxLayout()
        
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.preview_label.setMinimumHeight(200)
        self.preview_label.setStyleSheet("background-color: white; border: 1px solid #cccccc;")
        self.preview_label.setText("匹配结果预览将在这里显示")
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.preview_label)
        
        preview_layout.addWidget(scroll_area)
        
        preview_group.setLayout(preview_layout)
        main_layout.addWidget(preview_group)
        
        # 创建按钮区域
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("开始处理")
        self.start_button.clicked.connect(self.start_processing)
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.cancel_processing)
        self.cancel_button.setEnabled(False)
        
        button_layout.addStretch()
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.cancel_button)
        
        main_layout.addLayout(button_layout)
        
        # 连接信号
        self.mode_group.buttonClicked.connect(self.update_ui_for_mode)
        
        # 初始化UI状态
        self.update_ui_for_mode()
    
    def update_ui_for_mode(self):
        """根据选择的模式更新UI状态"""
        mode = self.mode_group.checkedId()
        
        # 完整流程模式
        if mode == 1 or mode == 0:  # 0表示没有选中任何按钮
            self.dxf_path_edit.setEnabled(True)
            self.browse_dxf_btn.setEnabled(True)
            self.bounds_path_edit.setEnabled(True)
            self.browse_bounds_btn.setEnabled(True)
            self.osm_path_edit.setEnabled(True)
            self.browse_osm_btn.setEnabled(True)
            self.text_path_edit.setEnabled(False)
            self.browse_text_btn.setEnabled(False)
        # 仅提取文本模式
        elif mode == 2:
            self.dxf_path_edit.setEnabled(True)
            self.browse_dxf_btn.setEnabled(True)
            self.bounds_path_edit.setEnabled(False)
            self.browse_bounds_btn.setEnabled(False)
            self.osm_path_edit.setEnabled(False)
            self.browse_osm_btn.setEnabled(False)
            self.text_path_edit.setEnabled(False)
            self.browse_text_btn.setEnabled(False)
        # 仅匹配文本模式
        elif mode == 3:
            self.dxf_path_edit.setEnabled(False)
            self.browse_dxf_btn.setEnabled(False)
            self.bounds_path_edit.setEnabled(True)
            self.browse_bounds_btn.setEnabled(True)
            self.osm_path_edit.setEnabled(True)
            self.browse_osm_btn.setEnabled(True)
            self.text_path_edit.setEnabled(True)
            self.browse_text_btn.setEnabled(True)
    
    def browse_dxf(self):
        """浏览DXF文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择DXF文件", "", "DXF文件 (*.dxf)"
        )
        if file_path:
            self.dxf_path_edit.setText(file_path)
            # u81eau52a8u8bbeu7f6eu8f93u51fau6587u4ef6u8defu5f84
            self.suggest_paths(file_path)
    
    def browse_bounds(self):
        """浏览边界文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择边界文件", "", "JSON文件 (*.json)"
        )
        if file_path:
            self.bounds_path_edit.setText(file_path)
    
    def browse_osm(self):
        """浏览OSM文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择OSM文件", "", "OSM文件 (*.osm)"
        )
        if file_path:
            self.osm_path_edit.setText(file_path)
            # u81eau52a8u8bbeu7f6eu8f93u51fau6587u4ef6u8defu5f84
            if not self.output_path_edit.text():
                output_path = str(Path(file_path).with_name(f"{Path(file_path).stem}_texted.osm"))
                self.output_path_edit.setText(output_path)
    
    def browse_text(self):
        """浏览文本文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择文本文件", "", "JSON文件 (*.json)"
        )
        if file_path:
            self.text_path_edit.setText(file_path)
    
    def browse_output(self):
        """浏览输出文件"""
        mode = self.mode_group.checkedId()
        
        if mode == 2:  # 仅提取文本模式
            file_path, _ = QFileDialog.getSaveFileName(
                self, "选择输出文件", "", "JSON文件 (*.json)"
            )
        else:  # 其他模式
            file_path, _ = QFileDialog.getSaveFileName(
                self, "选择输出文件", "", "OSM文件 (*.osm)"
            )
        
        if file_path:
            self.output_path_edit.setText(file_path)
    
    def browse_config(self):
        """浏览配置文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择配置文件", "", "YAML文件 (*.yaml *.yml)"
        )
        if file_path:
            self.config_path_edit.setText(file_path)
    
    def suggest_paths(self, dxf_path):
        """根据输入路径自动建议其他路径"""
        dxf_dir = Path(dxf_path).parent
        file_stem = Path(dxf_path).stem
        
        # 尝试找到bounds.json
        bounds_path = dxf_dir.parent / 'bounds' / 'bounds.json'
        if bounds_path.exists():
            self.bounds_path_edit.setText(str(bounds_path))
        
        # 尝试找到OSM文件
        osm_dir = dxf_dir.parent / 'osm' / 'original'
        if osm_dir.exists():
            osm_files = list(osm_dir.glob(f"{file_stem}*.osm"))
            if osm_files:
                self.osm_path_edit.setText(str(osm_files[0]))
                
                # 设置输出文件路径
                output_dir = dxf_dir.parent / 'osm' / 'texted'
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = output_dir / f"{osm_files[0].stem}_texted.osm"
                self.output_path_edit.setText(str(output_path))
    
    def start_processing(self):
        """开始处理"""
        # 获取当前选择的模式
        mode = self.mode_group.checkedId()
        
        # 验证共同输入
        output_path = self.output_path_edit.text().strip()
        if not output_path:
            QMessageBox.warning(self, "输入错误", "请选择输出文件路径")
            return
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 获取通用参数
        config_path = self.config_path_edit.text().strip() or None
        layer_name = self.layer_name_edit.text().strip()
        nearby_threshold = self.nearby_threshold_spin.value()
        center_distance_ratio = self.center_distance_ratio_spin.value()
        visualize = self.visualize_check.isChecked()
        
        # 获取过滤文本列表
        filter_text = self.filter_text_edit.toPlainText().strip()
        filter_text_list = [text.strip() for text in filter_text.split('\n') if text.strip()]
        
        # 根据不同模式验证输入并调用相应功能
        if mode == 1 or mode == 0:  # 完整流程模式
            # 验证输入
            dxf_path = self.dxf_path_edit.text().strip()
            bounds_path = self.bounds_path_edit.text().strip()
            osm_path = self.osm_path_edit.text().strip()
            
            if not dxf_path:
                QMessageBox.warning(self, "输入错误", "请选择DXF文件")
                return
            
            if not bounds_path:
                QMessageBox.warning(self, "输入错误", "请选择边界文件")
                return
            
            if not osm_path:
                QMessageBox.warning(self, "输入错误", "请选择OSM文件")
                return
            
            # 禁用开始按钮，启用取消按钮
            self.start_button.setEnabled(False)
            self.cancel_button.setEnabled(True)
            
            # 更新状态
            self.status_label.setText("正在处理...")
            self.total_progress_bar.setValue(0)
            self.step_progress_bar.setValue(0)
            
            # 调用文本提取模块
            self.log_message.emit(f"开始完整文本提取流程...\n输入DXF: {dxf_path}\n边界文件: {bounds_path}\n输入OSM: {osm_path}\n输出: {output_path}")
            
            # 启动处理线程
            self.text_module.start_full_process(
                dxf_path=dxf_path,
                bounds_path=bounds_path,
                osm_path=osm_path,
                output_path=output_path,
                config_path=config_path,
                layer_name=layer_name,
                nearby_threshold=nearby_threshold,
                center_distance_ratio=center_distance_ratio,
                filter_text_list=filter_text_list,
                visualize=visualize,
                progress_callback=self.update_progress,
                completion_callback=self.processing_completed
            )
        
        elif mode == 2:  # 仅提取文本模式
            # 验证输入
            dxf_path = self.dxf_path_edit.text().strip()
            
            if not dxf_path:
                QMessageBox.warning(self, "输入错误", "请选择DXF文件")
                return
            
            # 禁用开始按钮，启用取消按钮
            self.start_button.setEnabled(False)
            self.cancel_button.setEnabled(True)
            
            # 更新状态
            self.status_label.setText("正在处理...")
            self.total_progress_bar.setValue(0)
            self.step_progress_bar.setValue(0)
            
            # 调用文本提取模块
            self.log_message.emit(f"开始提取文本...\n输入DXF: {dxf_path}\n输出: {output_path}")
            
            # 启动处理线程
            self.text_module.start_extract_only(
                dxf_path=dxf_path,
                output_path=output_path,
                config_path=config_path,
                layer_name=layer_name,
                filter_text_list=filter_text_list,
                progress_callback=self.update_progress,
                completion_callback=self.processing_completed
            )
        
        elif mode == 3:  # 仅匹配文本模式
            # 验证输入
            bounds_path = self.bounds_path_edit.text().strip()
            osm_path = self.osm_path_edit.text().strip()
            text_path = self.text_path_edit.text().strip()
            
            if not bounds_path:
                QMessageBox.warning(self, "输入错误", "请选择边界文件")
                return
            
            if not osm_path:
                QMessageBox.warning(self, "输入错误", "请选择OSM文件")
                return
            
            if not text_path:
                QMessageBox.warning(self, "输入错误", "请选择文本文件")
                return
            
            # 禁用开始按钮，启用取消按钮
            self.start_button.setEnabled(False)
            self.cancel_button.setEnabled(True)
            
            # 更新状态
            self.status_label.setText("正在处理...")
            self.total_progress_bar.setValue(0)
            self.step_progress_bar.setValue(0)
            
            # 调用文本提取模块
            self.log_message.emit(f"开始匹配文本...\n边界文件: {bounds_path}\n输入OSM: {osm_path}\n文本文件: {text_path}\n输出: {output_path}")
            
            # 启动处理线程
            self.text_module.start_match_only(
                bounds_path=bounds_path,
                osm_path=osm_path,
                text_path=text_path,
                output_path=output_path,
                config_path=config_path,
                nearby_threshold=nearby_threshold,
                center_distance_ratio=center_distance_ratio,
                filter_text_list=filter_text_list,
                visualize=visualize,
                progress_callback=self.update_progress,
                completion_callback=self.processing_completed
            )
    
    def cancel_processing(self):
        """取消处理"""
        # 调用文本提取模块的取消方法
        self.text_module.cancel_processing()
        
        # 更新UI状态
        self.status_label.setText("已取消")
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        
        # 记录日志
        self.log_message.emit("文本提取已取消")
    
    def update_progress(self, total_progress, step_progress=None, status=None, preview_image=None):
        """更新进度和状态"""
        # 更新总体进度条
        self.total_progress_bar.setValue(int(total_progress * 100))
        
        # 更新当前步骤进度条
        if step_progress is not None:
            self.step_progress_bar.setValue(int(step_progress * 100))
        
        # 更新状态文本
        if status is not None:
            self.status_label.setText(status)
        
        # 更新预览图像
        if preview_image is not None:
            # 将图像数据转换为QImage
            if isinstance(preview_image, bytes):
                qimg = QImage.fromData(preview_image)
                pixmap = QPixmap.fromImage(qimg)
                self.preview_label.setPixmap(pixmap.scaled(
                    self.preview_label.width(), 
                    self.preview_label.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                ))
            elif isinstance(preview_image, str) and os.path.exists(preview_image):
                # 如果是文件路径，加载图像
                pixmap = QPixmap(preview_image)
                self.preview_label.setPixmap(pixmap.scaled(
                    self.preview_label.width(), 
                    self.preview_label.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                ))
            else:
                # 清除预览
                self.preview_label.setText("无法显示预览")
    
    def processing_completed(self, success, message, result_data=None, preview_image=None):
        """处理完成回调"""
        # 更新UI状态
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        
        if success:
            # 成功完成
            self.status_label.setText("完成")
            self.total_progress_bar.setValue(100)
            self.step_progress_bar.setValue(100)
            self.log_message.emit(f"文本提取完成: {message}")
            
            # 如果有预览图像，显示预览
            if preview_image is not None:
                self.update_progress(1.0, 1.0, "完成", preview_image)
            
            # 显示完成消息
            mode = self.mode_group.checkedId()
            if mode == 1 or mode == 0:  # 完整流程模式
                QMessageBox.information(self, "处理完成", 
                                       f"文本提取并添加到OSM文件已完成。\n\n{message}")
            elif mode == 2:  # 仅提取文本模式
                QMessageBox.information(self, "处理完成", 
                                       f"文本提取已完成。\n\n{message}")
            elif mode == 3:  # 仅匹配文本模式
                QMessageBox.information(self, "处理完成", 
                                       f"文本匹配并添加到OSM文件已完成。\n\n{message}")
        else:
            # 处理失败
            self.status_label.setText("失败")
            self.log_message.emit(f"文本提取失败: {message}")
            QMessageBox.warning(self, "处理失败", f"文本提取过程中出现错误: {message}")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
半自动流程子标签页

此模块实现了CAD预处理半自动流程子标签页，处理从已过滤DXF到PNG的转换流程。
"""

import os
import sys
from pathlib import Path

# 导入PyQt5组件
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QFileDialog, QComboBox, QCheckBox,
    QSpinBox, QDoubleSpinBox, QProgressBar, QGroupBox,
    QFormLayout, QRadioButton, QButtonGroup, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QSettings

class SemiProcessTab(QWidget):
    """
    CAD预处理半自动流程子标签页，处理从已过滤DXF到PNG的转换流程
    """
    
    # 定义信号，用于向主窗口发送日志消息
    log_message = pyqtSignal(str)
    
    def __init__(self, project_manager, process_module):
        super().__init__()
        
        # 保存项目管理器引用
        self.project_manager = project_manager
        
        # 保存处理模块引用
        self.process_module = process_module
        
        # 初始化UI
        self.init_ui()
    
    def init_ui(self):
        """初始化用户界面"""
        # 创建主布局
        main_layout = QVBoxLayout(self)
        
        # 创建输入区域
        input_group = QGroupBox("输入设置")
        input_layout = QFormLayout()
        
        # DXF文件选择
        self.input_mode_group = QButtonGroup(self)
        self.single_file_radio = QRadioButton("单个文件")
        self.batch_dir_radio = QRadioButton("批量处理目录")
        self.input_mode_group.addButton(self.single_file_radio, 1)
        self.input_mode_group.addButton(self.batch_dir_radio, 2)
        self.single_file_radio.setChecked(True)
        
        input_mode_layout = QHBoxLayout()
        input_mode_layout.addWidget(self.single_file_radio)
        input_mode_layout.addWidget(self.batch_dir_radio)
        input_layout.addRow("处理模式:", input_mode_layout)
        
        # 输入文件/目录选择
        self.input_path_edit = QLineEdit()
        self.browse_input_btn = QPushButton("浏览...")
        self.browse_input_btn.clicked.connect(self.browse_input)
        
        input_path_layout = QHBoxLayout()
        input_path_layout.addWidget(self.input_path_edit)
        input_path_layout.addWidget(self.browse_input_btn)
        input_layout.addRow("输入路径:", input_path_layout)
        
        # 输出目录选择
        self.output_dir_edit = QLineEdit()
        self.browse_output_btn = QPushButton("浏览...")
        self.browse_output_btn.clicked.connect(self.browse_output)
        
        output_dir_layout = QHBoxLayout()
        output_dir_layout.addWidget(self.output_dir_edit)
        output_dir_layout.addWidget(self.browse_output_btn)
        input_layout.addRow("输出目录:", output_dir_layout)
        
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
        
        # 目标PNG分辨率设置
        self.resolution_spin = QSpinBox()
        self.resolution_spin.setRange(1000, 10000)
        self.resolution_spin.setValue(4000)
        self.resolution_spin.setSingleStep(100)
        params_layout.addRow("目标PNG分辨率:", self.resolution_spin)
        
        # 边缘空隙比例设置
        self.padding_spin = QDoubleSpinBox()
        self.padding_spin.setRange(0.0, 10.0)
        self.padding_spin.setValue(3.0)
        self.padding_spin.setSingleStep(0.1)
        self.padding_spin.setSuffix("%")
        params_layout.addRow("边缘空隙比例:", self.padding_spin)
        
        # 线条粗细设置
        self.line_thickness_spin = QSpinBox()
        self.line_thickness_spin.setRange(1, 10)
        self.line_thickness_spin.setValue(1)
        params_layout.addRow("线条粗细:", self.line_thickness_spin)
        
        params_group.setLayout(params_layout)
        main_layout.addWidget(params_group)
        
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
        self.single_file_radio.toggled.connect(self.update_input_mode)
    
    def update_input_mode(self):
        """更新输入模式"""
        if self.single_file_radio.isChecked():
            self.browse_input_btn.setText("浏览文件...")
        else:
            self.browse_input_btn.setText("浏览目录...")
    
    def browse_input(self):
        """浏览输入文件或目录"""
        if self.single_file_radio.isChecked():
            # 单个文件模式
            file_path, _ = QFileDialog.getOpenFileName(
                self, "选择已过滤DXF文件", "", "DXF文件 (*.dxf)"
            )
            if file_path:
                self.input_path_edit.setText(file_path)
                # 自动设置输出目录
                self.suggest_output_dir(file_path)
        else:
            # 批量处理目录模式
            dir_path = QFileDialog.getExistingDirectory(
                self, "选择包含已过滤DXF文件的目录"
            )
            if dir_path:
                self.input_path_edit.setText(dir_path)
                # 自动设置输出目录
                self.suggest_output_dir(dir_path)
    
    def suggest_output_dir(self, input_path):
        """根据输入路径自动建议输出目录"""
        path = Path(input_path)
        
        # 如果是文件，获取其父目录
        if path.is_file():
            parent_dir = path.parent
        else:
            parent_dir = path
        
        # 检查父目录名称是否包含'dxf'或'manual_filter'
        parent_name = parent_dir.name
        if 'dxf' in parent_name or 'manual_filter' in parent_name:
            # 尝试找到项目根目录
            try:
                project_dir = parent_dir
                while project_dir.name not in ['data', ''] and project_dir.parent != project_dir:
                    project_dir = project_dir.parent
                
                if project_dir.name == 'data':
                    # 找到了data目录，建议使用标准输出路径
                    suggested_dir = project_dir / 'img' / 'png_manual_filter'
                    suggested_dir.mkdir(parents=True, exist_ok=True)
                    self.output_dir_edit.setText(str(suggested_dir))
                    return
            except Exception:
                pass
        
        # 如果无法确定标准路径，则使用输入目录旁边的png目录
        suggested_dir = parent_dir.parent / 'img' / 'png_manual_filter'
        self.output_dir_edit.setText(str(suggested_dir))
    
    def browse_output(self):
        """浏览输出目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择输出目录"
        )
        if dir_path:
            self.output_dir_edit.setText(dir_path)
    
    def browse_config(self):
        """浏览配置文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择配置文件", "", "YAML文件 (*.yaml *.yml)"
        )
        if file_path:
            self.config_path_edit.setText(file_path)
    
    def start_processing(self):
        """开始处理"""
        # 验证输入
        input_path = self.input_path_edit.text().strip()
        output_dir = self.output_dir_edit.text().strip()
        config_path = self.config_path_edit.text().strip() or None
        
        if not input_path:
            QMessageBox.warning(self, "输入错误", "请选择输入文件或目录")
            return
        
        if not output_dir:
            QMessageBox.warning(self, "输入错误", "请选择输出目录")
            return
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 获取参数
        resolution = self.resolution_spin.value()
        padding_ratio = self.padding_spin.value() / 100.0  # 转换为小数
        line_thickness = self.line_thickness_spin.value()
        
        # 这里将实现调用处理模块的功能
        self.log_message.emit(f"开始半自动处理流程...\n输入: {input_path}\n输出: {output_dir}")
        QMessageBox.information(self, "功能开发中", "半自动处理流程功能正在开发中...")
    
    def cancel_processing(self):
        """取消处理"""
        # 这里将实现取消处理的功能
        self.log_message.emit("取消处理")
        QMessageBox.information(self, "功能开发中", "取消处理功能正在开发中...")

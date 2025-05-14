#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整流程子标签页

此模块实现了CAD预处理完整流程子标签页，处理从DWG到PNG的完整转换流程。
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

class FullProcessTab(QWidget):
    """
    CAD预处理完整流程子标签页，处理从DWG到PNG的完整转换流程
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
        
        # DWG文件选择
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
        
        # 创建步骤控制区域
        steps_group = QGroupBox("步骤控制")
        steps_layout = QVBoxLayout()
        
        # 跳过步骤选择
        self.skip_dwg_to_dxf_check = QCheckBox("跳过DWG→DXF")
        self.skip_dxf_filter_check = QCheckBox("跳过DXF过滤")
        self.skip_dxf_to_svg_check = QCheckBox("跳过DXF→SVG")
        self.skip_svg_to_png_check = QCheckBox("跳过SVG→PNG")
        
        steps_layout.addWidget(self.skip_dwg_to_dxf_check)
        steps_layout.addWidget(self.skip_dxf_filter_check)
        steps_layout.addWidget(self.skip_dxf_to_svg_check)
        steps_layout.addWidget(self.skip_svg_to_png_check)
        
        steps_group.setLayout(steps_layout)
        main_layout.addWidget(steps_group)
        
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
                self, "选择DWG文件", "", "DWG文件 (*.dwg)"
            )
            if file_path:
                self.input_path_edit.setText(file_path)
        else:
            # 批量处理目录模式
            dir_path = QFileDialog.getExistingDirectory(
                self, "选择包含DWG文件的目录"
            )
            if dir_path:
                self.input_path_edit.setText(dir_path)
    
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
        if not input_path:
            QMessageBox.warning(self, "输入错误", "请选择输入文件或目录")
            return
        
        output_dir = self.output_dir_edit.text().strip()
        if not output_dir:
            QMessageBox.warning(self, "输入错误", "请选择输出目录")
            return
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 获取参数
        config_path = self.config_path_edit.text().strip() or None
        resolution = self.resolution_spin.value()
        padding_ratio = self.padding_spin.value() / 100.0  # 转换为小数
        line_thickness = self.line_thickness_spin.value()
        
        # 获取跳过步骤设置
        skip_steps = {
            'skip_dwg_to_dxf': self.skip_dwg_to_dxf_check.isChecked(),
            'skip_dxf_filter': self.skip_dxf_filter_check.isChecked(),
            'skip_dxf_to_svg': self.skip_dxf_to_svg_check.isChecked(),
            'skip_svg_to_png': self.skip_svg_to_png_check.isChecked()
        }
        
        # 获取处理模式
        is_batch = self.batch_dir_radio.isChecked()
        
        # 禁用开始按钮，启用取消按钮
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        
        # 更新状态
        self.status_label.setText("正在处理...")
        self.total_progress_bar.setValue(0)
        self.step_progress_bar.setValue(0)
        
        # 调用处理模块
        if is_batch:
            self.log_message.emit(f"开始批量完整处理流程...\n输入目录: {input_path}\n输出目录: {output_dir}")
            
            # 启动批量处理线程
            self.process_module.start_batch_full_process(
                input_dir=input_path,
                output_dir=output_dir,
                config_path=config_path,
                resolution=resolution,
                padding_ratio=padding_ratio,
                line_thickness=line_thickness,
                skip_steps=skip_steps,
                progress_callback=self.update_progress,
                completion_callback=self.processing_completed
            )
        else:
            self.log_message.emit(f"开始单文件完整处理流程...\n输入文件: {input_path}\n输出目录: {output_dir}")
            
            # 启动单文件处理线程
            self.process_module.start_full_process(
                input_path=input_path,
                output_dir=output_dir,
                config_path=config_path,
                params={
                    'resolution': resolution,
                    'padding_ratio': padding_ratio,
                    'line_thickness': line_thickness,
                    'skip_dwg_to_dxf': 1 in skip_steps,
                    'skip_dxf_filter': 2 in skip_steps,
                    'skip_dxf_to_svg': 3 in skip_steps,
                    'skip_svg_to_png': 4 in skip_steps
                }
            )
    
    def cancel_processing(self):
        """取消处理"""
        # 调用处理模块的取消方法
        self.process_module.cancel_processing()
        
        # 更新UI状态
        self.status_label.setText("已取消")
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        
        # 记录日志
        self.log_message.emit("完整处理流程已取消")
    
    def update_progress(self, total_progress, step_progress=None, step_name=None, status=None):
        """更新进度和状态"""
        # 更新总体进度条
        self.total_progress_bar.setValue(int(total_progress * 100))
        
        # 更新当前步骤进度条
        if step_progress is not None:
            self.step_progress_bar.setValue(int(step_progress * 100))
        
        # 更新状态文本
        if status is not None:
            self.status_label.setText(status)
        elif step_name is not None:
            self.status_label.setText(f"正在处理: {step_name}")
    
    def processing_completed(self, success, message, result_files=None):
        """处理完成回调"""
        # 更新UI状态
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        
        if success:
            # 成功完成
            self.status_label.setText("完成")
            self.total_progress_bar.setValue(100)
            self.step_progress_bar.setValue(100)
            
            # 记录日志
            self.log_message.emit(f"完整处理流程完成: {message}")
            
            # 显示完成消息
            result_files_text = ""
            if result_files and len(result_files) > 0:
                result_files_text = "\n\n生成的文件:\n" + "\n".join(result_files)
            
            QMessageBox.information(self, "处理完成", 
                                   f"完整处理流程已完成。\n\n{message}{result_files_text}")
        else:
            # 处理失败
            self.status_label.setText("失败")
            self.log_message.emit(f"完整处理流程失败: {message}")
            QMessageBox.warning(self, "处理失败", f"完整处理流程中出现错误: {message}")

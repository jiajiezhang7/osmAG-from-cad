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

# 导入语言管理器
from utils.language_manager import tr

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
        self.input_group = QGroupBox(tr("ui.input_settings"))
        input_layout = QFormLayout()

        # DXF文件选择
        self.input_mode_group = QButtonGroup(self)
        self.single_file_radio = QRadioButton(tr("sub_tabs.single_file"))
        self.batch_dir_radio = QRadioButton(tr("sub_tabs.batch_directory"))
        self.input_mode_group.addButton(self.single_file_radio, 1)
        self.input_mode_group.addButton(self.batch_dir_radio, 2)
        self.single_file_radio.setChecked(True)

        input_mode_layout = QHBoxLayout()
        input_mode_layout.addWidget(self.single_file_radio)
        input_mode_layout.addWidget(self.batch_dir_radio)
        self.processing_mode_label = QLabel(tr("sub_tabs.processing_mode") + ":")
        input_layout.addRow(self.processing_mode_label, input_mode_layout)

        # 输入文件/目录选择
        self.input_path_edit = QLineEdit()
        self.browse_input_btn = QPushButton(tr("buttons.browse_ellipsis"))
        self.browse_input_btn.clicked.connect(self.browse_input)

        input_path_layout = QHBoxLayout()
        input_path_layout.addWidget(self.input_path_edit)
        input_path_layout.addWidget(self.browse_input_btn)
        self.input_path_label = QLabel(tr("sub_tabs.input_path") + ":")
        input_layout.addRow(self.input_path_label, input_path_layout)

        # 输出目录选择
        self.output_dir_edit = QLineEdit()
        self.browse_output_btn = QPushButton(tr("buttons.browse_ellipsis"))
        self.browse_output_btn.clicked.connect(self.browse_output)

        output_dir_layout = QHBoxLayout()
        output_dir_layout.addWidget(self.output_dir_edit)
        output_dir_layout.addWidget(self.browse_output_btn)
        self.output_dir_label = QLabel(tr("sub_tabs.output_root_directory") + ":")
        input_layout.addRow(self.output_dir_label, output_dir_layout)

        # 添加说明标签
        self.output_note = QLabel(tr("notes.output_subdirs"))
        self.output_note.setStyleSheet("color: #666666; font-size: 10px;")
        input_layout.addRow("", self.output_note)

        # 配置文件选择
        self.config_path_edit = QLineEdit()
        self.browse_config_btn = QPushButton(tr("buttons.browse_ellipsis"))
        self.browse_config_btn.clicked.connect(self.browse_config)

        config_path_layout = QHBoxLayout()
        config_path_layout.addWidget(self.config_path_edit)
        config_path_layout.addWidget(self.browse_config_btn)
        self.config_path_label = QLabel(tr("files.config_file_optional") + ":")
        input_layout.addRow(self.config_path_label, config_path_layout)

        self.input_group.setLayout(input_layout)
        main_layout.addWidget(self.input_group)

        # 创建参数设置区域
        self.params_group = QGroupBox(tr("ui.parameter_settings"))
        params_layout = QFormLayout()

        # 目标PNG分辨率设置
        self.resolution_spin = QSpinBox()
        self.resolution_spin.setRange(1000, 10000)
        self.resolution_spin.setValue(4000)
        self.resolution_spin.setSingleStep(100)
        self.resolution_label = QLabel(tr("sub_tabs.target_png_resolution") + ":")
        params_layout.addRow(self.resolution_label, self.resolution_spin)

        # 边缘空隙比例设置
        self.padding_spin = QDoubleSpinBox()
        self.padding_spin.setRange(0.0, 10.0)
        self.padding_spin.setValue(3.0)
        self.padding_spin.setSingleStep(0.1)
        self.padding_spin.setSuffix("%")
        self.padding_label = QLabel(tr("sub_tabs.edge_padding_ratio") + ":")
        params_layout.addRow(self.padding_label, self.padding_spin)

        # 线条粗细设置
        self.line_thickness_spin = QSpinBox()
        self.line_thickness_spin.setRange(1, 10)
        self.line_thickness_spin.setValue(1)
        self.line_thickness_label = QLabel(tr("sub_tabs.line_thickness") + ":")
        params_layout.addRow(self.line_thickness_label, self.line_thickness_spin)

        self.params_group.setLayout(params_layout)
        main_layout.addWidget(self.params_group)

        # 创建进度显示区域
        self.progress_group = QGroupBox(tr("ui.progress_display"))
        progress_layout = QVBoxLayout()

        # 总体进度条
        self.overall_progress_label = QLabel(tr("progress.overall") + ":")
        progress_layout.addWidget(self.overall_progress_label)
        self.total_progress_bar = QProgressBar()
        progress_layout.addWidget(self.total_progress_bar)

        # 当前步骤进度条
        self.current_step_label = QLabel(tr("progress.current_step") + ":")
        progress_layout.addWidget(self.current_step_label)
        self.step_progress_bar = QProgressBar()
        progress_layout.addWidget(self.step_progress_bar)

        # 处理状态文本
        self.status_label = QLabel(tr("status.ready"))
        progress_layout.addWidget(self.status_label)

        self.progress_group.setLayout(progress_layout)
        main_layout.addWidget(self.progress_group)

        # 创建按钮区域
        button_layout = QHBoxLayout()

        self.start_button = QPushButton(tr("buttons.start_processing"))
        self.start_button.clicked.connect(self.start_processing)

        self.cancel_button = QPushButton(tr("buttons.cancel"))
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
            self.browse_input_btn.setText(tr("sub_tabs.browse_file"))
        else:
            self.browse_input_btn.setText(tr("sub_tabs.browse_directory"))

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
                    # 找到了data目录，建议使用项目根目录作为输出目录
                    # 脚本会在此目录下自动创建 img/png_manual_filter 和 img/svg_manual_filter
                    self.output_dir_edit.setText(str(project_dir))
                    return
            except Exception:
                pass

        # 如果无法确定标准路径，则使用输入目录的上级目录
        # 脚本会在此目录下自动创建 img/png_manual_filter 和 img/svg_manual_filter
        suggested_dir = parent_dir.parent
        self.output_dir_edit.setText(str(suggested_dir))

    def browse_output(self):
        """浏览输出根目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择输出根目录（将在此目录下创建img子目录）"
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
        params = {
            'resolution': resolution,
            'padding_ratio': padding_ratio,
            'line_thickness': line_thickness,
            'is_batch': is_batch
        }

        if is_batch:
            self.log_message.emit(f"开始批量半自动处理流程...\n输入目录: {input_path}\n输出根目录: {output_dir}\n将创建: {output_dir}/img/png_manual_filter 和 {output_dir}/img/svg_manual_filter")
        else:
            self.log_message.emit(f"开始单文件半自动处理流程...\n输入文件: {input_path}\n输出根目录: {output_dir}\n将创建: {output_dir}/img/png_manual_filter 和 {output_dir}/img/svg_manual_filter")

        # 通知父标签页当前正在运行半自动流程
        # 需要找到ProcessTab实例（可能是parent的parent）
        parent_widget = self.parent()
        while parent_widget and not hasattr(parent_widget, 'set_active_processing_tab'):
            parent_widget = parent_widget.parent()
        if parent_widget:
            parent_widget.set_active_processing_tab('semi')

        # 启动处理线程
        self.process_module.start_semi_process(
            input_path=input_path,
            output_dir=output_dir,
            config_path=config_path,
            params=params
        )

    def cancel_processing(self):
        """取消处理"""
        # 调用处理模块的取消方法
        self.process_module.cancel_processing()

        # 重置活动标签页
        parent_widget = self.parent()
        while parent_widget and not hasattr(parent_widget, 'set_active_processing_tab'):
            parent_widget = parent_widget.parent()
        if parent_widget:
            parent_widget.set_active_processing_tab(None)

        # 更新UI状态
        self.status_label.setText("已取消")
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

        # 记录日志
        self.log_message.emit("半自动处理流程已取消")

    def update_progress(self, progress, status=None):
        """更新进度和状态"""
        # 处理不同类型的进度值
        if isinstance(progress, (int, float)):
            if progress <= 1.0:
                # 如果是0-1范围，转换为0-100
                progress_value = int(progress * 100)
            else:
                # 如果已经是0-100范围
                progress_value = int(progress)
        else:
            progress_value = 0

        # 更新总体进度条
        self.total_progress_bar.setValue(progress_value)

        # 更新状态文本
        if status is not None:
            self.status_label.setText(status)

    def update_step_progress(self, progress, status=None):
        """更新步骤进度"""
        # 处理不同类型的进度值
        if isinstance(progress, (int, float)):
            if progress <= 1.0:
                # 如果是0-1范围，转换为0-100
                progress_value = int(progress * 100)
            else:
                # 如果已经是0-100范围
                progress_value = int(progress)
        else:
            progress_value = 0

        # 更新当前步骤进度条
        self.step_progress_bar.setValue(progress_value)

        # 更新状态文本
        if status is not None:
            self.status_label.setText(f"正在处理: {status}")

    def processing_completed(self, success, message):
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
            self.log_message.emit(f"半自动处理流程完成: {message}")

            # 显示完成消息弹窗
            QMessageBox.information(self, "处理完成",
                                   f"半自动处理流程已完成！\n\n{message}")
        else:
            # 处理失败
            self.status_label.setText(tr("status_messages.failed"))
            self.log_message.emit(f"{tr('log_messages.semi_process_failed')}: {message}")
            QMessageBox.warning(self, tr("error_messages.processing_failed"),
                               f"{tr('log_messages.semi_process_failed')}:\n\n{message}")

    def on_language_changed(self):
        """响应语言切换事件"""
        # 更新组框标题
        self.input_group.setTitle(tr("ui.input_settings"))
        self.params_group.setTitle(tr("ui.parameter_settings"))
        self.progress_group.setTitle(tr("ui.progress_display"))

        # 更新标签文本
        self.processing_mode_label.setText(tr("sub_tabs.processing_mode") + ":")
        self.input_path_label.setText(tr("sub_tabs.input_path") + ":")
        self.output_dir_label.setText(tr("sub_tabs.output_root_directory") + ":")
        self.config_path_label.setText(tr("files.config_file_optional") + ":")

        # 更新单选按钮
        self.single_file_radio.setText(tr("sub_tabs.single_file"))
        self.batch_dir_radio.setText(tr("sub_tabs.batch_directory"))

        # 更新参数标签
        self.resolution_label.setText(tr("sub_tabs.target_png_resolution") + ":")
        self.padding_label.setText(tr("sub_tabs.edge_padding_ratio") + ":")
        self.line_thickness_label.setText(tr("sub_tabs.line_thickness") + ":")

        # 更新进度标签
        self.overall_progress_label.setText(tr("progress.overall") + ":")
        self.current_step_label.setText(tr("progress.current_step") + ":")
        self.status_label.setText(tr("status.ready"))

        # 更新按钮文本
        self.browse_input_btn.setText(tr("buttons.browse_ellipsis"))
        self.browse_output_btn.setText(tr("buttons.browse_ellipsis"))
        self.browse_config_btn.setText(tr("buttons.browse_ellipsis"))
        self.start_button.setText(tr("buttons.start_processing"))
        self.cancel_button.setText(tr("buttons.cancel"))

        # 更新说明文本
        self.output_note.setText(tr("notes.output_subdirs"))

        # 更新输入模式按钮文本
        self.update_input_mode()

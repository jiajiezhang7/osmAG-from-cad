#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAD预处理标签页

此模块实现了CAD预处理标签页，包含完整流程和半自动流程两个子标签页。
"""

import os
import sys
from pathlib import Path

# 导入PyQt5组件
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QPushButton,
    QLabel, QLineEdit, QFileDialog, QComboBox, QCheckBox,
    QSpinBox, QDoubleSpinBox, QProgressBar, QGroupBox,
    QFormLayout, QRadioButton, QButtonGroup, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QSettings

# 导入处理模块
from modules.process_module import ProcessModule
# 导入子标签页模块
from .full_process_tab import FullProcessTab
from .semi_process_tab import SemiProcessTab

# 导入语言管理器
from utils.language_manager import tr

class ProcessTab(QWidget):
    """
    CAD预处理标签页，包含完整流程和半自动流程两个子标签页
    """

    # 定义信号，用于向主窗口发送日志消息
    log_message = pyqtSignal(str)

    def __init__(self, project_manager):
        super().__init__()

        # 保存项目管理器引用
        self.project_manager = project_manager

        # 初始化处理模块
        self.process_module = ProcessModule(self)

        # 跟踪当前正在运行的标签页
        self.active_processing_tab = None

        # 初始化UI
        self.init_ui()

    def init_ui(self):
        """初始化用户界面"""
        # 创建主布局
        main_layout = QVBoxLayout(self)

        # 创建项目选择区域
        self.project_group = QGroupBox(tr("project.selection"))
        project_layout = QHBoxLayout()

        self.project_combo = QComboBox()
        self.project_combo.addItems(self.project_manager.get_project_list())
        if self.project_manager.get_current_project():
            self.project_combo.setCurrentText(self.project_manager.get_current_project())

        self.refresh_project_btn = QPushButton(tr("project.refresh"))
        self.refresh_project_btn.clicked.connect(self.refresh_projects)

        self.select_project_label = QLabel(tr("project.select_project"))
        project_layout.addWidget(self.select_project_label)
        project_layout.addWidget(self.project_combo, 1)
        project_layout.addWidget(self.refresh_project_btn)

        self.project_group.setLayout(project_layout)
        main_layout.addWidget(self.project_group)

        # 创建子标签页
        self.tab_widget = QTabWidget()

        # 创建完整流程标签页
        self.full_process_tab = FullProcessTab(self.project_manager, self.process_module)
        self.full_process_tab.log_message.connect(self.forward_log_message)

        # 创建半自动流程标签页
        self.semi_process_tab = SemiProcessTab(self.project_manager, self.process_module)
        self.semi_process_tab.log_message.connect(self.forward_log_message)

        # 连接进程模块的信号到当前活动的标签页
        self.process_module.progress_updated.connect(self.route_progress_signal)
        self.process_module.step_progress_updated.connect(self.route_step_progress_signal)
        self.process_module.process_completed.connect(self.route_completion_signal)

        # 添加子标签页
        self.tab_widget.addTab(self.full_process_tab, tr("tabs.full_process"))
        self.tab_widget.addTab(self.semi_process_tab, tr("tabs.semi_process"))

        main_layout.addWidget(self.tab_widget)

    def refresh_projects(self):
        """刷新项目列表"""
        # 保存当前选择
        current_project = self.project_combo.currentText()

        # 清空并重新加载项目列表
        self.project_combo.clear()
        self.project_combo.addItems(self.project_manager.get_project_list())

        # 如果原项目仍然存在，则选中它
        if current_project in self.project_manager.get_project_list():
            self.project_combo.setCurrentText(current_project)
        elif self.project_manager.get_current_project():
            self.project_combo.setCurrentText(self.project_manager.get_current_project())

    def forward_log_message(self, message):
        """转发日志消息到主窗口"""
        self.log_message.emit(message)

    def route_progress_signal(self, progress, status=None):
        """根据正在运行的标签页路由进度信号"""
        if self.active_processing_tab == 'full':
            self.full_process_tab.update_progress(progress, status)
        elif self.active_processing_tab == 'semi':
            self.semi_process_tab.update_progress(progress, status)

    def route_step_progress_signal(self, progress, status=None):
        """根据正在运行的标签页路由步骤进度信号"""
        if self.active_processing_tab == 'full':
            self.full_process_tab.update_step_progress(progress, status)
        elif self.active_processing_tab == 'semi':
            self.semi_process_tab.update_step_progress(progress, status)

    def route_completion_signal(self, success, message):
        """根据正在运行的标签页路由完成信号"""
        if self.active_processing_tab == 'full':
            self.full_process_tab.processing_completed(success, message)
        elif self.active_processing_tab == 'semi':
            self.semi_process_tab.processing_completed(success, message)

        # 处理完成后重置活动标签页
        self.active_processing_tab = None

    def set_active_processing_tab(self, tab_type):
        """设置当前正在运行的标签页"""
        self.active_processing_tab = tab_type

    def on_language_changed(self):
        """响应语言切换事件"""
        # 更新项目选择区域
        self.project_group.setTitle(tr("project.selection"))
        self.select_project_label.setText(tr("project.select_project"))
        self.refresh_project_btn.setText(tr("project.refresh"))

        # 更新子标签页标题
        self.tab_widget.setTabText(0, tr("tabs.full_process"))
        self.tab_widget.setTabText(1, tr("tabs.semi_process"))

        # 通知子标签页更新语言
        if hasattr(self.full_process_tab, 'on_language_changed'):
            self.full_process_tab.on_language_changed()
        if hasattr(self.semi_process_tab, 'on_language_changed'):
            self.semi_process_tab.on_language_changed()

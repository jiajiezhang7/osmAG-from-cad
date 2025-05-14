#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAD2OSM图形界面应用主窗口

此模块实现了CAD2OSM图形界面应用的主窗口，包含选项卡式界面和基本功能。
"""

import sys
import os
from pathlib import Path

# 导入PyQt5组件
from PyQt5.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStatusBar, QAction, QFileDialog,
    QMessageBox, QSplitter, QTextEdit, QApplication
)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QSettings
from PyQt5.QtGui import QIcon, QFont

# 导入各个标签页
from ui.process_tab import ProcessTab
from ui.text_tab import TextTab
from ui.merge_tab import MergeTab
from ui.direction_tab import DirectionTab

# 导入项目管理器
from utils.project_manager import ProjectManager

class MainWindow(QMainWindow):
    """CAD2OSM图形界面应用的主窗口类"""
    
    def __init__(self):
        super().__init__()
        
        # 初始化窗口属性
        self.setWindowTitle("CAD2OSM图形界面应用")
        self.setMinimumSize(1000, 700)
        
        # 初始化项目管理器
        self.project_manager = ProjectManager()
        
        # 初始化UI
        self.init_ui()
        
        # 加载设置
        self.load_settings()
    
    def init_ui(self):
        """初始化用户界面"""
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建选项卡部件
        self.tab_widget = QTabWidget()
        
        # 创建各个标签页
        self.process_tab = ProcessTab(self.project_manager)
        self.text_tab = TextTab(self.project_manager)
        self.merge_tab = MergeTab(self.project_manager)
        self.direction_tab = DirectionTab(self.project_manager)
        
        # 添加标签页到选项卡部件
        self.tab_widget.addTab(self.process_tab, "CAD预处理")
        self.tab_widget.addTab(self.text_tab, "文本提取")
        self.tab_widget.addTab(self.merge_tab, "OSM合并")
        self.tab_widget.addTab(self.direction_tab, "方向校正")
        
        # 创建日志区域
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier New", 9))
        
        # 创建分割器，允许调整标签页和日志区域的大小
        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(self.tab_widget)
        splitter.addWidget(self.log_text)
        splitter.setSizes([500, 200])  # 设置初始大小
        
        # 添加分割器到主布局
        main_layout.addWidget(splitter)
        
        # 创建状态栏
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("就绪")
        
        # 创建菜单栏
        self.create_menu_bar()
    
    def create_menu_bar(self):
        """创建菜单栏"""
        # 创建菜单栏
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        # 新建项目动作
        new_project_action = QAction("新建项目", self)
        new_project_action.triggered.connect(self.create_new_project)
        file_menu.addAction(new_project_action)
        
        # 打开项目动作
        open_project_action = QAction("打开项目", self)
        open_project_action.triggered.connect(self.open_project)
        file_menu.addAction(open_project_action)
        
        file_menu.addSeparator()
        
        # 退出动作
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu("帮助")
        
        # 关于动作
        about_action = QAction("关于", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
    
    def create_new_project(self):
        """创建新项目"""
        # 这里将实现创建新项目的功能
        QMessageBox.information(self, "功能开发中", "创建新项目功能正在开发中...")
    
    def open_project(self):
        """打开现有项目"""
        # 这里将实现打开现有项目的功能
        QMessageBox.information(self, "功能开发中", "打开项目功能正在开发中...")
    
    def show_about_dialog(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于CAD2OSM", 
                          "<h3>CAD2OSM图形界面应用</h3>"
                          "<p>版本: 1.0.0</p>"
                          "<p>这是一个用于CAD到OSM转换的图形界面工具，包含以下功能：</p>"
                          "<ul>"
                          "<li>CAD预处理：DWG到PNG的转换</li>"
                          "<li>文本提取：从DXF提取文本并添加到OSM</li>"
                          "<li>OSM合并：合并多个OSM文件</li>"
                          "<li>方向校正：校正OSM中多边形的方向</li>"
                          "</ul>"
                          "<p>© 2025 AGSeg团队</p>")
    
    def load_settings(self):
        """加载应用程序设置"""
        settings = QSettings()
        
        # 恢复窗口位置和大小
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        
        # 恢复窗口状态（最大化等）
        state = settings.value("windowState")
        if state:
            self.restoreState(state)
    
    def closeEvent(self, event):
        """窗口关闭事件，保存设置"""
        # 保存窗口位置和大小
        settings = QSettings()
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())
        
        # 调用父类方法
        super().closeEvent(event)
    
    def log_message(self, message):
        """向日志区域添加消息"""
        self.log_text.append(message)
        # 滚动到底部
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

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
    QMessageBox, QSplitter, QTextEdit, QApplication, QMenu
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

# 导入语言管理器
from utils.language_manager import language_manager, tr

class MainWindow(QMainWindow):
    """CAD2OSM图形界面应用的主窗口类"""

    def __init__(self):
        super().__init__()

        # 初始化项目管理器
        self.project_manager = ProjectManager()

        # 连接语言切换信号
        language_manager.language_changed.connect(self.on_language_changed)

        # 初始化窗口属性
        self.setWindowTitle(tr("app.title"))
        self.setMinimumSize(1000, 700)

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

        # 连接日志信号
        self.process_tab.log_message.connect(self.log_message)
        self.text_tab.log_message.connect(self.log_message)
        self.merge_tab.log_message.connect(self.log_message)
        self.direction_tab.log_message.connect(self.log_message)

        # 添加标签页到选项卡部件
        self.tab_widget.addTab(self.process_tab, tr("tabs.process"))
        self.tab_widget.addTab(self.text_tab, tr("tabs.text"))
        self.tab_widget.addTab(self.merge_tab, tr("tabs.merge"))
        self.tab_widget.addTab(self.direction_tab, tr("tabs.direction"))

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
        self.statusBar.showMessage(tr("app.ready"))

        # 创建菜单栏
        self.create_menu_bar()

    def create_menu_bar(self):
        """创建菜单栏"""
        # 创建菜单栏
        menubar = self.menuBar()

        # 文件菜单
        self.file_menu = menubar.addMenu(tr("menu.file"))

        # 新建项目动作
        self.new_project_action = QAction(tr("menu.new_project"), self)
        self.new_project_action.triggered.connect(self.create_new_project)
        self.file_menu.addAction(self.new_project_action)

        # 打开项目动作
        self.open_project_action = QAction(tr("menu.open_project"), self)
        self.open_project_action.triggered.connect(self.open_project)
        self.file_menu.addAction(self.open_project_action)

        self.file_menu.addSeparator()

        # 退出动作
        self.exit_action = QAction(tr("menu.exit"), self)
        self.exit_action.triggered.connect(self.close)
        self.file_menu.addAction(self.exit_action)

        # 语言菜单
        self.language_menu = menubar.addMenu(tr("menu.language"))
        self.create_language_menu()

        # 帮助菜单
        self.help_menu = menubar.addMenu(tr("menu.help"))

        # 关于动作
        self.about_action = QAction(tr("menu.about"), self)
        self.about_action.triggered.connect(self.show_about_dialog)
        self.help_menu.addAction(self.about_action)

    def create_language_menu(self):
        """创建语言菜单"""
        # 获取支持的语言
        languages = language_manager.get_supported_languages()
        current_language = language_manager.get_current_language()

        # 创建语言动作
        self.language_actions = {}
        for lang_code, lang_name in languages.items():
            action = QAction(tr(f"menu.{lang_code.lower()}"), self)
            action.setCheckable(True)
            action.setChecked(lang_code == current_language)
            action.triggered.connect(lambda checked, code=lang_code: self.switch_language(code))
            self.language_menu.addAction(action)
            self.language_actions[lang_code] = action

    def switch_language(self, language_code):
        """切换语言"""
        if language_manager.switch_language(language_code):
            # 更新语言动作的选中状态
            for code, action in self.language_actions.items():
                action.setChecked(code == language_code)

            # 显示切换成功消息
            QMessageBox.information(self, tr("messages.language_switched"),
                                   tr("messages.language_switch_success"))

    def create_new_project(self):
        """创建新项目"""
        # 这里将实现创建新项目的功能
        QMessageBox.information(self, tr("messages.feature_in_development"),
                               tr("messages.new_project_developing"))

    def open_project(self):
        """打开现有项目"""
        # 这里将实现打开现有项目的功能
        QMessageBox.information(self, tr("messages.feature_in_development"),
                               tr("messages.open_project_developing"))

    def show_about_dialog(self):
        """显示关于对话框"""
        features = tr("about.features")
        features_html = ""
        if isinstance(features, list):
            features_html = "<ul>"
            for feature in features:
                features_html += f"<li>{feature}</li>"
            features_html += "</ul>"

        about_text = (
            f"<h3>{tr('app.title')}</h3>"
            f"<p>{tr('about.version')}</p>"
            f"<p>{tr('about.description')}</p>"
            f"{features_html}"
            f"<p>{tr('about.copyright')}</p>"
        )

        QMessageBox.about(self, tr("about.title"), about_text)

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

    def on_language_changed(self, language_code):
        """响应语言切换事件"""
        # 更新窗口标题
        self.setWindowTitle(tr("app.title"))

        # 更新菜单文本
        self.file_menu.setTitle(tr("menu.file"))
        self.new_project_action.setText(tr("menu.new_project"))
        self.open_project_action.setText(tr("menu.open_project"))
        self.exit_action.setText(tr("menu.exit"))

        self.language_menu.setTitle(tr("menu.language"))

        self.help_menu.setTitle(tr("menu.help"))
        self.about_action.setText(tr("menu.about"))

        # 更新语言菜单项文本
        for lang_code, action in self.language_actions.items():
            action.setText(tr(f"menu.{lang_code.lower()}"))

        # 更新标签页标题
        self.tab_widget.setTabText(0, tr("tabs.process"))
        self.tab_widget.setTabText(1, tr("tabs.text"))
        self.tab_widget.setTabText(2, tr("tabs.merge"))
        self.tab_widget.setTabText(3, tr("tabs.direction"))

        # 更新状态栏
        self.statusBar.showMessage(tr("app.ready"))

        # 通知各个标签页更新语言
        if hasattr(self.process_tab, 'on_language_changed'):
            self.process_tab.on_language_changed()
        if hasattr(self.text_tab, 'on_language_changed'):
            self.text_tab.on_language_changed()
        if hasattr(self.merge_tab, 'on_language_changed'):
            self.merge_tab.on_language_changed()
        if hasattr(self.direction_tab, 'on_language_changed'):
            self.direction_tab.on_language_changed()

    def log_message(self, message):
        """向日志区域添加消息"""
        self.log_text.append(message)
        # 滚动到底部
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

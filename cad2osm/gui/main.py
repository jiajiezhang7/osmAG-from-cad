#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAD2OSM图形界面应用入口点

此脚本是CAD2OSM图形界面应用的主入口，启动主窗口并初始化应用。
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# 导入PyQt5
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTranslator, QLocale

# 导入主窗口
from ui.main_window import MainWindow

# 导入语言管理器
from utils.language_manager import language_manager

def main():
    """应用程序入口点"""
    # 创建应用程序实例
    app = QApplication(sys.argv)

    # 设置应用程序名称和组织信息
    app.setApplicationName("CAD2OSM")
    app.setOrganizationName("AGSeg")

    # 初始化语言管理器（加载默认语言）
    language_manager.load_language("zh_CN")

    # 创建主窗口
    window = MainWindow()
    window.show()

    # 运行应用程序
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

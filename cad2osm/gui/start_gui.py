#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAD2OSM图形界面应用启动脚本

此脚本用于启动CAD2OSM图形界面应用。
"""

import os
import sys
from pathlib import Path

# 设置 Qt 平台插件路径以解决 "xcb" 加载问题
conda_prefix = os.environ.get('CONDA_PREFIX')
if conda_prefix:
    qt_plugin_path = os.path.join(conda_prefix, 'plugins')
    os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = qt_plugin_path
    # 您可以取消下面两行的注释来进行调试，以确认路径已设置
    # print(f"DEBUG: CONDA_PREFIX={conda_prefix}")
    # print(f"DEBUG: QT_QPA_PLATFORM_PLUGIN_PATH={os.environ.get('QT_QPA_PLATFORM_PLUGIN_PATH')}")
elif 'QT_QPA_PLATFORM_PLUGIN_PATH' not in os.environ:
    # 如果 CONDA_PREFIX 未设置，且用户也未手动设置 QT_QPA_PLATFORM_PLUGIN_PATH
    # 则打印警告。在非 Conda 环境中，用户可能需要手动配置此变量。
    print("警告: CONDA_PREFIX 未设置，且 QT_QPA_PLATFORM_PLUGIN_PATH 也未在外部设置。")
    print("Qt 平台插件可能无法找到。如果遇到 'xcb' 插件错误，请确保正确设置 QT_QPA_PLATFORM_PLUGIN_PATH。")

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# 导入主模块
from main import main

if __name__ == "__main__":
    main()

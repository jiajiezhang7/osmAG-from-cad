#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAD2OSM图形界面应用启动脚本

此脚本用于启动CAD2OSM图形界面应用。
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# 导入主模块
from main import main

if __name__ == "__main__":
    main()

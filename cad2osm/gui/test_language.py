#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语言管理器测试脚本

此脚本用于测试语言管理器的功能，无需启动GUI界面。
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# 导入语言管理器
from utils.language_manager import language_manager, tr

def test_language_manager():
    """测试语言管理器功能"""
    print("=== 语言管理器测试 ===")

    # 测试支持的语言
    print(f"支持的语言: {language_manager.get_supported_languages()}")

    # 测试当前语言
    print(f"当前语言: {language_manager.get_current_language()}")

    # 测试中文翻译
    print("\n=== 中文翻译测试 ===")
    print(f"应用标题: {tr('app.title')}")
    print(f"文件菜单: {tr('menu.file')}")
    print(f"新建项目: {tr('menu.new_project')}")
    print(f"标签页-处理: {tr('tabs.process')}")
    print(f"按钮-浏览: {tr('buttons.browse')}")
    print(f"状态-就绪: {tr('status.ready')}")

    # 测试新增的UI翻译
    print(f"输入设置: {tr('ui.input_settings')}")
    print(f"参数设置: {tr('ui.parameter_settings')}")
    print(f"进度显示: {tr('ui.progress_display')}")
    print(f"DXF文件: {tr('files.dxf_file')}")
    print(f"开始处理: {tr('buttons.start_processing')}")

    # 测试列表翻译
    features = tr("about.features")
    print(f"功能列表: {features}")

    # 切换到英文
    print("\n=== 切换到英文 ===")
    success = language_manager.switch_language("en_US")
    print(f"切换成功: {success}")
    print(f"当前语言: {language_manager.get_current_language()}")

    # 测试英文翻译
    print("\n=== 英文翻译测试 ===")
    print(f"App Title: {tr('app.title')}")
    print(f"File Menu: {tr('menu.file')}")
    print(f"New Project: {tr('menu.new_project')}")
    print(f"Tab-Process: {tr('tabs.process')}")
    print(f"Button-Browse: {tr('buttons.browse')}")
    print(f"Status-Ready: {tr('status.ready')}")

    # 测试新增的UI翻译
    print(f"Input Settings: {tr('ui.input_settings')}")
    print(f"Parameter Settings: {tr('ui.parameter_settings')}")
    print(f"Progress Display: {tr('ui.progress_display')}")
    print(f"DXF File: {tr('files.dxf_file')}")
    print(f"Start Processing: {tr('buttons.start_processing')}")

    # 测试列表翻译
    features = tr("about.features")
    print(f"Features List: {features}")

    # 切换回中文
    print("\n=== 切换回中文 ===")
    success = language_manager.switch_language("zh_CN")
    print(f"切换成功: {success}")
    print(f"当前语言: {language_manager.get_current_language()}")

    # 再次测试中文翻译
    print(f"应用标题: {tr('app.title')}")
    print(f"文件菜单: {tr('menu.file')}")

    # 测试不存在的键
    print("\n=== 错误处理测试 ===")
    print(f"不存在的键: {tr('nonexistent.key', '默认文本')}")
    print(f"不存在的键(无默认): {tr('nonexistent.key')}")

    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_language_manager()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语言切换功能演示脚本

此脚本演示了CAD2OSM GUI应用中各个UI组件的语言切换效果。
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# 导入语言管理器
from utils.language_manager import language_manager, tr

def demo_ui_components():
    """演示各个UI组件的语言切换"""

    def show_current_translations():
        """显示当前语言的翻译"""
        current_lang = language_manager.get_current_language()
        lang_name = language_manager.get_supported_languages()[current_lang]

        print(f"\n=== 当前语言: {lang_name} ({current_lang}) ===")

        # 主窗口组件
        print("\n【主窗口】")
        print(f"  应用标题: {tr('app.title')}")
        print(f"  文件菜单: {tr('menu.file')}")
        print(f"  语言菜单: {tr('menu.language')}")
        print(f"  帮助菜单: {tr('menu.help')}")

        # 标签页
        print("\n【标签页】")
        print(f"  CAD预处理: {tr('tabs.process')}")
        print(f"  文本提取: {tr('tabs.text')}")
        print(f"  OSM合并: {tr('tabs.merge')}")
        print(f"  方向校正: {tr('tabs.direction')}")

        # UI组件
        print("\n【UI组件】")
        print(f"  输入设置: {tr('ui.input_settings')}")
        print(f"  参数设置: {tr('ui.parameter_settings')}")
        print(f"  步骤控制: {tr('ui.step_control')}")
        print(f"  进度显示: {tr('ui.progress_display')}")
        print(f"  结果统计: {tr('ui.result_statistics')}")
        print(f"  结果预览: {tr('ui.result_preview')}")

        # 文件类型
        print("\n【文件类型】")
        print(f"  DXF文件: {tr('files.dxf_file')}")
        print(f"  OSM文件: {tr('files.osm_file')}")
        print(f"  边界文件: {tr('files.bounds_file')}")
        print(f"  输出文件: {tr('files.output_file')}")

        # 按钮
        print("\n【按钮】")
        print(f"  浏览: {tr('buttons.browse_ellipsis')}")
        print(f"  开始处理: {tr('buttons.start_processing')}")
        print(f"  开始合并: {tr('buttons.start_merging')}")
        print(f"  开始校正: {tr('buttons.start_correction')}")
        print(f"  取消: {tr('buttons.cancel')}")

        # 参数
        print("\n【参数设置】")
        print(f"  文本图层名称: {tr('params.layer_name')}")
        print(f"  附近匹配阈值: {tr('params.nearby_threshold')}")
        print(f"  中心距离比例: {tr('params.center_distance_ratio')}")
        print(f"  生成可视化: {tr('params.visualize')}")
        print(f"  区域类型: {tr('params.area_type')}")
        print(f"  偏移方法: {tr('params.offset_method')}")

        # 选项值
        print("\n【选项值】")
        print(f"  电梯: {tr('options.elevator')}")
        print(f"  楼梯: {tr('options.stairs')}")
        print(f"  两者: {tr('options.both')}")
        print(f"  质心: {tr('options.centroid')}")
        print(f"  顶点平均: {tr('options.vertex_average')}")

        # 统计信息
        print("\n【统计信息】")
        print(f"  匹配区域数量: {tr('stats.matched_areas')}")
        print(f"  纬度偏移量: {tr('stats.lat_offset')}")
        print(f"  经度偏移量: {tr('stats.lon_offset')}")
        print(f"  处理的way数量: {tr('stats.processed_ways')}")
        print(f"  反转的way数量: {tr('stats.reversed_ways')}")

        # 状态
        print("\n【状态】")
        print(f"  就绪: {tr('status.ready')}")
        print(f"  处理中: {tr('status.processing')}")
        print(f"  已完成: {tr('status.completed')}")
        print(f"  已停止: {tr('status.stopped')}")

        # 子标签页相关
        print("\n【子标签页组件】")
        print(f"  处理模式: {tr('sub_tabs.processing_mode')}")
        print(f"  单个文件: {tr('sub_tabs.single_file')}")
        print(f"  批量处理目录: {tr('sub_tabs.batch_directory')}")
        print(f"  浏览文件: {tr('sub_tabs.browse_file')}")
        print(f"  浏览目录: {tr('sub_tabs.browse_directory')}")
        print(f"  输入路径: {tr('sub_tabs.input_path')}")
        print(f"  输出根目录: {tr('sub_tabs.output_root_directory')}")
        print(f"  配置文件(可选): {tr('files.config_file_optional')}")
        print(f"  目标PNG分辨率: {tr('sub_tabs.target_png_resolution')}")
        print(f"  边缘空隙比例: {tr('sub_tabs.edge_padding_ratio')}")
        print(f"  线条粗细: {tr('sub_tabs.line_thickness')}")
        print(f"  跳过DWG→DXF: {tr('sub_tabs.skip_dwg_to_dxf')}")
        print(f"  跳过DXF过滤: {tr('sub_tabs.skip_dxf_filter')}")
        print(f"  跳过DXF→SVG: {tr('sub_tabs.skip_dxf_to_svg')}")
        print(f"  跳过SVG→PNG: {tr('sub_tabs.skip_svg_to_png')}")
        print(f"  正在处理文件: {tr('status_messages.processing_file')}")

    print("=== CAD2OSM GUI 语言切换功能演示 ===")

    # 显示中文界面
    language_manager.switch_language("zh_CN")
    show_current_translations()

    print("\n" + "="*60)

    # 显示英文界面
    language_manager.switch_language("en_US")
    show_current_translations()

    print("\n" + "="*60)

    # 切换回中文
    language_manager.switch_language("zh_CN")
    print(f"\n=== 演示完成，当前语言: {language_manager.get_current_language()} ===")

    print("\n【功能特点】")
    print("✅ 支持中英文双语切换")
    print("✅ 覆盖所有主要UI组件")
    print("✅ 实时切换，无需重启")
    print("✅ 保存用户选择")
    print("✅ 扩展性强，易于添加新语言")

    print("\n【使用方法】")
    print("1. 启动GUI应用: python cad2osm/gui/main.py")
    print("2. 点击菜单栏 '语言/Language'")
    print("3. 选择 '中文' 或 'English'")
    print("4. 界面立即切换到选择的语言")

if __name__ == "__main__":
    demo_ui_components()

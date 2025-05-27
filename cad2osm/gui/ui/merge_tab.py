#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSM合并标签页

此模块实现了OSM合并标签页，用于合并多个OSM文件。
"""

import os
import sys
from pathlib import Path

# 导入PyQt5组件
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QFileDialog, QComboBox, QCheckBox,
    QSpinBox, QDoubleSpinBox, QProgressBar, QGroupBox,
    QFormLayout, QRadioButton, QButtonGroup, QMessageBox,
    QListWidget, QAbstractItemView
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QSettings

# 导入合并模块
from modules.merge_module import MergeModule

# 导入语言管理器
from utils.language_manager import tr

class MergeTab(QWidget):
    """
    OSM合并标签页，用于合并多个OSM文件
    """

    # 定义信号，用于向主窗口发送日志消息
    log_message = pyqtSignal(str)

    def __init__(self, project_manager):
        super().__init__()

        # 保存项目管理器引用
        self.project_manager = project_manager

        # 初始化合并模块
        self.merge_module = MergeModule(self)

        # 连接合并模块的信号
        self.merge_module.progress_updated.connect(self.update_progress_signal)
        self.merge_module.process_completed.connect(self.merging_completed_signal)

        # 初始化UI
        self.init_ui()

    def init_ui(self):
        """初始化用户界面"""
        # 创建主布局
        main_layout = QVBoxLayout(self)

        # 创建输入区域
        self.input_group = QGroupBox(tr("ui.input_settings"))
        input_layout = QFormLayout()

        # 参照OSM文件选择
        self.ref_path_edit = QLineEdit()
        self.browse_ref_btn = QPushButton(tr("buttons.browse_ellipsis"))
        self.browse_ref_btn.clicked.connect(self.browse_ref)

        ref_path_layout = QHBoxLayout()
        ref_path_layout.addWidget(self.ref_path_edit)
        ref_path_layout.addWidget(self.browse_ref_btn)
        self.ref_label = QLabel(tr("files.reference_osm") + ":")
        input_layout.addRow(self.ref_label, ref_path_layout)

        # 目标OSM文件选择
        self.target_list = QListWidget()
        self.target_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.target_list.setMinimumHeight(150)

        target_list_layout = QVBoxLayout()
        target_list_layout.addWidget(self.target_list)

        target_buttons_layout = QHBoxLayout()
        self.add_target_btn = QPushButton(tr("buttons.add"))
        self.add_target_btn.clicked.connect(self.add_target)
        self.remove_target_btn = QPushButton(tr("buttons.remove"))
        self.remove_target_btn.clicked.connect(self.remove_target)
        self.clear_targets_btn = QPushButton(tr("buttons.clear"))
        self.clear_targets_btn.clicked.connect(self.clear_targets)

        target_buttons_layout.addWidget(self.add_target_btn)
        target_buttons_layout.addWidget(self.remove_target_btn)
        target_buttons_layout.addWidget(self.clear_targets_btn)

        target_list_layout.addLayout(target_buttons_layout)
        self.target_label = QLabel(tr("files.target_osm") + ":")
        input_layout.addRow(self.target_label, target_list_layout)

        # 输出文件路径
        self.output_path_edit = QLineEdit()
        self.browse_output_btn = QPushButton(tr("buttons.browse_ellipsis"))
        self.browse_output_btn.clicked.connect(self.browse_output)

        output_path_layout = QHBoxLayout()
        output_path_layout.addWidget(self.output_path_edit)
        output_path_layout.addWidget(self.browse_output_btn)
        self.output_label = QLabel(tr("files.output_file") + ":")
        input_layout.addRow(self.output_label, output_path_layout)

        self.input_group.setLayout(input_layout)
        main_layout.addWidget(self.input_group)

        # 创建参数设置区域
        self.params_group = QGroupBox(tr("ui.parameter_settings"))
        params_layout = QFormLayout()

        # 匹配区域类型选择
        self.area_type_combo = QComboBox()
        self.area_type_combo.addItems([tr("options.elevator"), tr("options.stairs"), tr("options.both")])
        self.area_type_combo.setCurrentIndex(2)  # 默认选择"两者"
        self.area_type_label = QLabel(tr("params.area_type") + ":")
        params_layout.addRow(self.area_type_label, self.area_type_combo)

        # 偏移计算方法选择
        self.offset_method_combo = QComboBox()
        self.offset_method_combo.addItems([tr("options.centroid"), tr("options.vertex_average")])
        self.offset_method_combo.setCurrentIndex(1)  # 默认选择"顶点平均"
        self.offset_method_label = QLabel(tr("params.offset_method") + ":")
        params_layout.addRow(self.offset_method_label, self.offset_method_combo)

        # 最小匹配区域数量设置
        self.min_matches_spin = QSpinBox()
        self.min_matches_spin.setRange(1, 10)
        self.min_matches_spin.setValue(2)
        self.min_matches_label = QLabel(tr("params.min_matches") + ":")
        params_layout.addRow(self.min_matches_label, self.min_matches_spin)

        self.params_group.setLayout(params_layout)
        main_layout.addWidget(self.params_group)

        # 创建结果统计区域
        self.stats_group = QGroupBox(tr("ui.result_statistics"))
        stats_layout = QFormLayout()

        self.matched_areas_label = QLabel("0")
        self.matched_areas_stat_label = QLabel(tr("stats.matched_areas") + ":")
        stats_layout.addRow(self.matched_areas_stat_label, self.matched_areas_label)

        self.lat_offset_label = QLabel("0.0")
        self.lat_offset_stat_label = QLabel(tr("stats.lat_offset") + ":")
        stats_layout.addRow(self.lat_offset_stat_label, self.lat_offset_label)

        self.lon_offset_label = QLabel("0.0")
        self.lon_offset_stat_label = QLabel(tr("stats.lon_offset") + ":")
        stats_layout.addRow(self.lon_offset_stat_label, self.lon_offset_label)

        self.stats_group.setLayout(stats_layout)
        main_layout.addWidget(self.stats_group)

        # 创建进度显示区域
        self.progress_group = QGroupBox(tr("ui.progress_display"))
        progress_layout = QVBoxLayout()

        # 总体进度条
        self.overall_progress_label = QLabel(tr("progress.overall") + ":")
        progress_layout.addWidget(self.overall_progress_label)
        self.total_progress_bar = QProgressBar()
        progress_layout.addWidget(self.total_progress_bar)

        # 处理状态文本
        self.status_label = QLabel(tr("status.ready"))
        progress_layout.addWidget(self.status_label)

        self.progress_group.setLayout(progress_layout)
        main_layout.addWidget(self.progress_group)

        # 创建按钮区域
        button_layout = QHBoxLayout()

        self.start_button = QPushButton(tr("buttons.start_merging"))
        self.start_button.clicked.connect(self.start_merging)

        self.cancel_button = QPushButton(tr("buttons.cancel"))
        self.cancel_button.clicked.connect(self.cancel_merging)
        self.cancel_button.setEnabled(False)

        button_layout.addStretch()
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.cancel_button)

        main_layout.addLayout(button_layout)

    def browse_ref(self):
        """浏览参照OSM文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择参照OSM文件", "", "OSM文件 (*.osm)"
        )
        if file_path:
            self.ref_path_edit.setText(file_path)
            # 自动设置输出文件路径
            self.suggest_output_path(file_path)

    def add_target(self):
        """添加目标OSM文件"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "选择目标OSM文件", "", "OSM文件 (*.osm)"
        )
        for file_path in file_paths:
            # 检查是否已经在列表中
            items = self.target_list.findItems(file_path, Qt.MatchExactly)
            if not items:
                self.target_list.addItem(file_path)

    def remove_target(self):
        """移除选中的目标OSM文件"""
        for item in self.target_list.selectedItems():
            self.target_list.takeItem(self.target_list.row(item))

    def clear_targets(self):
        """清空目标OSM文件列表"""
        self.target_list.clear()

    def browse_output(self):
        """浏览输出文件"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "选择输出文件", "", "OSM文件 (*.osm)"
        )
        if file_path:
            self.output_path_edit.setText(file_path)

    def suggest_output_path(self, ref_path):
        """根据参照文件路径自动建议输出文件路径"""
        if not self.output_path_edit.text():
            ref_file = Path(ref_path)
            # 尝试找到标准输出目录
            try:
                project_dir = ref_file.parent
                while project_dir.name not in ['osm', ''] and project_dir.parent != project_dir:
                    project_dir = project_dir.parent

                if project_dir.name == 'osm':
                    # 找到了osm目录，建议使用标准输出路径
                    output_dir = project_dir / 'merged'
                    output_dir.mkdir(parents=True, exist_ok=True)
                    output_path = output_dir / f"{ref_file.stem}_merged.osm"
                    self.output_path_edit.setText(str(output_path))
                    return
            except Exception:
                pass

            # 如果无法确定标准路径，则使用参照文件所在目录
            output_path = ref_file.with_name(f"{ref_file.stem}_merged.osm")
            self.output_path_edit.setText(str(output_path))

    def start_merging(self):
        """开始合并"""
        # 验证输入
        ref_path = self.ref_path_edit.text().strip()
        if not ref_path:
            QMessageBox.warning(self, "输入错误", "请选择参照OSM文件")
            return

        if self.target_list.count() == 0:
            QMessageBox.warning(self, "输入错误", "请添加至少一个目标OSM文件")
            return

        output_path = self.output_path_edit.text().strip()
        if not output_path:
            QMessageBox.warning(self, "输入错误", "请选择输出文件路径")
            return

        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 获取目标文件列表
        target_files = []
        for i in range(self.target_list.count()):
            target_files.append(self.target_list.item(i).text())

        # 获取参数
        area_type = self.area_type_combo.currentText()
        offset_method = self.offset_method_combo.currentText()
        min_matches = self.min_matches_spin.value()

        # 禁用开始按钮，启用取消按钮
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)

        # 重置统计信息
        self.matched_areas_label.setText("0")
        self.lat_offset_label.setText("0.0")
        self.lon_offset_label.setText("0.0")

        # 更新状态
        self.status_label.setText("正在处理...")
        self.total_progress_bar.setValue(0)

        # 调用合并模块
        self.log_message.emit(f"开始合并OSM文件...\n参照: {ref_path}\n目标: {len(target_files)}个文件\n输出: {output_path}")

        # 启动处理线程
        self.merge_module.start_merging(
            ref_path=ref_path,
            target_files=target_files,
            output_path=output_path,
            area_type=area_type,
            offset_method=offset_method,
            min_matches=min_matches,
            progress_callback=self.update_progress,
            completion_callback=self.merging_completed
        )

    def cancel_merging(self):
        """取消合并"""
        # 调用合并模块的取消方法
        self.merge_module.cancel_merging()

        # 更新UI状态
        self.status_label.setText("已取消")
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

        # 记录日志
        self.log_message.emit("OSM合并已取消")

    def update_progress_signal(self, progress, status=None):
        """更新进度（信号连接用）"""
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

        # 更新进度条
        self.total_progress_bar.setValue(progress_value)

        # 更新状态文本
        if status is not None:
            self.status_label.setText(status)

    def merging_completed_signal(self, success, message):
        """合并完成（信号连接用）"""
        # 更新UI状态
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

        if success:
            # 成功完成
            self.status_label.setText("完成")
            self.total_progress_bar.setValue(100)
            self.log_message.emit(f"OSM合并完成: {message}")
            QMessageBox.information(self, "合并完成",
                                   f"OSM合并已完成！\n\n{message}")
        else:
            # 处理失败
            self.status_label.setText("失败")
            self.log_message.emit(f"OSM合并失败: {message}")
            QMessageBox.warning(self, "合并失败", f"OSM合并过程中出现错误:\n\n{message}")

    def update_progress(self, progress, matched_areas=None, lat_offset=None, lon_offset=None, status=None):
        """更新进度和状态"""
        # 更新进度条
        self.total_progress_bar.setValue(int(progress * 100))

        # 更新统计信息
        if matched_areas is not None:
            self.matched_areas_label.setText(str(matched_areas))

        if lat_offset is not None:
            self.lat_offset_label.setText(f"{lat_offset:.6f}")

        if lon_offset is not None:
            self.lon_offset_label.setText(f"{lon_offset:.6f}")

        # 更新状态文本
        if status is not None:
            self.status_label.setText(status)

    def merging_completed(self, success, message, matched_areas=0, lat_offset=0.0, lon_offset=0.0):
        """合并完成回调"""
        # 更新UI状态
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

        # 更新统计信息
        self.matched_areas_label.setText(str(matched_areas))
        self.lat_offset_label.setText(f"{lat_offset:.6f}")
        self.lon_offset_label.setText(f"{lon_offset:.6f}")

        if success:
            # 成功完成
            self.status_label.setText("完成")
            self.total_progress_bar.setValue(100)
            self.log_message.emit(f"OSM合并完成: {message}")
            QMessageBox.information(self, "合并完成",
                                   f"OSM合并已完成。\n\n匹配区域数量: {matched_areas}\n纬度偏移量: {lat_offset:.6f}\n经度偏移量: {lon_offset:.6f}")
        else:
            # 处理失败
            self.status_label.setText("失败")
            self.log_message.emit(f"OSM合并失败: {message}")
            QMessageBox.warning(self, "合并失败", f"OSM合并过程中出现错误: {message}")

    def on_language_changed(self):
        """响应语言切换事件"""
        # 更新组框标题
        self.input_group.setTitle(tr("ui.input_settings"))
        self.params_group.setTitle(tr("ui.parameter_settings"))
        self.stats_group.setTitle(tr("ui.result_statistics"))
        self.progress_group.setTitle(tr("ui.progress_display"))

        # 更新文件标签
        self.ref_label.setText(tr("files.reference_osm") + ":")
        self.target_label.setText(tr("files.target_osm") + ":")
        self.output_label.setText(tr("files.output_file") + ":")

        # 更新参数标签
        self.area_type_label.setText(tr("params.area_type") + ":")
        self.offset_method_label.setText(tr("params.offset_method") + ":")
        self.min_matches_label.setText(tr("params.min_matches") + ":")

        # 更新下拉框选项
        self.area_type_combo.clear()
        self.area_type_combo.addItems([tr("options.elevator"), tr("options.stairs"), tr("options.both")])
        self.area_type_combo.setCurrentIndex(2)

        self.offset_method_combo.clear()
        self.offset_method_combo.addItems([tr("options.centroid"), tr("options.vertex_average")])
        self.offset_method_combo.setCurrentIndex(1)

        # 更新统计标签
        self.matched_areas_stat_label.setText(tr("stats.matched_areas") + ":")
        self.lat_offset_stat_label.setText(tr("stats.lat_offset") + ":")
        self.lon_offset_stat_label.setText(tr("stats.lon_offset") + ":")

        # 更新进度标签
        self.overall_progress_label.setText(tr("progress.overall") + ":")
        self.status_label.setText(tr("status.ready"))

        # 更新按钮文本
        self.browse_ref_btn.setText(tr("buttons.browse_ellipsis"))
        self.browse_output_btn.setText(tr("buttons.browse_ellipsis"))
        self.add_target_btn.setText(tr("buttons.add"))
        self.remove_target_btn.setText(tr("buttons.remove"))
        self.clear_targets_btn.setText(tr("buttons.clear"))
        self.start_button.setText(tr("buttons.start_merging"))
        self.cancel_button.setText(tr("buttons.cancel"))

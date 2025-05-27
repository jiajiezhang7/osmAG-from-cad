#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
方向校正标签页

此模块实现了方向校正标签页，用于校正OSM文件中多边形的方向。
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
    QTextEdit
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QSettings

# 导入方向校正模块
from modules.direction_module import DirectionModule

# 导入语言管理器
from utils.language_manager import tr

class DirectionTab(QWidget):
    """
    方向校正标签页，用于校正OSM文件中多边形的方向
    """

    # 定义信号，用于向主窗口发送日志消息
    log_message = pyqtSignal(str)

    def __init__(self, project_manager):
        super().__init__()

        # 保存项目管理器引用
        self.project_manager = project_manager

        # 初始化方向校正模块
        self.direction_module = DirectionModule(self)

        # 连接方向校正模块的信号
        self.direction_module.progress_updated.connect(self.update_progress_signal)
        self.direction_module.process_completed.connect(self.correction_completed_signal)

        # 初始化UI
        self.init_ui()

    def init_ui(self):
        """初始化用户界面"""
        # 创建主布局
        main_layout = QVBoxLayout(self)

        # 创建输入区域
        self.input_group = QGroupBox(tr("ui.input_settings"))
        input_layout = QFormLayout()

        # OSM文件选择
        self.osm_path_edit = QLineEdit()
        self.browse_osm_btn = QPushButton(tr("buttons.browse_ellipsis"))
        self.browse_osm_btn.clicked.connect(self.browse_osm)

        osm_path_layout = QHBoxLayout()
        osm_path_layout.addWidget(self.osm_path_edit)
        osm_path_layout.addWidget(self.browse_osm_btn)
        self.osm_label = QLabel(tr("files.osm_file") + ":")
        input_layout.addRow(self.osm_label, osm_path_layout)

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

        # 创建规则说明区域
        self.rules_group = QGroupBox(tr("ui.rules_description"))
        rules_layout = QVBoxLayout()

        self.rules_text = QTextEdit()
        self.rules_text.setReadOnly(True)
        self.rules_text.setPlainText(tr("rules.direction_correction"))
        rules_layout.addWidget(self.rules_text)

        self.rules_group.setLayout(rules_layout)
        main_layout.addWidget(self.rules_group)

        # 创建结果统计区域
        self.stats_group = QGroupBox(tr("ui.result_statistics"))
        stats_layout = QFormLayout()

        self.processed_ways_label = QLabel("0")
        self.processed_ways_stat_label = QLabel(tr("stats.processed_ways") + ":")
        stats_layout.addRow(self.processed_ways_stat_label, self.processed_ways_label)

        self.reversed_ways_label = QLabel("0")
        self.reversed_ways_stat_label = QLabel(tr("stats.reversed_ways") + ":")
        stats_layout.addRow(self.reversed_ways_stat_label, self.reversed_ways_label)

        self.stats_group.setLayout(stats_layout)
        main_layout.addWidget(self.stats_group)

        # 创建进度显示区域
        self.progress_group = QGroupBox(tr("ui.progress_display"))
        progress_layout = QVBoxLayout()

        # 总体进度条
        self.overall_progress_label = QLabel(tr("progress.overall") + ":")
        progress_layout.addWidget(self.overall_progress_label)
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)

        # 处理状态文本
        self.status_label = QLabel(tr("status.ready"))
        progress_layout.addWidget(self.status_label)

        self.progress_group.setLayout(progress_layout)
        main_layout.addWidget(self.progress_group)

        # 创建按钮区域
        button_layout = QHBoxLayout()

        self.start_button = QPushButton(tr("buttons.start_correction"))
        self.start_button.clicked.connect(self.start_correction)

        self.cancel_button = QPushButton(tr("buttons.cancel"))
        self.cancel_button.clicked.connect(self.cancel_correction)
        self.cancel_button.setEnabled(False)

        button_layout.addStretch()
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.cancel_button)

        main_layout.addLayout(button_layout)

    def browse_osm(self):
        """浏览OSM文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择OSM文件", "", "OSM文件 (*.osm)"
        )
        if file_path:
            self.osm_path_edit.setText(file_path)
            # 自动设置输出文件路径
            self.suggest_output_path(file_path)

    def browse_output(self):
        """浏览输出文件"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "选择输出文件", "", "OSM文件 (*.osm)"
        )
        if file_path:
            self.output_path_edit.setText(file_path)

    def suggest_output_path(self, osm_path):
        """根据输入文件路径自动建议输出文件路径"""
        if not self.output_path_edit.text():
            osm_file = Path(osm_path)
            # 尝试找到标准输出目录
            try:
                project_dir = osm_file.parent
                while project_dir.name not in ['osm', ''] and project_dir.parent != project_dir:
                    project_dir = project_dir.parent

                if project_dir.name == 'osm':
                    # 找到了osm目录，建议使用标准输出路径
                    output_dir = project_dir / 'corrected'
                    output_dir.mkdir(parents=True, exist_ok=True)
                    output_path = output_dir / f"{osm_file.stem}_corrected.osm"
                    self.output_path_edit.setText(str(output_path))
                    return
            except Exception:
                pass

            # 如果无法确定标准路径，则使用输入文件所在目录
            output_path = osm_file.with_name(f"{osm_file.stem}_corrected.osm")
            self.output_path_edit.setText(str(output_path))

    def start_correction(self):
        """开始方向校正"""
        # 验证输入
        osm_path = self.osm_path_edit.text().strip()
        if not osm_path:
            QMessageBox.warning(self, "输入错误", "请选择OSM文件")
            return

        output_path = self.output_path_edit.text().strip()
        if not output_path:
            QMessageBox.warning(self, "输入错误", "请选择输出文件路径")
            return

        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 禁用开始按钮，启用取消按钮
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)

        # 重置统计信息
        self.processed_ways_label.setText("0")
        self.reversed_ways_label.setText("0")

        # 更新状态
        self.status_label.setText("正在处理...")
        self.progress_bar.setValue(0)

        # 调用方向校正模块
        self.log_message.emit(f"开始方向校正...\n输入: {osm_path}\n输出: {output_path}")

        # 启动处理线程
        self.direction_module.start_correction(
            osm_path=osm_path,
            output_path=output_path,
            progress_callback=self.update_progress,
            completion_callback=self.correction_completed
        )

    def cancel_correction(self):
        """取消方向校正"""
        # 调用方向校正模块的取消方法
        self.direction_module.cancel_correction()

        # 更新UI状态
        self.status_label.setText("已取消")
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

        # 记录日志
        self.log_message.emit("方向校正已取消")

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
        self.progress_bar.setValue(progress_value)

        # 更新状态文本
        if status is not None:
            self.status_label.setText(status)

    def correction_completed_signal(self, success, message):
        """校正完成（信号连接用）"""
        # 更新UI状态
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

        if success:
            # 成功完成
            self.status_label.setText("完成")
            self.progress_bar.setValue(100)
            self.log_message.emit(f"方向校正完成: {message}")
            QMessageBox.information(self, "校正完成",
                                   f"方向校正已完成！\n\n{message}")
        else:
            # 处理失败
            self.status_label.setText("失败")
            self.log_message.emit(f"方向校正失败: {message}")
            QMessageBox.warning(self, "校正失败", f"方向校正过程中出现错误:\n\n{message}")

    def update_progress(self, progress, processed_ways=None, reversed_ways=None, status=None):
        """更新进度和状态"""
        # 更新进度条
        self.progress_bar.setValue(int(progress * 100))

        # 更新统计信息
        if processed_ways is not None:
            self.processed_ways_label.setText(str(processed_ways))

        if reversed_ways is not None:
            self.reversed_ways_label.setText(str(reversed_ways))

        # 更新状态文本
        if status is not None:
            self.status_label.setText(status)

    def correction_completed(self, success, message, processed_ways, reversed_ways):
        """校正完成回调"""
        # 更新UI状态
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

        # 更新统计信息
        self.processed_ways_label.setText(str(processed_ways))
        self.reversed_ways_label.setText(str(reversed_ways))

        if success:
            # 成功完成
            self.status_label.setText("完成")
            self.progress_bar.setValue(100)
            self.log_message.emit(f"方向校正完成: {message}")
            QMessageBox.information(self, "校正完成", f"方向校正已完成。\n\n处理的way数量: {processed_ways}\n反转的way数量: {reversed_ways}")
        else:
            # 处理失败
            self.status_label.setText("失败")
            self.log_message.emit(f"方向校正失败: {message}")
            QMessageBox.warning(self, "校正失败", f"方向校正过程中出现错误: {message}")

    def on_language_changed(self):
        """响应语言切换事件"""
        # 更新组框标题
        self.input_group.setTitle(tr("ui.input_settings"))
        self.rules_group.setTitle(tr("ui.rules_description"))
        self.stats_group.setTitle(tr("ui.result_statistics"))
        self.progress_group.setTitle(tr("ui.progress_display"))

        # 更新文件标签
        self.osm_label.setText(tr("files.osm_file") + ":")
        self.output_label.setText(tr("files.output_file") + ":")

        # 更新规则说明文本
        self.rules_text.setPlainText(tr("rules.direction_correction"))

        # 更新统计标签
        self.processed_ways_stat_label.setText(tr("stats.processed_ways") + ":")
        self.reversed_ways_stat_label.setText(tr("stats.reversed_ways") + ":")

        # 更新进度标签
        self.overall_progress_label.setText(tr("progress.overall") + ":")
        self.status_label.setText(tr("status.ready"))

        # 更新按钮文本
        self.browse_osm_btn.setText(tr("buttons.browse_ellipsis"))
        self.browse_output_btn.setText(tr("buttons.browse_ellipsis"))
        self.start_button.setText(tr("buttons.start_correction"))
        self.cancel_button.setText(tr("buttons.cancel"))

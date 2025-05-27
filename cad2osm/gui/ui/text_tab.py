#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本提取标签页

此模块实现了文本提取标签页，用于从DXF文件提取文本并添加到OSM文件。
"""

import os
import sys
from pathlib import Path

# 导入PyQt5组件
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QFileDialog, QComboBox, QCheckBox,
    QSpinBox, QDoubleSpinBox, QProgressBar, QGroupBox,
    QFormLayout, QGridLayout, QRadioButton, QButtonGroup, QMessageBox,
    QTextEdit, QScrollArea, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QSettings
from PyQt5.QtGui import QPixmap, QImage

# 导入文本提取模块
from modules.text_module import TextModule

# 导入语言管理器
from utils.language_manager import tr

class TextTab(QWidget):
    """
    文本提取标签页，用于从DXF文件提取文本并添加到OSM文件
    """

    # 定义信号，用于向主窗口发送日志消息
    log_message = pyqtSignal(str)

    def __init__(self, project_manager):
        super().__init__()

        # 保存项目管理器引用
        self.project_manager = project_manager

        # 初始化文本提取模块
        self.text_module = TextModule(self)

        # 连接文本模块的信号
        self.text_module.progress_updated.connect(self.update_progress_signal)
        self.text_module.step_progress_updated.connect(self.update_step_progress_signal)
        self.text_module.process_completed.connect(self.processing_completed)

        # 初始化UI
        self.init_ui()

    def init_ui(self):
        """初始化用户界面"""
        # 创建主布局
        main_layout = QVBoxLayout(self)

        # 创建模式选择区域
        self.mode_group_box = QGroupBox(tr("ui.processing_mode"))
        mode_layout = QHBoxLayout()

        self.mode_group = QButtonGroup(self)
        self.full_mode_radio = QRadioButton(tr("modes.full_process"))
        self.extract_only_radio = QRadioButton(tr("modes.extract_only"))
        self.match_only_radio = QRadioButton(tr("modes.match_only"))

        self.mode_group.addButton(self.full_mode_radio, 1)
        self.mode_group.addButton(self.extract_only_radio, 2)
        self.mode_group.addButton(self.match_only_radio, 3)

        self.full_mode_radio.setChecked(True)

        mode_layout.addWidget(self.full_mode_radio)
        mode_layout.addWidget(self.extract_only_radio)
        mode_layout.addWidget(self.match_only_radio)

        self.mode_group_box.setLayout(mode_layout)
        main_layout.addWidget(self.mode_group_box)

        # 创建输入区域
        self.input_group = QGroupBox(tr("ui.input_settings"))
        input_layout = QGridLayout()
        input_layout.setSpacing(10)  # 设置间距

        # 第一行：DXF文件选择 和 边界文件选择
        # DXF文件选择
        self.dxf_label = QLabel(tr("files.dxf_file") + ":")
        self.dxf_path_edit = QLineEdit()
        self.browse_dxf_btn = QPushButton(tr("buttons.browse_ellipsis"))
        self.browse_dxf_btn.clicked.connect(self.browse_dxf)

        dxf_path_layout = QHBoxLayout()
        dxf_path_layout.addWidget(self.dxf_path_edit)
        dxf_path_layout.addWidget(self.browse_dxf_btn)

        input_layout.addWidget(self.dxf_label, 0, 0)
        input_layout.addLayout(dxf_path_layout, 0, 1)

        # 边界文件选择
        self.bounds_label = QLabel(tr("files.bounds_file") + ":")
        self.bounds_path_edit = QLineEdit()
        self.browse_bounds_btn = QPushButton(tr("buttons.browse_ellipsis"))
        self.browse_bounds_btn.clicked.connect(self.browse_bounds)

        bounds_path_layout = QHBoxLayout()
        bounds_path_layout.addWidget(self.bounds_path_edit)
        bounds_path_layout.addWidget(self.browse_bounds_btn)

        input_layout.addWidget(self.bounds_label, 0, 2)
        input_layout.addLayout(bounds_path_layout, 0, 3)

        # 第二行：OSM文件选择 和 文本文件选择
        # OSM文件选择
        self.osm_label = QLabel(tr("files.osm_file") + ":")
        self.osm_path_edit = QLineEdit()
        self.browse_osm_btn = QPushButton(tr("buttons.browse_ellipsis"))
        self.browse_osm_btn.clicked.connect(self.browse_osm)

        osm_path_layout = QHBoxLayout()
        osm_path_layout.addWidget(self.osm_path_edit)
        osm_path_layout.addWidget(self.browse_osm_btn)

        input_layout.addWidget(self.osm_label, 1, 0)
        input_layout.addLayout(osm_path_layout, 1, 1)

        # 文本文件选择（仅匹配模式使用）
        self.text_label = QLabel(tr("files.text_file") + ":")
        self.text_path_edit = QLineEdit()
        self.browse_text_btn = QPushButton(tr("buttons.browse_ellipsis"))
        self.browse_text_btn.clicked.connect(self.browse_text)

        text_path_layout = QHBoxLayout()
        text_path_layout.addWidget(self.text_path_edit)
        text_path_layout.addWidget(self.browse_text_btn)

        input_layout.addWidget(self.text_label, 1, 2)
        input_layout.addLayout(text_path_layout, 1, 3)

        # 第三行：输出文件路径 和 配置文件选择
        # 输出文件路径
        self.output_label = QLabel(tr("files.output_file") + ":")
        self.output_path_edit = QLineEdit()
        self.browse_output_btn = QPushButton(tr("buttons.browse_ellipsis"))
        self.browse_output_btn.clicked.connect(self.browse_output)

        output_path_layout = QHBoxLayout()
        output_path_layout.addWidget(self.output_path_edit)
        output_path_layout.addWidget(self.browse_output_btn)

        input_layout.addWidget(self.output_label, 2, 0)
        input_layout.addLayout(output_path_layout, 2, 1)

        # 配置文件选择
        self.config_label = QLabel(tr("files.config_file_optional") + ":")
        self.config_path_edit = QLineEdit()
        self.browse_config_btn = QPushButton(tr("buttons.browse_ellipsis"))
        self.browse_config_btn.clicked.connect(self.browse_config)

        config_path_layout = QHBoxLayout()
        config_path_layout.addWidget(self.config_path_edit)
        config_path_layout.addWidget(self.browse_config_btn)

        input_layout.addWidget(self.config_label, 2, 2)
        input_layout.addLayout(config_path_layout, 2, 3)

        # 设置列的拉伸比例，使输入框能够合理分配空间
        input_layout.setColumnStretch(1, 1)  # 第一列输入框
        input_layout.setColumnStretch(3, 1)  # 第二列输入框

        self.input_group.setLayout(input_layout)
        main_layout.addWidget(self.input_group)

        # 创建参数设置区域
        self.params_group = QGroupBox(tr("ui.parameter_settings"))
        params_layout = QFormLayout()

        # 文本图层名称
        self.layer_name_edit = QLineEdit("——平面——文字")
        self.layer_name_label = QLabel(tr("params.layer_name") + ":")
        params_layout.addRow(self.layer_name_label, self.layer_name_edit)

        # 附近匹配偏移阈值
        self.nearby_threshold_spin = QSpinBox()
        self.nearby_threshold_spin.setRange(1, 500)
        self.nearby_threshold_spin.setValue(50)
        self.nearby_threshold_label = QLabel(tr("params.nearby_threshold") + ":")
        params_layout.addRow(self.nearby_threshold_label, self.nearby_threshold_spin)

        # 中心偏移比例阈值
        self.center_distance_ratio_spin = QDoubleSpinBox()
        self.center_distance_ratio_spin.setRange(0.1, 1.0)
        self.center_distance_ratio_spin.setValue(0.7)
        self.center_distance_ratio_spin.setSingleStep(0.1)
        self.center_distance_ratio_label = QLabel(tr("params.center_distance_ratio") + ":")
        params_layout.addRow(self.center_distance_ratio_label, self.center_distance_ratio_spin)

        # 可视化选项
        self.visualize_check = QCheckBox(tr("params.visualize"))
        params_layout.addRow("", self.visualize_check)

        self.params_group.setLayout(params_layout)
        main_layout.addWidget(self.params_group)

        # 创建文本过滤区域
        self.filter_group = QGroupBox(tr("ui.filter_settings"))
        filter_layout = QVBoxLayout()

        self.filter_description_label = QLabel(tr("rules.filter_text_description"))
        filter_layout.addWidget(self.filter_description_label)
        self.filter_text_edit = QTextEdit()
        self.filter_text_edit.setPlaceholderText(tr("hints.filter_text_placeholder"))
        filter_layout.addWidget(self.filter_text_edit)

        self.filter_group.setLayout(filter_layout)
        main_layout.addWidget(self.filter_group)

        # 创建进度显示区域
        self.progress_group = QGroupBox(tr("ui.progress_display"))
        progress_layout = QVBoxLayout()

        # 总体进度条
        self.overall_progress_label = QLabel(tr("progress.overall") + ":")
        progress_layout.addWidget(self.overall_progress_label)
        self.total_progress_bar = QProgressBar()
        progress_layout.addWidget(self.total_progress_bar)

        # 当前步骤进度条
        self.current_step_label = QLabel(tr("progress.current_step") + ":")
        progress_layout.addWidget(self.current_step_label)
        self.step_progress_bar = QProgressBar()
        progress_layout.addWidget(self.step_progress_bar)

        # 处理状态文本
        self.status_label = QLabel(tr("status.ready"))
        progress_layout.addWidget(self.status_label)

        self.progress_group.setLayout(progress_layout)
        main_layout.addWidget(self.progress_group)

        # 创建结果预览区域
        self.preview_group = QGroupBox(tr("ui.result_preview"))
        preview_layout = QVBoxLayout()

        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.preview_label.setMinimumHeight(200)
        self.preview_label.setStyleSheet("background-color: white; border: 1px solid #cccccc;")
        self.preview_label.setText(tr("hints.preview_placeholder"))

        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.preview_label)

        preview_layout.addWidget(scroll_area)

        self.preview_group.setLayout(preview_layout)
        main_layout.addWidget(self.preview_group)

        # 创建按钮区域
        button_layout = QHBoxLayout()

        self.start_button = QPushButton(tr("buttons.start_processing"))
        self.start_button.clicked.connect(self.start_processing)

        self.cancel_button = QPushButton(tr("buttons.cancel"))
        self.cancel_button.clicked.connect(self.cancel_processing)
        self.cancel_button.setEnabled(False)

        button_layout.addStretch()
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.cancel_button)

        main_layout.addLayout(button_layout)

        # 连接信号
        self.mode_group.buttonClicked.connect(self.update_ui_for_mode)

        # 初始化UI状态
        self.update_ui_for_mode()

    def update_ui_for_mode(self):
        """根据选择的模式更新UI状态"""
        mode = self.mode_group.checkedId()

        # 完整流程模式
        if mode == 1 or mode == 0:  # 0表示没有选中任何按钮
            self.dxf_path_edit.setEnabled(True)
            self.browse_dxf_btn.setEnabled(True)
            self.bounds_path_edit.setEnabled(True)
            self.browse_bounds_btn.setEnabled(True)
            self.osm_path_edit.setEnabled(True)
            self.browse_osm_btn.setEnabled(True)
            self.text_path_edit.setEnabled(False)
            self.browse_text_btn.setEnabled(False)
        # 仅提取文本模式
        elif mode == 2:
            self.dxf_path_edit.setEnabled(True)
            self.browse_dxf_btn.setEnabled(True)
            self.bounds_path_edit.setEnabled(False)
            self.browse_bounds_btn.setEnabled(False)
            self.osm_path_edit.setEnabled(False)
            self.browse_osm_btn.setEnabled(False)
            self.text_path_edit.setEnabled(False)
            self.browse_text_btn.setEnabled(False)
        # 仅匹配文本模式
        elif mode == 3:
            self.dxf_path_edit.setEnabled(False)
            self.browse_dxf_btn.setEnabled(False)
            self.bounds_path_edit.setEnabled(True)
            self.browse_bounds_btn.setEnabled(True)
            self.osm_path_edit.setEnabled(True)
            self.browse_osm_btn.setEnabled(True)
            self.text_path_edit.setEnabled(True)
            self.browse_text_btn.setEnabled(True)

    def browse_dxf(self):
        """浏览DXF文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择DXF文件", "", "DXF文件 (*.dxf)"
        )
        if file_path:
            self.dxf_path_edit.setText(file_path)
            # u81eau52a8u8bbeu7f6eu8f93u51fau6587u4ef6u8defu5f84
            self.suggest_paths(file_path)

    def browse_bounds(self):
        """浏览边界文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择边界文件", "", "JSON文件 (*.json)"
        )
        if file_path:
            self.bounds_path_edit.setText(file_path)

    def browse_osm(self):
        """浏览OSM文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择OSM文件", "", "OSM文件 (*.osm)"
        )
        if file_path:
            self.osm_path_edit.setText(file_path)
            # u81eau52a8u8bbeu7f6eu8f93u51fau6587u4ef6u8defu5f84
            if not self.output_path_edit.text():
                output_path = str(Path(file_path).with_name(f"{Path(file_path).stem}_texted.osm"))
                self.output_path_edit.setText(output_path)

    def browse_text(self):
        """浏览文本文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择文本文件", "", "JSON文件 (*.json)"
        )
        if file_path:
            self.text_path_edit.setText(file_path)

    def browse_output(self):
        """浏览输出文件"""
        mode = self.mode_group.checkedId()

        if mode == 2:  # 仅提取文本模式
            file_path, _ = QFileDialog.getSaveFileName(
                self, "选择输出文件", "", "JSON文件 (*.json)"
            )
        else:  # 其他模式
            file_path, _ = QFileDialog.getSaveFileName(
                self, "选择输出文件", "", "OSM文件 (*.osm)"
            )

        if file_path:
            self.output_path_edit.setText(file_path)

    def browse_config(self):
        """浏览配置文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择配置文件", "", "YAML文件 (*.yaml *.yml)"
        )
        if file_path:
            self.config_path_edit.setText(file_path)

    def suggest_paths(self, dxf_path):
        """根据输入路径自动建议其他路径"""
        dxf_dir = Path(dxf_path).parent
        file_stem = Path(dxf_path).stem

        # 尝试找到bounds.json
        bounds_path = dxf_dir.parent / 'bounds' / 'bounds.json'
        if bounds_path.exists():
            self.bounds_path_edit.setText(str(bounds_path))

        # 尝试找到OSM文件
        osm_dir = dxf_dir.parent / 'osm' / 'original'
        if osm_dir.exists():
            osm_files = list(osm_dir.glob(f"{file_stem}*.osm"))
            if osm_files:
                self.osm_path_edit.setText(str(osm_files[0]))

                # 设置输出文件路径
                output_dir = dxf_dir.parent / 'osm' / 'texted'
                output_dir.mkdir(parents=True, exist_ok=True)
                output_path = output_dir / f"{osm_files[0].stem}_texted.osm"
                self.output_path_edit.setText(str(output_path))

    def start_processing(self):
        """开始处理"""
        # 获取当前选择的模式
        mode = self.mode_group.checkedId()

        # 验证共同输入
        output_path = self.output_path_edit.text().strip()
        if not output_path:
            QMessageBox.warning(self, "输入错误", "请选择输出文件路径")
            return

        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # 获取通用参数
        config_path = self.config_path_edit.text().strip() or None
        layer_name = self.layer_name_edit.text().strip()
        nearby_threshold = self.nearby_threshold_spin.value()
        center_distance_ratio = self.center_distance_ratio_spin.value()
        visualize = self.visualize_check.isChecked()

        # 获取过滤文本列表
        filter_text = self.filter_text_edit.toPlainText().strip()
        filter_text_list = [text.strip() for text in filter_text.split('\n') if text.strip()]

        # 根据不同模式验证输入并调用相应功能
        if mode == 1 or mode == 0:  # 完整流程模式
            # 验证输入
            dxf_path = self.dxf_path_edit.text().strip()
            bounds_path = self.bounds_path_edit.text().strip()
            osm_path = self.osm_path_edit.text().strip()

            if not dxf_path:
                QMessageBox.warning(self, "输入错误", "请选择DXF文件")
                return

            if not bounds_path:
                QMessageBox.warning(self, "输入错误", "请选择边界文件")
                return

            if not osm_path:
                QMessageBox.warning(self, "输入错误", "请选择OSM文件")
                return

            # 禁用开始按钮，启用取消按钮
            self.start_button.setEnabled(False)
            self.cancel_button.setEnabled(True)

            # 更新状态
            self.status_label.setText("正在处理...")
            self.total_progress_bar.setValue(0)
            self.step_progress_bar.setValue(0)

            # 调用文本提取模块
            self.log_message.emit(f"开始完整文本提取流程...\n输入DXF: {dxf_path}\n边界文件: {bounds_path}\n输入OSM: {osm_path}\n输出: {output_path}")

            # 启动处理线程
            self.text_module.start_full_process(
                dxf_path=dxf_path,
                bounds_path=bounds_path,
                osm_path=osm_path,
                output_path=output_path,
                config_path=config_path,
                layer_name=layer_name,
                nearby_threshold=nearby_threshold,
                center_distance_ratio=center_distance_ratio,
                filter_text_list=filter_text_list,
                visualize=visualize,
                progress_callback=self.update_progress,
                completion_callback=self.processing_completed
            )

        elif mode == 2:  # 仅提取文本模式
            # 验证输入
            dxf_path = self.dxf_path_edit.text().strip()

            if not dxf_path:
                QMessageBox.warning(self, "输入错误", "请选择DXF文件")
                return

            # 禁用开始按钮，启用取消按钮
            self.start_button.setEnabled(False)
            self.cancel_button.setEnabled(True)

            # 更新状态
            self.status_label.setText("正在处理...")
            self.total_progress_bar.setValue(0)
            self.step_progress_bar.setValue(0)

            # 调用文本提取模块
            self.log_message.emit(f"开始提取文本...\n输入DXF: {dxf_path}\n输出: {output_path}")

            # 启动处理线程
            self.text_module.start_extract_only(
                dxf_path=dxf_path,
                output_path=output_path,
                config_path=config_path,
                layer_name=layer_name,
                filter_text_list=filter_text_list,
                progress_callback=self.update_progress,
                completion_callback=self.processing_completed
            )

        elif mode == 3:  # 仅匹配文本模式
            # 验证输入
            bounds_path = self.bounds_path_edit.text().strip()
            osm_path = self.osm_path_edit.text().strip()
            text_path = self.text_path_edit.text().strip()

            if not bounds_path:
                QMessageBox.warning(self, "输入错误", "请选择边界文件")
                return

            if not osm_path:
                QMessageBox.warning(self, "输入错误", "请选择OSM文件")
                return

            if not text_path:
                QMessageBox.warning(self, "输入错误", "请选择文本文件")
                return

            # 禁用开始按钮，启用取消按钮
            self.start_button.setEnabled(False)
            self.cancel_button.setEnabled(True)

            # 更新状态
            self.status_label.setText("正在处理...")
            self.total_progress_bar.setValue(0)
            self.step_progress_bar.setValue(0)

            # 调用文本提取模块
            self.log_message.emit(f"开始匹配文本...\n边界文件: {bounds_path}\n输入OSM: {osm_path}\n文本文件: {text_path}\n输出: {output_path}")

            # 启动处理线程
            self.text_module.start_match_only(
                bounds_path=bounds_path,
                osm_path=osm_path,
                text_path=text_path,
                output_path=output_path,
                config_path=config_path,
                nearby_threshold=nearby_threshold,
                center_distance_ratio=center_distance_ratio,
                filter_text_list=filter_text_list,
                visualize=visualize,
                progress_callback=self.update_progress,
                completion_callback=self.processing_completed
            )

    def cancel_processing(self):
        """取消处理"""
        # 调用文本提取模块的取消方法
        self.text_module.cancel_processing()

        # 更新UI状态
        self.status_label.setText("已取消")
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

        # 记录日志
        self.log_message.emit("文本提取已取消")

    def update_progress_signal(self, progress, status=None):
        """更新总体进度（信号连接用）"""
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

        # 更新总体进度条
        self.total_progress_bar.setValue(progress_value)

        # 更新状态文本
        if status is not None:
            self.status_label.setText(status)

    def update_step_progress_signal(self, progress, status=None):
        """更新步骤进度（信号连接用）"""
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

        # 更新当前步骤进度条
        self.step_progress_bar.setValue(progress_value)

        # 更新状态文本
        if status is not None:
            self.status_label.setText(f"正在处理: {status}")

    def update_progress(self, total_progress, step_progress=None, status=None, preview_image=None):
        """更新进度和状态"""
        # 更新总体进度条
        self.total_progress_bar.setValue(int(total_progress * 100))

        # 更新当前步骤进度条
        if step_progress is not None:
            self.step_progress_bar.setValue(int(step_progress * 100))

        # 更新状态文本
        if status is not None:
            self.status_label.setText(status)

        # 更新预览图像
        if preview_image is not None:
            # 将图像数据转换为QImage
            if isinstance(preview_image, bytes):
                qimg = QImage.fromData(preview_image)
                pixmap = QPixmap.fromImage(qimg)
                self.preview_label.setPixmap(pixmap.scaled(
                    self.preview_label.width(),
                    self.preview_label.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                ))
            elif isinstance(preview_image, str) and os.path.exists(preview_image):
                # 如果是文件路径，加载图像
                pixmap = QPixmap(preview_image)
                self.preview_label.setPixmap(pixmap.scaled(
                    self.preview_label.width(),
                    self.preview_label.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                ))
            else:
                # 清除预览
                self.preview_label.setText("无法显示预览")

    def processing_completed(self, success, message):
        """处理完成回调"""
        # 更新UI状态
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)

        if success:
            # 成功完成
            self.status_label.setText("完成")
            self.total_progress_bar.setValue(100)
            self.step_progress_bar.setValue(100)
            self.log_message.emit(f"文本提取完成: {message}")

            # 显示完成消息弹窗
            mode = self.mode_group.checkedId()
            if mode == 1 or mode == 0:  # 完整流程模式
                QMessageBox.information(self, "处理完成",
                                       f"文本提取并添加到OSM文件已完成！\n\n{message}")
            elif mode == 2:  # 仅提取文本模式
                QMessageBox.information(self, "处理完成",
                                       f"文本提取已完成！\n\n{message}")
            elif mode == 3:  # 仅匹配文本模式
                QMessageBox.information(self, "处理完成",
                                       f"文本匹配并添加到OSM文件已完成！\n\n{message}")
        else:
            # 处理失败
            self.status_label.setText("失败")
            self.log_message.emit(f"文本提取失败: {message}")
            QMessageBox.warning(self, "处理失败", f"文本提取过程中出现错误:\n\n{message}")

    def on_language_changed(self):
        """响应语言切换事件"""
        # 更新组框标题
        self.mode_group_box.setTitle(tr("ui.processing_mode"))
        self.input_group.setTitle(tr("ui.input_settings"))
        self.params_group.setTitle(tr("ui.parameter_settings"))
        self.filter_group.setTitle(tr("ui.filter_settings"))
        self.progress_group.setTitle(tr("ui.progress_display"))
        self.preview_group.setTitle(tr("ui.result_preview"))

        # 更新模式选择按钮
        self.full_mode_radio.setText(tr("modes.full_process"))
        self.extract_only_radio.setText(tr("modes.extract_only"))
        self.match_only_radio.setText(tr("modes.match_only"))

        # 更新文件标签
        self.dxf_label.setText(tr("files.dxf_file") + ":")
        self.bounds_label.setText(tr("files.bounds_file") + ":")
        self.osm_label.setText(tr("files.osm_file") + ":")
        self.text_label.setText(tr("files.text_file") + ":")
        self.output_label.setText(tr("files.output_file") + ":")
        self.config_label.setText(tr("files.config_file_optional") + ":")

        # 更新参数标签
        self.layer_name_label.setText(tr("params.layer_name") + ":")
        self.nearby_threshold_label.setText(tr("params.nearby_threshold") + ":")
        self.center_distance_ratio_label.setText(tr("params.center_distance_ratio") + ":")
        self.visualize_check.setText(tr("params.visualize"))

        # 更新进度标签
        self.overall_progress_label.setText(tr("progress.overall") + ":")
        self.current_step_label.setText(tr("progress.current_step") + ":")
        self.status_label.setText(tr("status.ready"))

        # 更新按钮文本
        self.browse_dxf_btn.setText(tr("buttons.browse_ellipsis"))
        self.browse_bounds_btn.setText(tr("buttons.browse_ellipsis"))
        self.browse_osm_btn.setText(tr("buttons.browse_ellipsis"))
        self.browse_text_btn.setText(tr("buttons.browse_ellipsis"))
        self.browse_output_btn.setText(tr("buttons.browse_ellipsis"))
        self.browse_config_btn.setText(tr("buttons.browse_ellipsis"))
        self.start_button.setText(tr("buttons.start_processing"))
        self.cancel_button.setText(tr("buttons.cancel"))

        # 更新其他文本
        self.filter_description_label.setText(tr("rules.filter_text_description"))
        self.filter_text_edit.setPlaceholderText(tr("hints.filter_text_placeholder"))
        self.preview_label.setText(tr("hints.preview_placeholder"))

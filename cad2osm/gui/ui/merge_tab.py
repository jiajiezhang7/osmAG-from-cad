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
        
        # 初始化UI
        self.init_ui()
    
    def init_ui(self):
        """初始化用户界面"""
        # 创建主布局
        main_layout = QVBoxLayout(self)
        
        # 创建输入区域
        input_group = QGroupBox("输入设置")
        input_layout = QFormLayout()
        
        # 参照OSM文件选择
        self.ref_path_edit = QLineEdit()
        self.browse_ref_btn = QPushButton("浏览...")
        self.browse_ref_btn.clicked.connect(self.browse_ref)
        
        ref_path_layout = QHBoxLayout()
        ref_path_layout.addWidget(self.ref_path_edit)
        ref_path_layout.addWidget(self.browse_ref_btn)
        input_layout.addRow("参照OSM文件:", ref_path_layout)
        
        # 目标OSM文件选择
        self.target_list = QListWidget()
        self.target_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.target_list.setMinimumHeight(150)
        
        target_list_layout = QVBoxLayout()
        target_list_layout.addWidget(self.target_list)
        
        target_buttons_layout = QHBoxLayout()
        self.add_target_btn = QPushButton("添加")
        self.add_target_btn.clicked.connect(self.add_target)
        self.remove_target_btn = QPushButton("移除")
        self.remove_target_btn.clicked.connect(self.remove_target)
        self.clear_targets_btn = QPushButton("清空")
        self.clear_targets_btn.clicked.connect(self.clear_targets)
        
        target_buttons_layout.addWidget(self.add_target_btn)
        target_buttons_layout.addWidget(self.remove_target_btn)
        target_buttons_layout.addWidget(self.clear_targets_btn)
        
        target_list_layout.addLayout(target_buttons_layout)
        input_layout.addRow("目标OSM文件:", target_list_layout)
        
        # 输出文件路径
        self.output_path_edit = QLineEdit()
        self.browse_output_btn = QPushButton("浏览...")
        self.browse_output_btn.clicked.connect(self.browse_output)
        
        output_path_layout = QHBoxLayout()
        output_path_layout.addWidget(self.output_path_edit)
        output_path_layout.addWidget(self.browse_output_btn)
        input_layout.addRow("输出文件:", output_path_layout)
        
        input_group.setLayout(input_layout)
        main_layout.addWidget(input_group)
        
        # 创建参数设置区域
        params_group = QGroupBox("参数设置")
        params_layout = QFormLayout()
        
        # 匹配区域类型选择
        self.area_type_combo = QComboBox()
        self.area_type_combo.addItems(["电梯", "楼梯", "两者"])
        self.area_type_combo.setCurrentIndex(2)  # 默认选择"两者"
        params_layout.addRow("匹配区域类型:", self.area_type_combo)
        
        # 偏移计算方法选择
        self.offset_method_combo = QComboBox()
        self.offset_method_combo.addItems(["质心", "顶点平均"])
        self.offset_method_combo.setCurrentIndex(1)  # 默认选择"顶点平均"
        params_layout.addRow("偏移计算方法:", self.offset_method_combo)
        
        # 最小匹配区域数量设置
        self.min_matches_spin = QSpinBox()
        self.min_matches_spin.setRange(1, 10)
        self.min_matches_spin.setValue(2)
        params_layout.addRow("最小匹配区域数量:", self.min_matches_spin)
        
        params_group.setLayout(params_layout)
        main_layout.addWidget(params_group)
        
        # 创建结果统计区域
        stats_group = QGroupBox("结果统计")
        stats_layout = QFormLayout()
        
        self.matched_areas_label = QLabel("0")
        stats_layout.addRow("匹配区域数量:", self.matched_areas_label)
        
        self.lat_offset_label = QLabel("0.0")
        stats_layout.addRow("纬度偏移量:", self.lat_offset_label)
        
        self.lon_offset_label = QLabel("0.0")
        stats_layout.addRow("经度偏移量:", self.lon_offset_label)
        
        stats_group.setLayout(stats_layout)
        main_layout.addWidget(stats_group)
        
        # 创建进度显示区域
        progress_group = QGroupBox("进度")
        progress_layout = QVBoxLayout()
        
        # 总体进度条
        progress_layout.addWidget(QLabel("总体进度:"))
        self.total_progress_bar = QProgressBar()
        progress_layout.addWidget(self.total_progress_bar)
        
        # 处理状态文本
        self.status_label = QLabel("就绪")
        progress_layout.addWidget(self.status_label)
        
        progress_group.setLayout(progress_layout)
        main_layout.addWidget(progress_group)
        
        # 创建按钮区域
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("开始合并")
        self.start_button.clicked.connect(self.start_merging)
        
        self.cancel_button = QPushButton("取消")
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
        
        # 获取目标文件列表
        target_files = []
        for i in range(self.target_list.count()):
            target_files.append(self.target_list.item(i).text())
        
        # 获取参数
        area_type = self.area_type_combo.currentText()
        offset_method = self.offset_method_combo.currentText()
        min_matches = self.min_matches_spin.value()
        
        # 这里将实现调用合并模块的功能
        self.log_message.emit(f"开始合并OSM文件...\n参照: {ref_path}\n目标: {len(target_files)}个文件\n输出: {output_path}")
        QMessageBox.information(self, "功能开发中", "OSM合并功能正在开发中...")
    
    def cancel_merging(self):
        """取消合并"""
        # 这里将实现取消合并的功能
        self.log_message.emit("取消合并")
        QMessageBox.information(self, "功能开发中", "取消合并功能正在开发中...")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目管理器模块

此模块负责管理CAD2OSM项目的文件结构和配置。
"""

import os
import yaml
import json
from pathlib import Path
from datetime import datetime

class ProjectManager:
    """
    项目管理器类，负责管理项目的文件结构和配置
    """
    
    def __init__(self, config_path=None):
        """
        初始化项目管理器
        
        参数:
            config_path: 配置文件路径，默认为应用程序目录下的config/app_config.yaml
        """
        # 设置默认配置路径
        if config_path is None:
            # 获取应用程序目录
            app_dir = Path(__file__).parent.parent.parent
            self.config_path = os.path.join(app_dir, 'gui', 'config', 'app_config.yaml')
        else:
            self.config_path = config_path
        
        # 确保配置目录存在
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        
        # 初始化项目列表
        self.projects = {}
        
        # 当前活动项目
        self.current_project = None
        
        # 加载配置
        self.load_config()
    
    def load_config(self):
        """
        加载应用程序配置
        """
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                    if config and 'projects' in config:
                        self.projects = config['projects']
                    if config and 'current_project' in config:
                        self.current_project = config['current_project']
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                # 使用默认配置
                self.projects = {}
                self.current_project = None
        else:
            # 配置文件不存在，使用默认配置
            self.projects = {}
            self.current_project = None
    
    def save_config(self):
        """
        保存应用程序配置
        """
        try:
            config = {
                'projects': self.projects,
                'current_project': self.current_project
            }
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
    
    def create_project(self, project_name, project_root):
        """
        创建新项目
        
        参数:
            project_name: 项目名称
            project_root: 项目根目录
            
        返回:
            成功返回True，失败返回False
        """
        if project_name in self.projects:
            print(f"项目 {project_name} 已存在")
            return False
        
        # 创建项目目录结构
        project_dir = os.path.join(project_root, 'data', project_name)
        
        # 定义标准目录结构
        dirs = {
            'dwg': os.path.join(project_dir, 'dwg'),
            'dxf': {
                'original': os.path.join(project_dir, 'dxf', 'original'),
                'auto_filter': os.path.join(project_dir, 'dxf', 'auto_filter'),
                'manual_filter': os.path.join(project_dir, 'dxf', 'manual_filter')
            },
            'img': {
                'svg_auto_filter': os.path.join(project_dir, 'img', 'svg_auto_filter'),
                'svg_manual_filter': os.path.join(project_dir, 'img', 'svg_manual_filter'),
                'png_auto_filter': os.path.join(project_dir, 'img', 'png_auto_filter'),
                'png_manual_filter': os.path.join(project_dir, 'img', 'png_manual_filter')
            },
            'osm': {
                'original': os.path.join(project_dir, 'osm', 'original'),
                'texted': os.path.join(project_dir, 'osm', 'texted'),
                'merged': os.path.join(project_dir, 'osm', 'merged'),
                'corrected': os.path.join(project_dir, 'osm', 'corrected')
            },
            'bounds': os.path.join(project_dir, 'bounds')
        }
        
        try:
            # 创建目录结构
            for _, path in dirs['dxf'].items():
                os.makedirs(path, exist_ok=True)
            
            for _, path in dirs['img'].items():
                os.makedirs(path, exist_ok=True)
            
            for _, path in dirs['osm'].items():
                os.makedirs(path, exist_ok=True)
            
            os.makedirs(dirs['dwg'], exist_ok=True)
            os.makedirs(dirs['bounds'], exist_ok=True)
            
            # 添加项目到配置
            self.projects[project_name] = {
                'path': project_root,
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'last_modified': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'status': {}
            }
            
            # 设置为当前项目
            self.current_project = project_name
            
            # 保存配置
            self.save_config()
            
            return True
        except Exception as e:
            print(f"创建项目目录结构失败: {e}")
            return False
    
    def open_project(self, project_name):
        """
        打开现有项目
        
        参数:
            project_name: 项目名称
            
        返回:
            成功返回True，失败返回False
        """
        if project_name not in self.projects:
            print(f"项目 {project_name} 不存在")
            return False
        
        # 设置为当前项目
        self.current_project = project_name
        
        # 更新最后修改时间
        self.projects[project_name]['last_modified'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 保存配置
        self.save_config()
        
        return True
    
    def get_project_path(self, project_name=None):
        """
        获取项目路径
        
        参数:
            project_name: 项目名称，默认为当前项目
            
        返回:
            项目路径，如果项目不存在则返回None
        """
        if project_name is None:
            project_name = self.current_project
        
        if project_name not in self.projects:
            return None
        
        return os.path.join(self.projects[project_name]['path'], 'data', project_name)
    
    def get_directory_path(self, dir_type, sub_type=None, project_name=None):
        """
        获取特定类型目录的路径
        
        参数:
            dir_type: 目录类型，如'dwg', 'dxf', 'img', 'osm', 'bounds'
            sub_type: 子类型，如'original', 'auto_filter'等
            project_name: 项目名称，默认为当前项目
            
        返回:
            目录路径，如果项目或目录类型不存在则返回None
        """
        project_path = self.get_project_path(project_name)
        if not project_path:
            return None
        
        if dir_type not in ['dwg', 'dxf', 'img', 'osm', 'bounds']:
            return None
        
        if dir_type == 'dwg':
            return os.path.join(project_path, 'dwg')
        elif dir_type == 'bounds':
            return os.path.join(project_path, 'bounds')
        elif dir_type in ['dxf', 'img', 'osm']:
            if sub_type is None:
                return os.path.join(project_path, dir_type)
            
            # 验证子类型
            valid_sub_types = {
                'dxf': ['original', 'auto_filter', 'manual_filter'],
                'img': ['svg_auto_filter', 'svg_manual_filter', 'png_auto_filter', 'png_manual_filter'],
                'osm': ['original', 'texted', 'merged', 'corrected']
            }
            
            if sub_type not in valid_sub_types[dir_type]:
                return None
            
            return os.path.join(project_path, dir_type, sub_type)
        
        return None
    
    def update_project_status(self, status_key, status_value, project_name=None):
        """
        更新项目状态
        
        参数:
            status_key: 状态键
            status_value: 状态值
            project_name: 项目名称，默认为当前项目
            
        返回:
            成功返回True，失败返回False
        """
        if project_name is None:
            project_name = self.current_project
        
        if project_name not in self.projects:
            return False
        
        # 更新状态
        if 'status' not in self.projects[project_name]:
            self.projects[project_name]['status'] = {}
        
        self.projects[project_name]['status'][status_key] = status_value
        self.projects[project_name]['last_modified'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 保存配置
        self.save_config()
        
        return True
    
    def get_project_status(self, status_key, project_name=None):
        """
        获取项目状态
        
        参数:
            status_key: 状态键
            project_name: 项目名称，默认为当前项目
            
        返回:
            状态值，如果项目或状态键不存在则返回None
        """
        if project_name is None:
            project_name = self.current_project
        
        if project_name not in self.projects:
            return None
        
        if 'status' not in self.projects[project_name]:
            return None
        
        return self.projects[project_name]['status'].get(status_key, None)
    
    def get_project_list(self):
        """
        获取项目列表
        
        返回:
            项目名称列表
        """
        return list(self.projects.keys())
    
    def get_current_project(self):
        """
        获取当前项目名称
        
        返回:
            当前项目名称，如果没有当前项目则返回None
        """
        return self.current_project

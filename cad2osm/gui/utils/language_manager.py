#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语言管理器

此模块实现了GUI应用的国际化支持，包括语言包加载、文本翻译和语言切换功能。
"""

import os
import yaml
from pathlib import Path
from PyQt5.QtCore import QObject, pyqtSignal


class LanguageManager(QObject):
    """语言管理器，负责处理国际化相关功能"""
    
    # 语言切换信号
    language_changed = pyqtSignal(str)
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """单例模式实现"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化语言管理器"""
        if self._initialized:
            return
            
        super().__init__()
        
        # 获取i18n目录路径
        self.i18n_dir = Path(__file__).parent.parent / "i18n"
        
        # 支持的语言列表
        self.supported_languages = {
            "zh_CN": "中文",
            "en_US": "English"
        }
        
        # 当前语言和语言包
        self.current_language = "zh_CN"
        self.language_data = {}
        
        # 默认语言包（中文）
        self.default_language = "zh_CN"
        
        # 标记为已初始化
        self._initialized = True
        
        # 加载默认语言
        self.load_language(self.current_language)
    
    def get_supported_languages(self):
        """获取支持的语言列表"""
        return self.supported_languages
    
    def get_current_language(self):
        """获取当前语言"""
        return self.current_language
    
    def load_language(self, language_code):
        """加载指定语言包"""
        try:
            language_file = self.i18n_dir / f"{language_code}.yaml"
            
            if not language_file.exists():
                print(f"Warning: Language file {language_file} not found, using default language")
                language_code = self.default_language
                language_file = self.i18n_dir / f"{language_code}.yaml"
            
            with open(language_file, 'r', encoding='utf-8') as f:
                self.language_data = yaml.safe_load(f)
            
            self.current_language = language_code
            return True
            
        except Exception as e:
            print(f"Error loading language file: {e}")
            # 如果加载失败，尝试加载默认语言
            if language_code != self.default_language:
                return self.load_language(self.default_language)
            return False
    
    def switch_language(self, language_code):
        """切换语言"""
        if language_code not in self.supported_languages:
            print(f"Warning: Unsupported language code: {language_code}")
            return False
        
        if language_code == self.current_language:
            return True
        
        if self.load_language(language_code):
            # 发送语言切换信号
            self.language_changed.emit(language_code)
            return True
        
        return False
    
    def tr(self, key_path, default_text=None):
        """
        翻译文本
        
        Args:
            key_path: 翻译键路径，如 "app.title" 或 "menu.file"
            default_text: 默认文本，如果翻译不存在则返回此文本
        
        Returns:
            翻译后的文本
        """
        try:
            # 分割键路径
            keys = key_path.split('.')
            
            # 在语言数据中查找翻译
            current_data = self.language_data
            for key in keys:
                if isinstance(current_data, dict) and key in current_data:
                    current_data = current_data[key]
                else:
                    # 如果找不到翻译，返回默认文本或键路径
                    return default_text if default_text is not None else key_path
            
            # 如果找到的是列表，返回第一个元素或整个列表
            if isinstance(current_data, list):
                return current_data
            elif isinstance(current_data, str):
                return current_data
            else:
                return default_text if default_text is not None else key_path
                
        except Exception as e:
            print(f"Translation error for key '{key_path}': {e}")
            return default_text if default_text is not None else key_path
    
    def tr_list(self, key_path, default_list=None):
        """
        翻译列表
        
        Args:
            key_path: 翻译键路径
            default_list: 默认列表
        
        Returns:
            翻译后的列表
        """
        result = self.tr(key_path)
        if isinstance(result, list):
            return result
        else:
            return default_list if default_list is not None else []


# 全局语言管理器实例
language_manager = LanguageManager()


def tr(key_path, default_text=None):
    """全局翻译函数的快捷方式"""
    return language_manager.tr(key_path, default_text)


def tr_list(key_path, default_list=None):
    """全局翻译列表函数的快捷方式"""
    return language_manager.tr_list(key_path, default_list)

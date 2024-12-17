from dataclasses import dataclass
from typing import Optional

@dataclass
class Settings:
    def __init__(self):
        # 基本设置
        self.scale_numerator = 1.0
        self.scale_divisor = 1.0
        self.curve_steps = 4
        
        # 投影设置
        self.center_lat = 0.0  # 中心纬度
        self.center_lon = 0.0  # 中心经度
        self.projection = "EPSG:3857"  # 默认使用Web墨卡托投影
        
        # SVG解析设置
        self.parse_groups = True  # 是否解析SVG组
        self.parse_transforms = True  # 是否处理变换
        self.close_paths = True  # 是否自动闭合路径
        self.min_segment_length = 0.1  # 最小线段长度(米)
        
    @property 
    def scale(self):
        if self.scale_divisor < 0.0001:
            return 1.0
        return self.scale_numerator / self.scale_divisor

    def set_scale_numerator(self, value: float):
        self.scale_numerator = float(value)
        
    def set_scale_divisor(self, value: float):
        if value == 0:
            raise ValueError("Scale divisor cannot be 0")
        self.scale_divisor = float(value)
        
    def set_curve_steps(self, value: int):
        if value < 1:
            raise ValueError("Curve steps cannot be less than 1") 
        self.curve_steps = int(value) 
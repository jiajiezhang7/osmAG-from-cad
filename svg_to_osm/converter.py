from pathlib import Path
import math
from typing import List, Tuple, Optional
import xml.etree.ElementTree as ET
from xml.dom import minidom
import svgpathtools
import numpy as np
from pyproj import Transformer, CRS
from settings import Settings

class Node:
    def __init__(self, id: int, lat: float, lon: float):
        self.id = id
        self.lat = lat
        self.lon = lon
        self.tags = {}

class Way:
    def __init__(self, id: int):
        self.id = id
        self.nodes: List[Node] = []
        self.tags = {}

class Transform:
    def __init__(self, matrix=None):
        self.matrix = matrix if matrix is not None else np.eye(3)
    
    @staticmethod
    def from_svg_transform(transform_str: str) -> 'Transform':
        """从SVG transform字符串创建变换矩阵"""
        matrix = np.eye(3)
        if not transform_str:
            return Transform(matrix)
            
        # 解析transform字符串
        for transform in transform_str.split(')'):
            if not transform.strip():
                continue
                
            name, params = transform.split('(')
            params = [float(p) for p in params.replace(',', ' ').split()]
            
            if name.strip() == 'translate':
                tx, ty = params if len(params) == 2 else (params[0], 0)
                translation = np.array([[1, 0, tx],
                                     [0, 1, ty],
                                     [0, 0, 1]])
                matrix = matrix @ translation
                
            elif name.strip() == 'scale':
                sx, sy = params if len(params) == 2 else (params[0], params[0])
                scale = np.array([[sx, 0, 0],
                                [0, sy, 0],
                                [0, 0, 1]])
                matrix = matrix @ scale
                
            elif name.strip() == 'rotate':
                angle = math.radians(params[0])
                if len(params) == 3:  # 带中心点的旋转
                    cx, cy = params[1:]
                    matrix = matrix @ np.array([[1, 0, cx],
                                              [0, 1, cy],
                                              [0, 0, 1]])
                rotation = np.array([[math.cos(angle), -math.sin(angle), 0],
                                   [math.sin(angle), math.cos(angle), 0],
                                   [0, 0, 1]])
                matrix = matrix @ rotation
                if len(params) == 3:
                    matrix = matrix @ np.array([[1, 0, -cx],
                                              [0, 1, -cy],
                                              [0, 0, 1]])
                                              
        return Transform(matrix)
    
    def apply_to_point(self, x: float, y: float) -> Tuple[float, float]:
        """应用变换到点"""
        point = np.array([x, y, 1])
        transformed = self.matrix @ point
        return (transformed[0], transformed[1])

class SvgConverter:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.node_id = 1
        self.way_id = 1
        self.nodes: List[Node] = []
        self.ways: List[Way] = []
        
        # 设置投影转换器
        self.proj = Transformer.from_crs(
            CRS.from_epsg(3857),  # Web墨卡托
            CRS.from_epsg(4326),  # WGS84
            always_xy=True
        )
        
    def _create_node(self, x: float, y: float, transform: Optional[Transform] = None) -> Node:
        """创建一个新的OSM节点，支持坐标变换"""
        if transform:
            x, y = transform.apply_to_point(x, y)
            
        # 将SVG坐标转换为Web墨卡托坐标
        scale = self.settings.scale
        mx = x * scale
        my = -y * scale  # SVG的y轴向下，需要反转
        
        # Web墨卡托坐标转WGS84经纬度
        lon, lat = self.proj.transform(
            mx + self.settings.center_lon,
            my + self.settings.center_lat
        )
        
        node = Node(self.node_id, lat, lon)
        self.node_id += 1
        self.nodes.append(node)
        return node

    def _process_svg_element(self, element, transform: Optional[Transform] = None):
        """处理SVG元素"""
        # 获取元素的transform属性
        element_transform = Transform.from_svg_transform(element.get('transform', ''))
        if transform:
            # 组合变换
            combined_transform = Transform(transform.matrix @ element_transform.matrix)
        else:
            combined_transform = element_transform
            
        if element.tag.endswith('g') and self.settings.parse_groups:
            # 处理组
            for child in element:
                self._process_svg_element(child, combined_transform)
                
        elif element.tag.endswith('path'):
            # 处理路径
            path = svgpathtools.parse_path(element.get('d', ''))
            way = self._process_path(path, combined_transform)
            
            # 处理样式属性
            style = element.get('style', '')
            if style:
                way.tags['svg:style'] = style
                
        # 可以添加对其他SVG元素类型的支持
        elif element.tag.endswith('rect'):
            # 处理矩形
            x = float(element.get('x', 0))
            y = float(element.get('y', 0))
            width = float(element.get('width', 0))
            height = float(element.get('height', 0))
            
            way = Way(self.way_id)
            self.way_id += 1
            
            # 创建矩形的四个角点
            way.nodes = [
                self._create_node(x, y, combined_transform),
                self._create_node(x + width, y, combined_transform),
                self._create_node(x + width, y + height, combined_transform),
                self._create_node(x, y + height, combined_transform),
                self._create_node(x, y, combined_transform)  # 闭合路径
            ]
            self.ways.append(way)

    def convert_file(self, input_path: Path, output_path: Path):
        """转换SVG文件到OSM XML"""
        # 解析SVG文件
        tree = ET.parse(input_path)
        root = tree.getroot()
        
        # 处理所有SVG元素
        for element in root:
            self._process_svg_element(element)
            
        # 生成并保存OSM XML
        osm_xml = self._create_osm_xml()
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(osm_xml) 
from pathlib import Path
import math
from typing import List, Tuple, Optional
import xml.etree.ElementTree as ET
from xml.dom import minidom
import svgpathtools
import numpy as np
from pyproj import Transformer, CRS
from .settings import Settings

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
        
        # 计算中心点的Web墨卡托坐标
        self.center_x, self.center_y = Transformer.from_crs(
            CRS.from_epsg(4326),  # WGS84
            CRS.from_epsg(3857),  # Web墨卡托
            always_xy=True
        ).transform(self.settings.center_lon, self.settings.center_lat)

    def _create_node(self, x: float, y: float, transform: Optional[Transform] = None) -> Node:
        """创建一个新的OSM节点，支持坐标变换"""
        if transform:
            x, y = transform.apply_to_point(x, y)
            
        # 将SVG坐标转换为Web墨卡托坐标
        scale = self.settings.scale
        mx = x * scale + self.center_x  # 添加中心点偏移
        my = -y * scale + self.center_y  # SVG的y轴向下，需要反转
        
        # Web墨卡托坐标转WGS84经纬度
        lon, lat = self.proj.transform(mx, my)
        
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

    def _process_path(self, path, transform: Optional[Transform] = None) -> Way:
        """处理 SVG 路径并转换为 OSM way
        
        Args:
            path: svgpathtools Path 对象
            transform: 可选的坐标变换
        
        Returns:
            Way: 包含转换后节点的 OSM way
        """
        way = Way(self.way_id)
        self.way_id += 1
        
        # 如果路径为空，直接返回
        if not path:
            return way
            
        last_point = None
        min_distance_squared = self.settings.min_segment_length ** 2
        
        # 处理路径中的每个段
        for segment in path:
            # 根据曲线类型计算采样点
            points = []
            if hasattr(segment, 'start'):
                points.append((segment.start.real, segment.start.imag))
                
            # 对曲线进行采样
            for t in np.linspace(0, 1, self.settings.curve_steps)[1:]:
                point = segment.point(t)
                points.append((point.real, point.imag))
                
            # 处理采样点
            for x, y in points:
                # 如果存在上一个点，检查新点是否离得太近
                if last_point is not None:
                    dx = x - last_point[0]
                    dy = y - last_point[1]
                    if dx * dx + dy * dy < min_distance_squared:
                        continue
                        
                # 创建新节点
                node = self._create_node(x, y, transform)
                way.nodes.append(node)
                last_point = (x, y)
        
        # 如果设置要求闭合路径，且路径未闭合，则添加起始点作为终点
        if (self.settings.close_paths and 
            way.nodes and 
            len(way.nodes) > 1 and 
            (way.nodes[0].lat != way.nodes[-1].lat or 
             way.nodes[0].lon != way.nodes[-1].lon)):
            way.nodes.append(way.nodes[0])
        
        # 如果路径至少有两个点，则添加到ways列表
        if len(way.nodes) >= 2:
            self.ways.append(way)
            
        return way

    def _create_osm_xml(self) -> str:
        """创建OSM XML输出
        
        Returns:
            str: 格式化的OSM XML字符串
        """
        osm = ET.Element('osm', version='0.6', generator='svg_to_osm')
        
        # 添加所有节点
        for node in self.nodes:
            node_elem = ET.SubElement(osm, 'node',
                id=f'-{node.id}',  # 添加负号前缀
                action='modify',
                visible='true',
                lat=f"{node.lat:.8f}",
                lon=f"{node.lon:.8f}"
            )
            # 如果有标签则添加
            for key, value in node.tags.items():
                tag = ET.SubElement(node_elem, 'tag', k=key, v=str(value))
        
        # 添加所有路径
        for way in self.ways:
            way_elem = ET.SubElement(osm, 'way',
                id=f'-{way.id}',  # 添加负号前缀
                action='modify',
                visible='true'
            )
            # 添加way的节点引用
            for node in way.nodes:
                ET.SubElement(way_elem, 'nd', ref=f'-{node.id}')  # 节点引用也需要负号前缀
            # 添加way的标签
            for key, value in way.tags.items():
                tag = ET.SubElement(way_elem, 'tag', k=key, v=str(value))
        
        # 格式化XML输出
        xml_str = ET.tostring(osm, encoding='unicode')
        dom = minidom.parseString(xml_str)
        return dom.toprettyxml(indent="  ")

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
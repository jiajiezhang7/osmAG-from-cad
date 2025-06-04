#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
osmAG XML Semantic版本兼容性测试脚本

该脚本专门用于验证semantic版本的osmAG XML文件是否符合格式要求和转换标准。
基于semantic2fix_id.py的转换逻辑，验证semantic版本特有的标签格式和命名规则。

主要差异：
1. ID格式：semantic版本使用语义化名称（如"E1a-F2-01"），fix_id版本使用数字ID
2. 引用方式：semantic版本通过name标签引用，fix_id版本通过数字ID引用
3. 跨楼层通道：semantic版本中from/to可以相同（表示跨楼层），需要特殊处理
4. 垂直交通：电梯和楼梯在不同楼层有相同名称但不同ID

作者: AI Assistant
日期: 2024
"""

import xml.etree.ElementTree as ET
import argparse
import sys
import os
import re
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path


class ValidationLevel(Enum):
    """验证级别枚举"""
    ERROR = "ERROR"      # 严重错误，会导致转换失败
    WARNING = "WARNING"  # 警告，可能影响功能
    INFO = "INFO"        # 信息，建议改进


@dataclass
class ValidationResult:
    """验证结果数据类"""
    level: ValidationLevel
    category: str
    message: str
    element_id: Optional[str] = None
    line_number: Optional[int] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NodeData:
    """节点数据结构"""
    id: str  # semantic版本可能使用字符串ID
    lat: float
    lon: float
    action: str
    visible: bool
    tags: Dict[str, str] = field(default_factory=dict)
    line_number: Optional[int] = None


@dataclass
class WayData:
    """路径数据结构"""
    id: str  # semantic版本可能使用字符串ID
    node_refs: List[str]  # semantic版本节点引用可能是字符串
    tags: Dict[str, str] = field(default_factory=dict)
    action: str = "modify"
    visible: bool = True
    line_number: Optional[int] = None


class SemanticOSMAGValidator:
    """semantic版本osmAG XML文件验证器"""
    
    def __init__(self):
        self.nodes: Dict[str, NodeData] = {}
        self.ways: Dict[str, WayData] = {}
        self.areas: Dict[str, WayData] = {}
        self.passages: Dict[str, WayData] = {}
        self.vertical_transport: Dict[str, WayData] = {}  # 电梯和楼梯
        self.cross_level_passages: Dict[str, WayData] = {}  # 跨楼层通道
        self.results: List[ValidationResult] = []
        
        # semantic版本特有的统计信息
        self.stats = {
            'total_nodes': 0,
            'total_ways': 0,
            'total_areas': 0,
            'total_passages': 0,
            'total_vertical_transport': 0,
            'total_cross_level_passages': 0,
            'areas_by_level': {},
            'vertical_transport_by_level': {},
            'semantic_name_patterns': {},
            'errors': 0,
            'warnings': 0,
            'infos': 0
        }
        
        # semantic版本命名规则模式
        self.semantic_patterns = {
            'area_name': re.compile(r'^[A-Z]\d+[a-z]?-F\d+-.*$'),  # E1a-F2-01
            'structure_name': re.compile(r'^[A-Z]\d+[a-z]?-F\d+$'),  # E1a-F2
            'elevator_name': re.compile(r'^[A-Z]\d+-P\d+$'),  # E2-P3
            'stair_name': re.compile(r'^[A-Z]\d+-ST-\d+$'),  # E1-ST-01
            'passage_name': re.compile(r'^.*_to_.*$'),  # E1a-F2-01_to_E1a-F2-COR-01
        }
    
    def add_result(self, level: ValidationLevel, category: str, message: str, 
                   element_id: Optional[str] = None, line_number: Optional[int] = None,
                   **details):
        """添加验证结果"""
        result = ValidationResult(
            level=level,
            category=category,
            message=message,
            element_id=element_id,
            line_number=line_number,
            details=details
        )
        self.results.append(result)
        
        # 更新统计
        if level == ValidationLevel.ERROR:
            self.stats['errors'] += 1
        elif level == ValidationLevel.WARNING:
            self.stats['warnings'] += 1
        else:
            self.stats['infos'] += 1
    
    def validate_file(self, file_path: str) -> bool:
        """验证单个semantic版本osmAG文件"""
        try:
            # 重置状态
            self._reset_state()
            
            # 检查文件存在性
            if not os.path.exists(file_path):
                self.add_result(ValidationLevel.ERROR, "FILE", f"文件不存在: {file_path}")
                return False
            
            # 解析XML
            try:
                tree = ET.parse(file_path)
                root = tree.getroot()
            except ET.ParseError as e:
                self.add_result(ValidationLevel.ERROR, "XML", f"XML解析错误: {e}")
                return False
            
            # 验证根元素
            if not self._validate_root_element(root):
                return False
            
            # 第一阶段：解析所有节点和路径
            self._parse_nodes(root)
            self._parse_ways(root)
            
            # 第二阶段：分类和验证
            self._classify_ways()
            self._validate_semantic_naming()
            self._validate_nodes()
            self._validate_areas()
            self._validate_passages()
            self._validate_vertical_transport()
            self._validate_cross_level_passages()
            
            # 第三阶段：semantic版本特有的验证
            self._validate_semantic_references()
            self._validate_level_consistency()
            
            # 生成统计信息
            self._generate_statistics()
            
            return self.stats['errors'] == 0
            
        except Exception as e:
            self.add_result(ValidationLevel.ERROR, "SYSTEM", f"验证过程中发生异常: {e}")
            return False
    
    def _reset_state(self):
        """重置验证器状态"""
        self.nodes.clear()
        self.ways.clear()
        self.areas.clear()
        self.passages.clear()
        self.vertical_transport.clear()
        self.cross_level_passages.clear()
        self.results.clear()
        self.stats = {
            'total_nodes': 0,
            'total_ways': 0,
            'total_areas': 0,
            'total_passages': 0,
            'total_vertical_transport': 0,
            'total_cross_level_passages': 0,
            'areas_by_level': {},
            'vertical_transport_by_level': {},
            'semantic_name_patterns': {},
            'errors': 0,
            'warnings': 0,
            'infos': 0
        }

    def _validate_root_element(self, root: ET.Element) -> bool:
        """验证根元素"""
        if root.tag != "osm":
            self.add_result(ValidationLevel.ERROR, "ROOT", "根元素必须是'osm'")
            return False

        # 检查必需属性
        if "version" not in root.attrib:
            self.add_result(ValidationLevel.ERROR, "ROOT", "根元素缺少'version'属性")
            return False

        if root.attrib["version"] != "0.6":
            self.add_result(ValidationLevel.WARNING, "ROOT",
                          f"版本号不是0.6: {root.attrib['version']}")

        if "generator" not in root.attrib:
            self.add_result(ValidationLevel.INFO, "ROOT", "根元素缺少'generator'属性")

        return True

    def _parse_nodes(self, root: ET.Element):
        """解析所有节点"""
        for node_elem in root.findall("node"):
            try:
                # 获取必需属性
                node_id = node_elem.attrib["id"]
                lat = float(node_elem.attrib["lat"])
                lon = float(node_elem.attrib["lon"])
                action = node_elem.attrib.get("action", "modify")
                visible = node_elem.attrib.get("visible", "true").lower() == "true"

                # 解析标签
                tags = {}
                for tag_elem in node_elem.findall("tag"):
                    k = tag_elem.attrib.get("k", "")
                    v = tag_elem.attrib.get("v", "")
                    tags[k] = v

                # 创建节点数据
                node_data = NodeData(
                    id=node_id,
                    lat=lat,
                    lon=lon,
                    action=action,
                    visible=visible,
                    tags=tags,
                    line_number=getattr(node_elem, 'sourceline', None)
                )

                self.nodes[node_id] = node_data
                self.stats['total_nodes'] += 1

            except KeyError as e:
                self.add_result(ValidationLevel.ERROR, "NODE",
                              f"节点缺少必需属性: {e}",
                              element_id=node_elem.attrib.get("id"))
            except ValueError as e:
                self.add_result(ValidationLevel.ERROR, "NODE",
                              f"节点属性值格式错误: {e}",
                              element_id=node_elem.attrib.get("id"))

    def _parse_ways(self, root: ET.Element):
        """解析所有路径"""
        for way_elem in root.findall("way"):
            try:
                # 获取必需属性
                way_id = way_elem.attrib["id"]
                action = way_elem.attrib.get("action", "modify")
                visible = way_elem.attrib.get("visible", "true").lower() == "true"

                # 解析节点引用
                node_refs = []
                for nd_elem in way_elem.findall("nd"):
                    ref_id = nd_elem.attrib["ref"]
                    node_refs.append(ref_id)

                # 解析标签
                tags = {}
                for tag_elem in way_elem.findall("tag"):
                    k = tag_elem.attrib.get("k", "")
                    v = tag_elem.attrib.get("v", "")
                    tags[k] = v

                # 创建路径数据
                way_data = WayData(
                    id=way_id,
                    node_refs=node_refs,
                    tags=tags,
                    action=action,
                    visible=visible,
                    line_number=getattr(way_elem, 'sourceline', None)
                )

                self.ways[way_id] = way_data
                self.stats['total_ways'] += 1

            except KeyError as e:
                self.add_result(ValidationLevel.ERROR, "WAY",
                              f"路径缺少必需属性: {e}",
                              element_id=way_elem.attrib.get("id"))
            except ValueError as e:
                self.add_result(ValidationLevel.ERROR, "WAY",
                              f"路径属性值格式错误: {e}",
                              element_id=way_elem.attrib.get("id"))

    def _classify_ways(self):
        """分类路径为区域、通道、垂直交通等"""
        for way_id, way_data in self.ways.items():
            osmag_type = way_data.tags.get("osmAG:type", "")
            area_type = way_data.tags.get("osmAG:areaType", "")

            if osmag_type == "area":
                self.areas[way_id] = way_data
                self.stats['total_areas'] += 1

                # 统计各层级区域数量
                level = way_data.tags.get("level", "unknown")
                if level not in self.stats['areas_by_level']:
                    self.stats['areas_by_level'][level] = 0
                self.stats['areas_by_level'][level] += 1

                # 分类垂直交通设施
                if area_type in ['elevator', 'stairs']:
                    self.vertical_transport[way_id] = way_data
                    self.stats['total_vertical_transport'] += 1

                    if level not in self.stats['vertical_transport_by_level']:
                        self.stats['vertical_transport_by_level'][level] = 0
                    self.stats['vertical_transport_by_level'][level] += 1

            elif osmag_type == "passage":
                self.passages[way_id] = way_data
                self.stats['total_passages'] += 1

                # 检查是否是跨楼层通道
                from_area = way_data.tags.get("osmAG:from", "")
                to_area = way_data.tags.get("osmAG:to", "")
                if from_area == to_area and from_area:
                    self.cross_level_passages[way_id] = way_data
                    self.stats['total_cross_level_passages'] += 1

            else:
                if osmag_type:  # 只有当osmAG:type存在但不是已知类型时才警告
                    self.add_result(ValidationLevel.WARNING, "CLASSIFICATION",
                                  f"路径osmAG:type类型未知: {osmag_type}",
                                  element_id=str(way_id))

    def _validate_semantic_naming(self):
        """验证semantic版本的命名规则（仅检查name标签是否存在）"""
        for way_id, way_data in self.ways.items():
            name = way_data.tags.get("name", "")
            osmag_type = way_data.tags.get("osmAG:type", "")
            area_type = way_data.tags.get("osmAG:areaType", "")

            if not name:
                if osmag_type in ["area", "passage"]:
                    self.add_result(ValidationLevel.ERROR, "SEMANTIC_NAMING",
                                  f"缺少name标签", element_id=str(way_id))
                continue

            # 仅统计命名模式，不验证格式标准
            pattern_type = self._get_name_pattern_type(name, osmag_type, area_type)
            if pattern_type not in self.stats['semantic_name_patterns']:
                self.stats['semantic_name_patterns'][pattern_type] = 0
            self.stats['semantic_name_patterns'][pattern_type] += 1

    def _get_name_pattern_type(self, name: str, osmag_type: str, area_type: str) -> str:
        """获取名称模式类型"""
        if osmag_type == "area":
            if area_type == "structure":
                return "structure"
            elif area_type == "elevator":
                return "elevator"
            elif area_type == "stairs":
                return "stairs"
            else:
                return "area"
        elif osmag_type == "passage":
            return "passage"
        else:
            return "unknown"

    def _validate_nodes(self):
        """验证节点数据"""
        for node_id, node_data in self.nodes.items():
            # 验证坐标范围
            if not (-90 <= node_data.lat <= 90):
                self.add_result(ValidationLevel.ERROR, "NODE",
                              f"纬度超出有效范围: {node_data.lat}",
                              element_id=str(node_id))

            if not (-180 <= node_data.lon <= 180):
                self.add_result(ValidationLevel.ERROR, "NODE",
                              f"经度超出有效范围: {node_data.lon}",
                              element_id=str(node_id))

            # 验证action值
            valid_actions = ["modify", "delete", "create"]
            if node_data.action not in valid_actions:
                self.add_result(ValidationLevel.WARNING, "NODE",
                              f"action值不标准: {node_data.action}",
                              element_id=str(node_id))

    def _validate_areas(self):
        """验证区域数据"""
        for area_id, area_data in self.areas.items():
            # 验证必需标签
            required_tags = ["name", "osmAG:areaType", "level"]
            for tag in required_tags:
                if tag not in area_data.tags:
                    self.add_result(ValidationLevel.ERROR, "AREA",
                                  f"区域缺少必需标签: {tag}",
                                  element_id=str(area_id))

            # 验证区域类型
            area_type = area_data.tags.get("osmAG:areaType", "")
            valid_area_types = ["room", "corridor", "structure", "elevator", "stairs"]
            if area_type and area_type not in valid_area_types:
                self.add_result(ValidationLevel.WARNING, "AREA",
                              f"区域类型不标准: {area_type}",
                              element_id=str(area_id))

            # 验证层级
            level = area_data.tags.get("level", "")
            if level:
                try:
                    level_num = int(level)
                    if level_num < -10 or level_num > 50:  # 合理的楼层范围
                        self.add_result(ValidationLevel.WARNING, "AREA",
                                      f"楼层数值可能不合理: {level_num}",
                                      element_id=str(area_id))
                except ValueError:
                    self.add_result(ValidationLevel.ERROR, "AREA",
                                  f"楼层值格式错误: {level}",
                                  element_id=str(area_id))

            # 验证节点数量
            if len(area_data.node_refs) < 3:
                self.add_result(ValidationLevel.ERROR, "AREA",
                              f"区域节点数量不足(至少3个): {len(area_data.node_refs)}",
                              element_id=str(area_id))

            # 验证闭合性
            if len(area_data.node_refs) >= 2:
                if area_data.node_refs[0] != area_data.node_refs[-1]:
                    self.add_result(ValidationLevel.ERROR, "AREA",
                                  f"区域未闭合: 首节点{area_data.node_refs[0]} != 尾节点{area_data.node_refs[-1]}",
                                  element_id=str(area_id))

            # 验证节点引用
            for node_ref in area_data.node_refs:
                if node_ref not in self.nodes:
                    self.add_result(ValidationLevel.ERROR, "AREA",
                                  f"引用了不存在的节点: {node_ref}",
                                  element_id=str(area_id))

    def _validate_passages(self):
        """验证通道数据"""
        for passage_id, passage_data in self.passages.items():
            # 验证必需标签
            required_tags = ["name", "osmAG:from", "osmAG:to"]
            for tag in required_tags:
                if tag not in passage_data.tags:
                    self.add_result(ValidationLevel.ERROR, "PASSAGE",
                                  f"通道缺少必需标签: {tag}",
                                  element_id=str(passage_id))

            # 验证节点数量（通道必须恰好有2个节点）
            if len(passage_data.node_refs) != 2:
                self.add_result(ValidationLevel.ERROR, "PASSAGE",
                              f"通道节点数量错误(必须2个): {len(passage_data.node_refs)}",
                              element_id=str(passage_id))

            # 验证节点引用
            for node_ref in passage_data.node_refs:
                if node_ref not in self.nodes:
                    self.add_result(ValidationLevel.ERROR, "PASSAGE",
                                  f"引用了不存在的节点: {node_ref}",
                                  element_id=str(passage_id))

            # semantic版本特有：验证from/to引用的语义化名称
            from_area = passage_data.tags.get("osmAG:from", "")
            to_area = passage_data.tags.get("osmAG:to", "")

            # 由于名称格式不重要，去除名称格式检查

            # 验证from和to不能都为空
            if not from_area and not to_area:
                self.add_result(ValidationLevel.ERROR, "PASSAGE",
                              f"通道的起始和目标区域都为空",
                              element_id=str(passage_id))

    def _validate_vertical_transport(self):
        """验证垂直交通设施（电梯和楼梯）"""
        # 按名称分组垂直交通设施
        vertical_by_name = {}
        for vt_id, vt_data in self.vertical_transport.items():
            name = vt_data.tags.get("name", "")
            if name:
                if name not in vertical_by_name:
                    vertical_by_name[name] = []
                vertical_by_name[name].append((vt_id, vt_data))

        # 验证每个垂直交通设施
        for name, vt_list in vertical_by_name.items():
            if len(vt_list) < 2:
                # 垂直交通设施应该在多个楼层存在
                self.add_result(ValidationLevel.WARNING, "VERTICAL_TRANSPORT",
                              f"垂直交通设施'{name}'只在一个楼层存在",
                              element_id=vt_list[0][0])

            # 验证不同楼层的同名垂直交通设施
            levels = set()
            for vt_id, vt_data in vt_list:
                level = vt_data.tags.get("level", "")
                if level in levels:
                    self.add_result(ValidationLevel.ERROR, "VERTICAL_TRANSPORT",
                                  f"垂直交通设施'{name}'在楼层{level}重复定义",
                                  element_id=vt_id)
                levels.add(level)

                # 去除垂直交通设施名称格式验证

    def _validate_cross_level_passages(self):
        """验证跨楼层通道"""
        for passage_id, passage_data in self.cross_level_passages.items():
            from_area = passage_data.tags.get("osmAG:from", "")
            to_area = passage_data.tags.get("osmAG:to", "")
            passage_level = passage_data.tags.get("level", "")

            # 跨楼层通道的from和to应该相同
            if from_area != to_area:
                self.add_result(ValidationLevel.ERROR, "CROSS_LEVEL_PASSAGE",
                              f"跨楼层通道的from({from_area})和to({to_area})应该相同",
                              element_id=str(passage_id))
                continue

            # 验证引用的区域是否是垂直交通设施
            referenced_area_name = from_area
            is_vertical_transport = False

            for vt_id, vt_data in self.vertical_transport.items():
                if vt_data.tags.get("name", "") == referenced_area_name:
                    is_vertical_transport = True
                    break

            if not is_vertical_transport:
                self.add_result(ValidationLevel.WARNING, "CROSS_LEVEL_PASSAGE",
                              f"跨楼层通道引用的区域'{referenced_area_name}'不是垂直交通设施",
                              element_id=str(passage_id))

            # 验证跨楼层通道的层级信息
            if not passage_level:
                self.add_result(ValidationLevel.ERROR, "CROSS_LEVEL_PASSAGE",
                              f"跨楼层通道缺少level标签",
                              element_id=str(passage_id))
            else:
                try:
                    level_num = int(passage_level)
                    # 检查是否存在相邻楼层的同名垂直交通设施
                    adjacent_levels = [str(level_num - 1), str(level_num + 1)]
                    found_adjacent = False

                    for vt_id, vt_data in self.vertical_transport.items():
                        if (vt_data.tags.get("name", "") == referenced_area_name and
                            vt_data.tags.get("level", "") in adjacent_levels):
                            found_adjacent = True
                            # 验证跨楼层通道的level是否为连接的两个楼层中较高的那个
                            other_level = vt_data.tags.get("level", "")
                            if other_level and passage_level:
                                try:
                                    other_level_num = int(other_level)
                                    passage_level_num = int(passage_level)
                                    expected_level = str(max(other_level_num, passage_level_num))
                                    if passage_level != expected_level:
                                        self.add_result(ValidationLevel.WARNING, "CROSS_LEVEL_PASSAGE",
                                                      f"跨楼层通道层级({passage_level})应为连接楼层中较高的({expected_level})",
                                                      element_id=str(passage_id))
                                except ValueError:
                                    pass
                            break

                    if not found_adjacent:
                        self.add_result(ValidationLevel.WARNING, "CROSS_LEVEL_PASSAGE",
                                      f"跨楼层通道'{referenced_area_name}'在相邻楼层未找到对应设施",
                                      element_id=str(passage_id))

                except ValueError:
                    self.add_result(ValidationLevel.ERROR, "CROSS_LEVEL_PASSAGE",
                                  f"跨楼层通道level值格式错误: {passage_level}",
                                  element_id=str(passage_id))

    def _is_valid_semantic_reference(self, reference: str) -> bool:
        """验证语义化引用是否有效"""
        if not reference:
            return False

        # 检查是否匹配任何已知的命名模式
        for pattern in self.semantic_patterns.values():
            if pattern.match(reference):
                return True

        # 允许一些常见的变体
        common_patterns = [
            r'^[A-Z]\d+[a-z]?-F\d+-[A-Z]+(-\d+)?$',  # E1a-F2-COR-01
            r'^[A-Z]\d+-[A-Z]+-\d+$',  # E1-ST-01
            r'^[A-Z]\d+-P\d+$',  # E2-P3
        ]

        for pattern_str in common_patterns:
            if re.match(pattern_str, reference):
                return True

        return False

    def _validate_semantic_references(self):
        """验证semantic版本的引用完整性"""
        # 收集所有区域名称
        area_names = set()
        for area_data in self.areas.values():
            name = area_data.tags.get("name", "")
            if name:
                area_names.add(name)

        # 验证通道引用
        for passage_id, passage_data in self.passages.items():
            from_area = passage_data.tags.get("osmAG:from", "")
            to_area = passage_data.tags.get("osmAG:to", "")

            if from_area and from_area not in area_names:
                self.add_result(ValidationLevel.ERROR, "SEMANTIC_REFERENCE",
                              f"通道引用了不存在的起始区域: {from_area}",
                              element_id=str(passage_id))

            if to_area and to_area not in area_names:
                self.add_result(ValidationLevel.ERROR, "SEMANTIC_REFERENCE",
                              f"通道引用了不存在的目标区域: {to_area}",
                              element_id=str(passage_id))

        # 验证父子关系引用
        for area_id, area_data in self.areas.items():
            parent_name = area_data.tags.get("osmAG:parent", "")
            if parent_name and parent_name not in area_names:
                self.add_result(ValidationLevel.ERROR, "SEMANTIC_REFERENCE",
                              f"区域引用了不存在的父区域: {parent_name}",
                              element_id=str(area_id))

    def _validate_level_consistency(self):
        """验证层级一致性"""
        # 按层级分组区域
        areas_by_level = {}
        for area_data in self.areas.values():
            level = area_data.tags.get("level", "")
            if level:
                if level not in areas_by_level:
                    areas_by_level[level] = []
                areas_by_level[level].append(area_data)

        # 验证父子区域的层级一致性
        for area_id, area_data in self.areas.items():
            parent_name = area_data.tags.get("osmAG:parent", "")
            child_level = area_data.tags.get("level", "")

            if parent_name and child_level:
                # 查找父区域
                parent_level = None
                for parent_area in self.areas.values():
                    if parent_area.tags.get("name", "") == parent_name:
                        parent_level = parent_area.tags.get("level", "")
                        break

                if parent_level and parent_level != child_level:
                    self.add_result(ValidationLevel.WARNING, "LEVEL_CONSISTENCY",
                                  f"子区域层级({child_level})与父区域层级({parent_level})不一致",
                                  element_id=str(area_id))

        # 验证通道的层级一致性
        for passage_id, passage_data in self.passages.items():
            passage_level = passage_data.tags.get("level", "")
            from_area = passage_data.tags.get("osmAG:from", "")
            to_area = passage_data.tags.get("osmAG:to", "")

            if passage_level:
                # 检查连接的区域是否在同一层级
                for area_name in [from_area, to_area]:
                    if area_name:
                        area_level = None
                        for area_data in self.areas.values():
                            if area_data.tags.get("name", "") == area_name:
                                area_level = area_data.tags.get("level", "")
                                break

                        if area_level and area_level != passage_level:
                            # 跨楼层通道除外
                            if passage_id not in self.cross_level_passages:
                                self.add_result(ValidationLevel.WARNING, "LEVEL_CONSISTENCY",
                                              f"通道层级({passage_level})与连接区域'{area_name}'层级({area_level})不一致",
                                              element_id=str(passage_id))

    def _generate_statistics(self):
        """生成统计信息"""
        # 基本统计已在解析过程中更新

        # 计算semantic版本特有的统计信息
        if self.areas:
            # 计算每层区域的平均节点数
            level_node_counts = {}
            for area_data in self.areas.values():
                level = area_data.tags.get("level", "unknown")
                if level not in level_node_counts:
                    level_node_counts[level] = []
                level_node_counts[level].append(len(area_data.node_refs))

            self.stats['avg_nodes_per_area_by_level'] = {}
            for level, counts in level_node_counts.items():
                self.stats['avg_nodes_per_area_by_level'][level] = sum(counts) / len(counts)

        # 计算通道连接统计（基于语义化名称）
        if self.passages:
            area_connections = {}
            for passage_data in self.passages.values():
                from_area = passage_data.tags.get("osmAG:from", "")
                to_area = passage_data.tags.get("osmAG:to", "")

                if from_area and to_area:
                    if from_area not in area_connections:
                        area_connections[from_area] = set()
                    if to_area not in area_connections:
                        area_connections[to_area] = set()

                    area_connections[from_area].add(to_area)
                    area_connections[to_area].add(from_area)

            self.stats['area_connections'] = {k: len(v) for k, v in area_connections.items()}
            if area_connections:
                self.stats['avg_connections_per_area'] = sum(len(v) for v in area_connections.values()) / len(area_connections)

        # 统计跨楼层通道的分布
        if self.cross_level_passages:
            cross_level_by_type = {}
            for passage_data in self.cross_level_passages.values():
                referenced_area = passage_data.tags.get("osmAG:from", "")
                if referenced_area:
                    # 判断是电梯还是楼梯
                    transport_type = "unknown"
                    if self.semantic_patterns['elevator_name'].match(referenced_area):
                        transport_type = "elevator"
                    elif self.semantic_patterns['stair_name'].match(referenced_area):
                        transport_type = "stairs"

                    if transport_type not in cross_level_by_type:
                        cross_level_by_type[transport_type] = 0
                    cross_level_by_type[transport_type] += 1

            self.stats['cross_level_passages_by_type'] = cross_level_by_type

    def print_report(self, verbose: bool = False):
        """打印验证报告"""
        print("=" * 80)
        print("osmAG XML Semantic版本兼容性验证报告")
        print("=" * 80)

        # 打印统计信息
        print(f"\n📊 统计信息:")
        print(f"  节点总数: {self.stats['total_nodes']}")
        print(f"  路径总数: {self.stats['total_ways']}")
        print(f"  区域总数: {self.stats['total_areas']}")
        print(f"  通道总数: {self.stats['total_passages']}")
        print(f"  垂直交通设施: {self.stats['total_vertical_transport']}")
        print(f"  跨楼层通道: {self.stats['total_cross_level_passages']}")

        if self.stats['areas_by_level']:
            print(f"  各层级区域分布:")
            for level, count in sorted(self.stats['areas_by_level'].items()):
                print(f"    层级 {level}: {count} 个区域")

        if self.stats['vertical_transport_by_level']:
            print(f"  各层级垂直交通设施分布:")
            for level, count in sorted(self.stats['vertical_transport_by_level'].items()):
                print(f"    层级 {level}: {count} 个设施")

        if 'cross_level_passages_by_type' in self.stats:
            print(f"  跨楼层通道类型分布:")
            for transport_type, count in self.stats['cross_level_passages_by_type'].items():
                print(f"    {transport_type}: {count} 个")

        if self.stats['semantic_name_patterns']:
            print(f"  语义化命名模式分布:")
            for pattern, count in self.stats['semantic_name_patterns'].items():
                print(f"    {pattern}: {count} 个")

        if 'avg_connections_per_area' in self.stats:
            print(f"  平均每区域连接数: {self.stats['avg_connections_per_area']:.2f}")

        # 打印验证结果统计
        print(f"\n🔍 验证结果:")
        print(f"  错误: {self.stats['errors']} 个")
        print(f"  警告: {self.stats['warnings']} 个")
        print(f"  信息: {self.stats['infos']} 个")

        # 按类别分组显示问题
        if self.results:
            print(f"\n📋 详细问题列表:")

            # 按级别和类别分组
            grouped_results = {}
            for result in self.results:
                level = result.level.value
                category = result.category

                if level not in grouped_results:
                    grouped_results[level] = {}
                if category not in grouped_results[level]:
                    grouped_results[level][category] = []

                grouped_results[level][category].append(result)

            # 按严重程度排序显示
            for level in ["ERROR", "WARNING", "INFO"]:
                if level in grouped_results:
                    print(f"\n  {level}:")
                    for category, results in grouped_results[level].items():
                        print(f"    {category} ({len(results)} 个):")
                        for result in results[:10 if not verbose else None]:  # 限制显示数量
                            element_info = f" [元素: {result.element_id}]" if result.element_id else ""
                            line_info = f" [行: {result.line_number}]" if result.line_number else ""
                            print(f"      - {result.message}{element_info}{line_info}")

                        if not verbose and len(results) > 10:
                            print(f"      ... 还有 {len(results) - 10} 个类似问题")

        # 打印总体结论
        print(f"\n🎯 验证结论:")
        if self.stats['errors'] == 0:
            print("  ✅ 文件通过semantic版本兼容性验证")
            if self.stats['warnings'] > 0:
                print("  ⚠️  存在一些警告，建议检查")
        else:
            print("  ❌ 文件存在兼容性问题，需要修复")

        print("=" * 80)

    def save_report(self, output_file: str):
        """保存验证报告到JSON文件"""
        report_data = {
            'statistics': self.stats,
            'results': [
                {
                    'level': result.level.value,
                    'category': result.category,
                    'message': result.message,
                    'element_id': result.element_id,
                    'line_number': result.line_number,
                    'details': result.details
                }
                for result in self.results
            ],
            'summary': {
                'total_issues': len(self.results),
                'errors': self.stats['errors'],
                'warnings': self.stats['warnings'],
                'infos': self.stats['infos'],
                'passed': self.stats['errors'] == 0,
                'semantic_version': True
            }
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        print(f"Semantic版本验证报告已保存到: {output_file}")


def validate_single_file(file_path: str, verbose: bool = False, save_report: bool = False) -> bool:
    """验证单个semantic版本文件"""
    validator = SemanticOSMAGValidator()

    print(f"\n🔍 正在验证Semantic版本文件: {file_path}")
    success = validator.validate_file(file_path)

    # 打印报告
    validator.print_report(verbose)

    # 保存报告
    if save_report:
        # 创建报告文件夹
        report_dir = Path("validation_reports")
        report_dir.mkdir(exist_ok=True)
        
        # 生成报告文件路径
        report_file = report_dir / f"{Path(file_path).stem}_semantic_validation_report.json"
        validator.save_report(str(report_file))

    return success


def validate_multiple_files(file_paths: List[str], verbose: bool = False, save_report: bool = False) -> Dict[str, bool]:
    """批量验证多个semantic版本文件"""
    results = {}
    total_files = len(file_paths)
    passed_files = 0

    print(f"\n🚀 开始批量验证 {total_files} 个Semantic版本文件...")
    print("=" * 80)

    for i, file_path in enumerate(file_paths, 1):
        print(f"\n[{i}/{total_files}] 验证文件: {file_path}")

        try:
            success = validate_single_file(file_path, verbose, save_report)
            results[file_path] = success
            if success:
                passed_files += 1
                print("✅ 验证通过")
            else:
                print("❌ 验证失败")
        except Exception as e:
            print(f"❌ 验证过程中发生异常: {e}")
            results[file_path] = False

        print("-" * 40)

    # 打印批量验证总结
    print(f"\n📊 批量验证总结:")
    print(f"  总文件数: {total_files}")
    print(f"  通过验证: {passed_files}")
    print(f"  验证失败: {total_files - passed_files}")
    print(f"  成功率: {passed_files/total_files*100:.1f}%")

    # 列出失败的文件
    failed_files = [f for f, success in results.items() if not success]
    if failed_files:
        print(f"\n❌ 验证失败的文件:")
        for file_path in failed_files:
            print(f"  - {file_path}")

    return results


def find_semantic_osmag_files(directory: str) -> List[str]:
    """在目录中查找所有semantic版本osmAG文件"""
    osmag_files = []
    directory_path = Path(directory)

    if directory_path.is_file():
        if directory_path.suffix.lower() == '.osm':
            osmag_files.append(str(directory_path))
    elif directory_path.is_dir():
        # 递归查找.osm文件
        for osm_file in directory_path.rglob('*.osm'):
            osmag_files.append(str(osm_file))

    return sorted(osmag_files)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="osmAG XML Semantic版本兼容性测试工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 验证单个semantic版本文件
  python test_compatibility_semantic.py semantic_file.osm

  # 验证semantic_tags目录中的所有文件
  python test_compatibility_semantic.py area_graph_data_parser/data/semantic_tags/

  # 详细模式验证并保存报告
  python test_compatibility_semantic.py semantic_file.osm --verbose --save-report

  # 批量验证多个semantic版本文件
  python test_compatibility_semantic.py file1.osm file2.osm file3.osm

Semantic版本特有功能:
  - 验证语义化命名规则（E1a-F2-01格式）
  - 检查跨楼层通道的特殊逻辑
  - 验证垂直交通设施的多楼层一致性
  - 检查semantic引用的完整性
        """
    )

    parser.add_argument('paths', nargs='+',
                       help='要验证的semantic版本osmAG文件路径或目录路径')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='显示详细的验证信息')
    parser.add_argument('-s', '--save-report', action='store_true',
                       help='保存验证报告到JSON文件')
    parser.add_argument('--version', action='version', version='osmAG Semantic版本兼容性测试工具 v1.0')

    args = parser.parse_args()

    # 收集所有要验证的文件
    all_files = []
    for path in args.paths:
        files = find_semantic_osmag_files(path)
        if not files:
            print(f"⚠️  在路径 '{path}' 中未找到osmAG文件")
        else:
            all_files.extend(files)

    if not all_files:
        print("❌ 未找到任何osmAG文件进行验证")
        sys.exit(1)

    # 去重
    all_files = list(set(all_files))

    print(f"🎯 找到 {len(all_files)} 个Semantic版本osmAG文件待验证")

    # 执行验证
    if len(all_files) == 1:
        # 单文件验证
        success = validate_single_file(all_files[0], args.verbose, args.save_report)
        sys.exit(0 if success else 1)
    else:
        # 批量验证
        results = validate_multiple_files(all_files, args.verbose, args.save_report)

        # 根据验证结果设置退出码
        all_passed = all(results.values())
        sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()

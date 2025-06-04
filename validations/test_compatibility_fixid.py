#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
osmAG XML兼容性测试脚本

该脚本用于验证新生成的osmAG XML文件是否完全兼容现有的C++解析器标准和格式要求。
基于area_graph_data_parser包中的C++解析逻辑实现Python版本的验证器。

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
    ERROR = "ERROR"      # 严重错误，会导致解析失败
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
    id: int
    lat: float
    lon: float
    action: str
    visible: bool
    tags: Dict[str, str] = field(default_factory=dict)
    line_number: Optional[int] = None


@dataclass
class WayData:
    """路径数据结构"""
    id: int
    node_refs: List[int]
    tags: Dict[str, str] = field(default_factory=dict)
    action: str = "modify"
    visible: bool = True
    line_number: Optional[int] = None


class OSMAGValidator:
    """osmAG XML文件验证器"""
    
    def __init__(self):
        self.nodes: Dict[int, NodeData] = {}
        self.ways: Dict[int, WayData] = {}
        self.areas: Dict[int, WayData] = {}
        self.passages: Dict[int, WayData] = {}
        self.results: List[ValidationResult] = []
        self.stats = {
            'total_nodes': 0,
            'total_ways': 0,
            'total_areas': 0,
            'total_passages': 0,
            'areas_by_level': {},
            'errors': 0,
            'warnings': 0,
            'infos': 0
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
        """验证单个osmAG文件"""
        try:
            # 重置状态
            self.nodes.clear()
            self.ways.clear()
            self.areas.clear()
            self.passages.clear()
            self.results.clear()
            self.stats = {
                'total_nodes': 0,
                'total_ways': 0,
                'total_areas': 0,
                'total_passages': 0,
                'areas_by_level': {},
                'errors': 0,
                'warnings': 0,
                'infos': 0
            }

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
            self._validate_nodes()
            self._validate_areas()
            self._validate_passages()

            # 第三阶段：交叉验证
            self._cross_validate()

            # 生成统计信息
            self._generate_statistics()

            return self.stats['errors'] == 0

        except Exception as e:
            self.add_result(ValidationLevel.ERROR, "SYSTEM", f"验证过程中发生异常: {e}")
            return False

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
                node_id = int(node_elem.attrib["id"])
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
                way_id = int(way_elem.attrib["id"])
                action = way_elem.attrib.get("action", "modify")
                visible = way_elem.attrib.get("visible", "true").lower() == "true"

                # 解析节点引用
                node_refs = []
                for nd_elem in way_elem.findall("nd"):
                    ref_id = int(nd_elem.attrib["ref"])
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
        """分类路径为区域和通道"""
        for way_id, way_data in self.ways.items():
            osmag_type = way_data.tags.get("osmAG:type", "")

            if osmag_type == "area":
                self.areas[way_id] = way_data
                self.stats['total_areas'] += 1

                # 统计各层级区域数量
                level = way_data.tags.get("level", "unknown")
                if level not in self.stats['areas_by_level']:
                    self.stats['areas_by_level'][level] = 0
                self.stats['areas_by_level'][level] += 1

            elif osmag_type == "passage":
                self.passages[way_id] = way_data
                self.stats['total_passages'] += 1
            else:
                self.add_result(ValidationLevel.WARNING, "CLASSIFICATION",
                              f"路径缺少osmAG:type标签或类型未知: {osmag_type}",
                              element_id=str(way_id))

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
            required_tags = ["osmAG:areaType", "level"]
            for tag in required_tags:
                if tag not in area_data.tags:
                    self.add_result(ValidationLevel.ERROR, "AREA",
                                  f"区域缺少必需标签: {tag}",
                                  element_id=str(area_id))

            # 验证区域类型
            area_type = area_data.tags.get("osmAG:areaType", "")
            valid_area_types = ["room", "corridor", "structure", "elevator", "stair"]
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

            # 验证父子关系
            parent_id = area_data.tags.get("osmAG:parent", "")
            if parent_id:
                try:
                    parent_id_int = int(parent_id)
                    if parent_id_int not in self.areas:
                        self.add_result(ValidationLevel.ERROR, "AREA",
                                      f"引用了不存在的父区域: {parent_id}",
                                      element_id=str(area_id))
                except ValueError:
                    self.add_result(ValidationLevel.ERROR, "AREA",
                                  f"父区域ID格式错误: {parent_id}",
                                  element_id=str(area_id))

    def _validate_passages(self):
        """验证通道数据"""
        for passage_id, passage_data in self.passages.items():
            # 验证必需标签
            required_tags = ["osmAG:from", "osmAG:to"]
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

            # 验证from/to区域引用
            from_area = passage_data.tags.get("osmAG:from", "")
            to_area = passage_data.tags.get("osmAG:to", "")

            if from_area:
                try:
                    from_area_int = int(from_area)
                    if from_area_int not in self.areas:
                        self.add_result(ValidationLevel.ERROR, "PASSAGE",
                                      f"引用了不存在的起始区域: {from_area}",
                                      element_id=str(passage_id))
                except ValueError:
                    self.add_result(ValidationLevel.ERROR, "PASSAGE",
                                  f"起始区域ID格式错误: {from_area}",
                                  element_id=str(passage_id))

            if to_area:
                try:
                    to_area_int = int(to_area)
                    if to_area_int not in self.areas:
                        self.add_result(ValidationLevel.ERROR, "PASSAGE",
                                      f"引用了不存在的目标区域: {to_area}",
                                      element_id=str(passage_id))
                except ValueError:
                    self.add_result(ValidationLevel.ERROR, "PASSAGE",
                                  f"目标区域ID格式错误: {to_area}",
                                  element_id=str(passage_id))

            # 验证from和to不能相同
            if from_area == to_area and from_area:
                self.add_result(ValidationLevel.ERROR, "PASSAGE",
                              f"通道的起始和目标区域相同: {from_area}",
                              element_id=str(passage_id))

    def _cross_validate(self):
        """交叉验证"""
        # 验证通道节点是否在对应区域的边界上
        for passage_id, passage_data in self.passages.items():
            from_area_id = passage_data.tags.get("osmAG:from", "")
            to_area_id = passage_data.tags.get("osmAG:to", "")

            if from_area_id and to_area_id:
                try:
                    from_area_int = int(from_area_id)
                    to_area_int = int(to_area_id)

                    if from_area_int in self.areas and to_area_int in self.areas:
                        from_area = self.areas[from_area_int]
                        to_area = self.areas[to_area_int]

                        # 检查通道节点是否在区域边界上
                        for node_ref in passage_data.node_refs:
                            in_from_area = node_ref in from_area.node_refs
                            in_to_area = node_ref in to_area.node_refs

                            if not (in_from_area or in_to_area):
                                self.add_result(ValidationLevel.WARNING, "CROSS_VALIDATION",
                                              f"通道节点{node_ref}不在连接的区域边界上",
                                              element_id=str(passage_id))
                except ValueError:
                    pass  # 已在前面验证过格式错误

        # 验证区域层级一致性
        for area_id, area_data in self.areas.items():
            parent_id = area_data.tags.get("osmAG:parent", "")
            if parent_id:
                try:
                    parent_id_int = int(parent_id)
                    if parent_id_int in self.areas:
                        parent_area = self.areas[parent_id_int]
                        child_level = area_data.tags.get("level", "")
                        parent_level = parent_area.tags.get("level", "")

                        if child_level and parent_level and child_level != parent_level:
                            self.add_result(ValidationLevel.WARNING, "CROSS_VALIDATION",
                                          f"子区域层级({child_level})与父区域层级({parent_level})不一致",
                                          element_id=str(area_id))
                except ValueError:
                    pass  # 已在前面验证过格式错误

    def _generate_statistics(self):
        """生成统计信息"""
        # 基本统计已在解析过程中更新

        # 计算额外统计信息
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

        # 计算通道连接统计
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

    def print_report(self, verbose: bool = False):
        """打印验证报告"""
        print("=" * 80)
        print("osmAG XML兼容性验证报告")
        print("=" * 80)

        # 打印统计信息
        print(f"\n📊 统计信息:")
        print(f"  节点总数: {self.stats['total_nodes']}")
        print(f"  路径总数: {self.stats['total_ways']}")
        print(f"  区域总数: {self.stats['total_areas']}")
        print(f"  通道总数: {self.stats['total_passages']}")

        if self.stats['areas_by_level']:
            print(f"  各层级区域分布:")
            for level, count in sorted(self.stats['areas_by_level'].items()):
                print(f"    层级 {level}: {count} 个区域")

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
            print("  ✅ 文件通过兼容性验证")
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
                'passed': self.stats['errors'] == 0
            }
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        print(f"验证报告已保存到: {output_file}")


def validate_single_file(file_path: str, verbose: bool = False, save_report: bool = False) -> bool:
    """验证单个文件"""
    validator = OSMAGValidator()

    print(f"\n🔍 正在验证文件: {file_path}")
    success = validator.validate_file(file_path)

    # 打印报告
    validator.print_report(verbose)

    # 保存报告
    if save_report:
        # 创建报告文件夹
        report_dir = Path("validation_reports")
        report_dir.mkdir(exist_ok=True)
        
        # 生成报告文件路径
        report_file = report_dir / f"{Path(file_path).stem}_validation_report.json"
        validator.save_report(str(report_file))

    return success


def validate_multiple_files(file_paths: List[str], verbose: bool = False, save_report: bool = False) -> Dict[str, bool]:
    """批量验证多个文件"""
    results = {}
    total_files = len(file_paths)
    passed_files = 0

    print(f"\n🚀 开始批量验证 {total_files} 个文件...")
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


def find_osmag_files(directory: str) -> List[str]:
    """在目录中查找所有osmAG文件"""
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
        description="osmAG XML兼容性测试工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 验证单个文件
  python test_compatibility.py file.osm

  # 验证目录中的所有文件
  python test_compatibility.py /path/to/directory/

  # 详细模式验证并保存报告
  python test_compatibility.py file.osm --verbose --save-report

  # 批量验证多个文件
  python test_compatibility.py file1.osm file2.osm file3.osm
        """
    )

    parser.add_argument('paths', nargs='+',
                       help='要验证的osmAG文件路径或目录路径')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='显示详细的验证信息')
    parser.add_argument('-s', '--save-report', action='store_true',
                       help='保存验证报告到JSON文件')
    parser.add_argument('--version', action='version', version='osmAG兼容性测试工具 v1.0')

    args = parser.parse_args()

    # 收集所有要验证的文件
    all_files = []
    for path in args.paths:
        files = find_osmag_files(path)
        if not files:
            print(f"⚠️  在路径 '{path}' 中未找到osmAG文件")
        else:
            all_files.extend(files)

    if not all_files:
        print("❌ 未找到任何osmAG文件进行验证")
        sys.exit(1)

    # 去重
    all_files = list(set(all_files))

    print(f"🎯 找到 {len(all_files)} 个osmAG文件待验证")

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

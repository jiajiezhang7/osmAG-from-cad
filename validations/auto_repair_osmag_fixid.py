#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
osmAG Fix_ID版本自动修复脚本

该脚本用于自动修复fix_id版本osmAG XML文件中的常见问题。
基于test_compatibility.py检测出的问题类型，提供安全的自动修复功能。

支持的修复类型：
1. 根元素标准化
2. 属性值标准化
3. 区域闭合性修复
4. 缺失标签补充
5. 数值格式修复
6. 类型标准化

作者: AI Assistant
日期: 2024
"""

import xml.etree.ElementTree as ET
import argparse
import sys
import os
import shutil
import re
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
from datetime import datetime

# 导入验证工具
try:
    from test_compatibility import OSMAGValidator, ValidationLevel
except ImportError:
    print("错误: 无法导入test_compatibility模块，请确保文件在同一目录下")
    sys.exit(1)


class FixLevel(Enum):
    """修复级别枚举"""
    SAFE = "SAFE"           # 安全修复，不会改变语义
    MODERATE = "MODERATE"   # 中等修复，可能轻微改变语义
    RISKY = "RISKY"        # 风险修复，可能显著改变语义


@dataclass
class FixResult:
    """修复结果数据类"""
    level: FixLevel
    category: str
    description: str
    element_id: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    success: bool = True


class OSMAGFixIDFixer:
    """Fix_ID版本osmAG文件自动修复器"""
    
    def __init__(self, enable_moderate_fixes: bool = False, enable_risky_fixes: bool = False):
        self.enable_moderate_fixes = enable_moderate_fixes
        self.enable_risky_fixes = enable_risky_fixes
        self.fix_results: List[FixResult] = []
        self.stats = {
            'files_processed': 0,
            'files_fixed': 0,
            'total_fixes': 0,
            'safe_fixes': 0,
            'moderate_fixes': 0,
            'risky_fixes': 0,
            'failed_fixes': 0
        }
    
    def add_fix_result(self, level: FixLevel, category: str, description: str,
                      element_id: Optional[str] = None, old_value: Optional[str] = None,
                      new_value: Optional[str] = None, success: bool = True):
        """添加修复结果"""
        result = FixResult(
            level=level,
            category=category,
            description=description,
            element_id=element_id,
            old_value=old_value,
            new_value=new_value,
            success=success
        )
        self.fix_results.append(result)
        
        # 更新统计
        self.stats['total_fixes'] += 1
        if success:
            if level == FixLevel.SAFE:
                self.stats['safe_fixes'] += 1
            elif level == FixLevel.MODERATE:
                self.stats['moderate_fixes'] += 1
            else:
                self.stats['risky_fixes'] += 1
        else:
            self.stats['failed_fixes'] += 1
    
    def fix_file(self, file_path: str, output_path: Optional[str] = None) -> bool:
        """修复单个文件，保留原文件，输出到新文件"""
        try:
            self.fix_results.clear()
            
            # 检查文件存在性
            if not os.path.exists(file_path):
                print(f"❌ 文件不存在: {file_path}")
                return False
            
            # 确定输出路径
            if output_path is None:
                # 默认输出路径：原文件名_fixed.osm
                file_dir = os.path.dirname(file_path)
                file_name = Path(file_path).stem
                output_path = os.path.join(file_dir, f"{file_name}_fixed.osm")
            
            # 解析XML
            try:
                tree = ET.parse(file_path)
                root = tree.getroot()
            except ET.ParseError as e:
                print(f"❌ XML解析错误: {e}")
                return False
            
            # 执行修复
            fixed = False
            
            # 1. 修复根元素
            if self._fix_root_element(root):
                fixed = True
            
            # 2. 修复节点
            if self._fix_nodes(root):
                fixed = True
            
            # 3. 修复路径
            if self._fix_ways(root):
                fixed = True
            
            # 4. 修复区域
            if self._fix_areas(root):
                fixed = True
            
            # 5. 修复通道
            if self._fix_passages(root):
                fixed = True
            
            # 保存修复后的文件
            if fixed:
                # 格式化XML输出
                self._format_xml(root)
                tree.write(output_path, encoding='utf-8', xml_declaration=True)
                
                print(f"✅ 修复后的文件已保存: {output_path}")
                print(f"   原始文件保持不变: {file_path}")
                self.stats['files_fixed'] += 1
            else:
                print(f"ℹ️  文件无需修复: {file_path}")
            
            self.stats['files_processed'] += 1
            return True
            
        except Exception as e:
            print(f"❌ 修复过程中发生异常: {e}")
            return False
    
    def _fix_root_element(self, root: ET.Element) -> bool:
        """修复根元素"""
        fixed = False
        
        # 修复版本号
        if root.attrib.get("version") != "0.6":
            old_version = root.attrib.get("version", "未设置")
            root.attrib["version"] = "0.6"
            self.add_fix_result(FixLevel.SAFE, "ROOT", "标准化版本号",
                              old_value=old_version, new_value="0.6")
            fixed = True
        
        # 添加generator属性
        if "generator" not in root.attrib:
            root.attrib["generator"] = "osmAG_auto_fixer"
            self.add_fix_result(FixLevel.SAFE, "ROOT", "添加generator属性",
                              new_value="osmAG_auto_fixer")
            fixed = True
        
        return fixed
    
    def _fix_nodes(self, root: ET.Element) -> bool:
        """修复节点"""
        fixed = False
        
        for node_elem in root.findall("node"):
            node_id = node_elem.attrib.get("id", "unknown")
            
            # 修复action属性
            if "action" not in node_elem.attrib:
                node_elem.attrib["action"] = "modify"
                self.add_fix_result(FixLevel.SAFE, "NODE", "添加action属性",
                                  element_id=node_id, new_value="modify")
                fixed = True
            elif node_elem.attrib["action"] not in ["modify", "delete", "create"]:
                old_action = node_elem.attrib["action"]
                node_elem.attrib["action"] = "modify"
                self.add_fix_result(FixLevel.SAFE, "NODE", "标准化action属性",
                                  element_id=node_id, old_value=old_action, new_value="modify")
                fixed = True
            
            # 修复visible属性
            if "visible" not in node_elem.attrib:
                node_elem.attrib["visible"] = "true"
                self.add_fix_result(FixLevel.SAFE, "NODE", "添加visible属性",
                                  element_id=node_id, new_value="true")
                fixed = True
            
            # 修复坐标格式（如果启用中等修复）
            if self.enable_moderate_fixes:
                if self._fix_coordinate_format(node_elem, node_id):
                    fixed = True
        
        return fixed

    def _fix_coordinate_format(self, node_elem: ET.Element, node_id: str) -> bool:
        """修复坐标格式"""
        fixed = False

        # 修复纬度
        lat_str = node_elem.attrib.get("lat", "")
        if lat_str:
            try:
                lat = float(lat_str)
                # 检查范围
                if lat < -90 or lat > 90:
                    # 尝试简单的修正
                    if lat < -90:
                        new_lat = -90.0
                    else:
                        new_lat = 90.0

                    node_elem.attrib["lat"] = str(new_lat)
                    self.add_fix_result(FixLevel.MODERATE, "NODE", "修正纬度范围",
                                      element_id=node_id, old_value=lat_str, new_value=str(new_lat))
                    fixed = True
            except ValueError:
                pass  # 无法修复的格式错误

        # 修复经度
        lon_str = node_elem.attrib.get("lon", "")
        if lon_str:
            try:
                lon = float(lon_str)
                # 检查范围
                if lon < -180 or lon > 180:
                    # 尝试简单的修正
                    if lon < -180:
                        new_lon = -180.0
                    else:
                        new_lon = 180.0

                    node_elem.attrib["lon"] = str(new_lon)
                    self.add_fix_result(FixLevel.MODERATE, "NODE", "修正经度范围",
                                      element_id=node_id, old_value=lon_str, new_value=str(new_lon))
                    fixed = True
            except ValueError:
                pass  # 无法修复的格式错误

        return fixed

    def _fix_ways(self, root: ET.Element) -> bool:
        """修复路径"""
        fixed = False

        for way_elem in root.findall("way"):
            way_id = way_elem.attrib.get("id", "unknown")

            # 修复action属性
            if "action" not in way_elem.attrib:
                way_elem.attrib["action"] = "modify"
                self.add_fix_result(FixLevel.SAFE, "WAY", "添加action属性",
                                  element_id=way_id, new_value="modify")
                fixed = True

            # 修复visible属性
            if "visible" not in way_elem.attrib:
                way_elem.attrib["visible"] = "true"
                self.add_fix_result(FixLevel.SAFE, "WAY", "添加visible属性",
                                  element_id=way_id, new_value="true")
                fixed = True

        return fixed

    def _fix_areas(self, root: ET.Element) -> bool:
        """修复区域"""
        fixed = False

        for way_elem in root.findall("way"):
            way_id = way_elem.attrib.get("id", "unknown")

            # 检查是否是区域
            tags = {}
            for tag_elem in way_elem.findall("tag"):
                k = tag_elem.attrib.get("k", "")
                v = tag_elem.attrib.get("v", "")
                tags[k] = v

            if tags.get("osmAG:type") == "area":
                # 修复区域闭合性
                if self._fix_area_closure(way_elem, way_id):
                    fixed = True

                # 修复缺失的必需标签
                if self._fix_missing_area_tags(way_elem, way_id, tags):
                    fixed = True

                # 标准化区域类型
                if self._fix_area_type(way_elem, way_id, tags):
                    fixed = True

                # 修复层级格式
                if self.enable_moderate_fixes:
                    if self._fix_level_format(way_elem, way_id, tags):
                        fixed = True

        return fixed

    def _fix_area_closure(self, way_elem: ET.Element, way_id: str) -> bool:
        """修复区域闭合性"""
        node_refs = []
        for nd_elem in way_elem.findall("nd"):
            ref = nd_elem.attrib.get("ref", "")
            if ref:
                node_refs.append(ref)

        if len(node_refs) >= 3 and node_refs[0] != node_refs[-1]:
            # 添加闭合节点
            new_nd = ET.SubElement(way_elem, "nd")
            new_nd.attrib["ref"] = node_refs[0]

            self.add_fix_result(FixLevel.SAFE, "AREA", "修复区域闭合性",
                              element_id=way_id,
                              old_value=f"首节点{node_refs[0]} != 尾节点{node_refs[-1]}",
                              new_value=f"已闭合到节点{node_refs[0]}")
            return True

        return False

    def _fix_missing_area_tags(self, way_elem: ET.Element, way_id: str, tags: Dict[str, str]) -> bool:
        """修复缺失的区域标签"""
        fixed = False

        # 检查osmAG:areaType
        if "osmAG:areaType" not in tags:
            # 尝试智能推断
            area_type = self._infer_area_type(tags)
            if area_type:
                new_tag = ET.SubElement(way_elem, "tag")
                new_tag.attrib["k"] = "osmAG:areaType"
                new_tag.attrib["v"] = area_type

                self.add_fix_result(FixLevel.MODERATE, "AREA", "智能推断区域类型",
                                  element_id=way_id, new_value=area_type)
                fixed = True

        return fixed

    def _infer_area_type(self, tags: Dict[str, str]) -> Optional[str]:
        """智能推断区域类型"""
        # 基于现有标签推断
        name = tags.get("name", "").lower()

        if "corridor" in name or "hallway" in name:
            return "corridor"
        elif "room" in name or any(x in name for x in ["office", "lab", "classroom"]):
            return "room"
        elif "elevator" in name or "lift" in name:
            return "elevator"
        elif "stair" in name or "step" in name:
            return "stair"
        elif "structure" in name or "building" in name:
            return "structure"
        else:
            return "room"  # 默认为房间

    def _fix_area_type(self, way_elem: ET.Element, way_id: str, tags: Dict[str, str]) -> bool:
        """标准化区域类型"""
        area_type = tags.get("osmAG:areaType", "")
        valid_types = ["room", "corridor", "structure", "elevator", "stair"]

        if area_type and area_type not in valid_types:
            # 尝试映射到标准类型
            standard_type = self._map_to_standard_type(area_type)
            if standard_type:
                # 找到并更新标签
                for tag_elem in way_elem.findall("tag"):
                    if tag_elem.attrib.get("k") == "osmAG:areaType":
                        tag_elem.attrib["v"] = standard_type

                        self.add_fix_result(FixLevel.SAFE, "AREA", "标准化区域类型",
                                          element_id=way_id, old_value=area_type, new_value=standard_type)
                        return True

        return False

    def _map_to_standard_type(self, area_type: str) -> Optional[str]:
        """映射到标准区域类型"""
        type_mapping = {
            "stairs": "stair",
            "elevators": "elevator",
            "rooms": "room",
            "corridors": "corridor",
            "hall": "corridor",
            "hallway": "corridor",
            "office": "room",
            "lab": "room",
            "laboratory": "room",
            "classroom": "room",
            "building": "structure"
        }

        return type_mapping.get(area_type.lower())

    def _fix_level_format(self, way_elem: ET.Element, way_id: str, tags: Dict[str, str]) -> bool:
        """修复层级格式"""
        level = tags.get("level", "")
        if level:
            try:
                level_num = int(level)
                # 检查合理范围
                if level_num < -10 or level_num > 50:
                    # 尝试修正明显错误
                    if level_num < -10:
                        new_level = "0"  # 默认为地面层
                    elif level_num > 50:
                        new_level = "1"  # 默认为一层
                    else:
                        return False

                    # 更新标签
                    for tag_elem in way_elem.findall("tag"):
                        if tag_elem.attrib.get("k") == "level":
                            tag_elem.attrib["v"] = new_level

                            self.add_fix_result(FixLevel.MODERATE, "AREA", "修正层级数值",
                                              element_id=way_id, old_value=level, new_value=new_level)
                            return True
            except ValueError:
                # 尝试修复非数字的层级值
                if level.lower() in ["ground", "g", "gf"]:
                    new_level = "0"
                elif level.lower() in ["first", "1st", "f1"]:
                    new_level = "1"
                elif level.lower() in ["second", "2nd", "f2"]:
                    new_level = "2"
                else:
                    return False

                # 更新标签
                for tag_elem in way_elem.findall("tag"):
                    if tag_elem.attrib.get("k") == "level":
                        tag_elem.attrib["v"] = new_level

                        self.add_fix_result(FixLevel.MODERATE, "AREA", "标准化层级格式",
                                          element_id=way_id, old_value=level, new_value=new_level)
                        return True

        return False

    def _fix_passages(self, root: ET.Element) -> bool:
        """修复通道"""
        fixed = False

        for way_elem in root.findall("way"):
            way_id = way_elem.attrib.get("id", "unknown")

            # 检查是否是通道
            tags = {}
            for tag_elem in way_elem.findall("tag"):
                k = tag_elem.attrib.get("k", "")
                v = tag_elem.attrib.get("v", "")
                tags[k] = v

            if tags.get("osmAG:type") == "passage":
                # 目前通道的修复比较有限，主要是格式标准化
                # 复杂的引用问题需要人工干预
                pass

        return fixed

    def _format_xml(self, root: ET.Element):
        """格式化XML输出"""
        # 简单的缩进格式化
        def indent(elem, level=0):
            i = "\n" + level * "  "
            if len(elem):
                if not elem.text or not elem.text.strip():
                    elem.text = i + "  "
                if not elem.tail or not elem.tail.strip():
                    elem.tail = i
                for child in elem:
                    indent(child, level + 1)
                if not child.tail or not child.tail.strip():
                    child.tail = i
            else:
                if level and (not elem.tail or not elem.tail.strip()):
                    elem.tail = i

        indent(root)

    def print_fix_report(self):
        """打印修复报告"""
        print("=" * 80)
        print("osmAG Fix_ID版本自动修复报告")
        print("=" * 80)

        # 打印统计信息
        print(f"\n📊 修复统计:")
        print(f"  处理文件数: {self.stats['files_processed']}")
        print(f"  修复文件数: {self.stats['files_fixed']}")
        print(f"  总修复数: {self.stats['total_fixes']}")
        print(f"  安全修复: {self.stats['safe_fixes']}")
        print(f"  中等修复: {self.stats['moderate_fixes']}")
        print(f"  风险修复: {self.stats['risky_fixes']}")
        print(f"  失败修复: {self.stats['failed_fixes']}")

        # 按类别分组显示修复结果
        if self.fix_results:
            print(f"\n📋 详细修复列表:")

            # 按级别和类别分组
            grouped_results = {}
            for result in self.fix_results:
                level = result.level.value
                category = result.category

                if level not in grouped_results:
                    grouped_results[level] = {}
                if category not in grouped_results[level]:
                    grouped_results[level][category] = []

                grouped_results[level][category].append(result)

            # 按修复级别排序显示
            for level in ["SAFE", "MODERATE", "RISKY"]:
                if level in grouped_results:
                    print(f"\n  {level}:")
                    for category, results in grouped_results[level].items():
                        print(f"    {category} ({len(results)} 个):")
                        for result in results[:5]:  # 限制显示数量
                            element_info = f" [元素: {result.element_id}]" if result.element_id else ""
                            change_info = ""
                            if result.old_value and result.new_value:
                                change_info = f" ({result.old_value} → {result.new_value})"
                            elif result.new_value:
                                change_info = f" (→ {result.new_value})"

                            status = "✅" if result.success else "❌"
                            print(f"      {status} {result.description}{element_info}{change_info}")

                        if len(results) > 5:
                            print(f"      ... 还有 {len(results) - 5} 个类似修复")

        print("=" * 80)

    def save_fix_report(self, output_file: str):
        """保存修复报告到JSON文件"""
        report_data = {
            'statistics': self.stats,
            'fix_results': [
                {
                    'level': result.level.value,
                    'category': result.category,
                    'description': result.description,
                    'element_id': result.element_id,
                    'old_value': result.old_value,
                    'new_value': result.new_value,
                    'success': result.success
                }
                for result in self.fix_results
            ],
            'summary': {
                'total_fixes': self.stats['total_fixes'],
                'files_processed': self.stats['files_processed'],
                'files_fixed': self.stats['files_fixed'],
                'success_rate': self.stats['files_fixed'] / max(self.stats['files_processed'], 1) * 100
            }
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        print(f"修复报告已保存到: {output_file}")


def fix_single_file(file_path: str, output_path: Optional[str] = None,
                   enable_moderate: bool = False, enable_risky: bool = False,
                   save_report: bool = False) -> bool:
    """修复单个文件，保留原文件，输出到新文件"""
    fixer = OSMAGFixIDFixer(enable_moderate, enable_risky)

    print(f"\n🔧 正在修复Fix_ID版本文件: {file_path}")

    # 修复前验证
    print("📋 修复前验证...")
    validator = OSMAGValidator()
    pre_fix_success = validator.validate_file(file_path)
    pre_fix_errors = validator.stats['errors']
    pre_fix_warnings = validator.stats['warnings']

    # 执行修复
    success = fixer.fix_file(file_path, output_path)

    if success and fixer.stats['total_fixes'] > 0:
        # 修复后验证
        print("📋 修复后验证...")
        fixed_file = output_path if output_path else file_path
        post_fix_success = validator.validate_file(fixed_file)
        post_fix_errors = validator.stats['errors']
        post_fix_warnings = validator.stats['warnings']

        # 打印对比结果
        print(f"\n📊 修复效果对比:")
        print(f"  错误数: {pre_fix_errors} → {post_fix_errors} (减少 {pre_fix_errors - post_fix_errors})")
        print(f"  警告数: {pre_fix_warnings} → {post_fix_warnings} (减少 {pre_fix_warnings - post_fix_warnings})")
        print(f"  验证状态: {'❌' if not pre_fix_success else '✅'} → {'✅' if post_fix_success else '❌'}")

    # 打印修复报告
    fixer.print_fix_report()

    # 保存报告
    if save_report:
        report_file = f"{Path(file_path).stem}_fix_report.json"
        fixer.save_fix_report(report_file)

    return success


def fix_multiple_files(file_paths: List[str], output_dir: Optional[str] = None,
                      enable_moderate: bool = False, enable_risky: bool = False,
                      save_report: bool = False) -> Dict[str, bool]:
    """批量修复多个文件并保存到新文件"""
    results = {}
    total_files = len(file_paths)
    fixed_files = 0

    print(f"\n🚀 开始批量修复 {total_files} 个Fix_ID版本文件...")
    print("=" * 80)

    for i, file_path in enumerate(file_paths, 1):
        print(f"\n[{i}/{total_files}] 修复文件: {file_path}")

        try:
            # 确定输出路径
            output_path = None
            if output_dir:
                file_name = Path(file_path).stem
                output_path = os.path.join(output_dir, f"{file_name}_fixed.osm")

            success = fix_single_file(file_path, output_path, enable_moderate,
                                    enable_risky, save_report)
            results[file_path] = success
            if success:
                fixed_files += 1
                print("✅ 修复完成")
            else:
                print("❌ 修复失败")
        except Exception as e:
            print(f"❌ 修复过程中发生异常: {e}")
            results[file_path] = False

        print("-" * 40)

    # 打印批量修复总结
    print(f"\n📊 批量修复总结:")
    print(f"  总文件数: {total_files}")
    print(f"  修复完成: {fixed_files}")
    print(f"  修复失败: {total_files - fixed_files}")
    print(f"  成功率: {fixed_files/total_files*100:.1f}%")

    return results


def find_fixid_osmag_files(directory: str) -> List[str]:
    """在目录中查找所有fix_id版本osmAG文件"""
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
        description="osmAG Fix_ID版本自动修复工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 修复单个文件（仅安全修复）
  python auto_fix_osmag_fixid.py file.osm

  # 修复文件并启用中等风险修复
  python auto_fix_osmag_fixid.py file.osm --enable-moderate

  # 修复到指定输出文件
  python auto_fix_osmag_fixid.py file.osm --output fixed_file.osm

  # 批量修复目录中的所有文件
  python auto_fix_osmag_fixid.py /path/to/directory/ --enable-moderate --save-report

  # 修复到指定输出目录
  python auto_fix_osmag_fixid.py /path/to/input/ --output-dir /path/to/output/

修复级别说明:
  - SAFE: 安全修复，不会改变语义（默认启用）
  - MODERATE: 中等修复，可能轻微改变语义（需要--enable-moderate）
  - RISKY: 风险修复，可能显著改变语义（需要--enable-risky）
        """
    )

    parser.add_argument('paths', nargs='+',
                       help='要修复的Fix_ID版本osmAG文件路径或目录路径')
    parser.add_argument('-o', '--output',
                       help='输出文件路径（单文件修复时）')
    parser.add_argument('--output-dir',
                       help='输出目录路径（批量修复时）')
    parser.add_argument('--enable-moderate', action='store_true',
                       help='启用中等风险修复')
    parser.add_argument('--enable-risky', action='store_true',
                       help='启用高风险修复')
    parser.add_argument('-s', '--save-report', action='store_true',
                       help='保存修复报告到JSON文件')
    parser.add_argument('--version', action='version', version='osmAG Fix_ID版本自动修复工具 v1.0')

    args = parser.parse_args()
    
    # 检查参数
    if len(args.paths) > 1 and args.output:
        print("\n错误: 指定多个文件时不能使用--output参数\n")
        parser.print_help()
        return
    
    # 如果指定了输出目录，确保其存在
    if args.output_dir and not os.path.exists(args.output_dir):
        try:
            os.makedirs(args.output_dir)
            print(f"\n已创建输出目录: {args.output_dir}")
        except Exception as e:
            print(f"\n错误: 无法创建输出目录: {e}")
            return
    
    # 处理文件或目录
    all_file_paths = []
    for path in args.paths:
        if os.path.isfile(path):
            if path.lower().endswith('.osm'):
                all_file_paths.append(path)
            else:
                print(f"\n警告: 跳过非.osm文件: {path}")
        elif os.path.isdir(path):
            files = find_fixid_osmag_files(path)
            if files:
                all_file_paths.extend(files)
                print(f"\n在目录 {path} 中找到 {len(files)} 个Fix_ID版本osmAG文件")
            else:
                print(f"\n警告: 目录 {path} 中未找到Fix_ID版本osmAG文件")
        else:
            print(f"\n错误: 路径不存在或不可访问: {path}")
    
    # 没有可处理的文件
    if not all_file_paths:
        print("\n错误: 未找到可修复的Fix_ID版本osmAG文件\n")
        return
    
    # 执行修复
    start_time = time.time()
    
    if len(all_file_paths) == 1:
        # 单文件修复
        file_path = all_file_paths[0]
        fix_single_file(
            file_path, 
            args.output, 
            args.enable_moderate, 
            args.enable_risky,
            args.save_report
        )
    else:
        # 多文件修复
        results = fix_multiple_files(
            all_file_paths, 
            args.output_dir,
            args.enable_moderate, 
            args.enable_risky,
            args.save_report
        )

    # 根据修复结果设置退出码
    if len(all_file_paths) > 1:
        all_success = all(results.values())
        sys.exit(0 if all_success else 1)


if __name__ == "__main__":
    main()

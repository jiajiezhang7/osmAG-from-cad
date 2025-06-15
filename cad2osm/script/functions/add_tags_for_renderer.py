#!/usr/bin/env python3
# 修复脚本，用于为渲染器添加必要的标签
# 1. 为普通passage（非跨楼层passage）添加door相关标签
# 2. 为电梯添加room=elevator标签
# 3. 为楼梯添加room=stairs标签
import xml.etree.ElementTree as ET
import os
import re

def add_tags_for_renderer(input_file, output_file):
    """
    为渲染器添加必要的标签：
    1. 为普通passage添加door相关标签：indoor=door, door=yes
    2. 为电梯（osmAG:areaType=elevator）添加room=elevator标签
    3. 为楼梯（osmAG:areaType=stairs）添加room=stairs标签
    排除跨楼层passage（由add_vertical_passages.py创建的passage）
    """
    # 解析XML文件
    tree = ET.parse(input_file)
    root = tree.getroot()
    
    # 统计信息
    total_passages = 0
    vertical_passages = 0
    regular_passages = 0
    modified_passages = 0
    total_elevators = 0
    modified_elevators = 0
    total_stairs = 0
    modified_stairs = 0
    
    # 找到所有way元素
    ways = root.findall(".//way")
    
    # 处理每个way
    for way in ways:
        # 获取所有tag
        tags = way.findall('tag')
        tag_dict = {tag.get('k'): tag.get('v') for tag in tags}
        
        # 处理passage
        if tag_dict.get('osmAG:type') == 'passage':
            total_passages += 1
            
            # 判断是否是跨楼层passage
            is_vertical_passage = is_vertical_passage_func(tag_dict)
            
            if is_vertical_passage:
                vertical_passages += 1
                print(f"跳过跨楼层passage: way {way.get('id')}, name: {tag_dict.get('name', 'N/A')}")
            else:
                regular_passages += 1
                
                # 检查是否已经有indoor和door标签
                has_indoor_tag = 'indoor' in tag_dict
                has_door_tag = 'door' in tag_dict
                
                # 添加或更新indoor标签
                if has_indoor_tag:
                    # 更新现有的indoor标签
                    indoor_tag = way.find(".//tag[@k='indoor']")
                    if indoor_tag is not None:
                        indoor_tag.set('v', 'door')
                else:
                    # 创建新的indoor标签
                    new_indoor_tag = ET.SubElement(way, 'tag')
                    new_indoor_tag.set('k', 'indoor')
                    new_indoor_tag.set('v', 'door')
                
                # 添加或更新door标签
                if has_door_tag:
                    # 更新现有的door标签
                    door_tag = way.find(".//tag[@k='door']")
                    if door_tag is not None:
                        door_tag.set('v', 'yes')
                else:
                    # 创建新的door标签
                    new_door_tag = ET.SubElement(way, 'tag')
                    new_door_tag.set('k', 'door')
                    new_door_tag.set('v', 'yes')
                
                modified_passages += 1
                print(f"已修改passage: way {way.get('id')}, name: {tag_dict.get('name', 'N/A')}")
        
        # 处理电梯
        elif tag_dict.get('osmAG:areaType') == 'elevator':
            total_elevators += 1
            
            # 检查是否已经有room标签
            has_room_tag = 'room' in tag_dict
            
            if has_room_tag:
                # 更新现有的room标签
                room_tag = way.find(".//tag[@k='room']")
                if room_tag is not None:
                    room_tag.set('v', 'elevator')
            else:
                # 创建新的room标签
                new_room_tag = ET.SubElement(way, 'tag')
                new_room_tag.set('k', 'room')
                new_room_tag.set('v', 'elevator')
            
            modified_elevators += 1
            print(f"已为电梯添加room标签: way {way.get('id')}, name: {tag_dict.get('name', 'N/A')}")
        
        # 处理楼梯
        elif tag_dict.get('osmAG:areaType') == 'stairs':
            total_stairs += 1
            
            # 检查是否已经有room标签
            has_room_tag = 'room' in tag_dict
            
            if has_room_tag:
                # 更新现有的room标签
                room_tag = way.find(".//tag[@k='room']")
                if room_tag is not None:
                    room_tag.set('v', 'stairs')
            else:
                # 创建新的room标签
                new_room_tag = ET.SubElement(way, 'tag')
                new_room_tag.set('k', 'room')
                new_room_tag.set('v', 'stairs')
            
            modified_stairs += 1
            print(f"已为楼梯添加room标签: way {way.get('id')}, name: {tag_dict.get('name', 'N/A')}")
    
    # 打印统计信息
    print(f"\n=== 统计信息 ===")
    print(f"总passage数量: {total_passages}")
    print(f"跨楼层passage数量: {vertical_passages}")
    print(f"普通passage数量: {regular_passages}")
    print(f"修改的passage数量: {modified_passages}")
    print(f"总电梯数量: {total_elevators}")
    print(f"修改的电梯数量: {modified_elevators}")
    print(f"总楼梯数量: {total_stairs}")
    print(f"修改的楼梯数量: {modified_stairs}")
    
    # 保存修改后的文件
    tree.write(output_file, encoding='UTF-8', xml_declaration=True)
    print(f"\n修改后的文件已保存至: {output_file}")

def is_vertical_passage_func(tag_dict):
    """
    判断是否是跨楼层passage
    跨楼层passage的特征：
    1. name标签包含'_passage_'和数字模式（由add_vertical_passages.py创建）
    2. 有osmAG:from和osmAG:to标签，且值相同（指向同一个电梯或楼梯）
    """
    name = tag_dict.get('name', '')
    osm_ag_from = tag_dict.get('osmAG:from', '')
    osm_ag_to = tag_dict.get('osmAG:to', '')
    
    # 检查name标签是否符合垂直passage的命名模式
    # 格式：elevator_passage_xxxx 或 stairs_passage_xxxx
    vertical_name_pattern = re.compile(r'(elevator|stairs)_passage_\d{4}')
    has_vertical_name = vertical_name_pattern.match(name)
    
    # 检查osmAG:from和osmAG:to是否相同且不为空
    # 跨楼层passage的from和to指向同一个电梯或楼梯名称
    has_same_from_to = (osm_ag_from and osm_ag_to and osm_ag_from == osm_ag_to)
    
    # 如果符合命名模式或者有相同的from/to标签，则认为是跨楼层passage
    return has_vertical_name or has_same_from_to

def verify_tags(file_path):
    """验证添加的标签是否符合要求"""
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    verification_passed = True
    error_count = 0
    total_regular_passages = 0
    total_elevators = 0
    total_stairs = 0
    
    for way in root.findall(".//way"):
        tags = {tag.get('k'): tag.get('v') for tag in way.findall(".//tag")}
        
        # 检查普通passage
        if tags.get('osmAG:type') == 'passage':
            if not is_vertical_passage_func(tags):
                total_regular_passages += 1
                
                # 检查是否有indoor=door标签
                if tags.get('indoor') != 'door':
                    print(f"错误: way {way.get('id')} 缺少或错误的indoor标签，期望 'door'，实际 '{tags.get('indoor', 'N/A')}'")
                    verification_passed = False
                    error_count += 1
                
                # 检查是否有door=yes标签
                if tags.get('door') != 'yes':
                    print(f"错误: way {way.get('id')} 缺少或错误的door标签，期望 'yes'，实际 '{tags.get('door', 'N/A')}'")
                    verification_passed = False
                    error_count += 1
        
        # 检查电梯
        elif tags.get('osmAG:areaType') == 'elevator':
            total_elevators += 1
            
            # 检查是否有room=elevator标签
            if tags.get('room') != 'elevator':
                print(f"错误: way {way.get('id')} 缺少或错误的room标签，期望 'elevator'，实际 '{tags.get('room', 'N/A')}'")
                verification_passed = False
                error_count += 1
        
        # 检查楼梯
        elif tags.get('osmAG:areaType') == 'stairs':
            total_stairs += 1
            
            # 检查是否有room=stairs标签
            if tags.get('room') != 'stairs':
                print(f"错误: way {way.get('id')} 缺少或错误的room标签，期望 'stairs'，实际 '{tags.get('room', 'N/A')}'")
                verification_passed = False
                error_count += 1
    
    print(f"\n=== 验证结果 ===")
    print(f"检查的普通passage数量: {total_regular_passages}")
    print(f"检查的电梯数量: {total_elevators}")
    print(f"检查的楼梯数量: {total_stairs}")
    
    if verification_passed:
        print("验证通过: 所有标签都正确添加")
    else:
        print(f"验证失败: 发现 {error_count} 个错误")
    
    return verification_passed

if __name__ == "__main__":
    # 使用固定的文件路径
    default_input = "/home/jay/AGSeg_ws/AGSeg/good-res/historical_museum/historical_museum460_merged_filtered_osmAG_texted.osm"
    default_output = "/home/jay/AGSeg_ws/AGSeg/good-res/historical_museum/historical_museum460_merged_filtered_osmAG_texted_added_tags.osm"
    
    input_file = input(f"请输入OSM文件路径 (默认: {default_input}): ").strip() or default_input
    output_file = input(f"请输入输出文件路径 (默认: {default_output}): ").strip() or default_output
    
    # 确保输出目录存在
    output_dir = os.path.dirname(output_file)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    try:
        # 执行添加标签
        add_tags_for_renderer(input_file, output_file)
        
        # 验证添加的标签
        print("\n正在验证添加的标签...")
        verify_tags(output_file)
        
    except ET.ParseError:
        print("错误: 无效的XML文件")
    except FileNotFoundError:
        print("错误: 找不到输入文件")
    except Exception as e:
        print(f"错误: {str(e)}") 
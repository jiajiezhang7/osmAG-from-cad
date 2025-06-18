#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试passage连接更新功能

此脚本用于验证当房间名称发生变化时，相关passage的osmAG:from和osmAG:to标签是否正确更新。
"""

import xml.etree.ElementTree as ET
import tempfile
import os
from add_text_to_osm import update_osm_tree

def create_test_osm():
    """
    创建一个测试用的OSM文件，包含房间和passage
    """
    osm_content = '''<?xml version="1.0" encoding="UTF-8"?>
<osm version="0.6" generator="test">
  <!-- 测试房间 -->
  <way id="-1001" action="modify" visible="true">
    <nd ref="-101"/>
    <nd ref="-102"/>
    <nd ref="-103"/>
    <nd ref="-104"/>
    <nd ref="-101"/>
    <tag k="indoor" v="room"/>
    <tag k="name" v="room_101"/>
    <tag k="osmAG:areaType" v="room"/>
    <tag k="osmAG:type" v="area"/>
  </way>
  
  <way id="-1002" action="modify" visible="true">
    <nd ref="-105"/>
    <nd ref="-106"/>
    <nd ref="-107"/>
    <nd ref="-108"/>
    <nd ref="-105"/>
    <tag k="indoor" v="room"/>
    <tag k="name" v="room_102"/>
    <tag k="osmAG:areaType" v="room"/>
    <tag k="osmAG:type" v="area"/>
  </way>
  
  <way id="-1003" action="modify" visible="true">
    <nd ref="-109"/>
    <nd ref="-110"/>
    <nd ref="-111"/>
    <nd ref="-112"/>
    <nd ref="-109"/>
    <tag k="indoor" v="room"/>
    <tag k="osmAG:areaType" v="room"/>
    <tag k="osmAG:type" v="area"/>
  </way>
  
  <!-- 测试passage -->
  <way id="-2001" action="modify" visible="true">
    <nd ref="-201"/>
    <nd ref="-202"/>
    <tag k="name" v="p_1"/>
    <tag k="osmAG:from" v="room_101"/>
    <tag k="osmAG:to" v="room_102"/>
    <tag k="osmAG:type" v="passage"/>
  </way>
  
  <way id="-2002" action="modify" visible="true">
    <nd ref="-203"/>
    <nd ref="-204"/>
    <tag k="name" v="p_2"/>
    <tag k="osmAG:from" v="room_102"/>
    <tag k="osmAG:to" v="room_-1003"/>
    <tag k="osmAG:type" v="passage"/>
  </way>
  
  <way id="-2003" action="modify" visible="true">
    <nd ref="-205"/>
    <nd ref="-206"/>
    <tag k="name" v="p_3"/>
    <tag k="osmAG:from" v="other_room"/>
    <tag k="osmAG:to" v="room_101"/>
    <tag k="osmAG:type" v="passage"/>
  </way>
</osm>'''
    
    return osm_content

def create_test_matches():
    """
    创建测试用的匹配结果
    """
    matches = {
        '-1001': [  # room_101 -> 办公室A
            {
                'text': '办公室A',
                'pixel_point': [100, 100],
                'match_type': 'inside',
                'score': 95
            }
        ],
        '-1002': [  # room_102 -> 会议室B
            {
                'text': '会议室B',
                'pixel_point': [200, 200],
                'match_type': 'inside',
                'score': 90
            }
        ],
        '-1003': [  # 无名房间 -> 存储间C
            {
                'text': '存储间C',
                'pixel_point': [300, 300],
                'match_type': 'nearby',
                'score': 80
            }
        ]
    }
    return matches

def run_test():
    """
    运行测试
    """
    print("开始测试passage连接更新功能...")
    
    # 创建临时文件
    with tempfile.NamedTemporaryFile(mode='w', suffix='.osm', delete=False, encoding='utf-8') as temp_file:
        temp_file.write(create_test_osm())
        temp_osm_path = temp_file.name
    
    try:
        # 解析OSM文件
        tree = ET.parse(temp_osm_path)
        root = tree.getroot()
        
        print("\n=== 更新前的状态 ===")
        print_rooms_and_passages(root)
        
        # 创建匹配结果
        matches = create_test_matches()
        
        print("\n=== 应用匹配结果 ===")
        for room_id, match_list in matches.items():
            for match in match_list:
                print(f"房间 {room_id} -> '{match['text']}'")
        
        # 应用更新
        updated_count = update_osm_tree(tree, matches)
        
        print(f"\n=== 更新结果 ===")
        print(f"更新了 {updated_count} 个房间")
        
        print("\n=== 更新后的状态 ===")
        print_rooms_and_passages(tree.getroot())
        
        # 验证结果
        print("\n=== 验证结果 ===")
        validate_updates(tree.getroot())
        
    finally:
        # 清理临时文件
        os.unlink(temp_osm_path)

def print_rooms_and_passages(root):
    """
    打印房间和passage的信息
    """
    print("房间信息:")
    for way in root.findall('.//way'):
        way_id = way.get('id')
        tags = {tag.get('k'): tag.get('v') for tag in way.findall('./tag')}
        
        if tags.get('indoor') == 'room':
            name = tags.get('name', '(无名称)')
            print(f"  房间 {way_id}: {name}")
    
    print("\nPassage信息:")
    for way in root.findall('.//way'):
        way_id = way.get('id')
        tags = {tag.get('k'): tag.get('v') for tag in way.findall('./tag')}
        
        if tags.get('osmAG:type') == 'passage':
            name = tags.get('name', '(无名称)')
            from_room = tags.get('osmAG:from', '(未设置)')
            to_room = tags.get('osmAG:to', '(未设置)')
            print(f"  Passage {way_id} ({name}): {from_room} -> {to_room}")

def validate_updates(root):
    """
    验证更新是否正确
    """
    success = True
    
    # 预期的更新结果
    expected_room_names = {
        '-1001': '办公室A',
        '-1002': '会议室B',
        '-1003': '存储间C'
    }
    
    expected_passage_updates = {
        '-2001': {'osmAG:from': '办公室A', 'osmAG:to': '会议室B'},
        '-2002': {'osmAG:from': '会议室B', 'osmAG:to': '存储间C'},
        '-2003': {'osmAG:from': 'other_room', 'osmAG:to': '办公室A'}  # 只有to应该更新
    }
    
    # 验证房间名称
    print("验证房间名称:")
    for way in root.findall('.//way'):
        way_id = way.get('id')
        tags = {tag.get('k'): tag.get('v') for tag in way.findall('./tag')}
        
        if tags.get('indoor') == 'room' and way_id in expected_room_names:
            expected_name = expected_room_names[way_id]
            actual_name = tags.get('name', '')
            
            if actual_name == expected_name:
                print(f"  ✅ 房间 {way_id}: '{actual_name}' (正确)")
            else:
                print(f"  ❌ 房间 {way_id}: 期望 '{expected_name}', 实际 '{actual_name}'")
                success = False
    
    # 验证passage连接
    print("\n验证passage连接:")
    for way in root.findall('.//way'):
        way_id = way.get('id')
        tags = {tag.get('k'): tag.get('v') for tag in way.findall('./tag')}
        
        if tags.get('osmAG:type') == 'passage' and way_id in expected_passage_updates:
            expected = expected_passage_updates[way_id]
            
            for key, expected_value in expected.items():
                actual_value = tags.get(key, '')
                
                if actual_value == expected_value:
                    print(f"  ✅ Passage {way_id}.{key}: '{actual_value}' (正确)")
                else:
                    print(f"  ❌ Passage {way_id}.{key}: 期望 '{expected_value}', 实际 '{actual_value}'")
                    success = False
    
    print(f"\n=== 测试结果: {'通过' if success else '失败'} ===")
    return success

if __name__ == "__main__":
    run_test() 
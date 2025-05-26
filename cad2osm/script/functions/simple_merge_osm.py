#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
简单合并两个OSM文件的脚本，不计算偏移量，只确保ID唯一性
用于合并绝对long/lat确定的osmAG,例如相邻的建筑物等
'''

import os
import sys
import argparse
import xml.etree.ElementTree as ET
from collections import defaultdict
import copy

def load_osm_file(file_path):
    '''
    加载OSM文件
    '''
    try:
        tree = ET.parse(file_path)
        root = tree.getroot()
        return root, tree
    except Exception as e:
        print(f"错误：无法加载OSM文件 {file_path}，原因：{e}")
        return None, None

def ensure_version_attribute(element):
    '''
    确保元素有version属性，JOSM需要此属性
    '''
    if 'version' not in element.attrib:
        element.set('version', '1')

def simple_merge_osm(file1, file2, output_file):
    '''
    简单合并两个OSM文件，确保ID唯一性
    '''
    # 加载第一个OSM文件
    root1, tree1 = load_osm_file(file1)
    if root1 is None:
        return False
    
    # 加载第二个OSM文件
    root2, tree2 = load_osm_file(file2)
    if root2 is None:
        return False
    
    # 创建合并后的OSM树
    merged_tree = copy.deepcopy(tree1)
    merged_root = merged_tree.getroot()
    
    # 获取第一个文件中的最大ID
    max_id = 0
    for element in root1.findall('.//*[@id]'):
        id_str = element.get('id')
        if id_str.startswith('-'):
            try:
                id_val = int(id_str)
                max_id = min(max_id, id_val)  # 负数ID，取最小值（绝对值最大）
            except ValueError:
                pass
    
    # ID映射字典
    id_mapping = {}
    
    # 处理第二个文件中的所有节点
    for node in root2.findall('.//node'):
        old_id = node.get('id')
        # 如果ID是负数，需要重新分配
        if old_id.startswith('-'):
            try:
                new_id = str(max_id - 1)  # 递减负数ID
                max_id = int(new_id)
                id_mapping[old_id] = new_id
                node.set('id', new_id)
            except ValueError:
                # 如果ID不是整数，保持原样
                id_mapping[old_id] = old_id
        else:
            # 正数ID不变
            id_mapping[old_id] = old_id
        
        ensure_version_attribute(node)
        merged_root.append(copy.deepcopy(node))
    
    # 处理第二个文件中的way
    for way in root2.findall('.//way'):
        old_id = way.get('id')
        # 如果ID是负数，需要重新分配
        if old_id.startswith('-'):
            try:
                new_id = str(max_id - 1)  # 递减负数ID
                max_id = int(new_id)
                id_mapping[old_id] = new_id
                way.set('id', new_id)
            except ValueError:
                # 如果ID不是整数，保持原样
                id_mapping[old_id] = old_id
        else:
            # 正数ID不变
            id_mapping[old_id] = old_id
        
        # 更新way中的nd引用
        for nd in way.findall('./nd'):
            ref = nd.get('ref')
            if ref in id_mapping:
                nd.set('ref', id_mapping[ref])
        
        ensure_version_attribute(way)
        merged_root.append(copy.deepcopy(way))
    
    # 处理第二个文件中的relation
    for relation in root2.findall('.//relation'):
        old_id = relation.get('id')
        # 如果ID是负数，需要重新分配
        if old_id.startswith('-'):
            try:
                new_id = str(max_id - 1)  # 递减负数ID
                max_id = int(new_id)
                id_mapping[old_id] = new_id
                relation.set('id', new_id)
            except ValueError:
                # 如果ID不是整数，保持原样
                id_mapping[old_id] = old_id
        else:
            # 正数ID不变
            id_mapping[old_id] = old_id
        
        # 更新relation中的member引用
        for member in relation.findall('./member'):
            ref = member.get('ref')
            if ref in id_mapping:
                member.set('ref', id_mapping[ref])
        
        ensure_version_attribute(relation)
        merged_root.append(copy.deepcopy(relation))
    
    # 保存合并后的文件
    merged_tree.write(output_file, encoding='UTF-8', xml_declaration=True)
    print(f"成功合并OSM文件并保存到: {output_file}")
    print(f"共处理了 {len(id_mapping)} 个元素的ID映射")
    return True

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='简单合并两个OSM文件，不计算偏移量，只确保ID唯一性')
    parser.add_argument('--file1', required=True, help='第一个OSM文件路径')
    parser.add_argument('--file2', required=True, help='第二个OSM文件路径')
    parser.add_argument('--output', required=True, help='输出OSM文件路径')
    args = parser.parse_args()
    
    # 执行合并
    success = simple_merge_osm(args.file1, args.file2, args.output)
    if success:
        print("合并完成！")
        return 0
    else:
        print("合并失败！")
        return 1

if __name__ == '__main__':
    sys.exit(main())

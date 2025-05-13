#!/usr/bin/env python
# -*- coding: utf-8 -*-

import xml.etree.ElementTree as ET
import argparse
import math
import copy

def is_clockwise(nodes):
    """
    判断多边形的旋转方向是顺时针还是逆时针
    使用叉积法计算多边形的有向面积
    在地理坐标系(lat/lon)中，正值表示顺时针，负值表示逆时针
    这与笛卡尔坐标系的判断正好相反
    
    参数:
        nodes: 包含(lat, lon)坐标的节点列表
    返回:
        True表示顺时针，False表示逆时针
    """
    # 计算有向面积（叉积和）
    area = 0.0
    for i in range(len(nodes)):
        j = (i + 1) % len(nodes)
        # 使用叉积公式: (x2-x1)*(y2+y1)
        area += (float(nodes[j][1]) - float(nodes[i][1])) * (float(nodes[j][0]) + float(nodes[i][0]))
    
    # 在地理坐标系(lat/lon)中：
    # 面积为正表示顺时针，为负表示逆时针
    # 这与笛卡尔坐标系的判断正好相反
    return area > 0

def correct_way_direction(osm_file, output_file=None):
    """
    读取OSM文件，调整way的节点顺序：
    - osmAG:areaType == room 的way应为逆时针
    - osmAG:areaType == structure 的way应为顺时针
    
    参数:
        osm_file: 输入的OSM文件路径
        output_file: 输出的OSM文件路径，默认为在原文件名后添加_direction_corrected
    """
    if output_file is None:
        output_file = osm_file.replace('.osm', '_direction_corrected.osm')
    
    # 解析XML文件
    tree = ET.parse(osm_file)
    root = tree.getroot()
    
    # 首先构建node_id到坐标的映射
    node_map = {}
    for node in root.findall('.//node'):
        node_id = node.get('id')
        lat = node.get('lat')
        lon = node.get('lon')
        node_map[node_id] = (lat, lon)
    
    # 处理所有way
    ways_processed = 0
    ways_reversed = 0
    
    for way in root.findall('.//way'):
        # 检查是否有area_type标签
        area_type = None
        for tag in way.findall('./tag[@k="osmAG:areaType"]'):
            area_type = tag.get('v')
        
        # 只处理room和structure类型
        if area_type not in ['room', 'structure']:
            continue
        
        ways_processed += 1
        
        # 获取所有节点引用
        nd_refs = way.findall('./nd')
        
        # 检查是否是闭合多边形（首尾节点相同）
        if len(nd_refs) < 4:  # 至少需要4个节点（包括重复的首尾节点）
            print(f"警告: Way {way.get('id')} 节点数量不足，跳过")
            continue
        
        first_node_ref = nd_refs[0].get('ref')
        last_node_ref = nd_refs[-1].get('ref')
        
        if first_node_ref != last_node_ref:
            print(f"警告: Way {way.get('id')} 不是闭合多边形，跳过")
            continue
        
        # 收集节点坐标
        nodes = []
        for nd in nd_refs[:-1]:  # 排除最后一个节点（与第一个相同）
            node_id = nd.get('ref')
            if node_id in node_map:
                nodes.append(node_map[node_id])
            else:
                print(f"警告: 节点 {node_id} 未找到，跳过 Way {way.get('id')}")
                break
        else:  # 只有当for循环正常完成时才执行
            # 判断当前方向
            current_clockwise = is_clockwise(nodes)
            
            # 根据area_type决定是否需要反转
            need_reverse = False
            if area_type == 'room' and current_clockwise:
                # room应为逆时针，但当前是顺时针，需要反转
                need_reverse = True
            elif area_type == 'structure' and not current_clockwise:
                # structure应为顺时针，但当前是逆时针，需要反转
                need_reverse = True
            
            if need_reverse:
                ways_reversed += 1
                # 反转节点顺序（保留首尾节点相同）
                nd_refs_copy = list(nd_refs)
                first_nd = nd_refs_copy[0]  # 保存第一个节点
                
                # 清除原有节点
                for nd in list(way):
                    if nd.tag == 'nd':
                        way.remove(nd)
                
                # 首先添加第一个节点
                way.append(first_nd)
                
                # 添加反转后的中间节点
                for nd in reversed(nd_refs_copy[1:-1]):
                    way.append(nd)
                    
                # 添加最后一个节点（与第一个相同）
                way.append(first_nd)
    
    # 保存修改后的文件
    tree.write(output_file, encoding='utf-8', xml_declaration=True)
    print(f"处理完成: 共处理 {ways_processed} 个way，反转了 {ways_reversed} 个way")
    print(f"已保存修正后的文件到: {output_file}")

def main():
    parser = argparse.ArgumentParser(description='调整OSM文件中way的节点顺序')
    parser.add_argument('input', help='输入的OSM文件路径')
    parser.add_argument('-o', '--output', help='输出的OSM文件路径')
    
    args = parser.parse_args()
    correct_way_direction(args.input, args.output)

if __name__ == '__main__':
    main()
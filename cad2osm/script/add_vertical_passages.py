#!/usr/bin/env python3
# 修复脚本，对于现有的osmAG（已经tag了elevator，stairs）， 加入针对跨楼层电梯和楼梯连通的passage
import xml.etree.ElementTree as ET
import math
import random
from collections import defaultdict

def calculate_polygon_center(nodes, node_dict):
    """
    计算多边形的中心点坐标
    使用更稳定的算法，确保相同形状的多边形计算出相同的中心点
    """
    # 收集所有节点的坐标
    points = []
    for nd_ref in nodes:
        node_id = nd_ref.get('ref')
        if node_id in node_dict:
            node = node_dict[node_id]
            lat = float(node.get('lat'))
            lon = float(node.get('lon'))
            points.append((lat, lon))
    
    if not points:
        return None, None
    
    # 使用多边形面积加权的质心计算方法
    # 这比简单平均更准确，对于相同形状的多边形会产生相同的中心点
    # 参考：https://en.wikipedia.org/wiki/Centroid#Of_a_polygon
    
    # 首先按照坐标排序，确保相同形状的多边形有相同的顺序
    # 这样即使节点ID不同，只要形状相同，中心点就会相同
    points.sort()
    
    # 计算质心
    area = 0
    cx = 0
    cy = 0
    
    # 对于简单多边形，我们可以使用更简单的算法
    # 直接计算边界框的中心点，这对于矩形电梯/楼梯足够准确
    min_lat = min(p[0] for p in points)
    max_lat = max(p[0] for p in points)
    min_lon = min(p[1] for p in points)
    max_lon = max(p[1] for p in points)
    
    # 使用边界框中心点，确保相同形状的多边形有相同的中心点
    center_lat = (min_lat + max_lat) / 2
    center_lon = (min_lon + max_lon) / 2
    
    # 格式化到固定小数位，避免浮点数精度问题
    center_lat = float(f"{center_lat:.10f}")
    center_lon = float(f"{center_lon:.10f}")
    
    return center_lat, center_lon

def add_vertical_passages(input_file, output_file):
    """
    为电梯和楼梯添加垂直连通的passage
    """
    # 解析XML文件
    tree = ET.parse(input_file)
    root = tree.getroot()
    
    # 创建新节点列表，稍后将其插入到文件前列
    new_nodes = []
    
    # 统计信息
    total_elevators = 0
    total_stairs = 0
    added_passages = 0
    added_nodes = 0
    
    # 创建节点ID和way ID的计数器（负数，避免与现有ID冲突）
    next_node_id = -1
    next_way_id = -1
    
    # 创建节点字典，用于快速查找
    node_dict = {}
    for node in root.findall(".//node"):
        node_dict[node.get('id')] = node
    
    # 按类型和楼层收集电梯和楼梯
    vertical_transports = defaultdict(lambda: defaultdict(list))
    
    # 找到所有电梯和楼梯
    for way in root.findall(".//way"):
        way_id = way.get('id')
        area_type_tag = way.find(".//tag[@k='osmAG:areaType']")
        level_tag = way.find(".//tag[@k='level']")
        name_tag = way.find(".//tag[@k='name']")
        
        if (area_type_tag is not None and level_tag is not None and name_tag is not None):
            area_type = area_type_tag.get('v')
            level = level_tag.get('v')
            name = name_tag.get('v')
            
            if area_type == 'elevator':
                vertical_transports['elevator'][name].append({
                    'way_id': way_id,
                    'level': level,
                    'nodes': way.findall('nd'),
                    'height': get_tag_value(way, 'height')
                })
                total_elevators += 1
            elif area_type == 'stairs':
                vertical_transports['stairs'][name].append({
                    'way_id': way_id,
                    'level': level,
                    'nodes': way.findall('nd'),
                    'height': get_tag_value(way, 'height')
                })
                total_stairs += 1
    
    # 为每种垂直运输方式创建passage
    for transport_type, name_groups in vertical_transports.items():
        for name, instances in name_groups.items():
            # 按楼层排序
            sorted_instances = sorted(instances, key=lambda x: float(x['level']))
            
            # 为相邻楼层创建passage
            for i in range(len(sorted_instances) - 1):
                lower = sorted_instances[i]
                upper = sorted_instances[i+1]
                
                # 计算两个多边形的中心点
                # 对于垂直重叠的电梯/楼梯，我们希望中心点在水平面上完全重合
                # 因此我们使用两个多边形的节点的并集来计算一个共同的中心点
                all_nodes = lower['nodes'] + upper['nodes']
                center_lat, center_lon = calculate_polygon_center(all_nodes, node_dict)
                
                if center_lat is None or center_lon is None:
                    print(f"警告: 无法计算 {transport_type} '{name}' 的中心点，跳过创建passage")
                    continue
                
                # 创建两个新节点，但不直接添加到root中
                lower_node = ET.Element('node')
                lower_node.set('id', str(next_node_id))
                lower_node.set('action', 'modify')
                lower_node.set('visible', 'true')
                lower_node.set('lat', str(center_lat))
                lower_node.set('lon', str(center_lon))
                # 添加level标签
                lower_level_tag = ET.SubElement(lower_node, 'tag')
                lower_level_tag.set('k', 'level')
                lower_level_tag.set('v', lower['level'])
                # 将节点添加到新节点列表
                new_nodes.append(lower_node)
                next_node_id -= 1
                added_nodes += 1
                
                upper_node = ET.Element('node')
                upper_node.set('id', str(next_node_id))
                upper_node.set('action', 'modify')
                upper_node.set('visible', 'true')
                upper_node.set('lat', str(center_lat))
                upper_node.set('lon', str(center_lon))
                # 添加level标签
                upper_level_tag = ET.SubElement(upper_node, 'tag')
                upper_level_tag.set('k', 'level')
                upper_level_tag.set('v', upper['level'])
                # 将节点添加到新节点列表
                new_nodes.append(upper_node)
                next_node_id -= 1
                added_nodes += 1
                
                # 创建连接passage - 使用更加易读的格式
                # 首先创建way元素
                passage = ET.Element('way')
                passage.set('id', str(next_way_id))
                passage.set('action', 'modify')
                passage.set('visible', 'true')
                next_way_id -= 1
                
                # 添加节点引用，使用缩进格式
                nd1 = ET.SubElement(passage, 'nd')
                nd1.set('ref', lower_node.get('id'))
                nd1.tail = '\n    '  # 添加缩进和换行
                
                nd2 = ET.SubElement(passage, 'nd')
                nd2.set('ref', upper_node.get('id'))
                nd2.tail = '\n    '  # 添加缩进和换行
                
                # 添加标签，使用缩进格式
                # height标签 (如果可用)
                if upper.get('height'):
                    height_tag = ET.SubElement(passage, 'tag')
                    height_tag.set('k', 'height')
                    height_tag.set('v', upper.get('height'))
                    height_tag.tail = '\n    '  # 添加缩进和换行
                
                # level标签
                level_tag = ET.SubElement(passage, 'tag')
                level_tag.set('k', 'level')
                level_tag.set('v', upper['level'])
                level_tag.tail = '\n    '  # 添加缩进和换行
                
                # name标签
                passage_name = f"{transport_type}_passage_{random.randint(1000, 9999)}"
                name_tag = ET.SubElement(passage, 'tag')
                name_tag.set('k', 'name')
                name_tag.set('v', passage_name)
                name_tag.tail = '\n    '  # 添加缩进和换行
                
                # osmAG:from标签
                from_tag = ET.SubElement(passage, 'tag')
                from_tag.set('k', 'osmAG:from')
                from_tag.set('v', name)
                from_tag.tail = '\n    '  # 添加缩进和换行
                
                # osmAG:to标签
                to_tag = ET.SubElement(passage, 'tag')
                to_tag.set('k', 'osmAG:to')
                to_tag.set('v', name)
                to_tag.tail = '\n    '  # 添加缩进和换行
                
                # osmAG:type标签
                type_tag = ET.SubElement(passage, 'tag')
                type_tag.set('k', 'osmAG:type')
                type_tag.set('v', 'passage')
                type_tag.tail = '\n  '  # 添加缩进和换行
                
                # 设置way元素的缩进
                passage.text = '\n    '  # 第一个子元素前的缩进
                passage.tail = '\n'  # way元素后的换行
                
                # 将创建好的passage添加到root
                root.append(passage)
                
                added_passages += 1
    
    # 打印统计信息
    print(f"总电梯数量: {total_elevators}")
    print(f"总楼梯数量: {total_stairs}")
    print(f"添加的passage数量: {added_passages}")
    print(f"添加的节点数量: {added_nodes}")
    
    # 将新节点插入到XML文件前列
    # 首先找到第一个way元素的位置
    first_way_index = None
    for i, child in enumerate(root):
        if child.tag == 'way':
            first_way_index = i
            break
    
    # 如果找到way元素，将新节点插入到第一个way元素之前
    # 如果没有way元素，则插入到最后
    if first_way_index is not None:
        # 逆序插入，使得节点顺序与添加顺序一致
        for node in reversed(new_nodes):
            root.insert(first_way_index, node)
    else:
        # 如果没有way元素，直接添加到最后
        for node in new_nodes:
            root.append(node)
    
    # 保存修改后的文件
    tree.write(output_file, encoding='UTF-8', xml_declaration=True)
    print(f"修改后的文件已保存至: {output_file}")

def get_tag_value(element, tag_key):
    """
    获取元素的标签值
    """
    tag = element.find(f".//tag[@k='{tag_key}']")
    return tag.get('v') if tag is not None else None

def verify_passages(file_path):
    """
    验证添加的passage是否符合要求
    """
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    verification_passed = True
    error_count = 0
    
    # 检查所有passage
    for way in root.findall(".//way"):
        type_tag = way.find(".//tag[@k='osmAG:type']")
        if type_tag is not None and type_tag.get('v') == 'passage':
            # 检查必要的标签
            from_tag = way.find(".//tag[@k='osmAG:from']")
            to_tag = way.find(".//tag[@k='osmAG:to']")
            level_tag = way.find(".//tag[@k='level']")
            name_tag = way.find(".//tag[@k='name']")
            
            if from_tag is None or to_tag is None:
                print(f"错误: passage {way.get('id')} 缺少from/to标签")
                verification_passed = False
                error_count += 1
            
            if level_tag is None:
                print(f"错误: passage {way.get('id')} 缺少level标签")
                verification_passed = False
                error_count += 1
            
            if name_tag is None:
                print(f"错误: passage {way.get('id')} 缺少name标签")
                verification_passed = False
                error_count += 1
            
            # 检查节点
            nodes = way.findall('nd')
            if len(nodes) != 2:
                print(f"错误: passage {way.get('id')} 应该有2个节点，实际有 {len(nodes)} 个")
                verification_passed = False
                error_count += 1
    
    if verification_passed:
        print("验证通过: 所有添加的passage都符合要求")
    else:
        print(f"验证失败: 发现 {error_count} 个错误")
    
    return verification_passed

if __name__ == "__main__":
    # 获取用户输入的文件路径，或使用默认路径
    default_input = "/home/jay/osm_vis_ws/data/SIST1_SEM_semanic_biggestever_right_height.osm"  # 替换为实际的默认输入文件路径
    default_output = "/home/jay/osm_vis_ws/data/SIST1_SEM_semanic_biggestever_with_vertical_passages.osm"  # 替换为实际的默认输出文件路径
    
    input_file = input(f"请输入OSM文件路径 (默认: {default_input}): ").strip() or default_input
    output_file = input(f"请输入输出文件路径 (默认: {default_output}): ").strip() or default_output
    
    try:
        # 执行添加垂直passage
        add_vertical_passages(input_file, output_file)
        
        # 验证添加的passage
        print("\n正在验证添加的passage...")
        verify_passages(output_file)
        
    except ET.ParseError:
        print("错误: 无效的XML文件")
    except FileNotFoundError:
        print("错误: 找不到输入文件")
    except Exception as e:
        print(f"错误: {str(e)}")

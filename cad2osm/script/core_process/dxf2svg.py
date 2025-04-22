# Last Edited by Jiajie 24.11.22 (Done)
# 很好的把经过图层过滤的  cad.dxf 转化为保留了细节的svg
import ezdxf
import svgwrite
import math
import os
import glob
import numpy as np
import json

def get_entity_bounds(entity):
    """获取单个实体的边界点"""
    points = []
    
    if entity.dxftype() == 'LINE':
        points = [(entity.dxf.start.x, entity.dxf.start.y),
                 (entity.dxf.end.x, entity.dxf.end.y)]
    
    elif entity.dxftype() == 'CIRCLE':
        center = entity.dxf.center
        radius = entity.dxf.radius
        # Add more points around circle for more precise bounds
        angles = [i * math.pi/4 for i in range(8)]
        points = [(center.x + radius * math.cos(angle),
                  center.y + radius * math.sin(angle)) for angle in angles]
    
    elif entity.dxftype() == 'ARC':
        center = entity.dxf.center
        radius = entity.dxf.radius
        start_angle = math.radians(entity.dxf.start_angle)
        end_angle = math.radians(entity.dxf.end_angle)
        
        # Add intermediate points for more precise bounds
        if end_angle < start_angle:
            end_angle += 2 * math.pi
        num_points = 8
        angle_step = (end_angle - start_angle) / num_points
        points = [(center.x + radius * math.cos(start_angle + i * angle_step),
                  center.y + radius * math.sin(start_angle + i * angle_step))
                 for i in range(num_points + 1)]
    
    elif entity.dxftype() == 'LWPOLYLINE':
        points = [(p[0], p[1]) for p in entity.get_points()]
        if getattr(entity, 'closed', False):
            points.append(points[0])
    
    elif entity.dxftype() == 'POLYLINE':
        points = [(vertex.dxf.location.x, vertex.dxf.location.y) 
                 for vertex in entity.vertices]
        if entity.is_closed:
            points.append(points[0])
    
    return points

def get_bounds(points):
    """从点集计算边界，添加边距"""
    if not points:
        return None
    
    xs, ys = zip(*points)
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    
    # 添加边距 (从 1% 增加到 3%)
    width = max_x - min_x
    height = max_y - min_y
    # 如果宽度或高度为0，给一个最小边距，避免padding为0
    base_dimension = max(width, height)
    if base_dimension == 0: 
        padding = 1.0 # 或者其他合适的默认小边距值
    else:
        padding = base_dimension * 0.03 # 从 0.01 增加到 0.03
    
    return (min_x - padding, min_y - padding, 
            max_x + padding, max_y + padding)

def get_modelspace_bounds(msp, lower_percentile=0.5, upper_percentile=99.5):
    """获取所有实体的整体边界 (使用百分位数过滤离群点)"""
    all_points = []
    for entity in msp:
        try:
            points = get_entity_bounds(entity)
            if points:
                all_points.extend(points)
        except Exception as e:
            # print(f"Warning: Skipping entity {entity.dxftype()} due to error: {e}")
            continue
    
    if not all_points:
        return None

    # 分离 x 和 y 坐标
    all_x = [p[0] for p in all_points]
    all_y = [p[1] for p in all_points]

    if not all_x: # 再次检查以防万一
        return None

    # 1. 计算坐标的百分位数边界
    try:
        min_x_bound = np.percentile(all_x, lower_percentile)
        max_x_bound = np.percentile(all_x, upper_percentile)
        min_y_bound = np.percentile(all_y, lower_percentile)
        max_y_bound = np.percentile(all_y, upper_percentile)
    except IndexError:
        # 如果 all_x 或 all_y 为空或 numpy 出错，回退到不进行过滤
        print("Warning: Error calculating percentiles. Falling back to using all points.")
        final_points = all_points
        return get_bounds(final_points)

    # 2. 过滤点
    filtered_points = [
        p for p in all_points
        if (min_x_bound <= p[0] <= max_x_bound) and \
           (min_y_bound <= p[1] <= max_y_bound)
    ]

    # 3. 如果过滤后没有点，则回退到使用所有点 (保险措施)
    if not filtered_points:
        print("Warning: Percentile filtering removed all points. Falling back to using all points.")
        final_points = all_points
    else:
        # print(f"Filtered points using percentiles: {len(filtered_points)}/{len(all_points)}")
        final_points = filtered_points

    # 4. 使用过滤后的点计算最终边界
    final_bounds = get_bounds(final_points)
    
    # print(f"Percentile bounds: x=[{min_x_bound}, {max_x_bound}], y=[{min_y_bound}, {max_y_bound}]")
    # print(f"Final bounds: {final_bounds}")

    return final_bounds

def normalize_coordinates(bounds, target_size=4000):  # 增加默认分辨率
    """规范化坐标"""
    min_x, min_y, max_x, max_y = bounds
    width = max_x - min_x
    height = max_y - min_y
    # 保持宽高比
    if width > height:
        scale = target_size / width
    else:
        scale = target_size / height
    return scale, min_x, min_y

def dxf_to_svg(input_path, output_path, target_size=4000):  # 增加默认分辨率
    try:
        doc = ezdxf.readfile(input_path)
        msp = doc.modelspace()
        
        bounds = get_modelspace_bounds(msp)
        if not bounds:
            return False, "无法获取图形边界，请检查DXF文件是否包含有效实体"
        
        scale, min_x, min_y = normalize_coordinates(bounds, target_size)
        
        width = (bounds[2] - bounds[0]) * scale
        height = (bounds[3] - bounds[1]) * scale
        
        # --- 新增：保存边界信息到 JSON 文件 ---
        bounds_path = os.path.splitext(output_path)[0] + '.bounds.json'
        bounds_data = {
            'min_x_padded': bounds[0],
            'min_y_padded': bounds[1],
            'max_x_padded': bounds[2],
            'max_y_padded': bounds[3],
            'svg_width_px': width, # 也保存计算出的svg像素尺寸
            'svg_height_px': height
        }
        try:
            with open(bounds_path, 'w') as f_bounds:
                json.dump(bounds_data, f_bounds, indent=4)
            # print(f"Saved bounds to: {bounds_path}")
        except Exception as e:
            print(f"Error saving bounds to {bounds_path}: {e}")
            return False, f"无法保存边界文件: {e}"
        # --- 结束新增 ---
        
        dwg = svgwrite.Drawing(output_path, 
                             size=(f'{width:.2f}px', f'{height:.2f}px'),
                             viewBox=f'0 0 {width:.2f} {height:.2f}')
        
        transform = f'translate({-min_x * scale},{height + min_y * scale}) scale({scale},-{scale})'
        group = dwg.g(transform=transform)
        
        # 减小线条宽度以保持细节 （TODO 可适度调整宽度）
        base_width = 2.0/scale  # 更细的基准线宽
        
        for entity in msp:
            if entity.dxftype() == 'LINE':
                group.add(dwg.line(
                    start=(entity.dxf.start.x, entity.dxf.start.y),
                    end=(entity.dxf.end.x, entity.dxf.end.y),
                    stroke='black',
                    stroke_width=base_width
                ))
            elif entity.dxftype() == 'CIRCLE':
                group.add(dwg.circle(
                    center=(entity.dxf.center.x, entity.dxf.center.y),
                    r=entity.dxf.radius,
                    stroke='black',
                    stroke_width=base_width,
                    fill='none'
                ))
            elif entity.dxftype() == 'ARC':
                start_angle = math.radians(entity.dxf.start_angle)
                end_angle = math.radians(entity.dxf.end_angle)
                radius = entity.dxf.radius
                center = entity.dxf.center
                
                if end_angle < start_angle:
                    end_angle += 2 * math.pi
                
                start_x = center.x + radius * math.cos(start_angle)
                start_y = center.y + radius * math.sin(start_angle)
                end_x = center.x + radius * math.cos(end_angle)
                end_y = center.y + radius * math.sin(end_angle)
                
                large_arc = 1 if (end_angle - start_angle > math.pi) else 0
                path = f'M {start_x},{start_y} A {radius},{radius} 0 {large_arc} 1 {end_x},{end_y}'
                group.add(dwg.path(d=path, stroke='black', 
                                 stroke_width=base_width, fill='none'))
            
            elif entity.dxftype() in ('POLYLINE', 'LWPOLYLINE'):
                points = []
                if entity.dxftype() == 'POLYLINE':
                    points = [(vertex.dxf.location.x, vertex.dxf.location.y) 
                             for vertex in entity.vertices]
                    is_closed = entity.is_closed
                else:
                    points = [(point[0], point[1]) for point in entity.get_points()]
                    is_closed = getattr(entity, 'closed', False)
                
                if points:
                    path_data = f'M {points[0][0]},{points[0][1]}'
                    for point in points[1:]:
                        path_data += f' L {point[0]},{point[1]}'
                    if is_closed:
                        path_data += ' Z'
                    group.add(dwg.path(d=path_data, stroke='black', 
                                     stroke_width=base_width, fill='none'))
        
        dwg.add(group)
        dwg.save()
        return True, "转换成功"
    
    except Exception as e:
        return False, f"转换失败: {str(e)}"


if __name__ == "__main__":
    # --- 用户可修改路径 ---
    input_dir = "/home/jay/AGSeg_ws/AGSeg/cad2osm/data/data_dxf/ShanghaiTech/teaching_center/filtered_trial/"
    output_dir = "/home/jay/AGSeg_ws/AGSeg/cad2osm/data/data_img/ShanghaiTech/teaching_center/svg_filtered_trial/"
    # --------------------

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 查找输入目录下的所有 DXF 文件
    dxf_files = glob.glob(os.path.join(input_dir, '*.dxf'))

    if not dxf_files:
        print(f"错误：在目录 '{input_dir}' 中未找到任何 .dxf 文件。")
    else:
        print(f"找到 {len(dxf_files)} 个 DXF 文件，开始批量转换...")
        success_count = 0
        fail_count = 0

        for input_file in dxf_files:
            filename = os.path.basename(input_file)
            svg_filename = os.path.splitext(filename)[0] + ".svg"
            svg_file = os.path.join(output_dir, svg_filename)

            print(f"--- 正在处理: {filename} ---")
            success, message = dxf_to_svg(input_file, svg_file)
            if success:
                print(f"  -> 转换成功: {svg_file}")
                success_count += 1
            else:
                print(f"  -> 转换失败: {message}")
                fail_count += 1

        print("\n--- 批量转换完成 ---")
        print(f"成功转换文件数: {success_count}")
        print(f"失败文件数: {fail_count}")
        print(f"SVG 文件保存在: {output_dir}")
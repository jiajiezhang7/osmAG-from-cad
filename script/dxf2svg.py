# Last Edited by Jiajie 24.11.22 (Done)
# 很好的把经过图层过滤的  cad.dxf 转化为保留了细节的svg
import ezdxf
import svgwrite
import math

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
    
    # 添加1%的边距
    width = max_x - min_x
    height = max_y - min_y
    padding = max(width, height) * 0.01
    
    return (min_x - padding, min_y - padding, 
            max_x + padding, max_y + padding)

def get_modelspace_bounds(msp):
    """获取所有实体的整体边界"""
    all_points = []
    for entity in msp:
        try:
            points = get_entity_bounds(entity)
            all_points.extend(points)
        except:
            continue
    
    if not all_points:
        return None
        
    return get_bounds(all_points)

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
    input_file = "/home/johnnylin/area_graph_segment/data_dxf/SIST-F1_filtered_20241126_211945.dxf"
    svg_file = "/home/johnnylin/area_graph_segment/data_dxf/new.svg"
    
    success, message = dxf_to_svg(input_file, svg_file)
    print(message)
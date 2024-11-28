import cv2
import numpy as np
import potrace
from svg.path import Path, Line
import svgwrite

def extract_boundaries(image_path, output_svg_path):
    """
    从分割图中提取边界并保存为SVG
    
    参数:
        image_path: 输入的分割图路径
        output_svg_path: 输出的SVG文件路径
    """
    # 读取图像
    img = cv2.imread(image_path)
    
    # 转换为灰度图
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 使用Canny边缘检测
    edges = cv2.Canny(img, 50, 150)
    
    # 可选：使用形态学操作细化边缘
    kernel = np.ones((3,3), np.uint8)
    edges = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel)
    
    # 找到轮廓
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # 创建SVG文件
    dwg = svgwrite.Drawing(output_svg_path, profile='tiny')
    
    # 添加轮廓到SVG
    for contour in contours:
        # 简化轮廓点
        epsilon = 0.01 * cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, epsilon, True)
        
        # 转换轮廓点为SVG路径
        points = approx.reshape(-1, 2)
        if len(points) >= 2:
            path_data = f"M {points[0][0]},{points[0][1]}"
            for point in points[1:]:
                path_data += f" L {point[0]},{point[1]}"
            path_data += " Z"  # 闭合路径
            
            # 添加路径到SVG，使用黑色线条
            dwg.add(dwg.path(d=path_data, stroke='black', fill='none', stroke_width=1))
    
    # 保存SVG文件
    dwg.save()

def alternative_boundary_extraction(image_path):
    """
    使用颜色差分方法提取边界
    
    参数:
        image_path: 输入的分割图路径
    返回:
        边界图像
    """
    # 读取图像
    img = cv2.imread(image_path)
    
    # 创建位移版本的图像
    shifted_right = np.roll(img, 1, axis=1)
    shifted_down = np.roll(img, 1, axis=0)
    
    # 计算颜色差异
    diff_x = np.any(img != shifted_right, axis=2)
    diff_y = np.any(img != shifted_down, axis=2)
    
    # 合并边界
    boundaries = np.logical_or(diff_x, diff_y)
    
    return boundaries.astype(np.uint8) * 255

# 使用示例
if __name__ == "__main__":
    input_file = "segmentation_map.png"
    output_file = "boundaries.svg"
    
    # 使用主要方法
    extract_boundaries(input_file, output_file)
    
    # 或者使用替代方法
    boundaries = alternative_boundary_extraction(input_file)
    cv2.imwrite("boundaries.png", boundaries)
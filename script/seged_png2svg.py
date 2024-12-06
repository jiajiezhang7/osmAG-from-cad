# Last edited by Jiajie Zhang 2024.12.06 
# 该脚本用于将Jiawei's Area Graph Segmented 可视化颜色分割结果 ---> 黑色描边的封闭多边形.svg
import cv2
import numpy as np
import potrace
from svg.path import Path, Line
import svgwrite

def extract_boundaries(image_path, output_svg_path):
    """
    从分割图中提取边界并保存为SVG
    """
    # 读取图像
    img = cv2.imread(image_path)
    
    # 1. 处理黑色边缘
    # 提取黑色像素
    black_mask = np.all(img < 30, axis=2).astype(np.uint8) * 255
    # 使用形态学操作连接断开的边缘
    kernel = np.ones((3,3), np.uint8)
    black_edges = cv2.morphologyEx(black_mask, cv2.MORPH_CLOSE, kernel)
    
    # 2. 处理颜色边界
    # 对图像进行轻度模糊以减少噪声
    blurred = cv2.GaussianBlur(img, (3,3), 0)
    # 计算颜色差异
    color_edges = np.zeros_like(black_mask)
    for i in range(img.shape[0]-1):
        for j in range(img.shape[1]-1):
            # 检查水平和垂直方向的颜色差异
            diff_h = np.any(np.abs(blurred[i,j] - blurred[i,j+1]) > 30)
            diff_v = np.any(np.abs(blurred[i,j] - blurred[i+1,j]) > 30)
            if diff_h or diff_v:
                color_edges[i,j] = 255

    # 合并两种边缘
    combined_edges = cv2.bitwise_or(black_edges, color_edges)
    
    # 使用更细致的轮廓检测参数
    contours, _ = cv2.findContours(combined_edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_TC89_KCOS)
    
    # 创建SVG文件
    dwg = svgwrite.Drawing(output_svg_path, profile='tiny')
    
    # 添加轮廓到SVG，使用更小的简化参数
    for contour in contours:
        if len(contour) >= 2:
            # 使用更小的epsilon值以保留更多细节
            epsilon = 0.001 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            points = approx.reshape(-1, 2)
            path_data = f"M {points[0][0]},{points[0][1]}"
            for point in points[1:]:
                path_data += f" L {point[0]},{point[1]}"
            path_data += " Z"
            
            dwg.add(dwg.path(d=path_data, stroke='black', fill='none', stroke_width=1))
    
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
    input_file = "/home/jay/agSeg_ws/area_graph_segment/build/290.png"
    output_file = "/home/jay/agSeg_ws/area_graph_segment/data_img/boundaries_290.svg"
    
    # 使用主要方法
    extract_boundaries(input_file, output_file)
    
    # 或者使用替代方法
    boundaries = alternative_boundary_extraction(input_file)
    cv2.imwrite("/home/jay/agSeg_ws/area_graph_segment/data_img/boundaries_290.png", boundaries)
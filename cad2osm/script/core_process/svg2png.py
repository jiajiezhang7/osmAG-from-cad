# Last Edited by Jiajie (Done)
#  可以把保留了dxf完美细节的svg转化为抗锯齿效果还不错的png，全白色背景，黑色线条为墙面
#  整合了墙壁空隙填充算法，生成的PNG将是墙壁填充后的结果
import numpy as np
import cv2
from svgpathtools import svg2paths
import cairosvg
from PIL import Image
import io
import os
import glob
import json

# 禁用PIL的最大图像尺寸限制
Image.MAX_IMAGE_PIXELS = None

class WallGapFiller:
    """建筑平面图墙壁轮廓填充器 - 整合版"""
    
    def __init__(self):
        self.kernel_sizes = {
            'small': cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)),
            'medium': cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)),
            'large': cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7)),
            'xlarge': cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
        }
    
    def detect_parallel_lines_improved(self, binary_image, gap_size='medium'):
        """
        改进的平行线检测 - 多尺度处理
        Args:
            binary_image: 二值图像 (线条为白色)
            gap_size: 空隙大小
        Returns:
            填充后的图像
        """
        results = []
        
        # 多尺度处理
        scales = ['small', 'medium', 'large']
        if gap_size == 'large':
            scales.append('xlarge')
        
        for scale in scales:
            kernel = self.kernel_sizes[scale]
            
            # 不同方向的结构元素
            horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel.shape[1]*3, 1))
            vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, kernel.shape[0]*3))
            
            # 检测水平线条
            horizontal_lines = cv2.morphologyEx(binary_image, cv2.MORPH_CLOSE, horizontal_kernel)
            horizontal_lines = cv2.morphologyEx(horizontal_lines, cv2.MORPH_OPEN, horizontal_kernel)
            
            # 检测垂直线条
            vertical_lines = cv2.morphologyEx(binary_image, cv2.MORPH_CLOSE, vertical_kernel)
            vertical_lines = cv2.morphologyEx(vertical_lines, cv2.MORPH_OPEN, vertical_kernel)
            
            # 合并当前尺度的结果
            scale_result = cv2.bitwise_or(horizontal_lines, vertical_lines)
            results.append(scale_result)
        
        # 合并所有尺度的结果
        combined = results[0]
        for result in results[1:]:
            combined = cv2.bitwise_or(combined, result)
        
        # 最终的形态学处理
        kernel = self.kernel_sizes[gap_size]
        filled = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel, iterations=2)
        
        return filled
    
    def distance_transform_fill(self, binary_image, max_distance=8):
        """
        使用距离变换来识别和填充墙壁内部
        Args:
            binary_image: 二值图像 (线条为白色)
            max_distance: 最大填充距离
        Returns:
            距离变换填充结果
        """
        # 计算距离变换
        dist_transform = cv2.distanceTransform(cv2.bitwise_not(binary_image), cv2.DIST_L2, 5)
        
        # 创建填充掩码：距离小于阈值的区域
        fill_mask = dist_transform < max_distance
        
        # 转换为二值图像
        filled = np.zeros_like(binary_image)
        filled[fill_mask] = 255
        
        # 与原始线条结合
        result = cv2.bitwise_or(binary_image, filled)
        
        return result
    
    def adaptive_morphology(self, binary_image, gap_size='medium'):
        """
        自适应形态学处理
        Args:
            binary_image: 二值图像
            gap_size: 空隙大小
        Returns:
            处理后的图像
        """
        # 分析图像中线条的平均宽度
        contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        avg_width = 3  # 默认值
        if contours:
            widths = []
            for contour in contours:
                rect = cv2.minAreaRect(contour)
                width, height = rect[1]
                if width > 0 and height > 0:
                    min_dim = min(width, height)
                    if min_dim > 1:
                        widths.append(min_dim)
            
            if widths:
                avg_width = int(np.mean(widths))
                avg_width = max(3, min(avg_width, 15))  # 限制在合理范围内
        
        # 根据分析结果创建自适应kernel
        adaptive_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (avg_width, avg_width))
        
        # 自适应形态学处理
        result = cv2.morphologyEx(binary_image, cv2.MORPH_CLOSE, adaptive_kernel, iterations=1)
        result = cv2.morphologyEx(result, cv2.MORPH_OPEN, self.kernel_sizes['small'], iterations=1)
        
        return result
    
    def detect_wall_contours_improved(self, binary_image):
        """
        改进的墙壁轮廓检测
        Args:
            binary_image: 二值图像 (线条为白色)
        Returns:
            轮廓列表
        """
        # 查找轮廓
        contours, _ = cv2.findContours(binary_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 更宽松的轮廓过滤条件
        filtered_contours = []
        image_area = binary_image.size
        
        for contour in contours:
            area = cv2.contourArea(contour)
            perimeter = cv2.arcLength(contour, True)
            
            # 计算轮廓的长宽比和紧凑度
            if area > 0 and perimeter > 0:
                # 获取最小外接矩形
                rect = cv2.minAreaRect(contour)
                width, height = rect[1]
                if width > 0 and height > 0:
                    aspect_ratio = max(width, height) / min(width, height)
                    
                    # 保留更多类型的轮廓
                    if (20 < area < image_area * 0.2 and  # 面积范围更宽
                        aspect_ratio > 1.5):  # 长宽比大于1.5的细长形状
                        filtered_contours.append(contour)
        
        return filtered_contours
    
    def fill_wall_gaps(self, binary_image, gap_size='medium'):
        """
        墙壁空隙填充主函数 - 多方法组合
        Args:
            binary_image: 二值图像 (线条为白色, 背景为黑色)
            gap_size: 空隙大小
        Returns:
            填充后的图像
        """
        # 方法1: 改进的平行线检测
        parallel_filled = self.detect_parallel_lines_improved(binary_image, gap_size)
        
        # 方法2: 距离变换填充
        distance_params = {'small': 5, 'medium': 8, 'large': 12}
        max_dist = distance_params.get(gap_size, 8)
        distance_filled = self.distance_transform_fill(binary_image, max_dist)
        
        # 方法3: 自适应形态学
        adaptive_filled = self.adaptive_morphology(binary_image, gap_size)
        
        # 合并所有方法的结果
        combined = cv2.bitwise_or(binary_image, parallel_filled)
        combined = cv2.bitwise_or(combined, distance_filled)
        combined = cv2.bitwise_or(combined, adaptive_filled)
        
        # 轮廓检测和填充
        contours = self.detect_wall_contours_improved(combined)
        
        # 创建输出图像
        result = combined.copy()
        
        # 填充所有检测到的轮廓
        if contours:
            cv2.fillPoly(result, contours, 255)
        
        # 最终的清理和连接
        kernel = self.kernel_sizes[gap_size]
        final_result = cv2.morphologyEx(result, cv2.MORPH_CLOSE, kernel, iterations=1)
        final_result = cv2.morphologyEx(final_result, cv2.MORPH_OPEN, self.kernel_sizes['small'], iterations=1)
        
        return final_result
    
    def remove_noise_improved(self, image, min_area=100):
        """
        改进的噪声去除 - 更智能的过滤
        Args:
            image: 输入图像 (墙壁为白色)
            min_area: 最小连通区域面积
        Returns:
            去噪后的图像
        """
        # 查找连通组件
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            image, connectivity=8
        )
        
        # 创建输出图像
        output = np.zeros_like(image)
        
        # 分析所有组件的特征
        areas = [stats[i, cv2.CC_STAT_AREA] for i in range(1, num_labels)]
        if areas:
            median_area = np.median(areas)
            # 动态调整最小面积阈值
            adaptive_min_area = max(min_area, median_area * 0.1)
        else:
            adaptive_min_area = min_area
        
        # 保留大于阈值的连通区域
        for i in range(1, num_labels):  # 跳过背景标签0
            area = stats[i, cv2.CC_STAT_AREA]
            width = stats[i, cv2.CC_STAT_WIDTH]
            height = stats[i, cv2.CC_STAT_HEIGHT]
            
            # 更智能的过滤条件
            aspect_ratio = max(width, height) / max(min(width, height), 1)
            
            # 保留大面积或细长形状的区域
            if (area >= adaptive_min_area or 
                (area >= min_area * 0.3 and aspect_ratio > 3)):
                output[labels == i] = 255
        
        return output

# 创建全局的墙壁填充器实例
wall_filler = WallGapFiller()

def load_bounds_json(svg_path):
    """
    从与SVG文件关联的bounds.json加载边界信息
    """
    bounds_path = os.path.splitext(svg_path)[0] + '.bounds.json'
    if os.path.exists(bounds_path):
        try:
            with open(bounds_path, 'r') as f:
                bounds_data = json.load(f)
            if 'svg_width_px' in bounds_data and 'svg_height_px' in bounds_data:
                return bounds_data
        except Exception as e:
            print(f"警告: 无法加载bounds.json文件: {e}")
    return None

def svg_to_occupancy_grid(svg_path, output_size=(4000, 4000), line_thickness=2, 
                         enable_wall_filling=True, gap_size='medium', min_area=100):
    """
    将线条式SVG地图转换为occupancy grid map
    保持原始线条的连续性和细节，并可选择应用墙壁填充算法
    如果存在bounds.json文件，则使用其中记录的尺寸
    """
    # 尝试加载bounds.json
    bounds_data = load_bounds_json(svg_path)
    if bounds_data:
        # 使用bounds.json中记录的尺寸
        target_width = int(bounds_data['svg_width_px'])
        target_height = int(bounds_data['svg_height_px'])
        print(f"使用bounds.json中的尺寸: {target_width}x{target_height}")
    else:
        # 使用默认尺寸但仍然保持宽高比
        target_width, target_height = output_size
        print(f"未找到bounds.json，使用默认尺寸: {target_width}x{target_height}")
    
    # 使用高质量设置进行初始渲染
    png_data = cairosvg.svg2png(
        url=svg_path,
        dpi=4800,  # 使用较高的DPI以保持细节
        scale=5.0   # 使用较大的缩放以确保线条质量
    )
    
    # 将PNG数据转换为PIL Image
    img = Image.open(io.BytesIO(png_data))
    
    # 使用bounds.json中的尺寸或保持宽高比调整大小
    if bounds_data:
        # 直接使用bounds.json中的尺寸
        new_width = target_width
        new_height = target_height
    else:
        # 获取原始尺寸
        original_width, original_height = img.size
        
        # 计算保持宽高比的新尺寸
        aspect_ratio = original_width / original_height
        if aspect_ratio > 1:
            new_width = target_width
            new_height = int(target_width / aspect_ratio)
        else:
            new_height = target_height
            new_width = int(target_height * aspect_ratio)
    
    # 使用Lanczos重采样调整大小
    img = img.resize((new_width, new_height), Image.LANCZOS)
    
    # 转换为numpy数组
    img_array = np.array(img)
    
    # 处理RGBA图像
    if len(img_array.shape) == 3 and img_array.shape[2] == 4:
        # 直接使用alpha通道，这样可以最好地保持原始线条
        binary = (img_array[:, :, 3] < 127).astype(np.uint8) * 255
    else:
        # 如果是RGB图像，转换为灰度后二值化
        img_gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        _, binary = cv2.threshold(img_gray, 127, 255, cv2.THRESH_BINARY)
    
    # 应用墙壁填充算法（可选）
    if enable_wall_filling:
        print("应用墙壁填充算法...")
        
        # 检查图像中的线条颜色：如果黑色像素较少，说明线条是黑色的，需要反转
        black_pixels = np.count_nonzero(binary == 0)
        white_pixels = np.count_nonzero(binary == 255)
        
        # 确保线条为白色，背景为黑色（wall_filler期望的格式）
        if black_pixels < white_pixels * 0.5:  # 黑色像素少于50%，说明线条是黑色的
            wall_input = cv2.bitwise_not(binary)  # 反转，使线条变为白色
        else:
            wall_input = binary.copy()
        
        # 应用墙壁填充算法
        filled_walls = wall_filler.fill_wall_gaps(wall_input, gap_size)
        
        # 去噪处理
        cleaned_walls = wall_filler.remove_noise_improved(filled_walls, min_area)
        
        # 将结果转换回原始格式（线条为黑色，背景为白色）
        binary = cv2.bitwise_not(cleaned_walls)
        
        print("墙壁填充完成")
    
    # 如果需要加粗线条
    if line_thickness > 1:
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (line_thickness, line_thickness))
        binary = cv2.dilate(binary, kernel, iterations=1)
    
    # 转换为0-1格式，1表示障碍物（黑色），0表示自由空间（白色）
    occupancy_grid = (binary < 128).astype(np.uint8)
    
    return occupancy_grid

def save_occupancy_grid(occupancy_grid, output_path):
    """
    保存occupancy grid map为PNG文件
    """
    # 转换为标准格式（黑色墙体，白色背景）
    img = ((1 - occupancy_grid) * 255).astype(np.uint8)
    
    # 使用最高质量设置保存PNG
    cv2.imwrite(
        output_path,
        img,
        [
            cv2.IMWRITE_PNG_COMPRESSION, 0,  # 无压缩
            cv2.IMWRITE_PNG_STRATEGY, cv2.IMWRITE_PNG_STRATEGY_DEFAULT
        ]
    )

# 使用示例
if __name__ == "__main__":
    # --- 用户可修改路径 ---
    input_dir = "/home/jay/AGSeg_ws/AGSeg/good-res/Universita-pianta-02/" # 输入 SVG 文件夹
    output_dir = "/home/jay/AGSeg_ws/AGSeg/good-res/Universita-pianta-02/" # 输出 PNG 文件夹
    target_output_size = (4000, 4000) # 默认目标 PNG 尺寸（当bounds.json不存在时使用）
    target_line_thickness = 1        # 输出 PNG 中的线条粗细 (1表示保持原样)
    
    # 墙壁填充算法参数
    enable_wall_filling = True       # 是否启用墙壁填充
    wall_gap_size = 'medium'        # 墙壁空隙大小: 'small', 'medium', 'large'
    wall_min_area = 100             # 最小连通区域面积
    # --------------------

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 查找输入目录下的所有 SVG 文件
    svg_files = glob.glob(os.path.join(input_dir, '*.svg'))

    if not svg_files:
        print(f"错误：在目录 '{input_dir}' 中未找到任何 .svg 文件。")
    else:
        print(f"找到 {len(svg_files)} 个 SVG 文件，开始批量转换...")
        if enable_wall_filling:
            print(f"墙壁填充已启用 - 空隙大小: {wall_gap_size}, 最小区域: {wall_min_area}")
        else:
            print("墙壁填充已禁用")
            
        success_count = 0
        fail_count = 0
        failed_files = []

        for svg_file in svg_files:
            filename = os.path.basename(svg_file)
            png_filename = os.path.splitext(filename)[0] + ".png"
            output_file = os.path.join(output_dir, png_filename)

            print(f"--- 正在处理: {filename} ---")
            try:
                grid = svg_to_occupancy_grid(
                    svg_file,
                    output_size=target_output_size,
                    line_thickness=target_line_thickness,
                    enable_wall_filling=enable_wall_filling,
                    gap_size=wall_gap_size,
                    min_area=wall_min_area
                )
                save_occupancy_grid(grid, output_file)
                print(f"  -> 转换成功: {output_file}")
                success_count += 1
            except Exception as e:
                print(f"  -> 转换失败: {filename} - {e}")
                fail_count += 1
                failed_files.append(filename)

        print("\n--- 批量转换完成 ---")
        print(f"成功转换文件数: {success_count}")
        print(f"失败文件数: {fail_count}")
        if failed_files:
            print("失败的文件列表:")
            for f in failed_files:
                print(f"  - {f}")
        print(f"PNG 文件保存在: {output_dir}")

    # # 旧的单文件处理逻辑 (注释掉或删除)
    # svg_file = "/home/jay/agSeg_ws/area_graph_segment/data_img/SIST_f1_latest_v5.svg"
    # output_file = "/home/jay/agSeg_ws/area_graph_segment/data_img/SIST_f1_latest_v5.png" 
    # grid = svg_to_occupancy_grid(
    #     svg_file,
    #     output_size=(4000, 4000),
    #     line_thickness=1  # 设为1保持原始线条粗细
    # )
    # save_occupancy_grid(grid, output_file)
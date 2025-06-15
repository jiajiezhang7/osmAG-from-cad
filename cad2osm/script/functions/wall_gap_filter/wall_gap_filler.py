#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
建筑平面图墙壁轮廓填充脚本 - 改进版
检测CAD平面图中的墙壁轮廓线（细长条矩形或平行线），将其内部填充为黑色
改进版本：提高识别率，使用多种检测方法组合
"""

import cv2
import numpy as np
import os
import argparse
from pathlib import Path


class WallGapFiller:
    """建筑平面图墙壁轮廓填充器 - 改进版"""
    
    def __init__(self):
        self.kernel_sizes = {
            'small': cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)),
            'medium': cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)),
            'large': cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7)),
            'xlarge': cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
        }
    
    def preprocess_image(self, image):
        """
        图像预处理 - 改进版
        Args:
            image: 输入图像
        Returns:
            处理后的二值图像 (墙壁线条为白色，背景为黑色)
        """
        # 转换为灰度图
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()
        
        # 轻微的高斯模糊去噪，保留更多细节
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)
        
        # 使用OTSU阈值进行二值化
        _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 检查图像中的线条颜色：如果黑色像素较少，说明线条是黑色的，需要反转
        black_pixels = np.count_nonzero(binary == 0)
        white_pixels = np.count_nonzero(binary == 255)
        
        if black_pixels < white_pixels * 0.5:  # 黑色像素少于50%，说明线条是黑色的
            binary = cv2.bitwise_not(binary)  # 反转，使线条变为白色
        
        return binary
    
    def detect_line_segments(self, binary_image):
        """
        使用霍夫变换检测直线段
        Args:
            binary_image: 二值图像 (线条为白色)
        Returns:
            线段图像
        """
        # 边缘检测
        edges = cv2.Canny(binary_image, 50, 150, apertureSize=3)
        
        # 霍夫直线检测
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=30, minLineLength=20, maxLineGap=10)
        
        # 创建线段图像
        line_image = np.zeros_like(binary_image)
        
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                cv2.line(line_image, (x1, y1), (x2, y2), 255, 2)
        
        return line_image
    
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
    
    def distance_transform_fill(self, binary_image, max_distance=10):
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
    
    def fill_wall_interiors_improved(self, binary_image, gap_size='medium'):
        """
        改进的墙壁内部填充 - 多方法组合
        Args:
            binary_image: 二值图像 (线条为白色)
            gap_size: 空隙大小
        Returns:
            填充后的图像
        """
        # 方法1: 改进的平行线检测
        parallel_filled = self.detect_parallel_lines_improved(binary_image, gap_size)
        
        # 方法2: 霍夫直线检测
        line_segments = self.detect_line_segments(binary_image)
        
        # 方法3: 距离变换填充
        distance_params = {'small': 5, 'medium': 8, 'large': 12}
        max_dist = distance_params.get(gap_size, 8)
        distance_filled = self.distance_transform_fill(binary_image, max_dist)
        
        # 方法4: 自适应形态学
        adaptive_filled = self.adaptive_morphology(binary_image, gap_size)
        
        # 合并所有方法的结果
        combined = cv2.bitwise_or(binary_image, parallel_filled)
        combined = cv2.bitwise_or(combined, line_segments)
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
    
    def enhance_wall_structure(self, image):
        """
        增强墙壁结构
        Args:
            image: 输入图像 (墙壁为白色)
        Returns:
            增强后的图像
        """
        # 使用形态学梯度增强边缘
        gradient = cv2.morphologyEx(image, cv2.MORPH_GRADIENT, self.kernel_sizes['small'])
        
        # 与原图结合
        enhanced = cv2.bitwise_or(image, gradient)
        
        return enhanced
    
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
    
    def process_image(self, image_path, output_path=None, gap_size='medium', 
                     min_area=100, save_steps=False):
        """
        处理单张图像 - 改进版
        Args:
            image_path: 输入图像路径
            output_path: 输出图像路径
            gap_size: 空隙大小
            min_area: 最小连通区域面积
            save_steps: 是否保存中间步骤
        Returns:
            处理后的图像
        """
        print(f"正在处理图像: {image_path}")
        
        # 读取图像
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"无法读取图像: {image_path}")
        
        # 获取输出路径
        if output_path is None:
            input_path = Path(image_path)
            output_path = input_path.parent / f"{input_path.stem}_filled{input_path.suffix}"
        
        # 步骤1: 预处理
        binary = self.preprocess_image(image)
        if save_steps:
            cv2.imwrite(str(output_path).replace('.', '_step1_binary.'), binary)
        
        # 步骤2: 改进的墙壁内部填充
        filled = self.fill_wall_interiors_improved(binary, gap_size)
        if save_steps:
            cv2.imwrite(str(output_path).replace('.', '_step2_filled.'), filled)
        
        # 步骤3: 增强墙壁结构
        enhanced = self.enhance_wall_structure(filled)
        if save_steps:
            cv2.imwrite(str(output_path).replace('.', '_step3_enhanced.'), enhanced)
        
        # 步骤4: 改进的噪声去除
        denoised = self.remove_noise_improved(enhanced, min_area)
        if save_steps:
            cv2.imwrite(str(output_path).replace('.', '_step4_denoised.'), denoised)
        
        # 最终步骤: 确保输出格式正确 - 墙壁为黑色(0)，背景为白色(255)
        # 当前denoised中墙壁是白色的，需要反转
        final = cv2.bitwise_not(denoised)
        
        # 保存最终结果
        cv2.imwrite(str(output_path), final)
        print(f"处理完成，结果保存至: {output_path}")
        
        return final
    
    def process_directory(self, input_dir, output_dir=None, **kwargs):
        """
        批量处理目录中的图像
        Args:
            input_dir: 输入目录
            output_dir: 输出目录
            **kwargs: 其他参数
        """
        input_path = Path(input_dir)
        if output_dir is None:
            output_path = input_path / "filled_results"
        else:
            output_path = Path(output_dir)
        
        # 创建输出目录
        output_path.mkdir(exist_ok=True)
        
        # 支持的图像格式
        image_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff'}
        
        # 处理所有图像文件
        for image_file in input_path.rglob('*'):
            if image_file.suffix.lower() in image_extensions:
                try:
                    output_file = output_path / f"{image_file.stem}_filled{image_file.suffix}"
                    self.process_image(image_file, output_file, **kwargs)
                except Exception as e:
                    print(f"处理图像 {image_file} 时出错: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='建筑平面图墙壁轮廓填充工具 - 改进版')
    parser.add_argument('input', help='输入图像文件或目录路径')
    parser.add_argument('-o', '--output', help='输出路径')
    parser.add_argument('-g', '--gap-size', choices=['small', 'medium', 'large'], 
                       default='medium', help='空隙大小 (默认: medium)')
    parser.add_argument('-m', '--min-area', type=int, default=100, 
                       help='最小连通区域面积 (默认: 100)')
    parser.add_argument('-s', '--save-steps', action='store_true', 
                       help='保存中间处理步骤')
    parser.add_argument('-b', '--batch', action='store_true', 
                       help='批量处理模式')
    
    args = parser.parse_args()
    
    # 创建处理器
    filler = WallGapFiller()
    
    try:
        if args.batch or Path(args.input).is_dir():
            # 批量处理
            filler.process_directory(
                args.input, args.output, 
                gap_size=args.gap_size, 
                min_area=args.min_area,
                save_steps=args.save_steps
            )
        else:
            # 单文件处理
            filler.process_image(
                args.input, args.output, 
                gap_size=args.gap_size, 
                min_area=args.min_area,
                save_steps=args.save_steps
            )
    except Exception as e:
        print(f"处理过程中出现错误: {e}")
        return 1
    
    print("处理完成！")
    return 0


if __name__ == "__main__":
    exit(main()) 
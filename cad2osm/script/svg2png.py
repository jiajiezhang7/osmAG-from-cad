# Last Edited by Jiajie (Done)
#  可以把保留了dxf完美细节的svg转化为抗锯齿效果还不错的png，全白色背景，黑色线条为墙面
import numpy as np
import cv2
from svgpathtools import svg2paths
import cairosvg
from PIL import Image
import io
import os
import glob

# 禁用PIL的最大图像尺寸限制
Image.MAX_IMAGE_PIXELS = None

def svg_to_occupancy_grid(svg_path, output_size=(4000, 4000), line_thickness=2):
    """
    将线条式SVG地图转换为occupancy grid map
    保持原始线条的连续性和细节
    """
    # 使用高质量设置进行初始渲染
    png_data = cairosvg.svg2png(
        url=svg_path,
        dpi=4800,  # 使用较高的DPI以保持细节
        scale=5.0   # 使用较大的缩放以确保线条质量
    )
    
    # 将PNG数据转换为PIL Image
    img = Image.open(io.BytesIO(png_data))
    
    # 获取原始尺寸
    original_width, original_height = img.size
    
    # 计算保持宽高比的新尺寸
    aspect_ratio = original_width / original_height
    if aspect_ratio > 1:
        new_width = output_size[0]
        new_height = int(output_size[0] / aspect_ratio)
    else:
        new_height = output_size[1]
        new_width = int(output_size[1] * aspect_ratio)
    
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
    input_dir = "/home/jay/AGSeg_ws/AGSeg/cad2osm/data/data_img/svg_filtered_trial/" # 输入 SVG 文件夹
    output_dir = "/home/jay/AGSeg_ws/AGSeg/cad2osm/data/data_img/png_filtered_trial/" # 输出 PNG 文件夹
    target_output_size = (4000, 4000) # 目标 PNG 尺寸
    target_line_thickness = 1        # 输出 PNG 中的线条粗细 (1表示保持原样)
    # --------------------

    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    # 查找输入目录下的所有 SVG 文件
    svg_files = glob.glob(os.path.join(input_dir, '*.svg'))

    if not svg_files:
        print(f"错误：在目录 '{input_dir}' 中未找到任何 .svg 文件。")
    else:
        print(f"找到 {len(svg_files)} 个 SVG 文件，开始批量转换...")
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
                    line_thickness=target_line_thickness
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
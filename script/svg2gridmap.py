# vanilla version， 可以把保留了dxf完美细节的svg转化为抗锯齿效果还不错的png，全白色背景，黑色线条为墙面
import numpy as np
import cv2
from svgpathtools import svg2paths
import cairosvg
from PIL import Image
import io

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
    svg_file = "/home/jay/areaGraph_ws/data_cad/SIST_f1_latest_v5.svg"
    output_file = "/home/jay/areaGraph_ws/data_cad/oc_5.png"
    
    grid = svg_to_occupancy_grid(
        svg_file,
        output_size=(4000, 4000),
        line_thickness=1  # 设为1保持原始线条粗细
    )
    
    save_occupancy_grid(grid, output_file)
# 建筑平面图墙壁轮廓填充工具

这是一个基于OpenCV的Python工具，专门用于处理CAD建筑平面图中的墙壁轮廓线，检测细长条矩形或平行线结构，并将其内部空隙填充为黑色，生成实心的墙壁结构。

## 功能特性

- **墙壁轮廓检测**: 自动识别CAD图中的细长条矩形和平行线结构
- **内部填充**: 将墙壁轮廓线之间的空隙填充为黑色
- **平行线处理**: 专门优化处理平行线结构的墙壁
- **多种处理模式**: 支持不同大小的空隙处理（small/medium/large）
- **批量处理**: 支持单文件和批量目录处理
- **中间步骤保存**: 可选择保存处理过程中的中间结果

## 处理原理

### 输入：CAD平面图
- 白色背景
- 墙壁呈现为细长条矩形或平行线（通常为黑色线条）

### 输出：填充后的平面图
- 白色背景
- 墙壁为实心黑色区域

### 处理流程

1. **图像预处理**
   - 转换为灰度图
   - 高斯模糊去噪
   - 二值化处理，确保线条为白色

2. **平行线检测**
   - 使用方向性形态学操作检测水平和垂直线条
   - 连接断开的线条片段
   - 填充平行线之间的空隙

3. **轮廓检测与填充**
   - 检测墙壁轮廓
   - 填充轮廓内部区域
   - 合并线条和填充区域

4. **结构增强**
   - 使用形态学梯度增强边缘
   - 确保墙壁结构完整

5. **噪声去除**
   - 连通组件分析
   - 保留大于阈值的墙壁区域

## 安装依赖

```bash
pip install -r requirements.txt
```

或者手动安装：

```bash
pip install opencv-python>=4.5.0 numpy>=1.20.0
```

## 使用方法

### 1. 命令行使用

#### 处理单张图像
```bash
python wall_gap_filler.py input_image.png -o output_image.png
```

#### 批量处理目录
```bash
python wall_gap_filler.py input_directory/ -o output_directory/ --batch
```

#### 使用不同参数
```bash
# 处理细小空隙
python wall_gap_filler.py input.png -g small -m 50

# 处理大空隙并保存中间步骤
python wall_gap_filler.py input.png -g large -s

# 批量处理并设置最小区域面积
python wall_gap_filler.py input_dir/ -b -m 200
```

### 2. 作为Python模块使用

```python
from wall_gap_filler import WallGapFiller

# 创建处理器实例
filler = WallGapFiller()

# 处理单张图像
result = filler.process_image(
    image_path="input.png",
    output_path="output.png",
    gap_size='medium',
    min_area=100,
    save_steps=True
)

# 批量处理
filler.process_directory(
    input_dir="input_images/",
    output_dir="output_images/",
    gap_size='medium',
    min_area=100
)
```

## 参数说明

### 命令行参数

- `input`: 输入图像文件或目录路径（必需）
- `-o, --output`: 输出路径（可选，默认在输入文件同目录）
- `-g, --gap-size`: 空隙大小，可选值：small/medium/large（默认：medium）
- `-m, --min-area`: 最小连通区域面积（默认：100）
- `-s, --save-steps`: 保存中间处理步骤
- `-b, --batch`: 批量处理模式

### 空隙大小设置

- **small**: 3x3像素结构元素，适合处理细密的线条结构
- **medium**: 5x5像素结构元素，适合处理标准的CAD线条
- **large**: 7x7像素结构元素，适合处理粗线条或大间隙

## 算法特点

### 针对CAD图优化

1. **方向性处理**: 分别处理水平和垂直线条，更适合建筑图纸
2. **平行线检测**: 专门识别和连接平行线结构
3. **轮廓填充**: 智能填充封闭或半封闭的墙壁轮廓
4. **结构保持**: 保持原始CAD图的精确结构

### 处理效果

- **输入**: 线条式墙壁（细线）→ **输出**: 实心墙壁（粗线/面）
- 保持墙壁的原始形状和比例
- 填充墙壁内部的空白区域
- 连接断开的墙壁段落

## 输出结果

- 处理后的图像将墙壁轮廓填充为实心黑色区域
- 如果启用`save_steps=True`，会保存以下中间结果：
  - `*_step1_binary.*`: 二值化结果
  - `*_step2_filled.*`: 轮廓填充结果
  - `*_step3_enhanced.*`: 结构增强结果
  - `*_step4_denoised.*`: 去噪结果

## 适用场景

1. **建筑CAD图纸**: 将线条式墙壁转换为实心墙壁
2. **平面图处理**: 增强墙壁的视觉效果
3. **图纸标准化**: 统一不同来源CAD图的墙壁表示方式
4. **预处理工作**: 为后续的建筑分析准备数据

## 优化建议

1. **参数调整**：
   - 对于精细线条，使用`gap_size='small'`
   - 对于标准CAD图，使用`gap_size='medium'`
   - 对于粗线条图，使用`gap_size='large'`

2. **预处理**：
   - 确保输入图像对比度清晰
   - 建议图像分辨率适中（避免过大或过小）

3. **后处理**：
   - 可根据需要调整`min_area`参数过滤小噪点
   - 结合其他CAD处理工具进行进一步优化

## 注意事项

- 支持的图像格式：PNG、JPG、JPEG、BMP、TIFF
- 最适合处理黑白或高对比度的CAD图纸
- 处理效果取决于原始图像的线条清晰度
- 建议先在小样本上测试参数设置

## 技术细节

### 核心算法

- **方向性形态学**: 使用水平和垂直核进行定向处理
- **轮廓检测**: 基于OpenCV的轮廓查找和填充
- **多层处理**: 结合线条检测和区域填充的混合方法

### 性能特点

- 专门优化处理建筑图纸的线条结构
- 保持原始比例和几何精度
- 高效的批量处理能力 
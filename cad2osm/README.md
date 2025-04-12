# CAD 到 OSM 转换工具集

本工具集实现了从CAD图纸（DWG格式）到OpenStreetMap（OSM）数据的自动化转换流程。

## 整体流程

```
DWG -> DXF -> Filtered DXF -> SVG -> PNG
```

整个转换流程包括以下步骤：
1. 使用 `dwg2dxf_oda.py` 将 DWG 文件转换为 DXF 格式
2. 使用 `dxf_layer_info.py` 分析 DXF 文件中的图层信息
3. 使用 `dxf_filter.py` 过滤 DXF 文件，保留墙体等关键图层
4. 使用 `dxf2svg.py` 将过滤后的 DXF 文件转换为 SVG 格式
5. 使用 `svg2png.py` 将 SVG 文件转换为 PNG 图像

## 1. DWG 到 DXF 转换脚本 (dwg2dxf_oda.py)

这个脚本用于将 DWG 文件转换为 DXF 格式，使用 ODA File Converter 作为转换工具。

### 基本用法
```bash
# 转换单个文件
python3 dwg2dxf_oda.py -i input.dwg -o output.dxf

# 批量转换目录
python3 dwg2dxf_oda.py -i input_dir -o output_dir

# 递归转换（包含子目录）
python3 dwg2dxf_oda.py -i input_dir -o output_dir -r

# 启用调试模式
python3 dwg2dxf_oda.py -i input.dwg -o output.dxf -d
```

### 调用方式

#### 1. 转换单个文件

如果你想转换单个 DWG 文件，可以使用以下命令：
```bash
python3 dwg2dxf_oda.py -i /path/to/input.dwg -o /path/to/output.dxf
```
- `-i` 或 `--input`：指定输入的 DWG 文件路径。
- `-o` 或 `--output`：指定输出的 DXF 文件路径。

#### 2. 批量转换目录中的文件

如果你想批量转换一个目录中的所有 DWG 文件，可以使用以下命令：
```bash
python3 dwg2dxf_oda.py -i /path/to/input_dir -o /path/to/output_dir
```
- `-i` 或 `--input`：指定输入的 DWG 文件目录。
- `-o` 或 `--output`：指定输出的 DXF 文件目录。

#### 3. 递归转换子目录中的文件

如果你希望递归地处理子目录中的 DWG 文件，可以添加 `-r` 或 `--recursive` 参数：
```bash
python3 dwg2dxf_oda.py -i /path/to/input_dir -o /path/to/output_dir -r
```

#### 4. 启用调试日志

如果你想查看更详细的日志信息，可以添加 `-d` 或 `--debug` 参数：
```bash
python3 dwg2dxf_oda.py -i /path/to/input.dwg -o /path/to/output.dxf -d
```

### 示例

假设你有一个 DWG 文件 `example.dwg`，你想将其转换为 `example.dxf`，可以使用以下命令：
```bash
python3 dwg2dxf_oda.py -i example.dwg -o example.dxf
```

如果你想批量转换 `input_folder` 目录中的所有 DWG 文件，并将结果保存到 `output_folder` 目录中，可以使用以下命令：
```bash
python3 dwg2dxf_oda.py -i input_folder -o output_folder -r
```

### 注意事项

- 确保 ODA File Converter 已正确安装，并且路径配置正确。
- 如果转换过程中遇到问题，可以启用调试日志 (`-d`) 来查看更详细的信息。

## 2. DXF 图层信息分析脚本 (dxf_layer_info.py)

这个脚本用于分析 DXF 文件中的图层信息，帮助了解 DXF 文件的结构和内容。

### 基本用法
```bash
python3 dxf_layer_info.py <input_dxf_file>
```

### 功能
- 提取 DXF 文件中的所有图层名称
- 解码 DXF 文件中的 Unicode 转义序列
- 生成图层信息报告文件

## 3. DXF 图层过滤脚本 (dxf_filter.py)

这个脚本用于过滤 DXF 文件中的图层，保留墙体等关键图层，去除不需要的图层。

### 基本用法
```bash
python3 dxf_filter.py
```

### 功能
- 根据预定义规则过滤 DXF 文件图层
- 保留包含"WALL"等关键词的图层
- 根据图层名称评分决定是否保留图层
- 生成过滤报告

### 输出文件
- 过滤后的 DXF 文件：`<原文件名>_filtered_<时间戳>.dxf`
- 过滤报告：`<原文件名>_filtered_<时间戳>_report.txt`

## 4. DXF 转 SVG 脚本 (dxf2svg.py)

这个脚本用于将 DXF 文件转换为 SVG 格式，保留图形的精确细节。

### 基本用法
```bash
python3 dxf2svg.py <input_dxf_file> <output_svg_file>
```

### 功能
- 将 DXF 文件转换为 SVG 格式
- 保持原始图形的精确细节
- 支持批量转换

## 5. SVG 转 PNG 脚本 (svg2png.py)

这个脚本用于将 SVG 文件转换为 PNG 图像，生成高质量的栅格图像。

### 基本用法
```bash
python3 svg2png.py <input_svg_file> <output_png_file>
```

### 功能
- 将 SVG 文件转换为 PNG 格式
- 生成抗锯齿效果良好的图像
- 支持批量转换
- 输出全白色背景，黑色线条表示墙面

## 依赖安装
```bash
pip install ezdxf svgwrite svgpathtools cairosvg pillow numpy opencv-python
```

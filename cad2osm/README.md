# CAD 到 OSM 转换工具集

本工具集负责CAD文件的预处理，将DWG格式转换为PNG图像，为后续的区域图分割做准备。

## 转换流程

```
DWG -> DXF -> Filtered DXF -> SVG -> PNG
```

## 核心脚本概览

| 脚本 | 功能 | 输入 | 输出 |
|------|------|------|------|
| `dwg2dxf_oda.py` | DWG转DXF | .dwg | .dxf |
| `dxf_layer_info.py` | 图层信息分析 | .dxf | 图层报告 |
| `dxf_filter.py` | DXF图层过滤 | .dxf | 过滤后.dxf |
| `dxf2svg.py` | DXF转SVG | .dxf | .svg + .bounds.json |
| `svg2png.py` | SVG转PNG | .svg | .png |

> 💡 **统一入口脚本**：文本提取功能请使用 `text_extract_module/text_extractor.py`

## 脚本详细说明

### 1. DWG 到 DXF 转换 (dwg2dxf_oda.py)

**功能**：使用 ODA File Converter 将 DWG 文件转换为 DXF 格式

**基本用法**：
```bash
# 转换单个文件
python3 dwg2dxf_oda.py -i input.dwg -o output.dxf

# 批量转换目录（递归）
python3 dwg2dxf_oda.py -i input_dir -o output_dir -r
```

**主要参数**：
- `-i, --input`: 输入文件或目录
- `-o, --output`: 输出文件或目录
- `-r, --recursive`: 递归处理子目录
- `-d, --debug`: 启用调试日志

**前置条件**：需要安装 ODA File Converter

### 2. DXF 图层信息分析 (dxf_layer_info.py)

**功能**：分析 DXF 文件中的图层信息，生成图层报告

**基本用法**：
```bash
python3 dxf_layer_info.py <input_dxf_file>
```

**输出**：图层信息报告文件，包含所有图层名称和Unicode解码

### 3. DXF 图层过滤 (dxf_filter.py)

**功能**：过滤 DXF 文件图层，保留墙体等关键图层

**基本用法**：
```bash
python3 dxf_filter.py  # 交互式选择文件
```

**输出文件**：
- `<原文件名>_filtered_<时间戳>.dxf` - 过滤后的DXF文件
- `<原文件名>_filtered_<时间戳>_report.txt` - 过滤报告

**过滤规则**：保留包含"WALL"等关键词的图层

### 4. DXF 转 SVG (dxf2svg.py)

**功能**：将 DXF 文件转换为 SVG 格式，保留图形精确细节

**基本用法**：
```bash
python3 dxf2svg.py <input_dxf_file> <output_svg_file>
```

**重要输出**：
- `.svg` 文件 - 矢量图形
- `.bounds.json` 文件 - **坐标转换边界信息**（文本提取模块必需）

### 5. SVG 转 PNG (svg2png.py)

**功能**：将 SVG 文件转换为高质量 PNG 图像

**基本用法**：
```bash
python3 svg2png.py <input_svg_file> <output_png_file>
```

**输出特点**：全白色背景，黑色线条表示墙面，适合区域图分割

## 环境依赖

**Python包依赖**：
```bash
pip install ezdxf svgwrite svgpathtools cairosvg pillow numpy opencv-python
```

**系统依赖**：
- ODA File Converter（用于DWG转DXF）

## 使用流程示例

```bash
# 1. DWG转DXF
python3 dwg2dxf_oda.py -i building.dwg -o building.dxf

# 2. 分析图层（可选）
python3 dxf_layer_info.py building.dxf

# 3. 过滤图层
python3 dxf_filter.py  # 选择building.dxf

# 4. DXF转SVG（生成.bounds.json）
python3 dxf2svg.py building_filtered.dxf building.svg

# 5. SVG转PNG
python3 svg2png.py building.svg building.png
```

> 📝 **下一步**：使用生成的PNG文件进行区域图分割，详见 [area_graph_segment/README.md](../area_graph_segment/README.md)

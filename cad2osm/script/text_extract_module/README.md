# CAD2OSM 文本提取模块

将DXF文件中的文本信息提取并匹配到osmAG.osm文件的房间中，为房间添加名称标签。

## 🎯 统一入口脚本

**推荐使用**：`text_extractor.py` - 一站式文本提取和房间命名解决方案

## 输入文件要求

| 文件类型 | 来源 | 说明 |
|---------|------|------|
| **DXF文件** | CAD原始文件 | 包含文本信息的建筑图纸 |
| **.bounds.json** | `dxf2svg.py`生成 | 坐标转换边界信息 |
| **osmAG.osm** | AreaGraph输出 | 包含房间多边形的拓扑地图 |
| **params.yaml** | 配置文件 | 可选，坐标转换参数 |

## 输出结果

- ✅ **更新后的OSM文件**：添加了房间名称的osmAG文件
- 📊 **可视化图像**：房间和文本匹配的可视化验证
- 📄 **中间JSON文件**：分步执行时的中间结果

## 使用方法

### 🚀 完整流程模式（推荐）

```bash
python text_extractor.py --mode full \
    --dxf <dxf_file> \
    --bounds <bounds_json> \
    --osm <osmAG.osm> \
    --output <output_osm> \
    [--config <params.yaml>] \
    [--visualize]
```

### 📋 主要参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--dxf` | DXF文件路径 | 必需 |
| `--bounds` | 边界信息JSON文件路径 | 必需 |
| `--osm` | osmAG.osm文件路径 | 必需 |
| `--output` | 输出OSM文件路径 | 必需 |
| `--config` | 配置文件路径 | 可选 |
| `--visualize` | 生成可视化图像 | False |
| `--layer` | DXF文本图层名称 | 'I—平面—文字' |
| `--nearby-threshold` | 附近匹配距离阈值(像素) | 50 |

### 🔧 分步执行模式

如需调试或自定义处理，可分步执行：

```bash
# 1. 提取文本
python text_extractor.py --mode extract_text --dxf <dxf_file> --output <text_json>

# 2. 转换坐标
python text_extractor.py --mode convert_coordinates --text <text_json> --bounds <bounds_json> --output <pixel_json>

# 3. 提取房间
python text_extractor.py --mode extract_rooms --osm <osmAG.osm> --output <rooms_json>

# 4. 匹配文本
python text_extractor.py --mode match_text --text <pixel_json> --rooms <rooms_json> --output <mapping_json>

# 5. 更新OSM
python text_extractor.py --mode update_osm --osm <osmAG.osm> --mapping <mapping_json> --output <output_osm>
```

## 完整工作流程

### 前置步骤

1. **CAD预处理**：
   ```bash
   cd cad2osm/script
   python dxf2svg.py <filtered_dxf> <output_svg>  # 生成.bounds.json
   python svg2png.py <svg_file> <png_file>
   ```

2. **区域图分割**：
   ```bash
   cd area_graph_segment/build
   ./bin/example_segmentation <png_file> 0.05 -1 -1 1.5  # 生成osmAG.osm
   ```

### 文本提取

3. **房间命名**：
   ```bash
   cd cad2osm/script/text_extract_module
   python text_extractor.py --mode full \
       --dxf <original_dxf> \
       --bounds <bounds_json> \
       --osm <osmAG.osm> \
       --output <texted_osm> \
       --visualize
   ```

## 使用示例

### 基本示例

```bash
python text_extractor.py --mode full \
    --dxf building.dxf \
    --bounds building.bounds.json \
    --osm building_osmAG.osm \
    --output building_texted.osm \
    --config params.yaml \
    --visualize
```

### 实际项目示例

```bash
# SIST-F1楼层处理
python text_extractor.py --mode full \
    --dxf /path/to/SIST-F1.dxf \
    --bounds /path/to/SIST-F1-filtered.bounds.json \
    --osm /path/to/SIST-F1_osmAG.osm \
    --output /path/to/SIST-F1_texted.osm \
    --config /path/to/params.yaml \
    --visualize
```

## 坐标转换原理

DXF到PNG像素坐标的转换：

```
pixel_x = (dxf_x - min_x_padded) * scale
pixel_y = svg_height - (dxf_y - min_y_padded) * scale
```

关键参数：
- `scale`: 由DXF边界和PNG尺寸计算的缩放因子
- `min_x_padded`, `min_y_padded`: DXF边界最小坐标（含边距）
- `svg_height`: SVG/PNG高度

## 环境依赖

```bash
pip install shapely xml.etree.ElementTree
```

## 注意事项

1. **文件对应**：确保.bounds.json与DXF文件对应
2. **图层名称**：根据CAD文件调整文本图层名称
3. **匹配阈值**：可根据实际情况调整距离阈值
4. **坐标系统**：使用与AreaGraph相同的坐标参考点

## 故障排除

**常见问题**：
- ❌ 找不到文本：检查图层名称是否正确
- ❌ 匹配失败：调整`--nearby-threshold`参数
- ❌ 坐标偏移：确认.bounds.json文件正确性
- ❌ 配置错误：检查params.yaml中的坐标参考点

**调试建议**：
- 使用`--visualize`参数查看匹配结果
- 分步执行模式逐步检查中间结果
- 检查日志输出中的警告信息

> 📝 **上一步**：确保已完成区域图分割，详见 [area_graph_segment/README.md](../../area_graph_segment/README.md)

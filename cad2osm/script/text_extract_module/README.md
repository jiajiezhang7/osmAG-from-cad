# CAD2OSM 文本提取模块

这个模块用于处理CAD文件到OSM格式的转换过程中的文本提取和匹配问题，特别是将DXF文本坐标与AreaGraph处理后的房间坐标进行匹配，并将文本标签添加到OSM文件中。

## 快速入门：使用统一脚本

为了简化工作流程，推荐使用统一入口脚本`text_extractor.py`进行文本提取和匹配。

### 必要的输入文件

使用`text_extractor.py`前，需要准备以下文件：

1. **DXF源文件**：包含文本信息的CAD原始文件
2. **边界信息文件**：由`dxf2svg.py`生成的`.bounds.json`文件，包含坐标转换所需的边界信息
3. **OSM文件**：由AreaGraph处理后生成的`osmAG.osm`文件，包含房间多边形信息
4. **配置文件**：可选的`params.yaml`配置文件，包含坐标转换参数

### 输出文件

脚本会生成以下输出：

1. **更新后的OSM文件**：添加了房间名称的OSM文件
2. **可视化图像**：可选的房间和文本匹配可视化图像
3. **中间JSON文件**：在分步执行模式下，会生成各步骤的中间结果JSON文件

## 统一入口脚本

### 统一入口脚本 (`text_extractor.py`)

为了简化工作流程，我们提供了一个统一的入口脚本 `text_extractor.py`，它整合了文本提取模块的所有功能，提供一站式处理流程。这个脚本可以执行完整的文本提取和匹配流程，也可以单独执行各个步骤。

#### 完整流程模式

```bash
python text_extractor.py --mode full \
    --dxf <dxf_file> \
    --bounds <bounds_json> \
    --osm <osmAG.osm> \
    --output <output_osm> \
    [--config <params.yaml>] \
    [--visualize] \
    [--layer <layer_name>]
```

参数:
- `--dxf`: DXF文件路径
- `--bounds`: dxf2svg.py生成的边界信息JSON文件路径
- `--osm`: AreaGraph生成的osmAG.osm文件路径
- `--output`: 输出的更新后的OSM文件路径
- `--config`: 可选的配置文件路径
- `--visualize`: 是否生成可视化图像
- `--visualization-output`: 可视化图像保存路径
- `--layer`: DXF文本图层名称，默认为'I—平面—文字'
- `--nearby-threshold`: 附近匹配的距离阈值，默认为50像素
- `--max-center-distance-ratio`: 内部匹配时，文本到中心距离与房间特征尺寸的比例阈值，默认为0.7

#### 分步执行模式

也可以单独执行各个步骤：

1. 提取文本：
```bash
python text_extractor.py --mode extract_text \
    --dxf <dxf_file> \
    --output <output_json> \
    [--layer <layer_name>]
```

2. 转换坐标：
```bash
python text_extractor.py --mode convert_coordinates \
    --text <text_json> \
    --bounds <bounds_json> \
    --output <output_json>
```

3. 提取房间多边形：
```bash
python text_extractor.py --mode extract_rooms \
    --osm <osmAG.osm> \
    --output <output_json>
```

4. 匹配文本到房间：
```bash
python text_extractor.py --mode match_text \
    --text <text_pixel_json> \
    --osm <osmAG.osm> \
    --output <mapping_json>
```

5. 更新OSM文件：
```bash
python text_extractor.py --mode update_osm \
    --text <mapping_json> \
    --osm <osmAG.osm> \
    --output <output_osm> \
    [--visualize]
```

## 原始工具说明

以下是各个独立工具的说明，这些工具已被统一入口脚本整合：

### 1. DXF文本坐标到像素坐标转换 (`dxf_text_to_pixel.py`)

将`extract_dxf_text.py`提取的DXF文本坐标转换为PNG像素坐标。

```bash
python dxf_text_to_pixel.py --input-json <extracted_text.json> --bounds-json <file.bounds.json> --output-json <output.json>
```

参数:
- `--input-json`: extract_dxf_text.py生成的文本JSON文件路径
- `--bounds-json`: dxf2svg.py生成的边界信息JSON文件路径
- `--output-json`: 输出的像素坐标JSON文件路径

### 2. 提取房间多边形 (`extract_room_polygons.py`)

从AreaGraph生成的osmAG.osm文件中提取房间多边形信息，并将经纬度坐标转换为像素坐标。脚本会自动尝试加载`cad2osm/config/params.yaml`配置文件。

```bash
python extract_room_polygons.py --input-osm <osmAG.osm> --output-json <rooms.json> [--config <custom_params.yaml>]
```

参数:
- `--input-osm`: AreaGraph生成的osmAG.osm文件路径
- `--output-json`: 输出的房间多边形JSON文件路径
- `--config`: 可选的自定义配置文件路径，如果提供则会覆盖默认配置

### 3. 匹配文本到房间 (`match_text_to_rooms.py`)

将转换后的文本像素坐标与房间多边形进行匹配，生成映射关系。可以选择直接更新osmAG.osm文件，将匹配到的文本赋值给房间的name标签。

```bash
python match_text_to_rooms.py --text-json <pixel_text.json> --rooms-json <rooms.json> --output-json <mapping.json> [--osm-file <osmAG.osm>] [--update-osm]
```

参数:
- `--text-json`: 包含像素坐标的文本JSON文件路径
- `--rooms-json`: 包含房间多边形的JSON文件路径
- `--output-json`: 输出的映射关系JSON文件路径
- `--osm-file`: 可选的osmAG.osm文件路径，用于更新房间名称
- `--update-osm`: 是否更新osmAG.osm文件，默认为否

## 完整工作流程

### 使用统一入口脚本的工作流程

1. 使用`dxf2svg.py`将DXF转换为SVG（同时生成.bounds.json文件）
   ```bash
   python /path/to/dxf2svg.py --input <dxf_file> --output <svg_file>
   ```
   - 这一步会在SVG文件同目录下生成必要的`.bounds.json`文件

2. 使用`svg2png.py`将SVG转换为PNG
   ```bash
   python /path/to/svg2png.py --input <svg_file> --output <png_file>
   ```

3. 使用AreaGraph处理PNG生成osmAG.osm
   - 这一步需要使用AreaGraph工具处理PNG图像
   - 生成的osmAG.osm文件包含房间多边形信息

4. 使用`text_extractor.py`一站式处理文本提取、坐标转换、房间提取、文本匹配和OSM更新
   ```bash
   python text_extractor.py --mode full \
       --dxf <dxf_file> \
       --bounds <bounds_json> \
       --osm <osmAG.osm> \
       --output <output_osm> \
       --config <params.yaml> \
       --visualize
   ```

### 文件准备清单

在运行统一脚本前，请确保以下文件已准备就绪：

| 文件类型 | 来源 | 说明 |
|---------|------|------|
| DXF文件 | 原始CAD文件 | 包含文本信息的CAD原始文件 |
| .bounds.json | dxf2svg.py生成 | 包含坐标转换所需的边界信息 |
| osmAG.osm | AreaGraph处理结果 | 包含房间多边形信息 |
| params.yaml | 配置文件 | 可选，包含坐标转换参数 |

### 统一脚本输出文件

执行完成后，脚本会生成以下文件：

| 文件类型 | 说明 |
|---------|------|
| 更新后的OSM文件 | 添加了房间名称的OSM文件 |
| 可视化图像 | 可选，房间和文本匹配的可视化图像 |
| 中间JSON文件 | 分步执行模式下的各步骤结果文件 |

### 使用独立工具的工作流程

1. 使用`extract_dxf_text.py`从DXF文件中提取文本信息
2. 使用`dxf2svg.py`将DXF转换为SVG（同时生成.bounds.json文件）
3. 使用`svg2png.py`将SVG转换为PNG
4. 使用AreaGraph处理PNG生成osmAG.osm
5. 使用`dxf_text_to_pixel.py`将DXF文本坐标转换为像素坐标
6. 使用`extract_room_polygons.py`从osmAG.osm提取房间多边形
7. 使用`match_text_to_rooms.py`将文本匹配到房间
8. 使用`add_text_to_osm.py`更新OSM文件

## 坐标转换原理

DXF到PNG像素坐标的转换公式：

```
pixel_x = (dxf_x - min_x_padded) * scale
pixel_y = svg_height - (dxf_y - min_y_padded) * scale
```

其中：
- `min_x_padded`, `min_y_padded`: DXF边界的最小坐标（带边距）
- `scale`: 缩放因子，由DXF边界尺寸和目标PNG尺寸计算得出
- `svg_height`: SVG/PNG的高度（像素）

## 依赖库

- json: 处理JSON文件
- argparse: 命令行参数解析
- shapely: 几何计算（点到多边形的距离、点是否在多边形内等）
- xml.etree.ElementTree: 解析XML文件

## 注意事项

1. 确保.bounds.json文件与提取的文本JSON文件对应同一个DXF文件
2. 匹配阈值（50像素）可能需要根据实际情况调整
3. `extract_room_polygons.py`脚本现在已经实现了经纬度到像素坐标的转换功能
4. 经纬度到像素坐标的转换实现了与`WGS84toCartesian.h`相同的投影计算方法
5. 脚本会自动尝试加载`cad2osm/config/params.yaml`配置文件
6. 如果找不到默认配置文件，脚本将使用硬编码的默认参数：root_lat=31.17947960435，root_lon=121.59139728509，root_pixel_x=3804.0，root_pixel_y=2801.0，resolution=0.044



## 使用示例

### 使用统一脚本 text_extractor.py 的示例

```bash
# 完整流程模式示例
python text_extractor.py --mode full \
--dxf /home/jay/AGSeg_ws/AGSeg/cad2osm/data/SIST/SIST-F1.dxf \
--bounds /home/jay/AGSeg_ws/AGSeg/cad2osm/data/SIST/img/svg_manual_filter/SIST-F1-filtered_new.bounds.json \
--osm /home/jay/AGSeg_ws/AGSeg/cad2osm/data/SIST/ag_osm/SIST-F1_clear_edited260_merged_filtered_osmAG.osm \
--output /home/jay/AGSeg_ws/AGSeg/cad2osm/data/SIST/ag_osm/SIST-F1_texted.osm \
--config /home/jay/AGSeg_ws/AGSeg/cad2osm/config/params.yaml \
--visualize \
--visualization-output /home/jay/AGSeg_ws/AGSeg/cad2osm/data/SIST/visualization/SIST-F1_text_matching.png
```

### 分步执行示例

```bash
# 1. 提取文本
python text_extractor.py --mode extract_text \
--dxf /home/jay/AGSeg_ws/AGSeg/cad2osm/data/SIST/SIST-F1.dxf \
--output /home/jay/AGSeg_ws/AGSeg/cad2osm/data/SIST/extract_text/SIST-F1.json \
--layer "I—平面—文字"

# 2. 转换坐标
python text_extractor.py --mode convert_coordinates \
--text /home/jay/AGSeg_ws/AGSeg/cad2osm/data/SIST/extract_text/SIST-F1.json \
--bounds /home/jay/AGSeg_ws/AGSeg/cad2osm/data/SIST/img/svg_manual_filter/SIST-F1-filtered_new.bounds.json \
--output /home/jay/AGSeg_ws/AGSeg/cad2osm/data/SIST/extract_text/SIST-F1_pixel.json

# 3. 提取房间多边形
python text_extractor.py --mode extract_rooms \
--osm /home/jay/AGSeg_ws/AGSeg/cad2osm/data/SIST/ag_osm/SIST-F1_clear_edited260_merged_filtered_osmAG.osm \
--output /home/jay/AGSeg_ws/AGSeg/cad2osm/data/SIST/extract_text/SIST-F1_rooms.json \
--config /home/jay/AGSeg_ws/AGSeg/cad2osm/config/params.yaml

# 4. 匹配文本到房间
python text_extractor.py --mode match_text \
--text /home/jay/AGSeg_ws/AGSeg/cad2osm/data/SIST/extract_text/SIST-F1_pixel.json \
--rooms /home/jay/AGSeg_ws/AGSeg/cad2osm/data/SIST/extract_text/SIST-F1_rooms.json \
--output /home/jay/AGSeg_ws/AGSeg/cad2osm/data/SIST/extract_text/SIST-F1_mapping.json

# 5. 更新OSM文件
python text_extractor.py --mode update_osm \
--osm /home/jay/AGSeg_ws/AGSeg/cad2osm/data/SIST/ag_osm/SIST-F1_clear_edited260_merged_filtered_osmAG.osm \
--mapping /home/jay/AGSeg_ws/AGSeg/cad2osm/data/SIST/extract_text/SIST-F1_mapping.json \
--output /home/jay/AGSeg_ws/AGSeg/cad2osm/data/SIST/ag_osm/SIST-F1_texted.osm \
--visualize
```

### 使用原始 add_text_to_osm.py 的示例（不推荐）

```bash
python /home/jay/AGSeg_ws/AGSeg/cad2osm/script/text_extract_module/add_text_to_osm.py \
--text-json /home/jay/AGSeg_ws/AGSeg/cad2osm/data/SIST/extract_text/SIST-F1.json \
--bounds-json /home/jay/AGSeg_ws/AGSeg/cad2osm/data/SIST/img/svg_manual_filter/SIST-F1-filtered_new.bounds.json \
--input-osm /home/jay/AGSeg_ws/AGSeg/cad2osm/data/SIST/ag_osm/SIST-F1_clear_edited260_merged_filtered_osmAG.osm \
--output-osm /home/jay/AGSeg_ws/AGSeg/cad2osm/data/SIST/ag_osm/SIST-F1_texted.osm \
--config /home/jay/AGSeg_ws/AGSeg/cad2osm/config/params.yaml \
--visualize \
--output-mapping-json /home/jay/AGSeg_ws/AGSeg/cad2osm/data/SIST/ag_osm/SIST-F1_mapping.json
```

### 使用新的统一入口脚本的示例

```bash
python /home/jay/AGSeg_ws/AGSeg/cad2osm/script/text_extract_module/text_extractor.py --mode full \
--dxf /home/jay/AGSeg_ws/AGSeg/cad2osm/data/SIST/dxf/original/SIST-F1.dxf \
--bounds /home/jay/AGSeg_ws/AGSeg/cad2osm/data/SIST/img/svg_manual_filter/SIST-F1-filtered_new.bounds.json \
--osm /home/jay/AGSeg_ws/AGSeg/cad2osm/data/SIST/ag_osm/SIST-F1_clear_edited260_merged_filtered_osmAG.osm \
--output /home/jay/AGSeg_ws/AGSeg/cad2osm/data/SIST/ag_osm/SIST-F1_texted_new.osm \
--config /home/jay/AGSeg_ws/AGSeg/cad2osm/config/params.yaml \
--visualize
```

```bash
python /home/jay/AGSeg_ws/AGSeg/cad2osm/script/text_extract_module/text_extractor.py --mode full \
--dxf /home/jay/AGSeg_ws/AGSeg/cad2osm/data/SIST/dxf/original/SIST-F2.dxf \
--bounds /home/jay/AGSeg_ws/AGSeg/cad2osm/data/SIST/img/svg_manual_filter/SIST-F2-filtered_new.bounds.json \
--osm /home/jay/AGSeg_ws/AGSeg/cad2osm/data/SIST/ag_osm/SIST-F2-filtered_new260_osmAG.osm \
--output /home/jay/AGSeg_ws/AGSeg/cad2osm/data/SIST/ag_osm/SIST-F2_texted.osm \
--config /home/jay/AGSeg_ws/AGSeg/cad2osm/config/params.yaml \
--visualize
```
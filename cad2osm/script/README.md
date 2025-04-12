# CAD2OSM 坐标转换工具集

这个工具集用于处理CAD文件到OSM格式的转换过程中的坐标转换问题，特别是将DXF文本坐标与AreaGraph处理后的房间坐标进行匹配。

## 工具说明

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

从AreaGraph生成的osmAG.osm文件中提取房间多边形信息，并将经纬度坐标转换为像素坐标。脚本会自动尝试加载`area_graph_segment/config/params.yaml`配置文件。

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

1. 使用`extract_dxf_text.py`从DXF文件中提取文本信息
2. 使用`dxf2svg.py`将DXF转换为SVG（同时生成.bounds.json文件）
3. 使用`svg2png.py`将SVG转换为PNG
4. 使用AreaGraph处理PNG生成osmAG.osm
5. 使用`dxf_text_to_pixel.py`将DXF文本坐标转换为像素坐标
6. 使用`extract_room_polygons.py`从osmAG.osm提取房间多边形
7. 使用`match_text_to_rooms.py`将文本匹配到房间

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
5. 脚本会自动尝试加载`area_graph_segment/config/params.yaml`配置文件
6. 如果找不到默认配置文件，脚本将使用硬编码的默认参数：root_lat=31.17947960435，root_lon=121.59139728509，root_pixel_x=3804.0，root_pixel_y=2801.0，resolution=0.044

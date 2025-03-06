# AGSeg 工程说明

本工程实现了从CAD图纸（DWG格式）到OpenStreetMap（OSM）数据的自动化转换流程。

## 整体流程

```
DWG -> DXF -> Filtered DXF -> SVG -> PNG -> Area Graph Segment -> PNG -> SVG -> OSM XML
```

## 使用步骤

### 1. DWG 到 DXF 转换脚本 (dwg2dxf_oda.py)

这个脚本用于将 DWG 文件转换为 DXF 格式，使用 ODA File Converter 作为转换工具。

#### 基本用法
```bash
cd cad2osm/script
# 转换单个文件
python3 dwg2dxf_oda.py -i input.dwg -o output.dxf
```

### 2. DXF 文件处理
```bash
cd cad2osm/script
python dxf_layer_info.py <input_dxf_file>  # 查看DXF文件中的图层信息
python filter_dxf.py <input_dxf_file> <output_filtered_dxf>  # 过滤并处理DXF文件
```

### 3. DXF 转 SVG
```bash
cd cad2osm/script
python dxf2svg.py <filtered_dxf_file> <output_svg_file>
```

### 4. SVG 转 PNG
```bash
cd cad2osm/script
python svg2png.py <input_svg_file> <output_png_file>
```

### 5. 区域图分割（Area Graph Segment）
区域图分割基于论文 "Area Graph: Generation of Topological Maps using the Voronoi Diagram" (ICAR 2019)实现。

#### 依赖安装
```bash
# Ubuntu系统下安装必要依赖
sudo apt-get install g++
sudo apt-get install cmake
sudo apt-get install qt4-default
sudo apt-get install libcgal-dev
```

#### 编译
```bash
cd area_graph_segment
mkdir build
cd build
cmake ..
make example_segmentation
```

#### 运行
```bash
./bin/example_segmentation <input_png_file> <resolution> <door_width> <corridor_width> <noise_percentage>
```

参数说明：
- input_png_file: 输入的地图PNG文件（注意：地图背景色应该比障碍物点颜色深）
- resolution: 地图分辨率（默认为0.05）
- door_width: 环境中最宽门的宽度（如果不确定，设置为-1，将使用固定值W=1.25）
- corridor_width: 环境中最窄走廊的宽度（如果不确定，设置为-1）
- noise_percentage: 地图中预估的噪声百分比（如果使用afterAlphaRemoval目录中的地图作为输入，可设为0）

示例：
```bash
./bin/example_segmentation input.png 0.05 -1 -1 1.5
# 或者指定具体的门宽和走廊宽度
./bin/example_segmentation input.png 0.05 0.85 2.7 1.5
```

### 6. PNG 转 SVG
```bash
cd area_graph_segment
python png2svg.py <segmented_png_file> <output_svg_file>
```

### 7. SVG 转 OSM

#### 依赖安装
```bash
pip install svgpathtools numpy pyproj
```

#### 使用方法
```bash
cd svg_to_osm
# 转换单个文件
python -m svg_to_osm.main <input_svg_file> <output_osm_file> \
    --center-lat 31.17947960453 \
    --center-lon 121.59139728492

# 批量转换目录
python -m svg_to_osm.main <input_svg_folder> <output_osm_folder> \
    --center-lat 31.17947960453 \
    --center-lon 121.59139728492
```

主要参数说明：
- `--scale-num`: 比例尺分子，默认为1.0
- `--scale-div`: 比例尺分母，默认为19.0
- `--curve-steps`: 曲线插值步数，默认为3
- `--center-lat`: 中心纬度
- `--center-lon`: 中心经度
- `--projection`: 投影代码，默认为EPSG:3857
- `--min-segment`: 最小线段长度(米)，默认为0.1

可以根据需要调整这些参数来优化转换效果。比如：
- 调整`scale-num`和`scale-div`来控制地图大小
- 增加`curve-steps`提高曲线精度
- 减小`min-segment`保留更多细节


## 目录结构说明
- `cad2osm/`: DXF文件处理和转换相关代码
- `area_graph_segment/`: 图像分割处理相关代码
- `svg_to_osm/`: SVG转OSM相关代码
- `osmAG_doc/`: osmAG standards文档
## 注意事项
1. 确保输入的DWG/DXF文件使用正确的图层命名规范
2. 转换过程中注意检查每个步骤的输出是否正确
3. 建议保留每个步骤的中间文件，便于问题定位

## 常见问题
如遇到问题，请检查：
1. 输入文件格式是否正确
2. Python环境及依赖包是否正确安装
3. 文件路径是否正确
4. 图层命名是否符合规范

如需更多帮助，请参考各子目录下的详细文档。

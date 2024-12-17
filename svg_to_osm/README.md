# SVG to OSM Converter

一个将 SVG 文件转换为 OpenStreetMap (OSM) XML 格式的工具

## 主要功能

- 支持单个 SVG 文件转换为 OSM 格式
- 支持批量处理整个目录下的 SVG 文件
- 支持自定义坐标系统和投影参数
- 支持 SVG 路径、组和变换的解析
- 支持曲线平滑度和精度的调整
- 输出标准的 OSM XML 格式

## 环境要求

### Python 版本
- Python 3.6 或更高版本

### 依赖包

- svgpathtools
- numpy
- pyproj

## 使用方法

### 基本用法

1. 转换单个文件：

python -m svg_to_osm.main input.svg output.osm \
--center-lat 31.17947960453 \
--center-lon 121.59139728492

2. 批量转换目录：

python -m svg_to_osm.main ./svg_folder ./osm_folder \
--center-lat 31.17947960453 \
--center-lon 121.59139728492


### 参数说明

#### 比例参数

--scale-num <数值> # 比例尺分子，默认为 1.0
--scale-div <数值> # 比例尺分母，默认为 19.0

#### 曲线参数

--curve-steps <整数> # 曲线插值步数，默认为 3

#### 投影参数

--center-lat <纬度> # 中心纬度，默认为 31.17947960453
--center-lon <经度> # 中心经度，默认为 121.59139728492
--projection <投影代码> # 默认为 EPSG:3857 (Web墨卡托)

#### SVG解析选项

--no-groups # 禁用SVG组解析
--no-transforms # 禁用SVG变换解析
--min-segment <数值> # 最小线段长度(米)，默认为 0.1

## 参数调优建议

1. **比例调整**：
   - 如果转换后的地图太大或太小，调整 `scale-num` 和 `scale-div`
   - 建议先用小数据测试找到合适的比例

2. **精度控制**：
   - 增加 `curve-steps` 可以提高曲线精度
   - 减小 `min-segment` 可以保留更多细节
   - 但两者都会增加输出文件大小
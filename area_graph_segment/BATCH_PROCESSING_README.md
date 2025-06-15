# 批量处理PNG文件指南

本文档介绍如何使用批量处理脚本自动化处理多个PNG建筑平面图文件。

## 概述

### 新增的命令行参数支持

现在 `area_graph_segmentation` 支持以下命令行参数来覆盖 `params.yaml` 中的配置：

```bash
./bin/area_graph_segmentation image.png [options]

Options:
  --resolution <value>        地图分辨率 (米/像素)
  --door-width <value>        门宽度
  --corridor-width <value>    走廊宽度  
  --noise-percent <value>     噪声百分比 (0-100)
  --png-width <value>         PNG图像宽度
  --png-height <value>        PNG图像高度
  --root-lat <value>          根节点纬度
  --root-lon <value>          根节点经度
  --root-pixel-x <value>      根节点像素X位置
  --root-pixel-y <value>      根节点像素Y位置
  --simplify-tolerance <value> 多边形简化容差
  --spike-angle <value>       毛刺移除角度阈值
  --spike-distance <value>    毛刺移除距离阈值
  --min-room-area <value>     最小房间面积过滤
  --clean-input <0|1>         启用输入清理
  --remove-furniture <0|1>    启用家具移除
  --record-time               启用时间记录
```

### 批量处理脚本功能

`batch_process_png.py` 脚本提供以下功能：

1. **自动建筑类型识别**: 根据文件名自动识别建筑类型
2. **智能参数配置**: 为不同建筑类型设置最适合的参数
3. **图像尺寸自适应**: 根据图片大小自动调整分辨率
4. **批量处理**: 一次处理整个目录的PNG文件
5. **进度监控**: 显示处理进度和结果统计

## 使用方法

### 1. 基本用法

```bash
# 进入area_graph_segment目录
cd area_graph_segment

# 批量处理指定目录的所有PNG文件
python3 batch_process_png.py /path/to/png/directory

# 例如处理cad2osm中的PNG文件
python3 batch_process_png.py ../cad2osm/data/web-cad/img/png_manual_filter
```

### 2. 预览模式

在实际执行前，可以使用预览模式查看将要执行的命令：

```bash
python3 batch_process_png.py ../cad2osm/data/web-cad/img/png_manual_filter --dry-run
```

### 3. 过滤特定文件

```bash
# 只处理包含"apartment"的文件
python3 batch_process_png.py ../cad2osm/data/web-cad/img/png_manual_filter --filter apartment

# 跳过包含"hotel"的文件
python3 batch_process_png.py ../cad2osm/data/web-cad/img/png_manual_filter --skip hotel
```

### 4. 指定可执行文件路径

```bash
python3 batch_process_png.py ../cad2osm/data/web-cad/img/png_manual_filter --executable ./bin/area_graph_segmentation
```

## 建筑类型配置

脚本会根据文件名自动识别以下建筑类型，并应用相应的参数配置：

### 支持的建筑类型

| 建筑类型 | 关键词 | 特点 |
|---------|--------|------|
| apartment | apartment, residential | 住宅公寓，门较窄，房间较小 |
| office | office, ufficio, schema-ufficio | 办公楼，廊道适中，房间规整 |
| hotel | hotel | 酒店，廊道较宽，房间标准化 |
| school | school, scuola, aule, universita | 学校，大廊道，大房间 |
| gym | gym, gymnasium | 体育馆，超大空间 |
| museum | museum, centro, cultural | 博物馆/文化中心，展览空间 |
| monastery | monastery | 修道院，传统建筑风格 |
| default | 其他 | 默认配置 |

### 参数配置示例

以下是不同建筑类型的典型参数配置：

```python
"apartment": {
    "resolution": 0.04,        # 分辨率
    "door_width": 0.9,         # 门宽0.9米
    "corridor_width": 1.2,     # 廊宽1.2米  
    "min_room_area": 8.0       # 最小房间8平米
}

"office": {
    "resolution": 0.035,
    "door_width": 1.0,         # 门宽1.0米
    "corridor_width": 1.5,     # 廊宽1.5米
    "min_room_area": 12.0      # 最小房间12平米
}

"hotel": {
    "resolution": 0.04,
    "door_width": 0.9,
    "corridor_width": 1.8,     # 酒店廊道较宽
    "min_room_area": 6.0       # 酒店房间可以较小
}
```

## 文件输出

每个处理的PNG文件会生成：

1. `{filename}_output/` 目录包含所有中间和最终结果
2. `{filename}_roomGraph.png` - 房间分割结果图
3. `{filename}_osmAG.osm` - OSM格式的结果文件

## 处理流程

1. **文件识别**: 扫描目录中的PNG文件
2. **类型判断**: 根据文件名识别建筑类型
3. **参数配置**: 加载对应建筑类型的参数配置
4. **尺寸分析**: 获取图片尺寸，调整分辨率参数
5. **命令构建**: 构建完整的命令行参数
6. **执行处理**: 调用area_graph_segmentation执行处理
7. **结果统计**: 输出处理成功/失败统计

## 故障排除

### 常见问题

1. **Python依赖问题**:
```bash
pip install Pillow  # 安装PIL库用于图像处理
```

2. **可执行文件路径问题**:
```bash
# 确保area_graph_segmentation已编译
cd area_graph_segment
make

# 或指定完整路径
python3 batch_process_png.py /path/to/png --executable /full/path/to/bin/area_graph_segmentation
```

3. **权限问题**:
```bash
chmod +x batch_process_png.py
chmod +x bin/area_graph_segmentation
```

### 调试建议

1. 先使用 `--dry-run` 模式预览命令
2. 从单个文件开始测试
3. 检查输出目录的日志文件
4. 确保PNG文件格式正确

## 扩展配置

如需添加新的建筑类型或调整参数，请修改 `batch_process_png.py` 中的 `BUILDING_CONFIGS` 字典。

## 性能建议

- 大批量处理时建议在后台运行
- 可以使用 `--filter` 参数分批处理
- 监控磁盘空间，每个文件会生成较多中间文件 
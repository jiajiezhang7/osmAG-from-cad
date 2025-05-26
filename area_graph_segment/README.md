# Area Graph - 区域图分割

## 概述

Area Graph 通过 Voronoi 图将室内环境分割成不同区域（房间、走廊等），生成拓扑地图用于机器人导航和路径规划。

**核心输出**：**osmAG.osm** - 包含房间几何形状、拓扑关系和语义信息的标准OSM XML格式文件

## 统一入口脚本

```bash
# 编译后的可执行文件
./bin/example_segmentation <input_png> <resolution> <door_width> <corridor_width> <noise_percentage>
```

## 学术背景

基于论文：Hou, J., Yuan, Y., and Schwertfeger, S., "Area Graph: Generation of Topological Maps using the Voronoi Diagram", ICAR 2019.

📄 [论文链接](https://arxiv.org/abs/1910.01019)

## 算法流程

1. **预处理** → **Voronoi图生成** → **拓扑图生成** → **房间检测** → **区域合并** → **osmAG导出**

核心步骤：
- 使用 Alpha Shape 算法进行家具移除和房间检测
- 基于 Voronoi 图生成拓扑结构
- 多边形优化，去除毛刺和尖角
- 输出标准OSM XML格式

## 快速开始

### 环境依赖

**Ubuntu系统安装**：
```bash
sudo apt-get install g++ cmake qtbase5-dev libcgal-dev
```

### 编译运行

```bash
cd area_graph_segment/
mkdir build && cd build
cmake ..
make example_segmentation

# 运行
./bin/example_segmentation <input_png> <resolution> <door_width> <corridor_width> <noise_percentage>
```

## 参数说明

| 参数 | 说明 | 推荐值 |
|------|------|--------|
| `input_png` | 输入PNG地图文件（白色背景，黑色障碍物） | - |
| `resolution` | 地图分辨率 | `0.05` |
| `door_width` | 最宽门的宽度（-1为自动） | `-1` 或 `0.85` |
| `corridor_width` | 最窄走廊宽度（-1为自动） | `-1` 或 `2.7` |
| `noise_percentage` | 噪声百分比估计 | `1.5` |

**使用示例**：
```bash
# 自动参数（推荐）
./bin/example_segmentation input.png 0.05 -1 -1 1.5

# 手动指定门宽和走廊宽度
./bin/example_segmentation input.png 0.05 0.85 2.7 1.5
```

## 高级配置

通过 `config/params.yaml` 可调整：

**多边形处理**：
- `simplify_tolerance`: 简化容差 (默认: 0.05)
- `spike_angle_threshold`: 毛刺角度阈值 (默认: 60.0°)

**小房间合并**：
- `min_area`: 最小房间面积 (默认: 4.0 m²)
- `max_merge_distance`: 最大合并距离 (默认: 1.5 m)

**坐标系统**：
- `root_node`: 地理坐标参考点设置

## 输出结果

| 文件 | 说明 | 用途 |
|------|------|------|
| **osmAG.osm** | 🎯 **核心输出** - OSM格式的拓扑地图 | 机器人导航、路径规划 |
| 彩色区域图 | 不同区域的颜色标记图像 | 可视化验证 |
| 轮廓图 | 区域边界的黑白图像 | 调试分析 |

### osmAG格式特点

**osmAG**（OpenStreetMap Area Graph）是标准OSM XML格式，包含：
- 🏠 **房间几何**：多边形轮廓和面积信息
- 🔗 **拓扑关系**：房间间的连接关系
- 🏷️ **语义标签**：房间类型、名称等属性
- 🎯 **导航友好**：直接支持OSM生态系统

## 代码架构

| 模块 | 功能 |
|------|------|
| **VoriGraph** | Voronoi图数据结构和处理 |
| **TopoGraph** | 拓扑图生成和优化 |
| **RoomDect** | 房间检测算法 |
| **AreaGraph** | 区域图生成和合并 |
| **osmAGExport** | OSM格式导出和多边形优化 |

## 参数调优建议

**减少过度分割**：
- 增大 `alphaShapeRemovalSquaredSize`: 625 → 900-1000
- 增大 `topoGraphMarkAsFeatureEdgeLength`: 16 → 20-24

**配置文件调整**：修改 `config/params.yaml` 中的多边形处理和房间合并参数

## 应用场景

- 🤖 **机器人导航**：高级别拓扑信息，支持语义导航
- 🗺️ **路径规划**：基于区域的高效路径规划
- 📍 **室内定位**：语义化定位和空间理解
- 💬 **人机交互**：理解"去会议室"等自然语言指令

> 📝 **下一步**：使用文本提取模块为房间添加名称，详见 [cad2osm/script/text_extract_module/README.md](../cad2osm/script/text_extract_module/README.md)

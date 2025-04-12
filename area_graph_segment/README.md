# Area Graph

## 概述

Area Graph 是一种用于生成室内环境拓扑地图的方法，通过 Voronoi 图将环境分割成不同的区域（如房间、走廊等），并表示它们之间的连接关系。这种表示方法对于机器人导航、路径规划和空间理解具有重要意义，能够帮助机器人更好地理解和交互于复杂的室内环境。

本项目的最终输出是 **osmAG** （OpenStreetMap Area Graph）格式的文件，它将区域图转换为标准的 OSM XML 格式，便于与现有导航和地图工具集成。osmAG 是整个工作流程中最重要的结果，它包含了房间的几何形状、拓扑关系和语义信息，可直接用于机器人导航和路径规划。

## 论文

本代码库实现了以下论文中描述的方法，该论文发表于 ICAR2019。论文预印本可在 [Arxiv](https://arxiv.org/abs/1910.01019) 获取。

Hou, J., Yuan, Y., and Schwertfeger, S., "Area Graph: Generation of Topological Maps using the Voronoi Diagram", 19th International Conference on Advanced Robotics (ICAR): IEEE Press, 2019.

```bibtex
@conference {hou2019area,
    title = {Area Graph: Generation of Topological Maps using the Voronoi Diagram},
    booktitle = {19th International Conference on Advanced Robotics (ICAR)},
    year = {2019},
    publisher = {IEEE Press},
    organization = {IEEE Press},
    author = {Hou, Jiawei and Yuan, Yijun and Schwertfeger, S{\"}oren}
}
```

## 算法流程

Area Graph 生成过程主要包括以下步骤：

1. **预处理**：
   - 去噪处理，移除地图中的噪点
   - 使用 Alpha Shape 算法进行家具移除

2. **Voronoi 图生成**：
   - 从输入地图中提取障碍物点
   - 基于这些点生成 Voronoi 图
   - 将 Voronoi 图转换为结构化表示

3. **拓扑图生成**：
   - 移除小边和死端
   - 保留最大连通分量

4. **房间检测**：
   - 使用 Alpha Shape 和多边形切割来检测房间区域
   - 标记门口和通道位置

5. **区域图生成与合并**：
   - 合并相似区域，减少过度分割
   - 优化最终区域图

6. **osmAG格式导出**：
   - 将区域图转换为OSM XML格式
   - 优化多边形，去除毛刺和尖角
   - 生成包含房间和通道信息的osmAG文件

## 编译方法

### 依赖项

在运行代码之前，请确保已安装以下依赖项：
- cmake
- g++
- Eigen3
- Qt4
- CGAL

在 Ubuntu 系统上，可以通过以下命令安装：

```bash
sudo apt-get install g++
sudo apt-get install cmake
sudo apt-get install qtbase5-dev
sudo apt-get install libcgal-dev
```

代码已在 Ubuntu 22.04上测试通过。

### 使用方法

按照以下步骤构建和运行 Area Graph 生成代码：

```bash
cd /path/to/area_graph_segment/
mkdir build
cd build
cmake ..
make example_segmentation
./bin/example_segmentation <Map.png> <resolution> <door_width> <corridor_width> <noise_percentage>
```

参数说明：

* **Map.png**：要生成 Area Graph 的地图文件。注意：请不要使用背景颜色比障碍物点更亮的地图。
* **resolution**：地图分辨率（默认值为 0.05）
* **door_width**：环境中最宽门的宽度
* **corridor_width**：环境中最窄走廊的宽度
  - 如果不知道门宽和走廊宽度，将这两个参数设为 -1，程序将使用固定值 W = 1.25 运行 Alpha Shape 算法来检测房间
* **noise_percentage**：地图中的噪声百分比估计值。如果使用 "afterAlphaRemoval" 目录中的地图作为输入，可以将此参数设为 0。

可以通过配置文件 `config/params.yaml` 调整更多参数，包括：

* **polygon_processing**：多边形处理参数
  - **simplify_enabled**：是否启用多边形简化（默认为 true）
  - **simplify_tolerance**：简化容差（默认为 0.05）
  - **spike_removal_enabled**：是否启用毛刺去除（默认为 true）
  - **spike_angle_threshold**：毛刺角度阈值（默认为 60.0）
  - **spike_distance_threshold**：毛刺距离阈值（默认为 0.30）

* **small_room_merge**：小房间合并参数
  - **enabled**：是否启用小房间合并（默认为 true）
  - **min_area**：小房间面积阈值（默认为 4.0 平方米）
  - **max_merge_distance**：最大合并距离（默认为 1.5 米）

* **root_node**：根节点坐标设置
  - **latitude**：纬度坐标
  - **longitude**：经度坐标

<!-- SIST-1-D走廊宽度=2.4m, 门宽=1.6m -->
示例：

```bash
./bin/area_graph_segmentation ../dataset/input/Freiburg79_scan_furnitures_trashbins.png 0.05 -1 -1 1.5
```

或者指定具体的门宽和走廊宽度：

```bash
./bin/area_graph_segmentation ../dataset/input/Freiburg79_scan_furnitures_trashbins.png 0.05 0.85 2.7 1.5
```

## 输出结果

程序会生成以下输出文件：
1. **osmAG.osm**：最重要的输出结果，包含了房间、通道等拓扑信息的OSM格式文件，可用于导航和路径规划
2. 彩色区域图：显示不同区域用不同颜色标记
3. 轮廓图：显示区域边界的黑白图像

### osmAG格式

osmAG（OpenStreetMap Area Graph）是本项目的核心输出格式，它将室内环境的拓扑结构以OSM XML格式表示，包含以下关键元素：

- 房间节点：表示环境中的各个区域（房间、走廊等）
- 通道连接：表示区域之间的连接关系
- 几何信息：包含房间的多边形轮廓
- 拓扑关系：描述房间之间的连接方式

这种格式特别适合用于机器人导航和路径规划，可以直接被支持OSM格式的导航系统使用。

## 代码结构

主要组件包括：

- **VoriGraph**：Voronoi 图的数据结构和处理函数
- **TopoGraph**：拓扑图的数据结构和处理函数
- **RoomDect**：房间检测算法
- **AreaGraph**：区域图生成和优化
- **osmAGExport**：将区域图转换为 osmAG 格式的模块，包含多边形优化和简化功能

## 参数调优

可以通过修改 `example.cpp` 中的配置参数来调整算法行为：

- 增大 `alphaShapeRemovalSquaredSize` 值（默认 625）到 900-1000，可以减少过度分割
- 增大 `topoGraphMarkAsFeatureEdgeLength` 值（默认 16）到 20-24，可以减少特征边的生成

## osmAG格式详解

osmAG（OpenStreetMap Area Graph）是本项目的最重要输出结果，它将区域图转换为标准的OSM XML格式，便于与其他导航和地图工具集成。

### 核心特点

1. **标准化表示**：采用OSM XML格式，与现有地图工具兼容
2. **拓扑信息**：包含房间之间的连接关系，便于路径规划
3. **几何信息**：保留房间的几何形状，支持精确定位
4. **优化处理**：多边形简化和毛刺去除，提高可用性


### 应用场景

osmAG格式特别适用于以下场景：

1. **机器人导航**：提供高级别拓扑信息，便于机器人在室内环境中导航
2. **路径规划**：支持基于区域的路径规划，比格点地图更高效
3. **室内定位**：结合其他定位技术，提供语义化定位信息
4. **人机交互**：便于机器人理解“去大厅”“进入会议室”等指令

## 许可证

请参阅项目根目录下的 LICENSE 文件。

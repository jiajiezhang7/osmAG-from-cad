# Area Graph

## 概述

Area Graph 是一种用于生成室内环境拓扑地图的方法，通过 Voronoi 图将环境分割成不同的区域（如房间、走廊等），并表示它们之间的连接关系。这种表示方法对于机器人导航、路径规划和空间理解具有重要意义，能够帮助机器人更好地理解和交互于复杂的室内环境。

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
1. 彩色区域图：显示不同区域用不同颜色标记
2. 轮廓图：显示区域边界的黑白图像

## 代码结构

主要组件包括：

- **VoriGraph**：Voronoi 图的数据结构和处理函数
- **TopoGraph**：拓扑图的数据结构和处理函数
- **RoomDect**：房间检测算法
- **AreaGraph**：区域图生成和优化

## 参数调优

可以通过修改 `example.cpp` 中的配置参数来调整算法行为：

- 增大 `alphaShapeRemovalSquaredSize` 值（默认 625）到 900-1000，可以减少过度分割
- 增大 `topoGraphMarkAsFeatureEdgeLength` 值（默认 16）到 20-24，可以减少特征边的生成

## 许可证

请参阅项目根目录下的 LICENSE 文件。

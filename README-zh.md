# AGSeg 工程说明

本工程实现了从CAD图纸（DWG格式）到Enhanced OpenStreetMap（OSM） - OSMAG Map的自动化转换流程。

## 整体流程

```
DWG -> DXF -> Filtered DXF -> SVG -> PNG -> Area Graph Segment -> osmAG.osm
```

## 快速开始

### 环境准备
```bash
# 安装Python依赖
pip install ezdxf svgwrite svgpathtools cairosvg pillow numpy opencv-python pyproj

# 安装系统依赖（Ubuntu）
sudo apt-get install g++ cmake qtbase5-dev libcgal-dev
```

### 基本使用流程

1. **CAD预处理**（详见 [cad2osm/README.md](cad2osm/README.md)）
   ```bash
   cd cad2osm/script
   python3 dwg2dxf_oda.py -i input.dwg -o output.dxf
   python dxf_filter.py  # 过滤DXF文件
   python dxf2svg.py <filtered_dxf> <output_svg>
   python svg2png.py <input_svg> <output_png>
   ```

2. **区域图分割**（详见 [area_graph_segment/README.md](area_graph_segment/README.md)）
   ```bash
   cd area_graph_segment/build
   ./bin/example_segmentation <input_png> 0.05 -1 -1 1.5
   ```

3. **文本提取与房间命名**（详见 [cad2osm/script/text_extract_module/README.md](cad2osm/script/text_extract_module/README.md)）
   ```bash
   cd cad2osm/script/text_extract_module
   python text_extractor.py --mode full \
       --dxf <dxf_file> \
       --bounds <bounds_json> \
       --osm <osmAG.osm> \
       --output <output_osm> \
       --visualize
   ```

## 主要组件

| 组件 | 功能 | 统一入口脚本 | 详细文档 |
|------|------|-------------|----------|
| **cad2osm** | CAD文件预处理和转换 | `cad2osm/script/` 下的各个脚本 | [cad2osm/README.md](cad2osm/README.md) |
| **area_graph_segment** | 区域图分割和osmAG生成 | `./bin/example_segmentation` | [area_graph_segment/README.md](area_graph_segment/README.md) |
| **文本提取模块** | DXF文本提取和房间命名 | `text_extract_module/text_extractor.py` | [cad2osm/script/text_extract_module/README.md](cad2osm/script/text_extract_module/README.md) |
| **GUI工具** | 图形界面操作工具 | `cad2osm/gui/start_gui.py` | [cad2osm/gui/README.md](cad2osm/gui/README.md) |

## 核心输出

**osmAG.osm** 是本工程最重要的输出结果，包含：
- 房间几何形状和拓扑关系
- 语义信息（房间名称、类型等）
- 标准OSM XML格式，便于导航和路径规划

## 目录结构
```
AGSeg/
├── cad2osm/                    # CAD预处理工具
│   ├── script/                 # 转换脚本
│   │   └── text_extract_module/ # 文本提取模块
│   ├── gui/                    # 图形界面
│   └── config/                 # 配置文件
├── area_graph_segment/         # 区域图分割
│   ├── src/                    # 源代码
│   ├── config/                 # 配置文件
│   └── dataset/                # 测试数据
└── osmAG_doc/                  # osmAG标准文档
```

## 注意事项

1. **文件格式**：确保DWG/DXF文件使用正确的图层命名规范
2. **中间文件**：建议保留每个步骤的中间文件，便于问题定位
3. **参数调优**：根据具体建筑图纸调整分辨率、门宽、走廊宽度等参数
4. **坐标系统**：注意配置正确的地理坐标参考点

## 故障排除

常见问题检查清单：
- [ ] Python环境及依赖包是否正确安装
- [ ] 系统依赖（cmake, Qt, CGAL）是否正确安装
- [ ] 输入文件格式和路径是否正确
- [ ] 图层命名是否符合规范
- [ ] 配置文件参数是否合理

如需更多帮助，请参考各子目录下的详细文档。

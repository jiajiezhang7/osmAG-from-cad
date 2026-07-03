# CAD2OSM 代码库

本代码库将 CAD 建筑平面图转换为 **osmAG** 地图：以标准 OSM XML 表达室内房间几何、通道拓扑关系，并可选加入文本语义房间名。

## 引用

```bibtex
@misc{zhang2025generationindooropenstreet,
      title={Generation of Indoor Open Street Maps for Robot Navigation from CAD Files}, 
      author={Jiajie Zhang and Shenrui Wu and Xu Ma and Sören Schwertfeger},
      year={2025},
      eprint={2507.00552},
      archivePrefix={arXiv},
      primaryClass={cs.RO},
      url={https://arxiv.org/abs/2507.00552}, 
}
```

论文链接：[Generation of Indoor Open Street Maps for Robot Navigation from CAD Files](https://arxiv.org/abs/2507.00552)

## 快速复现

推荐复现入口从已追踪的 DXF 子集开始，路径为 `cad2osm/data/web-cad/dxf/original`，这样可以避开 DWG 到 DXF 所需的 ODA 外部依赖。

```bash
# 构建 AreaGraph 可执行文件
cmake -S area_graph_segment -B area_graph_segment/build
cmake --build area_graph_segment/build --target area_graph_segmentation -j

# 预览一个 web-cad case，不实际运行
python3 run_pipeline.py --config config/repro_web_cad.yaml --case office --dry-run

# 单 case 端到端复现：DXF -> SVG/bounds -> PNG -> osmAG
python3 run_pipeline.py --config config/repro_web_cad.yaml --case office
```

输出位于 `runs/web-cad/<case>/`：

| 输出 | 说明 |
|------|------|
| `effective_config.yaml` | 本次运行真正生效的完整参数 |
| `run_manifest.json` | 输入、输出、命令和运行元数据 |
| `preprocess/*.svg`, `*.bounds.json`, `*.png` | CAD 预处理结果 |
| `area_graph/*_osmAG.osm` | 核心 osmAG 输出 |
| `area_graph/*_roomGraph.png` | 分割可视化结果 |

文本语义模块默认关闭，可按需开启：

```bash
python3 run_pipeline.py --config config/repro_web_cad.yaml --case office --with-text
```

## Pipeline 阶段

```
DXF -> SVG + bounds.json -> PNG -> AreaGraph segmentation -> osmAG.osm -> optional text naming
```

DWG 转换仍由 `cad2osm/script/core_process/dwg2dxf_oda.py` 支持，但需要 ODA File Converter，因此不放入默认复现路径。

## 参数地图

配置优先级为：

```
内置默认值 < YAML global < case profile < case overrides < CLI overrides
```

关键参数集中在 `config/repro_web_cad.yaml`，每次运行都会写入 `effective_config.yaml`。

| 参数 | 单位 | 影响阶段 | CLI 覆盖 |
|------|------|----------|----------|
| `map_preprocessing.resolution` | m/pixel | PNG 尺度、AreaGraph 阈值、OSM 导出、面积统计 | `--resolution` |
| `map_preprocessing.door_width/corridor_width` | m | 动态 alpha 计算 | `--set map_preprocessing.door_width=...` |
| `root_node.latitude/longitude/pixel_x/pixel_y` | deg / px | OSM 坐标转换 | `--root-lat`, `--root-lon`, `--root-pixel-x`, `--root-pixel-y` |
| `polygon_processing.simplify.tolerance` | px | OSM 多边形简化 | `--set polygon_processing.simplify.tolerance=...` |
| `polygon_processing.small_room_filter.min_area` | m2 | 小房间过滤 | `--min-room-area` |
| `area_graph.alpha.*` | px / mode | 房间分割粒度 | `--set area_graph.alpha.fixed_value=...` |
| `area_graph.vori_config.*` | px 或字段名中的 m | Voronoi/拓扑清理 | `--set area_graph.vori_config.<key>=...` |

`area_graph_segment/config/params.yaml` 仍是直接运行 `area_graph_segmentation` 时的默认配置。统一入口会生成 effective config 并通过 `--config` 传给 C++ 程序。


## 主要组件

| 组件 | 功能 | 入口 |
|------|------|------|
| `run_pipeline.py` | 可复现的 DXF 到 osmAG 统一编排 | `python3 run_pipeline.py --case office` |
| `cad2osm/script/core_process` | CAD 预处理工具 | 由 `run_pipeline.py` 调用，也可单独使用 |
| `area_graph_segment` | AreaGraph 分割与 osmAG 导出 | `area_graph_segment/build/bin/area_graph_segmentation` |
| `cad2osm/script/text_extract_module` | 可选 DXF 文本提取与房间命名 | `text_extractor.py` |

## 依赖

```bash
pip install ezdxf svgwrite svgpathtools cairosvg pillow numpy opencv-python pyproj pyyaml
sudo apt-get install g++ cmake qtbase5-dev libcgal-dev
```

更多模块细节请见 `area_graph_segment/README.md`、`cad2osm/README-zh.md` 和 `cad2osm/script/text_extract_module/README.md`。

# CAD2OSM Project Guide

This repository converts CAD floor plans into **osmAG** maps: standard OSM XML with indoor room geometry, passage topology, and optional semantic room names.

## Citation

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

Paper: [Generation of Indoor Open Street Maps for Robot Navigation from CAD Files](https://arxiv.org/abs/2507.00552)

## Reproducible Quick Start

The recommended reproducibility entrypoint starts from the tracked DXF subset under `cad2osm/data/web-cad/dxf/original`, avoiding the external DWG/ODA dependency.

```bash
# Build the AreaGraph executable
cmake -S area_graph_segment -B area_graph_segment/build
cmake --build area_graph_segment/build --target area_graph_segmentation -j

# Preview one tracked web-cad case without running the pipeline
python3 run_pipeline.py --config config/repro_web_cad.yaml --case office --dry-run

# Run one case end to end: DXF -> SVG/bounds -> PNG -> osmAG
python3 run_pipeline.py --config config/repro_web_cad.yaml --case office
```

Outputs are written to `runs/web-cad/<case>/`:

| Output | Purpose |
|--------|---------|
| `effective_config.yaml` | The fully merged parameters actually used for this run |
| `run_manifest.json` | Input files, generated outputs, commands, and run metadata |
| `preprocess/*.svg`, `*.bounds.json`, `*.png` | CAD preprocessing artifacts |
| `area_graph/*_osmAG.osm` | Main osmAG result |
| `area_graph/*_roomGraph.png` | Visual segmentation result |

The optional text naming stage is disabled by default:

```bash
python3 run_pipeline.py --config config/repro_web_cad.yaml --case office --with-text
```

## Pipeline Stages

```
DXF -> SVG + bounds.json -> PNG -> AreaGraph segmentation -> osmAG.osm -> optional text naming
```

DWG conversion is still available through `cad2osm/script/core_process/dwg2dxf_oda.py`, but it requires ODA File Converter and is not part of the default reproducibility path.

## Parameter Map

Configuration priority is:

```
built-in defaults < config global defaults < case profile < case overrides < CLI overrides
```

Key parameters live in `config/repro_web_cad.yaml` and are copied into each run's `effective_config.yaml`.

| Parameter | Unit | Used By | CLI Override |
|-----------|------|---------|--------------|
| `map_preprocessing.resolution` | m/pixel | PNG scale, AreaGraph thresholds, OSM export, area statistics | `--resolution` |
| `map_preprocessing.door_width` / `corridor_width` | m | Dynamic alpha calculation | `--set map_preprocessing.door_width=...` |
| `root_node.latitude/longitude/pixel_x/pixel_y` | deg / px | OSM coordinate conversion | `--root-lat`, `--root-lon`, `--root-pixel-x`, `--root-pixel-y` |
| `polygon_processing.simplify.tolerance` | px | OSM polygon simplification | `--set polygon_processing.simplify.tolerance=...` |
| `polygon_processing.small_room_filter.min_area` | m² | Room filtering | `--min-room-area` |
| `area_graph.alpha.*` | px / mode | Room split granularity | `--set area_graph.alpha.fixed_value=...` |
| `area_graph.vori_config.*` | px or m as named | Voronoi/topology cleanup | `--set area_graph.vori_config.<key>=...` |

`area_graph_segment/config/params.yaml` remains the direct executable default. The unified runner writes an effective config and passes it to `area_graph_segmentation --config`.

## Main Components

| Module | Purpose | Entry |
|--------|---------|-------|
| `run_pipeline.py` | Reproducible DXF-to-osmAG orchestration | `python3 run_pipeline.py --case office` |
| `cad2osm/script/core_process` | CAD preprocessing utilities | imported by `run_pipeline.py` or used directly |
| `area_graph_segment` | AreaGraph segmentation and osmAG export | `area_graph_segment/build/bin/area_graph_segmentation` |
| `cad2osm/script/text_extract_module` | Optional DXF text extraction and room naming | `text_extractor.py` |

## Dependencies

```bash
pip install ezdxf svgwrite svgpathtools cairosvg pillow numpy opencv-python pyproj pyyaml
sudo apt-get install g++ cmake qtbase5-dev libcgal-dev
```

For deeper module-level details, see `area_graph_segment/README.md`, `cad2osm/README-zh.md`, and `cad2osm/script/text_extract_module/README.md`.

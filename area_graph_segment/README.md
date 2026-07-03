# Area Graph - Indoor Space Segmentation

## Overview

Area Graph segments indoor environments into different regions (rooms, corridors, etc.) using Voronoi diagrams, generating topological maps for robot navigation and path planning.

**Core Output**: **osmAG.osm** - Standard OSM XML format file containing room geometries, topological relationships, and semantic information

## Unified Entry Script

```bash
# Compiled executable
./bin/area_graph_segmentation <input_png> [options]
```

## Academic Background

Based on the paper: Hou, J., Yuan, Y., and Schwertfeger, S., "Area Graph: Generation of Topological Maps using the Voronoi Diagram", ICAR 2019.

📄 [Paper Link](https://arxiv.org/abs/1910.01019)

## Algorithm Pipeline

1. **Preprocessing** → **Voronoi Generation** → **Topological Graph** → **Room Detection** → **Region Merging** → **osmAG Export**

Core Steps:
- Use Alpha Shape algorithm for furniture removal and room detection
- Generate topological structure based on Voronoi diagram
- Polygon optimization, removing spikes and sharp corners
- Export to standard OSM XML format

## Quick Start

### System Dependencies

**Ubuntu Installation**:
```bash
sudo apt-get install g++ cmake qtbase5-dev libcgal-dev
```

### Build and Run

```bash
cd area_graph_segment/
mkdir build && cd build
cmake ..
make area_graph_segmentation

# Run
./bin/area_graph_segmentation <input_png> \
    --config ../config/params.yaml \
    --output-dir ./run_output \
    --dump-effective-config
```

## Parameter Description

| Parameter | Description | Recommended Source |
|-----------|-------------|--------------------|
| `input_png` | Input PNG map file (white background, black obstacles) | positional |
| `--config` | YAML file containing the effective segmentation/export parameters | `config/params.yaml` or `run_pipeline.py` output |
| `--output-dir` | Directory for `clean.png`, `afterAlphaRemoval.png`, room graph, and osmAG | per-run output directory |
| `--dump-effective-config` | Writes the final config consumed by downstream exporters | enabled for reproducibility |
| `--resolution` | Map resolution in meters/pixel | CLI override for config |
| `--root-lat/lon/pixel-x/pixel-y` | Geographic root node and its PNG pixel anchor | CLI override for config |
| `--min-room-area` | Small-room filter threshold in square meters | CLI override for config |

**Usage Examples**:
```bash
# Config-driven run
./bin/area_graph_segmentation input.png \
    --config ../config/params.yaml \
    --output-dir ./run_output \
    --dump-effective-config

# Legacy positional format is still supported
./bin/area_graph_segmentation input.png 0.05 -1 -1 1.5
```

## Advanced Configuration

Adjustable through `config/params.yaml`:

**Map Preprocessing**:
- `resolution`: meters per pixel
- `door_width`, `corridor_width`: physical scale used for dynamic alpha
- `clean_input`, `remove_furniture`: optional preprocessing switches

**Polygon Processing**:
- `simplify_tolerance`: Simplification tolerance (default: 0.05)
- `spike_angle_threshold`: Spike angle threshold (default: 60.0°)

**Small Room Merging**:
- `min_area`: Minimum room area (default: 4.0 m²)
- `max_merge_distance`: Maximum merge distance (default: 1.5 m)

**Coordinate System**:
- `root_node`: Geographic coordinate reference point settings
- `level`: Floor information for OSM tags (default: "1")
- `height_per_level`: Height per floor (meters) for calculating room and passage heights (default: 3.2)

**AreaGraph Core**:
- `area_graph.alpha`: dynamic/fixed alpha strategy and outside-removal alpha
- `area_graph.vori_config`: Voronoi and topology cleanup thresholds
- `area_graph.furniture_removal.max_polygon_length`: furniture-removal polygon length threshold

## Output Results

| File | Description | Purpose |
|------|-------------|---------|
| **osmAG.osm** | 🎯 **Core Output** - Topological map in OSM format | Robot navigation, path planning |
| Colored region map | Color-coded image of different regions | Visualization verification |
| Contour map | Black and white image of region boundaries | Debug analysis |

### osmAG Format Features

**osmAG** (OpenStreetMap Area Graph) is in standard OSM XML format, containing:
- 🏠 **Room Geometry**: Polygon outlines and area information
- 🔗 **Topological Relations**: Connectivity between rooms
- 🏷️ **Semantic Tags**: Room types, names, and other attributes
- 📍 **Floor Information**: All rooms and passages include `level` tags
- 🎯 **Navigation-Friendly**: Direct support for OSM ecosystem

## Code Architecture

| Module | Function |
|--------|----------|
| **VoriGraph** | Voronoi diagram data structure and processing |
| **TopoGraph** | Topological graph generation and optimization |
| **RoomDect** | Room detection algorithm |
| **AreaGraph** | Region graph generation and merging |
| **osmAGExport** | OSM format export and polygon optimization |

## Parameter Tuning Recommendations

**Reduce Over-segmentation**:
- Increase `alphaShapeRemovalSquaredSize`: 625 → 900-1000
- Increase `topoGraphMarkAsFeatureEdgeLength`: 16 → 20-24

**Configuration File Adjustment**: Modify polygon processing and room merging parameters in `config/params.yaml`

## Application Scenarios

- 🤖 **Robot Navigation**: High-level topological information supporting semantic navigation
- 🗺️ **Path Planning**: Efficient region-based path planning
- 📍 **Indoor Localization**: Semantic localization and spatial understanding
- 💬 **Human-Robot Interaction**: Understanding natural language instructions like "go to the meeting room"

> 📝 **Next Step**: Use the text extraction module to add names to rooms, see [cad2osm/script/text_extract_module/README.md](../cad2osm/script/text_extract_module/README.md)

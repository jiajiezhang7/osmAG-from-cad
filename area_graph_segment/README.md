# Area Graph - Indoor Space Segmentation

## Overview

Area Graph segments indoor environments into different regions (rooms, corridors, etc.) using Voronoi diagrams, generating topological maps for robot navigation and path planning.

**Core Output**: **osmAG.osm** - Standard OSM XML format file containing room geometries, topological relationships, and semantic information

## Unified Entry Script

```bash
# Compiled executable
./bin/example_segmentation <input_png> <resolution> <door_width> <corridor_width> <noise_percentage>
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
make example_segmentation

# Run
./bin/example_segmentation <input_png> <resolution> <door_width> <corridor_width> <noise_percentage>
```

## Parameter Description

| Parameter | Description | Recommended Value |
|-----------|-------------|-------------------|
| `input_png` | Input PNG map file (white background, black obstacles) | - |
| `resolution` | Map resolution (meters/pixel) | `0.05` |
| `door_width` | Width of the widest door (-1 for automatic) | `-1` or `0.85` |
| `corridor_width` | Width of the narrowest corridor (-1 for automatic) | `-1` or `2.7` |
| `noise_percentage` | Noise percentage estimation | `1.5` |

**Usage Examples**:
```bash
# Automatic parameters (recommended)
./bin/example_segmentation input.png 0.05 -1 -1 1.5

# Manual door and corridor width specification
./bin/example_segmentation input.png 0.05 0.85 2.7 1.5
```

## Advanced Configuration

Adjustable through `config/params.yaml`:

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

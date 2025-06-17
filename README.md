# AGSeg Project Guide

This project provides an automated workflow to convert CAD drawings (DWG format) into **Enhanced OpenStreetMap (OSM)** — referred to as **OSMAG Map** in this repository.

## End-to-End Pipeline

```
DWG -> DXF -> Filtered DXF -> SVG -> PNG -> Area Graph Segment -> osmAG.osm
```

## Quick Start

### Environment Setup
```bash
# Install Python dependencies
pip install ezdxf svgwrite svgpathtools cairosvg pillow numpy opencv-python pyproj

# Install system dependencies (Ubuntu)
sudo apt-get install g++ cmake qtbase5-dev libcgal-dev
```

### Basic Workflow

1. **CAD Pre-processing** (see [cad2osm/README.md](cad2osm/README.md))
   ```bash
   cd cad2osm/script
   python3 dwg2dxf_oda.py -i input.dwg -o output.dxf
   python dxf_filter.py          # filter DXF file
   python dxf2svg.py <filtered_dxf> <output_svg>
   python svg2png.py <input_svg> <output_png>
   ```

2. **Area Graph Segmentation** (see [area_graph_segment/README.md](area_graph_segment/README.md))
   ```bash
   cd area_graph_segment/build
   ./bin/example_segmentation <input_png> 0.05 -1 -1 1.5
   ```

3. **Text Extraction & Room Naming** (see [cad2osm/script/text_extract_module/README.md](cad2osm/script/text_extract_module/README.md))
   ```bash
   cd cad2osm/script/text_extract_module
   python text_extractor.py --mode full \
       --dxf <dxf_file> \
       --bounds <bounds_json> \
       --osm <osmAG.osm> \
       --output <output_osm> \
       --visualize
   ```

## Main Components

| Module | Purpose | Entry Script | Documentation |
|--------|---------|-------------|---------------|
| **cad2osm** | CAD file pre-processing & conversion | scripts in `cad2osm/script/` | [cad2osm/README.md](cad2osm/README.md) |
| **area_graph_segment** | Area-graph segmentation & osmAG generation | `./bin/example_segmentation` | [area_graph_segment/README.md](area_graph_segment/README.md) |
| **Text Extraction Module** | DXF text extraction & room naming | `text_extract_module/text_extractor.py` | [cad2osm/script/text_extract_module/README.md](cad2osm/script/text_extract_module/README.md) |
| **GUI Tool** | Graphical user interface | `cad2osm/gui/start_gui.py` | [cad2osm/gui/README.md](cad2osm/gui/README.md) |

## Core Output

The most important output of this project is **`osmAG.osm`**, which contains:

- Room geometries and topological relationships
- Semantic information (room names, types, etc.)
- Standard OSM XML format, ready for navigation and path-planning tasks

## Directory Layout
```
AGSeg/
├── cad2osm/                    # CAD pre-processing utilities
│   ├── script/                 # Conversion scripts
│   │   └── text_extract_module/ # Text extraction sub-module
│   ├── gui/                    # Graphical interface
│   └── config/                 # Configuration files
├── area_graph_segment/         # Area-graph segmentation
│   ├── src/                    # Source code
│   ├── config/                 # Configuration files
│   └── dataset/                # Test datasets
└── osmAG_doc/                  # osmAG specification documents
```

## Notes

1. **File format**: Ensure DWG/DXF files follow the correct layer-naming conventions.
2. **Intermediate files**: Keep intermediate artifacts from each step to aid debugging.
3. **Parameter tuning**: Adjust resolution, door width, corridor width, etc., to match specific architectural drawings.
4. **Coordinate system**: Configure the proper geographic reference point.

## Troubleshooting Checklist

- [ ] Python environment and packages installed correctly
- [ ] System dependencies (cmake, Qt, CGAL) installed correctly
- [ ] Input file formats and paths are correct
- [ ] Layer naming conforms to conventions
- [ ] Configuration parameters are reasonable

For additional help, please refer to the detailed documentation in each sub-directory.

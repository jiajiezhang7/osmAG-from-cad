# CAD to OSM Conversion Toolset

This toolset handles CAD file preprocessing, converting DWG format to PNG images to prepare for subsequent area graph segmentation.

## Conversion Pipeline

```
DWG -> DXF -> Filtered DXF -> SVG -> PNG
```

## Core Scripts Overview

| Script | Function | Input | Output |
|--------|----------|-------|---------|
| `dwg2dxf_oda.py` | DWG to DXF conversion | .dwg | .dxf |
| `dxf_layer_info.py` | Layer information analysis | .dxf | Layer report |
| `dxf_filter.py` | DXF layer filtering | .dxf | Filtered .dxf |
| `dxf2svg.py` | DXF to SVG conversion | .dxf | .svg + .bounds.json |
| `svg2png.py` | SVG to PNG conversion | .svg | .png |

> 💡 **Unified Entry Script**: For text extraction functionality, use `text_extract_module/text_extractor.py`

## Detailed Script Documentation

### 1. DWG to DXF Conversion (dwg2dxf_oda.py)

**Function**: Converts DWG files to DXF format using ODA File Converter

**Basic Usage**:
```bash
# Convert single file
python3 dwg2dxf_oda.py -i input.dwg -o output.dxf

# Batch convert directory (recursive)
python3 dwg2dxf_oda.py -i input_dir -o output_dir -r
```

**Main Parameters**:
- `-i, --input`: Input file or directory
- `-o, --output`: Output file or directory
- `-r, --recursive`: Recursively process subdirectories
- `-d, --debug`: Enable debug logging

**Prerequisites**: ODA File Converter must be installed

### 2. DXF Layer Information Analysis (dxf_layer_info.py)

**Function**: Analyzes layer information in DXF files and generates layer reports

**Basic Usage**:
```bash
python3 dxf_layer_info.py <input_dxf_file>
```

**Output**: Layer information report file containing all layer names and Unicode decoding

### 3. DXF Layer Filtering (dxf_filter.py)

**Function**: Filters DXF file layers, preserving key layers such as walls

**Basic Usage**:
```bash
python3 dxf_filter.py  # Interactive file selection
```

**Output Files**:
- `<original_filename>_filtered_<timestamp>.dxf` - Filtered DXF file
- `<original_filename>_filtered_<timestamp>_report.txt` - Filtering report

**Filtering Rules**: Preserves layers containing keywords like "WALL"

### 4. DXF to SVG Conversion (dxf2svg.py)

**Function**: Converts DXF files to SVG format, preserving precise graphic details

**Basic Usage**:
```bash
python3 dxf2svg.py <input_dxf_file> <output_svg_file>
```

**Important Outputs**:
- `.svg` file - Vector graphics
- `.bounds.json` file - **Coordinate transformation boundary information** (required for text extraction module)

### 5. SVG to PNG Conversion (svg2png.py)

**Function**: Converts SVG files to high-quality PNG images

**Basic Usage**:
```bash
python3 svg2png.py <input_svg_file> <output_png_file>
```

**Output Characteristics**: Pure white background with black lines representing walls, suitable for area graph segmentation

## Environment Dependencies

**Python Package Dependencies**:
```bash
pip install ezdxf svgwrite svgpathtools cairosvg pillow numpy opencv-python
```

**System Dependencies**:
- ODA File Converter (for DWG to DXF conversion)

## Usage Workflow Example

```bash
# 1. Convert DWG to DXF
python3 dwg2dxf_oda.py -i building.dwg -o building.dxf

# 2. Analyze layers (optional)
python3 dxf_layer_info.py building.dxf

# 3. Filter layers
python3 dxf_filter.py  # Select building.dxf

# 4. Convert DXF to SVG (generates .bounds.json)
python3 dxf2svg.py building_filtered.dxf building.svg

# 5. Convert SVG to PNG
python3 svg2png.py building.svg building.png
```

> 📝 **Next Step**: Use the generated PNG file for area graph segmentation, see [area_graph_segment/README.md](../area_graph_segment/README.md)

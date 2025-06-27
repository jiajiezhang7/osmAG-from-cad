# Batch Processing Guide for PNG Floor Plans

This document provides a comprehensive guide for automated batch processing of PNG building floor plan files using the area graph segmentation system.

## Overview

### Command Line Parameter Support

The `area_graph_segmentation` executable now supports command-line arguments to override configurations in `params.yaml`:

```bash
./bin/area_graph_segmentation image.png [options]

Options:
  --resolution <value>        Map resolution (meters/pixel)
  --door-width <value>        Door width in meters
  --corridor-width <value>    Corridor width in meters
  --noise-percent <value>     Noise percentage (0-100)
  --png-width <value>         PNG image width
  --png-height <value>        PNG image height
  --root-lat <value>          Root node latitude
  --root-lon <value>          Root node longitude
  --root-pixel-x <value>      Root node pixel X position
  --root-pixel-y <value>      Root node pixel Y position
  --simplify-tolerance <value> Polygon simplification tolerance
  --spike-angle <value>       Spike removal angle threshold
  --spike-distance <value>    Spike removal distance threshold
  --min-room-area <value>     Minimum room area filter
  --clean-input <0|1>         Enable input cleaning
  --remove-furniture <0|1>    Enable furniture removal
  --record-time               Enable time recording
```

### Batch Processing Script Features

The `batch_process_png.py` script provides the following capabilities:

1. **Automatic Building Type Recognition**: Identifies building types based on filename patterns
2. **Intelligent Parameter Configuration**: Applies optimal parameters for different building types
3. **Image Size Adaptation**: Automatically adjusts resolution based on image dimensions
4. **Batch Processing**: Processes entire directories of PNG files at once
5. **Progress Monitoring**: Displays processing progress and result statistics
6. **Multi-Alpha Testing**: Advanced feature for parameter optimization

## Basic Usage

### 1. Standard Batch Processing

```bash
# Navigate to the area_graph_segment directory
cd area_graph_segment

# Process all PNG files in a specified directory
python3 batch_process_png.py /path/to/png/directory

# Example: Process PNG files from cad2osm
python3 batch_process_png.py ../cad2osm/data/web-cad/img/png_manual_filter
```

### 2. Preview Mode

Use dry-run mode to preview commands before execution:

```bash
python3 batch_process_png.py ../cad2osm/data/web-cad/img/png_manual_filter --dry-run
```

### 3. File Filtering

```bash
# Process only files containing "apartment"
python3 batch_process_png.py ../cad2osm/data/web-cad/img/png_manual_filter --filter apartment

# Skip files containing "hotel"
python3 batch_process_png.py ../cad2osm/data/web-cad/img/png_manual_filter --skip hotel
```

### 4. Custom Executable Path

```bash
python3 batch_process_png.py ../cad2osm/data/web-cad/img/png_manual_filter --executable ./bin/area_graph_segmentation
```

## Advanced Features: Multi-Alpha Testing

### What is Alpha Value Testing?

Multi-alpha testing is designed to solve segmentation quality issues when dealing with CAD images of unknown resolution downloaded from the web. By testing different alpha values, you can find the optimal parameter combination for specific images.

### Alpha Value Effects

In area_graph_segmentation, alpha values control the granularity of Voronoi diagram subdivision:
- **Smaller alpha values**: Produce coarser segmentation, suitable for buildings with larger rooms
- **Larger alpha values**: Produce finer segmentation, suitable for buildings with smaller rooms or complex structures

### Multi-Alpha Usage

#### 1. Basic Multi-Alpha Testing

```bash
# Test specific alpha values
python3 batch_process_png.py ./input_images --alpha-values "100,200,500,1000"

# Test alpha value range (automatically generates arithmetic sequence)
python3 batch_process_png.py ./input_images --alpha-values "100-1000"
```

#### 2. Using Preset Alpha Ranges

```bash
# Small range test (suitable for quick validation)
python3 batch_process_png.py ./input_images --alpha-preset small

# Medium range test (balanced choice)
python3 batch_process_png.py ./input_images --alpha-preset medium

# Large range test (suitable for large buildings)
python3 batch_process_png.py ./input_images --alpha-preset large

# Comprehensive test (includes all common values)
python3 batch_process_png.py ./input_images --alpha-preset comprehensive
```

#### 3. Preview Multi-Alpha Commands

```bash
# View commands to be executed without actually running them
python3 batch_process_png.py ./input_images --alpha-values "100,500,1000" --dry-run
```

#### 4. Combined with Other Parameters

```bash
# Process only files with specific keywords
python3 batch_process_png.py ./input_images --alpha-values "100,500,1000" --filter "apartment"

# Specify output directory
python3 batch_process_png.py ./input_images --alpha-values "100,500,1000" --output-dir ./multi_alpha_results
```

### Preset Alpha Value Ranges

| Preset Name | Alpha Values | Use Case |
|-------------|--------------|----------|
| small | [50, 100, 200, 500] | Quick testing, small buildings |
| medium | [100, 200, 500, 1000, 2000] | General purpose, balanced testing |
| large | [500, 1000, 2000, 5000] | Large buildings, complex structures |
| comprehensive | [50, 100, 200, 500, 1000, 2000, 5000, 10000] | Comprehensive testing |

### Multi-Alpha Output Structure

Multi-alpha testing creates the following directory structure:

```
output/
├── image1/
│   ├── alpha_100/
│   │   ├── image1.png
│   │   ├── image1_output/
│   │   ├── clean.png
│   │   ├── afterAlphaRemoval.png
│   │   └── ...
│   ├── alpha_200/
│   │   ├── image1.png
│   │   ├── image1_output/
│   │   └── ...
│   └── alpha_500/
│       └── ...
└── image2/
    ├── alpha_100/
    └── ...
```

## Building Type Configuration

The script automatically identifies building types based on filename patterns and applies appropriate parameter configurations:

### Supported Building Types

| Building Type | Keywords | Characteristics |
|---------------|----------|-----------------|
| apartment | apartment, residential | Residential apartments, narrow doors, smaller rooms |
| office | office, ufficio, schema-ufficio | Office buildings, moderate corridors, regular rooms |
| hotel | hotel | Hotels, wider corridors, standardized rooms |
| school | school, scuola, aule, universita | Schools, large corridors, large rooms |
| gym | gym, gymnasium | Gymnasiums, extra large spaces |
| museum | museum, centro, cultural | Museums/cultural centers, exhibition spaces |
| monastery | monastery | Monasteries, traditional architectural style |
| default | others | Default configuration |

### Parameter Configuration Examples

Here are typical parameter configurations for different building types:

```python
"apartment": {
    "resolution": 0.04,        # Resolution
    "door_width": 0.9,         # 0.9m door width
    "corridor_width": 1.2,     # 1.2m corridor width
    "min_room_area": 8.0       # 8 sqm minimum room area
}

"office": {
    "resolution": 0.035,
    "door_width": 1.0,         # 1.0m door width
    "corridor_width": 1.5,     # 1.5m corridor width
    "min_room_area": 12.0      # 12 sqm minimum room area
}

"hotel": {
    "resolution": 0.04,
    "door_width": 0.9,
    "corridor_width": 1.8,     # Wider hotel corridors
    "min_room_area": 6.0       # Hotel rooms can be smaller
}
```

## Alpha Value Calculation

The script automatically calculates corresponding door_width and corridor_width based on the following formula:

```
alpha_value = ceil(a^2 * 0.25 / resolution^2)
```

Where `a = min(door_width, corridor_width) + 0.1`

Reverse formula:
```
a = sqrt(alpha_value * 4 * resolution^2)
door_width = a - 0.1
corridor_width = a + 0.5
```

## File Output

Each processed PNG file generates:

1. `{filename}_output/` directory containing all intermediate and final results
2. `{filename}_roomGraph.png` - Room segmentation result image
3. `{filename}_osmAG.osm` - OSM format result file

## Processing Workflow

1. **File Identification**: Scan PNG files in the directory
2. **Type Recognition**: Identify building type based on filename
3. **Parameter Configuration**: Load parameter configuration for the building type
4. **Size Analysis**: Get image dimensions and adjust resolution parameters
5. **Command Construction**: Build complete command-line arguments
6. **Execute Processing**: Call area_graph_segmentation for processing
7. **Result Statistics**: Output success/failure processing statistics

## Usage Recommendations

### For Basic Processing
1. **First-time users**: Start with default building type recognition
2. **Known building types**: Use appropriate filters for consistent results
3. **Custom parameters**: Override specific parameters when needed

### For Multi-Alpha Testing
1. **Initial testing**: Use `--alpha-preset medium` for initial assessment
2. **Refinement**: Select narrower alpha value ranges based on initial results
3. **Batch processing**: Use the determined optimal alpha value for all similar images
4. **Result comparison**: Review output images from different alpha values and select the best segmentation

## Example Workflows

### Basic Workflow
```bash
# 1. Preview processing commands
python3 batch_process_png.py ./cad_images --dry-run

# 2. Process apartment buildings
python3 batch_process_png.py ./cad_images --filter apartment

# 3. Process with custom parameters
python3 batch_process_png.py ./cad_images --door-width 1.2 --corridor-width 1.8
```

### Multi-Alpha Workflow
```bash
# 1. Quick preview test
python3 batch_process_png.py ./cad_images --alpha-preset small --dry-run

# 2. Execute medium range test
python3 batch_process_png.py ./cad_images --alpha-preset medium

# 3. Refine based on results
python3 batch_process_png.py ./cad_images --alpha-values "800,1000,1200"

# 4. Process all images with optimal parameters
python3 batch_process_png.py ./all_cad_images --door-width 1.5 --corridor-width 2.0
```

## Troubleshooting

### Common Issues

1. **Python dependency issues**:
```bash
pip install Pillow  # Install PIL library for image processing
```

2. **Executable path issues**:
```bash
# Ensure area_graph_segmentation is compiled
cd area_graph_segment
make

# Or specify full path
python3 batch_process_png.py /path/to/png --executable /full/path/to/bin/area_graph_segmentation
```

3. **Permission issues**:
```bash
chmod +x batch_process_png.py
chmod +x bin/area_graph_segmentation
```

### Debugging Suggestions

1. Use `--dry-run` mode to preview commands first
2. Start testing with a single file
3. Check log files in output directories
4. Ensure PNG files are in correct format
5. Monitor disk space when using multi-alpha testing

## Performance Considerations

- Multi-alpha testing significantly increases processing time
- Recommend testing with a small subset of images first to find suitable alpha ranges
- Each alpha value creates complete output - monitor disk space usage
- Use preview mode (`--dry-run`) to review parameter settings without execution
- Consider running large batches in background for extended processing

## Configuration Extension

To add new building types or adjust parameters, modify the `BUILDING_CONFIGS` dictionary in `batch_process_png.py`.

## Notes

- Multi-alpha testing creates significantly more output files
- Use filtering options to process images in manageable batches
- The script automatically handles image size variations and parameter scaling
- Results should be evaluated visually to determine optimal segmentation quality 
# CAD2OSM Graphical User Interface Application

## Introduction

This is a graphical interface tool for CAD to OSM conversion, featuring the following functionalities:

1. **CAD Preprocessing**: DWG to PNG conversion
   - Complete workflow: DWG → DXF → Filtered DXF → SVG → PNG
   - Semi-automatic workflow: Pre-filtered DXF → SVG → PNG

2. **Text Extraction**: Extract text from DXF and add to OSM
   - Extract text from DXF files
   - Convert text coordinates to pixel coordinates
   - Extract room polygons from OSM files
   - Match text to rooms
   - Update OSM files

3. **OSM Merging**: Merge multiple OSM files
   - Support matching through elevator and stair areas
   - Automatically calculate and apply offsets
   - Update IDs to avoid conflicts

4. **Direction Correction**: Correct polygon orientations in OSM
   - Room polygons should be counter-clockwise
   - Structure polygons should be clockwise

## Installation

### Dependencies

```bash
pip install -r requirements.txt
```

### Running

```bash
python start_gui.py
```

## Usage Instructions

### Project Management

The application uses a project management system to organize files. Each project has a standard directory structure:

```
project_root/
├── data/
│   ├── [project_name]/
│   │   ├── dwg/                    # Original DWG files
│   │   ├── dxf/
│   │   │   ├── original/           # Original DXF files
│   │   │   ├── auto_filter/        # Auto-filtered DXF
│   │   │   └── manual_filter/      # Manually filtered DXF
│   │   ├── img/
│   │   │   ├── svg_auto_filter/    # SVG generated from auto-filtered
│   │   │   ├── svg_manual_filter/  # SVG generated from manually filtered
│   │   │   ├── png_auto_filter/    # PNG generated from auto-filtered
│   │   │   └── png_manual_filter/  # PNG generated from manually filtered
│   │   ├── osm/
│   │   │   ├── original/           # Original OSM files
│   │   │   ├── texted/             # OSM with added text
│   │   │   ├── merged/             # Merged OSM
│   │   │   └── corrected/          # Direction-corrected OSM
│   │   └── bounds/                 # Boundary information JSON files
```

### CAD Preprocessing

1. Select project
2. Choose processing mode (complete workflow or semi-automatic workflow)
3. Select input files or directory
4. Set output directory
5. Adjust parameters (resolution, edge gap ratio, line thickness)
6. Click "Start Processing" button
7. View log output and progress

### Text Extraction

1. Select processing mode (complete workflow, text extraction only, or text matching only)
2. Set input files (DXF file, boundary file, OSM file)
3. Set output file path
4. Adjust parameters (text layer name, matching threshold, etc.)
5. Set text filter list
6. Click "Start Processing" button
7. View matching result visualization images

### OSM Merging

1. Select reference OSM file
2. Add target OSM files (multiple selection supported)
3. Set output file path
4. Adjust parameters (matching area type, offset calculation method, minimum matching area count)
5. Click "Start Merging" button
6. View merge result statistics

### Direction Correction

1. Select OSM file
2. Set output file path
3. Click "Start Correction" button
4. View correction result statistics

## Development Notes

### Project Structure

```
gui/
├── main.py                 # Application entry point
├── start_gui.py            # Startup script
├── ui/                     # User interface components
│   ├── main_window.py      # Main window
│   ├── process_tab.py      # CAD preprocessing tab
│   ├── text_tab.py         # Text extraction tab
│   ├── merge_tab.py        # OSM merging tab
│   └── direction_tab.py    # Direction correction tab
├── modules/                # Functional modules
│   ├── process_module.py   # CAD preprocessing module
│   ├── text_module.py      # Text extraction module
│   ├── merge_module.py     # Merging module
│   └── direction_module.py # Direction correction module
├── utils/                  # Utility classes
│   └── project_manager.py  # Project manager
└── config/                 # Configuration files
    └── app_config.yaml     # Application configuration
```

### Extension Development

To add new functionality, follow these steps:

1. Create a new functional module in the `modules/` directory
2. Create corresponding user interface components in the `ui/` directory
3. Add new tabs in `main_window.py`
4. Update `config/app_config.yaml` to add related configurations

## License

This project is licensed under the MIT License. See the LICENSE file for details.

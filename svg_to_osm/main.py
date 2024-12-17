import argparse
from pathlib import Path
from converter import SvgConverter
from settings import Settings

def main():
    parser = argparse.ArgumentParser(description='Convert SVG files to OSM XML')
    parser.add_argument('input', help='Input SVG file')
    parser.add_argument('output', help='Output OSM file')
    
    # 基本设置
    parser.add_argument('--scale-num', type=float, default=1.0,
                      help='Scale numerator (default: 1.0)')
    parser.add_argument('--scale-div', type=float, default=1.0,
                      help='Scale divisor (default: 1.0)')
    parser.add_argument('--curve-steps', type=int, default=4,
                      help='Number of steps for curve interpolation (default: 4)')
    
    # 投影设置
    parser.add_argument('--center-lat', type=float, default=0.0,
                      help='Center latitude (default: 0.0)')
    parser.add_argument('--center-lon', type=float, default=0.0,
                      help='Center longitude (default: 0.0)')
    parser.add_argument('--projection', default='EPSG:3857',
                      help='Projection code (default: EPSG:3857)')
    
    # SVG解析设置
    parser.add_argument('--no-groups', action='store_false', dest='parse_groups',
                      help='Disable parsing of SVG groups')
    parser.add_argument('--no-transforms', action='store_false', dest='parse_transforms',
                      help='Disable parsing of SVG transforms')
    parser.add_argument('--min-segment', type=float, default=0.1,
                      help='Minimum segment length in meters (default: 0.1)')
    
    args = parser.parse_args()
    
    settings = Settings()
    settings.set_scale_numerator(args.scale_num)
    settings.set_scale_divisor(args.scale_div)
    settings.set_curve_steps(args.curve_steps)
    settings.center_lat = args.center_lat
    settings.center_lon = args.center_lon
    settings.projection = args.projection
    settings.parse_groups = args.parse_groups
    settings.parse_transforms = args.parse_transforms
    settings.min_segment_length = args.min_segment
    
    converter = SvgConverter(settings)
    
    try:
        converter.convert_file(Path(args.input), Path(args.output))
        print(f"Successfully converted {args.input} to {args.output}")
    except Exception as e:
        print(f"Error during conversion: {str(e)}")
        return 1
        
    return 0

if __name__ == "__main__":
    exit(main()) 
import argparse
from pathlib import Path
from .converter import SvgConverter
from .settings import Settings

def process_single_file(input_path: Path, output_path: Path, settings: Settings) -> int:
    """处理单个SVG文件
    
    Args:
        input_path: 输入SVG文件路径
        output_path: 输出OSM文件路径
        settings: 转换设置
        
    Returns:
        int: 0表示成功，1表示失败
    """
    converter = SvgConverter(settings)
    try:
        converter.convert_file(input_path, output_path)
        print(f"Successfully converted {input_path} to {output_path}")
        return 0
    except Exception as e:
        print(f"Error converting {input_path}: {str(e)}")
        return 1

def process_directory(input_dir: Path, output_dir: Path, settings: Settings) -> int:
    """处理目录下的所有SVG文件
    
    Args:
        input_dir: 输入目录路径
        output_dir: 输出目录路径
        settings: 转换设置
        
    Returns:
        int: 0表示全部成功，1表示存在失败
    """
    # 确保输出目录存在
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 获取所有svg文件
    svg_files = list(input_dir.glob("*.svg"))
    if not svg_files:
        print(f"No SVG files found in {input_dir}")
        return 1
        
    print(f"Found {len(svg_files)} SVG files to process")
    
    # 处理每个文件
    error_count = 0
    for svg_file in svg_files:
        # 构造输出文件路径，保持相同的文件名但改变扩展名
        output_path = output_dir / f"{svg_file.stem}.osm"
        if process_single_file(svg_file, output_path, settings) != 0:
            error_count += 1
            
    # 输出处理结果统计
    total = len(svg_files)
    success = total - error_count
    print(f"\nProcessing complete:")
    print(f"Total files: {total}")
    print(f"Successful conversions: {success}")
    print(f"Failed conversions: {error_count}")
    
    return 1 if error_count > 0 else 0

def main():
    # 命令行参数配置指南:
    # input: 输入的SVG文件路径
    # output: 输出的OSM文件路径
    # --scale-num: 缩放比例分子,增大会放大地图尺寸
    # --scale-div: 缩放比例分母,减小会放大地图尺寸
    # --curve-steps: 曲线插值步数,增大会使曲线更平滑但增加节点数量
    # --center-lat/lon: 地图中心坐标,需根据实际地理位置调整
    # --projection: 投影坐标系统,一般保持默认即可
    # --no-groups: 添加此参数会禁用SVG分组解析,可简化输出但会丢失层级关系
    # --no-transforms: 添加此参数会禁用SVG变换解析,可加快处理但会丢失旋转缩放等效果
    # --min-segment: 最小线段长度(米),增大会减少节点数但降低精度
    
    # 命令行参数配置指南:
    parser.add_argument('input', help='Input SVG file')
    parser.add_argument('output', help='Output OSM file')
    # --scale-num: 缩放比例分子,增大会放大地图尺寸
    # --scale-div: 缩放比例分母,减小会放大地图尺寸
    # --curve-steps: 曲线插值步数,增大会使曲线更平滑但增加节点数量
    # --center-lat/lon: 地图中心坐标,需根据实际地理位置调整
    # --projection: 投影坐标系统,一般保持默认即可
    # --no-groups: 添加此参数会禁用SVG分组解析,可简化输出但会丢失层级关系
    # --no-transforms: 添加此参数会禁用SVG变换解析,可加快处理但会丢失旋转缩放等效果
    # --min-segment: 最小线段长度(米),增大会减少节点数但降低精度
    
    parser = argparse.ArgumentParser(description='Convert SVG files to OSM XML')
    parser.add_argument('input', help='Input SVG file or directory')
    parser.add_argument('output', help='Output OSM file or directory')
    
    # 基本设置
    parser.add_argument('--scale-num', type=float, default=1.0,
                      help='Scale numerator (default: 1.0)')
    parser.add_argument('--scale-div', type=float, default=19.0,
                      help='Scale divisor (default: 19.0)')
    parser.add_argument('--curve-steps', type=int, default=3,
                      help='Number of steps for curve interpolation (default: 4)')
    
    # 投影设置
    parser.add_argument('--center-lat', type=float, default=31.17947960453,
                      help='Center latitude (default: 31.17947960453)')
    parser.add_argument('--center-lon', type=float, default=121.59139728492,
                      help='Center longitude (default: 121.59139728492)')
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
    
    # 创建设置对象
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
    
    # 转换输入输出路径为Path对象
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    # 根据输入类型选择处理方式
    if input_path.is_file():
        # 处理单个文件
        return process_single_file(input_path, output_path, settings)
    elif input_path.is_dir():
        # 处理目录
        return process_directory(input_path, output_path, settings)
    else:
        print(f"Error: Input path {input_path} does not exist")
        return 1

if __name__ == "__main__":
    exit(main()) 
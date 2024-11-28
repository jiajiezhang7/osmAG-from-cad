#!/usr/bin/env python3
import os
import sys
import logging
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
import time

class ODAConverter:
    def __init__(self, log_level=logging.INFO):
        """初始化转换器"""
        self.setup_logging(log_level)
        self.check_oda_installation()
        
    def setup_logging(self, log_level):
        """设置日志配置"""
        self.logger = logging.getLogger('ODAConverter')
        self.logger.setLevel(log_level)
        
        # 创建日志目录
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        
        # 设置日志文件
        log_file = log_dir / f'conversion_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        
        # 创建处理器
        console_handler = logging.StreamHandler()
        file_handler = logging.FileHandler(log_file)
        
        # 设置格式
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        
        # 添加处理器
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

    def check_oda_installation(self):
        """检查ODA File Converter是否已安装"""
        oda_paths = [
            '/opt/ODAFileConverter/ODAFileConverter',
            '/usr/bin/ODAFileConverter',
            os.path.expanduser('~/ODAFileConverter/ODAFileConverter')
        ]
        
        for path in oda_paths:
            if os.path.exists(path):
                self.oda_path = path
                self.logger.info(f"ODA File Converter found at: {path}")
                return
                
        self.logger.error("ODA File Converter not found")
        raise SystemExit(
            "Please install ODA File Converter from "
            "https://www.opendesign.com/guestfiles/oda_file_converter"
        )

    def convert_file(self, input_file, output_file):
        """
        转换单个文件
        :param input_file: 输入文件路径
        :param output_file: 输出文件路径
        :return: (bool, str) 转换是否成功及相关信息
        """
        try:
            start_time = time.time()
            self.logger.debug(f"Starting conversion of {input_file}")
            
            # 确保输入文件存在
            if not os.path.exists(input_file):
                return False, f"Input file not found: {input_file}"
            
            # 创建输出目录
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # 获取输入和输出文件的绝对路径
            input_abs = os.path.abspath(input_file)
            output_abs = os.path.abspath(output_file)
            
            # 构建ODA命令
            # 参数说明：
            # ACAD2018 - AutoCAD 2018格式
            # DXF - 输出格式
            # 1 - 输出版本 (1 = 2000)
            cmd = [
                self.oda_path,
                os.path.dirname(input_abs),  # 输入目录
                os.path.dirname(output_abs),  # 输出目录
                'ACAD2018',  # 输入格式
                'DXF',       # 输出格式
                '1',         # DXF版本 (2000)
                os.path.basename(input_abs)  # 输入文件名
            ]
            
            # 执行转换
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )
            
            # 检查结果
            if os.path.exists(output_file):
                duration = time.time() - start_time
                success_msg = f"Successfully converted {input_file} in {duration:.2f} seconds"
                self.logger.info(success_msg)
                return True, success_msg
            else:
                error_msg = f"Failed to convert {input_file}: {result.stderr}"
                self.logger.error(error_msg)
                return False, error_msg
                
        except subprocess.TimeoutExpired:
            error_msg = f"Conversion timeout for {input_file}"
            self.logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Error converting {input_file}: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

    def batch_convert(self, input_dir, output_dir, recursive=False):
        """
        批量转换目录中的文件
        :param input_dir: 输入目录
        :param output_dir: 输出目录
        :param recursive: 是否递归处理子目录
        :return: (int, int) 成功和失败的数量
        """
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        
        # 确保输出目录存在
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 收集所有要处理的文件
        pattern = '**/*.dwg' if recursive else '*.dwg'
        dwg_files = list(input_path.glob(pattern))
        total_files = len(dwg_files)
        
        if total_files == 0:
            self.logger.warning(f"No DWG files found in {input_dir}")
            return 0, 0
        
        self.logger.info(f"Found {total_files} DWG files to process")
        
        success_count = 0
        fail_count = 0
        
        for dwg_file in dwg_files:
            rel_path = dwg_file.relative_to(input_path)
            output_file = output_path / rel_path.with_suffix('.dxf')
            
            success, _ = self.convert_file(str(dwg_file), str(output_file))
            if success:
                success_count += 1
            else:
                fail_count += 1
            
            # 显示进度
            completed = success_count + fail_count
            progress = (completed / total_files) * 100
            self.logger.info(f"Progress: {progress:.1f}% ({completed}/{total_files})")
        
        # 输出统计信息
        self.logger.info("\nConversion Summary:")
        self.logger.info(f"Successfully converted: {success_count}")
        self.logger.info(f"Failed conversions: {fail_count}")
        self.logger.info(f"Total files processed: {total_files}")
        
        return success_count, fail_count

def main():
    parser = argparse.ArgumentParser(
        description='Convert DWG files to DXF format using ODA File Converter'
    )
    
    parser.add_argument(
        '-i', '--input',
        required=True,
        help='Input DWG file or directory'
    )
    
    parser.add_argument(
        '-o', '--output',
        required=True,
        help='Output DXF file or directory'
    )
    
    parser.add_argument(
        '-r', '--recursive',
        action='store_true',
        help='Recursively process subdirectories'
    )
    
    parser.add_argument(
        '-d', '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    args = parser.parse_args()
    
    # 创建转换器实例
    converter = ODAConverter(
        log_level=logging.DEBUG if args.debug else logging.INFO
    )
    
    # 处理输入
    try:
        if os.path.isdir(args.input):
            # 批量转换目录
            converter.batch_convert(args.input, args.output, args.recursive)
        else:
            # 转换单个文件
            success, message = converter.convert_file(args.input, args.output)
            if not success:
                sys.exit(1)
    except KeyboardInterrupt:
        converter.logger.info("\nConversion interrupted by user")
        sys.exit(1)
    except Exception as e:
        converter.logger.error(f"Conversion failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
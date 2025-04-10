#!/usr/bin/env python3
import os
import sys
import logging
import argparse
import subprocess
from datetime import datetime
from pathlib import Path
import time

# Last Modified by Jiajie Zhang 2024.12.05
# 该脚本用于调用ODA File Converter，可实现 File Folder -> File Folder的转换，也可实现单个文件的转换(dwg -> dxf)
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
                self.logger.error(f"Input file does not exist: {input_file}")
                return False, f"Input file not found: {input_file}"
            
            # 获取输入和输出文件的绝对路径
            input_abs = os.path.abspath(input_file)
            output_abs = os.path.abspath(output_file)
            
            self.logger.info(f"Input absolute path: {input_abs}")
            self.logger.info(f"Output absolute path: {output_abs}")
            
            # 检查输入文件权限
            self.logger.debug(f"Input file permissions: {oct(os.stat(input_abs).st_mode)[-3:]}")
            
            # 创建输出目录
            os.makedirs(os.path.dirname(output_abs), exist_ok=True)
            
            # 获取输入和输出文件的目录和文件名
            input_dir = os.path.dirname(input_abs)
            output_dir = os.path.dirname(output_abs)
            input_filename = os.path.basename(input_abs)
            
            # 构建命令
            cmd = [
                self.oda_path,
                input_dir,          # ODA需要目录作为输入
                output_dir,         # ODA需要目录作为输出
                'ACAD2018',
                'DXF',
                '1',                # 递归标志 (1=启用)
                '0',                # Audit 标志 (0=禁用) - 基于推测添加 - 正确的
                input_filename      # 只传入文件名
            ]
            
            self.logger.debug(f"Executing command: {' '.join(cmd)}")
            
            
            # 执行转换
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # 添加更详细的命令执行结果日志
            self.logger.debug(f"命令执行详情:")
            self.logger.debug(f"返回码: {result.returncode}")
            self.logger.debug(f"标准输出: {result.stdout}")
            self.logger.debug(f"标准错误: {result.stderr}")
            
            # 检查进程返回码
            if result.returncode != 0:
                error_msg = f"ODA转换失败 - 返回码: {result.returncode}\n输出: {result.stdout}\n错误: {result.stderr}"
                self.logger.error(error_msg)
                return False, error_msg
            
            # 检查输出文件
            if os.path.exists(output_file):
                if os.path.getsize(output_file) == 0:
                    error_msg = "输出文件大小为0字节，可能转换失败"
                    self.logger.error(error_msg)
                    return False, error_msg
                
                duration = time.time() - start_time
                success_msg = f"成功转换 {input_file}，用时 {duration:.2f} 秒"
                self.logger.info(success_msg)
                return True, success_msg
            else:
                error_msg = f"转换失败 - 未生成输出文件: {output_file}"
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
    # --- 在这里指定固定的输入和输出路径 ---
    hardcoded_input_path = "/home/jay/AGSeg_ws/AGSeg/cad2osm/data/data_dwg/SIST-F1.dwg"  # <--- 修改这里
    hardcoded_output_path = "/home/jay/AGSeg_ws/AGSeg/cad2osm/data/data_dxf/SIST-F1.dxf" # <--- 修改这里
    # ---------------------------------------

    parser = argparse.ArgumentParser(
        description='Convert DWG files to DXF format using ODA File Converter'
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
        # 使用硬编码的路径
        if os.path.isdir(hardcoded_input_path):
            # 批量转换目录
            converter.batch_convert(hardcoded_input_path, hardcoded_output_path, args.recursive)
        else:
            # 如果输入是文件，但输出是目录，自动构造输出文件名
            if os.path.isdir(hardcoded_output_path):
                input_filename = os.path.basename(hardcoded_input_path)
                output_file = os.path.join(
                    hardcoded_output_path,
                    os.path.splitext(input_filename)[0] + '.dxf'
                )
            else:
                # 如果输出也是文件路径
                output_file = hardcoded_output_path
                
            success, message = converter.convert_file(hardcoded_input_path, output_file)
            if not success:
                sys.exit(1)
    except KeyboardInterrupt:
        converter.logger.info("\n转换被用户中断")
        sys.exit(1)
    except Exception as e:
        converter.logger.error(f"转换失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
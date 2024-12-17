# dxf_layer_info.py
import ezdxf
import os
from datetime import datetime

def extract_layer_info(dxf_file, output_file):
    """
    从DXF文件中提取图层信息并保存到文本文件
    
    参数:
    dxf_file (str): DXF文件路径
    output_file (str): 输出文本文件路径
    """
    try:
        # 读取DXF文件
        doc = ezdxf.readfile(dxf_file)
        
        # 获取所有图层
        layers = [layer.dxf.name for layer in doc.layers]
        
        # 准备输出信息
        output_text = [
            f"DXF文件图层信息报告",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"DXF文件: {os.path.basename(dxf_file)}",
            f"图层总数: {len(layers)}",
            "\n图层列表:",
        ]
        
        # 添加图层信息
        for i, layer in enumerate(sorted(layers), 1):
            output_text.append(f"{i}. {layer}")
        
        # 写入文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(output_text))
            
        return True, "图层信息已成功导出"
        
    except ezdxf.DXFError as e:
        return False, f"DXF文件错误: {str(e)}"
    except Exception as e:
        return False, f"处理出错: {str(e)}"

def main():
    # 获取用户输入
    dxf_file = input("请输入DXF文件路径: ").strip('"')  # 支持拖拽文件时去除引号
    
    # 生成输出文件名（与DXF同目录，添加时间戳）
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = os.path.dirname(dxf_file) or '.'  # 如果没有目录则使用当前目录
    output_name = f"图层信息_{os.path.basename(dxf_file)}_{timestamp}.txt"
    output_file = os.path.join(output_dir, output_name)
    
    print(f"\n正在处理文件: {os.path.basename(dxf_file)}")
    success, message = extract_layer_info(dxf_file, output_file)
    
    if success:
        print(f"\n{message}")
        print(f"输出文件已保存至: {output_file}")
    else:
        print(f"\n错误: {message}")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
explode_blocks.py

将所有 INSERT 块引用展平到 modelspace，并输出一个仅包含几何实体的 DXF 文件。
"""
import ezdxf
import os
import sys

# --- 用户可修改路径 ---
INPUT_FILE = "/home/jay/AGSeg_ws/AGSeg/cad2osm/data/SEM/dxf/SEM-F1-Maxu.dxf"
OUTPUT_FILE = "/home/jay/AGSeg_ws/AGSeg/cad2osm/data/SEM/dxf/SEM-F1_Maxu_flattened.dxf"
# -----------------------

def explode_inserts(input_file: str, output_file: str):
    # 读取原始 DXF
    doc = ezdxf.readfile(input_file)
    # 创建新文档，保持相同版本
    new_doc = ezdxf.new(dxfversion=doc.dxfversion)
    # 复制头变量
    new_doc.header = doc.header
    try:
        new_doc.header['$ACADVER'] = doc.header['$ACADVER']
    except KeyError:
        pass
    
    msp = doc.modelspace()
    new_msp = new_doc.modelspace()
    # 遍历所有实体，爆破 INSERT，其余复制
    for entity in msp:
        if entity.dxftype() == 'INSERT':
            block_name = entity.dxf.name
            try:
                for sub in entity.virtual_entities():
                    new_msp.add_entity(sub)
            except Exception as e:
                print(f"警告: 展平块引用 '{block_name}' 失败: {e}", file=sys.stderr)
        else:
            try:
                new_msp.add_entity(entity.copy())
            except Exception as e:
                print(f"警告: 复制实体 {entity.dxftype()} 失败: {e}", file=sys.stderr)
    # 保存输出
    new_doc.saveas(output_file)
    print(f"输出文件已保存: {output_file}")


def main():
    # 使用硬编码路径
    input_file = INPUT_FILE
    output_file = OUTPUT_FILE
    if not os.path.isfile(input_file):
        print(f"错误: 输入文件不存在: {input_file}", file=sys.stderr)
        sys.exit(1)
    explode_inserts(input_file, output_file)

if __name__ == '__main__':
    main()

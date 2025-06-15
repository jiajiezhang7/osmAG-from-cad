#!/usr/bin/env python3
import cv2
import numpy as np
import os
from pathlib import Path
from cad2osm.script.functions.wall_gap_filter.wall_gap_filler import WallGapFiller

def analyze_image_stats(image_path):
    """分析图像统计信息"""
    img = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None
    
    black_pixels = np.count_nonzero(img == 0)
    white_pixels = np.count_nonzero(img == 255)
    gray_pixels = img.size - black_pixels - white_pixels
    total_pixels = img.size
    
    return {
        'black_percent': black_pixels / total_pixels * 100,
        'white_percent': white_pixels / total_pixels * 100,
        'gray_percent': gray_pixels / total_pixels * 100
    }

def batch_test_improved_algorithm():
    """批量测试改进后的算法"""
    print("=== 改进算法批量测试 ===")
    print("测试多个图像文件，验证识别率提升效果")
    print()
    
    # 输入目录和输出目录
    input_dir = Path("cad2osm/data/web-cad/img/png_manual_filter")
    output_dir = Path("test_output/improved_batch")
    output_dir.mkdir(exist_ok=True)
    
    # 创建处理器
    filler = WallGapFiller()
    
    # 测试参数组合
    test_configs = [
        {'gap_size': 'small', 'min_area': 50, 'suffix': 'small'},
        {'gap_size': 'medium', 'min_area': 100, 'suffix': 'medium'},
        {'gap_size': 'large', 'min_area': 150, 'suffix': 'large'}
    ]
    
    # 选择测试图像
    test_images = [
        "Aule-scolastiche-pianta-1.png",
        "office.png", 
        "apartment_1.png",
        "apartment_2.png",
        "hospital.png"
    ]
    
    results = []
    
    for image_name in test_images:
        image_path = input_dir / image_name
        if not image_path.exists():
            print(f"⚠️ 跳过不存在的图像: {image_name}")
            continue
        
        print(f"🔍 处理图像: {image_name}")
        
        # 分析原始图像
        original_stats = analyze_image_stats(image_path)
        if original_stats is None:
            print(f"❌ 无法读取原始图像: {image_name}")
            continue
        
        print(f"  原始: 墙壁{original_stats['black_percent']:.1f}%")
        
        # 测试不同参数配置
        best_config = None
        best_improvement = 0
        
        for config in test_configs:
            try:
                # 处理图像
                output_file = output_dir / f"{Path(image_name).stem}_{config['suffix']}.png"
                filler.process_image(
                    image_path, 
                    output_file, 
                    gap_size=config['gap_size'],
                    min_area=config['min_area']
                )
                
                # 分析结果
                result_stats = analyze_image_stats(output_file)
                if result_stats:
                    improvement = result_stats['black_percent'] / original_stats['black_percent']
                    print(f"  {config['suffix']}: 墙壁{result_stats['black_percent']:.1f}% (提升{improvement:.1f}x)")
                    
                    if improvement > best_improvement:
                        best_improvement = improvement
                        best_config = config
                
            except Exception as e:
                print(f"  ❌ {config['suffix']} 配置处理失败: {e}")
        
        if best_config:
            results.append({
                'image': image_name,
                'original_percent': original_stats['black_percent'],
                'best_config': best_config,
                'best_improvement': best_improvement,
                'final_percent': original_stats['black_percent'] * best_improvement
            })
        
        print()
    
    # 汇总结果
    print("=== 测试结果汇总 ===")
    if results:
        total_improvement = sum(r['best_improvement'] for r in results) / len(results)
        
        print(f"📊 平均识别率提升: {total_improvement:.1f}x")
        print()
        
        for result in results:
            print(f"📄 {result['image']}:")
            print(f"   原始: {result['original_percent']:.1f}%")
            print(f"   最佳: {result['final_percent']:.1f}% ({result['best_improvement']:.1f}x)")
            print(f"   配置: {result['best_config']['gap_size']}, min_area={result['best_config']['min_area']}")
            print()
        
        # 给出建议
        print("=== 使用建议 ===")
        if total_improvement >= 3.0:
            print("✅ 改进效果显著！建议使用新算法")
        elif total_improvement >= 2.0:
            print("👍 改进效果良好，推荐使用")
        elif total_improvement >= 1.5:
            print("🆗 有一定改进，可以考虑使用")
        else:
            print("⚠️ 改进效果有限，需要进一步优化")
        
        # 最佳参数建议
        best_configs = [r['best_config'] for r in results]
        gap_sizes = [c['gap_size'] for c in best_configs]
        min_areas = [c['min_area'] for c in best_configs]
        
        from collections import Counter
        most_common_gap = Counter(gap_sizes).most_common(1)[0][0]
        avg_min_area = sum(min_areas) / len(min_areas)
        
        print(f"📋 推荐参数:")
        print(f"   gap_size: {most_common_gap}")
        print(f"   min_area: {int(avg_min_area)}")
    
    else:
        print("❌ 没有成功处理的图像")

if __name__ == "__main__":
    batch_test_improved_algorithm() 
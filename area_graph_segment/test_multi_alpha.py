#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试多Alpha值功能的脚本
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from batch_process_png import calculate_door_corridor_from_alpha, parse_alpha_values

def test_alpha_calculation():
    """测试Alpha值计算功能"""
    print("=== 测试Alpha值计算功能 ===")
    
    # 测试不同的Alpha值和分辨率组合
    test_cases = [
        (100, 0.04),
        (500, 0.04),
        (1000, 0.04),
        (200, 0.05),
        (1000, 0.03)
    ]
    
    for alpha, resolution in test_cases:
        door_width, corridor_width = calculate_door_corridor_from_alpha(alpha, resolution)
        print(f"Alpha={alpha}, Resolution={resolution:.3f} -> "
              f"door_width={door_width:.3f}, corridor_width={corridor_width:.3f}")
    
    print()

def test_alpha_parsing():
    """测试Alpha值解析功能"""
    print("=== 测试Alpha值解析功能 ===")
    
    test_strings = [
        "100,200,500",
        "100-500",
        "50, 100, 200, 1000",
        "100-1000",
        ""
    ]
    
    for test_str in test_strings:
        result = parse_alpha_values(test_str)
        print(f"输入: '{test_str}' -> 输出: {result}")
    
    print()

def test_reverse_calculation():
    """测试反向计算的准确性"""
    print("=== 测试反向计算准确性 ===")
    
    # 模拟C++代码中的计算逻辑
    import math
    
    resolution = 0.04
    test_alphas = [100, 500, 1000, 2000]
    
    for target_alpha in test_alphas:
        # 使用我们的函数计算door_width和corridor_width
        door_width, corridor_width = calculate_door_corridor_from_alpha(target_alpha, resolution)
        
        # 模拟C++代码的计算逻辑
        a = min(door_width, corridor_width) + 0.1
        calculated_alpha = math.ceil(a * a * 0.25 / (resolution * resolution))
        
        print(f"目标Alpha={target_alpha}, 计算得到Alpha={calculated_alpha}, "
              f"误差={abs(target_alpha - calculated_alpha)}")
    
    print()

if __name__ == "__main__":
    test_alpha_calculation()
    test_alpha_parsing()
    test_reverse_calculation()
    
    print("=== 测试完成 ===")
    print("如果所有测试都通过，可以使用多Alpha值功能了！") 
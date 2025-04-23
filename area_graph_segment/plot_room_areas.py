#!/usr/bin/env python3
"""
Read room_areas.csv and plot area distribution and knee point detection using matplotlib.
"""
import csv
import numpy as np
import matplotlib.pyplot as plt
import matplotlib as mpl
# Use default matplotlib font for full English output
mpl.rcParams['font.sans-serif'] = ['DejaVu Sans']
mpl.rcParams['axes.unicode_minus'] = False

def main():
    rooms = []
    areas = []
    with open('/home/jay/AGSeg_ws/AGSeg/area_graph_segment/build/room_areas.csv', newline='') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            rooms.append(row[0])
            areas.append(float(row[1]))

    n = len(areas)
    if n == 0:
        print('No room data found.')
        return
    areas_sorted = sorted(areas, reverse=True)
    total = sum(areas)
    mean = total / n
    median = np.median(areas)
    min_area = areas_sorted[-1]
    max_area = areas_sorted[0]
    print(f'Room count: {n}')
    print(f'Area: min={min_area:.3f}, max={max_area:.3f}, mean={mean:.3f}, median={median:.3f}')

    # 检测拐点（Knee Detection）
    x = np.arange(n)
    y = np.array(areas_sorted)
    dx = n - 1
    dy = y[-1] - y[0]
    norm = np.hypot(dx, dy)
    distances = np.abs(dx * (y - y[0]) - dy * x) / norm
    knee_idx = int(np.argmax(distances))
    threshold = areas_sorted[knee_idx]
    print(f'Detected knee index: {knee_idx}, area threshold: {threshold:.3f}')
    print(f'> Threshold room count: {knee_idx+1}, <= Threshold room count: {n-knee_idx-1}')
    
    # 计算忽略前3个最大房间后的统计信息
    skip_largest = 3
    if n > skip_largest:
        areas_sorted_filtered = areas_sorted[skip_largest:]
        total_filtered = sum(areas_sorted_filtered)
        mean_filtered = total_filtered / (n - skip_largest)
        median_filtered = np.median(areas_sorted_filtered)
        min_area_filtered = areas_sorted_filtered[-1]
        max_area_filtered = areas_sorted_filtered[0]
        print(f'\nStats after excluding the largest {skip_largest} rooms:')
        print(f'Area: min={min_area_filtered:.3f}, max={max_area_filtered:.3f}, mean={mean_filtered:.3f}, median={median_filtered:.3f}')

    # 绘制直方图和排序曲线，忽略前3个最大的房间
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16,6))
    
    # 忽略前3个最大的房间
    skip_largest = 3
    areas_filtered = areas.copy()
    for i in range(min(skip_largest, len(areas_sorted))):
        largest = areas_sorted[i]
        if largest in areas_filtered:
            areas_filtered.remove(largest)
    
    # 绘制直方图，使用过滤后的数据
    ax1.hist(areas_filtered, bins=50, color='skyblue', edgecolor='grey')
    ax1.axvline(threshold, color='red', linestyle='--', label=f'Threshold {threshold:.3f}')
    ax1.set_title('Room Area Distribution (Excluding 3 Largest)')
    ax1.set_xlabel('Area (sqm)')
    ax1.set_ylabel('Room Count')
    ax1.legend()
    
    # 绘制排序曲线，使用过滤后的数据
    y_filtered = np.array(areas_sorted[skip_largest:])
    x_filtered = np.arange(len(y_filtered))
    ax2.plot(x_filtered, y_filtered, marker='o', linestyle='-')
    ax2.axhline(threshold, color='red', linestyle='--', label=f'Threshold {threshold:.3f}')
    ax2.axvline(knee_idx - skip_largest if knee_idx >= skip_largest else 0, 
               color='green', linestyle='--', 
               label=f'Knee Index {knee_idx}')
    ax2.set_title('Sorted Room Area Curve (Excluding 3 Largest)')
    ax2.set_xlabel('Room Rank')
    ax2.set_ylabel('Area (sqm)')
    ax2.legend()

    plt.tight_layout()
    # 保存图像到文件
    plt.savefig('room_areas_analysis_filtered.png')
    plt.show()

if __name__ == '__main__':
    main()

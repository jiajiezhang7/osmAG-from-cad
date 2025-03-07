# 多边形毛刺去除算法参数调整指南

## 参数概述

`removeSpikesFromPolygons`函数接受两个主要参数来控制毛刺去除的强度：

```cpp
removeSpikesFromPolygons(angleThreshold, distanceThreshold, &preservePoints);
```

## 参数详解

### 1. 角度阈值 (angleThreshold)
- **默认值**: 15.0度
- **范围**: 5.0-30.0度
- **效果**: 控制与90度偏差多少的角被视为毛刺
- **调整方向**: 
  - 值越小 → 越激进 → 移除更多角度接近90度的点
  - 值越大 → 越保守 → 只移除角度偏离90度很远的点
- **极端值**: 8.0 (非常激进)

### 2. 距离阈值 (distanceThreshold)
- **默认值**: 0.15
- **范围**: 0.05-0.3
- **效果**: 控制点到直线的距离多小时被视为毛刺
- **调整方向**:
  - 值越大 → 越激进 → 移除更多距离直线较远的点
  - 值越小 → 越保守 → 只移除几乎在直线上的点
- **极端值**: 0.3 (非常激进)

## 推荐参数组合

| 效果 | angleThreshold | distanceThreshold | 适用场景 |
|------|----------------|-------------------|----------|
| 非常激进 | 8.0 | 0.3 | 地图有大量毛刺需要强力清除 |
| 激进 | 10.0 | 0.25 | 地图有明显毛刺需要清除 |
| 中等 | 15.0 | 0.15 | 平衡毛刺去除和形状保留 |
| 保守 | 20.0 | 0.1 | 只去除明显的毛刺 |
| 非常保守 | 30.0 | 0.05 | 只去除极端毛刺，最大程度保留原始形状 |

## 针对特定毛刺类型的代码调整

对于特定类型的毛刺，可以直接修改`removeSpikesFromPolygon`函数中的判断逻辑：

1. **针对尖角**:
   ```cpp
   // 修改前
   if (angle < 30.0 || angle > 150.0) {
       isSpike = true;
   }
   
   // 修改后 (更激进)
   if (angle < 40.0 || angle > 140.0) {
       isSpike = true;
   }
   ```

2. **针对长毛刺**:
   ```cpp
   // 修改前
   if (minVectorLen > 0.1 && (distance / minVectorLen) < 0.1) {
       isSpike = true;
   }
   
   // 修改后 (更激进)
   if (minVectorLen > 0.1 && (distance / minVectorLen) < 0.15) {
       isSpike = true;
   }
   ```

## 处理顽固毛刺的技巧

对于特别顽固的毛刺，可以考虑多次应用算法：

```cpp
// 多次应用毛刺移除算法
for (int i = 0; i < 2; i++) {
    removeSpikesFromPolygons(15.0, 0.15, &preservePoints);
}
```

## 注意事项

- 参数过于激进可能会过度简化多边形，导致有意义的形状丢失
- 总是在调整参数后检查结果，确保重要的几何特征得到保留
- 保留点列表(preservePoints)确保通道端点不会被错误移除

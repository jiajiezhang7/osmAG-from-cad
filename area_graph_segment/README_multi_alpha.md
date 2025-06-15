# 多Alpha值测试功能使用说明

## 概述

新的批处理脚本支持多Alpha值测试功能，用于解决从网络下载的CAD图像分辨率未知导致的分割质量问题。通过测试不同的Alpha值，您可以找到最适合特定图像的参数组合。

## Alpha值的作用

在area_graph_segmentation中，Alpha值控制Voronoi图的细分程度：
- **较小的Alpha值**：产生较粗的分割，适合房间较大的建筑
- **较大的Alpha值**：产生较细的分割，适合房间较小或结构复杂的建筑

## 使用方法

### 1. 基本多Alpha值测试

```bash
# 测试指定的Alpha值
python batch_process_png.py ./input_images --alpha-values "100,200,500,1000"

# 测试Alpha值范围（自动生成等差数列）
python batch_process_png.py ./input_images --alpha-values "100-1000"
```

### 2. 使用预设Alpha值范围

```bash
# 小范围测试（适合快速验证）
python batch_process_png.py ./input_images --alpha-preset small

# 中等范围测试（平衡的选择）
python batch_process_png.py ./input_images --alpha-preset medium

# 大范围测试（适合大型建筑）
python batch_process_png.py ./input_images --alpha-preset large

# 全面测试（包含所有常用值）
python batch_process_png.py ./input_images --alpha-preset comprehensive
```

### 3. 预览模式

```bash
# 查看将要执行的命令而不实际运行
python batch_process_png.py ./input_images --alpha-values "100,500,1000" --dry-run
```

### 4. 结合其他参数

```bash
# 只处理包含特定关键词的文件
python batch_process_png.py ./input_images --alpha-values "100,500,1000" --filter "apartment"

# 指定输出目录
python batch_process_png.py ./input_images --alpha-values "100,500,1000" --output-dir ./multi_alpha_results
```

## 预设Alpha值范围

| 预设名称 | Alpha值 | 适用场景 |
|---------|---------|----------|
| small | [50, 100, 200, 500] | 快速测试，小型建筑 |
| medium | [100, 200, 500, 1000, 2000] | 一般用途，平衡测试 |
| large | [500, 1000, 2000, 5000] | 大型建筑，复杂结构 |
| comprehensive | [50, 100, 200, 500, 1000, 2000, 5000, 10000] | 全面测试 |

## 输出目录结构

多Alpha值测试会创建如下目录结构：

```
output/
├── image1/
│   ├── alpha_100/
│   │   ├── image1.png
│   │   ├── image1_output/
│   │   ├── clean.png
│   │   ├── afterAlphaRemoval.png
│   │   └── ...
│   ├── alpha_200/
│   │   ├── image1.png
│   │   ├── image1_output/
│   │   └── ...
│   └── alpha_500/
│       └── ...
└── image2/
    ├── alpha_100/
    └── ...
```

## Alpha值计算原理

脚本根据以下公式自动计算对应的door_width和corridor_width：

```
alpha_value = ceil(a^2 * 0.25 / resolution^2)
```

其中 `a = min(door_width, corridor_width) + 0.1`

反推公式：
```
a = sqrt(alpha_value * 4 * resolution^2)
door_width = a - 0.1
corridor_width = a + 0.5
```

## 使用建议

1. **首次测试**：使用 `--alpha-preset medium` 进行初始评估
2. **细化测试**：根据初始结果选择更窄的Alpha值范围
3. **批量处理**：确定最佳Alpha值后，用该值处理所有同类型图像
4. **结果比较**：查看不同Alpha值的输出图像，选择分割效果最好的

## 示例工作流程

```bash
# 1. 快速预览测试
python batch_process_png.py ./cad_images --alpha-preset small --dry-run

# 2. 执行中等范围测试
python batch_process_png.py ./cad_images --alpha-preset medium

# 3. 基于结果细化测试
python batch_process_png.py ./cad_images --alpha-values "800,1000,1200"

# 4. 处理所有图像（使用最佳Alpha值对应的参数）
python batch_process_png.py ./all_cad_images --door-width 1.5 --corridor-width 2.0
```

## 注意事项

- 多Alpha值测试会显著增加处理时间
- 建议先用少量图像测试找到合适的Alpha值范围
- 每个Alpha值都会创建完整的输出，注意磁盘空间
- 使用预览模式(`--dry-run`)可以在不实际运行的情况下查看参数设置 
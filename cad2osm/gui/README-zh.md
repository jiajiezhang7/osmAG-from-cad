# CAD2OSM图形界面应用

## 简介

这是一个用于CAD到OSM转换的图形界面工具，包含以下功能：

1. **CAD预处理**：DWG到PNG的转换
   - 完整流程：DWG → DXF → 过滤DXF → SVG → PNG
   - 半自动流程：已过滤DXF → SVG → PNG

2. **文本提取**：从DXF提取文本并添加到OSM
   - 从DXF文件提取文本
   - 将文本坐标转换为像素坐标
   - 从OSM文件提取房间多边形
   - 匹配文本到房间
   - 更新OSM文件

3. **OSM合并**：合并多个OSM文件
   - 支持通过电梯和楼梯区域匹配
   - 自动计算偏移量并应用
   - 更新ID以避免冲突

4. **方向校正**：校正OSM中多边形的方向
   - 房间(room)多边形应为逆时针方向
   - 结构(structure)多边形应为顺时针方向

## 安装

### 依赖项

```bash
pip install -r requirements.txt
```

### 运行

```bash
python start_gui.py
```

## 使用说明

### 项目管理

应用程序使用项目管理系统组织文件。每个项目都有标准的目录结构：

```
project_root/
├── data/
│   ├── [项目名]/
│   │   ├── dwg/                    # 原始DWG文件
│   │   ├── dxf/
│   │   │   ├── original/           # 原始DXF文件
│   │   │   ├── auto_filter/        # 自动过滤后的DXF
│   │   │   └── manual_filter/      # 手动过滤后的DXF
│   │   ├── img/
│   │   │   ├── svg_auto_filter/    # 自动过滤后生成的SVG
│   │   │   ├── svg_manual_filter/  # 手动过滤后生成的SVG
│   │   │   ├── png_auto_filter/    # 自动过滤后生成的PNG
│   │   │   └── png_manual_filter/  # 手动过滤后生成的PNG
│   │   ├── osm/
│   │   │   ├── original/           # 原始OSM文件
│   │   │   ├── texted/             # 添加文本后的OSM
│   │   │   ├── merged/             # 合并后的OSM
│   │   │   └── corrected/          # 方向校正后的OSM
│   │   └── bounds/                 # 边界信息JSON文件
```

### CAD预处理

1. 选择项目
2. 选择处理模式（完整流程或半自动流程）
3. 选择输入文件或目录
4. 设置输出目录
5. 调整参数（分辨率、边缘空隙比例、线条粗细）
6. 点击"开始处理"按钮
7. 查看日志输出和进度

### 文本提取

1. 选择处理模式（完整流程、仅提取文本或仅匹配文本）
2. 设置输入文件（DXF文件、边界文件、OSM文件）
3. 设置输出文件路径
4. 调整参数（文本图层名称、匹配阈值等）
5. 设置文本过滤列表
6. 点击"开始处理"按钮
7. 查看匹配结果可视化图像

### OSM合并

1. 选择参照OSM文件
2. 添加目标OSM文件（可多选）
3. 设置输出文件路径
4. 调整参数（匹配区域类型、偏移计算方法、最小匹配区域数量）
5. 点击"开始合并"按钮
6. 查看合并结果统计

### 方向校正

1. 选择OSM文件
2. 设置输出文件路径
3. 点击"开始校正"按钮
4. 查看校正结果统计

## 开发说明

### 项目结构

```
gui/
├── main.py                 # 应用入口点
├── start_gui.py            # 启动脚本
├── ui/                     # 用户界面组件
│   ├── main_window.py      # 主窗口
│   ├── process_tab.py      # CAD预处理标签页
│   ├── text_tab.py         # 文本提取标签页
│   ├── merge_tab.py        # OSM合并标签页
│   └── direction_tab.py    # 方向校正标签页
├── modules/                # 功能模块
│   ├── process_module.py   # CAD预处理模块
│   ├── text_module.py      # 文本提取模块
│   ├── merge_module.py     # 合并模块
│   └── direction_module.py # 方向校正模块
├── utils/                  # 工具类
│   └── project_manager.py  # 项目管理器
└── config/                 # 配置文件
    └── app_config.yaml     # 应用配置
```

### 扩展开发

要添加新功能，请按照以下步骤操作：

1. 在`modules/`目录下创建新的功能模块
2. 在`ui/`目录下创建相应的用户界面组件
3. 在`main_window.py`中添加新的标签页
4. 更新`config/app_config.yaml`添加相关配置

## 许可证

本项目采用MIT许可证。详见LICENSE文件。

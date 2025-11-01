# Ownership
Ownership dataset base on TongSim


# TongSim 桌面场景生成管线 (Table Scene Generation Pipeline)

本项目是一个基于 TongSim 模拟环境的、分为两个主要阶段的自动化场景生成管线：

1.  **阶段一：桌面网格测量 (`table_margin.py`)**
    此阶段通过物理模拟（在桌面上放置测试物体）来精确测量桌面的安全可用区域。它会遍历所有场景中的桌子，并为每张桌子生成一个 `JSON` 文件，其中包含所有“安全”（物体不会掉落）的网格坐标。

2.  **阶段二：场景生成与放置 (`run_pipeline_table_with_grid_items`)**
    此阶段读取第一阶段生成的网格 `JSON` 文件，然后在这些安全网格上智能地放置物品。它还会围绕桌子生成并安置人物（可坐/可站），为人物分配专属物品，生成连锁物品（如书旁边的笔），并自动生成多视角摄像头以捕捉生成的场景。

最终目的是自动创建大量丰富、真实、可交互的“人与桌子”的合成数据场景。

## 主要功能

  * **物理安全检测**：通过物理模拟测试每个网格，确保物品放置后不会掉落或滑动。
  * **智能网格划分**：使用BFS算法从中心扩展，自动适应不规则桌面。
  * **人物智能放置**：在桌子四周自动生成人物，并处理坐/站姿态（包括自动查找和调整椅子）。
  * **分区物品放置**：将桌面划分为 `main`（主要）、`frequent`（常用）、`infrequent`（不常用）等区域，实现更真实的物品布局。
  * **连锁物品生成**：支持基于规则的连锁放置（例如，放置一本书后，有概率在旁边放一支笔）。
  * **多视角数据采集**：自动生成环绕视角和俯视角的摄像头，并拍摄图像。
  * **详细数据导出**：将场景中所有物品、人物和摄像头的详细信息（位置、旋转、归属、动作等）保存为 `JSON` 文件。

## 项目文件结构

```
.
├── table_margin.py               # 阶段一: 桌面网格生成脚本
├── run_pipeline_table_with_grid_items.py  # 阶段二: 场景生成主脚本 (注：您提供了函数名)
│
├── query_util.py                 # 工具: TongSim 查询实体
├── entity_util.py                # 工具: 实体筛选与处理
├── other_util.py                 # 工具: AABB边界、面积计算等
│
├── agent_config.py               # 配置: 人物蓝图与特性
├── item_config.py                # 配置: 物品蓝图、属性、权重
├── composed_item.py              # 配置: 物品连锁生成规则
│
├── ownership/
│   ├── object/
│   │   ├── selected_scenes.txt   # 依赖: 筛选后的场景列表
│   │   └── chair.txt             # 依赖: 椅子蓝图ID列表
│   │
│   ├── table_boundaries/         # (输出) 阶段一生成的网格 JSON 存放处
│   │   ├── SDBP_Map_..._table_....json
│   │   └── ...
│   │
│   └── logs_grid/                # (输出) 阶段二生成的场景数据 (JSON 和 图像)
│       └── table_scene_map.../
│           ├── scene_data.json
│           ├── Camera_0.png
│           └── TopCamera_0.png
│
└── README.md                     # 本文件
```

## 依赖与环境

  * **TongSim**: 本项目依赖 TongSim 模拟器环境及 `tongsim` Python API。
  * **Python 3.x**
  * **依赖文件**: 运行前，需要准备好以下文件：
      * `./ownership/object/selected_scenes.txt`: 包含要处理的地图名称（例如 `SDBP_Map_001`），每行一个。
      * `./ownership/object/chair.txt`: 包含所有被视作“椅子”的蓝图ID。
      * `objects_info.json` (在 `json_util.py` 中被引用): 包含资产类型信息。

## 如何运行：两步工作流

### 步骤一：生成桌面网格数据

首先，您必须运行 `table_margin.py` 来分析所有桌子并生成安全网格 `JSON` 文件。

**示例 (`table_margin.py`)**:

```python
if __name__ == "__main__":
    # 示例: 测试 1 到 300 号地图，网格大小为 10.0
    run_table_boundary_measurement(
        map_range=range(1, 300), 
        grid_size=10.0
    )

    # 示例: 仅测试 1 到 10 号地图
    # run_table_boundary_measurement(
    #     map_range=range(1, 10),
    #     grid_size=10.0
    # )
```

运行后，所有生成的网格数据将保存在 `./ownership/table_boundaries/` 目录下。

### 步骤二：使用网格生成场景

在拥有网格数据后，您可以运行主管线 `run_pipeline_table_with_grid_items` 来创建完整的场景。

**示例 (`run_pipeline_table_with_grid_items.py`)**:

```python
# 基本用法
run_pipeline_table_with_grid_items(
    map_range=range(1, 10),
    num_agents=2,
    agent_sides=['front', 'back'],
    max_item=9
)

# 完整配置示例
run_pipeline_table_with_grid_items(
    map_range=range(1, 300),
    min_room_area=4.0,
    min_table_area=0.4,
    log_dir="./ownership/logs_grid",
    grid_dir="./ownership/table_boundaries",
    num_agents=3,
    agent_sides=['front', 'left', 'right'],
    max_item=12
)
```

运行后，所有生成的场景数据（`scene_data.json` 和图像）将保存在 `./ownership/logs_grid/` 目录下。

-----

## 阶段一：桌面网格生成 (`table_margin.py`) 详解

### 功能概述

生成桌子的边界网格划分JSON文件，记录桌面的安全可用区域。

### 主要函数

#### 1\. `measure_table_grid_boundaries()`

**功能**: 测量桌面安全边界并划分为格子网格

**参数**:

  - `ue`: TongSim实例
  - `table_object`: 桌子对象
  - `grid_size`: 格子大小（默认10.0）
  - `test_blueprint`: 测试物体蓝图（默认棒球）
  - `test_duration`: 测试等待时间（默认2.0秒）
  - `safety_margin`: 安全边距（默认0.0）
  - `print_info`: 是否打印详细信息

**返回值**:

```python
{
    'table_id': 桌子ID,
    'grid_size': 格子大小,
    'table_bounds': {
        'x_min', 'x_max', 
        'y_min', 'y_max', 
        'z_surface',
        'center_x', 'center_y'
    },
    'safe_grids': [
        {
            'id': 格子编号,
            'grid_x': 网格X坐标,
            'grid_y': 网格Y坐标,
            'x_min', 'x_max',
            'y_min', 'y_max',
            'center_x', 'center_y',
            'z': 桌面高度
        },
        ...
    ],
    'total_safe_grids': 安全格子数,
    'total_tested_grids': 测试格子数,
    'timestamp': 时间戳
}
```

**执行流程**:

1.  获取桌子的AABB边界和桌面高度
2.  计算桌子中心点
3.  计算网格范围（从中心向外扩展）
4.  使用BFS（广度优先搜索）从中心格子开始向外扩展测试
      - 对每个格子调用 `test_grid_safety()` 测试安全性
      - 只有当前格子安全，才将相邻格子加入队列
      - 格子超出桌子边界直接标记为不安全
5.  记录所有安全格子的信息
6.  返回完整的网格数据

**BFS扩展方向**: 上下左右四个方向

-----

#### 2\. `test_grid_safety()`

**功能**: 测试单个格子的安全性

**参数**:

  - `ue`: TongSim实例
  - `grid_center_x`: 格子中心X坐标
  - `grid_center_y`: 格子中心Y坐标
  - `table_surface_z`: 桌面高度
  - `table_ground_z`: 桌子底部高度
  - `test_blueprint`: 测试物体蓝图
  - `test_duration`: 测试持续时间（默认2.0秒）
  - `movement_threshold`: 移动阈值（默认5.0）
  - `print_info`: 是否打印详细信息

**返回值**: `bool` (True=安全, False=不安全)

**执行流程**:

1.  在格子中心上方5单位生成测试物体
2.  记录初始位置
3.  等待物理稳定（test\_duration秒）
4.  获取最终位置
5.  进行三项安全检查：
      - **检查1**: 物体是否掉落到地面（比较到地面和桌面的距离）
      - **检查2**: 水平移动距离是否超过阈值
      - **检查3**: Z轴偏离桌面是否超过50单位
6.  删除测试物体
7.  返回安全性结果

-----

#### 3\. `run_table_boundary_measurement()`

**功能**: 遍历所有地图的所有桌子，批量测量边界并生成JSON文件

**参数**:

  - `map_range`: 地图范围（默认0-300）
  - `min_room_area`: 最小房间面积（默认4平方米）
  - `min_table_area`: 最小桌子面积（默认0.4平方米）
  - `grid_size`: 格子大小（默认10.0）
  - `output_dir`: 输出目录（默认`./ownership/table_boundaries`）

**执行流程**:

1.  读取筛选后的场景列表（`selected_scenes.txt`）
2.  创建输出目录
3.  遍历地图范围：
      - 打开地图
      - 获取房间信息
      - 遍历每个房间：
          - 检查房间面积是否符合要求
          - 查询房间内的桌子
          - 遍历每张桌子：
              - 验证桌子面积和长宽比
              - 删除桌子上的所有物品
              - 删除附近的椅子
              - 调用 `measure_table_grid_boundaries()` 测量边界
              - 保存JSON文件到输出目录
4.  输出统计信息（总桌子数、成功数、失败数、成功率）

**输出文件命名**: `{map_name}_{room_name}_table_{table_id}.json`

-----

### JSON文件用途

生成的JSON文件用于后续的物品放置功能（即**阶段二**），主要函数（如 `spawn_items_on_grid_new`）会读取JSON文件中的 `safe_grids` 信息，在安全格子上放置物品。

### 主要依赖 (工具函数)

  - `fix_aabb_bounds()` - 修复AABB边界
  - `get_room_bbox()` - 获取房间边界框
  - `get_room_boundary()` - 获取房间边界信息
  - `get_area()` - 计算面积
  - `validate_table()` - 验证桌子是否符合条件
  - `query_existing_objects_in_room()` - 查询房间内物品
  - `find_objects_near_table()` - 查找桌子附近物品
  - `filter_objects_by_type()` - 按类型筛选物品

-----

## 阶段二：场景生成管线 (`run_pipeline_table_with_grid_items`) 详解

### 一、主函数逻辑

`run_pipeline_table_with_grid_items()` 是基于网格系统的桌面场景生成Pipeline主函数。

#### 主要流程

1.  **初始化**: 加载场景列表、资产信息
2.  **遍历地图**: 逐个打开地图、查找房间和桌子
3.  **加载网格**: 读取桌子的网格JSON数据
4.  **清理环境**: 删除桌子上的原有物品
5.  **生成人物**: 配置并生成人物，放置在桌子周围
6.  **放置物品**: 基于网格系统在桌面放置物品
7.  **生成动作**: 为人物生成随机动作
8.  **创建摄像头**: 生成多视角摄像头
9.  **保存数据**: 拍摄图像并保存场景JSON数据

-----

### 二、配置文件说明

#### 1\. `agent_config.py` - 人物配置

**功能**: 定义人物类型与蓝图的映射关系

**核心数据结构**:

```python
AGENT_BLUEPRINT_MAPPING = {
    'girl': ["SDBP_Aich_AIBabyV7_Shoes", "SDBP_Aich_AIBaby_Lele_Shoes"],
    'boy': ["SDBP_Aich_AIBaby_Tiantian_90"],
    'woman': ["SDBP_Aich_Liyuxia"],
    'grandpa': ["SDBP_Aich_Yeye"],
    'man': ["SDBP_Aich_Zhanghaoran"]
}
```

**工具函数**:

  - `extract_base_agent_id()`: 从完整ID提取基础人物ID
  - `get_agent_trait()`: 根据人物ID获取特性（girl/boy/woman等）

#### 2\. `item_config.py` - 物品配置

**功能**: 定义物品类型、蓝图、属性

**核心数据结构**:

  - `ITEM_BLUEPRINTS`: 物品类型 → 蓝图列表映射
  - `ITEM_PROPERTIES`: 物品属性（旋转、缩放、放置区域等）
  - `AGENT_ITEM_MAPPING`: 人物类型 → 专属物品映射
  - `COMMON_ITEMS`: 所有人都可能拥有的物品
  - `NON_REPEATING_ITEM_TYPES`: 不可重复物品（如computer）
  - `SITTING_ITEM_WEIGHT_BOOST`: 坐姿下的物品权重加成

**物品属性示例**:

```python
'book': {
    'zone_types': ['main', 'frequent', 'infrequent'],  # 可放置区域
    'rotation_z': -90,  # Z轴旋转
    'min_distance': 0.0,  # 距离人物最小距离
    'max_distance': 40.0,  # 距离人物最大距离
    'safe_margin': 5.0  # 安全边距
}
```

#### 3\. `composed_item.py` - 连锁物品配置

**功能**: 定义物品之间的连锁生成规则

**核心数据结构**:

```python
ITEM_CHAIN_RULES = {
    'book': [{
        'chain_item': 'pen',  # 连锁物品
        'probability': 0.6,  # 生成概率
        'direction': 'right',  # 相对人物的方向
        'max_range': 2  # 最大搜索层数
    }]
}
```

**工具函数**:

  - `get_direction_mapping()`: 根据人物站位获取方向映射
  - `get_chain_grids()`: 获取连锁物品可放置的网格列表

-----

### 三、子函数详解

#### 1\. `load_table_grid_json()` - 加载网格数据

**文件**: `item_util.py`

**功能**: 根据地图、房间、桌子ID加载对应的网格JSON文件（由**阶段一**生成）

**参数**:

  - `map_name`: 地图名称（如 "SDBP\_Map\_001"）
  - `room_name`: 房间名称（如 "diningRoom"）
  - `table_id`: 桌子ID
  - `grid_dir`: 网格JSON文件目录

**返回值**: 网格数据字典，包含 `safe_grids`（安全格子列表）

**匹配方式**:

1.  精确匹配: `{map_name}_{room_name}_table_{table_id}.json`
2.  模糊匹配: 搜索包含 `table_id` 的文件

#### 2\. `generate_agent_configuration()` - 生成人物配置

**文件**: `agent_util.py`

**功能**: 生成人物的蓝图、站位、坐姿配置

**优先级**: `agent_blueprints` \> `agent_traits` \> `num_agents` \> 全随机(2-4人)

**参数**:

  - `num_agents`: 人物数量
  - `agent_blueprints`: 指定的人物蓝图列表（最高优先级）
  - `agent_sides`: 指定的人物方位列表
  - `agent_is_sit`: 指定的人物是否坐下列表
  - `agent_traits`: 人物特性列表 ['girl', 'boy', 'woman', 'grandpa', 'man']
  - `side_probabilities`: 方位概率 [front, back, left, right]
  - `sit_probability`: 坐下概率

**返回值**: `(agent_blueprints, agent_sides, agent_is_sit, agent_traits)`

**流程**:

1.  根据优先级确定人物数量和蓝图
2.  生成随机站位（如果未指定）
3.  生成随机坐姿配置（如果未指定）

#### 3\. `generate_and_spawn_agents()` - 生成并放置人物

**文件**: `agent_util.py`

**功能**: 在桌子周围生成人物并放置椅子

**参数**:

  - `ue`: TongSim实例
  - `table_object`: 桌子对象
  - `room_bound`: 房间边界
  - `nearby_objects`: 附近物品列表
  - `agent_blueprints`: 人物蓝图列表
  - `agent_sides`: 人物站位列表
  - `agent_is_sit`: 是否坐下列表
  - `agent_traits`: 人物特性列表
  - `min_distance`: 距桌子最小距离（默认20cm）
  - `max_distance`: 距桌子最大距离（默认50cm）
  - `min_agent_distance`: 人物之间最小距离（默认60cm）
  - `safe_margin`: 安全边距（默认15cm）

**返回值**: `(agents_complete_info, nearby_items_info)`

**流程**:

1.  **确定人物位置**: 根据 `agent_sides` 在桌子四周计算位置
2.  **生成人物实体**: 使用 `spawn_entity` 创建人物
3.  **处理坐姿**:
      - 站立: 直接放置
      - 坐下: 查找附近椅子 → 调整椅子位置 → 执行坐下动作
4.  **椅子调整**: 使用 `_try_sit_on_chair()` 多次尝试调整椅子位置
5.  **碰撞检测**: 确保人物之间、人物与物品之间无重叠
6.  **构建完整信息**: 包含 entity, location, rotation, status, side, trait 等

**椅子调整子流程** (`_try_sit_on_chair()`):

  - 尝试坐下 → 检查位置 → 如果失败则调整椅子 → 重复
  - 最多尝试 `max_chair_adjust_attempts` 次
  - 每次调整移动 `chair_move_step` 距离

#### 4\. `spawn_items_on_grid_new()` - 基于网格放置物品

**文件**: `item_util.py`

**功能**: 使用网格系统在桌面上放置物品

**参数**:

  - `ue`: TongSim实例
  - `table_object`: 桌子对象
  - `agents`: 人物对象列表
  - `grid_data`: 网格数据（从JSON加载）
  - `agent_features_list`: 人物特征列表
  - `max_total_items`: 桌面最大物品总数（默认10）
  - `max_items_per_agent`: 每个人物最多物品数量（默认3）

**返回值**: `(spawned_items, owners_list, features_list)`

**主要流程**:

  * **阶段1: 初始化**

      * 获取 `safe_grids`（安全网格列表）和 `table_surface_z`（桌面高度）

  * **阶段2: 网格划分**

    1.  **找到基准网格** (`find_agent_base_grid`): 为每个人物选择最近的安全网格作为基准。
    2.  **划分统御网格** (`get_agent_controlled_grids`): 从基准网格扩展，使用边界线划分每个人物的“领地”。
    3.  **分区** (`divide_grids_into_zones`): 将每个人的领地再细分为 `main`, `frequent`, `infrequent`, `temporary` 区域。

  * **阶段3: 物品生成主循环**

    1.  **选择人物**: 随机选择一个未达物品上限的人物。
    2.  **选择物品类型** (`select_item_type_for_agent`): 根据人物类型、坐姿（权重加成）、是否重复等规则，加权随机选择一个物品类型。
    3.  **选择网格** (`select_grid_from_zones`): 根据物品属性（如 `zone_types`, `min_distance`）在可用分区中选择一个网格。
    4.  **放置物品** (`_spawn_single_item_for_agent`):
          * **a. 蓝图选择**: 随机选择一个蓝图。
          * **b. 旋转计算** (`calculate_item_rotation`): 计算朝向人物的旋转或随机旋转。
          * **c. 悬空检测** (`check_item_placement_validity`): 在空中（Z+70）生成物品，检查AABB投影是否重叠或超出桌面。
          * **d. 桌面重新生成**: 删除测试物品，在桌面（Z+1）重新生成并开启物理。
          * **e. 落地检测** (`check_item_landing`): 等待1秒，检查物品是否掉落（`distance_to_surface > 40`）。
          * **f. 旋转稳定性检测** (`check_item_rotation_stability`): 检查特定物品（如杯子、电脑）的最终姿态是否稳定（角度差 \< 15°）。
          * **g. `platefood` 特殊处理**: 先放盘子，再在盘子上放食物，并检查是否成功。
    5.  **构建返回信息** (`create_complete_info`): 包含ID, type, location, owner, grid\_id 等。
    6.  **连锁物品生成** (`_spawn_chain_item_for_trigger`):
          * 检查 `ITEM_CHAIN_RULES`，根据概率决定是否生成。
          * 使用 `get_chain_grids()` 查找附近的安全网格。
          * 执行与(4)相同的放置和检测流程。
    7.  **更新状态**: 更新已用网格、物品计数等。

  * **终止条件**: 达到 `max_total_items` 或所有人物达到 `max_items_per_agent` 或尝试次数过多。

#### 5\. `generate_actions_for_all_agents()` - 生成人物动作

**文件**: `action_util.py`

**功能**: 为所有人物生成随机动作（伸手、指向）

**参数**:

  - `agents`: 人物列表
  - `all_spawned_items`: 所有物品列表
  - `item_owners_list`: 物品所有者列表
  - `action_probability`: 执行动作的概率（默认0.7）

**返回值**: 动作统计信息字典

**流程**:

1.  遍历每个人物，根据概率决定是否执行动作。
2.  检查可用动作类型:
      - `action_reach_item()`: 伸手触摸**自己**的物品。
          - 站立: 移动到物品 → 转向 → 伸手。
          - 坐下: 仅在距离 ≤60cm 时直接伸手。
      - `action_point_at_item()`: 指向**任意**物品。
          - 转向物品 → 指向。

#### 6\. 摄像头与数据保存 (camera\_util.py, json\_util.py)

  - `calculate_entities_center()`: 计算所有人物和物品的中心点。
  - `generate_camera_positions()`: 在桌子周围生成多个环绕摄像头位置，并检查遮挡。
  - `generate_top_view_camera_position()`: 生成一个包含所有实体的俯视摄像头。
  - `add_capture_camera()`: 在计算出的位置创建摄像头实体。
  - `capture_and_save_images()`: 遍历所有摄像头，拍摄并保存图像。
  - `add_entities_to_json()`: 将所有实体（人物、物品、相机）的详细信息保存到 `scene_data.json`。

-----

### 四、数据流图

```
Pipeline主流程:
┌─────────────────────────────────────────────────────────────┐
│ 1. 初始化: 加载场景列表、资产信息                          │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. 遍历地图: 打开地图 → 获取房间 → 查找桌子                │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. load_table_grid_json(): 加载网格数据 (来自阶段一)        │
│    返回: {safe_grids: [...], table_bounds: {...}}           │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. 清理: 删除桌上原有物品                                   │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. generate_agent_configuration(): 生成人物配置             │
│    返回: (blueprints, sides, is_sit, traits)                │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. generate_and_spawn_agents(): 生成并放置人物              │
│    → 计算位置 → 生成实体 → 处理坐姿 → 调整椅子             │
│    返回: (agents_complete_info, nearby_items_info)          │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. spawn_items_on_grid_new(): 放置物品                      │
│    ┌──────────────────────────────────────────────────┐    │
│    │ a. 网格划分: find_agent_base_grid()              │    │
│    │              get_agent_controlled_grids()        │    │
│    │              divide_grids_into_zones()           │    │
│    ├──────────────────────────────────────────────────┤    │
│    │ b. 主循环: select_item_type_for_agent()          │    │
│    │           select_grid_from_zones()               │    │
│    │           _spawn_single_item_for_agent()         │    │
│    │             → 悬空检测 → 落地检测 → 旋转检测    │    │
│    │           _spawn_chain_item_for_trigger()        │    │
│    │             → 连锁物品生成                       │    │
│    └──────────────────────────────────────────────────┘    │
│    返回: (spawned_items, owners_list, features_list)        │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 8. generate_actions_for_all_agents(): 生成动作              │
│    → action_reach_item() / action_point_at_item()           │
│    返回: action_stats                                        │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 9. 摄像头: calculate_entities_center()                      │
│           generate_camera_positions()                        │
│           generate_top_view_camera_position()                │
│           add_capture_camera()                               │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 10. capture_and_save_images(): 拍摄图像                     │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 11. add_entities_to_json(): 保存场景数据                    │
│     → 物品、人物、摄像头信息保存到JSON                      │
└─────────────────────────────────────────────────────────────┘
```

-----

### 五、关键数据结构

#### 1\. 网格数据格式 (阶段一输出)

```python
{
    'table_id': 桌子ID,
    'grid_size': 10.0,
    'table_bounds': {...},
    'safe_grids': [
        {
            'id': 1,
            'grid_x': 0,  # 网格坐标
            'grid_y': 0,
            'center_x': 0.0, # 实际世界坐标
            'center_y': 0.0,
            'z': 80.0,
            ...
        },
        ...
    ]
}
```

#### 2\. 人物完整信息格式 (阶段二生成)

```python
{
    'entity': agent对象,
    'id': 'SDBP_Aich_Liyuxia_1_ABC123',
    'base_id': 'SDBP_Aich_Liyuxia',
    'trait': 'woman',
    'location': {'x': 100.0, 'y': 50.0, 'z': 0.0},
    'rotation': {...},
    'status': 'sitting',  # 或 'standing'
    'side': 'front',  # 或 'back', 'left', 'right'
    'chair_id': 'Chair_123',  # 如果坐下
    'base_grid': {...},  # 基准网格
    'controlled_grids': [...],  # 统御网格
    'zones': { 'main': [...], 'frequent': [...], ... }
}
```

#### 3\. 物品完整信息格式 (阶段二生成)

```python
{
    'id': 'BP_Laptop_01_1_XYZ789',
    'base_id': 'BP_Laptop_01',
    'my_type': 'computer',
    'location': {'x': 10.0, 'y': 5.0, 'z': 81.0},
    'rotation': {...},
    'entity_min': Vector3(...),
    'entity_max': Vector3(...),
    'entity': item对象,
    'owner': 'SDBP_Aich_Liyuxia_1_ABC123',
    'grid_id': { 'id': 5, 'grid_x': 1, 'grid_y': 0, ... }
}
```

#### 4\. 动作结果格式 (阶段二生成)

```python
{
    'success': True,
    'action_type': 'reach_item',  # 或 'point_at_item'
    'target_item_id': 'BP_Laptop_01_1_XYZ789',
    'hand_used': 'right',  # 或 'left'
    'distance': 45.5,  # 距离（cm）
    'error': None
}
```

-----

### 六、输出文件 (阶段二)

#### 1\. 场景JSON文件

  * **保存位置**: `{log_dir}/table_scene_map{num}_room_{name}_table{idx}/scene_data.json`
  * **包含内容**:
      * `scene_info`: 地图、房间、桌子信息
      * `objects`: 所有物品信息（包含owner）
      * `agents`: 所有人物信息（包含动作）
      * `cameras`: 所有摄像头信息
      * `timestamps`: 时间戳

#### 2\. 图像文件

  * **保存位置**: 与JSON文件同目录
  * **命名格式**:
      * 普通摄像头: `Camera_0.png`, `Camera_1.png`, ...
      * 俯视摄像头: `TopCamera_0.png`

-----

### 七、注意事项

1.  **网格数据依赖**: 必须先运行 `table_margin.py` 生成网格JSON文件。
2.  **人物数量**: 最少需要2个人物，否则跳过该场景。
3.  **物品计数**: `platefood`（盘子+食物）只计为一个物品。
4.  **连锁物品**: 连锁物品也计入 `max_total_items` 和 `max_items_per_agent`。
5.  **坐姿限制**: 坐下的人物伸手距离限制为60cm。
6.  **资源释放**: 场景生成完成后自动释放所有人物和物品实体。




# 场景重建与修改管线 (Rebuild & Variation Pipelines)

本文档详细说明了 `table_pipline.py` 中用于**批量重建场景**和**生成场景变体 (Variation)** 的两个核心管线（Pipeline）。

这两个管线都依赖于已有的数据，但它们的目的和工作方式有**重大区别**：

1.  **`run_pipeline_rebuild_scenes` (场景重新生成)**:

      * **输入**: 一个 `scenes_list.json` 文件。这个文件只包含场景的**高级参数**（如地图名、房间名、人物位置组合）。
      * **工作方式**: 它会**重新运行**场景*生成*流程。它会重新生成人物、*重新随机放置*物品、重新生成动作。
      * **用途**: 用于根据一组固定的*位置参数*，批量生成*全新*的、随机的场景。

2.  **`run_pipeline_add_agent_variations` (场景修改)**:

      * **输入**: 一个*完整*的 `scene_data.json` 文件。这个文件包含*所有*已保存的实体（人物、椅子、物品）的精确位置、旋转和属性。
      * **工作方式**: 它会**精确重建**JSON中的原始场景，然后在此基础上应用*修改*（如添加/交换人物、改变状态、增减物品、移动物品）。
      * **用途**: 用于对一个*已知*的、*已保存*的场景，生成大量可控的变体。

-----

## 1\. `run_pipeline_rebuild_scenes` (批量重新生成)

此管线用于批量**重新生成**场景。它会读取一个包含多个场景*参数*的列表文件 (`scenes_list.json`)，然后遍历该列表，为每个条目从头开始生成一个全新的场景。

### 函数定义

```python
def run_pipeline_rebuild_scenes(scenes_list_file="./ownership/rebulid_scene/scenes_list.json", 
                                grid_dir="./ownership/table_boundaries",
                                log_dir="./ownership/logs_rebuild", 
                                max_item=5, filters=None, print_info=True):
    """
    从场景列表文件批量重建场景
    
    参考 run_pipeline_table_with_grid_items 的结构，但使用已保存的场景信息
    
    Args:
        scenes_list_file: 场景列表JSON文件路径
        grid_dir: 网格数据目录
        log_dir: 重建结果保存目录
        max_item: 最大物品数量
        filters: 筛选条件（可选），例如:
            {
                'combination_type': 'face_to_face',
                'agent_count': 2,
                'map_name': 'SDBP_Map_001'
            }
        print_info: 是否打印详细信息
    """
```

### 核心依赖

  * `utils.rebuild.load_scenes_list`: 加载 `scenes_list.json`。
  * `utils.rebuild.filter_scenes`: 根据 `filters` 参数筛选场景列表。
  * `utils.rebuild.rebuild_scene_from_info`: **(核心)** 真正执行单个场景重建的函数。

### 执行流程

1.  **加载场景列表**: 调用 `load_scenes_list` 读取 `scenes_list_file` (一个 JSON 文件，通常由 `scan_and_extract_all_scenes` 生成)。
2.  **筛选场景**: (可选) 如果提供了 `filters`，则调用 `filter_scenes` 缩小场景列表范围。
3.  **遍历处理**: 遍历筛选后的 `scenes_list`。
4.  **调用重建**: 对每个 `scene_info`，调用 `rebuild_scene_from_info`。
5.  **`rebuild_scene_from_info` 内部流程**：
    a.  打开 `scene_info` 中指定的地图、房间。
    b.  查找 `table_id` 对应的桌子实体。
    c.  加载该桌子的**网格数据** (`grid_dir`)。
    d.  清空桌面上所有物品。
    e.  **重新生成人物**: 调用 `generate_and_spawn_agents`，使用 `scene_info` 中的 `positions`（如 `['front', 'back']`）和 `agents_info`（如蓝图、坐姿）来*重新*创建人物。
    f.  **重新放置物品**: 调用 `spawn_items_on_grid`（或 `spawn_items_on_grid_new`）在安全网格上*随机*放置*新*物品（最多 `max_item` 个）。
    g.  **重新生成动作**: 调用 `generate_actions_for_all_agents` 为人物生成*新*的随机动作。
    h.  **生成摄像头**: 创建环绕和俯视摄像头。
    i.  **保存数据**: 拍摄图像并保存*新*的 `scene_data.json` 到 `log_dir`。
    j.  **清理**: (可选) `auto_cleanup=True` 会删除所有生成的实体。

-----

## 2\. `run_pipeline_add_agent_variations` (场景修改与变体生成)

此管线用于加载一个**已有的、完整的** `scene_data.json` 文件，**精确重建**该场景，然后对其应用各种**修改**（增/删/改 人物或物品），最后生成一个新的 `scene_data.json`。

这是您用来“改变人与物品”的核心函数。

### 函数定义

```python
def run_pipeline_add_agent_variations(json_file_path, base_output_dir=None, 
                                      enable_add_agent=False, enable_change_status=False, 
                                      enable_swap_blueprints=False, enable_replace_blueprint=False,
                                      enable_change_action=False, enable_change_item_type=False,
                                      item_type_change_counts=None,
                                      adjust_item_count=0,
                                      move_item_count=0,
                                      print_info=True):
    """
    遍历所有可能的参数组合，为场景添加新人物和/或改变人物状态和/或交换/替换人物蓝图和/或改变人物动作和/或改变物品类型和/或增减物品数量和/或移动物品
    
    遍历策略：
    1. swap_agent_blueprints: 遍历所有可能的人物蓝图交换对（可选，与enable_replace_blueprint互斥）
    2. replace_agent_blueprint: 遍历所有可能的人物蓝图替换（可选，与enable_swap_blueprints互斥）
    3. change_agent_status: 遍历所有人物的状态改变（可选）
    4. change_agent_action: 遍历所有人物的动作改变（可选）
    5. change_item_type_count: 遍历所有指定的物品类型修改数量（可选）
    6. move_item_count: 移动物品到其他owner区域（可选）
    7. reference_agent_index: 遍历所有已有人物作为参考（可选）
    8. placement_strategy: 遍历 'face_to_face' 和 'same_side'
    8. new_agent_trait: 遍历所有不重复的蓝图
    
    Args:
        json_file_path: 原始场景JSON文件路径
        base_output_dir: 输出基础目录（可选）
        enable_add_agent: 是否启用添加新人物的遍历（默认False）
        enable_change_status: 是否启用改变人物状态的遍历（默认False）
        enable_swap_blueprints: 是否启用交换人物蓝图的遍历（默认False）
                               ⚠️ 与 enable_replace_blueprint 互斥
        enable_replace_blueprint: 是否启用替换人物蓝图的遍历（默认False）
                                 ⚠️ 与 enable_swap_blueprints 互斥
        enable_change_action: 是否启用改变人物动作的遍历（默认False）
        enable_change_item_type: 是否启用改变物品类型的遍历（默认False）
        item_type_change_counts: 物品类型修改数量列表（可选），例如 [1, 2, 3] 表示遍历修改1个、2个、3个物品
                                如果为None且enable_change_item_type=True，将根据场景中物品数量自动生成
        print_info: 是否打印详细信息
        
    示例：
        # 只添加新人物
        run_pipeline_add_agent_variations(..., enable_add_agent=True)
        
        # 只改变状态
        run_pipeline_add_agent_variations(..., enable_change_status=True)
        
        # 只交换蓝图
        run_pipeline_add_agent_variations(..., enable_swap_blueprints=True)
        
        # 只替换蓝图
        run_pipeline_add_agent_variations(..., enable_replace_blueprint=True)
        
        # 只改变动作
        run_pipeline_add_agent_variations(..., enable_change_action=True)
        
        # 只改变物品类型
        run_pipeline_add_agent_variations(..., enable_change_item_type=True, item_type_change_counts=[1, 2])
        
        # 替换蓝图 + 改变状态 + 改变动作 + 改变物品类型
        run_pipeline_add_agent_variations(..., enable_replace_blueprint=True, enable_change_status=True, 
                                         enable_change_action=True, enable_change_item_type=True,
                                         item_type_change_counts=[1, 2, 3])
        
        # 只重建原场景，不做任何修改
        run_pipeline_add_agent_variations(..., enable_add_agent=False, enable_change_status=False, enable_swap_blueprints=False)
    """
```

### 核心依赖

  * `utils.rebuild.rebuild_and_modify_scene_from_json`: **(核心)** 真正执行单个场景修改的函数。

### 执行流程

1.  **加载父JSON**: 读取 `json_file_path` (一个*完整*的 `scene_data.json`)，获取已有人物、物品等信息。
2.  **生成修改组合**: 根据所有 `enable_...` 标志，生成一个包含所有可能修改组合的巨大迭代列表。
      * 例如，如果 `enable_swap_blueprints=True` (有3个选项) 且 `enable_change_status=True` (有3个选项)，它将生成 3x3=9 种组合进行测试。
3.  **遍历组合**: 遍历所有生成的修改组合。
4.  **调用修改函数**: 对每个组合，调用 `rebuild_and_modify_scene_from_json` 并传入修改参数。

### `rebuild_and_modify_scene_from_json` (核心工作流)

这个子函数是所有修改功能的实现中心。

1.  **精确重建 (`rebuild_exact_scene_from_json`)**:

      * 函数首先会调用 `rebuild_exact_scene_from_json`。
      * 这个辅助函数会打开地图，并严格按照 `scene_data.json` 里的数据，在**精确的坐标**和**旋转**下，重新生成所有的椅子、人物和桌面物品。
      * 它还会重新执行 `json` 中保存的动作（如 `reach_item`）。
      * **结果**: 此时，模拟器中的场景与 `json` 文件完全一致。

2.  **应用修改 (按顺序)**:

      * **物品删除 (`adjust_item_count < 0`)**: 如果 `adjust_item_count` 为负数，它会*首先*从 `json` 数据中随机删除指定数量的物品，这些物品*不会*被重建。
      * **物品类型修改 (`change_item_type_count > 0`)**: 随机选择指定数量的物品，并将其 `base_id` (蓝图) 替换为另一个人偏好的蓝图。`platefood` 会被当作一个整体处理。
      * **蓝图修改 (`swap...` / `replace...`)**: 在重建人物*之前*，修改 `agents_data` 列表中的 `base_id`。
      * **状态修改 (`change_agent_status`)**: 重建人物后，强制指定索引的人物改变状态（坐→站 或 站→坐）。
          * `站→坐`: 人物会查找自己一侧（front/back/left/right）的**可用椅子**并坐下。如果找不到可用椅子，该次修改将**失败**并报错 `no_available_chair`。
          * `坐→站`: 人物会站起来，并释放其占用的椅子（使其变为“可用”）。
      * **物品增加 (`adjust_item_count > 0`)**: 在所有物品重建*之后*，调用 `adjust_table_items_count`，使用网格系统在可用空间中随机添加新物品。
      * **物品移动 (`move_item_count > 0`)**: 在所有物品重建*之后*，调用 `move_items_to_other_owners`，随机选择 `move_item_count` 个物品，将它们移动到另一个人的区域，并更新其 `owner`。
      * **动作修改 (`change_agent_action`)**: 强制指定索引的人物执行新动作（`reach_item`, `point_at_item`, `none`）。如果从 `point` 改为 `reach`，它会自动查找一个该人物拥有的、可触及的物品。
      * **添加新人物 (`add_agent=True`)**: 在所有修改*最后*，调用 `add_agent_to_existing_scene`。
          * 它会根据 `reference_agent_index`（参考人物）和 `placement_strategy`（放置策略）来确定新人物的方位（`front`/`back`/`left`/`right`）。
          * 如果 `should_sit=True`，它会查找该方位的**可用椅子**。如果找不到，添加人物将**失败**。
          * 新人物的蓝图会自动从 `AGENT_BLUEPRINT_MAPPING` 中选择一个*未被*场景中其他人使用的蓝图。

3.  **保存结果**:

      * 所有修改完成后，管线会生成*新*的摄像头，拍摄图像，并保存一个*新*的 `scene_data.json` 到以该修改命名的子文件夹中。
      * 如果任何关键步骤失败（如找不到椅子坐下），该次组合将被标记为 `success: False`，并删除对应的失败文件夹。

### 【重要】注意事项 (您提到的“对不上的地方”)

  * **函数依赖**: `run_pipeline_rebuild_scenes` 和 `run_pipeline_add_agent_variations` 只是“启动器”。真正的逻辑在 `utils/rebuild.py` 文件的 `rebuild_scene_from_info` 和 `rebuild_and_modify_scene_from_json` 函数中。
  * **椅子是关键**: 几乎所有的人物修改（`change_agent_status` 从站到坐，`add_agent` 坐下）都**强依赖**于场景中必须有**可用的椅子**（即 `rebuilt_chairs` 列表中未被 `occupied_chair_ids` 占用的椅子）。如果JSON中的椅子不够，或者位置不佳，很多修改组合都会失败。
  * **动作修改逻辑**: 动作修改 (`change_agent_action`) 是基于索引的，并且会智能地选择目标。例如，从 `point_at_item` 改为 `reach_item` 时，它会*自动*在 `generated_items` 中查找该人物拥有的（`owner` 匹配）且可触及的物品作为新目标。
  * **物品修改**: `adjust_item_count` 和 `move_item_count` 是在 `run_pipeline_add_agent_variations` 中新增的参数，它们依赖于 `utils.item_util.py` 中的 `adjust_table_items_count` 和 `move_items_to_other_owners` 函数。这些函数*同样依赖网格数据* (`grid_data`) 来执行碰撞检测和放置。



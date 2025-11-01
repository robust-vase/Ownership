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

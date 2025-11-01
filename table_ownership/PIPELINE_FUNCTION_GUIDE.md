# run_pipeline_table_with_grid_items 函数详解

## 一、主函数逻辑

`run_pipeline_table_with_grid_items()` 是基于网格系统的桌面场景生成Pipeline主函数。

### 主要流程

1. **初始化**: 加载场景列表、资产信息
2. **遍历地图**: 逐个打开地图、查找房间和桌子
3. **加载网格**: 读取桌子的网格JSON数据
4. **清理环境**: 删除桌子上的原有物品
5. **生成人物**: 配置并生成人物，放置在桌子周围
6. **放置物品**: 基于网格系统在桌面放置物品
7. **生成动作**: 为人物生成随机动作
8. **创建摄像头**: 生成多视角摄像头
9. **保存数据**: 拍摄图像并保存场景JSON数据

---

## 二、配置文件说明

### 1. `agent_config.py` - 人物配置

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

### 2. `item_config.py` - 物品配置

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

### 3. `composed_item.py` - 连锁物品配置

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

---

## 三、子函数详解

### 1. `load_table_grid_json()` - 加载网格数据

**文件**: `item_util.py`

**功能**: 根据地图、房间、桌子ID加载对应的网格JSON文件

**参数**:
- `map_name`: 地图名称（如 "SDBP_Map_001"）
- `room_name`: 房间名称（如 "diningRoom"）
- `table_id`: 桌子ID
- `grid_dir`: 网格JSON文件目录

**返回值**: 网格数据字典，包含 `safe_grids`（安全格子列表）

**匹配方式**:
1. 精确匹配: `{map_name}_{room_name}_table_{table_id}.json`
2. 模糊匹配: 搜索包含 `table_id` 的文件

---

### 2. `generate_agent_configuration()` - 生成人物配置

**文件**: `agent_util.py`

**功能**: 生成人物的蓝图、站位、坐姿配置

**优先级**: `agent_blueprints` > `agent_traits` > `num_agents` > 全随机(2-4人)

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
1. 根据优先级确定人物数量和蓝图
2. 生成随机站位（如果未指定）
3. 生成随机坐姿配置（如果未指定）

---

### 3. `generate_and_spawn_agents()` - 生成并放置人物

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
1. **确定人物位置**: 根据 `agent_sides` 在桌子四周计算位置
2. **生成人物实体**: 使用 `spawn_entity` 创建人物
3. **处理坐姿**:
   - 站立: 直接放置
   - 坐下: 查找附近椅子 → 调整椅子位置 → 执行坐下动作
4. **椅子调整**: 使用 `_try_sit_on_chair()` 多次尝试调整椅子位置
5. **碰撞检测**: 确保人物之间、人物与物品之间无重叠
6. **构建完整信息**: 包含 entity, location, rotation, status, side, trait 等

**椅子调整子流程** (`_try_sit_on_chair()`):
- 尝试坐下 → 检查位置 → 如果失败则调整椅子 → 重复
- 最多尝试 `max_chair_adjust_attempts` 次
- 每次调整移动 `chair_move_step` 距离

---

### 4. `spawn_items_on_grid_new()` - 基于网格放置物品

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

#### 阶段1: 初始化
- 获取 `safe_grids`（安全网格列表）
- 获取 `table_surface_z`（桌面高度）
- 读取 `agent_features_list` 获取人物状态（sitting/standing）

#### 阶段2: 网格划分
1. **找到基准网格** (`find_agent_base_grid`):
   - 计算每个人物到所有网格的距离
   - 选择最近的网格作为基准

2. **划分统御网格** (`get_agent_controlled_grids`):
   - 从基准网格向外扩展
   - 使用边界线（过桌子中心、垂直于基准线）划分区域
   - 只选择与基准网格在边界线同侧的网格
   - 曼哈顿距离不超过 `control_radius`

3. **分区** (`divide_grids_into_zones`):
   - **main区**: 基准线两侧各1.5格（15单位）范围内
   - **frequent区**: 人物右手侧（常用区域）
   - **infrequent区**: 人物左手侧（不常用区域）
   - **temporary区**: 桌子边缘最近的3-5个网格

#### 阶段3: 物品生成主循环

对每个尝试：

1. **选择人物**: 随机选择未达到物品上限的人物

2. **选择物品类型** (`select_item_type_for_agent`):
   - 根据人物类型（girl/boy/woman等）选择可能的物品
   - 过滤已使用的非重复物品
   - 坐姿下特定物品权重加成
   - 使用加权随机选择

3. **选择网格** (`select_grid_from_zones`):
   - 根据物品属性选择可用分区
   - 过滤已使用的网格
   - 使用基准线投影过滤距离（min_distance ~ max_distance）

4. **放置物品** (`_spawn_single_item_for_agent`):
   
   **a. 蓝图选择**:
   - 普通物品: 从 `ITEM_BLUEPRINTS` 中选择
   - platefood: 需要 plate（盘子）和 food（食物）两个蓝图
   - 过滤已使用的非重复蓝图

   **b. 位置和旋转计算**:
   - 位置: 网格中心，先抬高70单位（用于碰撞检测）
   - 旋转: `calculate_item_rotation()`
     - 如果 `rotation_z=360`，使用随机旋转
     - 计算朝向人物的旋转
     - 组合 Z→Y→X 轴旋转

   **c. 悬空检测** (`check_item_placement_validity`):
   - 将抬高的物品AABB投影到桌面
   - 检查与其他物品是否重叠
   - 检查是否完全在桌子边界内
   - 失败则销毁物品，尝试下一个网格

   **d. 桌面重新生成**:
   - 删除高处的测试物品
   - 在桌面 `table_surface_z + 1.0` 重新生成
   - 启用物理模拟（`is_simulating_physics=True`）

   **e. 落地检测** (`check_item_landing`):
   - 等待1秒让物理稳定
   - 比较物品到地面和桌面的距离
   - 如果 `distance_to_surface > 40` 则失败

   **f. 旋转稳定性检测** (`check_item_rotation_stability`):
   - 仅检查特定物品: drink, milk, wine, computer, cup
   - 计算当前旋转与期望旋转的四元数角度差
   - 如果角度差 > 15° 则失败

   **g. platefood特殊处理**:
   - 在 plate 上方10单位生成 food
   - 等待1.5秒让 food 落到 plate 上
   - 检查 food 是否成功落在 plate 上
   - 失败则同时删除 plate 和 food

5. **构建返回信息** (`create_complete_info`):
   ```python
   {
       'id': 物品ID,
       'base_id': 基础蓝图ID,
       'my_type': 物品类型,
       'location': {x, y, z},
       'rotation': {x, y, z, w},
       'entity_min': AABB最小点,
       'entity_max': AABB最大点,
       'entity': 实体对象,
       'owner': 所有者ID,
       'grid_id': 网格字典
   }
   ```

6. **连锁物品生成** (`_spawn_chain_item_for_trigger`):
   - 检查 `ITEM_CHAIN_RULES` 是否有连锁规则
   - 根据概率决定是否生成
   - 使用 `get_chain_grids()` 获取候选网格（支持层级浮动）
   - 使用相同的放置流程（旋转、悬空、落地、稳定性检测）
   - platefood连锁也支持 plate + food

7. **更新状态**:
   - 添加到 `spawned_items`, `owners_list`, `features_list`
   - 更新 `used_grids`, `used_blueprints`, `used_item_types`
   - 更新 `agent_item_count`, `total_item_count`
   - platefood只计数一次

#### 终止条件:
- 达到 `max_total_items`
- 所有人物达到 `max_items_per_agent`
- 尝试次数超过 `max_total_items * 100`

---

### 5. `generate_actions_for_all_agents()` - 生成人物动作

**文件**: `action_util.py`

**功能**: 为所有人物生成随机动作

**参数**:
- `agents`: 人物列表
- `agent_features_list`: 人物特征列表
- `all_spawned_items`: 所有物品列表
- `item_owners_list`: 物品所有者列表
- `item_features_list`: 物品特征列表
- `action_probability`: 执行动作的概率（默认0.7）

**返回值**: 动作统计信息字典

**流程**:
1. 对每个人物调用 `generate_random_action_for_agent()`
2. 根据概率决定是否执行动作
3. 检查可用动作类型:
   - **reach_item**: 伸手触摸自己的物品
   - **point_at_item**: 指向任意物品

**动作执行子流程**:

#### `action_reach_item()` - 伸手触摸物品
1. 判断物品在左边还是右边（`determine_hand_side`）
2. 根据人物状态执行:
   - **站立**: 移动到物品 → 转向物品 → 伸手
   - **坐下**: 检查距离 → 如果 ≤60cm 直接伸手（不移动）
3. 返回动作结果（包含 hand_used, distance 等信息）

#### `action_point_at_item()` - 指向物品
1. 判断物品在左边还是右边
2. 转向物品
3. 执行指向动作
4. 返回动作结果

---

### 6. `calculate_entities_center()` - 计算实体中心

**文件**: `camera_util.py`

**功能**: 计算所有人物和物品的中心位置

**参数**:
- `agents`: 人物列表
- `items`: 物品列表

**返回值**: 中心位置 `Vector3(x, y, z)`

**流程**:
1. 获取所有人物的位置
2. 获取所有物品的位置
3. 计算平均位置

---

### 7. `generate_camera_positions()` - 生成摄像头位置

**文件**: `camera_util.py`

**功能**: 在桌子周围生成多个摄像头位置

**参数**:
- `ue`: TongSim实例
- `room_bound`: 房间边界
- `target_object`: 目标对象（桌子）
- `center_location`: 中心位置
- `distance_range`: 距离范围 [min, max]
- `height`: 高度范围 [min, max]
- `agents`: 人物列表
- `num_cameras`: 摄像头数量

**返回值**: 摄像头位置列表

**流程**:
1. 随机生成候选位置（环绕桌子）
2. 检查是否在房间内
3. 检查视线是否被人物遮挡
4. 选择最佳位置

---

### 8. `generate_top_view_camera_position()` - 生成俯视摄像头

**文件**: `camera_util.py`

**功能**: 生成能够看到所有人物和物品的俯视摄像头位置

**参数**:
- `room_bound`: 房间边界
- `agents`: 人物列表
- `items`: 物品列表
- `margin_factor`: 边距因子（默认1.5）
- `safe_margin`: 安全边距（默认30）

**返回值**: 俯视摄像头位置

**流程**:
1. 计算所有实体的边界框
2. 计算中心位置
3. 根据边界框大小和边距因子计算高度
4. 确保在房间高度范围内

---

### 9. `add_capture_camera()` - 创建摄像头

**文件**: `camera_util.py`

**功能**: 创建摄像头实体

**参数**:
- `ue`: TongSim实例
- `camera_positions`: 摄像头位置列表
- `center_location`: 中心位置
- `target_obj`: 目标对象
- `camera_name_prefix`: 摄像头名称前缀

**返回值**: 摄像头对象列表

**流程**:
1. 遍历所有位置
2. 计算朝向（看向中心位置）
3. 使用 `spawn_entity` 创建摄像头
4. 返回摄像头列表

---

### 10. `capture_and_save_images()` - 拍摄图像

**文件**: `camera_util.py`

**功能**: 使用摄像头拍摄图像并保存

**参数**:
- `cameras`: 摄像头列表
- `save_dir`: 保存目录
- `delay_before_capture`: 拍摄前延迟（默认0.01秒）

**返回值**: 保存的图像路径字典

**流程**:
1. 遍历所有摄像头
2. 切换到摄像头视角
3. 等待延迟时间
4. 拍摄图像
5. 保存到文件

---

### 11. `add_entities_to_json()` - 保存实体到JSON

**文件**: `json_util.py`

**功能**: 将实体信息添加到JSON文件

**参数**:
- `json_file_path`: JSON文件路径
- `entities`: 实体对象列表
- `entity_type`: 实体类型（'object', 'agent', 'camera'）
- `owner`: 所有者信息（可选）
- `features`: 统一特征信息（可选）
- `features_list`: 每个实体的特征列表（可选）
- `auto_detect_asset_type`: 是否自动检测资产类型

**返回值**: 是否成功

**流程**:
1. 读取现有JSON文件
2. 遍历实体列表，提取信息:
   - id, location, rotation
   - AABB边界（物品）
   - 资产类型（从 `objects_info.json` 加载）
   - 所有者、特征信息
3. 添加到对应的列表（objects/agents/cameras）
4. 保存JSON文件

---

## 四、数据流图

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
│ 3. load_table_grid_json(): 加载网格数据                     │
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

---

## 五、关键数据结构

### 1. 网格数据格式

```python
{
    'table_id': 桌子ID,
    'grid_size': 10.0,  # 格子大小
    'table_bounds': {
        'x_min': -100.0,
        'x_max': 100.0,
        'y_min': -50.0,
        'y_max': 50.0,
        'z_surface': 80.0,
        'center_x': 0.0,
        'center_y': 0.0
    },
    'safe_grids': [
        {
            'id': 1,
            'grid_x': 0,  # 网格坐标
            'grid_y': 0,
            'x_min': -5.0,  # 实际坐标
            'x_max': 5.0,
            'y_min': -5.0,
            'y_max': 5.0,
            'center_x': 0.0,
            'center_y': 0.0,
            'z': 80.0
        },
        ...
    ]
}
```

### 2. 人物完整信息格式

```python
{
    'entity': agent对象,
    'id': 'SDBP_Aich_Liyuxia_1_ABC123',
    'base_id': 'SDBP_Aich_Liyuxia',
    'trait': 'woman',
    'location': {'x': 100.0, 'y': 50.0, 'z': 0.0},
    'rotation': {'x': 0.0, 'y': 0.0, 'z': 0.0, 'w': 1.0},
    'status': 'sitting',  # 或 'standing'
    'side': 'front',  # 或 'back', 'left', 'right'
    'chair_id': 'Chair_123',  # 如果坐下
    'base_grid': {...},  # 基准网格
    'controlled_grids': [...],  # 统御网格
    'zones': {  # 分区
        'main': [...],
        'frequent': [...],
        'infrequent': [...],
        'temporary': [...]
    }
}
```

### 3. 物品完整信息格式

```python
{
    'id': 'BP_Laptop_01_1_XYZ789',
    'base_id': 'BP_Laptop_01',
    'my_type': 'computer',
    'location': {'x': 10.0, 'y': 5.0, 'z': 81.0},
    'rotation': {'x': 0.0, 'y': 0.0, 'z': -90.0, 'w': 0.707},
    'entity_min': Vector3(-20, -15, 80),
    'entity_max': Vector3(20, 15, 85),
    'entity_size': Vector3(0.7, 0.7, 0.7),
    'entity': item对象,
    'owner': 'SDBP_Aich_Liyuxia_1_ABC123',
    'grid_id': {  # 所在网格
        'id': 5,
        'grid_x': 1,
        'grid_y': 0,
        'center_x': 10.0,
        'center_y': 0.0
    }
}
```

### 4. 动作结果格式

```python
{
    'success': True,
    'action_type': 'reach_item',  # 或 'point_at_item'
    'target_item_id': 'BP_Laptop_01_1_XYZ789',
    'hand_used': 'right',  # 或 'left'
    'distance': 45.5,  # 距离（cm）
    'error': None  # 如果失败则包含错误信息
}
```

---

## 六、使用示例

```python
# 基本用法
run_pipeline_table_with_grid_items(
    map_range=range(1, 10),
    num_agents=2,
    agent_sides=['front', 'back'],
    max_item=9
)

# 完整配置
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

---

## 七、输出文件

### 1. 场景JSON文件

保存位置: `{log_dir}/table_scene_map{num}_room_{name}_table{idx}/scene_data.json`

包含内容:
- `scene_info`: 地图、房间、桌子信息
- `objects`: 所有物品信息（包含owner）
- `agents`: 所有人物信息（包含动作）
- `cameras`: 所有摄像头信息
- `timestamps`: 时间戳

### 2. 图像文件

保存位置: 与JSON文件同目录

命名格式:
- 普通摄像头: `Camera_0.png`, `Camera_1.png`, ...
- 俯视摄像头: `TopCamera_0.png`

---

## 八、注意事项

1. **网格数据依赖**: 必须先运行 `table_margin.py` 生成网格JSON文件
2. **人物数量**: 最少需要2个人物，否则跳过该场景
3. **物品计数**: platefood（盘子+食物）只计数一次
4. **连锁物品**: 连锁物品也计入 `max_total_items` 和 `max_items_per_agent`
5. **坐姿限制**: 坐下的人物伸手距离限制为60cm
6. **资源释放**: 场景生成完成后自动释放所有人物和物品实体

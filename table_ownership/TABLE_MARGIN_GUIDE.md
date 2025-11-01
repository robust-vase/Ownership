# table_margin.py 函数说明

## 功能概述

生成桌子的边界网格划分JSON文件，记录桌面的安全可用区域。

---

## 主要函数

### 1. `measure_table_grid_boundaries()`

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

1. 获取桌子的AABB边界和桌面高度
2. 计算桌子中心点
3. 计算网格范围（从中心向外扩展）
4. 使用BFS（广度优先搜索）从中心格子开始向外扩展测试
   - 对每个格子调用 `test_grid_safety()` 测试安全性
   - 只有当前格子安全，才将相邻格子加入队列
   - 格子超出桌子边界直接标记为不安全
5. 记录所有安全格子的信息
6. 返回完整的网格数据

**BFS扩展方向**: 上下左右四个方向

---

### 2. `test_grid_safety()`

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

1. 在格子中心上方5单位生成测试物体
2. 记录初始位置
3. 等待物理稳定（test_duration秒）
4. 获取最终位置
5. 进行三项安全检查：
   - **检查1**: 物体是否掉落到地面（比较到地面和桌面的距离）
   - **检查2**: 水平移动距离是否超过阈值
   - **检查3**: Z轴偏离桌面是否超过50单位
6. 删除测试物体
7. 返回安全性结果

---

### 3. `run_table_boundary_measurement()`

**功能**: 遍历所有地图的所有桌子，批量测量边界并生成JSON文件

**参数**:
- `map_range`: 地图范围（默认0-300）
- `min_room_area`: 最小房间面积（默认4平方米）
- `min_table_area`: 最小桌子面积（默认0.4平方米）
- `grid_size`: 格子大小（默认10.0）
- `output_dir`: 输出目录（默认"./ownership/table_boundaries"）

**执行流程**:

1. 读取筛选后的场景列表（`selected_scenes.txt`）
2. 创建输出目录
3. 遍历地图范围：
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
4. 输出统计信息（总桌子数、成功数、失败数、成功率）

**输出文件命名**: `{map_name}_{room_name}_table_{table_id}.json`

---

## JSON文件用途

生成的JSON文件用于后续的物品放置功能：
- `spawn_items_on_grid()` - 基于网格放置物品
- `spawn_items_on_grid_new()` - 使用子函数的重构版本

这些函数会读取JSON文件中的 `safe_grids` 信息，在安全格子上放置物品。

---

## 主要依赖

**工具函数**:
- `fix_aabb_bounds()` - 修复AABB边界
- `get_room_bbox()` - 获取房间边界框
- `get_room_boundary()` - 获取房间边界信息
- `get_area()` - 计算面积
- `validate_table()` - 验证桌子是否符合条件
- `query_existing_objects_in_room()` - 查询房间内物品
- `find_objects_near_table()` - 查找桌子附近物品
- `filter_objects_by_type()` - 按类型筛选物品

---

## 使用示例

```python
# 测试单个地图的所有桌子
run_table_boundary_measurement(
    map_range=range(1, 10),
    grid_size=10.0
)

# 测试所有地图（1-300）
run_table_boundary_measurement(
    map_range=range(1, 300),
    grid_size=10.0
)
```

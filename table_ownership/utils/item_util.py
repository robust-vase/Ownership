import tongsim as ts
import random
import math
import time
import json
import os
import glob

from configs.agent_config import get_agent_trait
from configs.item_config import (
    ITEM_BLUEPRINTS as item_blueprints,
    ITEM_PROPERTIES as item_properties,
    AGENT_ITEM_MAPPING as agent_item_mapping,
    COMMON_ITEMS as common_items,
    NON_REPEATING_ITEM_TYPES as non_repeating_item_types,
    SITTING_ITEM_WEIGHT_BOOST as sitting_item_weight_boost,
    REPEATABLE_BLUEPRINTS as repeatable_blueprints
)
from configs.composed_item import (
    ITEM_CHAIN_RULES,
    get_chain_grids
)

# Import utility functions from other_util.py
from .other_util import (
    get_object_aabb,
    check_item_overlap,
    is_bbox_contained,
    determine_object_side
)

from .entity_util import (
    get_blueprint_from_entity_id
)

from .orientation_util import (
    look_at_rotation,
    quaternion_angle_difference
)   

# ============== 旋转计算辅助函数 ==============
def create_axis_rotation(angle_degrees, axis):
    """
    创建绕指定轴旋转的四元数
    
    Args:
        angle_degrees: 旋转角度（度）
        axis: 旋转轴 ('x', 'y', 或 'z')
    
    Returns:
        ts.Quaternion: 旋转四元数
    """
    angle_rad = math.radians(angle_degrees) / 2
    if axis == 'x':
        return ts.Quaternion(
            math.cos(angle_rad),  # w
            math.sin(angle_rad),  # x
            0,                    # y
            0                     # z
        )
    elif axis == 'y':
        return ts.Quaternion(
            math.cos(angle_rad),  # w
            0,                    # x
            math.sin(angle_rad),  # y
            0                     # z
        )
    elif axis == 'z':
        return ts.Quaternion(
            math.cos(angle_rad),  # w
            0,                    # x
            0,                    # y
            math.sin(angle_rad)   # z
        )
    else:
        # 默认返回单位四元数（无旋转）
        return ts.Quaternion(1, 0, 0, 0)

# ============== 几何计算辅助函数 ==============
"""
这些函数封装了常用的几何计算操作，用于处理基于直线、垂线和投影的空间关系判断。

核心概念：
1. 基准线（Baseline）：从base_grid中点到桌子中心的连线，用于确定方向
2. 边界线（Boundary）：过桌子中心、垂直于基准线的垂线，用于划分区域
3. 投影距离（Projection）：点在基准线方向上的投影，用于距离判断
4. 有向距离（Signed Distance）：点到直线的带符号距离，用于判断在直线的哪一侧

主要应用：
- get_agent_controlled_grids: 使用边界线判断网格是否在agent控制范围内
- divide_grids_into_zones: 使用平行线划分main/frequent/infrequent分区
- filter_grids_by_distance: 使用投影距离筛选满足min/max距离要求的网格
"""

def get_perpendicular_vector(dir_x, dir_y):
    """
    获取垂直向量（逆时针旋转90度）
    
    Args:
        dir_x: 原向量X分量
        dir_y: 原向量Y分量
    
    Returns:
        tuple: (perp_x, perp_y) 垂直向量
    """
    return -dir_y, dir_x


def point_to_line_signed_distance(px, py, line_point_x, line_point_y, line_dir_x, line_dir_y):
    """
    计算点到直线的有向距离
    
    直线定义：过点(line_point_x, line_point_y)，方向为(line_dir_x, line_dir_y)
    
    Args:
        px: 点的X坐标
        py: 点的Y坐标
        line_point_x: 直线上一点的X坐标
        line_point_y: 直线上一点的Y坐标
        line_dir_x: 直线方向向量的X分量（应该是归一化的）
        line_dir_y: 直线方向向量的Y分量（应该是归一化的）
    
    Returns:
        float: 有向距离，正负表示在直线的不同侧
    """
    vec_x = px - line_point_x
    vec_y = py - line_point_y
    # 叉积：vec × dir
    cross_product = vec_x * line_dir_y - vec_y * line_dir_x
    return cross_product


def calculate_baseline_to_table_center(base_center_x, base_center_y, table_object):
    """
    计算从基准点到桌子中心的基准线
    
    Args:
        base_center_x: 基准点X坐标
        base_center_y: 基准点Y坐标
        table_object: 桌子对象
    
    Returns:
        tuple: (dir_x_norm, dir_y_norm, dir_length, table_center_x, table_center_y)
               归一化方向向量、原始长度、桌子中心坐标
    """
    
    table_min, table_max = get_object_aabb(table_object)
    table_center_x = (table_min.x + table_max.x) / 2
    table_center_y = (table_min.y + table_max.y) / 2
    

    dir_x = table_center_x - base_center_x
    dir_y = table_center_y - base_center_y
    dir_length = math.sqrt(dir_x ** 2 + dir_y ** 2)
    
    if dir_length < 0.001:
        # 基准点就在桌子中心
        return 0.0, 0.0, 0.0, table_center_x, table_center_y
    
    dir_x_norm = dir_x / dir_length
    dir_y_norm = dir_y / dir_length
    
    return dir_x_norm, dir_y_norm, dir_length, table_center_x, table_center_y


def filter_grids_by_distance(grids, base_center_x, base_center_y, dir_x_norm, dir_y_norm, min_distance, max_distance):
    """
    基于距离限制过滤网格（使用投影方法）
    
    在从base_grid到桌子中心的方向上，选择投影距离在[min_distance, max_distance]范围内的网格
    
    Args:
        grids: 待过滤的网格列表
        base_center_x: 基准点X坐标
        base_center_y: 基准点Y坐标
        dir_x_norm: 归一化方向向量的X分量
        dir_y_norm: 归一化方向向量的Y分量
        min_distance: 最小距离
        max_distance: 最大距离
    
    Returns:
        list: 满足距离要求的网格列表
    """
    filtered_grids = []
    
    for grid in grids:
        grid_center_x = grid['center_x']
        grid_center_y = grid['center_y']
        
        # 计算网格中心沿方向向量的投影距离
        vec_x = grid_center_x - base_center_x
        vec_y = grid_center_y - base_center_y
        # 点积：投影到方向向量上
        grid_distance = vec_x * dir_x_norm + vec_y * dir_y_norm
        
        # 检查是否在[min_distance, max_distance]范围内
        if min_distance <= grid_distance <= max_distance:
            filtered_grids.append(grid)
    
    return filtered_grids


# ============== 测试和调试函数 ==============
def visualize_agent_zones(ue, agents, agent_grids, table_surface_z, print_info=False):
    """
    可视化每个人物的分区网格（使用不同颜色的球体标记）
    
    用于调试和验证分区逻辑是否正确
    
    Args:
        ue: TongSim实例
        agents: 人物对象列表
        agent_grids: 人物网格信息字典 {agent: {'base_grid', 'controlled_grids', 'zones', 'type'}}
        table_surface_z: 桌面高度
        print_info: 是否打印详细信息
    """
    
    # 定义不同分区使用的测试蓝图
    zone_blueprints = {
        'main': 'BP_Ball_BaseBall_ver2',        # 主区域 - 棒球ver2
        'frequent': 'BP_Ball_BaseBall_ver1',    # 常用区域 - 棒球ver1
        'infrequent': 'BP_Ball_BaseBall_ver3',  # 不常用区域 - 棒球ver3
        'temporary': 'BP_Base_Decoration_BlueBall'  # 临时区域 - 篮球（优先显示）
    }
    
    print("\n" + "="*60)
    print("开始可视化人物分区网格")
    print("="*60)
    
    for agent in agents:
        if agent not in agent_grids:
            print(f"[SKIP] 人物 {agent.id} 没有网格信息")
            continue
        
        agent_info = agent_grids[agent]
        agent_type = agent_info['type']
        zones = agent_info['zones']
        
        print(f"\n{'='*60}")
        print(f"人物: {agent.id} ({agent_type})")
        print(f"{'='*60}")
        
        # 存储本次生成的测试球体
        test_balls = []
        
        # 创建一个集合记录已经可视化的网格（优先temporary）
        visualized_grid_ids = set()
        
        # 按优先级顺序绘制：temporary > main > frequent > infrequent
        zone_order = ['temporary', 'main', 'frequent', 'infrequent']
        
        for zone_name in zone_order:
            zone_grids = zones.get(zone_name, [])
            if not zone_grids:
                print(f"  [{zone_name}] 无网格")
                continue
            
            blueprint = zone_blueprints[zone_name]
            
            # 过滤掉已经可视化的网格（除了temporary，它总是显示）
            if zone_name == 'temporary':
                grids_to_visualize = zone_grids
            else:
                grids_to_visualize = [g for g in zone_grids if g['id'] not in visualized_grid_ids]
            
            if not grids_to_visualize:
                print(f"  [{zone_name}] {len(zone_grids)}个网格（已被其他分区覆盖）")
                continue
            
            print(f"  [{zone_name}] {len(grids_to_visualize)}个网格 - 使用 {blueprint}")
            
            # 在每个网格中心生成测试球体
            for grid in grids_to_visualize:
                grid_center_x = grid['center_x']
                grid_center_y = grid['center_y']
                grid_x = grid['grid_x']
                grid_y = grid['grid_y']
                
                # 在网格中心上方生成球体
                spawn_location = ts.Vector3(grid_center_x, grid_center_y, table_surface_z + 5.0)
                
                try:
                    test_ball = ue.spawn_entity(
                        entity_type=ts.BaseObjectEntity,
                        blueprint=blueprint,
                        location=spawn_location,
                        is_simulating_physics=True,
                        scale=ts.Vector3(0.5, 0.5, 0.5),  # 缩小球体以便观察
                        quat=None
                    )
                    test_balls.append(test_ball)
                    
                    # 标记该网格已可视化
                    visualized_grid_ids.add(grid['id'])
                    
                    if print_info:
                        print(f"    网格({grid_x}, {grid_y}) @ ({grid_center_x:.1f}, {grid_center_y:.1f})")
                
                except Exception as e:
                    print(f"    [ERROR] 生成测试球失败: {e}")
        
        # 等待物理稳定
        time.sleep(1.0)
        
        # 打印统计信息
        print(f"\n  生成测试球体总数: {len(test_balls)}")
        print(f"  分区统计:")
        print(f"    - main: {len(zones['main'])} 个网格")
        print(f"    - frequent: {len(zones['frequent'])} 个网格")
        print(f"    - infrequent: {len(zones['infrequent'])} 个网格")
        print(f"    - temporary: {len(zones['temporary'])} 个网格")
        
        # 检查重叠情况
        temporary_ids = set(g['id'] for g in zones['temporary'])
        main_ids = set(g['id'] for g in zones['main'])
        overlap_count = len(temporary_ids & main_ids)
        if overlap_count > 0:
            print(f"  注意: temporary与main有 {overlap_count} 个网格重叠（显示为temporary）")
        
        # 等待用户按回车键继续
        print(f"\n  按回车键删除测试球体并继续下一个人物...")
        input()
        
        # 删除所有测试球体
        deleted_count = 0
        for test_ball in test_balls:
            try:
                ue.destroy_entity(test_ball.id)
                deleted_count += 1
            except Exception as e:
                print(f"    [WARNING] 删除球体 {test_ball.id} 失败: {e}")
        
        print(f"  已删除 {deleted_count}/{len(test_balls)} 个测试球体")
    
    print(f"\n{'='*60}")
    print("所有人物分区可视化完成")
    print(f"{'='*60}\n")



# ============== 基于网格放置物品的功能 ==============
# 加载对应的网格JSON文件
def load_table_grid_json(map_name, room_name, table_id, grid_dir="./ownership/table_boundaries"):
    """
    根据场景名称、房间名称和桌子ID加载对应的网格JSON文件
    
    支持两种匹配方式：
    1. 精确匹配：{map_name}_{room_name}_table_{table_id}.json
    2. 模糊匹配：通过table_id在所有文件中查找
    
    Args:
        map_name: 地图名称，如 "SDBP_Map_001"
        room_name: 房间名称，如 "diningRoom"
        table_id: 桌子ID
        grid_dir: 网格JSON文件目录
    
    Returns:
        dict: 网格数据，包含safe_grids等信息，如果文件不存在返回None
    """
    # 方法1: 精确匹配（包含map_name）
    # 文件名格式：{map_name}_{room_name}_table_{table_id}.json
    pattern_exact = f"{map_name}_{room_name}_table_{table_id}.json"
    json_path_exact = os.path.join(grid_dir, pattern_exact)
    
    if os.path.exists(json_path_exact):
        try:
            with open(json_path_exact, 'r', encoding='utf-8') as f:
                grid_data = json.load(f)
            print(f"[SUCCESS] 加载网格文件（精确匹配）: {pattern_exact}")
            return grid_data
        except Exception as e:
            print(f"[ERROR] 加载网格JSON文件失败: {e}")
            return None
    
    # 方法2: 模糊匹配（只使用table_id）
    # 在目录中搜索包含table_id的文件
    print(f"[INFO] 精确匹配失败，尝试模糊匹配: table_id={table_id}")
    
    # 列出目录中所有JSON文件
    all_json_files = glob.glob(os.path.join(grid_dir, "*.json"))
    
    # 查找文件名中包含table_id的文件
    matched_files = []
    for json_file in all_json_files:
        filename = os.path.basename(json_file)
        # 检查文件名是否包含 table_{table_id}
        if f"table_{table_id}" in filename:
            matched_files.append(json_file)
    
    if not matched_files:
        print(f"[WARNING] 未找到包含 table_id '{table_id}' 的网格JSON文件")
        print(f"[INFO] 搜索目录: {grid_dir}")
        print(f"[INFO] 搜索模式: *table_{table_id}*.json")
        return None
    
    # 如果找到多个匹配文件，尝试进一步筛选
    if len(matched_files) > 1:
        # 优先选择同时匹配map_name和room_name的文件
        for json_file in matched_files:
            filename = os.path.basename(json_file)
            if map_name in filename and room_name in filename:
                print(f"[SUCCESS] 加载网格文件（模糊匹配-优先）: {os.path.basename(json_file)}")
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        grid_data = json.load(f)
                    return grid_data
                except Exception as e:
                    print(f"[ERROR] 加载网格JSON文件失败: {e}")
                    continue
        
        # 如果没有同时匹配的，使用第一个找到的
        print(f"[WARNING] 找到 {len(matched_files)} 个匹配文件，使用第一个: {os.path.basename(matched_files[0])}")
    
    # 加载找到的文件
    try:
        with open(matched_files[0], 'r', encoding='utf-8') as f:
            grid_data = json.load(f)
        print(f"[SUCCESS] 加载网格文件（模糊匹配）: {os.path.basename(matched_files[0])}")
        return grid_data
    except Exception as e:
        print(f"[ERROR] 加载网格JSON文件失败: {e}")
        return None

# 找到离人物最近的网格作为基准网格
def find_agent_base_grid(agent, safe_grids):
    """
    找到离人物最近的网格作为基准网格
    
    Args:
        agent: 人物对象
        safe_grids: 安全网格列表
    
    Returns:
        dict: 基准网格信息，如果没有找到返回None
    """
    if not safe_grids:
        return None
    
    agent_pos = agent.get_location()
    agent_x, agent_y = agent_pos.x, agent_pos.y
    
    min_distance = float('inf')
    base_grid = None
    
    for grid in safe_grids:
        grid_center_x = grid['center_x']
        grid_center_y = grid['center_y']
        
        # 计算欧氏距离
        distance = math.sqrt(
            (agent_x - grid_center_x) ** 2 + 
            (agent_y - grid_center_y) ** 2
        )
        
        if distance < min_distance:
            min_distance = distance
            base_grid = grid
    
    return base_grid

# 获取人物统御的所有网格
def get_agent_controlled_grids(base_grid, safe_grids, agent, table_object, control_radius=5):
    """
    获取人物统御的所有网格
    
    使用几何方法：
    1. 计算从base_grid中点到桌子中点的连线（基准线）
    2. 计算垂直于基准线且经过桌子中点的垂线（边界线）
    3. 只选择与base_grid在边界线同侧的网格
    4. 网格与base_grid的曼哈顿距离不超过control_radius
    
    Args:
        base_grid: 基准网格
        safe_grids: 所有安全网格
        agent: 人物对象
        table_object: 桌子对象
        control_radius: 统御半径（grid单位）
    
    Returns:
        list: 人物统御的网格列表
    """
    if not base_grid:
        return []
    
    base_grid_x = base_grid['grid_x']
    base_grid_y = base_grid['grid_y']
    base_center_x = base_grid['center_x']
    base_center_y = base_grid['center_y']
    
    # 计算基准线（从base_grid到桌子中心）
    dir_x_norm, dir_y_norm, dir_length, table_center_x, table_center_y = \
        calculate_baseline_to_table_center(base_center_x, base_center_y, table_object)
    
    if dir_length < 0.001:
        # base_grid就在桌子中心，使用简单的曼哈顿距离筛选
        controlled_grids = []
        for grid in safe_grids:
            manhattan_distance = abs(grid['grid_x'] - base_grid_x) + abs(grid['grid_y'] - base_grid_y)
            if manhattan_distance <= control_radius:
                controlled_grids.append(grid)
        return controlled_grids
    
    # 获取垂线方向（边界线方向）
    perp_x, perp_y = get_perpendicular_vector(dir_x_norm, dir_y_norm)
    
    # 计算base_grid相对于边界线的位置（用于判断方向）
    base_side = point_to_line_signed_distance(
        base_center_x, base_center_y,
        table_center_x, table_center_y,
        perp_x, perp_y
    )
    
    controlled_grids = []
    
    for grid in safe_grids:
        # 计算曼哈顿距离
        manhattan_distance = abs(grid['grid_x'] - base_grid_x) + abs(grid['grid_y'] - base_grid_y)
        
        if manhattan_distance <= control_radius:
            grid_center_x = grid['center_x']
            grid_center_y = grid['center_y']
            
            # 计算网格相对于边界线的位置
            grid_side = point_to_line_signed_distance(
                grid_center_x, grid_center_y,
                table_center_x, table_center_y,
                perp_x, perp_y
            )
            
            # 判断网格是否与base_grid在边界线同侧
            # 如果base_side和grid_side同号（或grid在边界线上），则在同侧
            if base_side * grid_side >= 0:
                controlled_grids.append(grid)
    
    return controlled_grids


def divide_grids_into_zones(base_grid, controlled_grids, agent, table_object):
    """
    将统御的网格划分为不同的分区
    
    使用计算机图形学方法：
    1. 从base_grid中点到桌子中点绘制基准线
    2. 绘制两条平行线（左右各偏移1.5个格子宽度，即15单位）
    3. main: 网格中点在两条平行线之间
    4. frequent: 人物右手侧的网格（常用区域）
    5. infrequent: 人物左手侧的网格（不常用区域）
    6. temporary: 贴在桌子边缘，离base_grid最近的3-5个网格
    
    右手侧判定规则（基于桌子坐标系：Y轴前后front为正，X轴左右left为正）：
    - 人在front → 右手是left（+X方向）
    - 人在back → 右手是right（-X方向）
    - 人在left → 右手是back（-Y方向）
    - 人在right → 右手是front（+Y方向）
    
    Args:
        base_grid: 基准网格
        controlled_grids: 统御的所有网格
        agent: 人物对象
        table_object: 桌子对象
    
    Returns:
        dict: 分区字典 {'main': [], 'frequent': [], 'infrequent': [], 'temporary': []}
    """
    base_grid_x = base_grid['grid_x']
    base_grid_y = base_grid['grid_y']
    base_center_x = base_grid['center_x']
    base_center_y = base_grid['center_y']
    
    zones = {
        'main': [],
        'frequent': [],
        'infrequent': [],
        'temporary': []
    }
    
    # 如果统御区域很小（横跨或纵跨小于3），不分区，全部作为main
    grid_x_values = [g['grid_x'] for g in controlled_grids]
    grid_y_values = [g['grid_y'] for g in controlled_grids]
    
    x_span = max(grid_x_values) - min(grid_x_values)
    y_span = max(grid_y_values) - min(grid_y_values)
    
    if x_span < 3 and y_span < 3:
        zones['main'] = controlled_grids
        return zones
    
    # 计算基准线（从base_grid到桌子中心）
    dir_x_norm, dir_y_norm, dir_length, table_center_x, table_center_y = \
        calculate_baseline_to_table_center(base_center_x, base_center_y, table_object)
    
    if dir_length < 0.001:
        # base_grid就在桌子中心，使用简单划分
        zones['main'] = controlled_grids
        return zones
    
    # 判断人物在桌子的哪一侧
    agent_side = determine_object_side(agent, table_object)
    
    # 根据人物位置确定右手方向向量（在桌子坐标系中）
    # Y轴：front为正；X轴：left为正
    if agent_side == 'front':
        # 人在front，右手是left（+X方向）
        right_hand_x, right_hand_y = 1.0, 0.0
    elif agent_side == 'back':
        # 人在back，右手是right（-X方向）
        right_hand_x, right_hand_y = -1.0, 0.0
    elif agent_side == 'left':
        # 人在left，右手是back（-Y方向）
        right_hand_x, right_hand_y = 0.0, -1.0
    elif agent_side == 'right':
        # 人在right，右手是front（+Y方向）
        right_hand_x, right_hand_y = 0.0, 1.0
    else:
        # 无法判断位置，使用默认分区（基于基准线的右侧作为frequent）
        right_hand_x, right_hand_y = -dir_y_norm, dir_x_norm
    
    # 计算基准线方向与右手方向的叉积，判断右手在基准线的哪一侧
    # 叉积：baseline × right_hand
    # 正值：右手在基准线左侧（逆时针方向）
    # 负值：右手在基准线右侧（顺时针方向）
    baseline_cross_righthand = dir_x_norm * right_hand_y - dir_y_norm * right_hand_x
    
    # 定义main区域的宽度（3个格子，每个格子10单位，所以左右各1.5格 = 15单位）
    main_half_width = 15.0
    
    # 先对所有网格进行分类（main/frequent/infrequent）
    for grid in controlled_grids:
        grid_center_x = grid['center_x']
        grid_center_y = grid['center_y']
        
        # 计算网格中点到基准线的有向距离
        # signed_dist > 0: 网格在基准线左侧（逆时针方向）
        # signed_dist < 0: 网格在基准线右侧（顺时针方向）
        signed_dist = point_to_line_signed_distance(
            grid_center_x, grid_center_y,
            base_center_x, base_center_y,
            dir_x_norm, dir_y_norm
        )
        
        # 根据有向距离分类
        if abs(signed_dist) <= main_half_width:
            # 在两条平行线之间 -> main
            zones['main'].append(grid)
        else:
            # 判断网格在基准线的哪一侧，结合右手方向判断是frequent还是infrequent
            # 如果右手在基准线左侧（baseline_cross_righthand > 0）：
            #   - signed_dist > 0（网格在左侧） -> infrequent（左手侧）
            #   - signed_dist < 0（网格在右侧） -> frequent（右手侧）
            # 如果右手在基准线右侧（baseline_cross_righthand < 0）：
            #   - signed_dist > 0（网格在左侧） -> frequent（右手侧）
            #   - signed_dist < 0（网格在右侧） -> infrequent（左手侧）
            
            if baseline_cross_righthand > 0:
                # 右手在基准线左侧
                if signed_dist > 0:
                    zones['infrequent'].append(grid)  # 网格在左侧 = 左手侧
                else:
                    zones['frequent'].append(grid)  # 网格在右侧 = 右手侧
            else:
                # 右手在基准线右侧（或共线）
                if signed_dist > 0:
                    zones['frequent'].append(grid)  # 网格在左侧 = 右手侧
                else:
                    zones['infrequent'].append(grid)  # 网格在右侧 = 左手侧
    
    # 找出桌子边缘的网格（用于temporary分区）
    # 边缘网格定义：至少有一个相邻格子（上下左右）不在controlled_grids中
    controlled_grid_coords = set((g['grid_x'], g['grid_y']) for g in controlled_grids)
    
    # 找出所有边缘网格
    edge_grids = []
    for grid in controlled_grids:
        gx = grid['grid_x']
        gy = grid['grid_y']
        
        # 检查四个相邻格子
        neighbors = [(gx + 1, gy), (gx - 1, gy), (gx, gy + 1), (gx, gy - 1)]
        
        # 如果至少有一个相邻格子不在controlled_grids中，这个格子就是边缘格子
        if any(neighbor not in controlled_grid_coords for neighbor in neighbors):
            edge_grids.append(grid)
    
    # 从边缘网格中选择离base_grid最近的3-5个作为temporary
    if edge_grids:
        # 计算每个边缘网格到base_grid的距离
        edge_distances = [
            (grid, math.sqrt((grid['center_x'] - base_center_x) ** 2 + 
                           (grid['center_y'] - base_center_y) ** 2))
            for grid in edge_grids
        ]
        
        # 按距离排序（从近到远）
        edge_distances.sort(key=lambda x: x[1])
        
        # 取最近的3-5个（根据边缘网格数量决定）
        num_temporary = min(5, max(3, len(edge_grids)))
        for i in range(min(num_temporary, len(edge_distances))):
            grid = edge_distances[i][0]
            # temporary网格可以与其他分区重叠，作为额外标签
            zones['temporary'].append(grid)
    
    return zones


def select_item_type_for_agent(agent, agent_type, used_item_types, 
                                agent_status=None, print_info=False):
    """
    为指定人物选择合适的物品类型（封装物品选择逻辑）
    
    Args:
        agent: 人物对象
        agent_type: 人物类型 ('man', 'woman', 'boy', 'girl', 'grandpa', 'unknown')
        used_item_types: 已使用的非重复物品类型集合
        agent_status: 人物状态字典（可选），用于获取sitting/standing状态
        print_info: 是否打印详细信息
    
    Returns:
        tuple: (item_type, item_properties_dict) 或 (None, None) 如果没有可用物品
            - item_type: 选中的物品类型字符串
            - item_properties_dict: 物品属性字典，包含：
                {
                    'zone_types': [...],
                    'min_distance': float,
                    'max_distance': float,
                    'rotation_z': float,
                    'rotation_x': float,
                    'rotation_y': float,
                    'scale': Vector3,
                    'safe_margin': float
                }
    """
    
    # 1. 构建可能的物品列表
    possible_items = []
    
    # 添加人物特定物品
    if agent_type in agent_item_mapping:
        possible_items.extend(agent_item_mapping[agent_type])
    
    # 添加通用物品
    possible_items.extend(common_items)
    
    # 2. 过滤已使用的非重复物品类型
    possible_items = [
        item for item in possible_items
        if item not in non_repeating_item_types or item not in used_item_types
    ]
    
    if not possible_items:
        if print_info:
            print(f"[WARNING] 人物类型 {agent_type} 没有可用的物品类型")
        return None, None
    
    # 3. 为物品设置权重
    agent_id = str(getattr(agent, 'id', ''))
    is_sitting = False
    if agent_status:
        is_sitting = agent_status.get(agent_id, 'standing') == 'sitting'
    
    item_weights = []
    for item in possible_items:
        # 基础权重：有连锁规则的物品权重更高
        if item in ITEM_CHAIN_RULES:
            weight = 4.0
        else:
            weight = 1.0
        
        # 如果人物坐下，某些物品获得额外权重加成
        if is_sitting and item in sitting_item_weight_boost:
            boost = sitting_item_weight_boost[item]
            weight *= boost
            if print_info and boost > 1.0:
                print(f"[PROCESSING] 人物 {agent_id} 坐下，{item} 权重加成 x{boost} 至 {weight}")
        
        item_weights.append(weight)
    
    # 4. 使用加权随机选择
    item_type = random.choices(possible_items, weights=item_weights, k=1)[0]
    
    # 5. 获取物品属性
    if item_type not in item_properties:
        if print_info:
            print(f"[WARNING] 物品类型 {item_type} 没有属性配置")
        return None, None
    
    item_prop = item_properties[item_type]
    
    # 6. 构建返回的属性字典（提取关键信息）
    result_properties = {
        'zone_types': item_prop['zone_types'],
        'min_distance': item_prop.get('min_distance', 10.0),
        'max_distance': item_prop.get('max_distance', 150.0),
        'rotation_z': item_prop.get('rotation_z', 0),
        'rotation_x': item_prop.get('rotation_x', 0),
        'rotation_y': item_prop.get('rotation_y', 0),
        'scale': item_prop.get('scale', ts.Vector3(1, 1, 1)),
        'safe_margin': item_prop.get('safe_margin', 5.0)
    }
    
    if print_info:
        print(f"[INFO] 为人物 {agent_id} ({agent_type}) 选择物品类型: {item_type}")
        print(f"       放置偏好: zone_types={result_properties['zone_types']}, "
              f"distance=[{result_properties['min_distance']}, {result_properties['max_distance']}]")
    
    return item_type, result_properties

# 从可用分区中选择合适的网格（基于距离过滤）
def select_grid_from_zones(agent_grid_info, zone_types, used_grids, base_grid, table_object, agent_id,
                           min_distance, max_distance, item_type, print_info=False):
    """
    从可用分区中选择合适的网格（基于距离过滤）
    
    Args:
        agent_grid_info: 可用的网格列表
        used_grids: 已使用的网格ID集合
        base_grid: 基准网格（人物位置网格）
        table_object: 桌子对象
        min_distance: 最小距离限制
        max_distance: 最大距离限制
        item_type: 物品类型（用于打印信息）
        print_info: 是否打印详细信息
    
    Returns:
        dict: 选中的网格字典，如果没有合适的网格则返回None
    """

    # 1. 选择合适的分区
    available_zones = []
    for zone_type in zone_types:
        if zone_type in agent_grid_info['zones'] and agent_grid_info['zones'][zone_type]:
            available_zones.extend(agent_grid_info['zones'][zone_type])
    
    if not available_zones:
        if print_info:
            print(f"[WARNING] 人物 {agent_id} 没有合适的分区放置 {item_type}")
        return None
    
    # 2. 过滤已使用的网格
    available_zones = [g for g in available_zones if g['id'] not in used_grids]
    
    if not available_zones:
        if print_info:
            print(f"[WARNING] 没有可用的网格放置物品 {item_type}")
        return None
    
    # 基于距离限制过滤网格
    base_center_x = base_grid['center_x']
    base_center_y = base_grid['center_y']
    
    # 计算基准线（从base_grid到桌子中心）
    dir_x_norm, dir_y_norm, dir_length, table_center_x, table_center_y = \
        calculate_baseline_to_table_center(base_center_x, base_center_y, table_object)
    
    if dir_length < 0.001:
        filtered_zones = available_zones
    else:
        filtered_zones = filter_grids_by_distance(
            available_zones,
            base_center_x, base_center_y,
            dir_x_norm, dir_y_norm,
            min_distance, max_distance
        )
    
    if not filtered_zones:
        if print_info:
            print(f"[WARNING] {item_type} 没有满足距离要求的网格 (min={min_distance}, max={max_distance})")
        return None
    
    # 随机选择一个网格
    selected_grid = random.choice(filtered_zones)
    return selected_grid

# 计算物品的最终旋转四元数
def calculate_item_rotation(item_prop, item_location, target_position):
    """
    计算物品的最终旋转四元数
    
    基于物品属性中的旋转配置和朝向目标位置，计算最终的旋转四元数。
    支持自由旋转（rotation_z=360时随机旋转）。
    
    Args:
        item_prop: 物品属性字典，包含 rotation_z, rotation_x, rotation_y
        item_location: 物品位置 (Vector3)
        target_position: 目标位置（通常是人物位置，Vector3）
    
    Returns:
        ts.Quaternion: 最终的旋转四元数
    """
    # 生成旋转
    rotation_z = item_prop.get('rotation_z', 0)
    rotation_x = item_prop.get('rotation_x', 0)
    rotation_y = item_prop.get('rotation_y', 0)
    
    # 如果rotation_z为360，表示自由旋转
    if rotation_z == 360:
        rotation_z = random.uniform(0, 360)
    
    # 计算朝向目标的基础旋转
    target_tem_pos = ts.Vector3(target_position.x, target_position.y, item_location.z)
    rotation_quat = look_at_rotation(item_location, target_tem_pos)
    
    # 创建各个轴的旋转
    x_rotation = create_axis_rotation(rotation_x, 'x')
    y_rotation = create_axis_rotation(rotation_y, 'y')
    z_rotation = create_axis_rotation(rotation_z, 'z')
    
    # 组合所有旋转（Z->Y->X顺序）
    final_rotation = rotation_quat * z_rotation * y_rotation * x_rotation
    
    return final_rotation

# 检查物品是否正确落在桌面上
def check_item_landing(item_obj, table_min_z, table_surface_z, print_info=False, item_type=None):
    """
    检查物品是否正确落在桌面上
    
    Args:
        item_obj: 物品对象
        table_min_z: 桌子高度最小点
        table_surface_z: 桌面高度
        print_info: 是否打印详细信息
        item_type: 物品类型（用于打印信息）
    
    Returns:
        bool: True表示物品正确落地，False表示物品掉落或位置异常
    """
    item_position = item_obj.get_location()
    
    # 检查物品是否掉到桌子下方或偏离桌面太远
    distance_to_floor = abs(item_position.z - table_min_z)
    distance_to_surface = abs(item_position.z - table_surface_z)
    
    if distance_to_floor < distance_to_surface or distance_to_surface > 40:
        if print_info:
            display_name = item_type
            print(f"[WARNING] {display_name} 掉落，重新生成 (距桌面: {distance_to_surface:.1f})")
        return False
    
    return True

# 检查物品旋转是否稳定（是否与预期旋转差异过大）
def check_item_rotation_stability(item_obj, expected_rotation, item_type, threshold_degrees=15.0, print_info=False):
    """
    检查物品旋转是否稳定（是否与预期旋转差异过大）
    
    Args:
        item_obj: 物品对象
        expected_rotation: 预期的旋转四元数
        item_type: 物品类型
        threshold_degrees: 旋转差异阈值（度数）
        print_info: 是否打印详细信息
    
    Returns:
        bool: True表示旋转稳定，False表示旋转变化过大
    """
    # 某些物品类型需要检查旋转稳定性
    check_rotation = item_type in ['drink', 'milk', 'wine', 'computer', 'smallcup', 'bigcup']
    
    if not check_rotation:
        return True
    
    current_rotation = item_obj.get_rotation()
    
    # 计算四元数之间的角度差异
    dot_product = (current_rotation.w * expected_rotation.w +
                  current_rotation.x * expected_rotation.x +
                  current_rotation.y * expected_rotation.y +
                  current_rotation.z * expected_rotation.z)
    
    dot_product = max(-1.0, min(1.0, dot_product))
    angle_rad = 2 * math.acos(abs(dot_product))
    rotation_diff = math.degrees(angle_rad)
    
    if rotation_diff > threshold_degrees:
        if print_info:
            display_name = item_type
            print(f"[WARNING] {display_name} 旋转变化过大 ({rotation_diff:.1f}度)，重新生成")
        return False
    
    return True

# 检查物品放置的有效性（悬空检测）
def check_item_placement_validity(item_obj, item_aabbs, table_min, table_max,
                                   table_surface_z, item_z, safe_margin, 
                                   item_type, print_info=False):
    """
    检查物品放置的有效性（悬空检测）
    
    在物品抬高状态下，检查物品的边界框投影到桌面后是否与其他物品重叠，
    以及是否完全在桌子范围内。
    
    Args:
        item_obj: 物品对象（处于抬高状态）
        item_aabbs: 已放置物品的AABB列表 [(min, max), ...]
        table_min: 桌子AABB最小点
        table_max: 桌子AABB最大点
        table_surface_z: 桌面高度
        item_z: 物品当前的Z轴高度（抬高后）
        safe_margin: 安全边距
        item_type: 物品类型（用于打印信息）
        print_info: 是否打印详细信息
    
    Returns:
        tuple: (is_valid, item_min, item_max)
            - is_valid: bool, True表示位置有效，False表示有冲突
    """
    # 获取物品的边界框并投影到桌面
    item_min_high, item_max_high = get_object_aabb(item_obj)
    
    # 计算投影偏移量
    z_offset = item_z - (table_surface_z + 1.0)
    item_min = ts.Vector3(item_min_high.x, item_min_high.y, item_min_high.z - z_offset)
    item_max = ts.Vector3(item_max_high.x, item_max_high.y, item_max_high.z - z_offset)
    
    # 检查是否与其他物品重叠
    for existing_min, existing_max in item_aabbs:
        if check_item_overlap(
            item_min, item_max, existing_min, existing_max,
            safe_margin=safe_margin, check_z_axis=True
        ):
            if print_info:
                print(f"[WARNING] 物品 {item_type} 与其他物品重叠")
            return False, item_min, item_max
    
    # 检查物品是否完全在桌子上
    if not is_bbox_contained(
        item_min, item_max,
        table_min, table_max,
        safe_margin=safe_margin,
        check_z_axis=False
    ):
        if print_info:
            print(f"[WARNING] 物品 {item_type} 超出桌子边界")
        return False, item_min, item_max
    
    return True


def create_complete_info(entity, my_type, owner_id, grid_dict):
    """
    从实体创建完整的信息字典
    
    Args:
        entity: 实体对象
        my_type: 物品类型（如 'book', 'plate', 'platefood' 等）
        owner_id: 拥有者ID（agent.id）
        grid_dict: 网格字典（包含 grid_x, grid_y, id 等信息）
    
    Returns:
        dict: 完整的物品信息字典
    """
    obj_id = entity.id
    location = entity.get_location()
    rotation = entity.get_rotation()
    entity_min, entity_max = get_object_aabb(entity)
    entity_size = entity.get_scale()
    
    # 提取基础蓝图ID
    base_id = get_blueprint_from_entity_id(obj_id)
    
    return {
        'id': obj_id,
        'base_id': base_id,
        'my_type': my_type,
        'location': {
            'x': location.x,
            'y': location.y,
            'z': location.z
        },
        'rotation': {
            'w': rotation.w,
            'x': rotation.x,
            'y': rotation.y,
            'z': rotation.z
        },
        'entity_min': entity_min,
        'entity_max': entity_max,
        'entity_size': entity_size,
        'entity': entity,
        'owner': str(owner_id),
        'grid_id': grid_dict
    }


def _spawn_chain_item_for_trigger(ue, trigger_item_type, trigger_grid, target_agent, agent_grid_info,
                                   table_object, table_surface_z, item_aabbs, used_grids, used_item_types, used_blueprints,
                                   repeatable_blueprints, safe_grids, print_info=False):
    """
    为触发物品生成连锁物品（子函数）
    
    Args:
        ue: TongSim实例
        trigger_item_type: 触发物品类型
        trigger_grid: 触发物品所在网格
        target_agent: 目标人物对象
        agent_grid_info: 人物的网格信息
        table_object: 桌子对象
        table_surface_z: 桌面高度
        item_aabbs: 已放置物品的AABB列表
        used_grids: 已使用的网格ID集合
        used_item_types: 已使用的非重复物品类型集合
        used_blueprints: 已使用的蓝图集合
        repeatable_blueprints: 可重复使用的蓝图集合
        safe_grids: 所有安全网格列表
        print_info: 是否打印详细信息
    
    Returns:
        list: 成功返回物品信息字典列表，失败返回None
    """
    if trigger_item_type not in ITEM_CHAIN_RULES:
        return None
    
    chain_rules = ITEM_CHAIN_RULES[trigger_item_type]
    
    for rule in chain_rules:
        # 检查概率
        if random.random() > rule['probability']:
            continue
        
        # 获取桌子边界
        table_min, table_max = get_object_aabb(table_object)

        chain_item_type = rule['chain_item']
        
        # 检查连锁物品配置是否存在
        if chain_item_type not in item_properties:
            if print_info:
                print(f"[WARNING] 连锁物品类型 {chain_item_type} 没有配置")
            continue
        
        # 检查是否是非重复物品且已使用
        if chain_item_type in non_repeating_item_types and chain_item_type in used_item_types:
            if print_info:
                print(f"[INFO] 连锁物品 {chain_item_type} 已存在，跳过")
            continue
        
        # 检查是否是platefood连锁物品
        is_chain_platefood = (chain_item_type == 'platefood')
        actual_chain_item_type = chain_item_type  # 保存原始类型
        
        # 获取连锁物品的可放置网格
        agent_side = determine_object_side(target_agent, table_object)
        chain_grids = get_chain_grids(
            current_grid=trigger_grid,
            direction=rule['direction'],
            max_range=rule['max_range'],
            agent_side=agent_side,
            all_grids=safe_grids
        )
        
        # 过滤已使用的网格
        chain_grids = [g for g in chain_grids if g['id'] not in used_grids]
        
        if not chain_grids:
            if print_info:
                print(f"[INFO] 没有可用网格放置连锁物品 {chain_item_type}")
            continue
        
        # 获取连锁物品蓝图
        chain_platefood_blueprint = None
        if is_chain_platefood:
            # platefood需要plate和食物两个蓝图
            if 'plate' not in item_blueprints or not item_blueprints['plate']:
                if print_info:
                    print(f"[WARNING] plate蓝图不存在，无法放置连锁platefood")
                continue
            
            available_chain_plate_blueprints = [
                bp for bp in item_blueprints['plate']
                if bp in repeatable_blueprints or bp not in used_blueprints
            ]
            if not available_chain_plate_blueprints:
                if print_info:
                    print(f"[WARNING] 连锁plate所有蓝图已使用，无法放置")
                continue
            chain_blueprint = random.choice(available_chain_plate_blueprints)
            
            available_chain_platefood_blueprints = [
                bp for bp in item_blueprints[chain_item_type]
                if bp in repeatable_blueprints or bp not in used_blueprints
            ]
            if not available_chain_platefood_blueprints:
                if print_info:
                    print(f"[WARNING] 连锁platefood所有蓝图已使用，无法放置")
                continue
            chain_platefood_blueprint = random.choice(available_chain_platefood_blueprints)
        else:
            if chain_item_type not in item_blueprints or not item_blueprints[chain_item_type]:
                if print_info:
                    print(f"[WARNING] 连锁物品类型 {chain_item_type} 没有蓝图")
                continue
            
            available_chain_blueprints = [
                bp for bp in item_blueprints[chain_item_type]
                if bp in repeatable_blueprints or bp not in used_blueprints
            ]
            if not available_chain_blueprints:
                if print_info:
                    print(f"[WARNING] 连锁{chain_item_type}所有蓝图已使用，无法放置")
                continue
            chain_blueprint = random.choice(available_chain_blueprints)
        
        chain_item_prop = item_properties[chain_item_type]
        chain_scale = chain_item_prop.get('scale', ts.Vector3(1, 1, 1))
        chain_safe_margin = chain_item_prop.get('safe_margin', 5.0)
        
        # 随机打乱网格顺序，然后逐个尝试
        random.shuffle(chain_grids)
        
        for chain_grid in chain_grids:
            # 生成连锁物品位置
            chain_x = chain_grid['center_x']
            chain_y = chain_grid['center_y']
            chain_z = table_surface_z + 1.0
            chain_location = ts.Vector3(chain_x, chain_y, chain_z)
            
            # 使用封装的旋转计算函数
            target_pos = target_agent.get_location()
            chain_final_rotation = calculate_item_rotation(
                item_prop=chain_item_prop,
                item_location=chain_location,
                target_position=target_pos
            )
            
            # 生成连锁物品（先不启用物理）
            try:
                chain_obj = ue.spawn_entity(
                    entity_type=ts.BaseObjectEntity,
                    blueprint=chain_blueprint,
                    location=chain_location,
                    is_simulating_physics=False,
                    scale=chain_scale,
                    quat=chain_final_rotation
                )
            except Exception as e:
                if print_info:
                    print(f"[ERROR] 生成连锁物品失败: {e}")
                continue  # 尝试下一个网格
            
            time.sleep(0.01)
            
            # 使用封装的悬空检测函数
            is_valid = check_item_placement_validity(
                item_obj=chain_obj,
                item_aabbs=item_aabbs,
                table_min=table_min,
                table_max=table_max,
                table_surface_z=table_surface_z,
                item_z=table_surface_z + 70.0,
                safe_margin=chain_safe_margin,
                item_type=chain_item_type,
                print_info=print_info
            )
            
            if not is_valid:
                ue.destroy_entity(chain_obj.id)
                continue  # 尝试下一个网格
            
            # 删除并重新生成（启用物理）
            ue.destroy_entity(chain_obj.id)
            
            chain_z = table_surface_z + 1.0
            chain_location = ts.Vector3(chain_x, chain_y, chain_z)
            
            try:
                chain_obj = ue.spawn_entity(
                    entity_type=ts.BaseObjectEntity,
                    blueprint=chain_blueprint,
                    location=chain_location,
                    is_simulating_physics=True,
                    scale=chain_scale,
                    quat=chain_final_rotation
                )
            except Exception as e:
                if print_info:
                    print(f"[ERROR] 重新生成连锁物品失败: {e}")
                continue  # 尝试下一个网格
            
            # 落地检测
            time.sleep(1.0)
            if not check_item_landing(chain_obj, table_min.z, table_surface_z, print_info, chain_item_type):
                ue.destroy_entity(chain_obj.id)
                continue  # 尝试下一个网格
            
            # 旋转检测
            if not check_item_rotation_stability(chain_obj, chain_final_rotation, chain_item_type, 
                                                 threshold_degrees=15.0, print_info=print_info):
                ue.destroy_entity(chain_obj.id)
                continue  # 尝试下一个网格
            
            # 如果是连锁platefood，在plate上方生成食物
            chain_platefood_obj = None
            if is_chain_platefood:
                chain_food_z = table_surface_z + 10.0
                chain_food_location = ts.Vector3(chain_x, chain_y, chain_food_z)
                
                chain_platefood_prop = item_properties['platefood']
                chain_food_scale = chain_platefood_prop.get('scale', ts.Vector3(1, 1, 1))
                
                # 使用封装的旋转计算函数
                chain_food_final_rotation = calculate_item_rotation(
                    item_prop=chain_platefood_prop,
                    item_location=chain_food_location,
                    target_position=target_pos
                )
                
                try:
                    chain_platefood_obj = ue.spawn_entity(
                        entity_type=ts.BaseObjectEntity,
                        blueprint=chain_platefood_blueprint,
                        location=chain_food_location,
                        is_simulating_physics=True,
                        scale=chain_food_scale,
                        quat=chain_food_final_rotation
                    )
                    
                    time.sleep(1.5)  # 等待食物落到plate上
                    
                    # 检查食物是否成功落在plate上
                    if not check_item_landing(chain_platefood_obj, table_min.z, table_surface_z, print_info, 'platefood'):
                        ue.destroy_entity(chain_platefood_obj.id)
                        ue.destroy_entity(chain_obj.id)
                        if print_info:
                            print(f"[WARNING] 连锁platefood掉落，删除plate，尝试下一个网格")
                        continue  # 尝试下一个网格
                    
                    if print_info:
                        print(f"[SUCCESS] 连锁platefood成功放置在plate上")
                        
                except Exception as e:
                    ue.destroy_entity(chain_obj.id)
                    if print_info:
                        print(f"[ERROR] 生成连锁platefood失败: {e}，删除plate，尝试下一个网格")
                    continue  # 尝试下一个网格
            
            # 成功放置连锁物品
            result_items = []
            
            # 对于platefood，返回plate和food两个信息
            if is_chain_platefood and chain_platefood_obj is not None:
                plate_info = create_complete_info(chain_obj, 'plate', target_agent.id, chain_grid)
                food_info = create_complete_info(chain_platefood_obj, 'platefood', target_agent.id, chain_grid)
                result_items.append(plate_info)
                result_items.append(food_info)
            else:
                chain_info = create_complete_info(chain_obj, chain_item_type, target_agent.id, chain_grid)
                result_items.append(chain_info)
            
            # 标记已使用的网格和蓝图
            used_grids.add(chain_grid['id'])
            
            if chain_item_type in non_repeating_item_types:
                used_item_types.add(chain_item_type)
            
            if chain_blueprint not in repeatable_blueprints:
                used_blueprints.add(chain_blueprint)
            if is_chain_platefood and chain_platefood_obj is not None and chain_platefood_blueprint not in repeatable_blueprints:
                used_blueprints.add(chain_platefood_blueprint)
            
            print(f"[SUCCESS] 连锁放置物品 {chain_item_type} 在网格 ({chain_grid['grid_x']}, {chain_grid['grid_y']}) "
                      f"为人物 {target_agent.id} (触发物品: {trigger_item_type})")
            
            return result_items  # 成功放置，返回结果
        
        # 如果所有网格都尝试完毕仍未放置成功
        if print_info:
            print(f"[INFO] 尝试所有可用网格后仍无法放置连锁物品 {chain_item_type}")
    
    return None  # 没有成功放置任何连锁物品


# 为指定人物生成单个物品（子函数）
def _spawn_single_item_for_agent(
    ue, agent, item_type, agent_grid_info, table_object, table_surface_z,
    item_aabbs, used_grids, used_blueprints, repeatable_blueprints, print_info=False
):
    """
    为指定人物生成单个物品（子函数）
    
    Args:
        ue: TongSim实例
        agent: 人物对象
        item_type: 物品类型
        agent_grid_info: 人物的网格信息（包含base_grid, controlled_grids, zones, type）
        table_object: 桌子对象
        table_surface_z: 桌面高度
        item_aabbs: 已放置物品的AABB列表（用于碰撞检测）
        used_grids: 已使用的网格ID集合
        used_blueprints: 已使用的蓝图集合
        repeatable_blueprints: 可重复使用的蓝图集合
        print_info: 是否打印详细信息
    
    Returns:
        list: 成功返回物品信息字典列表（普通物品返回1个，platefood返回2个：[plate_info, food_info]）
              失败返回None
    """
    # 桌子边界
    table_min, table_max = get_object_aabb(table_object)

    # 检查是否是platefood
    is_platefood = (item_type == 'platefood')
    actual_item_type = item_type
    
    # 获取物品属性
    if item_type not in item_properties:
        if print_info:
            print(f"[WARNING] 物品类型 {item_type} 没有属性配置")
        return None
    
    item_prop = item_properties[item_type]
    zone_types = item_prop['zone_types']
    min_distance = item_prop.get('min_distance', 10.0)
    max_distance = item_prop.get('max_distance', 150.0)
    
    
    # 使用封装的网格选择函数
    selected_grid = select_grid_from_zones(
        agent_grid_info=agent_grid_info,
        zone_types=zone_types,
        used_grids=used_grids,
        base_grid=agent_grid_info['base_grid'],
        table_object=table_object,
        min_distance=min_distance,
        max_distance=max_distance,
        item_type=item_type,
        agent_id=agent.id,
        print_info=print_info
    )
    
    if selected_grid is None:
        return None
    
    # 4. 选择物品蓝图
    if item_type not in item_blueprints or not item_blueprints[item_type]:
        if print_info:
            print(f"[WARNING] 物品类型 {item_type} 没有蓝图")
        return None
    
    # 选择具体蓝图
    platefood_blueprint = None
    if is_platefood:
        # platefood需要plate和食物两个蓝图
        if 'plate' not in item_blueprints or not item_blueprints['plate']:
            if print_info:
                print(f"[WARNING] plate蓝图不存在，无法放置platefood")
            return None
        
        # 过滤已使用的plate蓝图
        available_plate_blueprints = [
            bp for bp in item_blueprints['plate']
            if bp in repeatable_blueprints or bp not in used_blueprints
        ]
        if not available_plate_blueprints:
            if print_info:
                print(f"[WARNING] plate所有蓝图已使用，无法放置")
            return None
        blueprint = random.choice(available_plate_blueprints)
        
        # 过滤已使用的platefood蓝图
        available_platefood_blueprints = [
            bp for bp in item_blueprints[item_type]
            if bp in repeatable_blueprints or bp not in used_blueprints
        ]
        if not available_platefood_blueprints:
            if print_info:
                print(f"[WARNING] platefood所有蓝图已使用，无法放置")
            return None
        platefood_blueprint = random.choice(available_platefood_blueprints)
    else:
        # 普通物品
        available_blueprints = [
            bp for bp in item_blueprints[item_type]
            if bp in repeatable_blueprints or bp not in used_blueprints
        ]
        if not available_blueprints:
            if print_info:
                print(f"[WARNING] {item_type}所有蓝图已使用，无法放置")
            return None
        blueprint = random.choice(available_blueprints)
    
    # 5. 生成实验性物品（抬高检测碰撞）
    item_x = selected_grid['center_x']
    item_y = selected_grid['center_y']
    item_z = table_surface_z + 1.0
    item_location = ts.Vector3(item_x, item_y, item_z)
    
    # 使用封装的旋转计算函数
    target_pos = agent.get_location()
    final_rotation = calculate_item_rotation(
        item_prop=item_prop,
        item_location=item_location,
        target_position=target_pos
    )
    
    # 获取缩放和安全边距
    scale = item_prop.get('scale', ts.Vector3(1, 1, 1))
    safe_margin = item_prop.get('safe_margin', 5.0)
    
    # 生成物品（先不启用物理）
    try:
        item_temp_location = ts.Vector3(item_x, item_y, table_surface_z + 70.0)
        item_obj = ue.spawn_entity(
            entity_type=ts.BaseObjectEntity,
            blueprint=blueprint,
            location=item_temp_location,
            is_simulating_physics=False,
            scale=scale,
            quat=final_rotation
        )
    except Exception as e:
        if print_info:
            print(f"[ERROR] 生成物品失败: {e}")
        return None
    
    time.sleep(0.01)
    
    # 使用封装的悬空检测函数
    is_valid = check_item_placement_validity(
        item_obj=item_obj,
        item_aabbs=item_aabbs,
        table_min=table_min,
        table_max=table_max,
        table_surface_z=table_surface_z,
        item_z=table_surface_z + 70.0,
        safe_margin=safe_margin,
        item_type=item_type,
        print_info=print_info
    )
    # 删除高处的物品
    ue.destroy_entity(item_obj.id)
    if not is_valid:
        return None
    
    # 6. 放置真实物品到桌面
    try:
        item_obj = ue.spawn_entity(
            entity_type=ts.BaseObjectEntity,
            blueprint=blueprint,
            location=item_location,
            is_simulating_physics=True,
            scale=scale,
            quat=final_rotation
        )
    except Exception as e:
        if print_info:
            print(f"[ERROR] 重新生成物品失败: {e}")
        return None
    
    # 7. 落地检测
    time.sleep(1.0)
    if not check_item_landing(item_obj, table_min.z, table_surface_z, print_info, item_type):
        ue.destroy_entity(item_obj.id)
        return None
    
    # 8. 旋转检测
    if not check_item_rotation_stability(item_obj, final_rotation, item_type, threshold_degrees=15.0, print_info=print_info):
        ue.destroy_entity(item_obj.id)
        return None
    
    # 9. 如果是platefood，在plate上方生成食物
    platefood_obj = None
    if is_platefood:
        plate_position = item_obj.get_location()
        
        food_z = table_surface_z + 10.0
        food_location = ts.Vector3(item_x, item_y, food_z)
        
        platefood_prop = item_properties['platefood']
        food_scale = platefood_prop.get('scale', ts.Vector3(1, 1, 1))
        
        # 使用封装的旋转计算函数（food也需要朝向agent）
        food_final_rotation = calculate_item_rotation(
            item_prop=platefood_prop,
            item_location=food_location,
            target_position=target_pos
        )
        
        try:
            platefood_obj = ue.spawn_entity(
                entity_type=ts.BaseObjectEntity,
                blueprint=platefood_blueprint,
                location=food_location,
                is_simulating_physics=True,
                scale=food_scale,
                quat=food_final_rotation
            )
            
            # 检查食物是否成功落在plate上
            time.sleep(1.5)
            food_position = platefood_obj.get_location()
            if abs(food_position.z - table_min.z) < abs(food_position.z - table_surface_z):
                ue.destroy_entity(platefood_obj.id)
                ue.destroy_entity(item_obj.id)
                if print_info:
                    print(f"[WARNING] platefood掉落到地面，同时删除plate")
                return None
            
            if print_info:
                print(f"[SUCCESS] platefood成功放置在plate上")
                
        except Exception as e:
            ue.destroy_entity(item_obj.id)
            if print_info:
                print(f"[ERROR] 生成platefood失败: {e}，删除plate")
            return None
    
    # 10. 构建返回的完整信息字典
    result_items = []
    
    # 对于platefood，返回plate和food两个信息
    if is_platefood and platefood_obj is not None:
        plate_info = create_complete_info(item_obj, 'plate', agent.id, selected_grid)
        food_info = create_complete_info(platefood_obj, 'platefood', agent.id, selected_grid)
        result_items = [plate_info, food_info]
        
        # 标记已使用的蓝图
        if blueprint not in repeatable_blueprints:
            used_blueprints.add(blueprint)
        if platefood_blueprint not in repeatable_blueprints:
            used_blueprints.add(platefood_blueprint)
    else:
        # 普通物品
        item_info = create_complete_info(item_obj, actual_item_type, agent.id, selected_grid)
        result_items = [item_info]
        
        if blueprint not in repeatable_blueprints:
            used_blueprints.add(blueprint)
    
    # 标记已使用的网格
    used_grids.add(selected_grid['id'])
    
    if print_info:
        display_type = actual_item_type if is_platefood else item_type
        print(f"[SUCCESS] 放置物品 {display_type} 在网格 ({selected_grid['grid_x']}, {selected_grid['grid_y']}) "
              f"为人物 {agent.id}")
    
    return result_items


def spawn_items_on_grid(ue, table_object, agents, grid_data, agent_features_list=None, 
                        max_total_items=10, max_items_per_agent=3, print_info=False):
    """
    基于网格JSON数据在桌面上放置物品
    
    Args:
        ue: TongSim实例
        table_object: 桌子对象
        agents: 人物对象列表
        grid_data: 网格数据字典（从JSON加载）
        agent_features_list: 人物特征列表（与agents对应，包含status等信息）
        max_total_items: 桌面最大物品总数
        max_items_per_agent: 每个人物最多物品数量
        print_info: 是否打印详细信息
    
    Returns:
        tuple: (spawned_items, owners_list, features_list)
            - spawned_items: 生成的物品对象列表
            - owners_list: 每个物品的所有者ID列表（与spawned_items对应）
            - features_list: 每个物品的特征字典列表（与spawned_items对应）
    """
    
    if not grid_data or 'safe_grids' not in grid_data:
        print("[ERROR] 无效的网格数据")
        return [], [], []
    
    safe_grids = grid_data['safe_grids']
    table_bounds = grid_data['table_bounds']
    table_surface_z = table_bounds['z_surface']
    
    # 获取桌子边界
    table_min, table_max = get_object_aabb(table_object)
    
    if print_info:
        print(f"\n[INFO] 开始在网格上放置物品")
        print(f"[INFO] 可用网格数: {len(safe_grids)}")
    
    # 第一步：确定每个人物类型和状态
    agent_types = {}
    agent_status = {}  # 存储人物状态（sitting/standing）
    
    # 使用传入的agent_features_list来获取人物状态
    if agent_features_list and len(agent_features_list) == len(agents):
        for agent, features in zip(agents, agent_features_list):
            agent_id = str(getattr(agent, 'id', ''))
            status = features.get('status', 'standing')
            agent_status[agent_id] = status
            if print_info:
                print(f"[INFO] 从features_list读取人物 {agent_id} 状态: {status}")
    
    for agent in agents:
        agent_id = str(getattr(agent, 'id', ''))
        agent_type = get_agent_trait(agent_id) or 'unknown'
        
        if agent_type == 'unknown' and print_info:
            print(f"[WARNING] 无法识别人物类型 {agent_id}")
        
        agent_types[agent] = agent_type
        
        # 如果没有从features_list读取到状态，默认为standing
        if agent_id not in agent_status:
            agent_status[agent_id] = 'standing'
    
    # 第二步：为每个人物找到基准网格和统御区域
    agent_grids = {}
    for agent in agents:
        base_grid = find_agent_base_grid(agent, safe_grids)
        if not base_grid:
            if print_info:
                print(f"[WARNING] 无法为人物 {agent.id} 找到基准网格")
            continue
        
        # 根据人物类型设置统御半径
        agent_type = agent_types[agent]
        if agent_type in ['man', 'woman']:
            control_radius = 6
        elif agent_type in ['boy', 'girl']:
            control_radius = 4
        else:
            control_radius = 5
        
        controlled_grids = get_agent_controlled_grids(
            base_grid, safe_grids, agent, table_object, control_radius
        )
        
        zones = divide_grids_into_zones(base_grid, controlled_grids, agent, table_object)
        
        agent_grids[agent] = {
            'base_grid': base_grid,
            'controlled_grids': controlled_grids,
            'zones': zones,
            'type': agent_type
        }
        
        if print_info:
            print(f"[INFO] 人物 {agent.id} ({agent_type}):")
            print(f"  基准网格: ({base_grid['grid_x']}, {base_grid['grid_y']})")
            print(f"  统御网格数: {len(controlled_grids)}")
            print(f"  分区: main={len(zones['main'])}, frequent={len(zones['frequent'])}, "
                  f"infrequent={len(zones['infrequent'])}, temporary={len(zones['temporary'])}")
    
    # 测试：可视化每个人物的分区（调试用）
    # 如果需要测试，取消下面的注释
    # visualize_agent_zones(ue, agents, agent_grids, table_surface_z, print_info=True)
    
    # 第三步：生成物品
    spawned_items = []  # 所有生成的物品对象
    owners_list = []  # 每个物品的所有者ID（与spawned_items对应）
    features_list = []  # 每个物品的特征字典（与spawned_items对应）
    item_aabbs = []  # 存储已放置物品的边界框
    used_grids = set()  # 已使用的网格ID
    used_item_types = set()  # 已使用的非重复物品类型
    used_blueprints = set()  # 已使用的蓝图（除了可重复蓝图）
    agent_item_count = {agent: 0 for agent in agents}
    total_item_count = 0  # 实际物品计数（不包括plate附庸）
    
    attempt_count = 0
    max_attempts = max_total_items * 100
    
    while total_item_count < max_total_items and attempt_count < max_attempts:
        attempt_count += 1
        
        # 检查是否所有人物都已达到最大物品数量
        if all(count >= max_items_per_agent for count in agent_item_count.values()):
            if print_info:
                print("[INFO] 所有人物均已达到最大物品数量，停止生成")
            break
        
        # 随机选择一个还未达到物品上限的人物
        available_agents = [a for a in agents if a in agent_grids and agent_item_count[a] < max_items_per_agent]
        if not available_agents:
            break
        
        target_agent = random.choice(available_agents)
        agent_type = agent_types[target_agent]
        agent_grid_info = agent_grids[target_agent]
        
        # 使用封装的函数选择物品类型
        item_type, item_prop_dict = select_item_type_for_agent(
            agent=target_agent,
            agent_type=agent_type,
            used_item_types=used_item_types,
            agent_status=agent_status,
            print_info=print_info
        )
        
        # 如果没有可用物品，继续下一次尝试
        if item_type is None or item_prop_dict is None:
            continue
        
        # 检查是否是platefood，如果是，则需要先放置plate
        is_platefood = (item_type == 'platefood')
        actual_item_type = item_type  # 保存原始物品类型用于JSON记录
        
        # 从返回的字典中提取物品放置偏好
        zone_types = item_prop_dict['zone_types']
        min_distance = item_prop_dict['min_distance']
        max_distance = item_prop_dict['max_distance']
        
        # 选择合适的分区
        available_zones = []
        for zone_type in zone_types:
            if zone_type in agent_grid_info['zones'] and agent_grid_info['zones'][zone_type]:
                available_zones.extend(agent_grid_info['zones'][zone_type])
        
        if not available_zones:
            if print_info:
                print(f"[WARNING] 人物 {target_agent.id} 没有合适的分区放置 {item_type}")
            continue
        
        # 过滤已使用的网格
        available_zones = [g for g in available_zones if g['id'] not in used_grids]
        
        if not available_zones:
            if print_info:
                print(f"[WARNING] 没有可用的网格放置物品 {item_type}")
            continue
        
        # 基于距离限制过滤网格（使用垂线投影方法）
        base_grid = agent_grid_info['base_grid']
        base_center_x = base_grid['center_x']
        base_center_y = base_grid['center_y']
        
        # 计算基准线（从base_grid到桌子中心）
        dir_x_norm, dir_y_norm, dir_length, table_center_x, table_center_y = \
            calculate_baseline_to_table_center(base_center_x, base_center_y, table_object)
        
        if dir_length < 0.001:
            # base_grid就在桌子中心，所有网格都满足条件
            filtered_zones = available_zones
        else:
            # 使用投影方法过滤网格
            filtered_zones = filter_grids_by_distance(
                available_zones,
                base_center_x, base_center_y,
                dir_x_norm, dir_y_norm,
                min_distance, max_distance
            )
        
        if not filtered_zones:
            if print_info:
                print(f"[WARNING] {item_type} 没有满足距离要求的网格 (min={min_distance}, max={max_distance})")
            continue
        
        # 随机选择一个网格
        selected_grid = random.choice(filtered_zones)
        
        # 选择物品蓝图
        if item_type not in item_blueprints or not item_blueprints[item_type]:
            if print_info:
                print(f"[WARNING] 物品类型 {item_type} 没有蓝图")
            continue
        
        # 如果是platefood，使用plate蓝图；否则使用原物品蓝图
        if is_platefood:
            if 'plate' not in item_blueprints or not item_blueprints['plate']:
                if print_info:
                    print(f"[WARNING] plate蓝图不存在，无法放置platefood")
                continue
            # 过滤已使用的plate蓝图（如果plate不在可重复列表中）
            available_plate_blueprints = [
                bp for bp in item_blueprints['plate']
                if bp in repeatable_blueprints or bp not in used_blueprints
            ]
            if not available_plate_blueprints:
                if print_info:
                    print(f"[WARNING] plate所有蓝图已使用，无法放置")
                continue
            blueprint = random.choice(available_plate_blueprints)
            
            # 过滤已使用的platefood蓝图
            available_platefood_blueprints = [
                bp for bp in item_blueprints[item_type]
                if bp in repeatable_blueprints or bp not in used_blueprints
            ]
            if not available_platefood_blueprints:
                if print_info:
                    print(f"[WARNING] platefood所有蓝图已使用，无法放置")
                continue
            platefood_blueprint = random.choice(available_platefood_blueprints)
        else:
            # 过滤已使用的蓝图
            available_blueprints = [
                bp for bp in item_blueprints[item_type]
                if bp in repeatable_blueprints or bp not in used_blueprints
            ]
            if not available_blueprints:
                if print_info:
                    print(f"[WARNING] {item_type}所有蓝图已使用，无法放置")
                continue
            blueprint = random.choice(available_blueprints)
        
        # 生成物品位置（在网格中心，先抬高以进行碰撞检测）
        item_x = selected_grid['center_x']
        item_y = selected_grid['center_y']
        item_z = table_surface_z + 70.0  # 抬高以避免初始碰撞
        
        item_location = ts.Vector3(item_x, item_y, item_z)
        
        # 生成旋转（从字典中获取）
        rotation_z = item_prop_dict['rotation_z']
        rotation_x = item_prop_dict['rotation_x']
        rotation_y = item_prop_dict['rotation_y']
        
        # 如果rotation_z为360，表示自由旋转
        if rotation_z == 360:
            rotation_z = random.uniform(0, 360)
        
        target_pos = agent.get_location()
        target_tem_pos = ts.Vector3(target_pos.x, target_pos.y, item_z)
        rotation_quat = look_at_rotation(item_location, target_tem_pos)
        
        # 创建各个轴的旋转（使用全局辅助函数）
        x_rotation = create_axis_rotation(rotation_x, 'x')
        y_rotation = create_axis_rotation(rotation_y, 'y')
        z_rotation = create_axis_rotation(rotation_z, 'z')

        # 组合所有旋转（注意旋转顺序很重要，这里使用Z->Y->X的顺序）
        final_rotation = rotation_quat * z_rotation * y_rotation * x_rotation
        
        # 获取缩放和安全边距（从字典中获取）
        scale = item_prop_dict['scale']
        safe_margin = item_prop_dict['safe_margin']
        
        # 生成物品（先不启用物理）
        try:
            item_obj = ue.spawn_entity(
                entity_type=ts.BaseObjectEntity,
                blueprint=blueprint,
                location=item_location,
                is_simulating_physics=False,
                scale=scale,
                quat=final_rotation
            )
        except Exception as e:
            if print_info:
                print(f"[ERROR] 生成物品失败: {e}")
            continue
        
        time.sleep(0.01)
        
        # 获取物品的边界框（物品在高处，需要将边界框投影到桌面）
        item_min_high, item_max_high = get_object_aabb(item_obj)
        
        # 将边界框投影到桌面高度
        z_offset = item_z - (table_surface_z + 1.0)
        item_min = ts.Vector3(item_min_high.x, item_min_high.y, item_min_high.z - z_offset)
        item_max = ts.Vector3(item_max_high.x, item_max_high.y, item_max_high.z - z_offset)
        
        # 检查是否与其他物品重叠
        overlap_found = False
        for existing_min, existing_max in item_aabbs:
            if check_item_overlap(
                item_min, item_max, existing_min, existing_max,
                safe_margin=safe_margin, check_z_axis=True
            ):
                overlap_found = True
                break
        
        if overlap_found:
            ue.destroy_entity(item_obj.id)
            if print_info:
                print(f"[WARNING] 物品 {item_type} 与其他物品重叠")
            continue
        
        # 检查物品是否完全在桌子上
        if not is_bbox_contained(
            item_min, item_max,
            table_min, table_max,
            safe_margin=safe_margin,
            check_z_axis=False
        ):
            ue.destroy_entity(item_obj.id)
            if print_info:
                print(f"[WARNING] 物品 {item_type} 超出桌子边界")
            continue
        
        # 删除高处的物品，准备在桌面生成
        ue.destroy_entity(item_obj.id)
        
        # 更新物品位置到桌面（plate放在桌面上）
        item_z = table_surface_z + 1.0
        item_location = ts.Vector3(item_x, item_y, item_z)
        
        try:
            item_obj = ue.spawn_entity(
                entity_type=ts.BaseObjectEntity,
                blueprint=blueprint,
                location=item_location,
                is_simulating_physics=True,
                scale=scale,
                quat=final_rotation
            )
        except Exception as e:
            if print_info:
                print(f"[ERROR] 重新生成物品失败: {e}")
            continue
        
        
        # 落地检测
        time.sleep(1.0)
        item_position = item_obj.get_location()
        if abs(item_position.z - table_min.z) < abs(item_position.z - table_surface_z) or abs(item_position.z - table_surface_z) > 40:
            ue.destroy_entity(item_obj.id)
            if print_info:
                print(f"[WARNING] 物品 {item_type} 掉落，重新生成")
            continue
        
        # 对特定物品进行旋转检测（plate不检测，因为它是附庸）
        check_rotation = item_type in ['drink', 'milk', 'wine', 'computer', 'smallcup', 'bigcup']
            
        if check_rotation:
            current_rotation = item_obj.get_rotation()
            
            dot_product = (current_rotation.w * final_rotation.w +
                          current_rotation.x * final_rotation.x +
                          current_rotation.y * final_rotation.y +
                          current_rotation.z * final_rotation.z)
            
            dot_product = max(-1.0, min(1.0, dot_product))
            angle_rad = 2 * math.acos(abs(dot_product))
            rotation_diff = math.degrees(angle_rad)
            
            if rotation_diff > 15:
                ue.destroy_entity(item_obj.id)
                if print_info:
                    display_name = 'plate' if is_platefood else item_type
                    print(f"[WARNING] {display_name} 旋转变化过大 ({rotation_diff:.1f}度)，重新生成")
                continue
        
        # 如果是platefood，需要在plate上方生成食物
        platefood_obj = None
        if is_platefood:
            # 获取plate的当前位置
            plate_position = item_obj.get_location()
            
            # 在plate上方10单位生成食物
            food_z = table_surface_z + 10.0
            food_location = ts.Vector3(item_x, item_y, food_z)
            
            # 使用platefood的属性
            platefood_prop = item_properties['platefood']
            food_scale = platefood_prop.get('scale', ts.Vector3(1, 1, 1))
            
            # 食物的旋转
            food_rotation_z = platefood_prop.get('rotation_z', 0)
            if food_rotation_z == 360:
                food_rotation_z = random.uniform(0, 360)
            food_rotation_x = platefood_prop.get('rotation_x', 0)
            food_rotation_y = platefood_prop.get('rotation_y', 0)
            
            # 创建食物的旋转
            food_target_pos = ts.Vector3(target_pos.x, target_pos.y, food_z)
            food_rotation_quat = look_at_rotation(food_location, food_target_pos)
            
            food_x_rot = create_axis_rotation(food_rotation_x, 'x')
            food_y_rot = create_axis_rotation(food_rotation_y, 'y')
            food_z_rot = create_axis_rotation(food_rotation_z, 'z')
            food_final_rotation = food_rotation_quat * food_z_rot * food_y_rot * food_x_rot
            
            try:
                platefood_obj = ue.spawn_entity(
                    entity_type=ts.BaseObjectEntity,
                    blueprint=platefood_blueprint,
                    location=food_location,
                    is_simulating_physics=True,
                    scale=food_scale,
                    quat=food_final_rotation
                )
                
                time.sleep(1.5)  # 等待食物落到plate上
                
                # 检查食物是否成功落在plate上
                food_position = platefood_obj.get_location()
                if abs(food_position.z - table_min.z) < abs(food_position.z - table_surface_z):
                    # 食物掉到地上了，删除plate和食物
                    ue.destroy_entity(platefood_obj.id)
                    ue.destroy_entity(item_obj.id)
                    if print_info:
                        print(f"[WARNING] platefood掉落到地面，同时删除plate")
                    continue
                
                if print_info:
                    print(f"[SUCCESS] platefood成功放置在plate上")
                    
            except Exception as e:
                # 生成食物失败，删除plate
                ue.destroy_entity(item_obj.id)
                if print_info:
                    print(f"[ERROR] 生成platefood失败: {e}，删除plate")
                continue
        
        # 成功放置物品（对于platefood，item_obj是plate）
        # plate作为附庸，不计入物品总数
        if not is_platefood:
            spawned_items.append(item_obj)
        
        item_aabbs.append((item_min, item_max))
        used_grids.add(selected_grid['id'])
        
        # plate不计入人物物品数和总物品数
        if not is_platefood:
            agent_item_count[target_agent] += 1
            total_item_count += 1
        
        # 如果成功放置了platefood，将plate和食物都加入spawned_items，但只计数食物
        if is_platefood and platefood_obj is not None:
            spawned_items.append(item_obj)  # plate
            owners_list.append(str(target_agent.id))  # plate的owner
            features_list.append({'type': 'plate'})  # plate的features
            
            spawned_items.append(platefood_obj)  # platefood
            owners_list.append(str(target_agent.id))  # platefood的owner
            features_list.append({'type': 'platefood'})  # platefood的features
            
            agent_item_count[target_agent] += 1  # 只计数一次（食物）
            total_item_count += 1  # 只计数一次（食物）
        else:
            # 普通物品：添加到列表
            owners_list.append(str(target_agent.id))
            features_list.append({'type': item_type})
        
        # 标记非重复物品类型（使用实际物品类型）
        if actual_item_type in non_repeating_item_types:
            used_item_types.add(actual_item_type)
        
        # 标记已使用的蓝图（如果不在可重复列表中）
        if blueprint not in repeatable_blueprints:
            used_blueprints.add(blueprint)
        if is_platefood and platefood_obj is not None and platefood_blueprint not in repeatable_blueprints:
            used_blueprints.add(platefood_blueprint)
        
        if print_info:
            display_type = actual_item_type if is_platefood else item_type
            print(f"[SUCCESS] 放置物品 {display_type} 在网格 ({selected_grid['grid_x']}, {selected_grid['grid_y']}) "
                  f"为人物 {target_agent.id} [已放置:{total_item_count}/{max_total_items}]")
        
        # ============== 连锁物品生成逻辑 ==============
        if item_type in ITEM_CHAIN_RULES:
            chain_rules = ITEM_CHAIN_RULES[item_type]
            
            for rule in chain_rules:
                # 检查概率
                if random.random() > rule['probability']:
                    continue
                
                chain_item_type = rule['chain_item']
                
                # 检查是否已达到总物品上限
                if total_item_count >= max_total_items:
                    if print_info:
                        print(f"[INFO] 已达到物品上限，跳过连锁生成 {chain_item_type}")
                    break
                
                # 检查该人物是否已达到物品上限
                if agent_item_count[target_agent] >= max_items_per_agent:
                    if print_info:
                        print(f"[INFO] 人物 {target_agent.id} 已达到物品上限，跳过连锁生成 {chain_item_type}")
                    continue
                
                # 检查连锁物品配置是否存在
                if chain_item_type not in item_properties:
                    if print_info:
                        print(f"[WARNING] 连锁物品类型 {chain_item_type} 没有配置")
                    continue
                
                # 检查是否是非重复物品且已使用
                if chain_item_type in non_repeating_item_types and chain_item_type in used_item_types:
                    if print_info:
                        print(f"[INFO] 连锁物品 {chain_item_type} 已存在，跳过")
                    continue
                
                # 检查是否是platefood连锁物品
                is_chain_platefood = (chain_item_type == 'platefood')
                actual_chain_item_type = chain_item_type  # 保存原始类型
                
                # 获取连锁物品的可放置网格
                agent_side = determine_object_side(target_agent, table_object)
                chain_grids = get_chain_grids(
                    current_grid=selected_grid,
                    direction=rule['direction'],
                    max_range=rule['max_range'],
                    agent_side=agent_side,
                    all_grids=safe_grids
                )
                
                # 过滤已使用的网格
                chain_grids = [g for g in chain_grids if g['id'] not in used_grids]
                
                if not chain_grids:
                    if print_info:
                        print(f"[INFO] 没有可用网格放置连锁物品 {chain_item_type}")
                    continue
                
                # 获取连锁物品蓝图
                # 如果是platefood，使用plate蓝图；否则使用原物品蓝图
                if is_chain_platefood:
                    if 'plate' not in item_blueprints or not item_blueprints['plate']:
                        if print_info:
                            print(f"[WARNING] plate蓝图不存在，无法放置连锁platefood")
                        continue
                    # 过滤已使用的plate蓝图（如果plate不在可重复列表中）
                    available_chain_plate_blueprints = [
                        bp for bp in item_blueprints['plate']
                        if bp in repeatable_blueprints or bp not in used_blueprints
                    ]
                    if not available_chain_plate_blueprints:
                        if print_info:
                            print(f"[WARNING] 连锁plate所有蓝图已使用，无法放置")
                        continue
                    chain_blueprint = random.choice(available_chain_plate_blueprints)
                    
                    # 过滤已使用的platefood蓝图
                    available_chain_platefood_blueprints = [
                        bp for bp in item_blueprints[chain_item_type]
                        if bp in repeatable_blueprints or bp not in used_blueprints
                    ]
                    if not available_chain_platefood_blueprints:
                        if print_info:
                            print(f"[WARNING] 连锁platefood所有蓝图已使用，无法放置")
                        continue
                    chain_platefood_blueprint = random.choice(available_chain_platefood_blueprints)
                else:
                    if chain_item_type not in item_blueprints or not item_blueprints[chain_item_type]:
                        if print_info:
                            print(f"[WARNING] 连锁物品类型 {chain_item_type} 没有蓝图")
                        continue
                    # 过滤已使用的蓝图
                    available_chain_blueprints = [
                        bp for bp in item_blueprints[chain_item_type]
                        if bp in repeatable_blueprints or bp not in used_blueprints
                    ]
                    if not available_chain_blueprints:
                        if print_info:
                            print(f"[WARNING] 连锁{chain_item_type}所有蓝图已使用，无法放置")
                        continue
                    chain_blueprint = random.choice(available_chain_blueprints)
                
                chain_item_prop = item_properties[chain_item_type]
                chain_scale = chain_item_prop.get('scale', ts.Vector3(1, 1, 1))
                chain_safe_margin = chain_item_prop.get('safe_margin', 5.0)
                
                # 随机打乱网格顺序，然后逐个尝试
                random.shuffle(chain_grids)
                chain_placed = False
                
                for chain_grid in chain_grids:
                    # 生成连锁物品位置
                    chain_x = chain_grid['center_x']
                    chain_y = chain_grid['center_y']
                    chain_z = table_surface_z + 70.0
                    chain_location = ts.Vector3(chain_x, chain_y, chain_z)
                    
                    # 生成旋转
                    chain_rotation_z = chain_item_prop.get('rotation_z', 0)
                    if chain_rotation_z == 360:
                        chain_rotation_z = random.uniform(0, 360)
                    
                    chain_rotation_x = chain_item_prop.get('rotation_x', 0)
                    chain_rotation_y = chain_item_prop.get('rotation_y', 0)
                    
                    target_pos = target_agent.get_location()
                    target_tem_pos = ts.Vector3(target_pos.x, target_pos.y, chain_z)
                    chain_rotation_quat = look_at_rotation(chain_location, target_tem_pos)
                    
                    # 创建旋转（使用全局辅助函数）
                    x_rot = create_axis_rotation(chain_rotation_x, 'x')
                    y_rot = create_axis_rotation(chain_rotation_y, 'y')
                    z_rot = create_axis_rotation(chain_rotation_z, 'z')
                    chain_final_rotation = chain_rotation_quat * z_rot * y_rot * x_rot
                    
                    # 生成连锁物品（先不启用物理）
                    try:
                        chain_obj = ue.spawn_entity(
                            entity_type=ts.BaseObjectEntity,
                            blueprint=chain_blueprint,
                            location=chain_location,
                            is_simulating_physics=False,
                            scale=chain_scale,
                            quat=chain_final_rotation
                        )
                    except Exception as e:
                        if print_info:
                            print(f"[ERROR] 生成连锁物品失败: {e}")
                        continue  # 尝试下一个网格
                    
                    time.sleep(0.01)
                    
                    # 检查碰撞
                    chain_min_high, chain_max_high = get_object_aabb(chain_obj)
                    
                    z_offset = chain_z - (table_surface_z + 1.0)
                    chain_min = ts.Vector3(chain_min_high.x, chain_min_high.y, chain_min_high.z - z_offset)
                    chain_max = ts.Vector3(chain_max_high.x, chain_max_high.y, chain_max_high.z - z_offset)
                    
                    # 检查重叠
                    chain_overlap = False
                    for existing_min, existing_max in item_aabbs:
                        if check_item_overlap(chain_min, chain_max, existing_min, existing_max,
                                             safe_margin=chain_safe_margin, check_z_axis=False):
                            chain_overlap = True
                            break
                    
                    if chain_overlap:
                        ue.destroy_entity(chain_obj.id)
                        continue  # 尝试下一个网格
                    
                    # 检查是否在桌子上
                    if not is_bbox_contained(chain_min, chain_max, table_min, table_max,
                                            safe_margin=chain_safe_margin, check_z_axis=False):
                        ue.destroy_entity(chain_obj.id)
                        continue  # 尝试下一个网格
                    
                    # 删除并重新生成（启用物理）
                    ue.destroy_entity(chain_obj.id)
                    
                    chain_z = table_surface_z + 1.0
                    chain_location = ts.Vector3(chain_x, chain_y, chain_z)
                    
                    try:
                        chain_obj = ue.spawn_entity(
                            entity_type=ts.BaseObjectEntity,
                            blueprint=chain_blueprint,
                            location=chain_location,
                            is_simulating_physics=True,
                            scale=chain_scale,
                            quat=chain_final_rotation
                        )
                    except Exception as e:
                        if print_info:
                            print(f"[ERROR] 重新生成连锁物品失败: {e}")
                        continue  # 尝试下一个网格
                    
                    time.sleep(1.0)
                    
                    # 落地检测
                    chain_position = chain_obj.get_location()
                    if abs(chain_position.z - table_min.z) < abs(chain_position.z - table_surface_z) or \
                       abs(chain_position.z - table_surface_z) > 40:
                        ue.destroy_entity(chain_obj.id)
                        continue  # 尝试下一个网格
                    
                    # 旋转检测（包括platefood的plate）
                    check_chain_rotation = chain_item_type in ['drink', 'milk', 'wine', 'computer', 'smallcup', 'bigcup']
                    # 如果是连锁platefood，也检查plate的旋转
                    if is_chain_platefood:
                        check_chain_rotation = True
                    
                    if check_chain_rotation:
                        current_rotation = chain_obj.get_rotation()
                        dot_product = (current_rotation.w * chain_final_rotation.w +
                                      current_rotation.x * chain_final_rotation.x +
                                      current_rotation.y * chain_final_rotation.y +
                                      current_rotation.z * chain_final_rotation.z)
                        dot_product = max(-1.0, min(1.0, dot_product))
                        angle_rad = 2 * math.acos(abs(dot_product))
                        rotation_diff = math.degrees(angle_rad)
                        
                        if rotation_diff > 15:
                            ue.destroy_entity(chain_obj.id)
                            if print_info:
                                display_name = 'plate' if is_chain_platefood else chain_item_type
                                print(f"[WARNING] 连锁{display_name} 旋转变化过大 ({rotation_diff:.1f}度)，尝试下一个网格")
                            continue  # 尝试下一个网格
                    
                    # 如果是连锁platefood，需要在plate上方生成食物
                    chain_platefood_obj = None
                    if is_chain_platefood:
                        # 在plate上方10单位生成食物
                        chain_food_z = table_surface_z + 10.0
                        chain_food_location = ts.Vector3(chain_x, chain_y, chain_food_z)
                        
                        # 使用platefood的属性
                        chain_platefood_prop = item_properties['platefood']
                        chain_food_scale = chain_platefood_prop.get('scale', ts.Vector3(1, 1, 1))
                        
                        # 食物的旋转
                        chain_food_rotation_z = chain_platefood_prop.get('rotation_z', 0)
                        if chain_food_rotation_z == 360:
                            chain_food_rotation_z = random.uniform(0, 360)
                        chain_food_rotation_x = chain_platefood_prop.get('rotation_x', 0)
                        chain_food_rotation_y = chain_platefood_prop.get('rotation_y', 0)
                        
                        # 创建食物的旋转
                        target_pos = target_agent.get_location()
                        chain_food_target_pos = ts.Vector3(target_pos.x, target_pos.y, chain_food_z)
                        chain_food_rotation_quat = look_at_rotation(chain_food_location, chain_food_target_pos)
                        
                        chain_food_x_rot = create_axis_rotation(chain_food_rotation_x, 'x')
                        chain_food_y_rot = create_axis_rotation(chain_food_rotation_y, 'y')
                        chain_food_z_rot = create_axis_rotation(chain_food_rotation_z, 'z')
                        chain_food_final_rotation = chain_food_rotation_quat * chain_food_z_rot * chain_food_y_rot * chain_food_x_rot
                        
                        try:
                            chain_platefood_obj = ue.spawn_entity(
                                entity_type=ts.BaseObjectEntity,
                                blueprint=chain_platefood_blueprint,
                                location=chain_food_location,
                                is_simulating_physics=True,
                                scale=chain_food_scale,
                                quat=chain_food_final_rotation
                            )
                            
                            time.sleep(1.5)  # 等待食物落到plate上
                            
                            # 检查食物是否成功落在plate上
                            chain_food_position = chain_platefood_obj.get_location()
                            if abs(chain_food_position.z - table_min.z) < abs(chain_food_position.z - table_surface_z):
                                # 食物掉到地上了，删除plate和食物
                                ue.destroy_entity(chain_platefood_obj.id)
                                ue.destroy_entity(chain_obj.id)
                                if print_info:
                                    print(f"[WARNING] 连锁platefood掉落到地面，同时删除plate，尝试下一个网格")
                                continue  # 尝试下一个网格
                            
                            if print_info:
                                print(f"[SUCCESS] 连锁platefood成功放置在plate上")
                                
                        except Exception as e:
                            # 生成食物失败，删除plate
                            ue.destroy_entity(chain_obj.id)
                            if print_info:
                                print(f"[ERROR] 生成连锁platefood失败: {e}，删除plate，尝试下一个网格")
                            continue  # 尝试下一个网格
                    
                    # 成功放置连锁物品
                    spawned_items.append(chain_obj)
                    item_aabbs.append((chain_min, chain_max))
                    used_grids.add(chain_grid['id'])
                    agent_item_count[target_agent] += 1
                    total_item_count += 1
                    
                    # 如果是连锁platefood，将食物也加入spawned_items（不额外计数）
                    if is_chain_platefood and chain_platefood_obj is not None:
                        spawned_items.append(chain_platefood_obj)
                    
                    if chain_item_type in non_repeating_item_types:
                        used_item_types.add(chain_item_type)
                    
                    # 标记已使用的连锁物品蓝图（如果不在可重复列表中）
                    if chain_blueprint not in repeatable_blueprints:
                        used_blueprints.add(chain_blueprint)
                    if is_chain_platefood and chain_platefood_obj is not None and chain_platefood_blueprint not in repeatable_blueprints:
                        used_blueprints.add(chain_platefood_blueprint)
                    
                    if print_info:
                        display_chain_type = actual_chain_item_type if is_chain_platefood else chain_item_type
                        print(f"[SUCCESS] 连锁放置物品 {display_chain_type} 在网格 ({chain_grid['grid_x']}, {chain_grid['grid_y']}) "
                              f"为人物 {target_agent.id} (触发物品: {item_type})")
                    
                    # 添加连锁物品到列表（如果是chain_platefood，同时添加plate和food）
                    if is_chain_platefood and chain_platefood_obj is not None:
                        # 连锁plate
                        owners_list.append(str(target_agent.id))
                        features_list.append({'type': 'plate'})
                        # 连锁platefood
                        owners_list.append(str(target_agent.id))
                        features_list.append({'type': 'platefood'})
                    else:
                        # 普通连锁物品
                        owners_list.append(str(target_agent.id))
                        features_list.append({'type': chain_item_type})
                    
                    chain_placed = True
                    break  # 成功放置，跳出网格循环
                
                # 如果所有网格都尝试完毕仍未放置成功
                if not chain_placed and print_info:
                    print(f"[INFO] 尝试所有可用网格后仍无法放置连锁物品 {chain_item_type}")
        # ============== 连锁物品生成逻辑结束 ==============
    
    if print_info:
        print(f"\n[INFO] 物品放置完成")
        print(f"  实际物品数: {total_item_count}")
        print(f"  spawned_items总数: {len(spawned_items)} (包含附庸plate)")
        print(f"  owners_list长度: {len(owners_list)}")
        print(f"  features_list长度: {len(features_list)}")
        print(f"  各人物物品数: {agent_item_count}")
        print(f"  尝试次数: {attempt_count}")
        
        # 验证列表长度一致性
        if len(spawned_items) != len(owners_list) or len(spawned_items) != len(features_list):
            print(f"[ERROR] 列表长度不一致！spawned_items={len(spawned_items)}, "
                  f"owners_list={len(owners_list)}, features_list={len(features_list)}")
    
    return spawned_items, owners_list, features_list


def spawn_items_on_grid_new(ue, table_object, agents, grid_data, agent_features_list=None, 
                            max_total_items=10, max_items_per_agent=3, print_info=False):
    """
    基于网格JSON数据在桌面上放置物品（使用子函数重构版）
    
    Args:
        ue: TongSim实例
        table_object: 桌子对象
        agents: 人物对象列表
        grid_data: 网格数据字典（从JSON加载）
        agent_features_list: 人物特征列表（与agents对应，包含status等信息）
        max_total_items: 桌面最大物品总数
        max_items_per_agent: 每个人物最多物品数量
        print_info: 是否打印详细信息
    
    Returns:
        tuple: (spawned_items, owners_list, features_list)
            - spawned_items: 生成的物品对象列表
            - owners_list: 每个物品的所有者ID列表（与spawned_items对应）
            - features_list: 每个物品的特征字典列表（与spawned_items对应）
    """
    
    if not grid_data or 'safe_grids' not in grid_data:
        print("[ERROR] 无效的网格数据")
        return [], [], []
    
    safe_grids = grid_data['safe_grids']
    table_bounds = grid_data['table_bounds']
    table_surface_z = table_bounds['z_surface']
    
    # 获取桌子边界
    table_min, table_max = get_object_aabb(table_object)
    
    if print_info:
        print(f"\n[INFO] 开始在网格上放置物品 (使用子函数版本)")
        print(f"[INFO] 可用网格数: {len(safe_grids)}")
    
    # 第一步：确定每个人物类型和状态
    agent_types = {}
    agent_status = {}
    
    if agent_features_list and len(agent_features_list) == len(agents):
        for agent, features in zip(agents, agent_features_list):
            agent_id = str(getattr(agent, 'id', ''))
            status = features.get('status', 'standing')
            agent_status[agent_id] = status
            if print_info:
                print(f"[INFO] 从features_list读取人物 {agent_id} 状态: {status}")
    
    for agent in agents:
        agent_id = str(getattr(agent, 'id', ''))
        agent_type = get_agent_trait(agent_id) or 'unknown'
        
        if agent_type == 'unknown' and print_info:
            print(f"[WARNING] 无法识别人物类型 {agent_id}")
        
        agent_types[agent] = agent_type
        
        if agent_id not in agent_status:
            agent_status[agent_id] = 'standing'
    
    # 第二步：为每个人物找到基准网格和统御区域
    agent_grids = {}
    for agent in agents:
        base_grid = find_agent_base_grid(agent, safe_grids)
        if not base_grid:
            if print_info:
                print(f"[WARNING] 无法为人物 {agent.id} 找到基准网格")
            continue
        
        # 根据人物类型设置统御半径
        agent_type = agent_types[agent]
        if agent_type in ['man', 'woman']:
            control_radius = 6
        elif agent_type in ['boy', 'girl']:
            control_radius = 4
        else:
            control_radius = 5
        
        controlled_grids = get_agent_controlled_grids(
            base_grid, safe_grids, agent, table_object, control_radius
        )
        
        zones = divide_grids_into_zones(base_grid, controlled_grids, agent, table_object)
        
        agent_grids[agent] = {
            'base_grid': base_grid,
            'controlled_grids': controlled_grids,
            'zones': zones,
            'type': agent_type
        }
        
        if print_info:
            print(f"[INFO] 人物 {agent.id} ({agent_type}):")
            print(f"  基准网格: ({base_grid['grid_x']}, {base_grid['grid_y']})")
            print(f"  统御网格数: {len(controlled_grids)}")
            print(f"  分区: main={len(zones['main'])}, frequent={len(zones['frequent'])}, "
                  f"infrequent={len(zones['infrequent'])}, temporary={len(zones['temporary'])}")
        
        # 添加人物的网格信息到agent_features_list
        if agent_features_list:
            # 找到对应的features
            agent_idx = agents.index(agent)
            if agent_idx < len(agent_features_list):
                agent_features_list[agent_idx]['base_grid'] = base_grid
                agent_features_list[agent_idx]['controlled_grids'] = controlled_grids
                agent_features_list[agent_idx]['zones'] = zones
                agent_features_list[agent_idx]['type'] = agent_type
    
    # 第三步：生成物品
    spawned_items = []
    owners_list = []
    features_list = []
    item_aabbs = []
    used_grids = set()
    used_item_types = set()
    used_blueprints = set()
    agent_item_count = {agent: 0 for agent in agents}
    total_item_count = 0
    
    attempt_count = 0
    max_attempts = max_total_items * 100
    
    while total_item_count < max_total_items and attempt_count < max_attempts:
        attempt_count += 1
        
        # 检查是否所有人物都已达到最大物品数量
        if all(count >= max_items_per_agent for count in agent_item_count.values()):
            if print_info:
                print("[INFO] 所有人物均已达到最大物品数量，停止生成")
            break
        
        # 选择一个还未达到物品上限的人物
        available_agents = [a for a in agents if a in agent_grids and agent_item_count[a] < max_items_per_agent]
        if not available_agents:
            break
        
        target_agent = random.choice(available_agents)
        agent_type = agent_types[target_agent]
        agent_grid_info = agent_grids[target_agent]
        
        # 使用封装的函数选择物品类型
        item_type, item_prop = select_item_type_for_agent(
            agent=target_agent,
            agent_type=agent_type,
            used_item_types=used_item_types,
            agent_status=agent_status,
            print_info=print_info
        )
        is_platefood = (item_type == 'platefood')
        
        # 如果没有可用物品，继续下一次尝试
        if item_type is None or item_prop is None:
            continue
        
        # 使用子函数生成物品
        result_items = _spawn_single_item_for_agent(
            ue=ue,
            agent=target_agent,
            item_type=item_type,
            agent_grid_info=agent_grid_info,
            table_object=table_object,
            table_surface_z=table_surface_z,
            item_aabbs=item_aabbs,
            used_grids=used_grids,
            used_blueprints=used_blueprints,
            repeatable_blueprints=repeatable_blueprints,
            print_info=print_info
        )
        
        # 处理结果
        if result_items is None:
            # 生成失败，继续下一次尝试
            continue
        
        # 添加到结果列表
        for item_info in result_items:
            spawned_items.append(item_info['entity'])
            owners_list.append(str(item_info['owner']))
            features_list.append({'type': item_info['my_type']})

            item_aabbs.append(get_object_aabb(item_info['entity']))
        
        # 更新计数（platefood和plate只计数一次）
        if is_platefood:
            # platefood返回[plate_info, food_info]，只计数一次
            agent_item_count[target_agent] += 1
            total_item_count += 1
        else:
            # 普通物品
            agent_item_count[target_agent] += 1
            total_item_count += 1
        
        # 标记非重复物品类型
        if item_type in non_repeating_item_types:
            used_item_types.add(item_type)
        
        # ============== 连锁物品生成逻辑 ==============
        # 从result_items获取触发物品所在网格（使用grid_id字段）
        if result_items:
            # 直接从第一个result_item获取grid_id（已经包含完整的网格字典）
            trigger_grid = result_items[0]['grid_id']
            
            if trigger_grid and total_item_count < max_total_items and agent_item_count[target_agent] < max_items_per_agent:
                # 尝试生成连锁物品
                chain_result_items = _spawn_chain_item_for_trigger(
                    ue=ue,
                    trigger_item_type=item_type,
                    trigger_grid=trigger_grid,
                    target_agent=target_agent,
                    agent_grid_info=agent_grid_info,
                    table_object=table_object,
                    table_surface_z=table_surface_z,
                    item_aabbs=item_aabbs,
                    used_grids=used_grids,
                    used_item_types=used_item_types,
                    used_blueprints=used_blueprints,
                    repeatable_blueprints=repeatable_blueprints,
                    safe_grids=safe_grids,
                    print_info=print_info
                )
                
                if chain_result_items:
                    # 成功生成连锁物品，添加到结果列表
                    for chain_item_info in chain_result_items:
                        spawned_items.append(chain_item_info['entity'])
                        owners_list.append(str(chain_item_info['owner']))
                        features_list.append({'type': chain_item_info['my_type']})
                        # 注意：item_aabbs在子函数中已经更新
                    
                    # 更新计数（如果是platefood连锁，只计数一次）
                    agent_item_count[target_agent] += 1
                    total_item_count += 1
        # ============== 连锁物品生成逻辑结束 ==============
        
        if print_info:
            print(f"[已放置:{total_item_count}/{max_total_items}]")
    
    if print_info:
        print(f"\n[INFO] 物品放置完成")
        print(f"  实际物品数: {total_item_count}")
        print(f"  spawned_items总数: {len(spawned_items)} (包含附庸plate)")
        print(f"  owners_list长度: {len(owners_list)}")
        print(f"  features_list长度: {len(features_list)}")
        print(f"  各人物物品数: {agent_item_count}")
        print(f"  尝试次数: {attempt_count}")
        
        # 验证列表长度一致性
        if len(spawned_items) != len(owners_list) or len(spawned_items) != len(features_list):
            print(f"[ERROR] 列表长度不一致！spawned_items={len(spawned_items)}, "
                  f"owners_list={len(owners_list)}, features_list={len(features_list)}")
    
    return spawned_items, owners_list, features_list


# ============================================================================
# 物品数量调整功能（在已有物品基础上增加或减少）
# ============================================================================

def adjust_table_items_count(ue, table_object, agents, grid_data, existing_items_data, 
                              agent_features_list=None, adjust_count=0, print_info=False):
    """
    在已有物品的基础上增加或减少桌面物品数量
    
    逻辑说明：
    - adjust_count > 0: 随机增加指定数量的物品
    - adjust_count < 0: 随机删除指定数量的物品
    - adjust_count = 0: 不做任何修改
    
    增加逻辑：
    - 随机选择人物
    - 在人物的区域内随机生成物品
    - 避免与已有物品碰撞
    - 不使用连锁物品逻辑（简化版生成）
    
    减少逻辑：
    - 从existing_items_data中随机选择物品进行标记删除
    - 返回被删除的物品数据列表
    
    Args:
        ue: TongSim实例
        table_object: 桌子对象
        agents: 人物对象列表
        grid_data: 网格数据字典（从JSON加载）
        existing_items_data: 现有物品数据列表（从scene_data的table_items中提取）
                            格式: [{'type': 'object', 'owner': 'agent_id', 'base_id': '...', 
                                    'location': {...}, 'rotation': {...}, 'scale': {...}, 
                                    'features': {'type': 'drink'}}, ...]
        agent_features_list: 人物特征列表（与agents对应，包含status等信息）
        adjust_count: 调整数量（正数=增加，负数=减少，0=不变）
        print_info: 是否打印详细信息
    
    Returns:
        tuple: (spawned_items, owners_list, features_list, removed_items_data)
            - spawned_items: 新生成的物品对象列表（仅增加时有数据）
            - owners_list: 每个新物品的所有者ID列表（仅增加时有数据）
            - features_list: 每个新物品的特征字典列表（仅增加时有数据）
            - removed_items_data: 被标记删除的物品数据列表（仅减少时有数据）
    
    示例：
        # 增加2个物品
        new_items, owners, features, _ = adjust_table_items_count(
            ue, table, agents, grid, existing_items, adjust_count=2
        )
        
        # 减少2个物品
        _, _, _, removed = adjust_table_items_count(
            ue, table, agents, grid, existing_items, adjust_count=-2
        )
    """
    
    if print_info:
        print(f"\n[INFO] 开始调整桌面物品数量")
        print(f"  当前物品数: {len(existing_items_data)}")
        print(f"  调整数量: {adjust_count}")
        print(f"  目标物品数: {len(existing_items_data) + adjust_count}")
    
    spawned_items = []
    owners_list = []
    features_list = []
    removed_items_data = []
    
    # 如果调整数量为0，直接返回
    if adjust_count == 0:
        if print_info:
            print("[INFO] 调整数量为0，无需修改")
        return spawned_items, owners_list, features_list, removed_items_data
    
    # ========== 减少物品逻辑 ==========
    if adjust_count < 0:
        remove_count = abs(adjust_count)
        
        # 确保不会删除超过现有数量
        remove_count = min(remove_count, len(existing_items_data))
        
        if print_info:
            print(f"[INFO] 随机删除 {remove_count} 个物品")
        
        # 随机选择要删除的物品
        items_to_remove = random.sample(existing_items_data, remove_count)
        
        for item_data in items_to_remove:
            removed_items_data.append(item_data)
            if print_info:
                item_type = item_data.get('features', {}).get('type', 'unknown')
                owner = item_data.get('owner', 'unknown')
                print(f"[INFO] 标记删除物品: type={item_type}, owner={owner}")
        
        if print_info:
            print(f"[SUCCESS] 标记删除了 {len(removed_items_data)} 个物品")
        
        return spawned_items, owners_list, features_list, removed_items_data
    
    # ========== 增加物品逻辑 ==========
    if adjust_count > 0:
        if print_info:
            print(f"[INFO] 随机增加 {adjust_count} 个物品")
        
        # 检查网格数据有效性
        if not grid_data or 'safe_grids' not in grid_data:
            print("[ERROR] 无效的网格数据")
            return spawned_items, owners_list, features_list, removed_items_data
        
        safe_grids = grid_data['safe_grids']
        table_bounds = grid_data['table_bounds']
        table_surface_z = table_bounds['z_surface']
        
        # 获取桌子边界
        table_min, table_max = get_object_aabb(table_object)
        
        # 构建已有物品的边界框列表（用于碰撞检测）
        existing_item_aabbs = []
        used_grids = set()
        
        for item_data in existing_items_data:
            loc = item_data.get('location', {})
            item_x = loc.get('x', 0)
            item_y = loc.get('y', 0)
            item_z = loc.get('z', table_surface_z)
            
            # 获取物品类型和属性
            item_type = item_data.get('features', {}).get('type', 'unknown')
            
            # 估算物品的边界框（基于类型）
            safe_margin = 5.0
            if item_type in item_properties:
                safe_margin = item_properties[item_type].get('safe_margin', 5.0)
            
            # 创建一个大致的边界框（使用固定半径）
            half_size = 15.0  # 默认半径
            item_min = ts.Vector3(item_x - half_size, item_y - half_size, item_z - 5)
            item_max = ts.Vector3(item_x + half_size, item_y + half_size, item_z + 20)
            
            existing_item_aabbs.append((item_min, item_max))
            
            # 标记已使用的网格（找到最近的网格）
            min_dist = float('inf')
            closest_grid = None
            for grid in safe_grids:
                dist = math.sqrt((grid['center_x'] - item_x)**2 + (grid['center_y'] - item_y)**2)
                if dist < min_dist:
                    min_dist = dist
                    closest_grid = grid
            if closest_grid:
                used_grids.add(closest_grid['id'])
        
        if print_info:
            print(f"[INFO] 已有物品占用网格数: {len(used_grids)}")
            print(f"[INFO] 可用网格总数: {len(safe_grids)}")
        
        # 确定人物类型和状态
        agent_types = {}
        agent_status = {}
        
        if agent_features_list and len(agent_features_list) == len(agents):
            for agent, features in zip(agents, agent_features_list):
                agent_id = str(getattr(agent, 'id', ''))
                status = features.get('status', 'standing')
                agent_status[agent_id] = status
        
        for agent in agents:
            agent_id = str(getattr(agent, 'id', ''))
            agent_type = get_agent_trait(agent_id) or 'unknown'
            agent_types[agent] = agent_type
            
            if agent_id not in agent_status:
                agent_status[agent_id] = 'standing'
        
        # 为每个人物找到基准网格和统御区域
        agent_grids = {}
        for agent in agents:
            base_grid = find_agent_base_grid(agent, safe_grids)
            if not base_grid:
                if print_info:
                    print(f"[WARNING] 无法为人物 {agent.id} 找到基准网格")
                continue
            
            agent_type = agent_types[agent]
            if agent_type in ['man', 'woman']:
                control_radius = 6
            elif agent_type in ['boy', 'girl']:
                control_radius = 4
            else:
                control_radius = 5
            
            controlled_grids = get_agent_controlled_grids(
                base_grid, safe_grids, agent, table_object, control_radius
            )
            
            zones = divide_grids_into_zones(base_grid, controlled_grids, agent, table_object)
            
            agent_grids[agent] = {
                'base_grid': base_grid,
                'controlled_grids': controlled_grids,
                'zones': zones,
                'type': agent_type
            }
        
        if not agent_grids:
            if print_info:
                print("[ERROR] 没有可用的人物区域")
            return spawned_items, owners_list, features_list, removed_items_data
        
        # 开始生成新物品
        added_count = 0
        attempt_count = 0
        max_attempts = adjust_count * 100
        
        while added_count < adjust_count and attempt_count < max_attempts:
            attempt_count += 1
            
            # 随机选择一个人物
            available_agents = [a for a in agents if a in agent_grids]
            if not available_agents:
                break
            
            target_agent = random.choice(available_agents)
            agent_type = agent_types[target_agent]
            agent_grid_info = agent_grids[target_agent]
            
            # 选择物品类型
            possible_items = []
            if agent_type in agent_item_mapping:
                possible_items.extend(agent_item_mapping[agent_type])
            possible_items.extend(common_items)
            
            if not possible_items:
                continue
            
            # 随机选择物品类型
            item_type = random.choice(possible_items)
            
            # 获取物品属性
            if item_type not in item_properties:
                continue
            
            item_prop = item_properties[item_type]
            zone_types = item_prop['zone_types']
            min_distance = item_prop.get('min_distance', 10.0)
            max_distance = item_prop.get('max_distance', 150.0)
            
            # 选择合适的分区
            available_zones = []
            for zone_type in zone_types:
                if zone_type in agent_grid_info['zones'] and agent_grid_info['zones'][zone_type]:
                    available_zones.extend(agent_grid_info['zones'][zone_type])
            
            if not available_zones:
                continue
            
            # 过滤已使用的网格
            available_zones = [g for g in available_zones if g['id'] not in used_grids]
            
            if not available_zones:
                continue
            
            # 基于距离限制过滤网格
            base_grid = agent_grid_info['base_grid']
            base_center_x = base_grid['center_x']
            base_center_y = base_grid['center_y']
            
            dir_x_norm, dir_y_norm, dir_length, table_center_x, table_center_y = \
                calculate_baseline_to_table_center(base_center_x, base_center_y, table_object)
            
            if dir_length < 0.001:
                filtered_zones = available_zones
            else:
                filtered_zones = filter_grids_by_distance(
                    available_zones,
                    base_center_x, base_center_y,
                    dir_x_norm, dir_y_norm,
                    min_distance, max_distance
                )
            
            if not filtered_zones:
                continue
            
            # 随机选择网格
            selected_grid = random.choice(filtered_zones)
            
            # 选择蓝图
            if item_type not in item_blueprints or not item_blueprints[item_type]:
                continue
            
            available_blueprints_list = item_blueprints[item_type]
            blueprint = random.choice(available_blueprints_list)
            
            # 生成物品位置（先在高处）
            item_x = selected_grid['center_x']
            item_y = selected_grid['center_y']
            item_z = table_surface_z + 70.0
            
            item_location = ts.Vector3(item_x, item_y, item_z)
            
            # 生成旋转
            rotation_z = item_prop.get('rotation_z', 0)
            rotation_x = item_prop.get('rotation_x', 0)
            rotation_y = item_prop.get('rotation_y', 0)
            
            if rotation_z == 360:
                rotation_z = random.uniform(0, 360)
            
            target_pos = target_agent.get_location()
            target_tem_pos = ts.Vector3(target_pos.x, target_pos.y, item_z)
            rotation_quat = look_at_rotation(item_location, target_tem_pos)
            
            x_rotation = create_axis_rotation(rotation_x, 'x')
            y_rotation = create_axis_rotation(rotation_y, 'y')
            z_rotation = create_axis_rotation(rotation_z, 'z')
            final_rotation = rotation_quat * z_rotation * y_rotation * x_rotation
            
            scale = item_prop.get('scale', ts.Vector3(1, 1, 1))
            safe_margin = item_prop.get('safe_margin', 5.0)
            
            # 生成物品（先高处，不启用物理）
            try:
                item_obj = ue.spawn_entity(
                    entity_type=ts.BaseObjectEntity,
                    blueprint=blueprint,
                    location=item_location,
                    is_simulating_physics=False,
                    scale=scale,
                    quat=final_rotation
                )
            except Exception as e:
                if print_info:
                    print(f"[ERROR] 生成物品失败: {e}")
                continue
            
            time.sleep(0.01)
            
            # 获取边界框并投影到桌面
            item_min_high, item_max_high = get_object_aabb(item_obj)
            
            z_offset = item_z - (table_surface_z + 1.0)
            item_min = ts.Vector3(item_min_high.x, item_min_high.y, item_min_high.z - z_offset)
            item_max = ts.Vector3(item_max_high.x, item_max_high.y, item_max_high.z - z_offset)
            
            # 检查与已有物品的碰撞
            overlap_found = False
            for existing_min, existing_max in existing_item_aabbs:
                if check_item_overlap(
                    item_min, item_max,
                    existing_min, existing_max,
                    safe_margin=safe_margin,
                    check_z_axis=False
                ):
                    overlap_found = True
                    break
            
            if overlap_found:
                ue.destroy_entity(item_obj.id)
                if print_info:
                    print(f"[WARNING] 物品 {item_type} 与已有物品重叠")
                continue
            
            # 检查是否在桌子上
            if not is_bbox_contained(
                item_min, item_max,
                table_min, table_max,
                safe_margin=safe_margin,
                check_z_axis=False
            ):
                ue.destroy_entity(item_obj.id)
                if print_info:
                    print(f"[WARNING] 物品 {item_type} 超出桌子边界")
                continue
            
            # 删除高处物品，在桌面重新生成
            ue.destroy_entity(item_obj.id)
            
            item_z = table_surface_z + 1.0
            item_location = ts.Vector3(item_x, item_y, item_z)
            
            try:
                item_obj = ue.spawn_entity(
                    entity_type=ts.BaseObjectEntity,
                    blueprint=blueprint,
                    location=item_location,
                    is_simulating_physics=True,
                    scale=scale,
                    quat=final_rotation
                )
            except Exception as e:
                if print_info:
                    print(f"[ERROR] 重新生成物品失败: {e}")
                continue
            
            time.sleep(1.0)
            
            # 落地检测
            item_position = item_obj.get_location()
            if abs(item_position.z - table_min.z) < abs(item_position.z - table_surface_z) or abs(item_position.z - table_surface_z) > 40:
                ue.destroy_entity(item_obj.id)
                if print_info:
                    print(f"[WARNING] 物品 {item_type} 掉落，重新生成")
                continue
            
            # 成功放置物品
            spawned_items.append(item_obj)
            owners_list.append(str(target_agent.id))
            features_list.append({'type': item_type})
            
            existing_item_aabbs.append((item_min, item_max))
            used_grids.add(selected_grid['id'])
            
            added_count += 1
            
            if print_info:
                print(f"[SUCCESS] 添加物品 {item_type} 在网格 ({selected_grid['grid_x']}, {selected_grid['grid_y']}) "
                      f"为人物 {target_agent.id} [已添加:{added_count}/{adjust_count}]")
        
        if print_info:
            print(f"\n[INFO] 物品增加完成")
            print(f"  成功添加: {added_count}/{adjust_count}")
            print(f"  尝试次数: {attempt_count}")
        
        # 如果未能添加足够数量的物品，返回失败标记
        if added_count < adjust_count:
            if print_info:
                print(f"[WARNING] 未能添加足够的物品，需要 {adjust_count}，实际添加 {added_count}")
    
    return spawned_items, owners_list, features_list, removed_items_data


def move_items_to_other_owners(ue, table_object, agents, grid_data, existing_items_data, 
                                agent_features_list=None, move_count=0, print_info=False):
    """
    随机移动物品到其他owner的区域
    
    功能：
    1. 随机选择指定数量的物品
    2. 找到该物品当前owner的区域
    3. 选择一个其他owner的区域
    4. 将物品移动到新区域的某个格子上
    5. 如果是plate/platefood配对，一起移动
    
    Args:
        ue: TongSim实例
        table_object: 桌子实体对象
        agents: 人物实体列表
        grid_data: 网格数据字典（包含safe_grids）
        existing_items_data: 现有物品数据列表，每个元素包含:
            - id: 物品ID
            - owner: 所有者ID
            - location: 位置字典 {x, y, z}
            - rotation: 旋转字典 {w, x, y, z}
            - features: 特征字典 {type, ...}
        agent_features_list: 人物特征列表（可选）
        move_count: 需要移动的物品数量（正数）
        print_info: 是否打印详细信息
    
    Returns:
        tuple: (moved_items_data, move_pairs)
            - moved_items_data: 移动后的物品数据列表
            - move_pairs: 移动配对信息 [(item_idx, old_owner, new_owner), ...]
    """
    if move_count <= 0 or not existing_items_data:
        return existing_items_data, []
    
    if print_info:
        print(f"\n{'='*60}")
        print(f"[PROCESSING] 开始移动物品到其他owner区域...")
        print(f"[INFO] 需要移动 {move_count} 个物品")
        print(f"{'='*60}")
    
    import random
    import copy
    
    # 1. 识别plate/platefood配对关系
    platefood_pairs = {}  # {item_idx: paired_idx}
    for i, item_data in enumerate(existing_items_data):
        item_type = item_data.get('features', {}).get('type', '')
        owner = item_data.get('owner', '')
        
        if item_type in ['plate', 'platefood']:
            # 查找同一owner的配对物品
            for j, other_item in enumerate(existing_items_data):
                if i != j and other_item.get('owner') == owner:
                    other_type = other_item.get('features', {}).get('type', '')
                    
                    if (item_type == 'plate' and other_type == 'platefood') or \
                       (item_type == 'platefood' and other_type == 'plate'):
                        platefood_pairs[i] = j
                        platefood_pairs[j] = i
                        break
    
    if print_info and platefood_pairs:
        print(f"[INFO] 识别到 {len(platefood_pairs)//2} 对 plate/platefood 配对")
    
    # 2. 收集可移动的物品（排除配对的另一半，只保留代表）
    movable_items = []
    processed_pairs = set()
    
    for i, item_data in enumerate(existing_items_data):
        if i in platefood_pairs:
            pair_idx = platefood_pairs[i]
            pair_key = tuple(sorted([i, pair_idx]))
            
            if pair_key not in processed_pairs:
                processed_pairs.add(pair_key)
                movable_items.append(i)  # 只添加配对的第一个
        else:
            movable_items.append(i)
    
    # 3. 随机选择要移动的物品
    actual_move_count = min(move_count, len(movable_items))
    if actual_move_count == 0:
        if print_info:
            print(f"[WARNING] 没有可移动的物品")
        return existing_items_data, []
    
    selected_indices = random.sample(movable_items, actual_move_count)
    
    if print_info:
        print(f"[INFO] 随机选择 {actual_move_count} 个物品进行移动")
    
    # 4. 建立agent ID到agent实体的映射
    agent_id_to_entity = {}
    for agent in agents:
        agent_id_to_entity[str(agent.id)] = agent
    
    # 5. 获取网格数据
    safe_grids = grid_data.get('safe_grids', [])
    if not safe_grids:
        if print_info:
            print(f"[ERROR] 网格数据中没有safe_grids")
        return existing_items_data, []
    
    table_surface_z = table_object.get_world_aabb().max.z
    
    # 6. 确定每个人物的类型（从agent_features_list或默认）
    agent_types = {}
    for i, agent in enumerate(agents):
        if agent_features_list and i < len(agent_features_list):
            agent_type = agent_features_list[i].get('type', 'unknown')
        else:
            # 默认推断
            blueprint = agent.get_asset_id()
            if any(x in blueprint.lower() for x in ['baby', 'child', 'boy', 'girl']):
                agent_type = 'child'
            else:
                agent_type = 'adult'
        agent_types[agent] = agent_type
    
    # 7. 为每个人物划分区域
    agent_grids = {}
    for agent in agents:
        base_grid = find_agent_base_grid(agent, safe_grids)
        if not base_grid:
            if print_info:
                print(f"[WARNING] 无法为人物 {agent.id} 找到基准网格")
            continue
        
        agent_type = agent_types[agent]
        if agent_type in ['man', 'woman']:
            control_radius = 6
        elif agent_type in ['boy', 'girl']:
            control_radius = 4
        else:
            control_radius = 5
        
        controlled_grids = get_agent_controlled_grids(
            base_grid, safe_grids, agent, table_object, control_radius
        )
        
        zones = divide_grids_into_zones(base_grid, controlled_grids, agent, table_object)
        
        agent_grids[agent] = {
            'base_grid': base_grid,
            'controlled_grids': controlled_grids,
            'zones': zones,
            'type': agent_type
        }
    
    # 8. 构建已使用网格集合（除了要移动的物品）
    used_grids = set()
    for i, item_data in enumerate(existing_items_data):
        if i not in selected_indices and i not in [platefood_pairs.get(idx) for idx in selected_indices if idx in platefood_pairs]:
            # 找到物品占用的网格
            item_pos = item_data['location']
            for grid in safe_grids:
                # 网格数据结构: center_x, center_y, x_min, x_max, y_min, y_max
                grid_center_x = grid.get('center_x', grid.get('x', 0))
                grid_center_y = grid.get('center_y', grid.get('y', 0))
                grid_width = grid.get('x_max', 0) - grid.get('x_min', 0)
                grid_height = grid.get('y_max', 0) - grid.get('y_min', 0)
                
                if abs(grid_center_x - item_pos['x']) < grid_width/2 and \
                   abs(grid_center_y - item_pos['y']) < grid_height/2:
                    used_grids.add(grid['id'])
                    break
    
    # 9. 移动物品
    moved_items_data = copy.deepcopy(existing_items_data)
    move_pairs = []
    
    for item_idx in selected_indices:
        item_data = moved_items_data[item_idx]
        old_owner = item_data.get('owner', '')
        item_type = item_data.get('features', {}).get('type', '')
        
        if print_info:
            print(f"\n[INFO] 移动物品 {item_idx}: type={item_type}, old_owner={old_owner}")
        
        # 找到其他owner
        other_agents = [agent for agent in agents if str(agent.id) != old_owner]
        if not other_agents:
            if print_info:
                print(f"[WARNING] 没有其他owner，跳过移动")
            continue
        
        # 随机选择一个其他owner
        target_agent = random.choice(other_agents)
        new_owner = str(target_agent.id)
        
        if target_agent not in agent_grids:
            if print_info:
                print(f"[WARNING] 目标人物 {new_owner} 没有区域数据，跳过移动")
            continue
        
        # 获取目标人物的所有区域网格
        target_zones = agent_grids[target_agent]['zones']
        all_target_grids = []
        for zone_name in ['main', 'frequent', 'infrequent', 'temporary']:
            all_target_grids.extend(target_zones.get(zone_name, []))
        
        # 筛选未使用的网格
        available_grids = [g for g in all_target_grids if g['id'] not in used_grids]
        
        if not available_grids:
            if print_info:
                print(f"[WARNING] 目标人物 {new_owner} 的区域没有可用网格，跳过移动")
            continue
        
        # 随机选择一个网格
        selected_grid = random.choice(available_grids)
        
        # 计算新位置 - 使用网格中心点
        new_x = selected_grid.get('center_x', selected_grid.get('x', 0))
        new_y = selected_grid.get('center_y', selected_grid.get('y', 0))
        new_z = table_surface_z
        
        # 更新物品位置和owner
        moved_items_data[item_idx]['location'] = {'x': new_x, 'y': new_y, 'z': new_z}
        moved_items_data[item_idx]['owner'] = new_owner
        
        used_grids.add(selected_grid['id'])
        move_pairs.append((item_idx, old_owner, new_owner))
        
        if print_info:
            print(f"[SUCCESS] 移动物品 {item_idx} 从 {old_owner} 到 {new_owner}")
            print(f"         新位置: ({new_x:.1f}, {new_y:.1f}, {new_z:.1f})")
            print(f"         网格: ({selected_grid['grid_x']}, {selected_grid['grid_y']})")
        
        # 如果是配对物品，同时移动另一个
        if item_idx in platefood_pairs:
            pair_idx = platefood_pairs[item_idx]
            pair_data = moved_items_data[pair_idx]
            pair_type = pair_data.get('features', {}).get('type', '')
            
            # 如果是plate，platefood在上方；如果是platefood，plate在下方
            if item_type == 'plate':
                # platefood在上方
                moved_items_data[pair_idx]['location'] = {'x': new_x, 'y': new_y, 'z': new_z + 2.0}
            else:
                # plate在下方
                moved_items_data[pair_idx]['location'] = {'x': new_x, 'y': new_y, 'z': new_z}
                # 当前物品（platefood）调整到上方
                moved_items_data[item_idx]['location']['z'] = new_z + 2.0
            
            moved_items_data[pair_idx]['owner'] = new_owner
            
            if print_info:
                print(f"[INFO] 同时移动配对物品 {pair_idx} (type={pair_type})")
    
    if print_info:
        print(f"\n[SUCCESS] 完成 {len(move_pairs)} 个物品的移动")
        print(f"{'='*60}\n")
    
    return moved_items_data, move_pairs

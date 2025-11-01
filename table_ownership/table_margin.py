import os
import json
import time
import math
from collections import deque
from datetime import datetime

import tongsim as ts
from tongsim.type import ViewModeType

# 导入必要的工具函数
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .other_util import (
    fix_aabb_bounds,
    get_room_bbox,
    get_room_boundary,
    get_area,
    validate_table,
)

from .query_util import (
    query_existing_objects_in_room,
    find_objects_near_table,
)

from .entity_util import (
    filter_objects_by_type,
)



def measure_table_grid_boundaries(ue, table_object, grid_size=10.0, test_blueprint='BP_Ball_BaseBall_ver2', 
                                  test_duration=2.0, safety_margin=0.0, print_info=False):
    """
    测量桌面的安全边界并划分为格子网格
    
    通过在桌面上放置测试物体，从中心向外扩展，找出所有安全的格子位置
    
    Args:
        ue: TongSim实例
        table_object: 桌子对象
        grid_size: 格子大小（正方形边长），默认10.0
        test_blueprint: 测试物体的蓝图，默认为棒球
        test_duration: 测试等待时间（秒），默认2.0
        safety_margin: 安全边距，格子边缘距离桌子边缘的最小距离
        print_info: 是否打印详细信息
    
    Returns:
        dict: {
            'table_id': 桌子ID,
            'grid_size': 格子大小,
            'table_bounds': {'x_min', 'x_max', 'y_min', 'y_max', 'z_surface'},
            'safe_grids': [{'id', 'x_min', 'x_max', 'y_min', 'y_max', 'center_x', 'center_y'}, ...],
            'total_grids': 总格子数,
            'timestamp': 时间戳
        }
    """
    
    if print_info:
        print(f"\n[INFO] 开始测量桌面边界，格子大小: {grid_size}")
    
    # 1. 获取桌子的边界
    table_aabb = table_object.get_world_aabb()
    table_min, table_max = fix_aabb_bounds(table_aabb)
    
    # 桌面参数
    x_min, x_max = table_min.x, table_max.x
    y_min, y_max = table_min.y, table_max.y
    table_surface_z = table_max.z
    table_ground_z = table_min.z
    
    if print_info:
        print(f"[INFO] 桌子边界: X=[{x_min:.1f}, {x_max:.1f}], Y=[{y_min:.1f}, {y_max:.1f}], Z={table_surface_z:.1f}")
    
    # 2. 计算桌子中心
    center_x = (x_min + x_max) / 2
    center_y = (y_min + y_max) / 2
    
    # 3. 计算从中心开始的网格坐标系
    # 找到包含中心点的格子的索引
    half_grid = grid_size / 2
    
    # 计算网格的范围（以格子索引表示）
    # 从中心向外扩展到边界
    max_grids_x = int(math.ceil(max(abs(center_x - x_min), abs(x_max - center_x)) / grid_size)) + 1
    max_grids_y = int(math.ceil(max(abs(center_y - y_min), abs(y_max - center_y)) / grid_size)) + 1
    
    if print_info:
        print(f"[INFO] 网格范围: X=[-{max_grids_x}, {max_grids_x}], Y=[-{max_grids_y}, {max_grids_y}]")
    
    # 4. 使用BFS从中心向外扩展测试
    tested_grids = {}  # 存储已测试的格子 {(grid_x, grid_y): is_safe}
    safe_grids = []  # 存储安全的格子信息
    
    # BFS队列，从中心格子开始
    queue = deque([(0, 0)])  # (grid_x, grid_y)
    tested_grids[(0, 0)] = None  # 标记为已加入队列
    
    # 方向：上下左右
    directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
    
    test_count = 0
    safe_count = 0
    
    while queue:
        grid_x, grid_y = queue.popleft()
        
        # 计算当前格子的实际坐标
        grid_center_x = center_x + grid_x * grid_size
        grid_center_y = center_y + grid_y * grid_size
        
        # 计算格子的边界
        grid_x_min = grid_center_x - half_grid
        grid_x_max = grid_center_x + half_grid
        grid_y_min = grid_center_y - half_grid
        grid_y_max = grid_center_y + half_grid
        if print_info:
            print(f"格子范围[{grid_x_min}, {grid_x_max}], [{grid_y_min}, {grid_y_max}]")
        
        # 检查格子是否完全在桌子范围内（考虑安全边距）
        if (grid_x_min < x_min + safety_margin or grid_x_max > x_max - safety_margin or
            grid_y_min < y_min + safety_margin or grid_y_max > y_max - safety_margin):
            # 格子超出桌子边界，标记为不安全
            tested_grids[(grid_x, grid_y)] = False
            if print_info:
                print(f"[SKIP] 格子({grid_x}, {grid_y})超出桌子边界")
            continue
        
        # 测试当前格子
        is_safe = test_grid_safety(
            ue=ue,
            grid_center_x=grid_center_x,
            grid_center_y=grid_center_y,
            table_surface_z=table_surface_z,
            table_ground_z=table_ground_z,
            test_blueprint=test_blueprint,
            test_duration=test_duration,
            print_info=print_info
        )
        
        test_count += 1
        tested_grids[(grid_x, grid_y)] = is_safe
        
        if is_safe:
            safe_count += 1
            # 记录安全格子
            grid_info = {
                'id': safe_count,
                'grid_x': grid_x,
                'grid_y': grid_y,
                'x_min': float(grid_x_min),
                'x_max': float(grid_x_max),
                'y_min': float(grid_y_min),
                'y_max': float(grid_y_max),
                'center_x': float(grid_center_x),
                'center_y': float(grid_center_y),
                'z': float(table_surface_z)
            }
            safe_grids.append(grid_info)
            
            if print_info:
                print(f"[SAFE] 格子({grid_x}, {grid_y}) 安全 [已测试:{test_count}, 安全:{safe_count}]")
            
            # 只有当前格子安全时，才将相邻格子加入队列
            for dx, dy in directions:
                next_grid = (grid_x + dx, grid_y + dy)
                if next_grid not in tested_grids:
                    # 检查是否超出最大范围
                    if abs(next_grid[0]) <= max_grids_x and abs(next_grid[1]) <= max_grids_y:
                        queue.append(next_grid)
                        tested_grids[next_grid] = None  # 标记为已加入队列
        else:
            if print_info:
                print(f"[UNSAFE] 格子({grid_x}, {grid_y}) 不安全（物体掉落或移动）")
    
    # 5. 整理结果
    result = {
        'table_id': str(table_object.id),
        'grid_size': float(grid_size),
        'table_bounds': {
            'x_min': float(x_min),
            'x_max': float(x_max),
            'y_min': float(y_min),
            'y_max': float(y_max),
            'z_surface': float(table_surface_z),
            'center_x': float(center_x),
            'center_y': float(center_y)
        },
        'safe_grids': safe_grids,
        'total_safe_grids': safe_count,
        'total_tested_grids': test_count,
        'timestamp': datetime.now().isoformat()
    }
    
    if print_info:
        print(f"\n[SUCCESS] 测量完成:")
        print(f"  测试格子数: {test_count}")
        print(f"  安全格子数: {safe_count}")
        print(f"  覆盖率: {safe_count/test_count*100:.1f}%")
    
    return result


def test_grid_safety(ue, grid_center_x, grid_center_y, table_surface_z, table_ground_z, 
                     test_blueprint, test_duration=2.0, movement_threshold=5.0, print_info=False):
    """
    测试单个格子的安全性（物体是否会掉落或移动）
    
    Args:
        ue: TongSim实例
        grid_center_x: 格子中心X坐标
        grid_center_y: 格子中心Y坐标
        table_surface_z: 桌面高度
        table_ground_z: 桌子底部高度
        test_blueprint: 测试物体蓝图
        test_duration: 测试持续时间（秒）
        movement_threshold: 移动阈值，超过此距离视为不安全
        print_info: 是否打印详细信息
    
    Returns:
        bool: True表示安全，False表示不安全
    """
    try:
        # 在格子中心上方一点生成测试物体
        spawn_location = ts.Vector3(grid_center_x, grid_center_y, table_surface_z + 5.0)
        
        # 生成测试物体
        test_obj = ue.spawn_entity(
            entity_type=ts.BaseObjectEntity,
            blueprint=test_blueprint,
            location=spawn_location,
            is_simulating_physics=True,
            scale=None,
            quat=None
        )
        
        # 记录初始位置
        initial_position = test_obj.get_location()
        
        # 等待物理稳定
        time.sleep(test_duration)
        
        # 获取最终位置
        final_position = test_obj.get_location()
        
        # 检查1: 物体是否掉落到地面
        distance_to_ground = abs(final_position.z - table_ground_z)
        distance_to_surface = abs(final_position.z - table_surface_z)
        
        if distance_to_ground < distance_to_surface:
            # 物体更接近地面，说明掉落了
            ue.destroy_entity(test_obj.id)
            return False
        
        # 检查2: 物体在水平方向是否移动过多
        horizontal_movement = math.sqrt(
            (final_position.x - initial_position.x) ** 2 +
            (final_position.y - initial_position.y) ** 2
        )
        
        if horizontal_movement > movement_threshold:
            # 物体移动过多，说明位置不稳定
            ue.destroy_entity(test_obj.id)
            return False
        
        # 检查3: 物体Z轴是否偏离桌面太多
        z_deviation = abs(final_position.z - table_surface_z)
        if z_deviation > 50.0:  # 超过50单位视为异常
            ue.destroy_entity(test_obj.id)
            return False
        
        # 清理测试物体
        ue.destroy_entity(test_obj.id)
        
        return True
    
    except Exception as e:
        if print_info:
            print(f"[ERROR] 测试格子时出错: {e}")
        return False


def run_table_boundary_measurement(map_range=None, min_room_area=4, min_table_area=0.4, 
                                   grid_size=10.0, output_dir="./ownership/table_boundaries"):
    """
    遍历所有地图的所有桌子，测量边界并划分格子
    
    Args:
        map_range: 地图范围
        min_room_area: 最小房间面积
        min_table_area: 最小桌子面积
        grid_size: 格子大小
        output_dir: 输出目录
    """
    
    # 读取筛选后的场景列表
    try:
        with open('./ownership/object/selected_scenes.txt', 'r', encoding='utf-8') as f:
            selected_scenes = [line.strip() for line in f if line.strip()]
        print(f"[INFO] 已加载 {len(selected_scenes)} 个筛选场景")
    except FileNotFoundError:
        print("[WARNING] selected_scenes.txt 文件不存在，将处理所有地图")
        selected_scenes = []
    
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    with ts.TongSim(
        grpc_endpoint="127.0.0.1:5056",
        legacy_grpc_endpoint="127.0.0.1:50052",
    ) as ue:
        # 定义地图范围
        if map_range is None:
            map_range = range(0, 300)
        
        # 统计信息
        total_tables = 0
        successful_tables = 0
        
        for map_num in map_range:
            # 格式化地图名称
            map_name = f"SDBP_Map_{map_num:03d}"
            
            # 检查是否在筛选列表中
            if selected_scenes and map_name not in selected_scenes:
                print(f"[CONTINUE] 跳过不在筛选列表中的地图: {map_name}")
                continue
            
            # 打开地图
            print(f"\n{'='*60}")
            print(f"[PROCESSING] 正在打开地图: {map_name}")
            print(f"{'='*60}")
            success = ue.open_level(map_name)
            if not success:
                print(f"[WARNING] 无法打开地图: {map_name}，跳过")
                continue
            
            try:
                # 获取房间信息
                rooms = ue.spatical_manager.get_current_room_info()
                if not rooms:
                    print(f"[CONTINUE] 地图 {map_name} 中没有找到房间信息，跳过")
                    continue
                
                # 获取房间边界框信息
                room_bbox_dict = get_room_bbox(rooms)
                
                # 遍历当前地图的所有房间
                for room_info in rooms:
                    room_name = room_info['room_name']
                    
                    print(f"\n[PROCESSING] 处理房间: {room_name}")
                    room_bound = get_room_boundary(room_name, room_bbox_dict)
                    
                    # 面积小于阈值跳过
                    if get_area(room_bound) < min_room_area:
                        print(f"[CONTINUE] 房间 {room_name} 面积小于 {min_room_area} 平方米，跳过")
                        continue
                    
                    # 重新打开地图确保环境干净
                    success = ue.open_level(map_name)
                    if not success:
                        print(f"[WARNING] 无法打开地图: {map_name}，跳过")
                        continue
                    
                    # 查询房间内的桌子
                    table_entitys = query_existing_objects_in_room(
                        ue=ue, 
                        room_bound=room_bound, 
                        target_types=['coffeetable', 'diningTable', 'table', 'Table'], 
                        object_name="桌子"
                    )
                    
                    # 处理多个桌子
                    if table_entitys:
                        print(f"[PROCESSING] 找到 {len(table_entitys)} 张桌子，开始处理...")
                        for table_idx, table_entity in enumerate(table_entitys):
                            print(f"\n[PROCESSING] 处理第 {table_idx+1} / {len(table_entitys)} 张桌子: {table_entity.id}")
                            total_tables += 1
                            
                            # 验证桌子是否符合条件
                            if not validate_table(table_entity, min_table_area=min_table_area):
                                print(f"[CONTINUE] 桌子面积不符合条件，跳过")
                                continue

                            ue.change_view_mode(ViewModeType.MANUAL_CONTROL_VIEW)

                            # 查找桌子附近的物品
                            on_table_items, nearby_items = find_objects_near_table(
                                ue=ue,
                                table_object=table_entity,
                                search_distance=60.0
                            )
                            existed_chairs = filter_objects_by_type(objects_list=nearby_items, type_file_path='./ownership/object/chair.txt')
                            
                            # 删除桌子上的所有物品
                            if on_table_items:
                                print(f"[INFO] 正在删除桌子上的 {len(on_table_items)} 个物品...")
                                for item in on_table_items:
                                    try:
                                        ue.destroy_entity(item.id)
                                    except Exception as e:
                                        print(f"[WARNING] 删除物品 {item.id} 失败: {e}")
                                print(f"[SUCCESS] 已删除桌子上的物品")
                            else:
                                print(f"[INFO] 桌子上没有物品需要删除")

                            # 删除附近的物品
                            if existed_chairs:
                                print(f"[INFO] 正在删除附近的 {len(existed_chairs)} 个物品...")
                                for item in existed_chairs:
                                    try:
                                        ue.destroy_entity(item.id)
                                    except Exception as e:
                                        print(f"[WARNING] 删除物品 {item.id} 失败: {e}")
                                print(f"[SUCCESS] 已删除附近的物品")
                            else:
                                print(f"[INFO] 桌子附近没有物品需要删除")
                            
                            # 测量桌面边界
                            try:
                                result = measure_table_grid_boundaries(
                                    ue=ue,
                                    table_object=table_entity,
                                    grid_size=grid_size,
                                    test_blueprint='BP_Ball_BaseBall_ver2',
                                    test_duration=0.5,
                                    safety_margin=0.0,
                                    print_info=True
                                )
                                
                                # 保存结果到JSON文件
                                json_filename = f"{map_name}_{room_name}_table_{table_entity.id}.json"
                                json_path = os.path.join(output_dir, json_filename)
                                
                                # 添加额外信息
                                result['map_name'] = map_name
                                result['room_name'] = room_name
                                
                                with open(json_path, 'w', encoding='utf-8') as f:
                                    json.dump(result, f, indent=2, ensure_ascii=False)
                                
                                print(f"[SUCCESS] 结果已保存: {json_filename}")
                                successful_tables += 1
                            
                            except Exception as e:
                                print(f"[ERROR] 测量桌子 {table_entity.id} 时出错: {e}")
                                import traceback
                                traceback.print_exc()
                                continue
                    else:
                        print(f"[CONTINUE] 房间 {room_name} 没有桌子，跳过")
                        continue
            
            except Exception as e:
                print(f"[ERROR] 处理地图 {map_name} 时发生错误: {str(e)}")
                import traceback
                traceback.print_exc()
                continue
        
        # 输出统计信息
        print(f"\n{'='*60}")
        print(f"[DONE] 所有桌子测量完成")
        print(f"{'='*60}")
        print(f"总桌子数: {total_tables}")
        print(f"成功测量: {successful_tables}")
        print(f"失败数量: {total_tables - successful_tables}")
        print(f"成功率: {successful_tables/total_tables*100:.1f}%" if total_tables > 0 else "N/A")


if __name__ == "__main__":
    # 测试所有地图
    run_table_boundary_measurement(map_range=range(1, 300), grid_size=10.0)

import tongsim as ts

import re
import time

from .other_util import (
    determine_object_side,
    check_position_in_bbox,
    fix_aabb_bounds,
    get_object_aabb
)

from .entity_util import (
    get_blueprint_from_entity_id
)

# 查询房间已有物品
def query_existing_objects_in_room(ue, room_bound, target_types=None, print_info=False, object_name="物品"):
    """
    查询房间内已有的指定类型物品对象
    
    Args:
        ue: TongSim实例
        room_bound: 房间边界
        target_types: 要查找的物品类型列表，默认为 None（查找所有类型）
        print_info: 是否打印详细信息
        object_name: 物品名称（用于打印信息）
    
    Returns:
        list: 房间内的物品实体列表，如果没有找到返回空列表[]
    """
    if target_types is None:
        # 默认查找所有类型
        target_types = []
    x_min, y_min, _, x_max, y_max, _ = room_bound
    
    object_entities = []  # 返回实体列表
    try:
        # 启动 PG 实时流
        ue.pg_manager.start_pg_stream(pg_freq=10)
        print("[PROCESSING] Waiting for PG data...")
        time.sleep(0.5)  # 等待一段时间确保收到完整 PG 数据
        
        # 定义查询信息
        pg_metainfo = [
            {
                "component": "pose",
                "fields": ["location", "rotation"],
            },
            {
                "component": "object_state",
                "fields": ["object_type"],
            },
        ]

        # 执行查询
        result = ue.pg_manager.query(pg_metainfo)
        
        found_objects = []
        # 提取所有物品信息
        for obj_id, obj_data in result.items():
            # 跳过元数据和其他非物体条目
            if obj_id == '__meta__' or 'object_type' not in obj_data:
                continue
            
            obj_type = obj_data['object_type']
            
            # 如果指定了目标类型，检查是否匹配；如果未指定目标类型，则返回所有物品
            if not target_types or obj_type in target_types:
                # 提取位置和旋转信息
                location = obj_data.get('location', {})
                
                # 检查物品是否在房间边界内
                x = location.get('x', 0.0)
                y = location.get('y', 0.0)
                z = location.get('z', 0.0)
                
                if (x_min <= x <= x_max and y_min <= y <= y_max):
                    
                    rotation = obj_data.get('rotation', {})
                    
                    object_info = {
                        'id': obj_id,
                        'type': obj_type,
                        'location': {
                            'x': x,
                            'y': y,
                            'z': z
                        },
                        'rotation': {
                            'x': rotation.get('x', 0.0),
                            'y': rotation.get('y', 0.0),
                            'z': rotation.get('z', 0.0),
                            'w': rotation.get('w', 1.0)
                        }
                    }
                    
                    found_objects.append(object_info)
        if print_info:
            print(f"[INFO] 在房间找到 {len(found_objects)} 个{object_name}")
        # 如果没有找到物品，返回空列表
        if not found_objects:
            if print_info:
                print(f"[CONTINUE] 房间内没有找到符合条件的{object_name}")
            return object_entities
        
        # 打印物品信息
        if print_info:
            for i, obj in enumerate(found_objects):
                loc = obj['location']
                print(f"[INFO] {object_name} {i+1}: ID={obj['id']}, 类型={obj['type']}, "
                    f"位置=({loc['x']:.2f}, {loc['y']:.2f}, {loc['z']:.2f})")
        
        # 获取所有物品的实体对象
        for obj_info in found_objects:
            try:
                entity = ue.entity_from_id(ts.BaseObjectEntity, entity_id=str(obj_info['id']))
                if entity:
                    object_entities.append(entity)
                    if print_info:
                        print(f"[PROCESSING] 成功获取{object_name}实体: {obj_info['id']}")
            except Exception as e:
                print(f"[WARNING] 无法获取{object_name} {obj_info['id']} 的实体: {e}")
                continue
        
        return object_entities
        
    except Exception as e:
        print(f"[ERROR] 查询{object_name}时出现异常: {e}")
        return object_entities  # 异常情况下也返回空列表


# 查询房间已有物品（返回完整信息）
def query_existing_objects_in_room_with_info(ue, room_bound, target_types=None, print_info=False, object_name="物品"):
    """
    查询房间内已有的指定类型物品对象，返回完整信息
    
    Args:
        ue: TongSim实例
        room_bound: 房间边界
        target_types: 要查找的物品类型列表，默认为 None（查找所有类型）
        print_info: 是否打印详细信息
        object_name: 物品名称（用于打印信息）
    
    Returns:
        list: 房间内的物品完整信息列表，每个元素包含 id, type, location, rotation, entity
             如果没有找到返回空列表[]
    """
    if target_types is None:
        # 默认查找所有类型
        target_types = []
    x_min, y_min, _, x_max, y_max, _ = room_bound
    
    object_infos = []  # 返回完整信息列表
    try:
        # 启动 PG 实时流
        ue.pg_manager.start_pg_stream(pg_freq=10)
        print("[PROCESSING] Waiting for PG data...")
        time.sleep(0.5)  # 等待一段时间确保收到完整 PG 数据
        
        # 定义查询信息
        pg_metainfo = [
            {
                "component": "pose",
                "fields": ["location", "rotation"],
            },
            {
                "component": "object_state",
                "fields": ["object_type"],
            },
        ]

        # 执行查询
        result = ue.pg_manager.query(pg_metainfo)
        
        found_objects = []
        # 提取所有物品信息
        for obj_id, obj_data in result.items():
            # 跳过元数据和其他非物体条目
            if obj_id == '__meta__' or 'object_type' not in obj_data:
                continue
            
            obj_type = obj_data['object_type']
            
            # 如果指定了目标类型，检查是否匹配；如果未指定目标类型，则返回所有物品
            if not target_types or obj_type in target_types:
                # 提取位置和旋转信息
                location = obj_data.get('location', {})
                
                # 检查物品是否在房间边界内
                x = location.get('x', 0.0)
                y = location.get('y', 0.0)
                z = location.get('z', 0.0)
                
                if (x_min <= x <= x_max and y_min <= y <= y_max):
                    
                    rotation = obj_data.get('rotation', {})
                    
                    object_info = {
                        'id': obj_id,
                        'type': obj_type,
                        'location': {
                            'x': x,
                            'y': y,
                            'z': z
                        },
                        'rotation': {
                            'x': rotation.get('x', 0.0),
                            'y': rotation.get('y', 0.0),
                            'z': rotation.get('z', 0.0),
                            'w': rotation.get('w', 1.0)
                        }
                    }
                    
                    found_objects.append(object_info)
        
        if print_info:
            print(f"[INFO] 在房间找到 {len(found_objects)} 个{object_name}")
        
        # 如果没有找到物品，返回空列表
        if not found_objects:
            if print_info:
                print(f"[CONTINUE] 房间内没有找到符合条件的{object_name}")
            return object_infos
        
        # 打印物品信息
        if print_info:
            for i, obj in enumerate(found_objects):
                loc = obj['location']
                print(f"[INFO] {object_name} {i+1}: ID={obj['id']}, 类型={obj['type']}, "
                    f"位置=({loc['x']:.2f}, {loc['y']:.2f}, {loc['z']:.2f})")
        
        # 获取所有物品的实体对象，并组合完整信息
        for obj_info in found_objects:
            try:
                entity = ue.entity_from_id(ts.BaseObjectEntity, entity_id=str(obj_info['id']))
                if entity:
                    # 获取物体的AABB边界
                    entity_min, entity_max = get_object_aabb(entity)
                    # 获取物体大小
                    entity_size = entity.get_scale()
                    # 提取基础蓝图ID
                    base_id = get_blueprint_from_entity_id(obj_id)

                    # 创建包含实体对象的完整信息
                    complete_info = {
                        'id': obj_id,
                        'base_id': base_id,
                        'type': obj_type,
                        'location': {
                            'x': x,
                            'y': y,
                            'z': z
                        },
                        'rotation': {
                            'x': rotation.get('x', 0.0),
                            'y': rotation.get('y', 0.0),
                            'z': rotation.get('z', 0.0),
                            'w': rotation.get('w', 1.0)
                        },
                        'entity_min': entity_min,
                        'entity_max': entity_max,
                        'entity_size': entity_size,
                        'entity': entity
                    }
                    object_infos.append(complete_info)
                    if print_info:
                        print(f"[PROCESSING] 成功获取{object_name}实体: {obj_info['id']}")
            except Exception as e:
                print(f"[WARNING] 无法获取{object_name} {obj_info['id']} 的实体: {e}")
                continue
        
        return object_infos
        
    except Exception as e:
        print(f"[ERROR] 查询{object_name}时出现异常: {e}")
        return object_infos  # 异常情况下也返回空列表


# 查找桌子旁边一定范围内的所有物品
def find_objects_near_table(ue, table_object, search_distance=100.0, print_info=False):
    """
    查找桌子旁边一定范围内的所有物品，并区分桌上和桌旁物体
    
    Args:
        ue: TongSim实例
        table_object: 桌子对象
        search_distance: 搜索范围距离（厘米）
    
    Returns:
        tuple: (on_table_objects, nearby_objects) - 桌上物体列表和桌旁物体列表
    """
    
    # 启动 PG 实时流
    ue.pg_manager.start_pg_stream(pg_freq=10)
    print("[PROCESSING] Waiting for PG data...")
    time.sleep(0.5)  # 等待一段时间确保收到完整 PG 数据

    # 获取桌子的世界AABB边界
    table_aabb = table_object.get_world_aabb()
    table_min ,table_max = fix_aabb_bounds(table_aabb)

    on_table_objects = []  # 桌子上的物体
    nearby_objects = []    # 桌子附近但不在桌上的物体

    try:
        # 定义查询信息
        pg_metainfo = [
            {
                "component": "pose",
                "fields": ["location", "rotation"],
            },
            {
                "component": "object_state",
                "fields": ["object_type"],
            },
        ]
        
        # 执行查询
        result = ue.pg_manager.query(pg_metainfo)
        
        # 遍历所有物体
        for obj_id, obj_data in result.items():
            # 跳过元数据和其他非物体条目
            if obj_id == '__meta__' or 'object_type' not in obj_data:
                continue
            
            # 跳过桌子本身
            if obj_id == table_object.id:
                continue
            
            # 获取物体位置
            location = obj_data.get('location', {})
            x = location.get('x', 0.0)
            y = location.get('y', 0.0)
            z = location.get('z', 0.0)
            obj_position = ts.Vector3(x, y, z)
            
            # 检查物体是否在搜索范围内
            in_search_range = check_position_in_bbox(
                obj_position, table_min ,table_max, search_distance, True
            )
            if not in_search_range:
                continue

            # 检查物体是否在桌子上（水平在桌面范围内，垂直在桌面高度附近）
            on_table = (
                table_min.x <= x <= table_max.x and
                table_min.y <= y <= table_max.y and
                table_max.z - 5 <= z <= table_max.z + 60  # 允许一定的高度容差
            )
            
            try:
                # 获取物体实体
                entity = ue.entity_from_id(ts.BaseObjectEntity, entity_id=str(obj_id))
                
                if on_table:
                    on_table_objects.append(entity)
                    if  print_info == True:
                        print(f"[PROCESSING] 找到桌上物体: ID={obj_id}, 位置=({x:.2f}, {y:.2f}, {z:.2f})")

                else:
                    nearby_objects.append(entity)
                    if  print_info == True:
                        print(f"[PROCESSING] 找到附近物体: ID={obj_id}, 位置=({x:.2f}, {y:.2f}, {z:.2f})")

            except Exception as e:
                print(f"无法获取物体实体 {obj_id}: {e}")
                continue

        print(f"[INFO] 总共找到 {len(on_table_objects)} 个桌上物体和 {len(nearby_objects)} 个附近物体")
        
        return on_table_objects, nearby_objects
        
    except Exception as e:
        print(f"[ERROR] 查询附近物体时出现异常: {e}")
        return [], []


# 查找桌子旁边一定范围内的所有物品（返回完整信息）
def find_objects_near_table_with_info(ue, table_object, search_distance=100.0, print_info=False):
    """
    查找桌子旁边一定范围内的所有物品，并区分桌上和桌旁物体，返回完整信息
    
    Args:
        ue: TongSim实例
        table_object: 桌子对象
        search_distance: 搜索范围距离（厘米）
        print_info: 是否打印详细信息
    
    Returns:
        tuple: (on_table_objects_info, nearby_objects_info) 
               - 桌上物体完整信息列表和桌旁物体完整信息列表
               - 每个元素包含 id, type, location, rotation, entity, direction
    """
    
    # 启动 PG 实时流
    ue.pg_manager.start_pg_stream(pg_freq=10)
    print("[PROCESSING] Waiting for PG data...")
    time.sleep(0.5)  # 等待一段时间确保收到完整 PG 数据

    # 获取桌子的世界AABB边界
    table_aabb = table_object.get_world_aabb()
    table_min, table_max = fix_aabb_bounds(table_aabb)

    on_table_objects_info = []  # 桌子上的物体完整信息
    nearby_objects_info = []    # 桌子附近但不在桌上的物体完整信息

    try:
        # 定义查询信息
        pg_metainfo = [
            {
                "component": "pose",
                "fields": ["location", "rotation"],
            },
            {
                "component": "object_state",
                "fields": ["object_type"],
            },
        ]
        
        # 执行查询
        result = ue.pg_manager.query(pg_metainfo)
        
        # 遍历所有物体
        for obj_id, obj_data in result.items():
            # 跳过元数据和其他非物体条目
            if obj_id == '__meta__' or 'object_type' not in obj_data:
                continue
            
            # 跳过桌子本身
            if obj_id == table_object.id:
                continue
            
            # 获取物体位置
            location = obj_data.get('location', {})
            x = location.get('x', 0.0)
            y = location.get('y', 0.0)
            z = location.get('z', 0.0)
            obj_position = ts.Vector3(x, y, z)
            
            # 检查物体是否在搜索范围内
            in_search_range = check_position_in_bbox(
                obj_position, table_min, table_max, search_distance, True
            )
            if not in_search_range:
                continue

            # 检查物体是否在桌子上（水平在桌面范围内，垂直在桌面高度附近）
            on_table = (
                table_min.x <= x <= table_max.x and
                table_min.y <= y <= table_max.y and
                table_max.z - 5 <= z <= table_max.z + 60  # 允许一定的高度容差
            )
            
            # 获取物体类型
            obj_type = obj_data.get('object_type', 'Unknown')
            
            # 获取旋转信息
            rotation = obj_data.get('rotation', {})
            
            try:
                # 获取物体实体
                entity = ue.entity_from_id(ts.BaseObjectEntity, entity_id=str(obj_id))
                
                if entity:
                    # 获取物体的AABB边界
                    entity_min, entity_max = get_object_aabb(entity)
                    # 获取物体大小
                    entity_size = entity.get_scale()
                    # 提取基础蓝图ID
                    base_id = get_blueprint_from_entity_id(obj_id)
                    
                    # 创建包含实体对象的完整信息
                    complete_info = {
                        'id': obj_id,
                        'base_id': base_id,
                        'type': obj_type,
                        'location': {
                            'x': x,
                            'y': y,
                            'z': z
                        },
                        'rotation': {
                            'x': rotation.get('x', 0.0),
                            'y': rotation.get('y', 0.0),
                            'z': rotation.get('z', 0.0),
                            'w': rotation.get('w', 1.0)
                        },
                        'entity_min': entity_min,
                        'entity_max': entity_max,
                        'entity_size': entity_size,
                        'entity': entity,
                        'direction': 'none' if on_table else determine_object_side(entity, table_object)
                    }
                
                if on_table:
                    on_table_objects_info.append(complete_info)
                    if print_info:
                        print(f"[PROCESSING] 找到桌上物体: ID={obj_id}, 类型={obj_type}, "
                              f"位置=({x:.2f}, {y:.2f}, {z:.2f})")
                else:
                    nearby_objects_info.append(complete_info)
                    if print_info:
                        print(f"[PROCESSING] 找到附近物体: ID={obj_id}, 类型={obj_type}, "
                              f"位置=({x:.2f}, {y:.2f}, {z:.2f}), 方向={complete_info['direction']}")

            except Exception as e:
                print(f"[WARNING] 无法获取物体实体 {obj_id}: {e}")
                continue

        print(f"[INFO] 总共找到 {len(on_table_objects_info)} 个桌上物体和 {len(nearby_objects_info)} 个附近物体")
        
        return on_table_objects_info, nearby_objects_info
        
    except Exception as e:
        print(f"[ERROR] 查询附近物体时出现异常: {e}")
        return [], []

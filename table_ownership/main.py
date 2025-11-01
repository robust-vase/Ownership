import json
import os
import re
import math
import random
import time
from datetime import datetime
import numpy as np

import tongsim as ts
from tongsim.type import ViewModeType

# 几何计算包
import tongsim.math.geometry.geometry as geometry
dot = geometry.dot
cross = geometry.cross 
normalize = geometry.normalize 
# 角度计算 输入观察者位置pos 朝向目标target
def look_at_rotation(pos: ts.Vector3, target: ts.Vector3, world_up: ts.Vector3 = ts.Vector3(0, 0, 1)) -> ts.Quaternion:
    forward = normalize(target - pos)
    right = normalize(cross(world_up, forward))
    up = cross(forward, right)

    m00, m01, m02 = forward.x, right.x, up.x
    m10, m11, m12 = forward.y, right.y, up.y
    m20, m21, m22 = forward.z, right.z, up.z

    trace = m00 + m11 + m22
    if trace > 0:
        s = math.sqrt(trace + 1.0) * 2
        w = 0.25 * s
        x = (m21 - m12) / s
        y = (m02 - m20) / s
        z = (m10 - m01) / s
    elif (m00 > m11) and (m00 > m22):
        s = math.sqrt(1.0 + m00 - m11 - m22) * 2
        w = (m21 - m12) / s
        x = 0.25 * s
        y = (m01 + m10) / s
        z = (m02 + m20) / s
    elif m11 > m22:
        s = math.sqrt(1.0 + m11 - m00 - m22) * 2
        w = (m02 - m20) / s
        x = (m01 + m10) / s
        y = 0.25 * s
        z = (m12 + m21) / s
    else:
        s = math.sqrt(1.0 + m22 - m00 - m11) * 2
        w = (m10 - m01) / s
        x = (m02 + m20) / s
        y = (m12 + m21) / s
        z = 0.25 * s

    return ts.Quaternion(w, x, y, z) 

# 修复AABB边界框，确保min是最小值，max是最大值
def fix_aabb_bounds(aabb):
    """
    修复AABB边界框，确保min是最小值，max是最大值
    
    Args:
        aabb: 原始的AABB边界框对象，包含min和max属性
    
    Returns:
        tuple: (min_vector, max_vector) - 修复后的最小和最大边界向量
    """
    # 获取原始值
    original_min = aabb.min
    original_max = aabb.max
    
    # 创建修复后的min和max向量
    fixed_min = ts.Vector3(
        min(original_min.x, original_max.x),
        min(original_min.y, original_max.y),
        min(original_min.z, original_max.z)
    )
    
    fixed_max = ts.Vector3(
        max(original_min.x, original_max.x),
        max(original_min.y, original_max.y),
        max(original_min.z, original_max.z)
    )
    
    return fixed_min, fixed_max

# 检查一个点是否在边界框内（考虑安全边距）
def check_position_in_bbox(agent_position, bbox_min, bbox_max, safe_margin=0.0, check_z_axis=True):
    """
    检查一个点是否在边界框内（考虑安全边距）
    safe_margin > 0 边界扩大，使物品在边界框外围也可能检测到
    safe_margin < 0 边界缩小，使物品在边界框边缘也可能无法识别

    
    Args:
        agent_position: 点的位置 (Vector3)
        bbox_min: 边界框的最小点 (Vector3)
        bbox_max: 边界框的最大点 (Vector3)
        safe_margin: 安全边距，扩充边界框大小
        check_z_axis: 是否检查Z轴
    
    Returns:
        bool: True表示点在边界框内（包括安全边距），False表示不在
    """
    # 检查X轴
    in_x = (bbox_min.x - safe_margin <= agent_position.x <= bbox_max.x + safe_margin)
    
    # 检查Y轴
    in_y = (bbox_min.y - safe_margin <= agent_position.y <= bbox_max.y + safe_margin)
    
    # 检查Z轴（可选）
    if check_z_axis:
        in_z = (bbox_min.z - safe_margin <= agent_position.z <= bbox_max.z + safe_margin)
    else:
        in_z = True  # 如果不检查Z轴，默认认为在Z轴范围内
    
    return in_x and in_y and in_z

# 检查一个物品范围是否完全在边界框内（考虑安全边距）
def is_bbox_contained(inner_bbox_min, inner_bbox_max, outer_bbox_min, outer_bbox_max, safe_margin=0.0, check_z_axis=True):
    """
    检查一个边界框是否完全包含在另一个边界框内（考虑安全边距）
    
    Args:
        inner_bbox_min: 内部边界框的最小点 (Vector3)
        inner_bbox_max: 内部边界框的最大点 (Vector3)
        outer_bbox_min: 外部边界框的最小点 (Vector3)
        outer_bbox_max: 外部边界框的最大点 (Vector3)
        safe_margin: 安全边距，应用到外部边界框的内侧
        check_z_axis: 是否检查Z轴
    
    Returns:
        bool: True表示内部边界框完全在外部边界框内，False表示超出
    """
    # 检查X轴：内部最小点 >= 外部最小点 + 安全边距，内部最大点 <= 外部最大点 - 安全边距
    in_x = (inner_bbox_min.x >= outer_bbox_min.x + safe_margin and 
            inner_bbox_max.x <= outer_bbox_max.x - safe_margin)
    
    # 检查Y轴
    in_y = (inner_bbox_min.y >= outer_bbox_min.y + safe_margin and 
            inner_bbox_max.y <= outer_bbox_max.y - safe_margin)
    
    # 检查Z轴（可选）
    if check_z_axis:
        in_z = (inner_bbox_min.z >= outer_bbox_min.z + safe_margin and 
                inner_bbox_max.z <= outer_bbox_max.z - safe_margin)
    else:
        in_z = True  # 如果不检查Z轴，默认认为在Z轴范围内
    
    return in_x and in_y and in_z

# 判断在一定阈值范围下两个物品是否重叠
def check_item_overlap(itemA_min, itemA_max, itemB_min, itemB_max, safe_margin=0.0, check_z_axis=True):
    """
    检查两个物品是否在一定阈值范围内重叠
    Args:
        itemA_min: 物品A的最小边界点 (Vector3)
        itemA_max: 物品A的最大边界点 (Vector3)
        itemB_min: 物品B的最小边界点 (Vector3)
        itemB_max: 物品B的最大边界点 (Vector3)
        safe_margin: 安全边距，扩充边界框大小
        check_z_axis: 是否检查Z轴重叠
    
    Returns:
        bool: True表示有重叠，False表示无重叠
    """

    # 检查X轴重叠（考虑阈值）
    x_overlap = (itemA_max.x + safe_margin > itemB_min.x - safe_margin and 
                itemA_min.x - safe_margin < itemB_max.x + safe_margin)
    
    # 检查Y轴重叠（考虑阈值）
    y_overlap = (itemA_max.y + safe_margin > itemB_min.y - safe_margin and 
                itemA_min.y - safe_margin < itemB_max.y + safe_margin)
    
    # 检查Z轴重叠（考虑阈值和选项）
    if check_z_axis:
        z_overlap = (itemA_max.z + safe_margin > itemB_min.z - safe_margin and 
                    itemA_min.z - safe_margin < itemB_max.z + safe_margin)
    else:
        z_overlap = True  # 如果不检查Z轴，默认认为Z轴重叠
    
    # 如果三个轴都有重叠，则判定为物品重叠
    return x_overlap and y_overlap and z_overlap

# 根据类型文件筛选物品列表
def filter_objects_by_type(objects_list, type_file_path):
    """
    根据类型文件筛选物品列表
    
    Args:
        objects_list: 物品实体列表
        type_file_path: 包含类型ID的txt文件路径
    
    Returns:
        list: 属于指定类型的物品子列表
    """
    # 读取类型文件
    try:
        with open(type_file_path, 'r', encoding='utf-8') as f:
            type_ids = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"错误: 类型文件 {type_file_path} 不存在")
        return []
    
    # 创建匹配的实体列表
    matched_objects = []
    
    for obj in objects_list:
        obj_id = obj.id
        
        # 移除后缀
        base_id = obj_id
        # 匹配 _任意字符_数字 的模式
        pattern = r'(_[^_]+_\d+)$'
        match = re.search(pattern, obj_id)
        if match:
            base_id = obj_id[:match.start()]
        
        # 检查基础ID是否在类型列表中
        if base_id in type_ids:
            matched_objects.append(obj)
            print(f"匹配成功: {obj_id} -> 基础ID: {base_id}")
        else:
            print(f"不匹配: {obj_id} -> 基础ID: {base_id}")
    
    print(f"\n筛选结果: 共 {len(objects_list)} 个物品, 其中 {len(matched_objects)} 个匹配指定类型")
    return matched_objects

# 判断物体相对于参考物体的侧边位置
def determine_object_side(object, reference):
    """
    判断物体相对于参考物体的侧边位置
    
    Args:
        object_pos: 物体
        reference: 参考物体
    
    Returns:
        str: 侧边位置 ('front', 'back', 'left', 'right', 'unknown')
    """

    pos = object.get_location()
    obj_x, obj_y, obj_z = pos.x, pos.y, pos.z

    # 获取桌子的世界AABB边界
    reference_aabb = reference.get_world_aabb()
    reference_aabb_min ,reference_aabb_max = fix_aabb_bounds(reference_aabb)

    ref_min_x, ref_min_y, ref_min_z = reference_aabb_min
    ref_max_x, ref_max_y, ref_max_z = reference_aabb_max
    
    # 计算物体到参考物体各边的距离
    dist_to_front = obj_y - ref_max_y
    dist_to_back = obj_y - ref_min_y
    dist_to_left = obj_x - ref_max_x
    dist_to_right = obj_x - ref_min_x
    
    # 检查物体是否在桌子内部
    if (dist_to_front <= 0 and dist_to_back >= 0) and (dist_to_right <= 0 and dist_to_left >= 0):
        return 'unknown'
    
    # 检查符号是否相同来判断主导方向
    front_back_same_sign = (dist_to_front >= 0) == (dist_to_back >= 0)
    right_left_same_sign = (dist_to_right >= 0) == (dist_to_left >= 0)
    
    # 如果两个方向都符号相同，选择距离更远的方向
    if front_back_same_sign and right_left_same_sign:
        abs_y_dist = min(abs(dist_to_front), abs(dist_to_back))
        abs_x_dist = min(abs(dist_to_right), abs(dist_to_left))
        
        if abs_y_dist > abs_x_dist:
            return 'front' if dist_to_front > 0 else 'back'
        else:
            return 'left' if dist_to_left > 0 else 'right'
    
    # 如果只有前后方向符号相同
    elif front_back_same_sign:
        return 'front' if dist_to_front > 0 else 'back'
    
    # 如果只有左右方向符号相同
    elif right_left_same_sign:
        return 'left' if dist_to_left > 0 else 'right'
    
    # 如果符号都不相同，选择最小绝对距离的方向
    else:
        distances = {
            'front': abs(dist_to_front),
            'back': abs(dist_to_back),
            'right': abs(dist_to_right),
            'left': abs(dist_to_left)
        }
        return min(distances, key=distances.get)


# 获取全部房间bbox位置
def get_room_bbox(rooms):
    out = {}
    for room in rooms:
        out[room["room_name"]] = []
        for bbox in room["boxes"]:  # 房间形状可能不规则，因此会有多个包围盒
            min_item = bbox["min"]
            max_item = bbox["max"]
            x1, y1, z1 = min(min_item.x, max_item.x), min(min_item.y, max_item.y), min(min_item.z, max_item.z)
            x2, y2, z2 = max(min_item.x, max_item.x), max(min_item.y, max_item.y), max(min_item.z, max_item.z)
            room_bbox = [[x1, y1, z1], [x2, y2, z2]]
            out[room["room_name"]].append(room_bbox)
    return out

# 获取单个房间的边界具体信息
def get_room_boundary(room_name, room_bbox_dict, print_info=False):
    """
    获取单个房间的边界具体信息
    
    Args:
        room_name: 房间名称，如 "babyRoom"
        room_bbox_dict: 房间边界框字典
    
    Returns:
        房间的边界bbox信息
    """
    
    if room_name not in room_bbox_dict:
        print(f"错误：房间 '{room_name}' 不存在于room_bbox_dict中")
        return []

    # 获取房间边界框
    bbox_list = room_bbox_dict[room_name]
    if not bbox_list:
        print(f"错误：房间 '{room_name}' 的边界框数据为空")
        return []
    
    # 提取边界坐标
    min_vertex = bbox_list[0][0]  # 最小顶点 [x_min, y_min, z_min]
    max_vertex = bbox_list[0][1]  # 最大顶点 [x_max, y_max, z_max]
    
    x_min, y_min, z_min = min_vertex
    x_max, y_max, z_max = max_vertex
    
    # 计算房间尺寸
    room_width = abs(x_max - x_min)
    room_length = abs(y_max - y_min) 
    room_height = abs(z_max - z_min)
    
    # 计算房间中心点
    center_x = (x_min + x_max) / 2
    center_y = (y_min + y_max) / 2
    center_z = (z_min + z_max) / 2
    
    # 打印房间信息
    if  print_info == True:
        print(f"房间 '{room_name}' 信息:")
        print(f"  - 尺寸: {room_width:.2f} × {room_length:.2f} × {room_height:.2f}")
        print(f"  - 中心点: ({center_x:.2f}, {center_y:.2f}, {center_z:.2f})")
        print(f"  - 边界范围: X[{x_min:.2f} ~ {x_max:.2f}], Y[{y_min:.2f} ~ {y_max:.2f}], Z[{z_min:.2f} ~ {z_max:.2f}]")
        
    return [x_min, x_max, y_min, y_max, z_min, z_max]

# 计算面积
def get_room_area(room_bound):
    """
    获取房间的面积（平方米）
    
    Args:
        room_name: 房间名称
        room_bbox_dict: 房间边界框字典
    
    Returns:
        房间面积（平方米），如果出错返回-1
    """
    try:
        x_min, x_max, y_min, y_max, _, _ = room_bound
        
        # 计算尺寸并转换为米
        width_cm = abs(x_max - x_min)
        length_cm = abs(y_max - y_min)
        
        width_m = width_cm / 100.0
        length_m = length_cm / 100.0
        
        # 计算面积
        area = width_m * length_m
        return area
        
    except Exception as e:
        print(f"计算面积时出错: {e}")
        return -1


# 查询房间已有桌子
def query_existing_tables_in_room(ue, room_bound, target_types=None, print_info=False):
    """
    查询房间内已有的桌子对象
    
    Args:
        ue: TongSim实例
        room_bound: 房间边界
        target_types: 要查找的桌子类型列表，默认为 None
    
    Returns:
        entity: 房间内的一个桌子实体，如果没有找到返回None
    """
    if target_types is None:
        target_types = ['coffeetable', 'diningTable', 'table', 'Table']

    x_min, x_max, y_min, y_max, z_min, z_max = room_bound
    
    try:
        # 启动 PG 实时流
        ue.pg_manager.start_pg_stream(pg_freq=60)
        print("Waiting for PG data...")
        time.sleep(0.05)  # 等待一段时间确保收到完整 PG 数据
        
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
        
        table_objects = []

        # 提取所有桌子信息
        for obj_id, obj_data in result.items():
            # 跳过元数据和其他非物体条目
            if obj_id == '__meta__' or 'object_type' not in obj_data:
                continue
            
            obj_type = obj_data['object_type']
            
            # 检查是否是我们要找的桌子类型
            if obj_type in target_types:
                # 提取位置和旋转信息
                location = obj_data.get('location', {})
                
                # 检查桌子是否在房间边界内
                x = location.get('x', 0.0)
                y = location.get('y', 0.0)
                z = location.get('z', 0.0)
                
                if (x_min <= x <= x_max and 
                    y_min <= y <= y_max):
                    
                    rotation = obj_data.get('rotation', {})
                    
                    table_info = {
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
                    
                    table_objects.append(table_info)

        if  print_info == True:
            print(f"在房间找到 {len(table_objects)} 张桌子")

        # 如果没有找到桌子，返回None
        if not table_objects:
            print("房间内没有找到符合条件的桌子")
            return None
        
        # 打印桌子信息
        if  print_info == True:
            for i, table in enumerate(table_objects):
                loc = table['location']
                print(f"  桌子 {i+1}: ID={table['id']}, 类型={table['type']}, "
                    f"位置=({loc['x']:.2f}, {loc['y']:.2f}, {loc['z']:.2f})")
        
        # 返回第一个桌子的实体
        first_table_id = table_objects[0]['id']
        print(f"选择桌子: {first_table_id}")
        
        entity = ue.entity_from_id(ts.BaseObjectEntity, entity_id=str(first_table_id))
        return entity
        
    except Exception as e:
        print(f"[ERROR] 查询桌子时出现异常: {e}")
        return None

# 随机生成桌子 待修改 桌子种类以及桌子大小
def spawn_table(ue, room_name, room_bbox_dict, blueprint="BP_CoffeeTable_005", scale=ts.Vector3(1, 1, 1), safe_margin = 20.0, print_info=False):
    """
    安全生成桌子，避免穿模问题
    
    Args:
        ue: TongSim实例
        room_name: 房间名称
        room_bbox_dict: 房间边界字典
    
    Returns:
        table_obj: 桌子对象，如果生成失败返回None
    """
    
    # 获取房间边界
    room_bounds = get_room_boundary(room_name, room_bbox_dict)
    if not room_bounds:
        print(f"[ERROR] 无法获取房间 '{room_name}' 的边界信息")
        return None
    
    x_min, x_max, y_min, y_max, z_min, z_max = room_bounds

    attempts = 0
    table_obj = None
    max_attempts=100
    
    while attempts < max_attempts:
        attempts += 1
        
        try:
            # 生成桌子位置
            table_loc = ue.spatical_manager.get_random_spawn_location(room_name=room_name)
            table_loc[2] = z_min  # 放在地面上
            
            # 生成桌子
            table_obj = ue.spawn_entity(
                entity_type=ts.BaseObjectEntity,
                blueprint=blueprint,
                location=table_loc,
                is_simulating_physics=True,
                scale=scale,
                quat=None
            )
            
            # 等待物理引擎稳定
            time.sleep(0.01)

            # 检查桌子是否在房间边界内
            table_aabb = table_obj.get_world_aabb()
            table_min ,table_max = fix_aabb_bounds(table_aabb)
            
            table_in_room = is_bbox_contained(
                inner_bbox_min=table_min,
                inner_bbox_max=table_max,
                outer_bbox_min=ts.Vector3(x_min, y_min, z_min),
                outer_bbox_max=ts.Vector3(x_max, y_max, z_max),
                safe_margin=safe_margin,
                check_z_axis=False  # 通常不需要检查Z轴，因为桌子放在地面上
            )

            if not table_in_room:
                # print(f"[WARNING] 尝试 {attempts}: 桌子超出房间边界，删除并重新生成...")
                ue.destroy_entity(table_obj.id)
                table_obj = None
                continue
            
            if  print_info == True:
                print(f"[SUCCESS] 桌子生成成功！位置: {table_loc}, 桌子款式: {blueprint}")

            return table_obj
            
        except Exception as e:
            print(f"[ERROR] 生成桌子时出现异常: {e}")
            if table_obj:
                try:
                    ue.destroy_entity(table_obj.id)
                except:
                    pass
            table_obj = None
    
    print(f"[ERROR] 经过 {max_attempts} 次尝试后仍无法生成合适的桌子位置")
    return None

# 创建椅子
def generate_chairs(ue, table_object, room_bbox_dict, room_name, num_chairs, chair_sides, type_file_path, chair_blueprints, nearby_objects=[], 
                    min_distance=10, max_distance=90, safe_margin=15, print_info=False):
    """
    在桌子周围生成指定数量的椅子，避开附近的物体
    
    Args:
        ue: TongSim实例
        table_object: 桌子对象
        room_bbox_dict: 房间边界字典
        room_name: 房间名称
        num_chairs: 要生成的椅子数量
        chair_sides: 椅子方向列表
        type_file_path: 椅子类型文件路径
        chair_blueprints: 椅子蓝图列表
        nearby_objects: 附近的物体列表
        min_distance: 距离桌子的最小距离
        max_distance: 距离桌子的最大距离
        safe_margin: 边界的安全边距
    
    Returns:
        list: 生成的椅子对象列表
    """

    # 参数验证
    if chair_sides and num_chairs and len(chair_sides) != num_chairs:
        print(f"警告: chair_sides数量({len(chair_sides)})与num_chairs({num_chairs})不匹配，使用chair_sides数量")
        num_chairs = len(chair_sides)
    
    # 优先使用chair_blueprints参数
    if not chair_blueprints:
        # 如果没有提供chair_blueprints，则从文件读取
        try:
            with open(type_file_path, 'r', encoding='utf-8') as f:
                chair_blueprints = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print(f"错误: 椅子类型文件 {type_file_path} 不存在")
            return []
        except Exception as e:
            print(f"读取椅子类型文件失败: {e}")
            return []
    
    if not chair_blueprints:
        print("警告: 椅子类型列表为空")
        return []
    
    
    # 获取桌子的世界AABB边界
    table_aabb = table_object.get_world_aabb()
    table_min, table_max = fix_aabb_bounds(table_aabb)
    table_loc = table_object.get_location()
    # 获取房间边界
    room_bounds = get_room_boundary(room_name, room_bbox_dict)
    if not room_bounds:
        return []
    
    x_min, x_max, y_min, y_max, z_min, z_max = room_bounds
    chairs = []
    chair_positions = []
    
    # 预计算附近物体的AABB边界
    nearby_object_bounds = []
    for obj in nearby_objects:
        try:
            # 检查字典中是否有 'entity' 键
            if isinstance(obj, dict) and 'entity' in obj:
                entity = obj['entity']
                obj_aabb = entity.get_world_aabb()
                obj_aabb_min, obj_aabb_max = fix_aabb_bounds(obj_aabb)
                if obj_aabb.max.z - obj_aabb.min.z > 5:  # 防止地毯算入障碍物
                    nearby_object_bounds.append({
                        'min': obj_aabb_min,
                        'max': obj_aabb_max,
                        'entity': entity,
                        'type': obj.get('type', 'unknown')
                    })
            # 如果 obj 本身就是实体对象
            elif hasattr(obj, 'get_world_aabb'):
                obj_aabb = obj.get_world_aabb()
                obj_aabb_min, obj_aabb_max = fix_aabb_bounds(obj_aabb)
                if obj_aabb.max.z - obj_aabb.min.z > 5:  # 防止地毯算入障碍物
                    nearby_object_bounds.append({
                        'min': obj_aabb_min,
                        'max': obj_aabb_max,
                        'entity': obj,
                        'type': 'unknown'
                    })
        except Exception as e:
            print(f"无法获取物体边界: {e}")

    if print_info == True:
        print(f"预计算了 {len(nearby_object_bounds)} 个附近物体的边界")
        print(f"可用的椅子蓝图: {chair_blueprints}")
        print(f"椅子方向: {chair_sides}")

    # 为每个椅子生成位置
    for i in range(num_chairs):
        chair_placed = False
        attempts = 0
        max_attempts = 30  # 最大尝试次数
        
        # 获取当前椅子的方向和蓝图
        if chair_sides and i < len(chair_sides):
            side = chair_sides[i]
        else:
            # 如果没有指定方向，随机选择
            side = random.choice(['front', 'back', 'left', 'right'])
        
        # 随机选择椅子蓝图
        if i < len(chair_blueprints):
            chair_blueprint = chair_blueprints[i]
        else:
            chair_blueprint = random.choice(chair_blueprints)
        
        while not chair_placed and attempts < max_attempts:
            attempts += 1
            
            # 根据选择的侧边计算基础位置
            if side == 'front':  # 桌子正面（Y轴正方向）
                base_x = random.uniform(table_min.x, table_max.x)
                base_y = table_max.y
                direction = ts.Vector3(0, 1, 0)
            elif side == 'back':  # 桌子背面（Y轴负方向）
                base_x = random.uniform(table_min.x, table_max.x)
                base_y = table_min.y
                direction = ts.Vector3(0, -1, 0)
            elif side == 'left':  # 桌子左侧（X轴负方向）
                base_x = table_min.x
                base_y = random.uniform(table_min.y, table_max.y)
                direction = ts.Vector3(-1, 0, 0)
            else:  # 桌子右侧（X轴正方向）
                base_x = table_max.x
                base_y = random.uniform(table_min.y, table_max.y)
                direction = ts.Vector3(1, 0, 0)
            
            # 随机距离
            distance = random.uniform(min_distance, max_distance)
            
            # 计算最终位置
            chair_x = base_x + direction.x * distance
            chair_y = base_y + direction.y * distance
            chair_z = z_min  # 放在地面上
            chair_position = ts.Vector3(chair_x, chair_y, chair_z)

            # 检查是否与附近物体重叠
            too_close_to_object = False
            for obj_bounds in nearby_object_bounds:
                obj_min = obj_bounds['min']
                obj_max = obj_bounds['max']
                
                is_chair_in_object = check_position_in_bbox(chair_position, obj_min, obj_max, safe_margin=safe_margin, check_z_axis=False)

                # 检查椅子位置是否与物体有位置冲突
                if is_chair_in_object:
                    too_close_to_object = True
                    break

            if too_close_to_object:
                continue
            
            # 检查位置是否在房间边界内
            is_chair_in_room = check_position_in_bbox(chair_position, ts.Vector3(x_min, y_min, z_min), ts.Vector3(x_max, y_max, z_max), 
                                                      safe_margin=-safe_margin, check_z_axis=False)
            if not is_chair_in_room:
                continue

            # 检查与已有椅子的距离
            too_close_to_other_chair = False
            if chair_positions:  # 确保列表不为空
                agent_array = np.array([chair_position.x, chair_position.y, chair_position.z])
                existing_arrays = np.array([[pos.x, pos.y, pos.z] for pos in chair_positions])
                
                # 计算所有距离
                distances = np.linalg.norm(existing_arrays - agent_array, axis=1)
                
                # 检查是否有任何距离小于最小距离
                if np.any(distances < safe_margin * 2):
                    too_close_to_other_chair = True

            if too_close_to_other_chair:
                if print_info:
                    print(f"尝试 {attempts}: 椅子 {i+1} 位置 {chair_position} 与其他椅子物靠太近，重新尝试...")
                continue

            # 计算朝向：朝向桌子中心
            towards_position = ts.Vector3(table_loc.x, table_loc.y, table_loc.z)
            rotation_quat = look_at_rotation(chair_position, towards_position)
            # 创建一个绕Z轴旋转90度的四元数
            angle_rad = math.radians(-90)  # 90度转换为弧度
            z_rotation = ts.Quaternion(
                math.cos(angle_rad / 2),  # w
                0,                        # x
                0,                        # y
                math.sin(angle_rad / 2)   # z
            )
            # 组合两个旋转
            final_rotation = rotation_quat * z_rotation
            try:
                # 创建椅子
                chair = ue.spawn_entity(
                    entity_type=ts.BaseObjectEntity,
                    blueprint=chair_blueprint,
                    location=chair_position,
                    is_simulating_physics=False,  # 椅子不需要物理模拟
                    scale=ts.Vector3(1, 1, 1),
                    quat=final_rotation
                )
                
                # 等待一下确保椅子创建成功
                time.sleep(0.01)
                
                # 检查椅子是否成功创建
                if hasattr(chair, 'id'):
                    chairs.append(chair)
                    chair_positions.append(chair_position)
                    chair_placed = True
                    
                    print(f"椅子 {i+1} 生成在桌子{side}侧，位置: {chair_position}, 蓝图: {chair_blueprint}")
                    
                    # 从蓝图列表中移除已使用的蓝图（可选）
                    if len(chair_blueprints) > 1 and chair_blueprint in chair_blueprints:
                        chair_blueprints.remove(chair_blueprint)
                else:
                    print(f"椅子创建失败: {chair_blueprint}")
            except Exception as e:
                print(f"生成椅子时出错: {e}")
                continue
                
        if not chair_placed:
            print(f"警告: 无法为椅子 {i+1} 找到合适的位置")
    print(f"成功生成 {len(chairs)} 把椅子")
    return chairs

# 查找桌子旁边一定范围内的所有物品
def find_objects_near_table(ue, table_object, search_distance=70.0, print_info=False):
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
    ue.pg_manager.start_pg_stream(pg_freq=60)
    print("Waiting for PG data...")
    time.sleep(0.05)  # 等待一段时间确保收到完整 PG 数据

    # 获取桌子的世界AABB边界
    table_aabb = table_object.get_world_aabb()
    table_min ,table_max = fix_aabb_bounds(table_aabb)

    print(table_object.get_location())
    if  print_info == True:
        # 计算扩展的搜索范围（中间打孔的方形范围）
        search_min = ts.Vector3(
            table_min.x - search_distance,
            table_min.y - search_distance,
            table_min.z - search_distance
        )
        search_max = ts.Vector3(
            table_max.x + search_distance,
            table_max.y + search_distance,
            table_max.z + search_distance
        )
        print(f"桌子边界: min={table_min}, max={table_max}")
        print(f"搜索范围: min={search_min}, max={search_max}")
    
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
                obj_position, table_min ,table_max, search_distance, False
            )
            
            if not in_search_range:
                continue

            # 检查物体是否在桌子上（水平在桌面范围内，垂直在桌面高度附近）
            on_table = (
                table_min.x <= x <= table_max.x and
                table_min.y <= y <= table_max.y and
                table_max.z - 5 <= z <= table_max.z + 30  # 允许一定的高度容差
            )
            
            try:
                # 获取物体实体
                entity = ue.entity_from_id(ts.BaseObjectEntity, entity_id=str(obj_id))
                
                if on_table:
                    on_table_objects.append(entity)
                    if  print_info == True:
                        print(f"找到桌上物体: ID={obj_id}, 位置=({x:.2f}, {y:.2f}, {z:.2f})")
                else:
                    nearby_objects.append(entity)
                    if  print_info == True:
                        print(f"找到附近物体: ID={obj_id}, 位置=({x:.2f}, {y:.2f}, {z:.2f})")
                    
            except Exception as e:
                print(f"无法获取物体实体 {obj_id}: {e}")
                continue

        print(f"总共找到 {len(on_table_objects)} 个桌上物体和 {len(nearby_objects)} 个附近物体")
        
        return on_table_objects, nearby_objects
        
    except Exception as e:
        print(f"[ERROR] 查询附近物体时出现异常: {e}")
        return [], []


# 桌子旁随机生成人
def random_spawn_agents_around_table(ue, table_obj, room_bbox_dict, room_name, num_agents=2, nearby_objects = [], 
                              min_distance=10, max_distance=90, min_agent_distance=60, safe_margin = 15, print_info=False):
    """
    在桌子周围生成指定数量的人物，避开附近的物体
    
    Args:
        ue: TongSim实例
        table_obj: 桌子对象
        room_bbox_dict: 房间边界字典
        room_name: 房间名称
        num_agents: 要生成的人物数量
        nearby_objects: 附近的物体列表（包含entity信息）
        min_distance: 距离桌子的最小距离
        max_distance: 距离桌子的最大距离
        min_agent_distance: 人物之间的最小距离
        safe_margin: 边界的安全边距
    
    Returns:
        list: 生成的人物对象列表
    """
    
    # 人物蓝图列表
    agent_blueprints = [
        "SDBP_Aich_AIBabyV7_Shoes",
        "SDBP_Aich_AIBaby_Lele_Shoes",
        "SDBP_Aich_AIBaby_Tiantian_90",
        # "SDBP_Aich_Huangbo",
        "SDBP_Aich_Liyuxia",
        # "SDBP_Aich_Shenxin",
        # "SDBP_Aich_Sunhui",
        "SDBP_Aich_Yeye",
        "SDBP_Aich_Zhanghaoran",
        # "SDBP_Aich_Zhangzhiming"
    ]
    
    
    # 获取桌子的世界AABB边界
    table_aabb = table_obj.get_world_aabb()
    table_min ,table_max = fix_aabb_bounds(table_aabb)

    # 获取房间边界
    room_bounds = get_room_boundary(room_name, room_bbox_dict)
    if not room_bounds:
        return []
    
    x_min, x_max, y_min, y_max, z_min, z_max = room_bounds

    agents = []
    agent_positions = []
    
    # 预计算附近物体的AABB边界
    nearby_object_bounds = []
    for obj in nearby_objects:
        try:
            # 检查字典中是否有 'entity' 键
            if isinstance(obj, dict) and 'entity' in obj:
                entity = obj['entity']
                obj_aabb = entity.get_world_aabb()
                obj_aabb_min ,obj_aabb_max = fix_aabb_bounds(obj_aabb)
                if obj_aabb.max.z - obj_aabb.min.z > 5: # 防止地毯算入障碍物
                    nearby_object_bounds.append({
                        'min': obj_aabb_min,
                        'max': obj_aabb_max,
                        'entity': entity,
                        'type': obj.get('type', 'unknown')
                    })
            # 如果 obj 本身就是实体对象
            elif hasattr(obj, 'get_world_aabb'):
                obj_aabb = obj.get_world_aabb()
                obj_aabb_min ,obj_aabb_max = fix_aabb_bounds(obj_aabb)
                if obj_aabb.max.z - obj_aabb.min.z > 5: # 防止地毯算入障碍物
                    nearby_object_bounds.append({
                        'min': obj_aabb_min,
                        'max': obj_aabb_max,
                        'entity': obj,
                        'type': 'unknown'
                    })
        except Exception as e:
            print(f"无法获取物体边界: {e}")
    if  print_info == True:
        print(f"预计算了 {len(nearby_object_bounds)} 个附近物体的边界")
    

    for i in range(min(num_agents, len(agent_blueprints))):
        agent_placed = False
        attempts = 0
        max_attempts = 100  # 最大尝试次数
        
        while not agent_placed:
            attempts += 1
            
            # 随机选择桌子的一侧（前、后、左、右）
            side = random.choice(['front', 'back', 'left', 'right'])
            
            # 根据选择的侧边计算基础位置
            if side == 'front':  # 桌子正面（Y轴正方向）
                base_x = random.uniform(table_min.x, table_max.x)
                base_y = table_max.y
                direction = ts.Vector3(0, 1, 0)
            elif side == 'back':  # 桌子背面（Y轴负方向）
                base_x = random.uniform(table_min.x, table_max.x)
                base_y = table_min.y
                direction = ts.Vector3(0, -1, 0)
            elif side == 'left':  # 桌子左侧（X轴负方向）
                base_x = table_min.x
                base_y = random.uniform(table_min.y, table_max.y)
                direction = ts.Vector3(-1, 0, 0)
            else:  # 桌子右侧（X轴正方向）
                base_x = table_max.x
                base_y = random.uniform(table_min.y, table_max.y)
                direction = ts.Vector3(1, 0, 0)
            
            # 随机距离
            distance = random.uniform(min_distance, max_distance)
            
            # 计算最终位置
            agent_x = base_x + direction.x * distance
            agent_y = base_y + direction.y * distance
            agent_z = z_min  # 放在地面上

            agent_position = ts.Vector3(agent_x, agent_y, agent_z)

            # 检查是否与附近物体重叠
            too_close_to_object = False
            for obj_bounds in nearby_object_bounds:
                obj_min = obj_bounds['min']
                obj_max = obj_bounds['max']
                
                # 检查人物位置是否与物体有位置冲突，即是否靠太近
                is_agent_in_object = check_position_in_bbox(agent_position, obj_min, obj_max, 
                                                            safe_margin=safe_margin, check_z_axis=False)
                if is_agent_in_object:
                    too_close_to_object = True
                    break

            if too_close_to_object:
                continue

            # 检查位置是否在房间边界内
            is_agent_in_room = check_position_in_bbox(agent_position, ts.Vector3(x_min, y_min, z_min), ts.Vector3(x_max, y_max, z_max), 
                                                      safe_margin=-safe_margin, check_z_axis=False)

            if is_agent_in_room:

                # 检查与已有人物的距离
                too_close_to_other_agent = False
                if agent_positions:  # 确保列表不为空
                    agent_array = np.array([agent_position.x, agent_position.y, agent_position.z])
                    existing_arrays = np.array([[pos.x, pos.y, pos.z] for pos in agent_positions])
                    
                    # 计算所有距离
                    distances = np.linalg.norm(existing_arrays - agent_array, axis=1)
                    
                    # 检查是否有任何距离小于最小距离
                    if np.any(distances < min_agent_distance):
                        too_close_to_other_agent = True

                if too_close_to_other_agent:
                    continue

                # 随机选择人物蓝图
                agent_blueprint = random.choice(agent_blueprints)

                # 计算朝向：看向桌子上的随机点
                table_target_x = random.uniform(table_min.x, table_max.x)
                table_target_y = random.uniform(table_min.y, table_max.y)
                # table_target_z = random.uniform(table_min.z, table_max.z)
                towards_position = ts.Vector3(table_target_x, table_target_y, table_max.z)

                # 计算朝向四元数
                rotation_quat = look_at_rotation(agent_position, towards_position)
                # rotation_quat = look_at_rotation(agent_position, table_loc)

                try:
                    # 随机生成人物点
                    random_position = ue.spatical_manager.get_nearest_nav_position(target_location = agent_position)
                    # 创建人物
                    agent = ue.spawn_agent(
                        blueprint=agent_blueprint,
                        location=random_position,
                        desired_name=str(agent_blueprint),
                        quat=None,
                        scale=None
                    )

                    # 生成人物走向 agent_position 并且朝向 rotation_quat
                    agent.do_action(ts.action.MoveToLocation(loc=agent_position, speed= 999))
                    agent.do_action(ts.action.TurnToLocation(loc=towards_position))

                    
                    agents.append(agent)
                    agent_positions.append(agent_position)
                    agent_placed = True
                    
                    if  print_info == True:
                        print(f"人物 {i+1} 生成在桌子{side}侧，位置: {agent_position}, 蓝图: {agent_blueprint}, 方向: {rotation_quat}")

                    # 从蓝图列表中移除已使用的蓝图
                    if agent_blueprint in agent_blueprints:
                        agent_blueprints.remove(agent_blueprint)

                except Exception as e:
                    print(f"生成人物时出错: {e}")
                    continue
                
            else:
                print(f"尝试 {attempts}: 人物 {i+1} 位置 {agent_position} 超出房间边界，重新尝试...")

    return agents

# 规划桌子周围人物的位置和状态
def plan_agents_around_table(ue, table_object, room_bound, agent_blueprints, agent_sides, agent_is_sit, nearby_objects, 
                             min_distance=10, max_distance=90, min_agent_distance=60, safe_margin=15, print_info=False):
    """
    规划桌子周围人物的位置和状态（站立或坐下），返回规划结果而不实际生成人物
    
    Args:
        ue: TongSim实例
        table_object: 桌子对象
        room_bound: 房间边界
        agent_blueprints: 人物蓝图列表
        agent_sides: 人物方向列表
        agent_is_sit: 人物是否坐下的布尔列表
        nearby_objects: 附近的物体列表
        min_distance: 距离桌子的最小距离
        max_distance: 距离桌子的最大距离
        min_agent_distance: 人物之间的最小距离
        safe_margin: 边界的安全边距
        print_info: 是否打印详细信息
    
    Returns:
        list: 人物规划信息列表，每个元素是一个字典，包含:
            - blueprint: 人物蓝图
            - side: 方向
            - is_sit: 是否坐下
            - position: 位置（如果站立）
            - rotation: 朝向四元数
            - chair_id: 椅子ID（如果坐下）
            - status: 状态描述 ('standing' 或 'sitting')
    """
        
    # 检查输入参数一致性
    if len(agent_blueprints) != len(agent_sides) or len(agent_blueprints) != len(agent_is_sit):
        print("错误: 人物蓝图、方向和坐下状态数量不匹配")
        return []
    
    # 从附近物体中筛选出椅子
    existed_chairs = filter_objects_by_type(objects_list=nearby_objects, type_file_path='./ownership/object/chair.txt')
    if print_info:
        print(f"找到 {len(existed_chairs)} 把现有椅子")
    
    # 获取桌子的世界AABB边界
    table_aabb = table_object.get_world_aabb()
    table_min ,table_max = fix_aabb_bounds(table_aabb)
    
    x_min, x_max, y_min, y_max, z_min, z_max = room_bound
    
    # 预计算附近物体的AABB边界
    nearby_object_bounds = []
    for obj in nearby_objects:
        try:
            # 检查字典中是否有 'entity' 键
            if isinstance(obj, dict) and 'entity' in obj:
                entity = obj['entity']
                obj_aabb = entity.get_world_aabb()
                obj_aabb_min ,obj_aabb_max = fix_aabb_bounds(obj_aabb)
                if obj_aabb.max.z - obj_aabb.min.z > 15 and get_room_area([obj_aabb_min.x, obj_aabb_max.x, obj_aabb_min.y, obj_aabb_max.y, obj_aabb_min.z, obj_aabb_max.z]) < 1: # 防止地毯算入障碍物
                    nearby_object_bounds.append({
                        'min': obj_aabb_min,
                        'max': obj_aabb_max,
                        'entity': entity,
                        'type': obj.get('type', 'unknown')
                    })
            # 如果 obj 本身就是实体对象
            elif hasattr(obj, 'get_world_aabb'):
                obj_aabb = obj.get_world_aabb()
                obj_aabb_min ,obj_aabb_max = fix_aabb_bounds(obj_aabb)
                if obj_aabb.max.z - obj_aabb.min.z > 15 and get_room_area([obj_aabb_min.x, obj_aabb_max.x, obj_aabb_min.y, obj_aabb_max.y, obj_aabb_min.z, obj_aabb_max.z]) < 1: # 防止地毯算入障碍物
                    nearby_object_bounds.append({
                        'min': obj_aabb_min,
                        'max': obj_aabb_max,
                        'entity': obj,
                        'type': 'unknown'
                    })
        except Exception as e:
            print(f"无法获取物体边界: {e}")
    if  print_info == True:
        print(f"预计算了 {len(nearby_object_bounds)} 个附近物体的边界")
    
    # 计算每个椅子的方向
    chair_sides = []
    chair_positions = []
    for chair in existed_chairs:
        try:
            pos = chair.get_location()
            side = determine_object_side(chair, table_object)

            chair_sides.append(side)
            chair_positions.append((pos.x, pos.y, pos.z))
        except Exception as e:
            print(f"获取椅子 {chair.id} 信息失败: {e}")
            chair_sides.append('unknown')
            chair_positions.append((0, 0, 0))

    # 创建人物规划列表
    agent_plans = []
    agent_positions = []

    # 首先处理需要坐下的人物，尝试匹配椅子
    sitting_agents = []
    standing_agents = []

    for i, (blueprint, side, should_sit) in enumerate(zip(agent_blueprints, agent_sides, agent_is_sit)):
        if should_sit:
            sitting_agents.append((i, blueprint, side))
        else:
            standing_agents.append((i, blueprint, side))
    
    # 为需要坐下的人物匹配椅子
    matched_chairs = set()  # 记录已匹配的椅子
    
    for agent_idx, blueprint, side in sitting_agents:
        best_chair = None
        best_distance = float('inf')
        
        # 寻找同方向且最近的可用椅子
        for j, chair in enumerate(existed_chairs):
            # 如果方向不同直接跳过
            if j in matched_chairs or chair_sides[j] != side:
                continue
            # 这里可以添加更复杂的距离计算逻辑
            # 暂时使用随机数作为距离（简化实现）
            distance = random.random()
            
            if distance < best_distance:
                best_distance = distance
                best_chair = (j, chair)
        
        if best_chair:
            chair_idx, chair = best_chair
            matched_chairs.add(chair_idx)
            
            # 获取椅子位置和旋转
            try:
                # 计算朝向：看向桌子上的随机点
                table_target_x = random.uniform(table_min.x, table_max.x)
                table_target_y = random.uniform(table_min.y, table_max.y)
                # table_target_z = random.uniform(table_min.z, table_max.z)
                towards_position = ts.Vector3(table_target_x, table_target_y, table_max.z)
                
                agent_plans.append({
                    'blueprint': blueprint,
                    'side': side,
                    'is_sit': True,
                    'position': None,  # 坐下的人物不需要独立位置
                    'rotation': towards_position, 
                    'chair_id': chair.id,
                    'status': 'sitting'
                })
                
                if print_info:
                    print(f"人物 {agent_idx} 将坐在椅子 {chair.id} 上 (方向: {side})")
                    
            except Exception as e:
                print(f"获取椅子 {chair.id} 信息失败: {e}")
                # 如果获取椅子信息失败，将此人物转为站立
                standing_agents.append((agent_idx, blueprint, side))
        else:
            # 没有找到合适的椅子，将此人物转为站立
            if print_info:
                print(f"人物 {agent_idx} 需要坐下但未找到合适椅子，转为站立")
            standing_agents.append((agent_idx, blueprint, side))


    # 处理需要站立的人物（包括未能匹配到椅子的人物）
    for agent_idx, blueprint, side in standing_agents:
        agent_placed = False
        attempts = 0
        max_attempts = 100000  # 最大尝试次数
        
        while not agent_placed and attempts < max_attempts:
            attempts += 1
            
            # 根据选择的侧边计算基础位置
            if side == 'front':  # 桌子正面（Y轴正方向）
                base_x = random.uniform(table_min.x, table_max.x)
                base_y = table_max.y  # Y值更大表示更前方
                direction = ts.Vector3(0, 1, 0)  # 朝向Y轴正方向（前方）
            elif side == 'back':  # 桌子背面（Y轴负方向）
                base_x = random.uniform(table_min.x, table_max.x)
                base_y = table_min.y  # Y值更小表示更后方
                direction = ts.Vector3(0, -1, 0)  # 朝向Y轴负方向（后方）
            elif side == 'left':  # 桌子左侧（X轴正方向）
                base_x = table_max.x  # X值更大表示更左侧
                base_y = random.uniform(table_min.y, table_max.y)
                direction = ts.Vector3(1, 0, 0)  # 朝向X轴正方向（左侧）
            else:  # 桌子右侧（X轴负方向）
                base_x = table_min.x  # X值更小表示更右侧
                base_y = random.uniform(table_min.y, table_max.y)
                direction = ts.Vector3(-1, 0, 0)  # 朝向X轴负方向（右侧）
            
            # 随机距离
            distance = random.uniform(min_distance, max_distance)
            
            # 计算最终位置
            agent_x = base_x + direction.x * distance
            agent_y = base_y + direction.y * distance
            agent_z = z_min  # 放在地面上
            agent_position = ts.Vector3(agent_x, agent_y, agent_z)
            # 检查是否与附近物体重叠
            too_close_to_object = False
            for obj_bounds in nearby_object_bounds:
                obj_min = obj_bounds['min']
                obj_max = obj_bounds['max']
                
                # 检查人物位置是否与物体有位置冲突
                is_agent_in_object = check_position_in_bbox(agent_position, obj_min, obj_max, safe_margin=safe_margin, check_z_axis=False)
                if is_agent_in_object:
                    too_close_to_object = True
                    break
            if too_close_to_object:
                continue
            # 检查位置是否在房间边界内
            is_agent_in_room = check_position_in_bbox(agent_position, 
                                                     ts.Vector3(x_min, y_min, z_min), 
                                                     ts.Vector3(x_max, y_max, z_max), 
                                                     safe_margin=-safe_margin, check_z_axis=False)
            if not is_agent_in_room:
                continue

            # 检查与已有人物的距离
            too_close_to_other_agent = False
            for existing_pos in agent_positions:
                distance_to_other = np.sqrt(
                    (agent_position.x - existing_pos.x)**2 +
                    (agent_position.y - existing_pos.y)**2 +
                    (agent_position.z - existing_pos.z)**2
                )
                if distance_to_other < min_agent_distance:
                    too_close_to_other_agent = True
                    break
            if too_close_to_other_agent:
                continue

            # 计算朝向：看向桌子上的随机点
            table_target_x = random.uniform(table_min.x, table_max.x)
            table_target_y = random.uniform(table_min.y, table_max.y)
            towards_position = ts.Vector3(table_target_x, table_target_y, table_max.z)
            
            # 添加到规划结果
            agent_plans.append({
                'blueprint': blueprint,
                'side': side,
                'is_sit': False,
                'position': agent_position,
                'rotation': towards_position,
                'chair_id': None,
                'status': 'standing'
            })
            
            agent_positions.append(agent_position)
            agent_placed = True
            
            if print_info:
                print(f"人物 {agent_idx} 将站立在位置: {agent_position}, 方向: {side}")
        if not agent_placed:
            print(f"警告: {max_attempts} 次尝试后 无法为人物 {agent_idx} 找到合适的位置")
            # 添加一个空的规划项，表示规划失败
            agent_plans.append({
                'blueprint': blueprint,
                'side': side,
                'is_sit': False,
                'position': None,  # 设置为空
                'rotation': None,  # 设置为空
                'chair_id': None,
                'status': 'failed'  # 明确标记为失败状态
            })

    # 按原始索引顺序排序
    agent_plans.sort(key=lambda x: agent_blueprints.index(x['blueprint']))
    
    return agent_plans


from scipy.optimize import linear_sum_assignment    # 匹配算法
# 将人物与椅子进行距离匹配，并执行坐下动作
def agents_random_sit(ue, agents, chairs, sit_probability=1.0):
    """
    将人物与椅子进行距离匹配，并执行坐下动作
    
    Args:
        ue: Unreal Engine 对象
        agents: 人物实体列表
        chairs: 椅子实体列表
    
    Returns:
        list: 匹配成功的人物-椅子对列表
    """
    if not agents or not chairs:
        print("警告: 人物或椅子列表为空")
        return []
    
    # 获取所有人物和椅子的位置
    agent_positions = []
    for agent in agents:
        try:
            pos = agent.get_location()
            agent_positions.append((pos.x, pos.y, pos.z))
        except Exception as e:
            print(f"获取人物 {agent.id} 位置失败: {e}")
            agent_positions.append((0, 0, 0))
    
    chair_positions = []
    for chair in chairs:
        try:
            pos = chair.get_location()
            chair_positions.append((pos.x, pos.y, pos.z))
        except Exception as e:
            print(f"获取椅子 {chair.id} 位置失败: {e}")
            chair_positions.append((0, 0, 0))
    
    # 转换为numpy数组
    agent_positions = np.array(agent_positions)
    chair_positions = np.array(chair_positions)
    
    # 计算距离矩阵
    distance_matrix = np.zeros((len(agents), len(chairs)))
    for i, agent_pos in enumerate(agent_positions):
        for j, chair_pos in enumerate(chair_positions):
            # 计算欧几里得距离
            distance = np.sqrt(np.sum((agent_pos - chair_pos) ** 2))
            distance_matrix[i, j] = distance
    
    print("距离矩阵:")
    print(distance_matrix)
    
    # 使用匈牙利算法进行最优匹配
    row_ind, col_ind = linear_sum_assignment(distance_matrix)
    
    matched_pairs = []
    
    # 执行匹配和坐下动作
    for i, j in zip(row_ind, col_ind):
        if i < len(agents) and j < len(chairs):
            agent = agents[i]
            chair = chairs[j]
            distance = distance_matrix[i, j]
            
            print(f"匹配: {agent.id} -> {chair.id}, 距离: {distance:.2f}")

            # 检查是否执行坐下动作
            should_sit = random.random() <= sit_probability

            if should_sit:
                try:
                    # 移动到椅子并坐下
                    agent.do_action(ts.action.MoveToObject(object_id=chair.id, speed = 1000))
                    agent.do_action(ts.action.SitDownToObject(object_id=chair.id))
                    
                    matched_pairs.append((agent, chair, distance))
                    print(f"✓ 成功执行坐下动作: {agent.id} -> {chair.id}")
                    
                except Exception as e:
                    print(f"✗ 执行坐下动作失败: {agent.id} -> {chair.id}, 错误: {e}")
    
    # 处理未匹配的情况
    unmatched_agents = len(agents) - len(matched_pairs)
    unmatched_chairs = len(chairs) - len(matched_pairs)
    
    if unmatched_agents > 0:
        print(f"警告: {unmatched_agents} 个人物没有匹配到椅子")
    if unmatched_chairs > 0:
        print(f"提示: {unmatched_chairs} 把椅子没有被使用")
    
    return matched_pairs

# 人物的坐下的方向
def agents_sit(ue, room_bbox_dict, room_name, agents, agent_is_sit, table_object, agent_sides, chairs, min_distance=10, max_distance=90):

    """
    根据指定方向匹配人物和椅子，并执行坐下动作
    
    Args:
        ue: Unreal Engine 对象
        agents: 人物实体列表
        agent_is_sit: 人物是否坐下的布尔列表
        table_object: 桌子对象
        agent_sides: 人物方向列表
        chairs: 椅子实体列表
        min_distance: 最小距离
        max_distance: 最大距离
    
    Returns:
        list: 匹配成功的人物-椅子对列表
    """
    if not agents or not chairs:
        print("警告: 人物或椅子列表为空")
        return []
    
    if len(agents) != len(agent_sides) or len(agents) != len(agent_is_sit):
        print("错误: 人物数量与方向/坐下状态数量不匹配")
        return []
    
    # 获取桌子的世界AABB边界
    table_aabb = table_object.get_world_aabb()
    table_min, table_max = fix_aabb_bounds(table_aabb)
    
    # 获取所有人物和椅子的位置
    agent_positions = []
    for agent in agents:
        try:
            pos = agent.get_location()
            agent_positions.append((pos.x, pos.y, pos.z))
        except Exception as e:
            print(f"获取人物 {agent.id} 位置失败: {e}")
            agent_positions.append((0, 0, 0))
    
    chair_positions = []
    for chair in chairs:
        try:
            pos = chair.get_location()
            chair_positions.append((pos.x, pos.y, pos.z))
        except Exception as e:
            print(f"获取椅子 {chair.id} 位置失败: {e}")
            chair_positions.append((0, 0, 0))

    # 确定每个椅子的方向
    chair_sides = []
    for chair_pos in chair_positions:
        chair_x, chair_y, chair_z = chair_pos
        
        # 判断椅子相对于桌子的方向
        if abs(chair_y - table_max.y) < abs(chair_y - table_min.y):
            side = 'front'  # 靠近桌子正面
        else:
            side = 'back'   # 靠近桌子背面
            
        if abs(chair_x - table_max.x) < abs(chair_x - table_min.x):
            side = 'right'  # 靠近桌子右侧
        else:
            side = 'left'   # 靠近桌子左侧
        
        chair_sides.append(side)
    
    print(f"椅子方向: {chair_sides}")
    print(f"人物方向: {agent_sides}")

    # 转换为numpy数组
    agent_positions = np.array(agent_positions)
    chair_positions = np.array(chair_positions)
    
    # 计算距离矩阵
    distance_matrix = np.zeros((len(agents), len(chairs)))
    for i, agent_pos in enumerate(agent_positions):
        for j, chair_pos in enumerate(chair_positions):
            # 计算欧几里得距离
            distance = np.sqrt(np.sum((agent_pos - chair_pos) ** 2))
            distance_matrix[i, j] = distance
    
    print("距离矩阵:")
    print(distance_matrix)
    
    # 使用匈牙利算法进行最优匹配
    row_ind, col_ind = linear_sum_assignment(distance_matrix)
    matched_pairs = []

    # 使用原来的匈牙利算法进行匹配，我们根据匹配的结果进行椅子的移动操作
    # 这里我们需要根据每一个agnet以及agent_is_sit来进行操作
    # 如果agent_is_sit对应的不为坐下，那么可以跳过
    # 如果为坐下，那么我们需要比对匹配椅子的方向chair_sides与人物的方向
    # 如果方向一致，那么坐下；如果方向不一致，那么需要进行后续的删除椅子并且重新添加椅子的操作
    # 最后如果存在椅子不足的情况，就是我们的匈牙利算法没有给人匹配到椅子，我们直接创建椅子到固定的方向上
    # 执行匹配和坐下动作
    # 处理匹配结果
    for i, j in zip(row_ind, col_ind):
        if i < len(agents) and j < len(chairs):
            agent = agents[i]
            chair = chairs[j]
            agent_side = agent_sides[i]
            chair_side = chair_sides[j]
            should_sit = agent_is_sit[i]
            distance = distance_matrix[i, j]
            
            print(f"匹配: {agent.id} (方向:{agent_side}) -> {chair.id} (方向:{chair_side}), 距离: {distance:.2f}")
            if not should_sit:
                print(f"人物 {agent.id} 不需要坐下，跳过")
                continue
            if agent_side == chair_side:
                # 方向一致，执行坐下动作
                try:
                    agent.do_action(ts.action.MoveToObject(object_id=chair.id, speed=1000))
                    agent.do_action(ts.action.SitDownToObject(object_id=chair.id))
                    
                    matched_pairs.append((agent, chair, distance, agent_side))
                    print(f"✓ 成功执行坐下动作: {agent.id} -> {chair.id}")
                    
                except Exception as e:
                    print(f"✗ 执行坐下动作失败: {agent.id} -> {chair.id}, 错误: {e}")
            else:
                # 方向不一致，标记需要重新创建椅子
                print(f"方向不匹配: {agent_side} != {chair_side}, 椅子 {chair.id} 需要重新创建")

                try:
                    # 记住椅子ID和位置信息
                    chair_id = chair.id

                    # 移除后缀
                    base_id = chair_id
                    # 匹配 _任意字符_数字 的模式
                    pattern = r'(_[^_]+_\d+)$'
                    match = re.search(pattern, chair_id)
                    if match:
                        base_id = chair_id[:match.start()]

                    # 删除旧椅子
                    print(f"删除方向不匹配的椅子: {chair_id}")
                    ue.destroy_entity(chair_id)

                    # 使用generate_chairs函数重新创建椅子
                    new_chairs = generate_chairs(
                        ue=ue,
                        table_object=table_object,
                        room_bbox_dict=room_bbox_dict,  # 需要传入实际的room_bbox_dict
                        room_name=room_name,  # 需要传入实际的room_name
                        num_chairs=1,
                        chair_sides=[agent_side],
                        type_file_path='',  # 如果需要的话传入实际路径
                        chair_blueprints=[base_id],
                        nearby_objects=[obj for obj in chairs if obj.id != chair_id],  # 排除被删除的椅子
                        min_distance=min_distance,
                        max_distance=max_distance,
                        safe_margin=15,
                        print_info=False
                    )

                    if new_chairs and len(new_chairs) > 0:
                        new_chair = new_chairs[0]
                        print(f"✓ 成功重新创建椅子: {new_chair.id} 在 {agent_side} 方向")
                        
                        # 让人物坐到新椅子上
                        try:
                            agent.do_action(ts.action.MoveToObject(object_id=new_chair.id, speed=100))
                            agent.do_action(ts.action.SitDownToObject(object_id=new_chair.id))
                            matched_pairs.append((agent, new_chair, distance, agent_side))
                            print(f"✓ 成功执行坐下动作: {agent.id} -> {new_chair.id}")
                            
                            # 更新椅子列表
                            chairs.remove(chair)
                            chairs.append(new_chair)
                            
                        except Exception as e:
                            print(f"✗ 执行坐下动作失败: {agent.id} -> {new_chair.id}, 错误: {e}")
                    else:
                        print(f"✗ 重新创建椅子失败")
                        
                except Exception as e:
                    print(f"✗ 处理方向不匹配椅子失败: {e}")
    
    # 处理未匹配的情况
    unmatched_agents = len(agents) - len(matched_pairs)
    unmatched_chairs = len(chairs) - len(matched_pairs)
    
    if unmatched_agents > 0:
        print(f"警告: {unmatched_agents} 个人物没有匹配到椅子")
    if unmatched_chairs > 0:
        print(f"提示: {unmatched_chairs} 把椅子没有被使用")
    
    return matched_pairs

# 执行人物动作
def execute_agent_plans(ue, agent_plans, print_info=False):
    """
    根据人物规划信息实际生成人物并执行相应动作
    
    Args:
        ue: TongSim实例
        agent_plans: 人物规划信息列表
        print_info: 是否打印详细信息
    
    Returns:
        list: 生成的人物对象列表
    """

    agents = []

    for i, plan in enumerate(agent_plans):
        # 跳过规划失败的项目
        if plan['status'] == 'failed':
            print(f"跳过人物 {i}: 规划失败")
            continue
        
        blueprint = plan['blueprint']
        is_sit = plan['is_sit']
        towards_position = plan['rotation']
        
        try:
            if is_sit:
                # 处理坐下的人物
                chair_id = plan['chair_id']
                if not chair_id:
                    print(f"人物 {i} 需要坐下但未指定椅子ID")
                    continue
                
                # 通过ID获取椅子实体
                chair = ue.entity_from_id(ts.BaseObjectEntity, entity_id=str(chair_id))
                if not chair:
                    print(f"无法找到椅子实体: {chair_id}")
                    continue
                
                # 获取椅子位置
                chair_location = chair.get_location()
                
                # 获取最近的导航点
                random_position = ue.spatical_manager.get_nearest_nav_position(target_location=chair_location)
                
                # 生成人物
                agent = ue.spawn_agent(
                    blueprint=blueprint,
                    location=random_position,
                    desired_name=f"{blueprint}_{i}",
                    quat=None,
                    scale=None
                )

                # 执行坐下动作序列
                agent.do_action(ts.action.MoveToObject(object_id=chair.id, speed=1000))
                sit_result = agent.do_action(ts.action.SitDownToObject(object_id=chair.id))

                # 检查坐下是否成功
                sit_success = False
                if sit_result and len(sit_result) > 0:
                    # 检查所有动作结果的状态
                    for result in sit_result:
                        if hasattr(result, 'status') and result.status == 'end' and result.error_code == 0:
                            sit_success = True
                            break
                        elif hasattr(result, 'status') and result.status == 'error':
                            print(f"人物 {i} 坐下失败: error_code={getattr(result, 'error_code', 'unknown')}")
                
                agent.do_action(ts.action.TurnToLocation(loc=towards_position))
                
                if sit_success:
                    # 坐下成功，执行转向
                    agent.do_action(ts.action.TurnToLocation(loc=towards_position))
                    agents.append(agent)
                    
                    if print_info:
                        print(f"人物 {i} 已生成并成功坐在椅子 {chair_id} 上")

                else:
                    # 坐下失败，改为站立
                    if print_info:
                        print(f"人物 {i} 坐下失败，改为站立")
                    
                    # 获取当前位置
                    current_position = agent.get_location()
                    
                    # 执行站立动作序列
                    agent.do_action(ts.action.MoveToLocation(loc=current_position, speed=9999))
                    agent.do_action(ts.action.TurnToLocation(loc=towards_position))
                    
                    agents.append(agent)
                    
                    if print_info:
                        print(f"人物 {i} 已生成并改为站在位置 {current_position}")

            else:
                # 处理站立的人物
                position = plan['position']
                towards_position = plan['rotation']
                
                if not position:
                    print(f"人物 {i} 需要站立但未指定位置")
                    continue
                
                # 获取最近的导航点
                random_position = ue.spatical_manager.get_nearest_nav_position(target_location=position)
                
                # 生成人物
                agent = ue.spawn_agent(
                    blueprint=blueprint,
                    location=random_position,
                    desired_name=f"{blueprint}_{i}",
                    quat=None,
                    scale=None
                )
                
                # 执行站立动作序列
                agent.do_action(ts.action.MoveToLocation(loc=position, speed=9999))
                agent.do_action(ts.action.TurnToLocation(loc=towards_position))
                
                agents.append(agent)
                
                if print_info:
                    print(f"人物 {i} 已生成并安排站在位置 {position}")
                    
        except Exception as e:
            print(f"生成人物 {i} 时出错: {e}")
            continue
    
    return agents

# 生成人物配置
def generate_agent_configuration(num_agents=None, agent_blueprints=None, agent_sides=None, agent_is_sit=None, agent_traits=None,
                                 side_probabilities=[0.25, 0.25, 0.25, 0.25], sit_probability=0.5):
    """
    生成人物配置
    
    Args:
        num_agents: 人物数量（如果提供了agent_blueprints，则忽略此参数）
        agent_blueprints: 指定的人物蓝图列表
        agent_sides: 指定的人物方位列表
        agent_is_sit: 指定的人物是否坐下列表
        agent_traits: 人物特性列表 ['girl', 'boy', 'woman', 'grandpa', 'man']
        side_probabilities: 方位概率 [front, back, left, right]
        sit_probability: 坐下概率
    
    Returns:
        agent_blueprints, agent_sides, agent_is_sit 三个列表
    """

    # 人物蓝图映射表
    blueprint_mapping = {
        'girl': ["SDBP_Aich_AIBabyV7_Shoes", "SDBP_Aich_AIBaby_Lele_Shoes"],
        'boy': ["SDBP_Aich_AIBaby_Tiantian_90"],
        'woman': ["SDBP_Aich_Liyuxia"],
        'grandpa': ["SDBP_Aich_Yeye"],
        'man': ["SDBP_Aich_Zhanghaoran"]
    }

    # 人物类型限制
    trait_limits = {
        'man': 1,      # 男人最多1个
        'woman': 1,    # 女人最多1个
        'grandpa': 1,  # 爷爷最多1个
        'girl': 2,     # 女孩最多2个
        'boy': 2       # 男孩最多2个
    }

    # 方位映射
    side_mapping = ['front', 'back', 'left', 'right']
    

    # 如果提供了完整的agent_blueprints，则直接使用
    if agent_blueprints is not None:
        # 检查是否有重复的蓝图
        if len(agent_blueprints) != len(set(agent_blueprints)):
            print("警告: agent_blueprints中存在重复的人物蓝图，将使用全随机生成")
            agent_blueprints = None
            agent_traits = None
        else:
            num_agents = len(agent_blueprints)
        
        # 如果提供了agent_sides，检查长度是否匹配
        if agent_sides is not None and len(agent_sides) != num_agents:
            raise ValueError("agent_sides长度必须与agent_blueprints一致")
        
        # 如果提供了agent_is_sit，检查长度是否匹配
        if agent_is_sit is not None and len(agent_is_sit) != num_agents:
            raise ValueError("agent_is_sit长度必须与agent_blueprints一致")

    # 如果提供了agent_traits，检查类型限制
    if agent_traits is not None:
        # 检查人物类型限制
        trait_counts = {}
        for trait in agent_traits:
            trait_counts[trait] = trait_counts.get(trait, 0) + 1
        
        valid = True
        for trait, count in trait_counts.items():
            if trait in trait_limits and count > trait_limits[trait]:
                print(f"警告: {trait}类型的人物数量({count})超过限制({trait_limits[trait]})，将使用全随机生成")
                valid = False
                break
        
        if not valid:
            agent_traits = None
            agent_blueprints = None

    # 如果提供了agent_traits且有效，根据特性生成蓝图
    if agent_traits is not None and agent_blueprints is None:
        if num_agents is None:
            num_agents = len(agent_traits)
        elif len(agent_traits) != num_agents:
            raise ValueError("agent_traits长度必须与num_agents一致")
        
        agent_blueprints = []
        available_blueprints = {trait: blueprint_mapping[trait].copy() for trait in set(agent_traits)}
        
        for trait in agent_traits:
            if not available_blueprints[trait]:
                print(f"警告: {trait}类型没有可用的蓝图，将使用全随机生成")
                agent_blueprints = None
                agent_traits = None
                break
            
            blueprint = random.choice(available_blueprints[trait])
            agent_blueprints.append(blueprint)
            available_blueprints[trait].remove(blueprint)  # 移除已使用的蓝图避免重复
    
    # 全随机生成（包括之前检查失败的情况）
    if agent_blueprints is None:
        if num_agents is None:
            num_agents = random.randint(2, 4)  # 默认生成2-4个人物
        
        # 创建可用的蓝图池（避免重复）
        available_blueprints = []
        for trait, blueprints in blueprint_mapping.items():
            available_blueprints.extend([(trait, bp) for bp in blueprints])
        
        if len(available_blueprints) < num_agents:
            raise ValueError(f"可用的蓝图数量({len(available_blueprints)})不足以生成{num_agents}个人物")
        
        # 随机选择但不重复
        selected = random.sample(available_blueprints, num_agents)
        agent_traits = [item[0] for item in selected]
        agent_blueprints = [item[1] for item in selected]

    # 生成方位配置
    if agent_sides is None:
        agent_sides = random.choices(side_mapping, weights=side_probabilities, k=num_agents)
    
    # 生成坐下配置
    if agent_is_sit is None:
        agent_is_sit = [random.random() < sit_probability for _ in range(num_agents)]
    
    return agent_blueprints, agent_sides, agent_is_sit




# 桌子上随机生成物品
def spawn_items_on_table(ue, table_obj, num_items=3, max_attempts_per_item=10, safe_margin = 15):
    """
    在桌子上生成指定数量的物品，避免重叠
    
    Args:
        ue: TongSim实例
        table_obj: 桌子对象
        num_items: 要生成的物品数量
        max_attempts_per_item: 每个物品的最大尝试次数
    
    Returns:
        list: 生成的物品对象列表
    """
    
    if not table_obj:
        print("[ERROR] 桌子对象为空，无法生成物品")
        return []
    
    # 获取桌子的世界AABB边界和位置
    table_aabb = table_obj.get_world_aabb()
    table_min ,table_max = fix_aabb_bounds(table_aabb)
    table_location = table_obj.get_location()
    
    print(f"桌子边界: min={table_min}, max={table_max}")
    print(f"桌子中心: {table_location}")
    
    # 计算桌子的可用表面区域（稍微缩小一点避免物品太靠近边缘）
    safe_margin = 20.0  # 距离桌子边缘的边距
    surface_min_x = table_min.x + safe_margin
    surface_max_x = table_max.x - safe_margin
    surface_min_y = table_min.y + safe_margin
    surface_max_y = table_max.y - safe_margin
    surface_z = table_max.z  # 桌子表面高度
    
    print(f"可用表面区域: X[{surface_min_x:.2f}-{surface_max_x:.2f}], Y[{surface_min_y:.2f}-{surface_max_y:.2f}], Z={surface_z:.2f}")
    
    spawned_items = []  # 已生成的物品列表
    item_aabbs = []     # 已生成物品的边界框列表
    # 可选的物品蓝图列表
    TABLE_ITEMS_BLUEPRINTS = [
        "BP_Food_182", "BP_Food_183", "BP_Food_Bread_05", 
        "BP_Food_Donut_3", "BP_Food_Cake", "BP_Flex_Cup_Kitchen",
        "BP_Cup_Decor_003", "BP_Cup_Mug_White", "BP_Spoon_ChildSpoon", 
        "BP_Spoon_006"
    ]

    for item_index in range(num_items):
        if len(TABLE_ITEMS_BLUEPRINTS) == 0:
            print("[WARNING] 没有可用的物品蓝图")
            break
        
        # 随机选择一个物品蓝图
        blueprint = random.choice(TABLE_ITEMS_BLUEPRINTS)
        item_placed = False
        attempts = 0
        
        while not item_placed and attempts < max_attempts_per_item:
            attempts += 1
            
            try:
                # 在桌子表面随机生成位置
                item_x = random.uniform(surface_min_x, surface_max_x)
                item_y = random.uniform(surface_min_y, surface_max_y)
                item_z = surface_z + 1.0  # 稍微高于桌子表面，避免初始碰撞
                
                item_location = ts.Vector3(item_x, item_y, item_z)
                
                # 生成物品
                item_obj = ue.spawn_entity(
                    entity_type=ts.BaseObjectEntity,
                    blueprint=blueprint,
                    location=item_location,
                    is_simulating_physics=True,
                    scale=ts.Vector3(1, 1, 1),  # 使用较小的缩放
                    quat=None
                )
                
                # 等待物理引擎稳定
                time.sleep(0.01)
                
                # 获取物品的边界框
                item_aabb = item_obj.get_world_aabb()
                item_aabb.min ,item_aabb.max = fix_aabb_bounds(item_aabb)
                
                # 检查是否与其他物品重叠
                overlap_found = False
                for existing_aabb in item_aabbs:
                    if check_item_overlap(
                        existing_aabb.min, existing_aabb.max,  # 传递min/max向量
                        item_aabb.min, item_aabb.max,  # 传递min/max向量
                        safe_margin=safe_margin
                    ):
                        overlap_found = True
                        break
                
                if overlap_found:
                    ue.destroy_entity(item_obj.id)
                    continue
                
                # 成功放置物品
                spawned_items.append(item_obj)
                item_aabbs.append(item_aabb)
                item_placed = True
                
                print(f"物品 {item_index+1} 生成成功: {blueprint} 在位置 {item_location}")
                
            except Exception as e:
                print(f"生成物品时出现异常: {e}")
                if 'item_obj' in locals():
                    try:
                        ue.destroy_entity(item_obj.id)
                    except:
                        pass
        
        if not item_placed:
            print(f"[WARNING] 无法为物品 {item_index+1} 找到合适的位置")
    
    print(f"成功在桌子上生成了 {len(spawned_items)} 个物品")
    return spawned_items

# 生成人附近的物品
def generate_objects_with_agent(ue, table_object, target_agent, agents, num_items=1, max_distance=90, safe_margin = 15):
    """
    在桌子上生成靠近目标人物但远离其他人物的物品
    
    Args:
        ue: TongSim实例
        table_object: 桌子对象
        target_agent: 目标人物
        agents: 所有人物列表
        num_items: 要生成的物品数量
        max_distance: 物品距离目标人物的最大距离
    
    Returns:
        list: 生成的物品对象列表
    """

    # 可选的物品蓝图列表
    TABLE_ITEMS_BLUEPRINTS = [
        "BP_Food_182", "BP_Food_183", "BP_Food_Bread_05", 
        "BP_Food_Donut_3", "BP_Food_Cake", "BP_Flex_Cup_Kitchen",
        "BP_Cup_Decor_003", "BP_Cup_Mug_White", "BP_Spoon_ChildSpoon", 
        "BP_Spoon_006"
    ]

    if not table_object:
        print("[ERROR] 桌子对象为空，无法生成物品")
        return []
    
    # 获取桌子的世界AABB边界和位置
    table_aabb = table_object.get_world_aabb()
    table_min ,table_max = fix_aabb_bounds(table_aabb)
    table_location = table_object.get_location()
    
    print(f"桌子边界: min={table_min}, max={table_max}")
    print(f"桌子中心: {table_location}")
    
    # 计算桌子的可用表面区域（稍微缩小一点避免物品太靠近边缘）
    surface_min_x = table_min.x + safe_margin
    surface_max_x = table_max.x - safe_margin
    surface_min_y = table_min.y + safe_margin
    surface_max_y = table_max.y - safe_margin
    surface_z = table_max.z  # 桌子表面高度
    
    # 获取目标人物位置
    target_location = target_agent.get_location()
    target_pos = ts.Vector3(target_location.x, target_location.y, target_location.z)

    # 获取其他人物位置
    other_agents_positions = []
    for agent in agents:
        if agent.id != target_agent.id:  # 排除目标人物
            agent_location = agent.get_location()
            other_agents_positions.append(ts.Vector3(agent_location.x, agent_location.y, agent_location.z))
    
    spawned_items = []
    item_aabbs = []

    for item_index in range(num_items):
        if len(TABLE_ITEMS_BLUEPRINTS) == 0:
            print("[WARNING] 没有可用的物品蓝图")
            break
        
        blueprint = random.choice(TABLE_ITEMS_BLUEPRINTS)
        item_placed = False
        attempts = 0
        max_attempts = 20

        while not item_placed and attempts < max_attempts:
            attempts += 1
            
            try:
                # 在桌子表面随机生成位置
                item_x = random.uniform(surface_min_x, surface_max_x)
                item_y = random.uniform(surface_min_y, surface_max_y)
                item_z = surface_z + 1.0
                
                item_location = ts.Vector3(item_x, item_y, item_z)
                
                # 计算到目标人物的距离
                distance_to_target = math.sqrt(
                    (item_x - target_pos.x)**2 + 
                    (item_y - target_pos.y)**2
                )
                
                # 检查是否在最大距离范围内
                if distance_to_target > max_distance:
                    continue
                
                # 检查是否离其他人物足够远（至少保持一定距离）
                too_close_to_others = False
                for other_pos in other_agents_positions:
                    distance_to_other = math.sqrt(
                        (item_x - other_pos.x)**2 + 
                        (item_y - other_pos.y)**2
                    )
                    if distance_to_other < distance_to_target:  # 比其他人物至少保持70%的最大距离 或者 比其他人距离比自己近
                        too_close_to_others = True
                        break
                
                if too_close_to_others:
                    continue
                
                # 生成物品
                item_obj = ue.spawn_entity(
                    entity_type=ts.BaseObjectEntity,
                    blueprint=blueprint,
                    location=item_location,
                    is_simulating_physics=True,
                    scale=ts.Vector3(1, 1, 1),
                    quat=None
                )

                time.sleep(0.01)
                
                # 获取物品的边界框
                item_aabb = item_obj.get_world_aabb()
                item_aabb.min ,item_aabb.max = fix_aabb_bounds(item_aabb)
                
                # 检查是否与其他物品重叠
                overlap_found = False
                for existing_aabb in item_aabbs:
                    if check_item_overlap(
                        existing_aabb.min, existing_aabb.max,  # 传递min/max向量
                        item_aabb.min, item_aabb.max,  # 传递min/max向量
                        safe_margin=safe_margin
                    ):
                        overlap_found = True
                        break
                
                if overlap_found:
                    ue.destroy_entity(item_obj.id)
                    continue
                
                # 成功放置物品
                spawned_items.append(item_obj)
                item_aabbs.append(item_aabb)
                item_placed = True
                
                print(f"物品生成成功: {blueprint}")
                print(f"  位置: {item_location}")
                print(f"  距离目标人物: {distance_to_target:.2f}cm")
                
            except Exception as e:
                print(f"生成物品时出现异常: {e}")
                if 'item_obj' in locals():
                    try:
                        ue.destroy_entity(item_obj.id)
                    except:
                        pass
        
        if not item_placed:
            print(f"[WARNING] 无法找到合适的位置放置物品")
    
    print(f"成功生成了 {len(spawned_items)} 个靠近目标人物的物品")
    return spawned_items

# 桌子分区
def divide_table_into_zones(table_object, max_zone_length=200.0, zone_depth_ratio = 0.4, print_info=False):
    """
    将桌子划分为多个功能分区
    
    Args:
        table_object: 桌子对象
        target_agent: 目标人物对象（可选，用于确定主要朝向）
        zone_depth_ratio: 分区深度比例
        max_zone_length: 单个区域最大长度，超过此长度会自动拆分
        print_info: 是否打印分区信息
    
    Returns:
        dict: 分区信息字典，key为分区名称，value为分区边界框
    """

    # 获取桌子的世界AABB边界和位置
    table_aabb = table_object.get_world_aabb()
    table_min, table_max = fix_aabb_bounds(table_aabb)
    
    # 计算桌子尺寸
    table_width = table_max.x - table_min.x  # X方向宽度
    table_depth = table_max.y - table_min.y  # Y方向深度
    table_height = table_max.z - table_min.z  # Z方向高度
    
    zones = {}
    
    # 定义四个基本方向的分区
    sides = ['front', 'back', 'right', 'left']

    for side in sides:
        # 根据方向确定分区边界
        if side == 'front':
            # 前分区：从桌子前边缘向内部延伸
            zone_min = ts.Vector3(table_min.x, table_max.y - table_depth * zone_depth_ratio, table_max.z)
            zone_max = ts.Vector3(table_max.x, table_max.y, table_max.z)
            zone_width = table_width
            
        elif side == 'back':
            # 后分区：从桌子后边缘向内部延伸
            zone_min = ts.Vector3(table_min.x, table_min.y, table_max.z)
            zone_max = ts.Vector3(table_max.x, table_min.y + table_depth * zone_depth_ratio, table_max.z)
            zone_width = table_width
            
        elif side == 'right':
            # 右分区：从桌子右边缘（最小X值）向内部延伸
            # X轴：左正右负，所以右边缘是min.x（更负的值）
            zone_min = ts.Vector3(table_min.x, table_min.y, table_max.z)
            zone_max = ts.Vector3(table_min.x + table_width * zone_depth_ratio, table_max.y, table_max.z)
            zone_width = table_depth
            
        elif side == 'left':
            # 左分区：从桌子左边缘（最大X值）向内部延伸
            # X轴：左正右负，所以左边缘是max.x（更正的值）
            zone_min = ts.Vector3(table_max.x - table_width * zone_depth_ratio, table_min.y, table_max.z)
            zone_max = ts.Vector3(table_max.x, table_max.y, table_max.z)
            zone_width = table_depth
        
        # 检查是否需要拆分区域
        if zone_width > max_zone_length:
            # 需要拆分为两个子区域
            mid_point = (zone_min.x + zone_max.x) / 2 if side in ['front', 'back'] else (zone_min.y + zone_max.y) / 2
            
            if side in ['front', 'back']:
                # X轴方向拆分（左正右负）
                # 左侧子区域（X值较大，更正的值）
                zone_left_min = ts.Vector3(mid_point, zone_min.y, zone_max.z)
                zone_left_max = ts.Vector3(zone_max.x, zone_max.y, zone_max.z)
                
                # 右侧子区域（X值较小，更负的值）
                zone_right_min = ts.Vector3(zone_min.x, zone_min.y, zone_max.z)
                zone_right_max = ts.Vector3(mid_point, zone_max.y, zone_max.z)
                
                zones[f'{side}_left'] = {'min': zone_left_min, 'max': zone_left_max, 'side': side}
                zones[f'{side}_right'] = {'min': zone_right_min, 'max': zone_right_max, 'side': side}
                
            else:                
                # 前侧子区域（Y值较大）
                zone_front_min = ts.Vector3(zone_min.x, mid_point, zone_max.z)
                zone_front_max = ts.Vector3(zone_max.x, zone_max.y, zone_max.z)
                
                # 后侧子区域（Y值较小）
                zone_back_min = ts.Vector3(zone_min.x, zone_min.y, zone_max.z)
                zone_back_max = ts.Vector3(zone_max.x, mid_point, zone_max.z)
                
                zones[f'{side}_front'] = {'min': zone_front_min, 'max': zone_front_max, 'side': side}
                zones[f'{side}_back'] = {'min': zone_back_min, 'max': zone_back_max, 'side': side}
                
        else:
            # 不需要拆分，使用完整区域
            zones[side] = {'min': zone_min, 'max': zone_max, 'side': side}
    
    # 打印分区信息
    if print_info:
        print(f"桌子尺寸: 宽{table_width:.1f} × 深{table_depth:.1f} × 高{table_height:.1f}")
        print("分区信息:")
        for zone_name, zone_data in zones.items():
            zone_size = (
                zone_data['max'].x - zone_data['min'].x,
                zone_data['max'].y - zone_data['min'].y
            )
            main_flag = " (主要)" if zone_data.get('is_main', False) else ""
            print(f"  {zone_name}: {zone_size[0]:.1f}×{zone_size[1]:.1f}{main_flag}")
            print(f"  {zone_data['min'], zone_data['max']}")
    
    return zones

# 根据人物位置对分区进行更细致的划分
def refine_zone_for_person(zone_bbox, table_object, target_agent, handedness='right', main_zone_min_width=60.0, temp_zone_size=40.0, print_info=False):
    """
    根据人物位置对分区进行更细致的划分
    
    Args:
        zone_bbox: 原始分区边界框 {'min': Vector3, 'max': Vector3, 'side': str}
        table_object: 桌子对象
        target_agent: 目标人物对象
        handedness: 利手信息 ('right'或'left')
        temp_zone_size: 临时区域大小
        main_zone_min_width: 最小工作区尺寸
        print_info: 是否打印信息
    
    Returns:
        dict: 细化后的分区信息
    """
    # 得出人物的side
    agent_side = determine_object_side(target_agent, table_object)
    
    if agent_side == 'unknown':
        print("无法确定人物位置，使用默认分区")
        return {}
    
    # 先尝试精确匹配基础side（如front、back、left、right）
    if agent_side in zone_bbox:
        # 直接匹配基础分区
        agent_zone_data = zone_bbox[agent_side]
        agent_zone_name = agent_side
    else:
        # 处理细分分区的情况
        # 根据人物的基本方向找到相关的细分分区
        related_zones = {}
        for zone_name, zone_data in zone_bbox.items():
            if agent_side in zone_name:
                related_zones[zone_name] = zone_data
        
        if len(related_zones) > 0:
            # 获取人物位置
            agent_pos = target_agent.get_location()
            agent_x, agent_y, agent_z = agent_pos.x, agent_pos.y, agent_pos.z
            
            # 根据人物的基本方向确定判断逻辑
            if agent_side in ['left', 'right']:
                # 对于左右分区，需要判断人物在前后方向的位置
                # 计算桌子在Y方向的中点
                table_aabb = table_object.get_world_aabb()
                table_min, table_max = fix_aabb_bounds(table_aabb)
                table_center_y = (table_min.y + table_max.y) / 2
                
                if agent_y > table_center_y:
                    # 人物在桌子的前侧
                    target_zone_name = f"{agent_side}_front"
                else:
                    # 人物在桌子的后侧
                    target_zone_name = f"{agent_side}_back"
                
                # 检查目标分区是否存在
                if target_zone_name in related_zones:
                    agent_zone_data = related_zones[target_zone_name]
                    agent_zone_name = target_zone_name
                else:
                    # 如果目标分区不存在，选择第一个相关分区
                    agent_zone_name = list(related_zones.keys())[0]
                    agent_zone_data = related_zones[agent_zone_name]
                    
            elif agent_side in ['front', 'back']:
                # 对于前后分区，需要判断人物在左右方向的位置
                # 计算桌子在X方向的中点
                table_aabb = table_object.get_world_aabb()
                table_min, table_max = fix_aabb_bounds(table_aabb)
                table_center_x = (table_min.x + table_max.x) / 2
                
                if agent_x > table_center_x:
                    # X轴左正右负，agent_x > table_center_x 表示在桌子左侧
                    target_zone_name = f"{agent_side}_left"
                else:
                    # agent_x < table_center_x 表示在桌子右侧
                    target_zone_name = f"{agent_side}_right"
                
                # 检查目标分区是否存在
                if target_zone_name in related_zones:
                    agent_zone_data = related_zones[target_zone_name]
                    agent_zone_name = target_zone_name
                else:
                    # 如果目标分区不存在，选择第一个相关分区
                    agent_zone_name = list(related_zones.keys())[0]
                    agent_zone_data = related_zones[agent_zone_name]
        else:
            # 如果没有找到任何相关分区，选择最近的分区（理论上不会发生）
            return {}

    # 获取匹配的分区信息
    zone_min = agent_zone_data['min']
    zone_max = agent_zone_data['max']
    zone_side = agent_zone_data['side']
    
    # 计算分区尺寸
    zone_width = zone_max.x - zone_min.x
    zone_depth = zone_max.y - zone_min.y

    # 计算桌子中心
    table_aabb = table_object.get_world_aabb()
    table_min, table_max = fix_aabb_bounds(table_aabb)
    table_center_x = (table_min.x + table_max.x) / 2
    table_center_y = (table_min.y + table_max.y) / 2
    
    # 确定利手侧（常用区域侧）
    # 注意：利手是相对于人的视角，而不是桌子的绝对方向
    dominant_side = handedness

    refined_zones = {}
    # 根据分区方向确定划分逻辑
    if zone_side in ['front', 'back']:
        # 前后分区：沿X轴划分（宽度方向）
        total_width = zone_width
        
        # 确保主工作区最小宽度
        main_zone_width = max(main_zone_min_width, total_width * 0.5)
        main_zone_width = min(main_zone_width, total_width)
        
        # 计算剩余宽度
        remaining_width = total_width - main_zone_width
        
        # 计算各区域起始位置（居中布置）
        main_zone_start_x = zone_min.x + remaining_width / 2
        main_zone_end_x = main_zone_start_x + main_zone_width
        
        # 常用区域和非常用区域（深度一致）
        # 根据人物位置和利手确定常用区域位置
        if agent_side == 'front':
            # 人在桌子前面
            if dominant_side == 'right':
                # 右利手：常用区域在桌子左边（靠近xmin）
                infrequent_zone_min = ts.Vector3(zone_min.x, zone_min.y, zone_min.z)
                infrequent_zone_max = ts.Vector3(main_zone_start_x, zone_max.y, zone_max.z)
                
                frequent_zone_min = ts.Vector3(main_zone_end_x, zone_min.y, zone_min.z)
                frequent_zone_max = ts.Vector3(zone_max.x, zone_max.y, zone_max.z)
            else:
                # 左利手：常用区域在桌子右边（靠近xmax）
                infrequent_zone_min = ts.Vector3(main_zone_end_x, zone_min.y, zone_min.z)
                infrequent_zone_max = ts.Vector3(zone_max.x, zone_max.y, zone_max.z)
                
                frequent_zone_min = ts.Vector3(zone_min.x, zone_min.y, zone_min.z)
                frequent_zone_max = ts.Vector3(main_zone_start_x, zone_max.y, zone_max.z)
        else:
            # 人在桌子后面（面对桌子）
            if dominant_side == 'right':
                # 右利手：常用区域在桌子右边（靠近xmax）
                infrequent_zone_min = ts.Vector3(main_zone_end_x, zone_min.y, zone_min.z)
                infrequent_zone_max = ts.Vector3(zone_max.x, zone_max.y, zone_max.z)
                
                frequent_zone_min = ts.Vector3(zone_min.x, zone_min.y, zone_min.z)
                frequent_zone_max = ts.Vector3(main_zone_start_x, zone_max.y, zone_max.z)
            else:
                # 左利手：常用区域在桌子左边（靠近xmin）
                infrequent_zone_min = ts.Vector3(zone_min.x, zone_min.y, zone_min.z)
                infrequent_zone_max = ts.Vector3(main_zone_start_x, zone_max.y, zone_max.z)
                
                frequent_zone_min = ts.Vector3(main_zone_end_x, zone_min.y, zone_min.z)
                frequent_zone_max = ts.Vector3(zone_max.x, zone_max.y, zone_max.z)
        
        # 主工作区
        main_zone_min = ts.Vector3(main_zone_start_x, zone_min.y, zone_min.z)
        main_zone_max = ts.Vector3(main_zone_end_x, zone_max.y, zone_max.z)
        
    else:
        # 左右分区：沿Y轴划分（深度方向）
        total_depth = zone_depth
        
        # 确保主工作区最小宽度
        main_zone_depth = max(main_zone_min_width, total_depth * 0.5)
        main_zone_depth = min(main_zone_depth, total_depth)
        
        # 计算剩余深度
        remaining_depth = total_depth - main_zone_depth
        
        # 计算各区域起始位置（居中布置）
        main_zone_start_y = zone_min.y + remaining_depth / 2
        main_zone_end_y = main_zone_start_y + main_zone_depth

        # 常用区域和非常用区域（深度一致）
        # 根据人物位置和利手确定常用区域位置
        if agent_side == 'left':
            # 人在桌子左侧
            if dominant_side == 'right':
                # 右利手：常用区域在桌子后边（靠近ymin）
                frequent_zone_min = ts.Vector3(zone_min.x, zone_min.y, zone_min.z)
                frequent_zone_max = ts.Vector3(zone_max.x, main_zone_start_y, zone_max.z)
                
                infrequent_zone_min = ts.Vector3(zone_min.x, main_zone_end_y, zone_min.z)
                infrequent_zone_max = ts.Vector3(zone_max.x, zone_max.y, zone_max.z)
            else:
                # 左利手：常用区域在桌子前边（靠近ymax）
                frequent_zone_min = ts.Vector3(zone_min.x, main_zone_end_y, zone_min.z)
                frequent_zone_max = ts.Vector3(zone_max.x, zone_max.y, zone_max.z)
                
                infrequent_zone_min = ts.Vector3(zone_min.x, zone_min.y, zone_min.z)
                infrequent_zone_max = ts.Vector3(zone_max.x, main_zone_start_y, zone_max.z)
        else:
            # 人在桌子右侧
            if dominant_side == 'right':
                # 右利手：常用区域在桌子前边（靠近ymax）
                frequent_zone_min = ts.Vector3(zone_min.x, main_zone_end_y, zone_min.z)
                frequent_zone_max = ts.Vector3(zone_max.x, zone_max.y, zone_max.z)
                
                infrequent_zone_min = ts.Vector3(zone_min.x, zone_min.y, zone_min.z)
                infrequent_zone_max = ts.Vector3(zone_max.x, main_zone_start_y, zone_max.z)
            else:
                # 左利手：常用区域在桌子后边（靠近ymin）
                frequent_zone_min = ts.Vector3(zone_min.x, zone_min.y, zone_min.z)
                frequent_zone_max = ts.Vector3(zone_max.x, main_zone_start_y, zone_max.z)
                
                infrequent_zone_min = ts.Vector3(zone_min.x, main_zone_end_y, zone_min.z)
                infrequent_zone_max = ts.Vector3(zone_max.x, zone_max.y, zone_max.z)
        
        # 主工作区
        main_zone_min = ts.Vector3(zone_min.x, main_zone_start_y, zone_min.z)
        main_zone_max = ts.Vector3(zone_max.x, main_zone_end_y, zone_max.z)

    # 构建返回结果
    refined_zones['main'] = {'min': main_zone_min, 'max': main_zone_max, 'type': 'main'}
    refined_zones['frequent'] = {'min': frequent_zone_min, 'max': frequent_zone_max, 'type': 'frequent'}
    refined_zones['infrequent'] = {'min': infrequent_zone_min, 'max': infrequent_zone_max, 'type': 'infrequent'}
    
    # 临时区域（如果需要）
    if temp_zone_size > 0:
        # 判断分区类型
        if '_' not in agent_zone_name:
            # 基础分区（front、back、left、right）
            if zone_side in ['front', 'back']:
                # 前后分区
                if agent_side == 'front':
                    # 人在前面
                    if dominant_side == 'right':
                        # 右利手：临时区域放在左上角（Xmax, Ymax）
                        temp_zone_min = ts.Vector3(zone_max.x - temp_zone_size, zone_max.y - temp_zone_size, zone_min.z)
                        temp_zone_max = ts.Vector3(zone_max.x, zone_max.y, zone_max.z)
                    else:
                        # 左利手：临时区域放在右上角（Xmin, Ymax）
                        temp_zone_min = ts.Vector3(zone_min.x, zone_max.y - temp_zone_size, zone_min.z)
                        temp_zone_max = ts.Vector3(zone_min.x + temp_zone_size, zone_max.y, zone_max.z)
                else:
                    # 人在后面
                    if dominant_side == 'right':
                        # 右利手：临时区域放在右下角（Xmax, Ymin）
                        temp_zone_min = ts.Vector3(zone_max.x - temp_zone_size, zone_min.y, zone_min.z)
                        temp_zone_max = ts.Vector3(zone_max.x, zone_min.y + temp_zone_size, zone_max.z)
                    else:
                        # 左利手：临时区域放在左下角（Xmin, Ymin）
                        temp_zone_min = ts.Vector3(zone_min.x, zone_min.y, zone_min.z)
                        temp_zone_max = ts.Vector3(zone_min.x + temp_zone_size, zone_min.y + temp_zone_size, zone_max.z)
            else:
                # 左右分区
                if agent_side == 'left':
                    # 人在左侧
                    if dominant_side == 'right':
                        # 右利手：临时区域放在左下角（Xmax, Ymin）
                        temp_zone_min = ts.Vector3(zone_max.x - temp_zone_size, zone_min.y, zone_min.z)
                        temp_zone_max = ts.Vector3(zone_max.x, zone_min.y + temp_zone_size, zone_max.z)
                    else:
                        # 左利手：临时区域放在左上角（Xmax, Ymax）
                        temp_zone_min = ts.Vector3(zone_max.x - temp_zone_size, zone_max.y - temp_zone_size, zone_min.z)
                        temp_zone_max = ts.Vector3(zone_max.x, zone_max.y, zone_max.z)
                else:
                    # 人在右侧
                    if dominant_side == 'right':
                        # 右利手：临时区域放在右上角（Xmin, Ymax）
                        temp_zone_min = ts.Vector3(zone_min.x, zone_max.y - temp_zone_size, zone_min.z)
                        temp_zone_max = ts.Vector3(zone_min.x + temp_zone_size, zone_max.y, zone_max.z)
                    else:
                        # 左利手：临时区域放在右下角（Xmin, Ymin）
                        temp_zone_min = ts.Vector3(zone_min.x, zone_min.y, zone_min.z)
                        temp_zone_max = ts.Vector3(zone_min.x + temp_zone_size, zone_min.y + temp_zone_size, zone_max.z)
        else:
            # 细分分区（front_left、right_front等）- 与利手无关
            if 'front' in agent_zone_name and 'left' in agent_zone_name:
                # front_left: 临时区域放在左上角（Xmax, Ymax）
                temp_zone_min = ts.Vector3(zone_max.x - temp_zone_size, zone_max.y - temp_zone_size, zone_min.z)
                temp_zone_max = ts.Vector3(zone_max.x, zone_max.y, zone_max.z)
            elif 'front' in agent_zone_name and 'right' in agent_zone_name:
                # front_right: 临时区域放在右上角（Xmin, Ymax）
                temp_zone_min = ts.Vector3(zone_min.x, zone_max.y - temp_zone_size, zone_min.z)
                temp_zone_max = ts.Vector3(zone_min.x + temp_zone_size, zone_max.y, zone_max.z)
            elif 'back' in agent_zone_name and 'left' in agent_zone_name:
                # back_left: 临时区域放在左下角（Xmax, Ymin）
                temp_zone_min = ts.Vector3(zone_max.x - temp_zone_size, zone_min.y, zone_min.z)
                temp_zone_max = ts.Vector3(zone_max.x, zone_min.y + temp_zone_size, zone_max.z)
            elif 'back' in agent_zone_name and 'right' in agent_zone_name:
                # back_right: 临时区域放在右下角（Xmin, Ymin）
                temp_zone_min = ts.Vector3(zone_min.x, zone_min.y, zone_min.z)
                temp_zone_max = ts.Vector3(zone_min.x + temp_zone_size, zone_min.y + temp_zone_size, zone_max.z)
            elif 'left' in agent_zone_name and 'front' in agent_zone_name:
                # left_front: 临时区域放在左上角（Xmax, Ymax）
                temp_zone_min = ts.Vector3(zone_max.x - temp_zone_size, zone_max.y - temp_zone_size, zone_min.z)
                temp_zone_max = ts.Vector3(zone_max.x, zone_max.y, zone_max.z)
            elif 'left' in agent_zone_name and 'back' in agent_zone_name:
                # left_back: 临时区域放在左下角（Xmax, Ymin）
                temp_zone_min = ts.Vector3(zone_max.x - temp_zone_size, zone_min.y, zone_min.z)
                temp_zone_max = ts.Vector3(zone_max.x, zone_min.y + temp_zone_size, zone_max.z)
            elif 'right' in agent_zone_name and 'front' in agent_zone_name:
                # right_front: 临时区域放在右上角（Xmin, Ymax）
                temp_zone_min = ts.Vector3(zone_min.x, zone_max.y - temp_zone_size, zone_min.z)
                temp_zone_max = ts.Vector3(zone_min.x + temp_zone_size, zone_max.y, zone_max.z)
            elif 'right' in agent_zone_name and 'back' in agent_zone_name:
                # right_back: 临时区域放在右下角（Xmin, Ymin）
                temp_zone_min = ts.Vector3(zone_min.x, zone_min.y, zone_min.z)
                temp_zone_max = ts.Vector3(zone_min.x + temp_zone_size, zone_min.y + temp_zone_size, zone_max.z)
        
        refined_zones['temporary'] = {'min': temp_zone_min, 'max': temp_zone_max, 'type': 'temporary'}

    # 打印分区信息
    if print_info:
        print(f"人物专属分区 (侧: {zone_side}, 利手: {handedness}), 桌子分区: {agent_zone_name}:")
        for zone_name, zone_data in refined_zones.items():
            zone_size_x = zone_data['max'].x - zone_data['min'].x
            zone_size_y = zone_data['max'].y - zone_data['min'].y
            print(f"  {zone_name}: {zone_size_x:.1f}×{zone_size_y:.1f}")
            print(f"    {zone_data['min']}, {zone_data['max']}")
    
    return refined_zones

# 根据特定的分区生成物品
def spawn_items_in_person_zone(ue, table_object, target_agent, refined_zones, zone_types, item_blueprints, scale=ts.Vector3(1, 1, 1), 
                               rotation_z=0, rotation_x=0, rotation_y=0, on_table_items=None, 
                               max_distance=90.0, min_distance=10.0, safe_margin=5.0, print_info=False):
    """
    在人物专属分区内生成物品
    
    Args:
        ue: TongSim实例
        table_object: 桌子对象
        target_agent: 目标人物对象
        item_blueprints: 物品蓝图列表
        refined_zones: 细化后的分区信息
        zone_types: 指定的分区类型
        rotation: 旋转角度
        max_distance: 物品离人的最大距离
        min_distance: 物品离人的最小距离
        safe_margin: 物品离桌子边缘的安全距离
        on_table_items: 桌子上已有的物品列表
        print_info: 是否打印信息
    
    Returns:
        list: 生成的物品对象列表
    """

    if on_table_items is None:
        on_table_items = []
    
    # 检查zone_type是否有效
    valid_zones = []
    for zone_type in zone_types:
        if zone_type in refined_zones:
            valid_zones.append(zone_type)
        else:
            print(f"警告: 分区类型 '{zone_type}' 不存在于细化分区中")
    
    # 获取桌子的AABB和表面高度
    table_aabb = table_object.get_world_aabb()
    table_min, table_max = fix_aabb_bounds(table_aabb)
    table_surface_z = table_max.z

    # 获取目标人物位置
    target_pos = target_agent.get_location()
    
    # 获取已知物品的AABB列表
    existing_aabbs = []
    for item in on_table_items:
        item_aabb = item.get_world_aabb()
        item_min, item_max = fix_aabb_bounds(item_aabb)
        existing_aabbs.append((item_min, item_max))

    spawned_items = []
    item_aabbs = existing_aabbs.copy()  # 复制已知物品的AABB
    
    # 为每个蓝图生成一个物品
    for i, blueprint in enumerate(item_blueprints):
        item_placed = False
        attempts = 0
        max_attempts=100

        # 根据物品索引选择分区类型
        zone_type = valid_zones[i % len(valid_zones)]
        zone_data = refined_zones[zone_type]
        # 获取分区边界
        zone_min = zone_data['min']
        zone_max = zone_data['max']
        zone_side = zone_data.get('side', 'unknown')  # 获取分区所在的方向

        # 尝试在分区内放置物品
        while not item_placed and attempts < max_attempts:
            attempts += 1

            # 在选择的区域表面随机生成位置
            item_x = random.uniform(zone_min.x, zone_max.x)
            item_y = random.uniform(zone_min.y, zone_max.y)
            item_z = table_surface_z + 1.0  # 放在桌面之上
            
            item_location = ts.Vector3(item_x, item_y, item_z)

            # 计算到目标人物的距离
            distance_to_target = math.sqrt(
                (item_x - target_pos.x)**2 + 
                (item_y - target_pos.y)**2
            )
            
            # 检查距离是否在范围内
            if distance_to_target > max_distance or distance_to_target < min_distance:
                continue

            # 检查是否与其他物品重叠
            overlap_found_pre = False
            for existing_min, existing_max in item_aabbs:
                if check_position_in_bbox(item_location, existing_min, existing_max, safe_margin, False):
                    overlap_found_pre = True
                    break
            
            if overlap_found_pre:
                continue

            target_tem_pos = ts.Vector3(target_pos.x, target_pos.y, item_z)
            rotation_quat = look_at_rotation(item_location, target_tem_pos)

            # 创建绕各个轴的旋转四元数
            def create_axis_rotation(angle_degrees, axis):
                """创建绕指定轴旋转的四元数"""
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
            
            # 创建各个轴的旋转
            x_rotation = create_axis_rotation(rotation_x, 'x')
            y_rotation = create_axis_rotation(rotation_y, 'y')
            z_rotation = create_axis_rotation(rotation_z, 'z')

            # 组合所有旋转（注意旋转顺序很重要，这里使用Z->Y->X的顺序）
            final_rotation = rotation_quat * z_rotation * y_rotation * x_rotation

            # 生成物品
            item_obj = ue.spawn_entity(
                entity_type=ts.BaseObjectEntity,
                blueprint=blueprint,
                location=item_location,
                is_simulating_physics=True,
                scale=scale,
                quat=final_rotation
            )
            
            # 等待物理引擎稳定
            time.sleep(0.01)
            
            # 获取物品的边界框
            item_aabb = item_obj.get_world_aabb()
            item_min, item_max = fix_aabb_bounds(item_aabb)
            
            # 检查是否与其他物品重叠
            overlap_found = False
            for existing_min, existing_max in item_aabbs:
                if check_item_overlap(
                    item_min, item_max, 
                    existing_min, existing_max, 
                    safe_margin=safe_margin
                ):
                    overlap_found = True
                    break
            
            if overlap_found:
                ue.destroy_entity(item_obj.id)
                continue
            
            # 检查物品是否完全在桌子上（考虑安全边距）
            if not is_bbox_contained(
                item_min, item_max,  # 物品的边界框
                table_min, table_max,  # 桌子的边界框
                safe_margin=safe_margin,  # 可以根据需要调整安全边距
                check_z_axis=False  # Z轴通常不需要检查，因为物品在桌子上
            ):
                ue.destroy_entity(item_obj.id)
                continue
            
            # 成功放置物品
            spawned_items.append(item_obj)
            item_aabbs.append((item_min, item_max))
            item_placed = True

            # 同时更新传入的 on_table_items
            if on_table_items is not None:
                on_table_items.append(item_obj)
            if print_info:
                print(f"物品 {blueprint} 生成成功在 {zone_type} 区域, 位置 {item_location}, 距离人物 {distance_to_target:.1f}")
        
        if not item_placed:
            print(f"警告: 无法放置物品 {blueprint} 在分区内")
    
    return spawned_items

# 为每个agent生成物品配置
def generate_item_configurations(agents, zone_configs, max_total_items=5, max_items_per_agent=3):
    """
    为每个agent生成物品配置
    
    Args:
        agents: 人物对象列表
        zone_configs: zone配置列表
        max_total_items: 桌面最大物品总数
        max_items_per_agent: 每个人物最多物品数量
    
    Returns:
        list: 物品配置列表，每个元素为字典格式
    """

    # 人物蓝图映射表
    blueprint_mapping = {
        'girl': ["SDBP_Aich_AIBabyV7_Shoes", "SDBP_Aich_AIBaby_Lele_Shoes"],
        'boy': ["SDBP_Aich_AIBaby_Tiantian_90"],
        'woman': ["SDBP_Aich_Liyuxia"],
        'grandpa': ["SDBP_Aich_Yeye"],
        'man': ["SDBP_Aich_Zhanghaoran"]
    }

    # 读取物品文件
    def read_item_file(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print(f"警告: 文件 {filename} 不存在")
            return []
    
    # 非重复物品类型列表（这些类型的物品每个只能出现一次）
    non_repeating_item_types = ['computer', 'glasses', 'phone']
    # 物品蓝图定义
    item_blueprints = {
        'cup': read_item_file("./ownership/object/mycup.txt"),
        'book': read_item_file("./ownership/object/mybook.txt"),
        'computer': ["BP_Laptop_01"],
        'pen': read_item_file("./ownership/object/pen.txt"),
        'food': read_item_file("./ownership/object/myfood.txt"),
        'toy': read_item_file("./ownership/object/mytoy.txt"),
        'phone': ["BP_Phone"],
        'glasses': ["BP_Decor_Eyeglasses01Frame01"]
    }

    # 人物与物品的对应关系表
    agent_item_mapping = {
        'girl': ['book', 'toy'],
        'boy': ['book', 'toy'],
        'woman': ['computer', 'phone', 'glasses'],
        'man': ['computer', 'phone', 'glasses'],
        'grandpa': ['book', 'glasses'],
        'unknown': ['book']
    }
    # 通用物品（所有人都可能拥有）
    common_items = ['cup', 'food', 'pen']

    # 物品属性表
    item_properties = {
        'book': {
            'zone_types': ['main', 'frequent', 'infrequent'],
            'rotation_z': -90,
            'rotation_x': 90,
            'rotation_y': 0,
            'scale': ts.Vector3(0.6, 0.6, 0.6)
        },
        'toy': {
            'zone_types': ['frequent', 'infrequent'],
            'rotation_z': 0,
            'rotation_x': 0,
            'rotation_y': 0,
            'scale': ts.Vector3(0.5, 0.5, 0.5)
        },
        'computer': {
            'zone_types': ['main'],
            'rotation_z': -90,
            'rotation_x': 0,
            'rotation_y': 0,
            'scale': ts.Vector3(0.8, 0.8, 0.8)
        },
        'phone': {
            'zone_types': ['frequent', 'temporary'],
            'rotation_z': 90,
            'rotation_x': 90,
            'rotation_y': -90,
            'scale': ts.Vector3(0.6, 0.6, 0.6)
        },
        'glasses': {
            'zone_types': ['frequent'],
            'rotation_z': 90,
            'rotation_x': 0,
            'rotation_y': 0,
            'scale': ts.Vector3(0.6, 0.6, 0.6)
        },
        'cup': {
            'zone_types': ['frequent'],
            'rotation_z': 180,
            'rotation_x': 0,
            'rotation_y': 0,
            'scale': ts.Vector3(0.8, 0.8, 0.8)
        },
        'food': {
            'zone_types': ['frequent', 'infrequent'],
            'rotation_z': 0,
            'rotation_x': 0,
            'rotation_y': 0,
            'scale': ts.Vector3(0.6, 0.6, 0.6)
        },
        'pen': {
            'zone_types': ['frequent', 'infrequent'],
            'rotation_z': 0,
            'rotation_x': 0,
            'rotation_y': 0,
            'scale': ts.Vector3(0.8, 0.8, 0.8)
        }
    }

    # 检查agents和zone_configs长度是否匹配
    if len(agents) != len(zone_configs):
        raise ValueError("agents和zone_configs长度必须一致")

    # 第一步：确定每个人物类型
    agent_types = {}
    for agent in agents:
        agent_type = 'unknown'
        agent_id = getattr(agent, 'id', '')
        
        for agent_type_name, blueprints in blueprint_mapping.items():
            # 从前开始匹配，检查agent_id是否以blueprint中的任何一个字符串开头
            for blueprint in blueprints:
                if agent_id.startswith(blueprint):
                    agent_type = agent_type_name
                    break
            if agent_type != 'unknown':
                break
        
        if agent_type == 'unknown':
            print(f"警告: 无法识别人物类型 {agent_id}")
        
        agent_types[agent] = agent_type

    # 初始化数据结构
    all_configs = []
    used_items = set()  # 已使用的物品
    used_item_types = set()  # 已使用的非重复物品类型
    agent_occupied_zones = {agent: set() for agent in agents}  # 每个人物已占用的分区
    agent_item_count = {agent: 0 for agent in agents}  # 每个人物的物品数量
    
    # 合并特定偏好和通用物品
    all_item_preferences = {}
    # 为每个人物类型创建偏好配置
    for agent_type in agent_item_mapping.keys():
        all_item_preferences[agent_type] = []
        
        # 添加特定物品
        for item_type in agent_item_mapping[agent_type]:
            if item_type in item_properties:
                all_item_preferences[agent_type].append({
                    'types': [item_type],
                    **item_properties[item_type]
                })
        
        # 添加通用物品
        for item_type in common_items:
            if item_type in item_properties:
                all_item_preferences[agent_type].append({
                    'types': [item_type],
                    **item_properties[item_type]
                })
    # 确保unknown类型存在
    if 'unknown' not in all_item_preferences:
        all_item_preferences['unknown'] = [{
            'types': ['book'],
            **item_properties['book']
        }]

    # 第二步：循环生成物品配置
    attempt_count = 0
    max_attempts = max_total_items * 30  # 设置最大尝试次数，避免无限循环
    while len(all_configs) < max_total_items and attempt_count < max_attempts:
        attempt_count += 1
        # 如果所有人物都已达到最大物品数量，提前结束
        if all(count >= max_items_per_agent for count in agent_item_count.values()):
            break

        # 过滤掉已经被使用的非重复物品类型
        available_item_types = [t for t in item_blueprints.keys() 
                            if item_blueprints[t] and 
                            (t not in non_repeating_item_types or t not in used_item_types)]
        if not available_item_types:
            continue
        item_type = random.choice(available_item_types)

        # 随机选择一个具体的物品
        available_items = [i for i in item_blueprints[item_type] if i not in used_items]
        if not available_items:
            continue
        item = random.choice(available_items)

        # 找到所有可能喜欢这个物品的人物类型
        possible_agent_types = []
        for agent_type, prefs in all_item_preferences.items():
            for pref in prefs:
                if item_type in pref['types']:
                    if agent_type not in possible_agent_types:
                        possible_agent_types.append(agent_type)
                    break

        # 找到符合条件的人物
        valid_agents = []
        for agent in agents:
            if (agent_types[agent] in possible_agent_types and 
                agent_item_count[agent] < max_items_per_agent):
                valid_agents.append(agent)
        if not valid_agents:
            continue
        # 随机选择一个有效人物
        agent = random.choice(valid_agents)
        agent_type = agent_types[agent]
        
        # 找到这个人物类型对这个物品的偏好设置
        preference_settings = []
        for pref in all_item_preferences[agent_type]:
            if item_type in pref['types']:
                preference_settings.append(pref)
        if not preference_settings:
            continue
        # 随机选择一个偏好设置
        preference = random.choice(preference_settings)

        # 找到可用的区域类型
        available_zones = [zone for zone in preference['zone_types'] if zone not in agent_occupied_zones[agent]]
        if not available_zones:
            continue
        # 随机选择一个区域类型
        zone_type = random.choice(available_zones)
        
        # 找到对应的zone_config
        agent_idx = agents.index(agent)
        zone_config = zone_configs[agent_idx]
        
        # 创建配置
        item_config = {
            'agent': agent,
            'refined_zones': zone_config,
            'zone_types': [zone_type],
            'item_blueprints': [item],
            'scale': preference['scale'],
            'rotation_z': preference['rotation_z'],
            'rotation_x': preference['rotation_x'],  # 默认为0
            'rotation_y': preference['rotation_y'],  # 默认为0
            'max_distance': 150.0,
            'min_distance': 10.0,
            'safe_margin': 0.0
        }
        
        # 更新状态
        used_items.add(item)
        agent_occupied_zones[agent].add(zone_type)
        agent_item_count[agent] += 1
        all_configs.append(item_config)

        # 如果是非重复物品类型，添加到已使用类型集合
        if item_type in non_repeating_item_types:
            used_item_types.add(item_type)

    return all_configs





# 生成随机摄像头位置
def generate_camera_positions(room_bound, target_object, distance_range=[200, 500], num_cameras=5, z_min_height=180, z_max_height=300, safe_margin = 25.0, print_info=False):
    """
    为指定房间生成在半球范围内的随机摄像头位置
    
    Args:
        room_bound: 房间边界框
        target_object: 拍摄目标对象
        distance_range: 摄像头到目标的距离范围 [min_distance, max_distance]
        num_cameras: 需要生成的摄像头数量
        z_min_height: 摄像头最小高度（相对于地面）
        z_max_height: 摄像头最大高度（相对于地面）
    
    Returns:
        list: 摄像头位置列表 [ts.Vector3, ...]
    """
    
    # 获取目标物体的位置
    target_location = target_object.get_location()
    target_x, target_y, target_z = target_location.x, target_location.y, target_location.z
    
    # 提取房间边界坐标
    room_x_min, room_x_max, room_y_min , room_y_max, room_z_min, room_z_max  = room_bound
    
    # 距离范围
    min_distance, max_distance = distance_range

    # 生成随机摄像头位置（在半球范围内）
    camera_positions = []
    attempts = 0
    max_attempts = num_cameras * 200  # 最大尝试次数
    
    while len(camera_positions) < num_cameras and attempts < max_attempts:

        attempts += 1
        
        # 在半球范围内生成随机方向
        theta = random.uniform(0, 2 * math.pi)  # 水平角度
        phi = random.uniform(math.pi / 6, math.pi / 4)    # 垂直角度（上半球）

        
        # 随机距离
        distance = random.uniform(min_distance, max_distance)

        # 计算球坐标到直角坐标的转换
        x_offset = distance * math.sin(phi) * math.cos(theta)
        y_offset = distance * math.sin(phi) * math.sin(theta)
        z_offset = distance * math.cos(phi)
        
        # 计算摄像头位置（相对于目标）
        camera_x = target_x + x_offset
        camera_y = target_y + y_offset
        camera_z = target_z + z_offset
        
        # 确保摄像头高度在指定范围内
        camera_z = max(camera_z, z_min_height)
        camera_z = min(camera_z, z_max_height)
        
        # 检查是否在房间边界内
        is_in_room = check_position_in_bbox(ts.Vector3(camera_x, camera_y, camera_z), 
                                            ts.Vector3(room_x_min, room_y_min, room_z_min), 
                                            ts.Vector3(room_x_max, room_y_max, room_z_max), -safe_margin, False)
        if is_in_room:
            
            camera_pos = ts.Vector3(camera_x, camera_y, camera_z)
            camera_positions.append(camera_pos)
            
            if print_info:
                print(f"    摄像头 {len(camera_positions)}: ({camera_x:.2f}, {camera_y:.2f}, {camera_z:.2f})")
                print(f"    距离目标: {distance:.2f}, 角度: ({math.degrees(theta):.1f}°, {math.degrees(phi):.1f}°)")
    
    if len(camera_positions) < num_cameras:
        print(f"警告：只成功生成了 {len(camera_positions)}/{num_cameras} 个摄像头位置")
    
    return camera_positions

# 生成摄像头
def add_capture_camera(ue, camera_positions, target_obj, camera_name_prefix="Camera", print_info=False):
    """
    为每个摄像头位置创建摄像头，并使其看向目标对象
    
    Args:
        ue: TongSim实例
        camera_positions: 摄像头位置列表 [ts.Vector3, ...]
        target_obj: 目标对象，需要有get_location()方法
        camera_name_prefix: 摄像头名称前缀
    
    Returns:
        list: 创建的摄像头对象列表
    """
    cameras = []
    target_position = target_obj.get_location()
    
    for i, camera_position in enumerate(camera_positions):
        # 生成唯一的摄像头名称
        camera_name = f"{camera_name_prefix}_{i+1}"
        
        # 计算摄像头朝向目标的旋转
        camera_quat = look_at_rotation(camera_position, target_position)
        
        # 创建摄像头
        camera = ue.spawn_camera(
            camera_name = camera_name,  # 修正参数名
            loc = camera_position,  # 修正参数名和变量名
            quat = camera_quat,
            # fov= 90.0,
            # width = 1024,
            # height = 1024,
        )
        camera.set_intrinsic_params(90.0, 4096, 4096)
        cameras.append(camera)
        
        if print_info:
            print(f"已创建摄像头 {camera_name} 在位置 {camera_position}")
    
    return cameras

# 使用所有摄像头拍摄并保存图像
def capture_and_save_images(ue, cameras, save_dir="logs", delay_before_capture=0.5, RGB = True, Depth = False, print_info=False):
    """
    使用所有摄像头拍摄并保存图像
    
    Args:
        ue: TongSim实例
        cameras: 摄像头对象列表
        save_dir: 图像保存目录
        delay_before_capture: 拍摄前的延迟（秒），确保场景稳定
    
    Returns:
        dict: 保存的图像路径信息
    """
    
    # 创建保存目录
    os.makedirs(save_dir, exist_ok=True)
    
    # 生成时间戳用于文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 等待场景稳定
    if delay_before_capture > 0:
        print(f"等待 {delay_before_capture} 秒让场景稳定...")
        time.sleep(delay_before_capture)
    
    saved_images = {}
    
    for i, camera in enumerate(cameras):
        camera_id = camera.get_name() if hasattr(camera, 'get_name') else f"Camera_{i+1}"
        print(f"正在使用摄像头 {camera_id} 拍摄...")
        
        try:
            # 获取当前帧图像（RGB 和 Depth）
            image_wrapper = camera.get_current_imageshot(rgb=RGB, depth=False)
            
            # 使用图像时间戳作为唯一标识
            time_tag = str(image_wrapper.render_time)
            camera_prefix = f"{camera_id}_{time_tag}"
            
            # 保存RGB图像
            if image_wrapper.rgb:
                rgb_filename = f"{timestamp}_{camera_prefix}_rgb.png"
                rgb_path = os.path.join(save_dir, rgb_filename)
                with open(rgb_path, "wb") as f:
                    f.write(image_wrapper.rgb)
                print(f"[Saved] RGB image -> {rgb_path}")
                
                # 记录保存路径
                if camera_id not in saved_images:
                    saved_images[camera_id] = {}
                saved_images[camera_id]['rgb'] = rgb_path
            
            # 保存Depth图像
            if image_wrapper.depth:
                depth_filename = f"{timestamp}_{camera_prefix}_depth.png"
                depth_path = os.path.join(save_dir, depth_filename)
                with open(depth_path, "wb") as f:
                    f.write(image_wrapper.depth)
                print(f"[Saved] Depth image -> {depth_path}")
                
                # 记录保存路径
                if camera_id not in saved_images:
                    saved_images[camera_id] = {}
                saved_images[camera_id]['depth'] = depth_path
            
            print(f"摄像头 {camera_id} 拍摄完成")
            
        except Exception as e:
            print(f"[Error] 摄像头 {camera_id} 拍摄失败: {e}")
            if camera_id not in saved_images:
                saved_images[camera_id] = {}
            saved_images[camera_id]['error'] = str(e)
    
    return saved_images


# 创建桌子例子
def run_example():
    with ts.TongSim(
        grpc_endpoint="127.0.0.1:5056",
        legacy_grpc_endpoint="127.0.0.1:50052",
    ) as ue:
        ue.open_level("SDBP_Map_000")

        rooms = ue.spatical_manager.get_current_room_info()
        print(f"[INFO] 房间信息: {rooms}")
        room_bbox_dict = get_room_bbox(rooms) 
        print(f"[INFO] 房间边界bbox信息: {room_bbox_dict}")

        # 定义房间
        selected_room_name = "babyRoom"
        room_bound = get_room_boundary(selected_room_name, room_bbox_dict)
        # 根据房间空余位置生成桌子位置
        table_obj = spawn_table(
            ue=ue,
            room_name=selected_room_name,
            room_bbox_dict=room_bbox_dict,
            blueprint="BP_CoffeeTable_005",
            scale=ts.Vector3(1, 1, 1),
            safe_margin=50
        )
        if table_obj:
            print(f"桌子生成成功，ID: {table_obj.id}")
            # 继续生成人物等其他操作
        else:
            print("桌子生成失败，请检查房间空间是否足够")

        on_table_items, nearby_items  = find_objects_near_table(
            ue=ue,
            table_object=table_obj,
            search_distance=80.0
        )

        existed_chairs = filter_objects_by_type(objects_list=nearby_items, type_file_path='./ownership/chair.txt')

        chairs = generate_chairs(
            ue=ue,
            table_object=table_obj,
            room_bbox_dict=room_bbox_dict,
            room_name=selected_room_name,
            num_chairs=2,
            chair_sides=['left', 'right'],
            type_file_path='./ownership/chair.txt',
            chair_blueprints=None,
            nearby_objects=existed_chairs,
            min_distance=30,
            max_distance=80,
            safe_margin=20
        )

        nearby_items.extend(chairs)
        print(nearby_items)

        # # 在桌子上生成3个随机物品
        table_items = spawn_items_on_table(
            ue=ue,
            table_obj=table_obj,
            num_items=4,  # 生成3个物品
            max_attempts_per_item=20  # 每个物品最多尝试20次
        )
        
        # print(f"桌子上共有 {len(table_items)} 个物品")

        # 在桌子周围生成人物
        agents = spawn_agents_around_table(
            ue=ue,
            table_obj=table_obj,
            room_bbox_dict=room_bbox_dict,
            room_name=selected_room_name,
            nearby_objects = nearby_items,
            num_agents=2,
            min_distance=10,  # 距离桌子最近
            max_distance=200,  # 距离桌子最远
            safe_margin=0,
            print_info=False
        )
        # ue.change_view_mode(ViewModeType.THIRD_PERSON_VIEW)
        ue.change_view_mode(ViewModeType.MANUAL_CONTROL_VIEW)


        # # 执行坐下动作
        # matched_pairs = agents_random_sit(ue, agents, chairs, sit_probability=0.5)
        # print(f"\n匹配结果: 共 {len(matched_pairs)} 对人物-椅子匹配")
        # for agent, chair, distance in matched_pairs:
        #     print(f"  - {agent.id} 坐在 {chair.id} 上 (距离: {distance:.2f})")

        # obj_owner = generate_objects_with_agent(
        #     ue=ue,
        #     table_object=table_obj,
        #     target_agent=agents[0],
        #     agents=agents,
        #     num_items=2,
        #     max_distance=90,
        #     safe_margin= 5
        # )


        # 生成随机摄像头位置
        # camera_positions = generate_camera_positions(
        #     room_bound=room_bound,
        #     target_object=table_obj,
        #     distance_range=[300, 800],  # 距离目标300-600单位
        #     num_cameras=10,  # 生成摄像头个数
        #     z_min_height=180,  # 最低高度
        #     z_max_height=240  # 最高高度
        # )

        # # 创建所有摄像头
        # cameras = add_capture_camera(ue, camera_positions, table_obj)
        # print(f"成功创建了 {len(cameras)} 个摄像头")

        # # 拍摄图像
        # saved_images = capture_and_save_images(
        #     ue=ue,
        #     cameras=cameras,
        #     save_dir="./ownership/logs/table_scene_001",  # 自定义保存路径
        #     delay_before_capture=0.01  # 拍摄前等待1秒让物理稳定
        # )

# 已有桌子例子
def run_example_existedtable_randomagnets():
    with ts.TongSim(
        grpc_endpoint="127.0.0.1:5056",
        legacy_grpc_endpoint="127.0.0.1:50052",
    ) as ue:
        ue.open_level("SDBP_Map_019")

        rooms = ue.spatical_manager.get_current_room_info()
        print(f"[INFO] 房间信息: {rooms}")
        room_bbox_dict = get_room_bbox(rooms) 
        print(f"[INFO] 房间边界bbox信息: {room_bbox_dict}")

        # 定义房间
        selected_room_name = "diningRoom"
        room_bound = get_room_boundary(selected_room_name, room_bbox_dict)

        # 查询房间内的桌子
        table_entity = query_existing_tables_in_room(
            ue=ue,
            room_bound=room_bound
        )

        if table_entity:
            print(f"成功获取桌子实体: {table_entity.id}")

        on_table_items, nearby_items  = find_objects_near_table(
            ue=ue,
            table_object=table_entity,
            search_distance=80.0
        )

        # 在桌子周围生成人物
        agents = random_spawn_agents_around_table(
            ue=ue,
            table_obj=table_entity,
            room_bbox_dict=room_bbox_dict,
            room_name=selected_room_name,
            nearby_objects=nearby_items,
            num_agents=4,
            min_distance=10,  # 距离桌子最小单位
            max_distance=80,  # 距离桌子最大单位
            safe_margin=30
        )

        print(nearby_items)

        # 在桌子上生成3个随机物品
        # table_items = spawn_items_on_table(wd
        #     ue=ue,
        #     table_obj=table_entity,
        #     num_items=4,  # 生成3个waw物品
        #     max_attempts_per_item=20  # 每个物品最多尝试20次
        # )
        
        # print(f"桌子上共有 {len(table_items)} 个物品")

        existed_chairs = filter_objects_by_type(objects_list=nearby_items, type_file_path='./ownership/chair.txt')
        
        ue.change_view_mode(ViewModeType.MANUAL_CONTROL_VIEW)
        # 执行坐下动作
        matched_pairs = agents_random_sit(ue, agents, existed_chairs, 0.75)
        print(f"\n匹配结果: 共 {len(matched_pairs)} 对人物-椅子匹配")
        for agent, chair, distance in matched_pairs:
            print(f"  - {agent.id} 坐在 {chair.id} 上 (距离: {distance:.2f})")

        obj_owner = generate_objects_with_agent(
            ue=ue,
            table_object=table_entity,
            target_agent=agents[0],
            agents=agents,
            num_items=2,
            max_distance=90,
            safe_margin= 10
        )
        obj_owner = generate_objects_with_agent(
            ue=ue,
            table_object=table_entity,
            target_agent=agents[2],
            agents=agents,
            num_items=1,
            max_distance=90,
            safe_margin= 10
        )      
        obj_owner = generate_objects_with_agent(
            ue=ue,
            table_object=table_entity,
            target_agent=agents[3],
            agents=agents,
            num_items=3,
            max_distance=90,
            safe_margin= 10
        )


        # # 生成随机摄像头位置
        # camera_positions = generate_camera_positions(
        #     room_name=selected_room_name,
        #     room_bbox_dict=room_bbox_dict,
        #     target_object=table_entity,
        #     distance_range=[300, 800],  # 距离目标300-600单位
        #     num_cameras=10,  # 生成摄像头个数
        #     z_min_height=180,  # 最低高度
        #     z_max_height=240  # 最高高度
        # )

        # # 创建所有摄像头
        # cameras = add_capture_camera(ue, camera_positions, table_entity)
        # print(f"成功创建了 {len(cameras)} 个摄像头")

        # # 拍摄图像
        # saved_images = capture_and_save_images(
        #     ue=ue,
        #     cameras=cameras,
        #     save_dir="./ownership/logs/table_scene_001",  # 自定义保存路径
        #     delay_before_capture=0.01  # 拍摄前等待1秒让物理稳定
        # )aw

# 已有桌子例子
def run_example_existedtable():
    with ts.TongSim(
        grpc_endpoint="127.0.0.1:5056",
        legacy_grpc_endpoint="127.0.0.1:50052",
    ) as ue:
        ue.open_level("SDBP_Map_013")

        rooms = ue.spatical_manager.get_current_room_info()
        print(f"[INFO] 房间信息: {rooms}")
        room_bbox_dict = get_room_bbox(rooms) 
        print(f"[INFO] 房间边界bbox信息: {room_bbox_dict}")

        # 定义房间
        selected_room_name = "diningRoom"
        room_bound = get_room_boundary(selected_room_name, room_bbox_dict)

        # 查询房间内的桌子
        table_entity = query_existing_tables_in_room(
            ue=ue,
            room_bound=room_bound
        )

        if table_entity:
            print(f"成功获取桌子实体: {table_entity.id}")

        on_table_items, nearby_items  = find_objects_near_table(
            ue=ue,
            table_object=table_entity,
            search_distance=80.0
        )

        # 在桌子周围生成人物
        agents = random_spawn_agents_around_table(
            ue=ue,
            table_obj=table_entity,
            room_bbox_dict=room_bbox_dict,
            room_name=selected_room_name,
            nearby_objects=nearby_items,
            num_agents=2,
            min_distance=10,  # 距离桌子最小单位
            max_distance=80,  # 距离桌子最大单位
            safe_margin=20,
            print_info=False
        )
        # agents = spawn_agents_around_table(
        #     ue=ue,
        #     table_obj=table_entity,
        #     room_bbox_dict=room_bbox_dict,
        #     room_name=selected_room_name,
        #     nearby_objects=nearby_items,
        #     agent_blueprints=["SDBP_Aich_Yeye", "SDBP_Aich_Zhanghaoran"],
        #     agent_sides=["front", "back"],
        #     min_distance=10,  # 距离桌子最小单位
        #     max_distance=80,  # 距离桌子最大单位
        #     safe_margin=30
        # )

        # 在桌子上生成3个随机物品
        # table_items = spawn_items_on_table(wd
        #     ue=ue,
        #     table_obj=table_entity,
        #     num_items=4,  # 生成3个waw物品
        #     max_attempts_per_item=20  # 每个物品最多尝试20次
        # )
        # print(f"桌子上共有 {len(table_items)} 个物品")

        existed_chairs = filter_objects_by_type(objects_list=nearby_items, type_file_path='./ownership/chair.txt')
        
        ue.change_view_mode(ViewModeType.MANUAL_CONTROL_VIEW)
        # 执行坐下动作
        matched_pairs = agents_random_sit(ue, agents, existed_chairs, 0.75)
        print(f"\n匹配结果: 共 {len(matched_pairs)} 对人物-椅子匹配")
        for agent, chair, distance in matched_pairs:
            print(f"  - {agent.id} 坐在 {chair.id} 上 (距离: {distance:.2f})")

        # 执行坐下动作
        # agent_is_sit_list = [True, True]  # 第4个人物不坐下
        # agent_sides_list = ['front', 'front']  # 对应每个人物的方向
        # # agent_sides_list = ['right', 'left']  # 对应每个人物的方向

        # matched_pairs = agents_sit(
        #     ue=ue,
        #     room_bbox_dict=room_bbox_dict,
        #     room_name=selected_room_name,
        #     agents=agents,
        #     agent_is_sit=agent_is_sit_list,  # 需要提供这个列表
        #     table_object=table_entity,
        #     agent_sides=agent_sides_list,    # 需要提供这个列表
        #     chairs=existed_chairs,
        #     min_distance=30,
        #     max_distance=80
        # )

        print(f"\n匹配结果: 共 {len(matched_pairs)} 对人物-椅子匹配")
        for agent, chair, distance, side in matched_pairs:
            print(f"  - {agent.id} 坐在 {chair.id} 上 (方向: {side}, 距离: {distance:.2f})")

        obj_owner = generate_objects_with_agent(
            ue=ue,
            table_object=table_entity,
            target_agent=agents[0],
            agents=agents,
            num_items=2,
            max_distance=90,
            safe_margin= 10
        )



        # # 生成随机摄像头位置
        # camera_positions = generate_camera_positions(
        #     room_name=selected_room_name,
        #     room_bbox_dict=room_bbox_dict,
        #     target_object=table_entity,
        #     distance_range=[300, 800],  # 距离目标300-600单位
        #     num_cameras=10,  # 生成摄像头个数
        #     z_min_height=180,  # 最低高度
        #     z_max_height=240  # 最高高度
        # )

        # # 创建所有摄像头
        # cameras = add_capture_camera(ue, camera_positions, table_entity)
        # print(f"成功创建了 {len(cameras)} 个摄像头")

        # # 拍摄图像
        # saved_images = capture_and_save_images(
        #     ue=ue,
        #     cameras=cameras,
        #     save_dir="./ownership/logs/table_scene_001",  # 自定义保存路径
        #     delay_before_capture=0.01  # 拍摄前等待1秒让物理稳定
        # )aw

# 规划人物排布
def run_example_existedtable_planedagents():
    with ts.TongSim(
        grpc_endpoint="127.0.0.1:5056",
        legacy_grpc_endpoint="127.0.0.1:50052",
    ) as ue:
        ue.open_level("SDBP_Map_015")

        rooms = ue.spatical_manager.get_current_room_info()
        print(f"[INFO] 房间信息: {rooms}")
        room_bbox_dict = get_room_bbox(rooms) 
        print(f"[INFO] 房间边界bbox信息: {room_bbox_dict}")

        # 定义房间
        selected_room_name = "diningRoom"
        room_bound = get_room_boundary(selected_room_name, room_bbox_dict)

        # 查询房间内的桌子
        table_entity = query_existing_tables_in_room(
            ue=ue,
            room_bound=room_bound
        )

        if table_entity:
            print(f"成功获取桌子实体: {table_entity.id}")

        zones = divide_table_into_zones(table_object = table_entity, max_zone_length=160.0, zone_depth_ratio = 0.4, print_info=True)

        on_table_items, nearby_items  = find_objects_near_table(
            ue=ue,
            table_object=table_entity,
            search_distance=120.0
        )

        # 在桌子周围生成人物
        agent_blueprints, agent_sides, agent_is_sit = generate_agent_configuration(
            # num_agents=3,
            # agent_traits=['grandpa', 'girl', 'woman'],
            # agent_sides=['front', 'left', 'right'],  # 每个人物的方向
            sit_probability=0.5  # 50%概率坐下
        )
        agent_plans = plan_agents_around_table(
            ue=ue,
            table_object=table_entity,
            room_bound=room_bound,
            agent_blueprints=agent_blueprints,
            agent_sides=agent_sides,
            agent_is_sit=agent_is_sit,
            nearby_objects=nearby_items,
            min_distance=30,
            max_distance=80,
            print_info=True
        )
        # 计算成功的规划数量（status不为'failed'的数量）
        successful_plans = [plan for plan in agent_plans if plan.get('status') != 'failed']
        successful_count = len(successful_plans)
        # 检查条件：成功的规划数量必须>=2，且总长度也必须>=2
        if successful_count < 2 or len(agent_plans) < 2:
            print(f"未能规划出足够的人物位置，结束。成功规划: {successful_count}, 总规划: {len(agent_plans)}")
            return
        
        agents = execute_agent_plans(
            ue=ue,
            agent_plans=agent_plans,
            print_info=True
        )
        ue.change_view_mode(ViewModeType.MANUAL_CONTROL_VIEW)

        zone_configs = [
            refine_zone_for_person(
                zones, 
                table_entity, 
                agent, 
                handedness='right', 
                main_zone_min_width=60.0, 
                temp_zone_size=25.0, 
                print_info=True
            )
            for agent in agents
        ]

        item_configs = generate_item_configurations(
            agents=agents,
            zone_configs=zone_configs,
            max_total_items=7,  # 桌面最多物品
            max_items_per_agent=3  # 每个人最多物品
        )

        # 为每个配置生成物品
        for config in item_configs:
            spawned_items = spawn_items_in_person_zone(
                ue=ue,
                table_object=table_entity,
                target_agent=config['agent'],
                refined_zones=config['refined_zones'],
                zone_types=config['zone_types'],
                item_blueprints=config['item_blueprints'],
                scale=config['scale'],
                rotation_z=config['rotation_z'],
                rotation_x=config['rotation_x'],  # 添加 rotation_x
                rotation_y=config['rotation_y'],  # 添加 rotation_y
                on_table_items=on_table_items,
                max_distance=config['max_distance'],
                min_distance=config['min_distance'],
                safe_margin=config['safe_margin'],
                print_info=True
            )

        print("Finish")


        # 生成随机摄像头位置
        camera_positions = generate_camera_positions(
            room_bound=room_bound,
            target_object=table_entity,
            distance_range=[200, 500],  # 距离目标300-600单位
            num_cameras=10,  # 生成摄像头个数
            z_min_height=120,  # 最低高度
            z_max_height=250  # 最高高度
        )

        # 创建所有摄像头
        cameras = add_capture_camera(ue, camera_positions, table_entity)
        print(f"成功创建了 {len(cameras)} 个摄像头")

        # 拍摄图像
        saved_images = capture_and_save_images(
            ue=ue,
            cameras=cameras,
            save_dir="./ownership/logs/table_scene_001",  # 自定义保存路径
            delay_before_capture=0.01  # 拍摄前等待1秒让物理稳定
        )


# 接下来控制的是 合理化
#  控制人物生成: 年龄、性别、人物之间站位或者座位安排
#  size: 物品大小 桌子大小 人物大小参数 哪些该随机、哪些该自适应？
#  背景物品属性: 什么场景该出现什么背景？例如餐桌上不能出现显示屏？例如办公桌上不能出现玩具？以及椅子的款式应该要自适应？
#  定义 interested objects 的摆放规律参数，比如说位置，朝向，款式。例如就近原则，杯把朝向自己，例如款式也可能决定物品的归属，小孩用优质卡通款，大人使用成熟简约款，老人使用复古怀旧款
# 格子思想

# 关于人物座次的思路
# 第一步，确定桌子旁边椅子的分布情况，椅子有多怎么办，椅子少怎么办，椅子怎么分布？
# 第二部，根据人物的站位以及人物的创建agent对应的pos以及朝向，但是不及时创建人物
# 第三步，我们根据前面的人物的位置或者是否坐下等信息，创建人物并且执行行动

# pipline 生成思路
# 房间遍历，需要生成房间列表
# 桌子遍历，需要查找桌子
# 最关键核心：人与物品遍历
# 男女老少分组
# 物品分为 mian 核心区域 book computer 
# 常用区 computerMouse pen 
# 非常用区 cup food

# pipline 
def run_pipline_table_with_agents_objects():
    with ts.TongSim(
        grpc_endpoint="127.0.0.1:5056",
        legacy_grpc_endpoint="127.0.0.1:50052",
    ) as ue:
        # 定义地图范围
        map_range = range(21, 29)  # 000-257

        for map_num in map_range:
            # 格式化地图名称
            map_name = f"SDBP_Map_{map_num:03d}"

            # 打开地图
            print(f"\n[INFO] 正在打开地图: {map_name}")
            success = ue.open_level(map_name)
                
            if not success:
                print(f"[WARNING] 无法打开地图: {map_name}，跳过")
                continue
            
            try:
                # 获取房间信息
                rooms = ue.spatical_manager.get_current_room_info()
                if not rooms:
                    print(f"[WARNING] 地图 {map_name} 中没有找到房间信息，跳过")
                    continue
                    
                print(f"[INFO] 地图 {map_name} 的房间信息: {rooms}")
                
                # 获取房间边界框信息
                room_bbox_dict = get_room_bbox(rooms)
                print(f"[INFO] 地图 {map_name} 的房间边界bbox信息: {room_bbox_dict}")
                
                # 遍历当前地图的所有房间
                for room_info in rooms:
                    room_name = room_info['room_name']
                    
                    print(f"\n[PROCESSING] 处理地图 {map_name} 的房间: {room_name}")
                    room_bound = get_room_boundary(room_name, room_bbox_dict)

                    # 面积小于4 跳过
                    if get_room_area(room_bound) < 4:
                        continue

                    # 查询房间内的桌子
                    table_entity = query_existing_tables_in_room(ue=ue, room_bound=room_bound)
                    # 如果房间没有桌子，跳过
                    if table_entity is None or not table_entity:
                        print(f"[INFO] 房间 {room_name} 没有桌子，跳过")
                        continue
                    
                    zones = divide_table_into_zones(table_object = table_entity, max_zone_length=160.0, zone_depth_ratio = 0.4, print_info=False)

                    on_table_items, nearby_items  = find_objects_near_table(
                        ue=ue,
                        table_object=table_entity,
                        search_distance=150.0
                    )

                    # 在桌子周围生成人物
                    agent_blueprints, agent_sides, agent_is_sit = generate_agent_configuration(
                        sit_probability=0.5  # 50%概率坐下
                    )
                    agent_plans = plan_agents_around_table(
                        ue=ue,
                        table_object=table_entity,
                        room_bound=room_bound,
                        agent_blueprints=agent_blueprints,
                        agent_sides=agent_sides,
                        agent_is_sit=agent_is_sit,
                        nearby_objects=nearby_items,
                        min_distance=30,
                        max_distance=80,
                        print_info=False
                    )
                    # 计算成功的规划数量（status不为'failed'的数量）
                    successful_plans = [plan for plan in agent_plans if plan.get('status') != 'failed']
                    successful_count = len(successful_plans)
                    # 检查条件：成功的规划数量必须>=2，且总长度也必须>=2
                    if successful_count < 2 or len(agent_plans) < 2:
                        print(f"未能规划出足够的人物位置，结束。成功规划: {successful_count}, 总规划: {len(agent_plans)}")
                        continue

                    agents = execute_agent_plans(
                        ue=ue,
                        agent_plans=agent_plans,
                        print_info=False
                    )

                    zone_configs = [
                        refine_zone_for_person(
                            zones, 
                            table_entity, 
                            agent, 
                            handedness='right', 
                            main_zone_min_width=60.0, 
                            temp_zone_size=25.0, 
                            print_info=False
                        )
                        for agent in agents
                    ]

                    item_configs = generate_item_configurations(
                        agents=agents,
                        zone_configs=zone_configs,
                        max_total_items=7,  # 桌面最多物品
                        max_items_per_agent=3  # 每个人最多物品
                    )

                    total_spawned_items = 0
                    all_spawned_items = []
                    # 为每个配置生成物品
                    for config in item_configs:
                        spawned_items = spawn_items_in_person_zone(
                            ue=ue,
                            table_object=table_entity,
                            target_agent=config['agent'],
                            refined_zones=config['refined_zones'],
                            zone_types=config['zone_types'],
                            item_blueprints=config['item_blueprints'],
                            scale=config['scale'],
                            rotation_z=config['rotation_z'],
                            rotation_x=config['rotation_x'],
                            rotation_y=config['rotation_y'],
                            on_table_items=on_table_items,
                            max_distance=config['max_distance'],
                            min_distance=config['min_distance'],
                            safe_margin=config['safe_margin'],
                            print_info=False
                        )
                        total_spawned_items += len(spawned_items)
                        all_spawned_items.extend(spawned_items)

                    # 生成随机摄像头位置
                    camera_positions = generate_camera_positions(
                        room_bound=room_bound,
                        target_object=table_entity,
                        distance_range=[300, 600],  # 距离目标
                        num_cameras=10,  # 生成摄像头个数
                        z_min_height=120,  # 最低高度
                        z_max_height=250  # 最高高度
                    )

                    # 创建所有摄像头
                    cameras = add_capture_camera(ue, camera_positions, table_entity)
                    print(f"成功创建了 {len(cameras)} 个摄像头")

                    # 生成保存目录名称
                    save_dir_name = f"table_scene_map{map_num:03d}_agents{len(agents)}_items{total_spawned_items}"
                    save_dir = f"./ownership/logs/{save_dir_name}"
                    # 拍摄图像
                    saved_images = capture_and_save_images(
                        ue=ue,
                        cameras=cameras,
                        save_dir=save_dir,  # 自定义保存路径
                        delay_before_capture=0.01  # 拍摄前等待1秒让物理稳定
                    )
                    
                    print(f"[SUCCESS] 场景生成完成: {save_dir_name}")
                    print(f"  地图: {map_name}")
                    print(f"  房间: {room_name}")
                    print(f"  人物数量: {len(agents)}")
                    print(f"  物品总数: {total_spawned_items}")
                    print(f"  摄像头数量: {len(cameras)}")
                    print(f"  保存图像数量: {len(saved_images)}")
                    
            except Exception as e:
                print(f"[ERROR] 处理地图 {map_name} 时发生错误: {str(e)}")
                continue

# 摄像头角度设计
# 根据人物的在桌子的位置进行摄像头的选择
# 根据人物的角度进行摄像头的选择，根据人物与摄像头的距离自适应摄像头的位置

if __name__ == "__main__":
    # run_example()
    # run_example_existedtable_randomagnets()
    # run_example_existedtable_planedagents()
    run_pipline_table_with_agents_objects()
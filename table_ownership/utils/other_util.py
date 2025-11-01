import tongsim as ts
import math
import random
import os
import time


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

# 获得物体aabb边界框
def get_object_aabb(entity):
    """
    获取物体的AABB边界框
    
    Args:
        entity: 物体实体对象
    
    Returns:
        tuple: (min_vector, max_vector) - 物体的最小和最大边界向量
    """
    aabb = entity.get_world_aabb()
    aabb_min, aabb_max = fix_aabb_bounds(aabb)
    return aabb_min, aabb_max

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
        print(f"[ERROR] 房间 '{room_name}' 不存在于room_bbox_dict中")
        return []

    # 获取房间边界框
    bbox_list = room_bbox_dict[room_name]
    if not bbox_list:
        print(f"[ERROR] 房间 '{room_name}' 的边界框数据为空")
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
        print(f"[INFO] 房间 '{room_name}' 信息:")
        print(f"  - 尺寸: {room_width:.2f} × {room_length:.2f} × {room_height:.2f}")
        print(f"  - 中心点: ({center_x:.2f}, {center_y:.2f}, {center_z:.2f})")
        print(f"  - 边界范围: X[{x_min:.2f} ~ {x_max:.2f}], Y[{y_min:.2f} ~ {y_max:.2f}], Z[{z_min:.2f} ~ {z_max:.2f}]")
        
    return [x_min, y_min, z_min, x_max, y_max, z_max]

# 计算面积
def get_area(room_bound):
    """
    获取面积（平方米）
    
    Args:
        room_bound: 边界bbox信息
    
    Returns:
        房间面积（平方米），如果出错返回-1
    """
    try:
        x_min, y_min, _, x_max, y_max, _ = room_bound
        
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

# 桌子验证函数
def validate_table(table_entity, min_table_area, max_aspect_ratio=7.0):
    """
    桌子验证函数
    
    Args:
        table_entity: 桌子实体
        min_table_area: 最小桌面面积
        max_aspect_ratio: 最大长宽比
    
    Returns:
        是否选择桌子
    """

    table_min, table_max = get_object_aabb(table_entity)

    # 计算尺寸
    length_x = abs(table_max.x - table_min.x)
    length_y = abs(table_max.y - table_min.y)
    # 计算面积
    table_area = get_area([table_min.x, table_min.y, table_min.z, table_max.x,  table_max.y, table_max.z])
    if table_area < min_table_area:
        return False
    
    # 确定长边和短边
    long_side = max(length_x, length_y)
    short_side = min(length_x, length_y)

    if (long_side / short_side) >= max_aspect_ratio:
        return False

    return True




# 随机删除桌面物品
def random_remove_table_items(ue, table_object, on_table_items, area_threshold, max_item_count=None, print_info=False):
    """
    随机删除桌面物品，直到桌面物品总面积小于阈值
    
    Args:
        ue: Unreal Engine 实例
        table_object: 桌子对象
        on_table_items: 桌面上的物品列表
        area_threshold: 面积阈值比例
        max_item_count: 最大物品数量限制
    
    Returns:
        删除后的剩余物品列表
    """

    # 计算桌子面积
    table_aabb = table_object.get_world_aabb()
    table_min ,table_max = fix_aabb_bounds(table_aabb)
    table_area = get_area([table_min.x, table_min.y, table_min.z, table_max.x, table_max.y, table_max.z])

    area_threshold_area = table_area * area_threshold
    if print_info:
        print(f"[INFO] 桌子面积: {table_area:.2f} 平方米")
        print(f"[INFO] 面积阈值: {area_threshold_area:.2f} 平方米")
        if max_item_count:
            print(f"[INFO] 最大物品数量限制: {max_item_count}")

    # 计算当前桌面物品总面积
    total_item_area = 0
    item_areas = []
    
    for item in on_table_items:
        try:
            item_aabb = item.get_world_aabb()
            item_min ,item_max = fix_aabb_bounds(item_aabb)
            item_area = get_area([item_min.x, item_min.y, item_min.z, item_max.x, item_max.y, item_max.z])
            
            if item_area > 0:
                total_item_area += item_area
                item_areas.append((item, item_area))
                if print_info:
                    print(f"  物品 {item.id}: {item_area:.2f} 平方米")
        except Exception as e:
            print(f"[WARNING] 无法计算物品 {item.id} 的面积: {e}")
            continue
        
    current_item_count = len(on_table_items)
    if print_info:
        print(f"[INFO] 当前桌面物品数量: {current_item_count}")
        print(f"[INFO] 当前桌面物品总面积: {total_item_area:.2f} 平方米")
    # 检查是否需要删除（面积或数量超出限制）
    area_exceeded = total_item_area > area_threshold_area
    count_exceeded = max_item_count and current_item_count > max_item_count
    
    if not area_exceeded and not count_exceeded:
        if print_info:
            print("[INFO] 桌面物品已满足所有阈值要求，无需删除")
        return on_table_items
    
    # 确定删除原因和目标
    if area_exceeded and count_exceeded:
        delete_reason = "面积和数量都超出限制"
        target_area = area_threshold_area
        target_count = max_item_count
    elif area_exceeded:
        delete_reason = "面积超出限制"
        target_area = area_threshold_area
        target_count = None
    else:
        delete_reason = "数量超出限制"
        target_area = None
        target_count = max_item_count
    
    if print_info:
        print(f"[INFO] 需要删除物品，原因: {delete_reason}")
        if target_area:
            area_to_remove = total_item_area - target_area
            print(f"[INFO] 需要删除的面积: {area_to_remove:.2f} 平方米")
        if target_count:
            count_to_remove = current_item_count - target_count
            print(f"[INFO] 需要删除的物品数量: {count_to_remove}")

    # 随机打乱物品列表
    random.shuffle(item_areas)
    # 随机删除物品直到满足所有阈值
    removed_items = []
    remaining_items = []
    current_area = total_item_area
    current_count = current_item_count
    
    for item, area in item_areas:
        # 检查是否满足所有条件
        area_ok = target_area is None or current_area <= target_area
        count_ok = target_count is None or current_count <= target_count
        
        if area_ok and count_ok:
            # 已经满足所有阈值，保留剩余物品
            remaining_items.append(item)
            continue
        
        # 需要删除这个物品
        try:
            ue.destroy_entity(item.id)
            current_area -= area
            current_count -= 1
            removed_items.append(item)
            
            if print_info:
                status_info = []
                if target_area:
                    status_info.append(f"剩余面积: {current_area:.2f}/{target_area:.2f}")
                if target_count:
                    status_info.append(f"剩余数量: {current_count}/{target_count}")
                
                print(f"[INFO] 删除物品 {item.id}, 面积: {area:.2f} 平方米, {', '.join(status_info)}")
                
        except Exception as e:
            if print_info:
                print(f"[ERROR] 删除物品 {item.id} 失败: {e}")
            remaining_items.append(item)
            # 删除失败，不减少计数和面积
    
    if print_info:
        final_status = []
        if target_area:
            final_status.append(f"最终面积: {current_area:.2f}/{target_area:.2f}")
        if target_count:
            final_status.append(f"最终数量: {current_count}/{target_count}")
        
        print(f"[INFO] 删除完成，{', '.join(final_status)}")
        print(f"[INFO] 剩余物品数量: {len(remaining_items)}, 删除物品数量: {len(removed_items)}")
    
    return remaining_items

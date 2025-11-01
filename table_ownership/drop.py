import os
import cv2
import time
import threading
import math
import numpy as np
import random
import re

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

# 生成随机摄像头位置
def generate_camera_positions(ue, room_bound, target_location, num_cameras=5, safe_margin = 30, 
                              distance_range=[200, 500], height=[180, 300], min_cameras_distance = 40, print_info=False):
    """
    为指定房间生成在半球范围内的随机摄像头位置
    
    Args:
        room_bound: 房间边界框
        target_location: 拍摄目标位置
        num_cameras: 需要生成的摄像头数量
        safe_margin: 边界的安全边距
        distance_range: 摄像头到目标的距离范围 [min_distance, max_distance]
        height: 摄像头高度范围
        min_cameras_distance: 摄像头之间的最小距离
        print_info: 是否打印信息
    
    Returns:
        list: 摄像头位置列表 [ts.Vector3, ...]
    """
    
    # 获取目标物体的位置
    target_x, target_y, target_z = target_location.x, target_location.y, target_location.z
    
    # 提取房间边界坐标
    room_x_min, room_y_min, room_z_min, room_x_max, room_y_max, room_z_max = room_bound

    # 距离范围
    min_distance, max_distance = distance_range
    z_min_height, z_max_height = height

    # 查询窗帘
    curtain = query_existing_objects_in_room(ue, room_bound, target_types=['curtains'], object_name="窗帘")

    # 生成随机摄像头位置（在半球范围内）
    camera_positions = []
    attempts = 0
    max_attempts = num_cameras * 100000  # 最大尝试次数
    
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
        if not is_in_room:
            continue

        # 检查与已有摄像头的距离
        too_close_to_other_cameras = False
        for existing_camera in camera_positions:
            camera_distance = math.sqrt(
                (camera_x - existing_camera.x)**2 + 
                (camera_y - existing_camera.y)**2 + 
                (camera_z - existing_camera.z)**2
            )
            if camera_distance < min_cameras_distance:
                too_close_to_other_cameras = True
                break
        if too_close_to_other_cameras:
            continue

        # 检查是否与窗帘重叠
        is_in_curtain = False
        for curtain_obj in curtain:
            curtain_aabb = curtain_obj.get_world_aabb()
            curtain_min, curtain_max = fix_aabb_bounds(curtain_aabb)
            if check_position_in_bbox(ts.Vector3(camera_x, camera_y, camera_z), 
                                      curtain_min, curtain_max, safe_margin, False):
                is_in_curtain = True
                break
        if is_in_curtain:
            continue

        camera_pos = ts.Vector3(camera_x, camera_y, camera_z)
        camera_positions.append(camera_pos)
        
        if print_info:
            print(f"[PROCESSING] 摄像头 {len(camera_positions)}: ({camera_x:.2f}, {camera_y:.2f}, {camera_z:.2f})")
            print(f"[PROCESSING] 距离目标: {distance:.2f}, 角度: ({math.degrees(theta):.1f}°, {math.degrees(phi):.1f}°)")
    
    if len(camera_positions) < num_cameras:
        print(f"[WARNING] 只成功生成了 {len(camera_positions)}/{num_cameras} 个摄像头位置")
    
    return camera_positions

# 生成摄像头
def add_capture_camera(ue, camera_positions, target_position, camera_name_prefix="Camera", print_info=False):
    """
    为每个摄像头位置创建摄像头，并使其看向目标对象
    
    Args:
        ue: TongSim实例
        camera_positions: 摄像头位置列表 [ts.Vector3, ...]
        target_position: 目标对象位置
        camera_name_prefix: 摄像头名称前缀
    
    Returns:
        dict: 创建的摄像头对象字典 {name: camera_obj}
    """
    cameras = {}  # 改为字典
    
    for i, camera_position in enumerate(camera_positions):
        # 生成唯一的摄像头名称
        camera_name = f"{camera_name_prefix}_{i+1}"
        
        # 计算摄像头朝向目标的旋转
        camera_quat = look_at_rotation(camera_position, target_position)
        
        try:
            # 创建摄像头
            camera = ue.spawn_camera(
                camera_name=camera_name,
                loc=camera_position,
                quat=camera_quat,
            )
            camera.set_intrinsic_params(90.0, 1024, 1024)
            camera.start_imagedata_streaming(depth=True, segmentation=True)
            # 将摄像头添加到字典中，使用名称作为键
            cameras[camera_name] = camera
            if print_info:
                print(f"[PROCESSING] 已创建摄像头 {camera_name} 在位置 {camera_position}")
    
        except Exception as e:
            print(f"[ERROR] 创建摄像头 {camera_name} 失败: {e}")
            continue
    
    return cameras

# # 视频生成线程
# def gen_video(img_dir, cameras, is_running):
#     time.sleep(1) 
#     video_writers = {}
#     frame_sizes = {}
#     fps = 3
#     fourcc = cv2.VideoWriter_fourcc(*'mp4v')

#     # 初始化视频路径
#     video_paths = {}
#     pic_paths = {}

#     # 构建路径字典
#     for name, cam in cameras.items():
#         video_paths[name] = os.path.join(img_dir, f"{name}.mp4")
#         pic_paths[f"{name}_depth"] = os.path.join(img_dir, f"{name}_depth")
#         pic_paths[f"{name}_segmentation"] = os.path.join(img_dir, f"{name}_segmentation")

#     # 创建目录
#     for path in pic_paths.values():
#         os.makedirs(path, exist_ok=True)
        
#     # 开始采集
#     ind = 0
#     while is_running[0]:  # 使用列表来传递可变的状态
#         for name, cam in cameras.items():
#             try:
#                 # 检查摄像头是否有效
#                 if cam is None:
#                     print(f"Warning: Camera {name} is None")
#                     continue

#                 all_image_data = cam.fetch_image_data_from_streaming()
                
#                 # 检查图像数据是否有效
#                 if all_image_data is None or all_image_data.rgb is None:
#                     print(f"Warning: No image data from {name} at frame {ind}")
#                     continue

#                 rgb_buffer = all_image_data.rgb.tobytes()
#                 np_arr = np.frombuffer(rgb_buffer, dtype=np.uint8)
#                 img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
#                 if img is None:
#                     print(f"Warning: failed to decode frame {ind} from {name}")
#                     continue
                
#                 if name not in frame_sizes:
#                     h, w, _ = img.shape
#                     frame_sizes[name] = (w, h)
#                     video_writers[name] = cv2.VideoWriter(
#                         video_paths[name], fourcc, fps, (w, h)
#                     )
#                 video_writers[name].write(img)

#                 # Depth & segmentation
#                 segmentation_buffer = cam.fetch_segmentation_from_streaming()
#                 seg = segmentation_buffer.tobytes()
#                 depth_buffer = cam.fetch_depth_from_streaming()
#                 depth = depth_buffer.tobytes() 
#                 # 保存分割图像
#                 seg_path = os.path.join(pic_paths[f"{name}_segmentation"], f'{ind:06d}_seg.png')
#                 with open(seg_path, 'wb') as f:
#                     f.write(seg) 
                
#                 # 保存深度图像
#                 depth_path = os.path.join(pic_paths[f"{name}_depth"], f'{ind:06d}_depth.hdr')
#                 with open(depth_path, 'wb') as f:
#                     f.write(depth) 
#             except Exception as e:
#                 print(f"Error processing {name}: {e}")
#                 continue
#         ind += 1
#         time.sleep(0.333)
#     # 释放所有视频写入器
#     for writer in video_writers.values():
#         writer.release()
#     print(f"[INFO] 视频录制完成，共录制 {ind} 帧")

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

# 输出房间内所有物品的边界框
def get_room_objects_bbox(ue, room_bound):
    """
    输出房间内所有物品的边界框
    
    Args:
        ue: TongSim实例
        room_bound: 房间边界
    
    Returns:
        list: 房间内所有物品的边界框列表 [{'min': Vector3, 'max': Vector3}, ...]
    """
    x_min, y_min, _, x_max, y_max, _ = room_bound
    
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
    room_objects_bbox = []
    
    # 遍历所有物体
    for obj_id, obj_data in result.items():
        # 跳过元数据和其他非物体条目
        if obj_id == '__meta__' or 'object_type' not in obj_data:
            continue

        entity = ue.entity_from_id(ts.BaseObjectEntity, entity_id=str(obj_id))

        if entity:
            entity_aabb = entity.get_world_aabb()
            entity_min, entity_max = fix_aabb_bounds(entity_aabb)
            if (entity_min.x >= x_min and entity_max.x <= x_max and entity_min.y >= y_min and entity_max.y <= y_max):
                # 物体在房间边界内，添加到列表
                room_objects_bbox.append({
                    'min': entity_min,
                    'max': entity_max
                })
    
    return room_objects_bbox

# 根据类型文件筛选物品列表
def filter_objects_by_type(objects_list, type_file_path, print_info=False):
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
        print(f"[ERROR] 类型文件 {type_file_path} 不存在")
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
            if print_info == True:
                print(f"[PROCESSING] 匹配成功: {obj_id} -> 基础ID: {base_id}")
        else:
            if print_info == True:
                print(f"[PROCESSING] 不匹配: {obj_id} -> 基础ID: {base_id}")
    
    print(f"\n[PROCESSING] 筛选结果: 共 {len(objects_list)} 个物品, 其中 {len(matched_objects)} 个匹配指定类型")
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


# 掉落物品地点
def drop_object_position(ue, room_bound, room_object_bbox, safe_margin=80.0):
    """
    计算掉落物品的地点，避开墙壁
    
    Args:
        room_bound: 房间边界bbox信息
        room_object_bbox: 房间内已有物品的边界框列表
        safe_margin: 安全边距，单位厘米，默认20厘米
    
    Returns:
        掉落物品的随机位置 (ts.Vector3)
    """
    x_min, y_min, z_min, x_max, y_max, z_max = room_bound
    
    # 计算安全范围
    safe_x_min = x_min + safe_margin
    safe_x_max = x_max - safe_margin
    safe_y_min = y_min + safe_margin
    safe_y_max = y_max - safe_margin
    
    # 确保安全范围有效
    if safe_x_min >= safe_x_max or safe_y_min >= safe_y_max:
        raise ValueError("房间太小，无法应用安全边距")
    
    max_attempts = 100000  # 最大尝试次数
    for attempt in range(max_attempts):
        # 随机生成位置
        drop_x = random.uniform(safe_x_min, safe_x_max)
        drop_y = random.uniform(safe_y_min, safe_y_max)
        drop_z = z_min + 1.0  # 假设地面高度为z_min，加1厘米以避免与地面重叠

        is_inbox = False
        # 检查掉落点是否在任何物体的边界框内
        for obj_bbox in room_object_bbox:
            obj_min = obj_bbox['min']
            obj_max = obj_bbox['max']
            # 检查掉落点是否在物体的边界框内
            if check_position_in_bbox(ts.Vector3(drop_x, drop_y, drop_z), obj_min, obj_max, safe_margin=10.0, check_z_axis=False):
                is_inbox = True
                break   

        if is_inbox:
            # 如果在物体边界框内，重新计算位置
            drop_object_position = ts.Vector3(drop_x, drop_y, drop_z)
            continue
        else:
            drop_object_position = ts.Vector3(drop_x, drop_y, drop_z)
            break   
    return drop_object_position   

# 设置人物出发点以及人物终点
def set_agent_start_end(ue, room_bound, room_object_bbox, drop_position, plan_angle = None, min_distance=300, max_distance=500, safe_margin=50.0):
    """
    设置人物出发点以及人物终点
    
    Args:
        ue: TongSim实例
        room_bound: 房间边界bbox信息
        room_object_bbox: 房间内已有物品的边界框列表
        plan_angle: 路径角度（弧度制）
        min_distance: 最小距离，单位厘米
        max_distance: 最大距离，单位厘米
        drop_position: 掉落物品的位置 (ts.Vector3)
        safe_margin: 安全边距，单位厘米，默认50厘米
    
    Returns:
        tuple: (start_position, end_position) - 人物的起始位置和目标位置
    """
    x_min, y_min, z_min, x_max, y_max, z_max = room_bound

    def generate_valid_position(drop_pos, distance, angle):
        """生成有效的位置"""
        x_offset = distance * math.cos(angle)
        y_offset = distance * math.sin(angle)
        
        candidate_x = drop_pos.x + x_offset
        candidate_y = drop_pos.y + y_offset
        candidate_z = z_min + 1.0  # 默认高度设为1米（100厘米）
        
        return ts.Vector3(candidate_x, candidate_y, candidate_z)
    
    start_position = None
    end_position = None
    max_attempts = 100000  # 最大尝试次数
    # 生成起始位置和目标位置（在一条直线上）
    for attempt in range(max_attempts):
        # 随机选择角度（确定直线的方向）
        start_angle = random.uniform(0, 2 * math.pi)

        # 确定目标角度
        if plan_angle is None:
            # 随机角度：在0到2π之间随机选择
            end_angle = random.uniform(0, 2 * math.pi)
        else:
            # 使用指定的角度差
            end_angle = start_angle + plan_angle
        
        # 确保角度在0-2π范围内
        end_angle = end_angle % (2 * math.pi)

        # 随机选择起始距离和目标距离
        start_distance = random.uniform(min_distance, max_distance)
        end_distance = random.uniform(min_distance, max_distance)

        
        # 生成候选起始位置和目标位置
        candidate_start = generate_valid_position(drop_position, start_distance, start_angle)
        candidate_end = generate_valid_position(drop_position, end_distance, end_angle)
        
        # 检查两个位置是否都在房间边界内
        start_in_room = check_position_in_bbox(candidate_start, 
                                              ts.Vector3(x_min, y_min, z_min), 
                                              ts.Vector3(x_max, y_max, z_max), 
                                              -safe_margin, False)
        
        end_in_room = check_position_in_bbox(candidate_end, 
                                            ts.Vector3(x_min, y_min, z_min), 
                                            ts.Vector3(x_max, y_max, z_max), 
                                            -safe_margin, False)
        
        is_in_object = False
        for obj_bbox in room_object_bbox:
            obj_min = obj_bbox['min']
            obj_max = obj_bbox['max']
            if check_position_in_bbox(candidate_start, obj_min, obj_max, safe_margin=0.0, check_z_axis=False) or \
               check_position_in_bbox(candidate_end, obj_min, obj_max, safe_margin=0.0, check_z_axis=False):
                is_in_object = True
                break   
        if is_in_object:
            continue

        if start_in_room and end_in_room:
            start_position = candidate_start
            end_position = candidate_end
            break

    return start_position, end_position

# 随机在人物出发点放置物品并且生成人物，并拾起物品
def place_object_near_agent(ue, start_position, hand=ts.RIGHT_HAND):
    """
    随机在人物出发点放置物品并且生成人物，并拾起物品
    
    Args:
        ue: TongSim实例
        start_position: 人物的起始位置 (ts.Vector3)
    
    Returns:
        放置的物品实体 (BaseObjectEntity) 或 None
    """

    # 读取物品文件
    def read_item_file(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            print(f"[ERROR] 文件 {filename} 不存在")
            return []
    
    # 物品蓝图定义
    item_blueprints = {
        'cup': read_item_file("./ownership/object/mycup.txt"),
        'book': read_item_file("./ownership/object/mybook.txt"),
        'pen': read_item_file("./ownership/object/mypen.txt"),
        'food': read_item_file("./ownership/object/myfood.txt"),
        'toy': read_item_file("./ownership/object/mytoy.txt"),
        'phone': ["BP_Phone"]
    }

    # 人物与物品的对应关系表
    agent_item_mapping = {
        'girl': ['book', 'toy'],
        'boy': ['book', 'toy'],
        'woman': ['computer', 'phone', 'glasses'],
        'man': ['computer', 'phone', 'glasses'],
        'grandpa': ['book', 'glasses']
    }
    # 通用物品（所有人都可能拥有）
    common_items = ['cup', 'food', 'pen']

    # 人物蓝图映射表
    blueprint_mapping = {
        'girl': ["SDBP_Aich_AIBabyV7_Shoes", "SDBP_Aich_AIBaby_Lele_Shoes"],
        'boy': ["SDBP_Aich_AIBaby_Tiantian_90"],
        'woman': ["SDBP_Aich_Liyuxia"],
        'grandpa': ["SDBP_Aich_Yeye"],
        'man': ["SDBP_Aich_Zhanghaoran"]
    }
    # 过滤掉空的蓝图列表
    available_categories = {cat: blueprints for cat, blueprints in item_blueprints.items() if blueprints}
    
    if not available_categories:
        print("[ERROR] 没有可用的物品蓝图")
        return None
    
    # 随机选择物品类别
    category = random.choice(list(available_categories.keys()))
    # 从选定的类别中随机选择具体蓝图
    blueprint_list = available_categories[category]
    blueprint = random.choice(blueprint_list)

    try:
        # 生成物品
        item_obj = ue.spawn_entity(
            entity_type=ts.BaseObjectEntity,
            blueprint=blueprint,
            location=start_position,
            is_simulating_physics=False,
            scale=None,
            quat=None
        )
        print(f"[INFO] 成功生成物品: {blueprint} (ID: {item_obj.id}) at {start_position}")
    except Exception as e:
        print(f"[ERROR] 生成物品 {blueprint} 失败: {e}")
        return None, None

    # 根据物品类别选择对应的人物类型
    agent_type = None
    for agent, items in agent_item_mapping.items():
        if category in items:
            agent_type = agent
            break
    agent_blueprint = random.choice(blueprint_mapping[agent_type])

    # 获取最近的导航点
    random_position = ue.spatical_manager.get_nearest_nav_position(target_location=start_position)
    random_position.z = random_position.z + 70
    print(f"[INFO] 物品放置位置: {start_position}, 最近导航点: {random_position}")
    try:
        # 生成人物
        agent = ue.spawn_agent(
            blueprint=agent_blueprint,
            location=random_position,
            desired_name=f"{agent_type}_{category}",
            quat=None,
            scale=None
        )
        print(f"[INFO] 成功生成角色: {agent_blueprint} (ID: {agent.id}) at {random_position}")
    except Exception as e:
        print(f"[ERROR] 生成角色 {agent_blueprint} 失败: {e}")
        # 删除已生成的物品
        ue.destroy_entity(item_obj)
        return None, None

    # time1
    agent.do_action(ts.action.MoveToObject(object_id=item_obj.id))

    # time2
    agent.do_action(ts.action.TurnToObject(object_id=item_obj.id))

    # time3
    agent.do_action(ts.action.HandReach(which_hand=hand, target_location=item_obj.get_location()))
    agent.do_action(ts.action.TakeObject(which_hand=hand, object_id=item_obj.id))

    return item_obj, agent


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

    # 根据blueprint_mapping自适应生成人物类型限制
    trait_limits = {}
    for trait, blueprints in blueprint_mapping.items():
        trait_limits[trait] = len(blueprints)

    # 方位映射
    side_mapping = ['front', 'back', 'left', 'right']
    
    # 如果提供了完整的agent_blueprints，则直接使用
    if agent_blueprints is not None:
        # 检查是否有重复的蓝图
        if len(agent_blueprints) != len(set(agent_blueprints)):
            print("[WARNING] agent_blueprints中存在重复的人物蓝图，将使用全随机生成")
            agent_blueprints = None
            agent_traits = None
        else:
            num_agents = len(agent_blueprints)
        
        # 如果提供了agent_sides，检查长度是否匹配
        if agent_sides is not None and len(agent_sides) != num_agents:
            raise ValueError("[ERROR] agent_sides长度必须与agent_blueprints一致")
        
        # 如果提供了agent_is_sit，检查长度是否匹配
        if agent_is_sit is not None and len(agent_is_sit) != num_agents:
            raise ValueError("[ERROR] agent_is_sit长度必须与agent_blueprints一致")

    # 如果提供了agent_traits，检查类型限制
    if agent_traits is not None:
        # 检查人物类型限制
        trait_counts = {}
        for trait in agent_traits:
            trait_counts[trait] = trait_counts.get(trait, 0) + 1
        
        valid = True
        for trait, count in trait_counts.items():
            if trait not in trait_limits:
                print(f"[WARNING] {trait}类型不在支持的列表中")
                valid = False
                break
            if count > trait_limits[trait]:
                print(f"[WARNING] {trait}类型的人物数量({count})超过可用蓝图数量({trait_limits[trait]})")
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
            raise ValueError("[ERROR] agent_traits长度必须与num_agents一致")
        
        agent_blueprints = []
        available_blueprints = {trait: blueprint_mapping[trait].copy() for trait in set(agent_traits)}
        
        for trait in agent_traits:
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
            raise ValueError(f"[ERROR] 可用的蓝图数量({len(available_blueprints)})不足以生成{num_agents}个人物")
        
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
        print("[ERROR] 人物蓝图、方向和坐下状态数量不匹配")
        return []
    
    # 从附近物体中筛选出椅子
    existed_chairs = filter_objects_by_type(objects_list=nearby_objects, type_file_path='./ownership/object/chair.txt')
    if print_info:
        print(f"[INFO] 找到 {len(existed_chairs)} 把现有椅子")
    
    # 获取桌子的世界AABB边界
    table_aabb = table_object.get_world_aabb()
    table_min ,table_max = fix_aabb_bounds(table_aabb)
    
    x_min, y_min, z_min, x_max, y_max, z_max = room_bound
    
    # 预计算附近物体的AABB边界
    nearby_object_bounds = []
    # 过滤出地毯对象
    existed_carpet = filter_objects_by_type(objects_list=nearby_objects, type_file_path='./ownership/object/carpet.txt')
    carpet_ids = {carpet.id for carpet in existed_carpet} if existed_carpet else set()
    for obj in nearby_objects:
        try:
            # 检查是否是地毯，如果是则跳过
            if hasattr(obj, 'id') and obj.id in carpet_ids:
                continue
                
            # 检查字典中是否有 'entity' 键
            if isinstance(obj, dict) and 'entity' in obj:
                entity = obj['entity']
                obj_aabb = entity.get_world_aabb()
                obj_aabb_min ,obj_aabb_max = fix_aabb_bounds(obj_aabb)
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
                nearby_object_bounds.append({
                    'min': obj_aabb_min,
                    'max': obj_aabb_max,
                    'entity': obj,
                    'type': 'unknown'
                })
        except Exception as e:
            print(f"[ERROR] 无法获取物体边界: {e}")
    if  print_info == True:
        print(f"[INFO] 预计算了 {len(nearby_object_bounds)} 个附近物体的边界")
    
    # 计算每个椅子的方向
    chair_sides = [] # 椅子相对于桌子的侧边位置 
    chair_positions = []    # 椅子位置列表
    for chair in existed_chairs:
        try:
            pos = chair.get_location()
            side = determine_object_side(chair, table_object)

            chair_sides.append(side)
            chair_positions.append((pos.x, pos.y, pos.z))
        except Exception as e:
            print(f"[ERROR] 获取椅子 {chair.id} 信息失败: {e}")
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
                    print(f"[PROCESSING] 人物 {agent_idx} 将坐在椅子 {chair.id} 上 (方向: {side})")
                    
            except Exception as e:
                print(f"[WARNING] 获取椅子 {chair.id} 信息失败: {e}")
                # 如果获取椅子信息失败，将此人物转为站立
                standing_agents.append((agent_idx, blueprint, side))
        else:
            # 没有找到合适的椅子，将此人物转为站立
            if print_info:
                print(f"[PROCESSING] 人物 {agent_idx} 需要坐下但未找到合适椅子，转为站立")
            standing_agents.append((agent_idx, blueprint, side))


    # 处理需要站立的人物（包括未能匹配到椅子的人物）
    for agent_idx, blueprint, side in standing_agents:
        agent_placed = False
        attempts = 0
        max_attempts = 1000000  # 最大尝试次数
        
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
                    (agent_position.x - existing_pos.x)**2 + (agent_position.y - existing_pos.y)**2 + (agent_position.z - existing_pos.z)**2
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
                print(f"[PROCESSING] 人物 {agent_idx} 将站立在位置: {agent_position}, 方向: {side}")
        if not agent_placed:
            print(f"[CONTINUE] {max_attempts} 次尝试后 无法为人物 {agent_idx} 找到合适的位置")
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
            print(f"[CONTINUE] 跳过人物 {i}: 规划失败")
            continue
        
        blueprint = plan['blueprint']
        is_sit = plan['is_sit']
        towards_position = plan['rotation']
        
        try:
            if is_sit:
                # 处理坐下的人物
                chair_id = plan['chair_id']
                if not chair_id:
                    print(f"[WARNING] 人物 {i} 需要坐下但未指定椅子ID")
                    continue
                
                # 通过ID获取椅子实体
                chair = ue.entity_from_id(ts.BaseObjectEntity, entity_id=str(chair_id))
                if not chair:
                    print(f"[WARNING] 人物 {i} 需要坐下但无法找到椅子实体: {chair_id}")
                    continue
                
                # 获取椅子位置
                chair_location = chair.get_location()
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
                            print(f"[CONTINUE] 人物 {i} 坐下失败: error_code={getattr(result, 'error_code', 'unknown')}")
                
                if sit_success: # 坐下成功，执行转向
                    agent.do_action(ts.action.TurnToLocation(loc=towards_position))
                    agents.append(agent)
                    
                    if print_info:
                        print(f"[PROCESSING] 人物 {i} 已生成并成功坐在椅子 {chair_id} 上")

                else: # 坐下失败，改为站立
                    # 获取当前位置
                    current_position = agent.get_location()
                    
                    # 执行站立动作序列
                    agent.do_action(ts.action.MoveToLocation(loc=current_position))
                    agent.do_action(ts.action.TurnToLocation(loc=towards_position))
                    
                    agents.append(agent)
                    
                    if print_info:
                        print(f"[PROCESSING] 人物 {i} 已生成并改为站在位置 {current_position}")

            else:
                # 处理站立的人物
                position = plan['position']
                towards_position = plan['rotation']
                
                if not position:
                    print(f"[WARNING] 人物 {i} 需要站立但未指定位置")
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
                agent.do_action(ts.action.MoveToLocation(loc=position))
                agent.do_action(ts.action.TurnToLocation(loc=towards_position))
                agents.append(agent)
                
                if print_info:
                    print(f"[PROCESSING] 人物 {i} 已生成并安排站在位置 {position}")
                    
        except Exception as e:
            print(f"[ERROR] 生成人物 {i} 时出错: {e}")
            continue
    
    return agents


# 持续移动并掉落物品
def MoveToObject_whileDroping(agent, drop_position, end_position, hand=ts.RIGHT_HAND):

    print("[INFO] 启动持续移动任务...")
    agent.do_action(ts.action.MoveToLocation(loc=drop_position))
    agent.do_action(ts.action.HandRelease(which_hand=hand, target_location=drop_position))
    # print(f"[INFO] object : {object_entity.id}, object position : {object_entity.get_location()}")
    agent.do_action(ts.action.MoveToLocation(loc=end_position))
    
# 持续移动并放下物品
def MoveToObject_whilePutDown(agent, drop_position, end_position, hand=ts.RIGHT_HAND):

    print("[INFO] 启动持续移动任务...")
    agent.do_action(ts.action.MoveToLocation(loc=drop_position))
    agent.do_action(ts.action.PutDownToLocation(which_hand=hand, target_location=drop_position))
    # print(f"[INFO] object : {object_entity.id}, object position : {object_entity.get_location()}")
    agent.do_action(ts.action.MoveToLocation(loc=end_position))

# 倒垃圾
def MoveToObject_whileThrowTrash(agent, target_object, end_position, hand=ts.RIGHT_HAND):

    print("[INFO] 启动持续移动任务...")
    agent.do_action(ts.action.MoveToObject(object_id=target_object.id))
    aabb = target_object.get_world_aabb()
    aabb_min, aabb_max = fix_aabb_bounds(aabb)
    height = aabb_max.z - aabb_min.z
    object_x, object_y, object_z = target_object.get_location().x, target_object.get_location().y, target_object.get_location().z
    target_location = ts.Vector3(object_x, object_y, object_z + height)
    agent.do_action(ts.action.PutDownToLocation(which_hand=hand, target_location=target_location))
    # print(f"[INFO] object : {object_entity.id}, object position : {object_entity.get_location()}")
    agent.do_action(ts.action.MoveToLocation(loc=end_position)) 

# 物品传递
def MoveToObject_whilePass(ue, agents, table_object, start_position1, end_position1, end_position2, hand=ts.RIGHT_HAND):

    aabb = table_object.get_world_aabb()
    aabb_min, aabb_max = fix_aabb_bounds(aabb)
    
    max_attempts = 100000  # 最大尝试次数
    for attempt in range(max_attempts):
        # 随机生成位置
        drop_x = random.uniform(aabb_min.x, aabb_max.x)
        drop_y = random.uniform(aabb_min.y, aabb_max.y)
        drop_z = aabb_max.z + 1.0  # 假设地面高度为z_min，加1厘米以避免与地面重叠
        target_location = ts.Vector3(drop_x, drop_y, drop_z)

        if not check_position_in_bbox(target_location, aabb_min, aabb_max, -40, check_z_axis=False):
            break
        else:
            continue

    # 创建物品
    item_obj = ue.spawn_entity(
        entity_type=ts.BaseObjectEntity,
        blueprint='BP_Fruit_Apple_06',
        location=start_position1,
        is_simulating_physics=True,
        scale=None,
        quat=None
    )
    # 一号人物捡起物品
    agents[0].do_action(ts.action.MoveToLocation(loc=start_position1)) 
    agents[0].do_action(ts.action.TurnToObject(object_id=item_obj.id))
    agents[0].do_action(ts.action.HandReach(which_hand=hand, target_location=item_obj.get_location()))
    agents[0].do_action(ts.action.TakeObject(which_hand=hand, object_id=item_obj.id))

    # 一号人物走向桌子放下物品
    agents[0].do_action(ts.action.MoveToLocation(loc=target_location))
    agents[0].do_action(ts.action.PutDownToLocation(which_hand=hand, target_location=target_location))
    agents[0].do_action(ts.action.MoveToLocation(loc=end_position1)) 

    # 二号人物拿起物品
    agents[1].do_action(ts.action.MoveToLocation(loc=target_location)) 
    agents[1].do_action(ts.action.TurnToObject(object_id=item_obj.id))
    agents[1].do_action(ts.action.HandReach(which_hand=hand, target_location=item_obj.get_location()))
    agents[1].do_action(ts.action.TakeObject(which_hand=hand, object_id=item_obj.id))

    # 离开
    # agents[0].do_action(ts.action.MoveToLocation(loc=end_position1)) 
    agents[1].do_action(ts.action.MoveToLocation(loc=end_position2)) 



# 倒垃圾
def run_pipeline_Put(map_range=None, min_room_area=9.0, Put_object=None, dir = "./ownership/throw_rubbish/"):
    # 读取筛选后的场景列表
    try:
        with open('./ownership/object/selected_scenes.txt', 'r', encoding='utf-8') as f:
            selected_scenes = [line.strip() for line in f if line.strip()]
        print(f"[INFO] 已加载 {len(selected_scenes)} 个筛选场景")
    except FileNotFoundError:
        print("[WARNING] selected_scenes.txt 文件不存在，将处理所有地图")
        selected_scenes = []
    
    # server_ip = '127.0.0.1'
    server_ip = '10.2.168.2'
    with ts.TongSim(
        grpc_endpoint=f"{server_ip}:5056",
        legacy_grpc_endpoint=f"{server_ip}:50052",
    ) as ue:

        # 定义地图范围
        if map_range is None:
            map_range = range(0, 29)

        for map_num in map_range:
            # 格式化地图名称
            map_name = f"SDBP_Map_{map_num:03d}"

            # 打开地图
            print(f"\n[PROCESSING] 正在打开地图: {map_name}")
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
                    
                # print(f"[PROCESSING] 地图 {map_name} 的房间信息: {rooms}")
                
                # 获取房间边界框信息
                room_bbox_dict = get_room_bbox(rooms)
                # print(f"[PROCESSING] 地图 {map_name} 的房间边界bbox信息: {room_bbox_dict}")
                
                # 遍历当前地图的所有房间
                for room_info in rooms:
                    room_name = room_info['room_name']
                    
                    print(f"\n[PROCESSING] 处理地图 {map_name} 的房间: {room_name}")
                    room_bound = get_room_boundary(room_name, room_bbox_dict)

                    # 面积小于4 跳过
                    if get_area(room_bound) < min_room_area:
                        print(f"[CONTINUE] 房间 {room_name} 面积小于 {min_room_area} 平方米，跳过")
                        continue

                    Target_object = query_existing_objects_in_room(
                        ue=ue,
                        room_bound=room_bound,
                        target_types=Put_object,
                        print_info=True
                    )

                    if not Target_object:
                        print(f"[CONTINUE] 房间 {room_name} 内没有找到垃圾桶，跳过")
                        continue    

                    drop_object_position = Target_object[0].get_location()
                    print(f"[INFO] 垃圾桶位置: ({drop_object_position.x:.2f}, {drop_object_position.y:.2f}, {drop_object_position.z:.2f})")

                    room_objects_bbox = get_room_objects_bbox(ue, room_bound)
                    # 设置人物起始位置和目标位置
                    start_position, end_position = set_agent_start_end(ue, room_bound, room_objects_bbox, drop_object_position, plan_angle=None,
                                                                      min_distance=200, max_distance=300, safe_margin=50.0)

                    if start_position is None or end_position is None:
                        print(f"[CONTINUE] 无法为房间 {room_name} 生成有效的人物起始位置和目标位置，跳过")
                        continue
                    print(f"[INFO] 人物起始位置: ({start_position.x:.2f}, {start_position.y:.2f}, {start_position.z:.2f})")
                    print(f"[INFO] 人物目标位置: ({end_position.x:.2f}, {end_position.y:.2f}, {end_position.z:.2f})")

                    # 放置物品并生成角色
                    item_obj, agent = place_object_near_agent(ue, start_position, hand=ts.RIGHT_HAND)
                    if item_obj is None or agent is None:
                        print(f"[CONTINUE] 无法在房间 {room_name} 放置物品或生成角色，跳过")
                        continue

                    ue.change_view_mode(ViewModeType.THIRD_PERSON_VIEW)
                    # MoveToObject_whileThrowTrash(agent, Target_object[0], end_position, hand=ts.RIGHT_HAND)

                    def add_capture_camera(name, corner):
                        target = drop_object_position
                        quat = look_at_rotation(corner, target)
                        camera = ue.spawn_camera(
                            name, corner, quat
                        )
                        camera.set_intrinsic_params(90, 1024, 1024)
                        # 设置更高的图像流更新频率
                        camera.start_imagedata_streaming(depth=True, segmentation=True)
                        print(f"Camera {name} initialized with streaming")
                        return camera
                    cx, cy, cz = drop_object_position.x, drop_object_position.y, drop_object_position.z
                    w2 = 200
                    h2 = 200
                    corners = [
                        ts.Vector3(cx - w2, cy - h2, 160),  # 左下
                        ts.Vector3(cx + w2, cy - h2, 160),  # 右下
                        ts.Vector3(cx + w2, cy + h2, 160),  # 右上
                        ts.Vector3(cx - w2, cy + h2, 160),  # 左上
                    ]
                    print(corners)

                    cameras = {}
                    for i, corner in enumerate(corners):
                        cameras[f"camera_{i}"] = add_capture_camera(f"camera_{i}_{drop_object_position}", corner)

                    # *******************************************************
                    is_running = False

                    def gen_video(img_dir):
                        time.sleep(1) 
                        video_writers = {}
                        frame_sizes = {}
                        fps = 30  # 提高帧率到30fps，使视频更流畅
                        fourcc = cv2.VideoWriter_fourcc(*'mp4v')

                        # 初始化视频路径
                        video_paths = {
                            name: os.path.join(img_dir, f"{name}.mp4") for name in cameras
                        } 
                        pic_paths = {
                            f"{name}_depth": os.path.join(img_dir, name)
                            for name in cameras
                        } | {
                            f"{name}_segmentation": os.path.join(img_dir, name)
                            for name in cameras
                        }
                        for name, path in pic_paths.items():
                            os.makedirs(path, exist_ok=True)

                        # 开始采集
                        ind = 0
                        while is_running:
                            for name, cam in cameras.items():
                                try:
                                    all_image_data = cam.fetch_image_data_from_streaming()
                                    rgb_buffer = all_image_data.rgb.tobytes()
                                    np_arr = np.frombuffer(rgb_buffer, dtype=np.uint8)
                                    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

                                    if img is None:
                                        print(f"Warning: failed to decode frame {ind} from {name}")
                                        continue
                                    
                                    if name not in frame_sizes:
                                        h, w, _ = img.shape
                                        frame_sizes[name] = (w, h)
                                        video_writers[name] = cv2.VideoWriter(
                                            video_paths[name], fourcc, fps, (w, h)
                                        )

                                    video_writers[name].write(img)
                                    

                                    # Depth & segmentation
                                    name_source = name

                                    segmentation_buffer = cam.fetch_segmentation_from_streaming()
                                    seg = segmentation_buffer.tobytes()

                                    depth_buffer = cam.fetch_depth_from_streaming()
                                    depth = depth_buffer.tobytes() 

                                    name = name_source + "_segmentation"
                                    seg_path = os.path.join(pic_paths[name], '%06d_seg.png'%ind)
                                    with open(seg_path, 'wb') as f:
                                        f.write(seg) 
                                    
                                    name = name_source + "_depth"
                                    depth_path = os.path.join(pic_paths[name], '%06d_depth.hdr'%ind)
                                    with open(depth_path, 'wb') as f:
                                        f.write(depth) 

                                except Exception as e:
                                    print(f"Error processing {name}: {e}")
                                    continue

                            ind += 1
                            time.sleep(0.03)  # 减少休眠时间到30ms，大约对应30fps

                        for writer in video_writers.values():
                            writer.release()

                    # *******************************************************

                    save_dir_name = f"table_scene_map{map_num:03d}_room_{room_name}"
                    save_dir = os.path.join(dir, save_dir_name)
                    try:
                        is_running = True

                        th = threading.Thread(target=gen_video, args=(save_dir,))  
                        th.start()

                        MoveToObject_whileThrowTrash(agent, Target_object[0], end_position, hand=ts.RIGHT_HAND)

                        is_running = False
                        th.join()  
                    
                    except Exception as e:
                        print(f"Error occurred: {e}")
                        is_running = False
                        th.join()  

                    ue.destroy_entity(agent.id)

            except Exception as e:
                print(f"[ERROR] 处理地图 {map_name} 时发生错误: {str(e)}")
                continue

# 掉落物品
def run_pipline_dropping(map_range=None, min_room_area=9.0, dir = "./ownership/drop/"):
    # 读取筛选后的场景列表
    try:
        with open('./ownership/object/selected_scenes.txt', 'r', encoding='utf-8') as f:
            selected_scenes = [line.strip() for line in f if line.strip()]
        print(f"[INFO] 已加载 {len(selected_scenes)} 个筛选场景")
    except FileNotFoundError:
        print("[WARNING] selected_scenes.txt 文件不存在，将处理所有地图")
        selected_scenes = []
    # server_ip = '127.0.0.1'
    server_ip = '10.2.168.2'
    with ts.TongSim(
        grpc_endpoint=f"{server_ip}:5056",
        legacy_grpc_endpoint=f"{server_ip}:50052",
    ) as ue:

        # 定义地图范围
        if map_range is None:
            map_range = range(0, 29)

        for map_num in map_range:
            # 格式化地图名称
            map_name = f"SDBP_Map_{map_num:03d}"

            # 打开地图
            print(f"\n[PROCESSING] 正在打开地图: {map_name}")
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
                    
                # print(f"[PROCESSING] 地图 {map_name} 的房间信息: {rooms}")
                
                # 获取房间边界框信息
                room_bbox_dict = get_room_bbox(rooms)
                # print(f"[PROCESSING] 地图 {map_name} 的房间边界bbox信息: {room_bbox_dict}")
                
                # 遍历当前地图的所有房间
                for room_info in rooms:
                    # room_name = room_info['room_name'
                    room_name = 'livingRoom'
                    
                    print(f"\n[PROCESSING] 处理地图 {map_name} 的房间: {room_name}")
                    room_bound = get_room_boundary(room_name, room_bbox_dict)

                    # 面积小于4 跳过
                    if get_area(room_bound) < min_room_area:
                        print(f"[CONTINUE] 房间 {room_name} 面积小于 {min_room_area} 平方米，跳过")
                        continue

                    room_objects_bbox = get_room_objects_bbox(ue, room_bound)
                    # 生成掉落位置
                    drop_position = drop_object_position(ue, room_bound, room_objects_bbox, safe_margin=100.0)
                    print(f"[INFO] 掉落位置: ({drop_position.x:.2f}, {drop_position.y:.2f}, {drop_position.z:.2f})")

                    # 设置人物起始位置和目标位置
                    start_position, end_position = set_agent_start_end(ue, room_bound, room_objects_bbox, drop_position, plan_angle=math.pi,
                                                                      min_distance=200, max_distance=300, safe_margin=50.0)
                    
                    if start_position is None or end_position is None:
                        print(f"[CONTINUE] 无法为房间 {room_name} 生成有效的人物起始位置和目标位置，跳过")
                        continue
                    print(f"[INFO] 人物起始位置: ({start_position.x:.2f}, {start_position.y:.2f}, {start_position.z:.2f})")
                    print(f"[INFO] 人物目标位置: ({end_position.x:.2f}, {end_position.y:.2f}, {end_position.z:.2f})")

                    # 放置物品并生成角色
                    item_obj, agent = place_object_near_agent(ue, start_position, hand=ts.RIGHT_HAND)
                    if item_obj is None or agent is None:
                        print(f"[CONTINUE] 无法在房间 {room_name} 放置物品或生成角色，跳过")
                        continue
                    ue.change_view_mode(ViewModeType.THIRD_PERSON_VIEW)

                    def add_capture_camera(name, corner):
                        target = drop_position
                        quat = look_at_rotation(corner, target)
                        camera = ue.spawn_camera(
                            name, corner, quat
                        )
                        camera.set_intrinsic_params(90, 1024, 1024)
                        # 设置更高的图像流更新频率
                        camera.start_imagedata_streaming(depth=True, segmentation=True)
                        print(f"Camera {name} initialized with streaming")
                        return camera
                    cx, cy, cz = drop_position.x, drop_position.y, drop_position.z
                    w2 = 200
                    h2 = 200
                    corners = [
                        ts.Vector3(cx - w2, cy - h2, 160),  # 左下
                        ts.Vector3(cx + w2, cy - h2, 160),  # 右下
                        ts.Vector3(cx + w2, cy + h2, 160),  # 右上
                        ts.Vector3(cx - w2, cy + h2, 160),  # 左上
                    ]
                    print(corners)

                    cameras = {}
                    for i, corner in enumerate(corners):
                        cameras[f"camera_{i}"] = add_capture_camera(f"camera_{i}_{drop_position}", corner)

                    # *******************************************************
                    is_running = False

                    def gen_video(img_dir):
                        time.sleep(1) 
                        video_writers = {}
                        frame_sizes = {}
                        fps = 30  # 提高帧率到30fps，使视频更流畅
                        fourcc = cv2.VideoWriter_fourcc(*'mp4v')

                        # 初始化视频路径
                        video_paths = {
                            name: os.path.join(img_dir, f"{name}.mp4") for name in cameras
                        } 
                        pic_paths = {
                            f"{name}_depth": os.path.join(img_dir, name)
                            for name in cameras
                        } | {
                            f"{name}_segmentation": os.path.join(img_dir, name)
                            for name in cameras
                        }
                        for name, path in pic_paths.items():
                            os.makedirs(path, exist_ok=True)

                        # 开始采集
                        ind = 0
                        while is_running:
                            for name, cam in cameras.items():
                                try:
                                    all_image_data = cam.fetch_image_data_from_streaming()
                                    rgb_buffer = all_image_data.rgb.tobytes()
                                    np_arr = np.frombuffer(rgb_buffer, dtype=np.uint8)
                                    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

                                    if img is None:
                                        print(f"Warning: failed to decode frame {ind} from {name}")
                                        continue
                                    
                                    if name not in frame_sizes:
                                        h, w, _ = img.shape
                                        frame_sizes[name] = (w, h)
                                        video_writers[name] = cv2.VideoWriter(
                                            video_paths[name], fourcc, fps, (w, h)
                                        )

                                    video_writers[name].write(img)
                                    

                                    # Depth & segmentation
                                    name_source = name

                                    segmentation_buffer = cam.fetch_segmentation_from_streaming()
                                    seg = segmentation_buffer.tobytes()

                                    depth_buffer = cam.fetch_depth_from_streaming()
                                    depth = depth_buffer.tobytes() 

                                    name = name_source + "_segmentation"
                                    seg_path = os.path.join(pic_paths[name], '%06d_seg.png'%ind)
                                    with open(seg_path, 'wb') as f:
                                        f.write(seg) 
                                    
                                    name = name_source + "_depth"
                                    depth_path = os.path.join(pic_paths[name], '%06d_depth.hdr'%ind)
                                    with open(depth_path, 'wb') as f:
                                        f.write(depth) 

                                except Exception as e:
                                    print(f"Error processing {name}: {e}")
                                    continue

                            ind += 1
                            time.sleep(0.03)  # 减少休眠时间到30ms，大约对应30fps

                        for writer in video_writers.values():
                            writer.release()

                    # *******************************************************

                    save_dir_name = f"table_scene_map{map_num:03d}_room_{room_name}"
                    save_dir = os.path.join(dir, save_dir_name)
                    try:
                        is_running = True

                        th = threading.Thread(target=gen_video, args=(save_dir,))  
                        th.start()

                            
                        # MoveToObject_whileDroping(agent, drop_position, end_position, hand=ts.RIGHT_HAND)
                        MoveToObject_whilePutDown(agent, drop_position, end_position, hand=ts.RIGHT_HAND)

                        is_running = False
                        th.join()  
                    
                    except Exception as e:
                        print(f"Error occurred: {e}")
                        is_running = False
                        th.join()  

                    ue.destroy_entity(agent.id)


            except Exception as e:
                print(f"[ERROR] 处理地图 {map_name} 时发生错误: {str(e)}")
                continue

# 传递物品
def run_pipeline_Passing(map_range=None, min_room_area=9.0, dir = "./ownership/passing/"):
    # 读取筛选后的场景列表
    try:
        with open('./ownership/object/selected_scenes.txt', 'r', encoding='utf-8') as f:
            selected_scenes = [line.strip() for line in f if line.strip()]
        print(f"[INFO] 已加载 {len(selected_scenes)} 个筛选场景")
    except FileNotFoundError:
        print("[WARNING] selected_scenes.txt 文件不存在，将处理所有地图")
        selected_scenes = []
    
    # server_ip = '127.0.0.1'
    server_ip = '10.2.168.2'
    with ts.TongSim(
        grpc_endpoint=f"{server_ip}:5056",
        legacy_grpc_endpoint=f"{server_ip}:50052",
    ) as ue:

        # 定义地图范围
        if map_range is None:
            map_range = range(0, 29)

        for map_num in map_range:
            # 格式化地图名称
            map_name = f"SDBP_Map_{map_num:03d}"

            # 打开地图
            print(f"\n[PROCESSING] 正在打开地图: {map_name}")
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
                    
                # print(f"[PROCESSING] 地图 {map_name} 的房间信息: {rooms}")
                
                # 获取房间边界框信息
                room_bbox_dict = get_room_bbox(rooms)
                # print(f"[PROCESSING] 地图 {map_name} 的房间边界bbox信息: {room_bbox_dict}")
                
                # 遍历当前地图的所有房间
                for room_info in rooms:
                    room_name = room_info['room_name']
                    
                    print(f"\n[PROCESSING] 处理地图 {map_name} 的房间: {room_name}")
                    room_bound = get_room_boundary(room_name, room_bbox_dict)

                    # 面积小于4 跳过
                    if get_area(room_bound) < min_room_area:
                        print(f"[CONTINUE] 房间 {room_name} 面积小于 {min_room_area} 平方米，跳过")
                        continue

                    Table_object = query_existing_objects_in_room(
                        ue=ue,
                        room_bound=room_bound,
                        target_types=['coffeetable', 'diningTable', 'table', 'Table'],
                        print_info=True
                    )
                    if not Table_object:
                        print(f"[CONTINUE] 房间 {room_name} 内没有找到合适的桌子，跳过")
                        continue

                    room_objects_bbox = get_room_objects_bbox(ue, room_bound)
                    table_position = Table_object[0].get_location()

                    on_table_items, nearby_items  = find_objects_near_table(
                        ue=ue,
                        table_object=Table_object[0],
                        search_distance=160.0
                    )

                    # 在桌子周围生成人物
                    agent_blueprints, agent_sides, agent_is_sit = generate_agent_configuration(
                        sit_probability=0,  # 概率坐下
                        agent_traits=['boy', 'girl'],
                        num_agents=2,
                        agent_sides=["front", "back"]
                    )
                    agent_plans = plan_agents_around_table(
                        ue=ue,
                        table_object=Table_object[0],
                        room_bound=room_bound,
                        agent_blueprints=agent_blueprints,
                        agent_sides=agent_sides,
                        agent_is_sit=agent_is_sit,
                        nearby_objects=nearby_items,
                        min_distance=30,
                        max_distance=100,
                        print_info=False
                    )
                    agents = execute_agent_plans(
                        ue=ue,
                        agent_plans=agent_plans,
                        print_info=False
                    )

                    # 计算成功的规划数量（status不为'failed'的数量）
                    successful_plans = [plan for plan in agent_plans if plan.get('status') != 'failed']
                    successful_count = len(successful_plans)
                    # 检查条件：成功的规划数量必须>=2，且总长度也必须>=2
                    agent_num = 2
                    if successful_count < agent_num or len(agent_plans) < agent_num:
                        print(f"[CONTINUE] 未能规划出{agent_num}人物位置，结束。成功规划: {successful_count}, 总规划: {len(agent_plans)}")
                        continue
                    
                    drop_object_position = Table_object[0].get_location()
                    print(f"[INFO] 桌子位置: ({drop_object_position.x:.2f}, {drop_object_position.y:.2f}, {drop_object_position.z:.2f})")

                    # 设置人物起始位置和目标位置
                    start_position1, end_position1 = set_agent_start_end(ue, room_bound, room_objects_bbox, drop_object_position, plan_angle=None,
                                                                      min_distance=200, max_distance=500, safe_margin=50.0)

                    if start_position1 is None or end_position1 is None:
                        print(f"[CONTINUE] 无法为房间 {room_name} 生成有效的人物起始位置和目标位置，跳过")
                        continue
                    print(f"[INFO] 人物起始位置: ({start_position1.x:.2f}, {start_position1.y:.2f}, {start_position1.z:.2f})")
                    print(f"[INFO] 人物目标位置: ({end_position1.x:.2f}, {end_position1.y:.2f}, {end_position1.z:.2f})")

                    # 设置人物起始位置和目标位置
                    start_position2, end_position2 = set_agent_start_end(ue, room_bound, room_objects_bbox, drop_object_position, plan_angle=None,
                                                                      min_distance=200, max_distance=500, safe_margin=50.0)

                    if start_position2 is None or end_position2 is None:
                        print(f"[CONTINUE] 无法为房间 {room_name} 生成有效的人物起始位置和目标位置，跳过")
                        continue
                    print(f"[INFO] 人物起始位置: ({start_position2.x:.2f}, {start_position2.y:.2f}, {start_position2.z:.2f})")
                    print(f"[INFO] 人物目标位置: ({end_position2.x:.2f}, {end_position2.y:.2f}, {end_position2.z:.2f})")


                    # ue.change_view_mode(ViewModeType.THIRD_PERSON_VIEW)
                    ue.change_view_mode(ViewModeType.SURVEILLANCE_VIEW)
                    # MoveToObject_whilePass(ue, agents, Table_object[0], start_position1, end_position1, end_position2)

                    
                    def add_capture_camera(name, corner):
                        target = drop_object_position
                        quat = look_at_rotation(corner, target)
                        camera = ue.spawn_camera(
                            name, corner, quat
                        )
                        camera.set_intrinsic_params(90, 1024, 1024)
                        # 设置更高的图像流更新频率
                        camera.start_imagedata_streaming(depth=True, segmentation=True)
                        print(f"Camera {name} initialized with streaming")
                        return camera
                    cx, cy, cz = drop_object_position.x, drop_object_position.y, drop_object_position.z
                    w2 = 200
                    h2 = 200
                    corners = [
                        ts.Vector3(cx - w2, cy - h2, 160),  # 左下
                        ts.Vector3(cx + w2, cy - h2, 160),  # 右下
                        ts.Vector3(cx + w2, cy + h2, 160),  # 右上
                        ts.Vector3(cx - w2, cy + h2, 160),  # 左上
                    ]
                    print(corners)

                    cameras = {}
                    for i, corner in enumerate(corners):
                        cameras[f"camera_{i}"] = add_capture_camera(f"camera_{i}_{drop_object_position}", corner)

                    # *******************************************************
                    is_running = False

                    def gen_video(img_dir):
                        time.sleep(1) 
                        video_writers = {}
                        frame_sizes = {}
                        fps = 30  # 提高帧率到30fps，使视频更流畅
                        fourcc = cv2.VideoWriter_fourcc(*'mp4v')

                        # 初始化视频路径
                        video_paths = {
                            name: os.path.join(img_dir, f"{name}.mp4") for name in cameras
                        } 
                        pic_paths = {
                            f"{name}_depth": os.path.join(img_dir, name)
                            for name in cameras
                        } | {
                            f"{name}_segmentation": os.path.join(img_dir, name)
                            for name in cameras
                        }
                        for name, path in pic_paths.items():
                            os.makedirs(path, exist_ok=True)

                        # 开始采集
                        ind = 0
                        while is_running:
                            for name, cam in cameras.items():
                                try:
                                    all_image_data = cam.fetch_image_data_from_streaming()
                                    rgb_buffer = all_image_data.rgb.tobytes()
                                    np_arr = np.frombuffer(rgb_buffer, dtype=np.uint8)
                                    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

                                    if img is None:
                                        print(f"Warning: failed to decode frame {ind} from {name}")
                                        continue
                                    
                                    if name not in frame_sizes:
                                        h, w, _ = img.shape
                                        frame_sizes[name] = (w, h)
                                        video_writers[name] = cv2.VideoWriter(
                                            video_paths[name], fourcc, fps, (w, h)
                                        )

                                    video_writers[name].write(img)
                                    

                                    # Depth & segmentation
                                    name_source = name

                                    segmentation_buffer = cam.fetch_segmentation_from_streaming()
                                    seg = segmentation_buffer.tobytes()

                                    depth_buffer = cam.fetch_depth_from_streaming()
                                    depth = depth_buffer.tobytes() 

                                    name = name_source + "_segmentation"
                                    seg_path = os.path.join(pic_paths[name], '%06d_seg.png'%ind)
                                    with open(seg_path, 'wb') as f:
                                        f.write(seg) 
                                    
                                    name = name_source + "_depth"
                                    depth_path = os.path.join(pic_paths[name], '%06d_depth.hdr'%ind)
                                    with open(depth_path, 'wb') as f:
                                        f.write(depth) 

                                except Exception as e:
                                    print(f"Error processing {name}: {e}")
                                    continue

                            ind += 1
                            time.sleep(0.03)  # 减少休眠时间到30ms，大约对应30fps

                        for writer in video_writers.values():
                            writer.release()

                    # *******************************************************

                    save_dir_name = f"table_scene_map{map_num:03d}_room_{room_name}"
                    save_dir = os.path.join(dir, save_dir_name)
                    try:
                        is_running = True

                        th = threading.Thread(target=gen_video, args=(save_dir,))  
                        th.start()

                        MoveToObject_whilePass(ue, agents, Table_object[0], start_position1, end_position1, end_position2)

                        is_running = False
                        th.join()  
                    
                    except Exception as e:
                        print(f"Error occurred: {e}")
                        is_running = False
                        th.join()  

                    # 释放人物
                    [ue.destroy_entity(agent.id) for agent in agents]
                    

            except Exception as e:
                print(f"[ERROR] 处理地图 {map_name} 时发生错误: {str(e)}")
                continue

if __name__ == "__main__":
    # run_pipline_dropping(map_range=range(202, 240), dir = "./ownership/putdown/")
    # run_pipeline_Put(map_range=range(227, 250), Put_object=["wastebasket"], dir = "./ownership/throw_rubbish/")
    # run_pipeline_Put(map_range=range(230, 240), Put_object=['coffeetable', 'diningTable', 'table', 'Table'], dir = "./ownership/put_table/")
    run_pipeline_Passing(map_range=range(203,250), dir = "./ownership/passing/")


import tongsim as ts
import random
import math
import os
import time
from datetime import datetime

# Import utility functions from other_util.py
from .other_util import (
    fix_aabb_bounds,
    check_position_in_bbox
)

from utils.query_util import (
    query_existing_objects_in_room
)

from .orientation_util import (
    look_at_rotation    
)

# 生成随机摄像头位置
def calculate_entities_center(agents, items):
    """
    计算所有人物和物品的中心点
    
    Args:
        agents: 人物对象列表
        items: 物品对象列表
    
    Returns:
        ts.Vector3: 中心点位置
    """
    # 收集所有实体的位置
    all_positions = []
    
    # 添加人物位置
    for agent in agents:
        pos = agent.get_location()
        all_positions.append(pos)
    
    # 添加物品位置
    for item in items:
        pos = item.get_location()
        all_positions.append(pos)
    
    if not all_positions:
        return None
    
    # 计算边界框
    min_x = min(pos.x for pos in all_positions)
    min_y = min(pos.y for pos in all_positions)
    min_z = min(pos.z for pos in all_positions)
    max_x = max(pos.x for pos in all_positions)
    max_y = max(pos.y for pos in all_positions)
    max_z = max(pos.z for pos in all_positions)
    
    # 计算中心点
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2
    center_z = (min_z + max_z) / 2
    
    return ts.Vector3(center_x, center_y, center_z)

def generate_camera_positions(ue, room_bound, target_object, agents, center_location=None, num_cameras=5, safe_margin = 30, 
                              distance_range=[200, 500], height=[180, 300], agents_distance =100, min_cameras_distance = 80, print_info=False):
    """
    为指定房间生成在半球范围内的随机摄像头位置
    
    Args:
        room_bound: 房间边界框
        target_object: 拍摄目标对象
        agents: 房间内的人物对象列表
        num_cameras: 需要生成的摄像头数量
        safe_margin: 边界的安全边距
        distance_range: 摄像头到目标的距离范围 [min_distance, max_distance]
        height: 摄像头高度范围
        agents_distance: 摄像头与人物的最小距离
        min_cameras_distance: 摄像头之间的最小距离
        print_info: 是否打印信息
    
    Returns:
        list: 摄像头位置列表 [ts.Vector3, ...]
    """

    # 如果无法计算中心点，则使用桌子位置
    if center_location is None:
        center_location = target_object.get_location()
    
    target_x, target_y, target_z = center_location.x, center_location.y, center_location.z
    
    if print_info:
        print(f"[INFO] 使用场景中心点作为目标位置: {center_location}")
    
    # 提取房间边界坐标
    room_x_min, room_y_min, room_z_min, room_x_max, room_y_max, room_z_max = room_bound

    # 距离范围
    min_distance, max_distance = distance_range
    z_min_height, z_max_height = height

    # 查询可能影响摄像头放置的物品
    obstacle_types = [
        'curtains',      # 窗帘
        'windowframe',   # 窗框
        'window',        # 窗户
        'windowShutter', # 百叶窗
        'cabinet',       # 柜子
        'cupboard'       # 橱柜
    ]
    
    other_objects = query_existing_objects_in_room(
        ue=ue,
        room_bound=room_bound,
        target_types=obstacle_types,
        object_name="障碍物",
        print_info=print_info
    )
    
    if print_info:
        print(f"[INFO] 找到 {len(other_objects)} 个可能影响摄像头放置的物品")
        
    # 预先计算所有物品的AABB边界框
    obstacle_bounds = []
    for item in other_objects:
        try:
            item_aabb = item.get_world_aabb()
            item_min, item_max = fix_aabb_bounds(item_aabb)
            obstacle_bounds.append((item_min, item_max))
        except Exception as e:
            if print_info:
                print(f"[WARNING] 获取物品AABB失败: {str(e)}")
            continue
    
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

        # 检查是否与物品重叠
        camera_pos = ts.Vector3(camera_x, camera_y, camera_z)
        overlapping_with_item = False
        for item_min, item_max in obstacle_bounds:
            if check_position_in_bbox(camera_pos, item_min, item_max, safe_margin, True):  # 减小安全边距
                overlapping_with_item = True
                break
        if overlapping_with_item:
            continue

        # 检查与人物的距离
        too_close_to_agent = False  
        for agent in agents:
            agent_pos = agent.get_location()
            agent_distance = math.sqrt(
                (camera_x - agent_pos.x)**2 + 
                (camera_y - agent_pos.y)**2 + 
                (camera_z - agent_pos.z)**2
            )
            if agent_distance < agents_distance :
                too_close_to_agent = True
                break
        if too_close_to_agent:
            continue

        camera_pos = ts.Vector3(camera_x, camera_y, camera_z)
        camera_positions.append(camera_pos)
        
        if print_info:
            print(f"[PROCESSING] 摄像头 {len(camera_positions)}: ({camera_x:.2f}, {camera_y:.2f}, {camera_z:.2f})")
            print(f"[PROCESSING] 距离目标: {distance:.2f}, 角度: ({math.degrees(theta):.1f}°, {math.degrees(phi):.1f}°)")
    
    if len(camera_positions) < num_cameras:
        print(f"[WARNING] 只成功生成了 {len(camera_positions)}/{num_cameras} 个摄像头位置")
    
    return camera_positions

# 生成俯视摄像头的位置
def generate_top_view_camera_position(room_bound, agents, items, margin_factor=1.2, safe_margin=30, print_info=False):
    """
    生成俯视摄像头的位置
    
    Args:
        room_bound: 房间边界框
        agents: 人物对象列表
        items: 物品对象列表
        margin_factor: 视野边距系数（1.2表示额外20%的边距）
        safe_margin: 距离天花板的安全边距
        print_info: 是否打印信息
    
    Returns:
        ts.Vector3: 俯视摄像头位置
    """
    # 获取场景中所有实体的中心点和边界
    all_positions = []
    
    # 添加人物位置
    for agent in agents:
        pos = agent.get_location()
        all_positions.append(pos)
    
    # 添加物品位置
    for item in items:
        pos = item.get_location()
        all_positions.append(pos)
    
    if not all_positions:
        print("[ERROR] 没有找到任何实体用于计算俯视位置")
        return None
    
    # 计算边界框
    min_x = min(pos.x for pos in all_positions)
    min_y = min(pos.y for pos in all_positions)
    max_x = max(pos.x for pos in all_positions)
    max_y = max(pos.y for pos in all_positions)
    
    # 计算中心点
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2
    
    # 提取房间高度
    _, _, room_z_min, _, _, room_z_max = room_bound
    
    # 计算覆盖所需的最小高度
    # 使用最大的水平距离来确保完全覆盖
    scene_width = max_x - min_x
    scene_depth = max_y - min_y
    max_horizontal_size = max(scene_width, scene_depth) * margin_factor
    
    # 使用90度视场角计算所需高度（tan(45°) = 1）
    required_height = max_horizontal_size / 2  # 因为 tan(45°) = 1
    
    # 确定实际高度（不超过房间高度）
    camera_height = min(room_z_max - safe_margin, required_height + safe_margin)
    
    if camera_height < required_height:
        print(f"[WARNING] 房间高度不足以获得完整覆盖。需要 {required_height:.1f}，实际 {camera_height:.1f}")
    
    camera_position = ts.Vector3(center_x, center_y, camera_height)
    
    if print_info:
        print(f"[INFO] 俯视摄像头位置: {camera_position}")
        print(f"[INFO] 场景尺寸: {scene_width:.1f} x {scene_depth:.1f}")
        print(f"[INFO] 覆盖所需高度: {required_height:.1f}, 实际高度: {camera_height:.1f}")
    
    return camera_position

def add_capture_camera(ue, camera_positions, center_location, target_obj, camera_name_prefix="Camera", print_info=False):
    """
    为每个摄像头位置创建摄像头，并使其看向场景中心
    
    Args:
        ue: TongSim实例
        camera_positions: 摄像头位置列表 [ts.Vector3, ...] 或单个摄像头位置
        center_location: 场景中心点位置 (ts.Vector3)
        camera_name_prefix: 摄像头名称前缀
        print_info: 是否打印信息
    
    Returns:
        list: 创建的摄像头对象列表
    """
    cameras = []
    
    # 将单个摄像头位置转换为列表以统一处理
    if not isinstance(camera_positions, list):
        camera_positions = [camera_positions]
        
    for i, camera_position in enumerate(camera_positions):
        # 生成唯一的摄像头名称
        camera_name = f"{target_obj.id}_{camera_name_prefix}_{i+1}"
        
        # 计算摄像头朝向场景中心的旋转
        camera_quat = look_at_rotation(camera_position, center_location)
        
        # 创建摄像头
        camera = ue.spawn_camera(
            camera_name=camera_name,
            loc=camera_position,
            quat=camera_quat,
        )
        camera.set_intrinsic_params(90.0, 4096, 4096)
        cameras.append(camera)
        
        if print_info:
            print(f"[PROCESSING] 已创建摄像头 {camera_name} 在位置 {camera_position}")
    
    return cameras

# 使用所有摄像头拍摄并保存图像
def capture_and_save_images(cameras, save_dir="logs", delay_before_capture=0.5, RGB = True, Depth = False, print_info=False):
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
    # timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 等待场景稳定
    if delay_before_capture > 0:
        print(f"[PROCESSING] 等待 {delay_before_capture} 秒让场景稳定...")
        time.sleep(delay_before_capture)
    
    saved_images = {}
    
    for i, camera in enumerate(cameras):
        camera_id = camera.id
        print(f"[PROCESSING] 正在使用摄像头 {camera_id} 拍摄...")
        
        try:
            # 获取当前帧图像（RGB 和 Depth）
            image_wrapper = camera.get_current_imageshot(rgb=RGB, depth=False)
            
            # 使用图像时间戳作为唯一标识
            # time_tag = str(image_wrapper.render_time)
            # camera_prefix = f"{camera_id}_{time_tag}"
            
            # 保存RGB图像
            if image_wrapper.rgb:
                rgb_filename = f"{camera_id}_rgb.png"
                rgb_path = os.path.join(save_dir, rgb_filename)
                with open(rgb_path, "wb") as f:
                    f.write(image_wrapper.rgb)
                print(f"[Saved] RGB image -> {rgb_path}")
                
                # 记录保存路径
                if camera_id not in saved_images:
                    saved_images[camera_id] = {}
                saved_images[camera_id]['rgb'] = rgb_path
            
            # # 保存Depth图像
            # if image_wrapper.depth:
            #     depth_filename = f"{camera_id}_depth.png"
            #     depth_path = os.path.join(save_dir, depth_filename)
            #     with open(depth_path, "wb") as f:
            #         f.write(image_wrapper.depth)
            #     print(f"[Saved] Depth image -> {depth_path}")
                
            #     # 记录保存路径
            #     if camera_id not in saved_images:
            #         saved_images[camera_id] = {}
            #     saved_images[camera_id]['depth'] = depth_path
            
            print(f"摄像头 {camera_id} 拍摄完成")
            # ue.destroy_entity(camera_id)

            
        except Exception as e:
            print(f"[Error] 摄像头 {camera_id} 拍摄失败: {e}")
            if camera_id not in saved_images:
                saved_images[camera_id] = {}
            saved_images[camera_id]['error'] = str(e)
    
    return saved_images


import numpy as np
import json
from scene_visualization import get_object_display_type, create_reverse_blueprint_mapping

# ==================== 坐标转换函数 ====================
def quat2Rmat(x, y, z, w):
    R = np.zeros((3,3))
    R[0][0] = 1-2*y*y-2*z*z
    R[0][1] = 2*x*y+2*w*z
    R[0][2] = 2*x*z-2*w*y
    R[1][0] = 2*x*y-2*w*z
    R[1][1] = 1-2*x*x-2*z*z
    R[1][2] = 2*y*z+2*w*x
    R[2][0] = 2*x*z+2*w*y
    R[2][1] = 2*y*z-2*w*x
    R[2][2] = 1-2*x*x-2*y*y
    return R

def world2photo(point, rotation_matrix, location):
    point = np.array(point).reshape((3,))
    location = np.array(location).reshape((3,))
    rotation_matrix = np.array(rotation_matrix)
    R0 = rotation_matrix.transpose()
    R1 = location.reshape((3,1))
    R = np.concatenate((R0, R1), axis=1)
    ones = np.array([0,0,0,1])
    R = np.vstack((R, ones)) 
    R = np.matrix(R)
    R_I = R.I
    
    point = np.vstack((point.reshape(3,1), [1]))
    point_c = np.matmul(R_I, point)
    x, y, z = point_c[0,0], point_c[1,0], point_c[2,0]
    
    return [x, y, z]

def camera2image(point_camera, camera_intr_matrix):
    cx, cy, cz = point_camera
    point_ca = np.array([[cy], [cz], [cx], [1]])
    camera_intr_matrix = np.array(camera_intr_matrix)
    res = np.matmul(camera_intr_matrix, point_ca)
    res = res / res[-1]
    res = res.reshape((3,))
    
    out_w = camera_intr_matrix[0][2] * 2
    out_h = camera_intr_matrix[1][2] * 2
    
    point_x = res[0]
    point_y = out_h - res[1]
    return [point_x, point_y]

def world2image(point_world, camera_rotate_matrix, camera_intrinsic_matrix, camera_world_loc):
    point_camera = world2photo(point_world, camera_rotate_matrix, camera_world_loc)  
    point_pixel = camera2image(point_camera, camera_intrinsic_matrix)
    return point_pixel

# ==================== 投影函数 ====================
def prepare_camera_parameters(camera_data, image_width=4096, image_height=4096, fov=90.0):
    camera_world_loc = [camera_data['position']['x'], 
                       camera_data['position']['y'], 
                       camera_data['position']['z']]
    
    camera_quat = [camera_data['rotation']['x'],
                  camera_data['rotation']['y'],
                  camera_data['rotation']['z'],
                  camera_data['rotation']['w']]
    
    camera_rotate_matrix = quat2Rmat(*camera_quat)
    
    fov_rad = np.radians(fov)
    focal_length = image_width / (2 * np.tan(fov_rad / 2))
    
    camera_intrinsic_matrix = [
        [focal_length, 0, image_width / 2, 0],
        [0, focal_length, image_height / 2, 0],
        [0, 0, 1, 0]
    ]
    
    return camera_rotate_matrix, camera_intrinsic_matrix, camera_world_loc

def project_agent_to_image(agent_position, camera_data, image_width=4096, image_height=4096):
    camera_rotate_matrix, camera_intrinsic_matrix, camera_world_loc = prepare_camera_parameters(camera_data, image_width, image_height)
    
    agent_world_pos = [agent_position['x'], agent_position['y'], agent_position['z']]
    
    try:
        pixel_coords = world2image(agent_world_pos, camera_rotate_matrix, camera_intrinsic_matrix, camera_world_loc)
        return pixel_coords
    except Exception as e:
        print(f"投影错误: {e}")
        return None

def project_aabb_to_image(aabb_bounds, camera_data, image_width=4096, image_height=4096):
    min_point = aabb_bounds['min']
    max_point = aabb_bounds['max']
    
    corners_world = []
    for x in [min_point['x'], max_point['x']]:
        for y in [min_point['y'], max_point['y']]:
            for z in [min_point['z'], max_point['z']]:
                corners_world.append({'x': x, 'y': y, 'z': z})
    
    corner_points = []
    
    for corner in corners_world:
        pixel_coords = project_agent_to_image(corner, camera_data, image_width, image_height)
        if pixel_coords is not None:
            u, v = pixel_coords
            corner_points.append((u, v))
        else:
            corner_points.append((None, None))
    
    valid_points = [p for p in corner_points if p[0] is not None and p[1] is not None]
    
    if len(valid_points) == 0:
        return None
    
    u_coords = [p[0] for p in valid_points]
    v_coords = [p[1] for p in valid_points]
    
    x_min = max(0, min(u_coords))
    y_min = max(0, min(v_coords))
    x_max = min(image_width, max(u_coords))
    y_max = min(image_height, max(v_coords))
    
    return [x_min, y_min, x_max, y_max]

def calculate_all_projections(scene_data, image_width=4096, image_height=4096):
    """
    计算所有物体在所有相机中的投影
    返回一个嵌套字典，结构为：
    {
        camera_index: {
            object_id: {
                'bbox': [x_min, y_min, x_max, y_max],
                'center': [x, y],
                'visible': bool,
                'owner': str,
                'display_name': str
            }
        },
        'topcamera': {  # TopCamera的投影数据
            object_id: {...}
        }
    }
    """
    objects = scene_data['objects']
    cameras = scene_data['cameras']
    
    projections = {}
    
    # 创建反向蓝图映射
    reverse_blueprint_mapping = create_reverse_blueprint_mapping()
    
    # 为每个物体生成display_name
    asset_type_counters = {}
    object_display_names = {}
    
    for obj in objects:
        obj_type = get_object_display_type(obj)
        
        # 命名计数
        if obj_type in asset_type_counters:
            asset_type_counters[obj_type] += 1
            display_name = f"{obj_type}_{asset_type_counters[obj_type]}"
        else:
            asset_type_counters[obj_type] = 1
            display_name = f"{obj_type}_1"
        
        object_display_names[obj['id']] = display_name
    
    # 处理普通相机（非TopCamera）
    camera_list = [cam for cam in cameras if 'TopCamera' not in cam['id']]
    
    for cam_idx, camera in enumerate(camera_list):
        camera_projections = {}
        
        # 为每个物体计算投影
        for obj in objects:
            # 只处理有AABB的物体
            if 'aabb_bounds' not in obj:
                continue
            
            # 计算AABB投影
            bbox = project_aabb_to_image(obj['aabb_bounds'], camera, image_width, image_height)
            
            # 计算中心点投影
            center_coords = project_agent_to_image(obj['position'], camera, image_width, image_height)
            
            if bbox is not None and center_coords is not None:
                x_min, y_min, x_max, y_max = bbox
                center_x, center_y = center_coords
                
                # 判断是否在视图内
                visible = (0 <= x_min <= image_width and 
                          0 <= y_min <= image_height and
                          0 <= x_max <= image_width and 
                          0 <= y_max <= image_height and
                          x_max - x_min > 5 and 
                          y_max - y_min > 5)
                
                camera_projections[obj['id']] = {
                    'bbox': [float(x_min), float(y_min), float(x_max), float(y_max)],
                    'center': [float(center_x), float(center_y)],
                    'visible': bool(visible),
                    'owner': obj.get('owner', 'unknown'),
                    'asset_type': get_object_display_type(obj),
                    'display_name': object_display_names[obj['id']]
                }
        
        projections[cam_idx] = camera_projections
    
    # 处理TopCamera
    topcamera_list = [cam for cam in cameras if 'TopCamera' in cam['id']]
    if topcamera_list:
        topcamera = topcamera_list[0]
        topcamera_projections = {}
        
        for obj in objects:
            if 'aabb_bounds' not in obj:
                continue
            
            bbox = project_aabb_to_image(obj['aabb_bounds'], topcamera, image_width, image_height)
            center_coords = project_agent_to_image(obj['position'], topcamera, image_width, image_height)
            
            if bbox is not None and center_coords is not None:
                x_min, y_min, x_max, y_max = bbox
                center_x, center_y = center_coords
                
                visible = (0 <= x_min <= image_width and 
                          0 <= y_min <= image_height and
                          0 <= x_max <= image_width and 
                          0 <= y_max <= image_height and
                          x_max - x_min > 5 and 
                          y_max - y_min > 5)
                
                topcamera_projections[obj['id']] = {
                    'bbox': [float(x_min), float(y_min), float(x_max), float(y_max)],
                    'center': [float(center_x), float(center_y)],
                    'visible': bool(visible),
                    'owner': obj.get('owner', 'unknown'),
                    'asset_type': get_object_display_type(obj),
                    'display_name': object_display_names[obj['id']]
                }
        
        projections['topcamera'] = topcamera_projections
        
        # 计算agents在TopCamera中的投影
        agents = scene_data.get('agents', [])
        topcamera_agents = {}
        
        for agent in agents:
            agent_pixel_coords = project_agent_to_image(agent['position'], topcamera, image_width, image_height)
            
            if agent_pixel_coords is not None:
                u, v = agent_pixel_coords
                
                # 判断是否在视图内
                visible = (0 <= u <= image_width and 0 <= v <= image_height)
                
                # 获取agent的显示名称
                blueprint = agent.get('features', {}).get('type', 'unknown')
                display_name = reverse_blueprint_mapping.get(blueprint, blueprint)
                
                topcamera_agents[agent['id']] = {
                    'pixel_coords': [float(u), float(v)],
                    'visible': bool(visible),
                    'display_name': display_name,
                    'type': blueprint
                }
        
        projections['topcamera_agents'] = topcamera_agents
    
    return projections

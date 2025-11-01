import json
import numpy as np
import os
import glob
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from math import atan2, asin, degrees


# ==================== 人物蓝图映射 ====================
blueprint_mapping = {
    'girl': ["SDBP_Aich_AIBabyV7_Shoes", "SDBP_Aich_AIBaby_Lele_Shoes"],
    'boy': ["SDBP_Aich_AIBaby_Tiantian_90"],
    'woman': ["SDBP_Aich_Liyuxia"],
    'grandpa': ["SDBP_Aich_Yeye"],
    'man': ["SDBP_Aich_Zhanghaoran"]
}
def create_reverse_blueprint_mapping():
    reverse_mapping = {}
    for role, blueprints in blueprint_mapping.items():
        for i, blueprint in enumerate(blueprints, 1):
            if len(blueprints) > 1:
                reverse_mapping[blueprint] = f"{role}_{i}"
            else:
                reverse_mapping[blueprint] = role
    return reverse_mapping

def get_object_display_type(obj):
    """获取对象的显示类型，优先使用features.type，如果不存在则使用asset_type"""
    if 'features' in obj and 'type' in obj['features']:
        return obj['features']['type']
    return obj.get('asset_type', 'unknown')


def quaternion_to_euler(x, y, z, w):
    """将四元数转换为欧拉角（弧度）"""
    siny_cosp = 2 * (w * z + x * y)
    cosy_cosp = 1 - 2 * (y * y + z * z)
    yaw = atan2(siny_cosp, cosy_cosp)
    
    sinp = 2 * (w * y - z * x)
    if abs(sinp) >= 1:
        pitch = np.pi / 2 if sinp > 0 else -np.pi / 2
    else:
        pitch = asin(sinp)
    
    sinr_cosp = 2 * (w * x + y * z)
    cosr_cosp = 1 - 2 * (x * x + y * y)
    roll = atan2(sinr_cosp, cosr_cosp)
    
    return roll, pitch, yaw

def quaternion_to_direction_vector(x, y, z, w):
    """将四元数转换为前向方向向量"""
    forward_x = 2 * (x*z + w*y)
    forward_y = 2 * (y*z - w*x)
    forward_z = 1 - 2 * (x*x + y*y)
    
    return forward_x, forward_y, forward_z

def check_aabb_overlap(aabb1, aabb2, threshold=20):
    """检查两个AABB框是否重叠或接近"""
    # 扩展阈值的AABB
    min_x1 = aabb1['min']['x'] - threshold
    max_x1 = aabb1['max']['x'] + threshold
    min_y1 = aabb1['min']['y'] - threshold
    max_y1 = aabb1['max']['y'] + threshold
    
    min_x2 = aabb2['min']['x']
    max_x2 = aabb2['max']['x']
    min_y2 = aabb2['min']['y']
    max_y2 = aabb2['max']['y']
    
    # 判断是否重叠
    if max_x1 < min_x2 or min_x1 > max_x2 or max_y1 < min_y2 or min_y1 > max_y2:
        return False, 'none'
    
    # 判断重叠方向
    center_x1 = (min_x1 + max_x1) / 2
    center_x2 = (min_x2 + max_x2) / 2
    center_y1 = (min_y1 + max_y1) / 2
    center_y2 = (min_y2 + max_y2) / 2
    
    dx = abs(center_x1 - center_x2)
    dy = abs(center_y1 - center_y2)
    
    if dx > dy:
        return True, 'horizontal'
    else:
        return True, 'vertical'

def adjust_simple_label_position(labels, min_distance=20):
    """简单的标签位置避让函数（用于相机和人物标签）"""
    def get_distance(p1, p2):
        return np.sqrt((p1['x'] - p2['x'])**2 + (p1['y'] - p2['y'])**2)
    
    for i, label in enumerate(labels):
        label['offset_y'] = 15  # 默认偏移
        
        for j, other in enumerate(labels):
            if i != j:
                distance = get_distance(label, other)
                if distance < min_distance:
                    if label['y'] < other['y']:
                        label['offset_y'] = -25  # 向下偏移
                    else:
                        label['offset_y'] = 35  # 向上偏移

def determine_label_position(obj_index, objects, threshold=20):
    """确定标签位置"""
    current_obj = objects[obj_index]
    if 'aabb_bounds' not in current_obj:
        return {'position': 'top', 'offset_x': 0, 'offset_y': -20}
    
    current_aabb = current_obj['aabb_bounds']
    current_y = current_aabb['min']['y']  # 使用AABB的上边界作为y坐标
    
    # 找出所有上方的物体
    objects_above = []
    for i, other_obj in enumerate(objects):
        if i == obj_index:
            continue
        if 'aabb_bounds' not in other_obj:
            continue
        
        other_aabb = other_obj['aabb_bounds']
        other_y = other_aabb['max']['y']  # 使用其他物体的下边界
        
        # 如果其他物体在当前物体上方
        if other_y < current_y:
            # 计算两个AABB框在y方向上的距离
            y_distance = current_y - other_y
            if y_distance < threshold:
                objects_above.append((i, y_distance))
    
    # 如果没有上方物体或者与上方物体距离足够远，则在上方打标签
    if not objects_above:
        return {'position': 'top', 'offset_x': 0, 'offset_y': -8}
    
    # 如果有上方距离较近的物体，则在下方打标签
    return {'position': 'bottom', 'offset_x': 0, 'offset_y': 8}

def generate_scene_layout_plot(data, output_path, figsize=(14, 12)):
    """
    生成场景布局图并保存到指定路径
    
    Args:
        data: 包含场景信息的字典
        output_path: 输出图片文件路径
        figsize: 图片尺寸
    
    Returns:
        bool: 是否成功生成
    """
    try:
        # 提取数据
        scene_info = data['scene_info']
        objects = data['objects']
        agents = data['agents']
        cameras = data['cameras']
        
        # 创建图形
        plt.figure(figsize=figsize)
        
        # 设置y轴向下为正方向
        plt.gca().invert_yaxis()
        
        # 定义颜色方案
        table_aabb_color = 'gray'
        table_center_color = 'black'
        room_object_color = 'blue'
        person_table_object_color = 'green'
        agent_color = 'orange'
        camera_color = 'red'
        
        # 1. 绘制桌子位置和AABB边界框
        table_x = scene_info['position']['x']
        table_y = scene_info['position']['y']
        
        table_aabb = scene_info['aabb_bounds']
        table_min_x = table_aabb['min']['x']
        table_min_y = table_aabb['min']['y']
        table_max_x = table_aabb['max']['x']
        table_max_y = table_aabb['max']['y']
        table_width = table_max_x - table_min_x
        table_height = table_max_y - table_min_y
        
        table_rect = patches.Rectangle(
            (table_min_x, table_min_y), table_width, table_height,
            linewidth=2, edgecolor=table_aabb_color, facecolor=table_aabb_color, 
            alpha=0.3, label='Table'
        )
        plt.gca().add_patch(table_rect)
        
        # 绘制桌子中心点
        plt.scatter(table_x, table_y, c=table_center_color, s=150, marker='s', 
                   edgecolors='white', linewidth=1.5, zorder=5)


        # 2. 确定关键元素的范围（桌子和所有摄像机）
        key_points_x = [table_min_x, table_max_x, table_x]
        key_points_y = [table_min_y, table_max_y, table_y]
        
        # 添加所有摄像机位置到关键点
        for camera in cameras:
            cam_x = camera['position']['x']
            cam_y = camera['position']['y']
            key_points_x.append(cam_x)
            key_points_y.append(cam_y)
        
        # 计算关键元素的边界
        key_min_x = min(key_points_x)
        key_max_x = max(key_points_x)
        key_min_y = min(key_points_y)
        key_max_y = max(key_points_y)
        
        # 计算方形区域的中心点
        center_x = (key_min_x + key_max_x) / 2
        center_y = (key_min_y + key_max_y) / 2
        
        # 计算方形区域的边长（取最大边长并添加额外边距）
        key_width = key_max_x - key_min_x
        key_height = key_max_y - key_min_y
        square_size = max(key_width, key_height) * 1.2  # 添加20%边距
        
        # 设置方形区域的边界
        square_min_x = center_x - square_size / 2
        square_max_x = center_x + square_size / 2
        square_min_y = center_y - square_size / 2
        square_max_y = center_y + square_size / 2

        # 3. 预处理所有物体的命名和位置
        asset_type_counters = {}
        
        # 为每个物体确定标签位置
        for i, obj in enumerate(objects):
            # 处理命名
            asset_type = get_object_display_type(obj)
            if asset_type in asset_type_counters:
                asset_type_counters[asset_type] += 1
                display_name = f"{asset_type}_{asset_type_counters[asset_type]}"
            else:
                asset_type_counters[asset_type] = 1
                display_name = f"{asset_type}_1"
            
            obj['display_name'] = display_name
            
            # 确定标签位置
            label_position = determine_label_position(i, objects)
            obj['label_position'] = label_position
        
        # 4. 绘制所有物体
        for obj in objects:
            x = obj['position']['x']
            y = obj['position']['y']
            display_name = obj['display_name']
            owner = obj.get('owner', 'unknown')
            label_pos = obj['label_position']
            
            if owner == 'room':
                color = room_object_color
                bbox_color = room_object_color
            else:
                color = person_table_object_color
                bbox_color = person_table_object_color
            
            # 绘制物体的AABB边界框
            if 'aabb_bounds' in obj:
                aabb = obj['aabb_bounds']
                min_x = aabb['min']['x']
                min_y = aabb['min']['y']
                max_x = aabb['max']['x']
                max_y = aabb['max']['y']
                width = max_x - min_x
                height = max_y - min_y
                
                rect = patches.Rectangle(
                    (min_x, min_y), width, height,
                    linewidth=1, edgecolor=bbox_color, facecolor=bbox_color, alpha=0.15
                )
                plt.gca().add_patch(rect)
            
            # 绘制物体点
            plt.scatter(x, y, c=color, s=30, marker='o', alpha=0.8, zorder=4)
            
            # 根据AABB边界框的位置计算标签位置
            aabb = obj['aabb_bounds']
            min_x = aabb['min']['x']
            min_y = aabb['min']['y']
            max_x = aabb['max']['x']
            max_y = aabb['max']['y']
            center_x = (min_x + max_x) / 2
            
            # 只使用上下标签
            anchor_x = center_x
            anchor_y = min_y if label_pos['position'] == 'top' else max_y
            plt.annotate(
                display_name, 
                (anchor_x, anchor_y),
                xytext=(0, -8 if label_pos['position'] == 'top' else 8),
                textcoords='offset points',
                fontsize=8,
                color=color,
                weight='bold',
                ha='center',
                va='bottom' if label_pos['position'] == 'top' else 'top',
                bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8)
            )
        
        # 4. 绘制Agents（人物）位置和朝向
        reverse_blueprint_mapping = create_reverse_blueprint_mapping()
        
        if agents:
            agent_labels = []
            for agent in agents:
                agent_labels.append({
                    'x': agent['position']['x'],
                    'y': agent['position']['y'],
                    'offset_y': -20
                })
            
            adjust_simple_label_position(agent_labels, min_distance=30)
            
            for i, agent in enumerate(agents):
                agent_x = agent['position']['x']
                agent_y = agent['position']['y']
                blueprint = agent['features']['type'] if 'features' in agent and 'type' in agent['features'] else 'unknown'
                
                display_name = reverse_blueprint_mapping.get(blueprint, blueprint)
                
                # 提取四元数计算朝向
                rot = agent['rotation']
                qx, qy, qz, qw = rot['x'], rot['y'], rot['z'], rot['w']
                forward_x, forward_y, forward_z = quaternion_to_direction_vector(qx, qy, qz, qw)
                
                arrow_length = 25
                direction_magnitude = np.sqrt(forward_x**2 + forward_y**2)
                if direction_magnitude > 0:
                    norm_x = forward_x / direction_magnitude
                    norm_y = forward_y / direction_magnitude
                else:
                    norm_x, norm_y = 0, 0
                
                # 绘制Agent位置和朝向
                plt.scatter(agent_x, agent_y, c=agent_color, s=120, marker='D', 
                           edgecolors='black', linewidth=1.5, zorder=6)
                plt.arrow(agent_x, agent_y, norm_x * arrow_length, norm_y * arrow_length,
                         head_width=8, head_length=6, fc=agent_color, ec=agent_color, 
                         linewidth=1.5, alpha=0.8, zorder=5)
                plt.annotate(display_name, (agent_x, agent_y), 
                            xytext=(0, agent_labels[i]['offset_y']), 
                            textcoords='offset points', 
                            fontsize=9, color=agent_color, weight='bold', ha='center',
                            bbox=dict(boxstyle='round,pad=0.3', facecolor='white', alpha=0.9))
        
        # 5. 绘制相机位置和视角方向
        if cameras:
            camera_labels = []
            for camera in cameras:
                camera_labels.append({
                    'x': camera['position']['x'],
                    'y': camera['position']['y'],
                    'offset_y': 8
                })
            
            adjust_simple_label_position(camera_labels, min_distance=25)
            
            for i, camera in enumerate(cameras):
                cam_x = camera['position']['x']
                cam_y = camera['position']['y']
                
                rot = camera['rotation']
                qx, qy, qz, qw = rot['x'], rot['y'], rot['z'], rot['w']
                forward_x, forward_y, forward_z = quaternion_to_direction_vector(qx, qy, qz, qw)
                
                arrow_length = 20
                direction_magnitude = np.sqrt(forward_x**2 + forward_y**2)
                if direction_magnitude > 0:
                    norm_x = forward_x / direction_magnitude
                    norm_y = forward_y / direction_magnitude
                else:
                    norm_x, norm_y = 0, 0
                
                # 绘制相机位置和朝向
                plt.scatter(cam_x, cam_y, c=camera_color, s=100, marker='^', 
                           edgecolors='black', linewidth=1.5, zorder=6)
                plt.arrow(cam_x, cam_y, norm_x * arrow_length, norm_y * arrow_length,
                         head_width=6, head_length=5, fc=camera_color, ec=camera_color, 
                         linewidth=1.5, alpha=0.8, zorder=5)
                plt.annotate(f'Cam{i+1}', (cam_x, cam_y), 
                            xytext=(0, camera_labels[i]['offset_y']), 
                            textcoords='offset points',
                            fontsize=8, color=camera_color, weight='bold',
                            bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.9))
        
        # 设置坐标轴和标题
        plt.xlabel('X Coordinate', fontsize=12, fontweight='bold')
        plt.ylabel('Y Coordinate (Downward Positive)', fontsize=12, fontweight='bold')
        plt.title('Scene Layout - Top-Down View', fontsize=16, fontweight='bold', pad=20)
        plt.grid(True, alpha=0.2, linestyle='-', linewidth=0.5)
        
        # 图例
        legend_elements = [
            plt.Line2D([0], [0], marker='s', color='w', markerfacecolor=table_center_color, 
                       markersize=8, label='Table Center'),
            patches.Patch(facecolor=table_aabb_color, alpha=0.3, label='Table Range'),
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=room_object_color, 
                       markersize=8, label='Room Objects'),
            plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=person_table_object_color, 
                       markersize=8, label='Person/Table Objects'),
            plt.Line2D([0], [0], marker='D', color='w', markerfacecolor=agent_color, 
                       markersize=8, label='Agents'),
            plt.Line2D([0], [0], marker='^', color='w', markerfacecolor=camera_color, 
                       markersize=8, label='Cameras')
        ]
        
        plt.legend(handles=legend_elements, loc='upper right', fontsize=10, 
                   framealpha=0.9, fancybox=True, shadow=True)
        

        # 设置坐标轴范围 - 使用计算出的方形区域
        plt.xlim(square_min_x, square_max_x)
        plt.ylim(square_min_y, square_max_y)
        plt.axis('equal')
        
        plt.tight_layout()
        
        # 保存图片
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"[SUCCESS] 场景布局图已保存到: {output_path}")
        return True
        
    except Exception as e:
        print(f"[ERROR] 生成场景布局图失败: {e}")
        plt.close()
        return False

def batch_generate_scene_layouts(base_path):
    """
    批量生成场景布局图
    
    Args:
        base_path: 基础路径，如 './4agents_6_allmap/'
    
    Returns:
        dict: 包含处理结果的统计信息
    """
    results = {
        'total_folders': 0,
        'successful_generations': 0,
        'failed_generations': 0,
        'processed_folders': []
    }
    
    # 查找所有包含scene_data.json的文件夹
    json_pattern = os.path.join(base_path, "**", "scene_data.json")
    json_files = glob.glob(json_pattern, recursive=True)
    
    print(f"找到 {len(json_files)} 个scene_data.json文件")
    
    for json_file in json_files:
        folder_path = os.path.dirname(json_file)
        folder_name = os.path.basename(folder_path)
        
        results['total_folders'] += 1
        
        try:
            # 创建ground_truth文件夹
            ground_truth_dir = os.path.join(folder_path, "ground_truth")
            os.makedirs(ground_truth_dir, exist_ok=True)
            
            # 加载JSON数据
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 生成输出文件名
            output_filename = f"{folder_name}_layout.png"
            output_path = os.path.join(ground_truth_dir, output_filename)
            
            # 生成场景布局图
            success = generate_scene_layout_plot(data, output_path)
            
            if success:
                results['successful_generations'] += 1
                results['processed_folders'].append({
                    'folder': folder_name,
                    'status': 'success',
                    'output_path': output_path
                })
            else:
                results['failed_generations'] += 1
                results['processed_folders'].append({
                    'folder': folder_name,
                    'status': 'failed',
                    'output_path': output_path
                })
                
        except Exception as e:
            print(f"[ERROR] 处理文件夹 {folder_name} 失败: {e}")
            results['failed_generations'] += 1
            results['processed_folders'].append({
                'folder': folder_name,
                'status': 'error',
                'error': str(e)
            })
    
    # 打印统计信息
    print(f"\n{'='*80}")
    print("批量生成完成统计:")
    print(f"{'='*80}")
    print(f"总文件夹数: {results['total_folders']}")
    print(f"成功生成: {results['successful_generations']}")
    print(f"失败: {results['failed_generations']}")
    print(f"成功率: {results['successful_generations']/results['total_folders']*100:.1f}%")
    
    return results

def layout(base_path = "./ownership/4agents_6_allmap/"):
    # 批量生成
    results = batch_generate_scene_layouts(base_path)
    
    # 打印详细结果
    print(f"\n详细处理结果:")
    for item in results['processed_folders']:
        status_icon = "✅" if item['status'] == 'success' else "❌"
        print(f"{status_icon} {item['folder']}: {item['status']}")



from PIL import Image
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
    valid_corners = 0
    
    for corner in corners_world:
        pixel_coords = project_agent_to_image(corner, camera_data, image_width, image_height)
        if pixel_coords is not None:
            u, v = pixel_coords
            corner_points.append((u, v))
            if 0 <= u <= image_width and 0 <= v <= image_height:
                valid_corners += 1
        else:
            corner_points.append((None, None))
    
    valid_points = [p for p in corner_points if p[0] is not None and p[1] is not None]
    
    if len(valid_points) == 0:
        return None, corner_points
    
    u_coords = [p[0] for p in valid_points]
    v_coords = [p[1] for p in valid_points]
    
    x_min = max(0, min(u_coords))
    y_min = max(0, min(v_coords))
    x_max = min(image_width, max(u_coords))
    y_max = min(image_height, max(v_coords))
    
    image_bbox = [x_min, y_min, x_max, y_max]
    
    return image_bbox, corner_points


# ==================== 主处理函数 ====================
def determine_projection_label_position(obj_index, projections, threshold=40):
    """确定投影图中标签位置"""
    current_proj = projections[obj_index]
    current_bbox = current_proj['aabb_bbox']
    if current_bbox is None:
        return {'position': 'top', 'offset_y': -20}
    
    # 使用 bbox 的上边界作为y坐标
    current_y = current_bbox[1]  # y_min
    
    # 找出所有上方的物体
    objects_above = []
    for i, other_proj in enumerate(projections):
        if i == obj_index:
            continue
        if other_proj['aabb_bbox'] is None:
            continue
        
        other_bbox = other_proj['aabb_bbox']
        other_y = other_bbox[3]  # y_max
        
        # 如果其他物体在当前物体上方
        if other_y < current_y:
            # 计算两个AABB框在y方向上的距离
            y_distance = current_y - other_y
            if y_distance < threshold:
                objects_above.append((i, y_distance))
    
    # 如果没有上方物体或者与上方物体距离足够远，则在上方打标签
    if not objects_above:
        return {'position': 'top', 'offset_y': -20}
    
    # 如果有上方距离较近的物体，则在下方打标签
    return {'position': 'bottom', 'offset_y': 20}

def generate_camera_projection_plots(data, image_paths, output_dir, image_width=4096, image_height=4096):
    """
    为每个相机生成带投影框的图片
    
    Args:
        data: 场景数据字典
        image_paths: 图片路径列表
        output_dir: 输出目录
        image_width: 图像宽度
        image_height: 图像高度
    """
    objects = data['objects']
    agents = data['agents']
    cameras = data['cameras']
    
    reverse_blueprint_mapping = create_reverse_blueprint_mapping()
    
    # 定义颜色
    agent_color = 'gold'
    object_bbox_color = 'green'
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    results = []
    
    # 遍历所有图片（有几张图就处理几张）
    for img_idx, image_path in enumerate(image_paths):
        # 检查是否有对应的相机数据
        if img_idx >= len(cameras):
            print(f"警告: 图片 {img_idx+1} 没有对应的相机数据")
            continue
            
        camera = cameras[img_idx]
        
        # 加载图像
        try:
            img_pil = Image.open(image_path)
            img_array = np.array(img_pil)
        except Exception as e:
            print(f"错误: 无法加载图片 {image_path}: {e}")
            continue
        
        # 创建图形
        fig, ax = plt.subplots(figsize=(12, 12))
        ax.imshow(img_array)
        
        # 为当前相机计算投影
        agent_projections = []
        object_projections_with_aabb = []
        
        # 计算agents投影
        for agent in agents:
            pixel_coords = project_agent_to_image(agent['position'], camera, image_width, image_height)
            if pixel_coords is not None:
                u, v = pixel_coords
                status = "In view" if 0 <= u <= image_width and 0 <= v <= image_height else "Out of view"
                agent_projections.append({
                    'agent': agent,
                    'pixel_coords': (u, v),
                    'status': status
                })
        
        # 计算objects投影（带AABB）
        for obj in objects:
            pixel_coords = project_agent_to_image(obj['position'], camera, image_width, image_height)
            if pixel_coords is not None:
                u, v = pixel_coords
                status = "In view" if 0 <= u <= image_width and 0 <= v <= image_height else "Out of view"
                aabb_bbox, _ = project_aabb_to_image(obj['aabb_bounds'], camera, image_width, image_height)
                object_projections_with_aabb.append({
                    'object': obj,
                    'pixel_coords': (u, v),
                    'status': status,
                    'owner': obj.get('owner', 'unknown'),
                    'aabb_bbox': aabb_bbox
                })
        
        # 统计当前相机视图中每种asset_type的数量，用于编号
        asset_type_counter = {}
        for projection in object_projections_with_aabb:
            if projection['status'] == "In view" and projection['owner'] not in ['room']:
                obj = projection['object']
                asset_type = get_object_display_type(obj)
                if asset_type in asset_type_counter:
                    asset_type_counter[asset_type] += 1
                else:
                    asset_type_counter[asset_type] = 1
        
        # 为每种asset_type创建编号映射
        asset_type_current_count = {}
        asset_type_display_names = {}
        
        for projection in object_projections_with_aabb:
            if projection['status'] == "In view" and projection['owner'] not in ['room']:
                obj = projection['object']
                asset_type = get_object_display_type(obj)
                
                if asset_type not in asset_type_current_count:
                    asset_type_current_count[asset_type] = 1
                else:
                    asset_type_current_count[asset_type] += 1
                
                if asset_type_counter[asset_type] > 1:
                    display_name = f"{asset_type}_{asset_type_current_count[asset_type]}"
                else:
                    display_name = asset_type
                
                asset_type_display_names[id(obj)] = display_name
        
        # 预处理：过滤出在视图内的、不属于房间的物品
        visible_projections = []
        for proj in object_projections_with_aabb:
            if (proj['status'] == "In view" and 
                proj['owner'] not in ['room'] and 
                proj['aabb_bbox'] is not None):
                visible_projections.append(proj)
        
        # 为每个可见物体确定标签位置
        for i, proj in enumerate(visible_projections):
            label_pos = determine_projection_label_position(i, visible_projections)
            proj['label_position'] = label_pos
        
        # 绘制物品的AABB边界框和标签
        for projection in visible_projections:
            obj = projection['object']
            aabb_bbox = projection['aabb_bbox']
            label_pos = projection['label_position']
            x_min, y_min, x_max, y_max = aabb_bbox
            width = x_max - x_min
            height = y_max - y_min
            
            if width > 5 and height > 5:
                # 绘制AABB边界框
                rect = plt.Rectangle((x_min, y_min), width, height, 
                                   fill=False, edgecolor=object_bbox_color, linewidth=0.5, 
                                   linestyle='-', alpha=0.8)
                ax.add_patch(rect)
                
                # 获取显示名称
                display_name = asset_type_display_names.get(id(obj), obj.get('asset_type', 'unknown'))
                
                # 计算标签位置
                center_x = (x_min + x_max) / 2
                anchor_y = y_min if label_pos['position'] == 'top' else y_max
                
                # 绘制标签
                ax.annotate(
                    display_name,
                    (center_x, anchor_y),
                    xytext=(0, label_pos['offset_y']),
                    textcoords='offset points',
                    fontsize=4,
                    color=object_bbox_color,
                    weight='bold',
                    ha='center',
                    va='bottom' if label_pos['position'] == 'top' else 'top',
                    bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8)
                )
        
        # 统计当前相机视图中每种人物类型的数量，用于编号
        agent_type_counter = {}
        for projection in agent_projections:
            if projection['status'] == "In view":
                agent = projection['agent']
                blueprint = agent['features']['type'] if 'features' in agent and 'type' in agent['features'] else 'unknown'
                agent_type = reverse_blueprint_mapping.get(blueprint, blueprint)
                
                if agent_type in agent_type_counter:
                    agent_type_counter[agent_type] += 1
                else:
                    agent_type_counter[agent_type] = 1
        
        # 为每种人物类型创建编号映射
        agent_type_current_count = {}
        agent_display_names = {}
        
        for projection in agent_projections:
            if projection['status'] == "In view":
                agent = projection['agent']
                blueprint = agent['features']['type'] if 'features' in agent and 'type' in agent['features'] else 'unknown'
                base_agent_type = reverse_blueprint_mapping.get(blueprint, blueprint)
                
                if base_agent_type not in agent_type_current_count:
                    agent_type_current_count[base_agent_type] = 1
                else:
                    agent_type_current_count[base_agent_type] += 1
                
                if agent_type_counter[base_agent_type] > 1:
                    display_name = f"{base_agent_type}_{agent_type_current_count[base_agent_type]}"
                else:
                    display_name = base_agent_type
                
                agent_display_names[id(agent)] = display_name
        
        # 绘制agents
        for projection in agent_projections:
            agent = projection['agent']
            u, v = projection['pixel_coords']
            status = projection['status']
            
            if status == "In view":
                ax.scatter(u, v, c=agent_color, s=150, marker='D', 
                          edgecolors='black', linewidth=2, alpha=0.9)
                
                display_name = agent_display_names.get(id(agent), 'unknown')
                ax.text(u, v - 40, display_name, 
                       fontsize=5, color=agent_color, weight='bold', ha='center',
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='black', alpha=0.8))
        
        
        # 设置标题和统计信息
        in_view_agents = sum(1 for p in agent_projections if p['status'] == "In view")
        in_view_objects = sum(1 for p in object_projections_with_aabb if p['owner'] not in ['room'] and p['status'] == "In view")
        
        # ax.set_title(f'Camera {img_idx+1} ({camera["id"]})\n{in_view_agents} agents, {in_view_objects} objects in view', 
        #             fontsize=14, fontweight='bold')
        ax.axis('off')
        
        # 保存图片 - 使用原始图片文件名作为基础
        original_filename = os.path.basename(image_path)
        name_without_ext = os.path.splitext(original_filename)[0]
        output_filename = f"{name_without_ext}_projection.png"
        output_path = os.path.join(output_dir, output_filename)
        
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        results.append({
            'image_index': img_idx,
            'camera_id': camera['id'],
            'original_image': original_filename,
            'output_path': output_path,
            'agents_in_view': in_view_agents,
            'objects_in_view': in_view_objects
        })
        
        print(f"✅ 图片 {img_idx+1} 投影图已保存: {output_path}")
    
    return results

# ==================== 批量处理函数 ====================
def batch_process_scenes(base_path):
    """
    批量处理所有场景
    
    Args:
        base_path: 基础路径，如 './4agents_6_allmap/'
    
    Returns:
        dict: 处理结果统计
    """
    # 查找所有包含scene_data.json的文件夹
    json_pattern = os.path.join(base_path, "**", "scene_data.json")
    json_files = glob.glob(json_pattern, recursive=True)
    
    print(f"找到 {len(json_files)} 个场景数据文件")
    
    all_results = {}
    
    for json_file in json_files:
        folder_path = os.path.dirname(json_file)
        folder_name = os.path.basename(folder_path)
        
        print(f"\n{'='*60}")
        print(f"处理场景: {folder_name}")
        print(f"{'='*60}")
        
        try:
            # 加载JSON数据
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 查找对应的图片文件
            image_paths = glob.glob(os.path.join(folder_path, "*rgb.png"))
            print(f"找到 {len(image_paths)} 张图片")
            
            if len(image_paths) == 0:
                print(f"⚠️  警告: 在 {folder_path} 中没有找到rgb.png图片")
                continue
            
            # 创建输出目录
            output_dir = os.path.join(folder_path, "ground_truth")
            
            # 生成投影图
            results = generate_camera_projection_plots(data, image_paths, output_dir)
            
            all_results[folder_name] = {
                'folder_path': folder_path,
                'image_count': len(image_paths),
                'camera_count': len(data['cameras']),
                'agent_count': len(data['agents']),
                'object_count': len(data['objects']),
                'results': results
            }
            
            print(f"✅ 场景 {folder_name} 处理完成，生成 {len(results)} 张投影图")
            
        except Exception as e:
            print(f"❌ 处理场景 {folder_name} 时出错: {e}")
            continue
    
    return all_results

# ==================== MAIN函数 ====================
def pictures(base_path = "./ownership/4agents_1_allmap/"):
    """
    主函数：批量处理所有场景
    """
    
    # 检查路径是否存在
    if not os.path.exists(base_path):
        print(f"错误: 路径 {base_path} 不存在")
        return
    
    print("开始批量处理场景...")
    print(f"基础路径: {base_path}")
    
    # 执行批量处理
    results = batch_process_scenes(base_path)
    
    # 打印总结
    print(f"\n{'='*80}")
    print("批量处理完成总结:")
    print(f"{'='*80}")
    print(f"总处理场景数: {len(results)}")
    
    total_images = 0
    for scene_name, scene_info in results.items():
        image_count = scene_info['image_count']
        generated_count = len(scene_info['results'])
        total_images += generated_count
        print(f"  {scene_name}: {generated_count}/{image_count} 张图片处理完成")
    
    print(f"总共生成 {total_images} 张投影图")
    print(f"输出目录: 各场景文件夹下的 ground_truth 文件夹")

# 使用示例
if __name__ == "__main__":

    layout(base_path = "./ownership/2agents_1_allmap/")
    pictures(base_path = "./ownership/2agents_1_allmap/")
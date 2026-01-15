"""
Projection Utilities
====================
Mathematical projection logic for converting 3D world coordinates to 2D image pixels.
"""
import numpy as np
from config import IMAGE_WIDTH, IMAGE_HEIGHT, FOV


def quat2Rmat(x, y, z, w):
    """Convert quaternion to rotation matrix."""
    R = np.zeros((3, 3))
    R[0][0] = 1 - 2*y*y - 2*z*z
    R[0][1] = 2*x*y + 2*w*z
    R[0][2] = 2*x*z - 2*w*y
    R[1][0] = 2*x*y - 2*w*z
    R[1][1] = 1 - 2*x*x - 2*z*z
    R[1][2] = 2*y*z + 2*w*x
    R[2][0] = 2*x*z + 2*w*y
    R[2][1] = 2*y*z - 2*w*x
    R[2][2] = 1 - 2*x*x - 2*y*y
    return R


def world2camera(point, rotation_matrix, camera_location):
    """Transform world coordinates to camera coordinates."""
    point = np.array(point).reshape((3,))
    camera_location = np.array(camera_location).reshape((3,))
    rotation_matrix = np.array(rotation_matrix)
    
    R0 = rotation_matrix.transpose()
    R1 = camera_location.reshape((3, 1))
    R = np.concatenate((R0, R1), axis=1)
    ones = np.array([0, 0, 0, 1])
    R = np.vstack((R, ones))
    R = np.matrix(R)
    R_I = R.I
    
    point = np.vstack((point.reshape(3, 1), [1]))
    point_c = np.matmul(R_I, point)
    x, y, z = point_c[0, 0], point_c[1, 0], point_c[2, 0]
    
    return [x, y, z]


def camera2image(point_camera, camera_intrinsic):
    """Transform camera coordinates to image pixel coordinates."""
    cx, cy, cz = point_camera
    point_ca = np.array([[cy], [cz], [cx], [1]])
    camera_intrinsic = np.array(camera_intrinsic)
    res = np.matmul(camera_intrinsic, point_ca)
    res = res / res[-1]
    res = res.reshape((3,))
    
    out_w = camera_intrinsic[0][2] * 2
    out_h = camera_intrinsic[1][2] * 2
    
    point_x = res[0]
    point_y = out_h - res[1]
    return [point_x, point_y]


def world2image(point_world, rotation_matrix, intrinsic_matrix, camera_location):
    """Transform world coordinates to image pixel coordinates."""
    point_camera = world2camera(point_world, rotation_matrix, camera_location)
    point_pixel = camera2image(point_camera, intrinsic_matrix)
    return point_pixel


def prepare_camera_params(camera_data, image_width=IMAGE_WIDTH, image_height=IMAGE_HEIGHT, fov=FOV):
    """Prepare camera parameters from scene data."""
    camera_location = [
        camera_data['position']['x'],
        camera_data['position']['y'],
        camera_data['position']['z']
    ]
    
    camera_quat = [
        camera_data['rotation']['x'],
        camera_data['rotation']['y'],
        camera_data['rotation']['z'],
        camera_data['rotation']['w']
    ]
    
    rotation_matrix = quat2Rmat(*camera_quat)
    
    fov_rad = np.radians(fov)
    focal_length = image_width / (2 * np.tan(fov_rad / 2))
    
    intrinsic_matrix = [
        [focal_length, 0, image_width / 2, 0],
        [0, focal_length, image_height / 2, 0],
        [0, 0, 1, 0]
    ]
    
    return rotation_matrix, intrinsic_matrix, camera_location


def project_aabb_to_polygon(entity_min, entity_max, rotation_matrix, intrinsic_matrix, camera_location, image_width=IMAGE_WIDTH, image_height=IMAGE_HEIGHT):
    """
    Project 3D AABB to 2D polygon (convex hull of projected corners).
    
    Returns:
        List of [x, y] points or None if projection fails
    """
    corners_3d = []
    for x in [entity_min['x'], entity_max['x']]:
        for y in [entity_min['y'], entity_max['y']]:
            for z in [entity_min['z'], entity_max['z']]:
                corners_3d.append([x, y, z])
    
    projected_points = []
    for corner in corners_3d:
        try:
            pixel = world2image(corner, rotation_matrix, intrinsic_matrix, camera_location)
            if 0 <= pixel[0] <= image_width and 0 <= pixel[1] <= image_height:
                projected_points.append(pixel)
        except:
            continue
    
    if len(projected_points) < 3:
        return None
    
    # Compute convex hull (simple method: bounding box of valid points)
    u_coords = [p[0] for p in projected_points]
    v_coords = [p[1] for p in projected_points]
    
    x_min = max(0, min(u_coords))
    y_min = max(0, min(v_coords))
    x_max = min(image_width, max(u_coords))
    y_max = min(image_height, max(v_coords))
    
    # Return as 4-point polygon
    return [
        [x_min, y_min],
        [x_max, y_min],
        [x_max, y_max],
        [x_min, y_max]
    ]


def project_point_to_2d(location, rotation_matrix, intrinsic_matrix, camera_location):
    """
    Project a single 3D point to 2D (for agent labels).
    
    Returns:
        [x, y] or None if behind camera
    """
    try:
        point_3d = [location['x'], location['y'], location['z']]
        pixel = world2image(point_3d, rotation_matrix, intrinsic_matrix, camera_location)
        return pixel
    except:
        return None


def get_agent_label_position(agent, rotation_matrix, intrinsic_matrix, camera_location):
    """
    Get optimal 3D position for agent label (prefers head bone over location).
    
    Priority:
    1. skeleton.head
    2. skeleton.spine_03
    3. location (fallback)
    
    Returns:
        [x, y] pixel coordinates or None
    """
    position_3d = None
    
    # Priority 1: Head bone
    if 'skeleton' in agent and agent['skeleton'] and 'head' in agent['skeleton']:
        position_3d = agent['skeleton']['head']
    # Priority 2: Spine_03 bone
    elif 'skeleton' in agent and agent['skeleton'] and 'spine_03' in agent['skeleton']:
        position_3d = agent['skeleton']['spine_03']
    # Priority 3: Fallback to location
    elif 'location' in agent:
        position_3d = agent['location']
    
    if position_3d:
        return project_point_to_2d(position_3d, rotation_matrix, intrinsic_matrix, camera_location)
    
    return None


def get_agent_hull(agent, rotation_matrix, intrinsic_matrix, camera_location, image_width=IMAGE_WIDTH, image_height=IMAGE_HEIGHT):
    """
    Calculate 2D convex hull of agent's skeleton joints.
    
    Args:
        agent: Agent data with skeleton information
        rotation_matrix: Camera rotation matrix
        intrinsic_matrix: Camera intrinsic matrix
        camera_location: Camera position
        image_width: Image width for bounds checking
        image_height: Image height for bounds checking
    
    Returns:
        List of [x, y] points forming convex hull, or None if insufficient data
    """
    joints_2d = []
    
    # Project all skeleton joints to 2D
    if 'skeleton' in agent and agent['skeleton']:
        for bone_name, position in agent['skeleton'].items():
            if position and isinstance(position, dict) and 'x' in position:
                try:
                    pixel = project_point_to_2d(position, rotation_matrix, intrinsic_matrix, camera_location)
                    if pixel and 0 <= pixel[0] <= image_width and 0 <= pixel[1] <= image_height:
                        joints_2d.append(pixel)
                except:
                    continue
    
    # Fallback: use location if skeleton is missing
    if len(joints_2d) < 3 and 'location' in agent:
        try:
            center = project_point_to_2d(agent['location'], rotation_matrix, intrinsic_matrix, camera_location)
            if center:
                # Create a small circle around the agent location
                radius = 60
                joints_2d = [
                    [center[0] - radius, center[1] - radius],
                    [center[0] + radius, center[1] - radius],
                    [center[0] + radius, center[1] + radius],
                    [center[0] - radius, center[1] + radius]
                ]
        except:
            return None
    
    if len(joints_2d) < 3:
        return None
    
    # Calculate convex hull using scipy
    try:
        from scipy.spatial import ConvexHull
        points = np.array(joints_2d)
        hull = ConvexHull(points)
        hull_points = [joints_2d[i] for i in hull.vertices]
        return hull_points
    except:
        # Fallback: return bounding box if ConvexHull fails
        x_coords = [p[0] for p in joints_2d]
        y_coords = [p[1] for p in joints_2d]
        
        x_min = min(x_coords)
        y_min = min(y_coords)
        x_max = max(x_coords)
        y_max = max(y_coords)
        
        return [
            [x_min, y_min],
            [x_max, y_min],
            [x_max, y_max],
            [x_min, y_max]
        ]

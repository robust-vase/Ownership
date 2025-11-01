import tongsim as ts

import math

from .other_util import get_object_aabb

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


def quaternion_to_yaw(quat):
    """
    将四元数转换为yaw角度（绕Z轴旋转角度）
    
    Args:
        quat: 四元数对象 (x, y, z, w)
    
    Returns:
        float: yaw角度（弧度）
    """
    # 从四元数计算yaw角度
    # yaw = atan2(2*(w*z + x*y), 1 - 2*(y^2 + z^2))
    w = getattr(quat, 'w', 1.0)
    x = quat.x
    y = quat.y
    z = quat.z
    
    yaw = math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))
    return yaw


def calculate_agent_table_angle(agent, table_object, table_min=None, table_max=None):
    """
    计算人物朝向与桌子方向的夹角
    
    计算人物的朝向(yaw角度)与人物到桌子中心的连线方向之间的夹角。
    夹角越小，说明人物越正对着桌子。
    
    Args:
        agent: 人物对象（需要有 get_rotation() 和 get_location() 方法）
        table_object: 桌子对象（需要有 get_world_aabb() 方法）
        table_min: 桌子AABB最小点（可选，如果提供则不重新计算）
        table_max: 桌子AABB最大点（可选，如果提供则不重新计算）
    
    Returns:
        float: 夹角度数（0-180度），如果距离太近无法计算则返回 None
    
    Examples:
        >>> angle = calculate_agent_table_angle(agent, table)
        >>> if angle is not None and angle < 90:
        >>>     print("人物正对着桌子")
        >>> else:
        >>>     print("人物背对或侧对桌子")
    """
    # 获取人物的位置和朝向
    agent_rotation = agent.get_rotation()
    agent_position = agent.get_location()
    
    table_min, table_max = get_object_aabb(table_object)
    
    # 计算桌子中心位置
    table_center_x = (table_min.x + table_max.x) / 2
    table_center_y = (table_min.y + table_max.y) / 2
    
    # 计算从人物到桌子中心的向量
    dx = table_center_x - agent_position.x
    dy = table_center_y - agent_position.y
    distance_to_table = math.sqrt(dx**2 + dy**2)
    
    # 如果距离太近，无法准确计算角度
    if distance_to_table <= 0.001:
        return None
    
    # 归一化方向向量
    dx /= distance_to_table
    dy /= distance_to_table
    
    # 计算桌子方向的角度（相对于X轴）
    angle_to_table = math.atan2(dy, dx)
    
    # 获取人物朝向的yaw角度
    agent_yaw = quaternion_to_yaw(agent_rotation)
    
    # 计算人物朝向与桌子方向的夹角差
    angle_diff = angle_to_table - agent_yaw
    
    # 将角度差归一化到 [-π, π] 范围
    while angle_diff > math.pi:
        angle_diff -= 2 * math.pi
    while angle_diff < -math.pi:
        angle_diff += 2 * math.pi
    
    # 转换为角度（取绝对值，返回0-180度的夹角）
    angle_diff_deg = abs(math.degrees(angle_diff))
    
    return angle_diff_deg


def quaternion_angle_difference(quat1, quat2):
    """
    计算两个四元数之间的角度差异（度数）
    
    使用四元数点积计算两个旋转之间的最小角度差异。
    这个方法可以准确测量3D空间中的旋转偏差。
    
    Args:
        quat1: 第一个四元数（通常是当前旋转）
        quat2: 第二个四元数（通常是目标/期望旋转）
    
    Returns:
        float: 两个四元数之间的角度差异（度数，范围0-180）
    
    Examples:
        >>> current_rot = item_obj.get_rotation()
        >>> expected_rot = ts.Quaternion(1, 0, 0, 0)
        >>> angle_diff = quaternion_angle_difference(current_rot, expected_rot)
        >>> if angle_diff > 15:
        >>>     print("旋转偏差过大")
    """
    # 计算四元数点积
    dot_product = (quat1.w * quat2.w +
                  quat1.x * quat2.x +
                  quat1.y * quat2.y +
                  quat1.z * quat2.z)
    
    # 限制点积范围在[-1, 1]之间（避免浮点误差导致acos域错误）
    dot_product = max(-1.0, min(1.0, dot_product))
    
    # 计算角度（使用绝对值，因为我们只关心角度大小，不关心方向）
    angle_rad = 2 * math.acos(abs(dot_product))
    
    # 转换为度数
    angle_deg = math.degrees(angle_rad)
    
    return angle_deg

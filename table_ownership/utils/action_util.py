"""
动作工具模块 - 为人物生成随机动作

包含三种动作类型：
1. 挥手动作（向另一个人）
2. 伸手触摸物品（只能触摸自己的物品）
3. 指向物品（可以指向任意物品）
"""

import random
import math
import tongsim as ts

from .orientation_util import quaternion_to_yaw

# 检查动作是否执行成功
def check_action_success(action_result, print_info=False):
    """
    检查动作是否执行成功
    
    Args:
        action_result: do_action返回的结果
        print_info: 是否打印详细信息
    
    Returns:
        bool: True表示成功，False表示失败
    """
    if not action_result:
        if print_info:
            print("[CHECK] 动作返回值为空")
        return False
    
    if len(action_result) == 0:
        if print_info:
            print("[CHECK] 动作返回值列表为空")
        return False
    
    # 检查所有返回结果
    for result in action_result:
        if hasattr(result, 'status') and result.status == 'end' and result.error_code == 0:
            if print_info:
                print("[CHECK] 动作执行成功")
            return True
    
    if print_info:
        print("[CHECK] 动作执行失败")
    return False



def determine_hand_side(agent, item, print_info=False):
    """
    判断物品在人物的左边还是右边，决定使用哪只手
    
    Args:
        agent: 人物对象
        item: 物品对象
        print_info: 是否打印信息
    
    Returns:
        int: ts.LEFT_HAND 或 ts.RIGHT_HAND
    """
    try:
        # 获取人物和物品的位置
        agent_location = agent.get_location()
        item_location = item.get_location()
        
        # 获取人物的朝向（四元数）
        agent_rotation = agent.get_rotation()
        yaw = quaternion_to_yaw(agent_rotation)
        
        # 计算人物到物品的向量
        dx = item_location.x - agent_location.x
        dy = item_location.y - agent_location.y
        
        # 计算人物朝向的前向量
        forward_x = math.cos(yaw)
        forward_y = math.sin(yaw)
        
        # 计算人物朝向的右向量（顺时针旋转90度）
        right_x = math.sin(yaw)
        right_y = -math.cos(yaw)
        
        # 计算物品在人物右侧的投影（点积）
        dot_right = dx * right_x + dy * right_y
        
        # 如果投影为正，物品在右侧，使用右手；否则使用左手
        if dot_right > 0:
            hand = ts.RIGHT_HAND
            hand_name = "右手"
        else:
            hand = ts.LEFT_HAND
            hand_name = "左手"
        
        if print_info:
            print(f"[HAND] 物品 {item.id} 在人物 {agent.id} 的{'右' if dot_right > 0 else '左'}侧 (投影值: {dot_right:.2f})，使用{hand_name}")
        
        return hand
    
    except Exception as e:
        if print_info:
            print(f"[ERROR] 判断左右手失败: {e}，默认使用右手")
        return ts.RIGHT_HAND

def action_reach_item(agent, item, agent_status='standing', print_info=False, max_sitting_reach_distance=60.0):
    """
    执行伸手触摸物品动作序列
    
    根据人物状态执行不同的动作：
    - 站立状态：移动到物品附近 → 转向物品 → 伸手
    - 坐下状态：检查距离 → 如果距离合适则直接伸手（不移动、不转向）
    
    会自动判断物品在左边还是右边，选择合适的手
    
    Args:
        agent: 执行动作的人物对象
        item: 目标物品对象
        agent_status: 人物状态（'sitting' 或 'standing'）
        print_info: 是否打印信息
        max_sitting_reach_distance: 坐姿下最大伸手距离（cm），默认60cm
    
    Returns:
        dict: 动作执行结果 {
            'success': bool,
            'action_type': 'reach_item',
            'target_item_id': str,
            'hand_used': str,  # 'left' 或 'right'
            'error': str  # 如果失败
            'distance': float  # 人物与物品的距离（cm）
        }
    """
    try:
        item_location = item.get_location()
        agent_location = agent.get_location()
        
        # 计算人物与物品的距离
        dx = item_location.x - agent_location.x
        dy = item_location.y - agent_location.y
        distance = math.sqrt(dx*dx + dy*dy)
        
        # 判断使用哪只手
        hand = determine_hand_side(agent, item, print_info=print_info)
        hand_name = "左手" if hand == ts.LEFT_HAND else "右手"
        
        if agent_status == 'sitting':
            # 坐下状态：先检查距离是否在可伸手范围内
            if distance > max_sitting_reach_distance:
                if print_info:
                    print(f"[SKIP] {agent.id} (坐姿) 无法伸手触摸物品 {item.id} - 距离 {distance:.1f}cm 超过最大范围 {max_sitting_reach_distance}cm")
                return {
                    'success': False,
                    'action_type': 'reach_item',
                    'target_item_id': str(item.id),
                    'error': 'distance_too_far',
                    'distance': distance,
                    'agent_status': 'sitting',
                    'max_reach_distance': max_sitting_reach_distance
                }
            
            # 距离合适，直接伸手触摸，不移动不转向
            reach_result = agent.do_action(ts.action.HandReach(hand, item_location))
            reach_success = check_action_success(reach_result, print_info=print_info)
            
            if print_info:
                status_msg = "成功" if reach_success else "失败"
                print(f"[ACTION] {agent.id} (坐姿) 使用{hand_name}伸手触摸物品 {item.id} (距离:{distance:.1f}cm) - {status_msg}")
            
            return {
                'success': reach_success,
                'action_type': 'reach_item',
                'target_item_id': str(item.id),
                'hand_used': 'left' if hand == ts.LEFT_HAND else 'right',
                'agent_status': 'sitting',
                'distance': distance
            }
        else:
            # 站立状态：移动到物品附近，转向，然后伸手
            if print_info:
                print(f"[INFO] {agent.id} (站立) 开始移动到物品 {item.id} (初始距离:{distance:.1f}cm)")
            
            move_result = agent.do_action(ts.action.MoveToObject(object_id=item.id))
            move_success = check_action_success(move_result, print_info=print_info)
            
            if not move_success:
                if print_info:
                    print(f"[ERROR] {agent.id} 移动到物品 {item.id} 失败")
                return {
                    'success': False,
                    'action_type': 'reach_item',
                    'target_item_id': str(item.id),
                    'error': 'move_failed',
                    'agent_status': 'standing',
                    'distance': distance
                }
            
            # 移动后重新计算距离，检查是否在可伸手范围内
            agent_location_after_move = agent.get_location()
            dx_after = item_location.x - agent_location_after_move.x
            dy_after = item_location.y - agent_location_after_move.y
            distance_after_move = math.sqrt(dx_after*dx_after + dy_after*dy_after)
            
            if distance_after_move > max_sitting_reach_distance:
                if print_info:
                    print(f"[SKIP] {agent.id} (站立) 移动后距离 {distance_after_move:.1f}cm 仍超过最大伸手范围 {max_sitting_reach_distance}cm，跳过伸手")
                return {
                    'success': False,
                    'action_type': 'reach_item',
                    'target_item_id': str(item.id),
                    'error': 'distance_too_far_after_move',
                    'agent_status': 'standing',
                    'initial_distance': distance,
                    'distance_after_move': distance_after_move,
                    'max_reach_distance': max_sitting_reach_distance
                }
            
            if print_info:
                print(f"[INFO] {agent.id} 移动后距离: {distance_after_move:.1f}cm (可以伸手)")
            
            turn_result = agent.do_action(ts.action.TurnToObject(object_id=item.id))
            turn_success = check_action_success(turn_result, print_info=print_info)
            
            if not turn_success:
                if print_info:
                    print(f"[WARNING] {agent.id} 转向物品 {item.id} 失败，但继续伸手")
            
            reach_result = agent.do_action(ts.action.HandReach(hand, item_location))
            reach_success = check_action_success(reach_result, print_info=print_info)
            
            overall_success = move_success and reach_success
            
            if print_info:
                status_msg = "成功" if overall_success else "失败"
                print(f"[ACTION] {agent.id} (站立) 使用{hand_name}伸手触摸物品 {item.id} - {status_msg}")
            
            return {
                'success': overall_success,
                'action_type': 'reach_item',
                'target_item_id': str(item.id),
                'hand_used': 'left' if hand == ts.LEFT_HAND else 'right',
                'agent_status': 'standing',
                'move_success': move_success,
                'turn_success': turn_success,
                'reach_success': reach_success,
                'initial_distance': distance,
                'distance_after_move': distance_after_move
            }
    
    except Exception as e:
        if print_info:
            print(f"[ERROR] 伸手动作执行失败: {e}")
        return {
            'success': False,
            'action_type': 'reach_item',
            'error': str(e)
        }

# 执行指向物品动作序列
def action_point_at_item(agent, item, print_info=False):
    """
    执行指向物品动作序列
    
    会自动判断物品在左边还是右边，选择合适的手
    
    Args:
        agent: 执行动作的人物对象
        item: 目标物品对象
        print_info: 是否打印信息
    
    Returns:
        dict: 动作执行结果 {
            'success': bool,
            'action_type': 'point_at_item',
            'target_item_id': str,
            'hand_used': str,  # 'left' 或 'right'
            'error': str  # 如果失败
        }
    """
    try:
        item_location = item.get_location()
        
        # 判断使用哪只手
        hand = determine_hand_side(agent, item, print_info=print_info)
        hand_name = "左手" if hand == ts.LEFT_HAND else "右手"
        
        # 看向物品
        look_result = agent.do_action(ts.action.LookAtLocation(item_location))
        look_success = check_action_success(look_result, print_info=print_info)
        
        if not look_success:
            if print_info:
                print(f"[WARNING] {agent.id} 看向物品 {item.id} 失败，但继续指向")
        
        # 指向物品
        point_result = agent.do_action(ts.action.PointAtLocation(loc=item_location, which_hand=hand))
        point_success = check_action_success(point_result, print_info=print_info)
        
        overall_success = look_success and point_success
        
        if print_info:
            status_msg = "成功" if overall_success else "失败"
            print(f"[ACTION] {agent.id} 使用{hand_name}指向物品 {item.id} - {status_msg}")
        
        return {
            'success': overall_success,
            'action_type': 'point_at_item',
            'target_item_id': str(item.id),
            'hand_used': 'left' if hand == ts.LEFT_HAND else 'right',
            'look_success': look_success,
            'point_success': point_success
        }
    
    except Exception as e:
        if print_info:
            print(f"[ERROR] 指向动作执行失败: {e}")
        return {
            'success': False,
            'action_type': 'point_at_item',
            'error': str(e)
        }


def generate_random_action_for_agent(agent, agents, agent_features_list, 
                                     all_spawned_items, item_owners_list, item_features_list,
                                     action_probability=0.7,
                                     allow_point_at_item=True,
                                     print_info=False):
    """
    为单个人物随机生成并执行一个动作
    
    动作类型及条件：
    1. 伸手触摸 (reach_item): 需要有自己的物品（owner为自己）
    2. 指向 (point_at_item): 可以指向任意物品（受allow_point_at_item参数控制）
    
    Args:
        agent: 人物对象
        agents: 所有人物列表
        agent_features_list: 人物特征列表
        all_spawned_items: 所有物品列表
        item_owners_list: 物品所有者ID列表
        item_features_list: 物品特征列表
        action_probability: 生成动作的概率（0.0-1.0）
        allow_point_at_item: 是否允许使用point_at_item动作
        print_info: 是否打印详细信息
    
    Returns:
        dict: 动作结果，如果不执行动作则返回 None
    """
    # 根据概率决定是否执行动作
    if random.random() > action_probability:
        if print_info:
            print(f"[INFO] {agent.id} 跳过动作生成（概率判断）")
        return None
    
    agent_id = str(agent.id)
    
    # 获取当前agent的状态
    agent_status = 'standing'  # 默认站立
    agent_index = agents.index(agent) if agent in agents else -1
    if agent_index >= 0 and agent_index < len(agent_features_list):
        agent_status = agent_features_list[agent_index].get('status', 'standing')
    
    # 收集可用的动作选项
    available_actions = []
    
    # ========== 检查伸手触摸动作是否可用 ==========
    own_items = []
    for i, owner_id in enumerate(item_owners_list):
        if owner_id == agent_id:
            own_items.append((all_spawned_items[i], item_features_list[i]))
    
    # 如果是坐姿，需要过滤掉距离太远的物品
    if own_items and agent_status == 'sitting':
        max_reach_distance = 60.0  # 坐姿最大伸手距离（cm）
        agent_location = agent.get_location()
        
        reachable_items = []
        for item, features in own_items:
            item_location = item.get_location()
            dx = item_location.x - agent_location.x
            dy = item_location.y - agent_location.y
            distance = math.sqrt(dx*dx + dy*dy)
            
            if distance <= max_reach_distance:
                reachable_items.append((item, features))
                if print_info:
                    print(f"[INFO] {agent.id} (坐姿) 可以够到物品 {item.id} (距离: {distance:.1f}cm)")
            else:
                if print_info:
                    print(f"[INFO] {agent.id} (坐姿) 无法够到物品 {item.id} (距离: {distance:.1f}cm > {max_reach_distance}cm)")
        
        own_items = reachable_items
    
    if own_items:
        available_actions.append(('reach_item', own_items))
        if print_info:
            status_str = f" (坐姿，距离<=60cm)" if agent_status == 'sitting' else ""
            print(f"[INFO] {agent.id} 可执行伸手动作，可触摸物品数量: {len(own_items)}{status_str}")
    
    # ========== 检查指向动作是否可用 ==========
    if all_spawned_items and allow_point_at_item:
        available_actions.append(('point_at_item', all_spawned_items))
        if print_info:
            print(f"[INFO] {agent.id} 可执行指向动作，可指向物品数量: {len(all_spawned_items)}")
    elif not allow_point_at_item and print_info:
        print(f"[INFO] {agent.id} 指向动作被禁用（已有其他人物使用）")
    
    # 如果没有可用动作，返回None
    if not available_actions:
        if print_info:
            print(f"[WARNING] {agent.id} 没有可用的动作")
        return None
    
    # 随机选择一个动作类型
    action_type, targets = random.choice(available_actions)
    
    # 执行对应的动作
    if action_type == 'reach_item':
        target_item, _ = random.choice(targets)
        result = action_reach_item(agent, target_item, agent_status=agent_status, print_info=print_info)
        
    elif action_type == 'point_at_item':
        target_item = random.choice(targets)
        result = action_point_at_item(agent, target_item, print_info=print_info)
    
    else:
        return None
    
    return result


def generate_actions_for_all_agents(agents, agent_features_list,
                                    all_spawned_items, item_owners_list, item_features_list,
                                    action_probability=0.7,
                                    print_info=False):
    """
    为所有人物生成随机动作，并更新features列表
    
    规则：
    - 只允许一个人物使用point_at_item动作
    - 其他人物只能使用reach_item动作
    
    Args:
        agents: 所有人物列表
        agent_features_list: 人物特征列表（会被原地修改）
        all_spawned_items: 所有物品列表
        item_owners_list: 物品所有者ID列表
        item_features_list: 物品特征列表
        action_probability: 生成动作的概率
        print_info: 是否打印详细信息
    
    Returns:
        dict: 动作统计信息 {
            'total_agents': int,
            'action_count': int,
            'action_success_count': int,
            'action_failed_count': int,
            'reach_item_count': int,
            'point_at_item_count': int,
            'no_action_count': int
        }
    """
    if print_info:
        print(f"\n{'='*60}")
        print(f"[INFO] 开始为 {len(agents)} 个人物生成随机动作")
        print(f"[INFO] 动作生成概率: {action_probability}")
        print(f"[INFO] 规则：只允许一个人物使用point_at_item动作")
        print(f"{'='*60}\n")
    
    stats = {
        'total_agents': len(agents),
        'action_count': 0,
        'action_success_count': 0,
        'action_failed_count': 0,
        'reach_item_count': 0,
        'point_at_item_count': 0,
        'no_action_count': 0
    }
    
    # 验证列表长度一致性
    if len(agents) != len(agent_features_list):
        print(f"[ERROR] agents和agent_features_list长度不一致: {len(agents)} vs {len(agent_features_list)}")
        return stats
    
    # 标记是否已有人使用point_at_item
    point_at_item_used = False
    
    # 为每个人物生成动作
    for i, agent in enumerate(agents):
        if print_info:
            print(f"\n[PROCESSING] 处理人物 {i+1}/{len(agents)}: {agent.id}")
        
        # 如果已有人使用point_at_item，禁止其他人使用
        allow_point_at_item = not point_at_item_used
        
        # 生成动作
        action_result = generate_random_action_for_agent(
            agent=agent,
            agents=agents,
            agent_features_list=agent_features_list,
            all_spawned_items=all_spawned_items,
            item_owners_list=item_owners_list,
            item_features_list=item_features_list,
            action_probability=action_probability,
            allow_point_at_item=allow_point_at_item,
            print_info=print_info
        )
        
        # 更新features
        if action_result:
            action_type = action_result['action_type']
            success = action_result.get('success', False)
            
            # 将动作信息添加到features中
            if action_type == 'reach_item':
                agent_features_list[i]['action'] = 'reach_item'
                agent_features_list[i]['reach_item_id'] = action_result['target_item_id']
                agent_features_list[i]['action_success'] = success
                
                if 'hand_used' in action_result:
                    agent_features_list[i]['hand_used'] = action_result['hand_used']
                
                stats['reach_item_count'] += 1
                stats['action_count'] += 1
                
                if success:
                    stats['action_success_count'] += 1
                else:
                    stats['action_failed_count'] += 1
                
            elif action_type == 'point_at_item':
                agent_features_list[i]['action'] = 'point_at_item'
                agent_features_list[i]['point_item_id'] = action_result['target_item_id']
                agent_features_list[i]['action_success'] = success
                
                if 'hand_used' in action_result:
                    agent_features_list[i]['hand_used'] = action_result['hand_used']
                
                stats['point_at_item_count'] += 1
                stats['action_count'] += 1
                point_at_item_used = True  # 标记已使用
                
                if success:
                    stats['action_success_count'] += 1
                else:
                    stats['action_failed_count'] += 1
            
            if print_info:
                status_msg = "成功" if success else "失败"
                print(f"[SUCCESS] {agent.id} 执行了 {action_type} 动作 - {status_msg}")
        else:
            # 没有执行动作
            agent_features_list[i]['action'] = 'none'
            agent_features_list[i]['action_success'] = False
            stats['no_action_count'] += 1
            
            if print_info:
                print(f"[INFO] {agent.id} 未执行动作")
    
    # 打印统计信息
    if print_info:
        print(f"\n{'='*60}")
        print(f"[INFO] 动作生成完成")
        print(f"{'='*60}")
        print(f"  总人物数: {stats['total_agents']}")
        print(f"  执行动作数: {stats['action_count']}")
        print(f"    - 成功: {stats['action_success_count']}")
        print(f"    - 失败: {stats['action_failed_count']}")
        print(f"  动作类型统计:")
        print(f"    - 伸手触摸: {stats['reach_item_count']}")
        print(f"    - 指向: {stats['point_at_item_count']}")
        print(f"  未执行动作数: {stats['no_action_count']}")
        print(f"{'='*60}\n")
    
    return stats

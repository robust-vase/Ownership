
import tongsim as ts
import random
import math
import re
import time

from configs.agent_config import (
    AGENT_BLUEPRINT_MAPPING,
    BLUEPRINT_TO_TRAIT,
    get_agent_trait,
    extract_base_agent_id
)

# Import utility functions from other_util.py
from .other_util import (
    fix_aabb_bounds,
    get_object_aabb,
    check_position_in_bbox,
    determine_object_side,
    check_item_overlap
)

from .entity_util import (
    filter_objects_by_type,
    filter_objects_info_by_type
)

# Import JSON utility functions
from .json_util import add_entities_to_json

# Import orientation utility functions
from .orientation_util import calculate_agent_table_angle

# 生成人物配置
def generate_agent_configuration(num_agents=None, agent_blueprints=None, agent_sides=None, agent_is_sit=None, agent_traits=None,
                                 side_probabilities=[0.25, 0.25, 0.25, 0.25], sit_probability=0.5):
    """
    生成人物配置（优化版）
    
    优先级：agent_blueprints > agent_traits > num_agents > 全随机(2-4人)
    
    Args:
        num_agents: 人物数量
        agent_blueprints: 指定的人物蓝图列表（最高优先级）
        agent_sides: 指定的人物方位列表
        agent_is_sit: 指定的人物是否坐下列表
        agent_traits: 人物特性列表 ['girl', 'boy', 'woman', 'grandpa', 'man']
        side_probabilities: 方位概率 [front, back, left, right]
        sit_probability: 坐下概率
    
    Returns:
        tuple: (agent_blueprints, agent_sides, agent_is_sit, agent_traits)
    """
    from configs.agent_config import AGENT_BLUEPRINT_MAPPING, BLUEPRINT_TO_TRAIT
    
    side_mapping = ['front', 'back', 'left', 'right']
    use_random = False  # 是否使用全随机生成
    
    # ========== 第一优先级：使用 agent_blueprints ==========
    if agent_blueprints is not None:
        # 检查蓝图是否有重复
        if len(agent_blueprints) != len(set(agent_blueprints)):
            print("[WARNING] agent_blueprints 存在重复蓝图，将使用全随机生成")
            use_random = True
        else:
            num_agents = len(agent_blueprints)
            
            # 验证长度匹配
            if agent_sides is not None and len(agent_sides) != num_agents:
                print(f"[WARNING] agent_sides 长度({len(agent_sides)})与 agent_blueprints({num_agents})不匹配，将使用全随机生成")
                use_random = True
            elif agent_is_sit is not None and len(agent_is_sit) != num_agents:
                print(f"[WARNING] agent_is_sit 长度({len(agent_is_sit)})与 agent_blueprints({num_agents})不匹配，将使用全随机生成")
                use_random = True
            elif agent_traits is not None and len(agent_traits) != num_agents:
                print(f"[WARNING] agent_traits 长度({len(agent_traits)})与 agent_blueprints({num_agents})不匹配，将使用全随机生成")
                use_random = True
            else:
                # 根据蓝图反向生成 traits
                if agent_traits is None:
                    agent_traits = []
                    for bp in agent_blueprints:
                        trait = BLUEPRINT_TO_TRAIT.get(bp, 'unknown')
                        if trait == 'unknown':
                            print(f"[WARNING] 蓝图 {bp} 不在映射表中")
                        agent_traits.append(trait)
    
    # ========== 第二优先级：使用 agent_traits 生成蓝图 ==========
    if not use_random and agent_blueprints is None and agent_traits is not None:
        # 确定人物数量
        if num_agents is None:
            num_agents = len(agent_traits)
        elif num_agents != len(agent_traits):
            print(f"[WARNING] num_agents({num_agents})与 agent_traits 长度({len(agent_traits)})不匹配，将使用全随机生成")
            use_random = True
        
        if not use_random:
            # 验证长度匹配
            if agent_sides is not None and len(agent_sides) != num_agents:
                print(f"[WARNING] agent_sides 长度({len(agent_sides)})与 num_agents({num_agents})不匹配，将使用全随机生成")
                use_random = True
            elif agent_is_sit is not None and len(agent_is_sit) != num_agents:
                print(f"[WARNING] agent_is_sit 长度({len(agent_is_sit)})与 num_agents({num_agents})不匹配，将使用全随机生成")
                use_random = True
            else:
                # 检查 traits 的可用性（统计每种类型的数量）
                trait_counts = {}
                for trait in agent_traits:
                    trait_counts[trait] = trait_counts.get(trait, 0) + 1
                
                # 验证每种类型是否有足够的蓝图
                for trait, count in trait_counts.items():
                    if trait not in AGENT_BLUEPRINT_MAPPING:
                        print(f"[WARNING] trait '{trait}' 不在支持列表中，将使用全随机生成")
                        use_random = True
                        break
                    if count > len(AGENT_BLUEPRINT_MAPPING[trait]):
                        print(f"[WARNING] trait '{trait}' 需要 {count} 个但只有 {len(AGENT_BLUEPRINT_MAPPING[trait])} 个蓝图，将使用全随机生成")
                        use_random = True
                        break
                
                # 根据 traits 随机生成蓝图
                if not use_random:
                    agent_blueprints = []
                    available_blueprints = {trait: AGENT_BLUEPRINT_MAPPING[trait].copy() for trait in set(agent_traits)}
                    
                    for trait in agent_traits:
                        blueprint = random.choice(available_blueprints[trait])
                        agent_blueprints.append(blueprint)
                        available_blueprints[trait].remove(blueprint)  # 避免重复
    
    # ========== 第三优先级/全随机：根据 num_agents 或完全随机生成 ==========
    if use_random or agent_blueprints is None:
        # 确定人物数量
        if num_agents is None:
            num_agents = random.randint(2, 4)
        
        # 创建可用蓝图池
        available_blueprints = []
        for trait, blueprints in AGENT_BLUEPRINT_MAPPING.items():
            available_blueprints.extend([(trait, bp) for bp in blueprints])
        
        if len(available_blueprints) < num_agents:
            raise ValueError(f"[ERROR] 可用蓝图数量({len(available_blueprints)})不足以生成 {num_agents} 个人物")
        
        # 随机选择（不重复）
        selected = random.sample(available_blueprints, num_agents)
        agent_traits = [item[0] for item in selected]
        agent_blueprints = [item[1] for item in selected]
    
    # ========== 生成方位和坐下配置 ==========
    if agent_sides is None:
        agent_sides = random.choices(side_mapping, weights=side_probabilities, k=num_agents)
    
    if agent_is_sit is None:
        agent_is_sit = [random.random() < sit_probability for _ in range(num_agents)]
    
    return agent_blueprints, agent_sides, agent_is_sit, agent_traits


# ============== 人物生成优化 =============
# 生成并放置人物
def generate_and_spawn_agents(ue, table_object, room_bound, nearby_objects,
                              agent_blueprints, agent_sides, agent_is_sit, agent_traits,
                              min_distance=10, max_distance=90, min_agent_distance=60, max_agent_distance=300,
                              safe_margin=15, max_chair_adjust_attempts=8, chair_move_step=5.0, print_info=False):
    """
    直接在场景中创建人物（优化版本，接收已配置好的人物参数）
    
    Args:
        ue: TongSim实例
        table_object: 桌子对象
        room_bound: 房间边界
        nearby_objects: 附近的物体列表
        agent_blueprints: 人物蓝图列表（必需）
        agent_sides: 人物方位列表（必需）
        agent_is_sit: 人物是否坐下列表（必需）
        agent_traits: 人物特性列表（必需）
        min_distance: 距离桌子的最小距离
        max_distance: 距离桌子的最大距离
        min_agent_distance: 人物之间的最小距离（默认60cm）
        max_agent_distance: 人物之间的最大距离（默认300cm）
        safe_margin: 边界的安全边距
        max_chair_adjust_attempts: 椅子调整最大尝试次数
        chair_move_step: 椅子每次移动的步长
        print_info: 是否打印详细信息
    
    Returns:
        tuple: (agents_complete_info, nearby_objects)
            - agents_complete_info: 人物完整信息字典列表，每个元素包含完整的人物信息
            - nearby_objects: 更新后的附近物体列表（椅子可能被替换，由于list是可变对象，实际上会自动更新）
    """
    
    # 验证输入参数
    if not all([agent_blueprints, agent_sides, agent_is_sit, agent_traits]):
        raise ValueError("[ERROR] agent_blueprints, agent_sides, agent_is_sit, agent_traits 都是必需参数")
    
    if not (len(agent_blueprints) == len(agent_sides) == len(agent_is_sit) == len(agent_traits)):
        raise ValueError("[ERROR] 所有人物配置列表的长度必须一致")
    
    # 准备环境信息
    # 从附近物体中筛选出椅子和沙发（可坐下的物体），并添加标记
    existed_chairs_info = filter_objects_info_by_type(objects_info_list=nearby_objects, type_file_path='./ownership/object/chair.txt')
    existed_sofas_info = filter_objects_info_by_type(objects_info_list=nearby_objects, type_file_path='./ownership/object/sofa.txt')
    existed_carpet_info = filter_objects_info_by_type(objects_info_list=nearby_objects, type_file_path='./ownership/object/carpet.txt')
    
    # 为椅子和沙发添加可坐标记
    for chair_info in existed_chairs_info:
        chair_info['is_sittable'] = True
        chair_info['movable'] = True
        chair_info['matched'] = False
    
    for sofa_info in existed_sofas_info:
        sofa_info['is_sittable'] = True
        sofa_info['movable'] = False
        sofa_info['matched'] = False
    
    if print_info:
        print(f"[INFO] 找到 {len(existed_chairs_info)} 把椅子, {len(existed_sofas_info)} 个沙发")
    
    # 获取桌子的世界AABB边界
    table_min, table_max = get_object_aabb(table_object)
    
    x_min, y_min, z_min, x_max, y_max, z_max = room_bound
    
    # 提取地毯ID集合（用于过滤碰撞检测）
    carpet_ids = {carpet_info['id'] for carpet_info in existed_carpet_info}
    
    # 过滤出非地毯物品用于碰撞检测
    nearby_object_bounds = [
        obj_info for obj_info in nearby_objects 
        if obj_info['id'] not in carpet_ids
    ]
    
    # 第三步：开始生成人物
    agents_complete_info = []  # 存储完整的人物信息字典
    agent_positions = []
    
    # 辅助函数：创建人物完整信息字典
    def create_agent_complete_info(agent, trait, status, chair_id=None):
        """创建人物的完整信息字典"""
        location = agent.get_location()
        rotation = agent.get_rotation()
        
        complete_info = {
            'id': agent.id,
            'base_id': extract_base_agent_id(agent.id),
            'type': trait,
            'location': {
                'x': location.x,
                'y': location.y,
                'z': location.z
            },
            'rotation': {
                'x': rotation.x,
                'y': rotation.y,
                'z': rotation.z,
                'w': rotation.w
            },
            'entity_size': agent.get_scale(),
            'entity': agent,
            'direction': determine_object_side(agent, table_object),
            'status': status
        }
        
        # 如果是坐着的，添加椅子ID
        if chair_id is not None:
            complete_info['chair_id'] = chair_id
        
        return complete_info
    
    # 分类：需要坐下的和需要站立的
    sitting_agents = []
    standing_agents = []
    for i, (blueprint, side, should_sit, trait) in enumerate(zip(agent_blueprints, agent_sides, agent_is_sit, agent_traits)):
        if should_sit:
            sitting_agents.append((i, blueprint, side, trait))
        else:
            standing_agents.append((i, blueprint, side, trait))
    
    # 处理需要坐下的人物
    for agent_idx, blueprint, side, trait in sitting_agents:
        # 查找同方向且未匹配的可坐物体
        candidate_sit_objects = [
            obj_info for obj_info in nearby_objects 
            if obj_info.get('is_sittable') and obj_info['direction'] == side and not obj_info.get('matched', False)
        ]
        
        if not candidate_sit_objects:
            print(f"[PROCESSING] 人物 {agent_idx} 需要坐下但未找到合适座位，转为站立")
            standing_agents.append((agent_idx, blueprint, side, trait))
            continue
        
        # 随机选择一个座位
        selected_seat_info = random.choice(candidate_sit_objects)
        
        # 尝试让人物坐下
        agent, updated_seat_info = _try_sit_on_chair(
            ue=ue,
            seat_info=selected_seat_info,
            table_object=table_object,
            blueprint=blueprint,
            agent_idx=agent_idx,
            nearby_object_bounds=nearby_object_bounds,
            max_attempts=max_chair_adjust_attempts if selected_seat_info['movable'] else 1,
            move_step=chair_move_step,
            print_info=print_info
        )
        
        if agent:
            # 创建完整信息字典
            agent_complete_info = create_agent_complete_info(
                agent=agent,
                trait=trait,
                status="sitting",
                chair_id=str(updated_seat_info['id'])
            )
            agents_complete_info.append(agent_complete_info)
            
            # 记录位置
            agent_pos = agent.get_location()
            agent_positions.append(agent_pos)
            
            # 更新座位信息的matched字段（记录坐在上面的agent id）
            updated_seat_info['matched'] = agent.id
            
        else:
            # 如果人物生成失败，转为站立
            if print_info:
                print(f"[PROCESSING] 人物 {agent_idx} 坐下失败，转为站立")
            standing_agents.append((agent_idx, blueprint, side, trait))
    
    # 处理需要站立的人物
    for agent_idx, blueprint, side, trait in standing_agents:
        agent_placed = False
        attempts = 0
        max_attempts = 1000000
        
        while not agent_placed and attempts < max_attempts:
            attempts += 1
            
            # 根据选择的侧边计算基础位置
            if side == 'front':
                base_x = random.uniform(table_min.x, table_max.x)
                base_y = table_max.y
                direction = ts.Vector3(0, 1, 0)
            elif side == 'back':
                base_x = random.uniform(table_min.x, table_max.x)
                base_y = table_min.y
                direction = ts.Vector3(0, -1, 0)
            elif side == 'left':
                base_x = table_max.x
                base_y = random.uniform(table_min.y, table_max.y)
                direction = ts.Vector3(1, 0, 0)
            else:  # right
                base_x = table_min.x
                base_y = random.uniform(table_min.y, table_max.y)
                direction = ts.Vector3(-1, 0, 0)
            
            distance = random.uniform(min_distance, max_distance)
            agent_x = base_x + direction.x * distance
            agent_y = base_y + direction.y * distance
            agent_z = z_min
            agent_position = ts.Vector3(agent_x, agent_y, agent_z)
            
            # 检查是否与附近物体重叠
            too_close_to_object = False
            for obj_info in nearby_object_bounds:
                if check_position_in_bbox(agent_position, obj_info['entity_min'], obj_info['entity_max'], 
                                         safe_margin=safe_margin, check_z_axis=False):
                    too_close_to_object = True
                    break
            if too_close_to_object:
                continue
            
            # 检查位置是否在房间边界内
            if not check_position_in_bbox(agent_position, 
                                         ts.Vector3(x_min, y_min, z_min),
                                         ts.Vector3(x_max, y_max, z_max),
                                         safe_margin=-safe_margin, check_z_axis=False):
                continue
            
            # 检查与已有人物的距离（既不能太近也不能太远）
            too_close_to_other_agent = False
            too_far_from_other_agents = False
            
            for existing_pos in agent_positions:
                distance_to_other = math.sqrt(
                    (agent_position.x - existing_pos.x)**2 + 
                    (agent_position.y - existing_pos.y)**2 + 
                    (agent_position.z - existing_pos.z)**2
                )
                # 检查是否太近
                if distance_to_other < min_agent_distance:
                    too_close_to_other_agent = True
                    break
                # 检查是否太远
                if distance_to_other > max_agent_distance:
                    too_far_from_other_agents = True
                    break
            
            if too_close_to_other_agent or too_far_from_other_agents:
                continue
            
            # 生成站立的人物
            try:
                random_position = ue.spatical_manager.get_nearest_nav_position(target_location=agent_position)
                random_position.z = random_position.z + 70
                
                agent = ue.spawn_agent(
                    blueprint=blueprint,
                    location=random_position,
                    desired_name=f"{blueprint}_{agent_idx}",
                    quat=None,
                    scale=None
                )
                
                # 计算朝向
                table_target_x = random.uniform(table_min.x, table_max.x)
                table_target_y = random.uniform(table_min.y, table_max.y)
                towards_position = ts.Vector3(table_target_x, table_target_y, table_max.z)
                
                agent.do_action(ts.action.MoveToLocation(loc=agent_position))
                agent.do_action(ts.action.TurnToLocation(loc=towards_position))
                
                # 创建完整信息字典
                agent_complete_info = create_agent_complete_info(
                    agent=agent,
                    trait=trait,
                    status='standing'
                )
                agents_complete_info.append(agent_complete_info)
                
                agent_positions.append(agent_position)
                agent_placed = True
                
                if print_info:
                    print(f"[PROCESSING] 人物 {agent_idx} 已生成并站在位置 {agent_position}")
                    
            except Exception as e:
                print(f"[ERROR] 生成站立人物 {agent_idx} 时出错: {e}")
                continue
        
        if not agent_placed:
            print(f"[WARNING] 无法为人物 {agent_idx} 找到合适的站立位置")
    
    # 返回完整信息列表和更新后的nearby_objects
    # 注意：由于nearby_objects是可变对象(list)，内部的修改会自动反映到外部
    # 但为了代码清晰性，我们仍然返回它
    return agents_complete_info, nearby_objects


def _try_sit_on_chair(ue, seat_info, table_object, blueprint, agent_idx, nearby_object_bounds, 
                     max_attempts, move_step, print_info):
    """
    尝试让人物坐在座位上，如果失败则调整座位位置（仅针对可移动座位）并重新创建人物重试
    
    Args:
        ue: TongSim实例
        seat_info: 座位完整信息字典（包含id, base_id, location, rotation, direction, movable等）
        table_object: 桌子对象
        blueprint: 人物蓝图
        agent_idx: 人物索引
        nearby_object_bounds: 附近物体的完整信息列表（用于碰撞检测）
        max_attempts: 最大尝试次数
        move_step: 座位每次移动的步长
        print_info: 是否打印信息
    
    Returns:
        tuple: (agent_object, status, updated_seat_info)
            - agent_object: 人物对象或None
            - status: 人物状态或None
            - updated_seat_info: 更新后的座位信息字典（位置可能已改变）
    """
    
    # 获取桌子的世界AABB边界
    table_min, table_max = get_object_aabb(table_object)

    # 从座位信息中提取必要数据
    seat_id = seat_info['id']
    seat_side = seat_info['direction']
    movable = seat_info['movable']
    
    seat_entity = seat_info['entity']
    
    # 从seat_info中获取位置信息
    seat_location = ts.Vector3(
        seat_info['location']['x'],
        seat_info['location']['y'],
        seat_info['location']['z']
    )
    
    # 保存座位的原始位置（用于失败时恢复）
    original_location = ts.Vector3(seat_location.x, seat_location.y, seat_location.z)
    
    # 保存座位的原始AABB（用于碰撞检测）
    original_seat_min = seat_info['entity_min']
    original_seat_max = seat_info['entity_max']
    
    # 临时变量：跟踪当前尝试的位置和AABB（不直接修改seat_info）
    current_seat_location = ts.Vector3(seat_location.x, seat_location.y, seat_location.z)
    current_seat_min = ts.Vector3(original_seat_min.x, original_seat_min.y, original_seat_min.z)
    current_seat_max = ts.Vector3(original_seat_max.x, original_seat_max.y, original_seat_max.z)
    
    agent = None  # 当前尝试的人物对象
    seat_type = "椅子" if movable else "沙发"
    
    for attempt in range(max_attempts):
        # 第一步：获取座位位置附近的导航点并生成人物
        try:
            spawn_position = ue.spatical_manager.get_nearest_nav_position(target_location=current_seat_location)
            spawn_position.z = spawn_position.z + 70
            
            # 生成人物
            agent = ue.spawn_agent(
                blueprint=blueprint,
                location=spawn_position,
                desired_name=f"{blueprint}_{agent_idx}",
                quat=None,
                scale=None
            )
            
            # 第二步：执行坐下动作
            agent.do_action(ts.action.MoveToObject(object_id=seat_id, speed=1000))
            sit_result = agent.do_action(ts.action.SitDownToObject(object_id=seat_id))
            
            # 第三步：检查坐下是否成功
            sit_success = False
            if sit_result and len(sit_result) > 0:
                for result in sit_result:
                    if hasattr(result, 'status') and result.status == 'end' and result.error_code == 0:
                        sit_success = True
                        break
            
            if sit_success:
                # 坐下成功，检查人物是否面向桌子
                angle_diff_deg = calculate_agent_table_angle(agent=agent, table_object=table_object)
                
                if angle_diff_deg is not None and angle_diff_deg > 90.0:
                    # 人物背对桌子或侧对桌子，放弃该座位
                    if print_info:
                        print(f"[WARNING] 人物 {agent_idx} 坐在{seat_type}上但未面向桌子 (夹角: {angle_diff_deg:.1f}度)，放弃该座位")
                    
                    # 删除人物
                    ue.destroy_entity(agent.id)
                    agent = None
                    
                    # 恢复座位到原始位置（如果可移动且位置已改变）
                    if movable and (current_seat_location.x != original_location.x or 
                                   current_seat_location.y != original_location.y or 
                                   current_seat_location.z != original_location.z):
                        seat_entity.set_location(original_location)
                        if print_info:
                            print(f"[INFO] 座位已恢复到原始位置")
                    
                    return None, seat_info
                
                # 坐下成功且朝向正确 - 只在这里更新seat_info
                if print_info:
                    angle_str = f"(夹角: {angle_diff_deg:.1f}度)" if angle_diff_deg is not None else "(距离太近，跳过朝向检查)"
                    print(f"[SUCCESS] 人物 {agent_idx} 成功坐在{seat_type}上并面向桌子 {angle_str}, 尝试次数: {attempt + 1}")
                
                # ✅ 只在成功时更新座位信息
                seat_info['is_sit'] = True
                
                # 获取当前座位的最新信息
                current_loc = seat_entity.get_location()
                current_rot = seat_entity.get_rotation()
                entity_min, entity_max = get_object_aabb(seat_entity)
                
                seat_info['location'] = {
                    'x': current_loc.x,
                    'y': current_loc.y,
                    'z': current_loc.z
                }
                seat_info['rotation'] = {
                    'x': current_rot.x,
                    'y': current_rot.y,
                    'z': current_rot.z,
                    'w': current_rot.w
                }
                seat_info['entity_min'] = entity_min
                seat_info['entity_max'] = entity_max
                
                return agent, seat_info
            
            else:
                # 坐下失败
                if print_info:
                    print(f"[INFO] 人物 {agent_idx} 第 {attempt + 1} 次坐在{seat_type}上失败")
                
                # 删除人物
                ue.destroy_entity(agent.id)
                agent = None
                
                # 如果不可移动（沙发）或是最后一次尝试，直接返回失败
                if not movable or attempt == max_attempts - 1:
                    if not movable:
                        if print_info:
                            print(f"[WARNING] 人物 {agent_idx} 无法坐在沙发上（沙发不可移动），放弃该人物")
                    else:
                        if print_info:
                            print(f"[WARNING] 人物 {agent_idx} 经过 {max_attempts} 次尝试仍无法坐下，放弃该人物")
                        # 恢复座位到原始位置
                        if current_seat_location.x != original_location.x or current_seat_location.y != original_location.y:
                            seat_entity.set_location(original_location)
                            if print_info:
                                print(f"[INFO] 座位已恢复到原始位置")
                    
                    return None, seat_info
                
                # 第四步：调整座位位置（仅对可移动的座位）
                # 根据方向调整临时位置和AABB变量
                if seat_side == 'left':
                    current_seat_location.x += move_step
                    current_seat_min.x += move_step
                    current_seat_max.x += move_step
                elif seat_side == 'right':
                    current_seat_location.x -= move_step
                    current_seat_min.x -= move_step
                    current_seat_max.x -= move_step
                elif seat_side == 'front':
                    current_seat_location.y += move_step
                    current_seat_min.y += move_step
                    current_seat_max.y += move_step
                elif seat_side == 'back':
                    current_seat_location.y -= move_step
                    current_seat_min.y -= move_step
                    current_seat_max.y -= move_step
                
                # 第五步：检查新位置是否与nearby_objects冲突
                has_collision = False
                for obj_info in nearby_object_bounds:
                    try:
                        # 跳过自己
                        if obj_info['id'] == seat_id:
                            continue
                        
                        # 使用预先计算好的边界
                        obj_min = obj_info['entity_min']
                        obj_max = obj_info['entity_max']
                        
                        # 检测碰撞（使用调整后的AABB）
                        if check_item_overlap(current_seat_min, current_seat_max, obj_min, obj_max, 
                                            safe_margin=1.0, check_z_axis=False):
                            has_collision = True
                            if print_info:
                                print(f"[INFO] 座位调整时与物品 {obj_info['id']} 冲突，将恢复座位原位")
                            break
                    except Exception as e:
                        if print_info:
                            print(f"[DEBUG] 检测物体时出错（可能已删除）: {e}")
                        continue
                
                # 如果有碰撞，恢复座位到原始位置并返回失败
                if has_collision:
                    if print_info:
                        print(f"[INFO] 检测到碰撞，恢复座位到原始位置")
                    
                    seat_entity.set_location(original_location)
                    
                    return None, seat_info
                
                # 第六步：没有碰撞，移动座位到新位置
                try:
                    seat_entity.set_location(current_seat_location)
                    
                    if print_info:
                        print(f"[INFO] 第 {attempt + 1} 次调整：座位移至新位置 ({current_seat_location.x:.2f}, {current_seat_location.y:.2f}, {current_seat_location.z:.2f})")
                except Exception as e:
                    print(f"[ERROR] 移动座位失败: {e}")
                    
                    # 恢复座位到原始位置
                    seat_entity.set_location(original_location)
                    
                    return None, seat_info
                    
        except Exception as e:
            print(f"[ERROR] 尝试坐下时出错: {e}")
            # 如果人物已创建，删除人物
            if agent:
                try:
                    ue.destroy_entity(agent.id)
                    agent = None
                except:
                    pass
            
            # 如果是最后一次尝试，返回失败
            if attempt == max_attempts - 1:
                if print_info:
                    print(f"[WARNING] 人物 {agent_idx} 经过 {max_attempts} 次尝试后出错，放弃该人物")
                
                # 恢复座位到原始位置
                if movable and (current_seat_location.x != original_location.x or current_seat_location.y != original_location.y):
                    seat_entity.set_location(original_location)
                    if print_info:
                        print(f"[INFO] 座位已恢复到原始位置")
                
                return None, seat_info
            continue
    
    # 所有尝试都失败，恢复座位到原始位置
    if movable and (current_seat_location.x != original_location.x or current_seat_location.y != original_location.y):
        seat_entity.set_location(original_location)
        if print_info:
            print(f"[INFO] 所有尝试失败，座位已恢复到原始位置")
    
    return None, seat_info

# 临时
def extract_agents_and_features_from_complete_info(agents_complete_info):
    """
    从完整信息字典列表中提取传统的agents和agent_features_list格式
    用于向后兼容旧代码
    
    Args:
        agents_complete_info: 完整信息字典列表
    
    Returns:
        tuple: (agents, agent_features_list)
            - agents: 人物对象列表
            - agent_features_list: 人物特征信息列表
    """
    agents = []
    agent_features_list = []
    
    for agent_info in agents_complete_info:
        agents.append(agent_info['entity'])
        
        features = {
            'type': agent_info['type'],
            'status': agent_info['status']
        }
        
        # 如果有椅子ID，添加到features
        if 'chair_id' in agent_info:
            features['chair_id'] = agent_info['chair_id']
        
        agent_features_list.append(features)
    
    return agents, agent_features_list


# ============= 人物位置规划(已放弃) =============
# 规划桌子周围人物的位置和状态
def plan_agents_around_table(table_object, room_bound, agent_blueprints, agent_sides, agent_is_sit, agent_traits, nearby_objects, 
                             min_distance=10, max_distance=90, min_agent_distance=60, safe_margin=15, print_info=False):
    """
    规划桌子周围人物的位置和状态（站立或坐下），返回规划结果而不实际生成人物
    
    Args:
        table_object: 桌子对象
        room_bound: 房间边界
        agent_blueprints: 人物蓝图列表
        agent_sides: 人物方向列表
        agent_is_sit: 人物是否坐下的布尔列表
        agent_traits: 人物特征列表 ['girl', 'boy', 'woman', 'grandpa', 'man']
        nearby_objects: 附近的物体列表
        min_distance: 距离桌子的最小距离
        max_distance: 距离桌子的最大距离
        min_agent_distance: 人物之间的最小距离
        safe_margin: 边界的安全边距
        print_info: 是否打印详细信息
    
    Returns:
        list: 人物规划信息列表，每个元素是一个字典，包含:
            - blueprint: 人物蓝图
            - trait: 人物特征
            - side: 方向
            - is_sit: 是否坐下
            - position: 位置（如果站立）
            - rotation: 朝向四元数
            - chair_id: 椅子ID（如果坐下）
            - status: 状态描述 ('standing' 或 'sitting')
    """
        
    # 检查输入参数一致性
    if len(agent_blueprints) != len(agent_sides) or len(agent_blueprints) != len(agent_is_sit) or len(agent_blueprints) != len(agent_traits):
        print("[ERROR] 人物蓝图、方向、坐下状态和特征数量不匹配")
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
    for i, (blueprint, side, should_sit, trait) in enumerate(zip(agent_blueprints, agent_sides, agent_is_sit, agent_traits)):
        if should_sit:
            sitting_agents.append((i, blueprint, side, trait))
        else:
            standing_agents.append((i, blueprint, side, trait))

    # 为需要坐下的人物匹配椅子
    matched_chairs = set()  # 记录已匹配的椅子
    for agent_idx, blueprint, side, trait in sitting_agents:
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
                    'trait': trait,  # 添加特征信息
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
                standing_agents.append((agent_idx, blueprint, side, trait))
        else:
            # 没有找到合适的椅子，将此人物转为站立
            if print_info:
                print(f"[PROCESSING] 人物 {agent_idx} 需要坐下但未找到合适椅子，转为站立")
            standing_agents.append((agent_idx, blueprint, side, trait))


    # 处理需要站立的人物（包括未能匹配到椅子的人物）
    for agent_idx, blueprint, side, trait in standing_agents:
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
                distance_to_other = math.sqrt(
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
                'trait': trait,
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
                print(f"[PROCESSING] 人物 {agent_idx} 将站立在位置: {agent_position}, 方向: {side}, 特征: {trait}")

        if not agent_placed:
            print(f"[CONTINUE] {max_attempts} 次尝试后 无法为人物 {agent_idx} 找到合适的位置")
            # 添加一个空的规划项，表示规划失败
            agent_plans.append({
                'blueprint': blueprint,
                'trait': trait,  # 添加特征信息
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
def execute_agent_plans(ue, agent_plans, json_file_path=None, print_info=False):
    """
    根据人物规划信息实际生成人物并执行相应动作
    
    Args:
        ue: TongSim实例
        agent_plans: 人物规划信息列表
        json_file_path: JSON文件路径
        print_info: 是否打印详细信息
    
    Returns:
        list: 生成的人物对象列表
    """

    agents = []
    agent_features_list = []  # 存储每个agent的特征信息
    for i, plan in enumerate(agent_plans):
        # 跳过规划失败的项目
        if plan['status'] == 'failed':
            print(f"[CONTINUE] 跳过人物 {i}: 规划失败")
            continue
        
        blueprint = plan['blueprint']
        is_sit = plan['is_sit']
        towards_position = plan['rotation']
        agent_status = "standing"  # 默认状态为站立

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
                random_position.z = random_position.z + 70
                
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
                    agent_status = "sitting"  # 更新状态为坐下
                    
                    if print_info:
                        print(f"[PROCESSING] 人物 {i} 已生成并成功坐在椅子 {chair_id} 上")

                else: # 坐下失败，改为站立
                    # 获取当前位置
                    current_position = agent.get_location()
                    
                    # 执行站立动作序列
                    agent.do_action(ts.action.MoveToLocation(loc=current_position))
                    agent.do_action(ts.action.TurnToLocation(loc=towards_position))
                    
                    agents.append(agent)
                    agent_status = "standing"  # 状态为站立
                    
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
                random_position.z = random_position.z + 70
                
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
                agent_status = "standing"  # 状态为站立
                
                if print_info:
                    print(f"[PROCESSING] 人物 {i} 已生成并安排站在位置 {position}")
                    

            # 构建agent的特征信息（包含状态）
            agent_features = {
                'type': plan['trait'],
                'status': agent_status
            }
            
            # 如果坐下成功，添加椅子信息
            if is_sit and agent_status == "sitting":
                agent_features['chair_id'] = str(plan['chair_id'])

            agent_features_list.append(agent_features)

        except Exception as e:
            print(f"[ERROR] 生成人物 {i} 时出错: {e}")
            continue

    # 如果提供了JSON文件路径，自动添加到JSON
    if json_file_path and agents:
        success = add_entities_to_json(
            json_file_path=json_file_path,
            entities=agents,
            entity_type='agent',
            features_list=agent_features_list,
            auto_detect_asset_type=False
        )
        if success and print_info:
            print(f"[SUCCESS] 已自动将 {len(agents)} 个人物添加到JSON文件")
    
    return agents


# ============== 场景人物数量变化 ==============
def add_agent_to_existing_scene(ue, table_object, room_bound, nearby_objects,
                                 existing_agents, placement_strategy, reference_agent_index=0,
                                 new_agent_blueprint=None, new_agent_trait=None, 
                                 should_sit=True, available_chairs=None,
                                 min_distance=10, max_distance=90,
                                 min_agent_distance=60, max_agent_distance=300,
                                 safe_margin=15, max_chair_adjust_attempts=8,
                                 chair_move_step=5.0, print_info=False):
    """
    在已有人物的场景中添加新人物
    
    Args:
        ue: TongSim实例
        table_object: 桌子对象
        room_bound: 房间边界
        nearby_objects: 附近的物体列表
        existing_agents: 已存在的人物对象列表
        placement_strategy: 放置策略 ('face_to_face', 'adjacent_sides', 'same_side')
        reference_agent_index: 参考人物的索引（默认0，即第一个人物）
        new_agent_blueprint: 新人物蓝图（可选，如果为None则随机选择）
        new_agent_trait: 新人物特性（可选，如果为None则随机选择）
        should_sit: 新人物是否坐下
        available_chairs: 可用椅子列表（可选，如果为None则自动从nearby_objects中筛选）
        min_distance: 距离桌子的最小距离
        max_distance: 距离桌子的最大距离
        min_agent_distance: 人物之间的最小距离
        max_agent_distance: 人物之间的最大距离
        safe_margin: 边界的安全边距
        max_chair_adjust_attempts: 椅子调整最大尝试次数
        chair_move_step: 椅子每次移动的步长
        print_info: 是否打印详细信息
    
    Returns:
        tuple: (new_agent, agent_features, updated_nearby_objects)
            - new_agent: 新生成的人物对象或None
            - agent_features: 新人物的特征信息字典
            - updated_nearby_objects: 更新后的附近物体列表
    """
    
    if not existing_agents:
        raise ValueError("[ERROR] existing_agents不能为空，至少需要一个已存在的人物作为参考")
    
    if reference_agent_index >= len(existing_agents):
        raise ValueError(f"[ERROR] reference_agent_index ({reference_agent_index}) 超出范围")
    
    # 获取参考人物
    reference_agent = existing_agents[reference_agent_index]
    reference_position = reference_agent.get_location()
    reference_side = determine_object_side(reference_agent, table_object)
    
    if print_info:
        print(f"\n[INFO] 添加新人物到场景")
        print(f"  参考人物索引: {reference_agent_index}")
        print(f"  参考人物位置: ({reference_position.x:.2f}, {reference_position.y:.2f}, {reference_position.z:.2f})")
        print(f"  参考人物方位: {reference_side}")
        print(f"  放置策略: {placement_strategy}")
    
    # 根据放置策略确定新人物的方位
    new_agent_side = None
    
    if placement_strategy == 'face_to_face':
        # 对立面放置
        side_opposites = {
            'front': 'back',
            'back': 'front',
            'left': 'right',
            'right': 'left'
        }
        new_agent_side = side_opposites.get(reference_side)
        if print_info:
            print(f"  策略: face_to_face - 新人物方位: {new_agent_side} (对立面)")
    
    elif placement_strategy == 'adjacent_sides':
        # 相邻侧面放置
        side_adjacents = {
            'front': ['left', 'right'],
            'back': ['left', 'right'],
            'left': ['front', 'back'],
            'right': ['front', 'back']
        }
        adjacent_options = side_adjacents.get(reference_side, [])
        
        # 检查是否已有人物占据了某个相邻侧面，优先选择空闲侧面
        existing_sides = set()
        for agent in existing_agents:
            agent_side = determine_object_side(agent, table_object)
            existing_sides.add(agent_side)
        
        available_adjacents = [side for side in adjacent_options if side not in existing_sides]
        
        if available_adjacents:
            new_agent_side = random.choice(available_adjacents)
        else:
            # 如果相邻侧面都有人，随机选择一个
            new_agent_side = random.choice(adjacent_options)
        
        if print_info:
            print(f"  策略: adjacent_sides - 新人物方位: {new_agent_side} (相邻侧面)")
    
    elif placement_strategy == 'same_side':
        # 同侧放置
        new_agent_side = reference_side
        if print_info:
            print(f"  策略: same_side - 新人物方位: {new_agent_side} (同侧)")
    
    else:
        raise ValueError(f"[ERROR] 不支持的放置策略: {placement_strategy}")
    
    if not new_agent_side:
        raise ValueError(f"[ERROR] 无法确定新人物方位 (reference_side={reference_side})")
    
    # 如果没有指定蓝图，随机选择
    if new_agent_blueprint is None:
        # 从所有可用蓝图中随机选择
        all_blueprints = [bp for blueprints in AGENT_BLUEPRINT_MAPPING.values() for bp in blueprints]
        new_agent_blueprint = random.choice(all_blueprints)
    
    # 如果没有指定特性，根据蓝图推断
    if new_agent_trait is None:
        new_agent_trait = BLUEPRINT_TO_TRAIT.get(new_agent_blueprint, 'unknown')
    
    if print_info:
        print(f"  新人物蓝图: {new_agent_blueprint}")
        print(f"  新人物特性: {new_agent_trait}")
        print(f"  新人物状态: {'sitting' if should_sit else 'standing'}")
    
    # 收集已存在人物的位置信息（用于距离检查）
    agent_positions = []
    for agent in existing_agents:
        pos = agent.get_location()
        agent_positions.append(pos)
    
    # 准备环境信息
    # 如果没有提供可用椅子列表，则从nearby_objects中筛选
    if available_chairs is None:
        if print_info:
            print(f"[INFO] 未提供可用椅子列表，将从nearby_objects中筛选")
        existed_chairs = filter_objects_by_type(objects_list=nearby_objects, type_file_path='./ownership/object/chair.txt')
        existed_sofas = filter_objects_by_type(objects_list=nearby_objects, type_file_path='./ownership/object/sofa.txt')
        available_chairs = list(existed_chairs) + list(existed_sofas)
    else:
        existed_chairs = available_chairs
        existed_sofas = []
    
    if print_info:
        print(f"[INFO] 可用椅子数量: {len(available_chairs)}")
    
    # 获取桌子的世界AABB边界
    table_aabb = table_object.get_world_aabb()
    table_min, table_max = fix_aabb_bounds(table_aabb)
    
    x_min, y_min, z_min, x_max, y_max, z_max = room_bound
    
    # 预计算附近物体的AABB边界
    nearby_object_bounds = []
    existed_carpet = filter_objects_by_type(objects_list=nearby_objects, type_file_path='./ownership/object/carpet.txt')
    carpet_ids = {carpet.id for carpet in existed_carpet} if existed_carpet else set()
    
    for obj in nearby_objects:
        try:
            if hasattr(obj, 'id') and obj.id in carpet_ids:
                continue
            
            if isinstance(obj, dict) and 'entity' in obj:
                entity = obj['entity']
                obj_aabb = entity.get_world_aabb()
                obj_aabb_min, obj_aabb_max = fix_aabb_bounds(obj_aabb)
                nearby_object_bounds.append({
                    'min': obj_aabb_min,
                    'max': obj_aabb_max,
                    'entity': entity,
                    'obj': obj,
                    'type': obj.get('type', 'unknown')
                })
            elif hasattr(obj, 'get_world_aabb'):
                obj_aabb = obj.get_world_aabb()
                obj_aabb_min, obj_aabb_max = fix_aabb_bounds(obj_aabb)
                nearby_object_bounds.append({
                    'min': obj_aabb_min,
                    'max': obj_aabb_max,
                    'entity': obj,
                    'obj': obj,
                    'type': 'unknown'
                })
        except Exception as e:
            print(f"[ERROR] 无法获取物体边界: {e}")
    
    # 计算可坐物体信息
    chair_info = []
    
    # 使用提供的可用椅子列表（这些椅子未被占用）
    for chair in available_chairs:
        try:
            pos = chair.get_location()
            side = determine_object_side(chair, table_object)
            
            # 判断是否为沙发（不可移动）
            is_sofa = False
            if existed_sofas:
                is_sofa = any(str(chair.id) == str(sofa.id) for sofa in existed_sofas)
            
            chair_info.append({
                'entity': chair,
                'position': (pos.x, pos.y, pos.z),
                'side': side,
                'matched': False,
                'movable': not is_sofa  # 沙发不可移动
            })
        except Exception as e:
            print(f"[ERROR] 获取椅子 {chair.id} 信息失败: {e}")
    
    # 生成新人物
    new_agent = None
    agent_features = None
    
    if should_sit:
        # 需要坐下：查找同方向且未匹配的椅子
        candidate_chairs = [c for c in chair_info if c['side'] == new_agent_side and not c['matched']]
        
        if not candidate_chairs:
            if print_info:
                print(f"[WARNING] 新人物需要坐下但未找到合适椅子，转为站立")
            should_sit = False
        else:
            # 随机选择一把椅子或沙发
            selected_chair_info = random.choice(candidate_chairs)
            selected_chair_info['matched'] = True
            chair = selected_chair_info['entity']
            is_movable = selected_chair_info['movable']
            
            # 尝试让人物坐下
            new_agent, agent_status, final_chair = _try_sit_on_chair(
                ue, chair, table_object, new_agent_blueprint, len(existing_agents),
                nearby_object_bounds, max_chair_adjust_attempts if is_movable else 1,
                chair_move_step, print_info, movable=is_movable
            )
            
            if new_agent:
                agent_features = {
                    'type': new_agent_trait,
                    'status': agent_status
                }
                if agent_status == "sitting":
                    agent_features['chair_id'] = str(final_chair.id)
                
                # 更新nearby_objects（如果椅子被替换）
                if final_chair.id != chair.id:
                    if print_info:
                        print(f"[INFO] 椅子已更新: {chair.id} -> {final_chair.id}，更新nearby_objects")
                    nearby_objects = [obj for obj in nearby_objects 
                                    if not (hasattr(obj, 'id') and obj.id == chair.id)]
                    nearby_objects.append(final_chair)
                
                if print_info:
                    pos = new_agent.get_location()
                    print(f"[SUCCESS] 新人物已生成并坐在位置 ({pos.x:.2f}, {pos.y:.2f}, {pos.z:.2f})")
            else:
                if print_info:
                    print(f"[WARNING] 新人物坐下失败，转为站立")
                should_sit = False
    
    # 如果需要站立或坐下失败
    if not should_sit and new_agent is None:
        agent_placed = False
        attempts = 0
        max_attempts = 1000000
        
        while not agent_placed and attempts < max_attempts:
            attempts += 1
            
            # 根据选择的侧边计算基础位置
            if new_agent_side == 'front':
                base_x = random.uniform(table_min.x, table_max.x)
                base_y = table_max.y
                direction = ts.Vector3(0, 1, 0)
            elif new_agent_side == 'back':
                base_x = random.uniform(table_min.x, table_max.x)
                base_y = table_min.y
                direction = ts.Vector3(0, -1, 0)
            elif new_agent_side == 'left':
                base_x = table_max.x
                base_y = random.uniform(table_min.y, table_max.y)
                direction = ts.Vector3(1, 0, 0)
            else:  # right
                base_x = table_min.x
                base_y = random.uniform(table_min.y, table_max.y)
                direction = ts.Vector3(-1, 0, 0)
            
            distance = random.uniform(min_distance, max_distance)
            agent_x = base_x + direction.x * distance
            agent_y = base_y + direction.y * distance
            agent_z = z_min
            agent_position = ts.Vector3(agent_x, agent_y, agent_z)
            
            # 检查是否与附近物体重叠
            too_close_to_object = False
            for obj_bounds in nearby_object_bounds:
                if check_position_in_bbox(agent_position, obj_bounds['min'], obj_bounds['max'],
                                         safe_margin=safe_margin, check_z_axis=False):
                    too_close_to_object = True
                    break
            if too_close_to_object:
                continue
            
            # 检查位置是否在房间边界内
            if not check_position_in_bbox(agent_position,
                                         ts.Vector3(x_min, y_min, z_min),
                                         ts.Vector3(x_max, y_max, z_max),
                                         safe_margin=-safe_margin, check_z_axis=False):
                continue
            
            # 检查与已有人物的距离（既不能太近也不能太远）
            too_close_to_other_agent = False
            too_far_from_other_agents = False
            
            for existing_pos in agent_positions:
                distance_to_other = math.sqrt(
                    (agent_position.x - existing_pos.x)**2 +
                    (agent_position.y - existing_pos.y)**2 +
                    (agent_position.z - existing_pos.z)**2
                )
                if distance_to_other < min_agent_distance:
                    too_close_to_other_agent = True
                    break
                if distance_to_other > max_agent_distance:
                    too_far_from_other_agents = True
                    break
            
            if too_close_to_other_agent or too_far_from_other_agents:
                continue
            
            # 生成站立的人物
            try:
                random_position = ue.spatical_manager.get_nearest_nav_position(target_location=agent_position)
                random_position.z = random_position.z + 70
                
                new_agent = ue.spawn_agent(
                    blueprint=new_agent_blueprint,
                    location=random_position,
                    desired_name=f"{new_agent_blueprint}_{len(existing_agents)}",
                    quat=None,
                    scale=None
                )
                
                # 计算朝向
                table_target_x = random.uniform(table_min.x, table_max.x)
                table_target_y = random.uniform(table_min.y, table_max.y)
                towards_position = ts.Vector3(table_target_x, table_target_y, table_max.z)
                
                new_agent.do_action(ts.action.MoveToLocation(loc=agent_position))
                new_agent.do_action(ts.action.TurnToLocation(loc=towards_position))
                
                agent_placed = True
                
                agent_features = {
                    'type': new_agent_trait,
                    'status': 'standing'
                }
                
                if print_info:
                    print(f"[SUCCESS] 新人物已生成并站在位置 ({agent_position.x:.2f}, {agent_position.y:.2f}, {agent_position.z:.2f})")
                    
            except Exception as e:
                print(f"[ERROR] 生成站立人物时出错: {e}")
                continue
        
        if not agent_placed:
            print(f"[ERROR] 无法为新人物找到合适的站立位置")
    
    return new_agent, agent_features, nearby_objects

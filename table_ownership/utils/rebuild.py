
import tongsim as ts
import json
import os
import time
import csv
import re
import random
import math
from pathlib import Path
from tongsim.type import ViewModeType

from .other_util import (
    get_room_bbox,
    get_room_boundary,
    fix_aabb_bounds,
    query_existing_objects_in_room,
    find_objects_near_table,
    validate_table,
    determine_object_side
)

from .entity_util import (
    filter_objects_by_type
)

from .agent_util import (
    generate_and_spawn_agents, 
    generate_agent_configuration,
    add_agent_to_existing_scene
)

from .item_util import (
    load_table_grid_json,
    spawn_items_on_grid
)

from .camera_util import (
    calculate_entities_center,
    generate_camera_positions,
    generate_top_view_camera_position,
    add_capture_camera,
    capture_and_save_images
)

from .json_util import (
    add_entities_to_json,
    create_scene_json_file
)

from .action_util import (
    generate_actions_for_all_agents
)

# ============== 场景信息提取功能 ==============

def extract_scene_info_from_json(json_file_path, print_info=False):
    """
    从单个 JSON 文件中提取场景关键信息
    
    Args:
        json_file_path: JSON文件路径
        print_info: 是否打印详细信息
    
    Returns:
        dict: 场景信息 {
            'json_path': str,  # JSON文件路径
            'map_name': str,
            'room_name': str,
            'table_id': str,
            'combination_type': str,  # 'face_to_face', 'adjacent_sides', 'same_side'
            'positions': list,  # ['front', 'back'] 等
            'agent_count': int,  # 人物数量
            'agents_info': list  # 人物详细信息（蓝图、状态等）
        } 或 None (如果提取失败)
    """
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            scene_data = json.load(f)
        
        # 提取场景基础信息
        scene_info = scene_data.get('scene_info', {})
        map_name = scene_info.get('map_name')
        room_name = scene_info.get('room_name')
        table_id = scene_info.get('table_id')
        
        if not map_name or not room_name or not table_id:
            if print_info:
                print(f"[WARNING] {json_file_path} 缺少必要信息，跳过")
            return None
        
        # 提取人物组合信息
        agent_combination = scene_data.get('agent_combination', {})
        combination_type = agent_combination.get('type', 'unknown')
        positions = agent_combination.get('positions', [])
        
        # 提取人物信息
        agents_data = scene_data.get('agents', [])
        agents_info = []
        
        for agent_data in agents_data:
            features = agent_data.get('features', {})
            agent_info = {
                'base_id': agent_data.get('base_id'),
                'trait': features.get('type', 'unknown'),
                'status': features.get('status', 'standing'),
                'chair_id': features.get('chair_id', None)
            }
            agents_info.append(agent_info)
        
        result = {
            'json_path': json_file_path,
            'map_name': map_name,
            'room_name': room_name,
            'table_id': table_id,
            'combination_type': combination_type,
            'positions': positions,
            'agent_count': len(agents_info),
            'agents_info': agents_info
        }
        
        if print_info:
            print(f"[INFO] 提取场景: {map_name}/{room_name}/{table_id} - {combination_type} - {positions}")
        
        return result
    
    except Exception as e:
        if print_info:
            print(f"[ERROR] 提取 {json_file_path} 失败: {e}")
        return None


def scan_and_extract_all_scenes(root_dir, save_file=None, print_info=False):
    """
    扫描目录下所有 scene_data.json 文件，提取场景信息并保存到文件
    
    Args:
        root_dir: 根目录路径（例如：D:\\tongsim-python\\ownership\\rebulid_scene\\2agent）
        save_file: 保存文件路径（可选），支持 .json 或 .csv 格式
                   如果为 None，默认保存为 root_dir/scenes_list.json
        print_info: 是否打印详细信息
    
    Returns:
        list: 场景信息列表，每个元素是 extract_scene_info_from_json 返回的字典
    """
    scenes_list = []
    root_path = Path(root_dir)
    
    if not root_path.exists():
        print(f"[ERROR] 目录不存在: {root_dir}")
        return scenes_list
    
    # 递归查找所有 scene_data.json 文件
    json_files = list(root_path.rglob('scene_data.json'))
    
    if print_info:
        print(f"[INFO] 找到 {len(json_files)} 个 scene_data.json 文件")
        print(f"{'='*60}")
    
    for json_file in json_files:
        scene_info = extract_scene_info_from_json(str(json_file), print_info=print_info)
        if scene_info:
            scenes_list.append(scene_info)
    
    if print_info:
        print(f"{'='*60}")
        print(f"[INFO] 成功提取 {len(scenes_list)} 个场景信息")
        print(f"\n场景类型统计:")
        
        # 统计场景类型
        type_count = {}
        for scene in scenes_list:
            combo_type = scene['combination_type']
            type_count[combo_type] = type_count.get(combo_type, 0) + 1
        
        for combo_type, count in type_count.items():
            print(f"  - {combo_type}: {count} 个场景")
    
    # 保存到文件
    if save_file is None:
        save_file = os.path.join(root_dir, 'scenes_list.json')
    
    save_path = Path(save_file)
    save_path.parent.mkdir(parents=True, exist_ok=True)
    
    if save_path.suffix == '.csv':
        # 保存为CSV格式
        with open(save_file, 'w', encoding='utf-8', newline='') as f:
            if scenes_list:
                # CSV表头
                fieldnames = ['json_path', 'map_name', 'room_name', 'table_id', 
                             'combination_type', 'positions', 'agent_count', 'agents_info']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                # 写入数据（将列表和字典转为JSON字符串）
                for scene in scenes_list:
                    row = scene.copy()
                    row['positions'] = json.dumps(row['positions'], ensure_ascii=False)
                    row['agents_info'] = json.dumps(row['agents_info'], ensure_ascii=False)
                    writer.writerow(row)
        
        if print_info:
            print(f"\n[SUCCESS] 场景列表已保存到 CSV 文件: {save_file}")
    else:
        # 保存为JSON格式（默认）
        with open(save_file, 'w', encoding='utf-8') as f:
            json.dump(scenes_list, f, indent=2, ensure_ascii=False)
        
        if print_info:
            print(f"\n[SUCCESS] 场景列表已保存到 JSON 文件: {save_file}")
    
    return scenes_list


def filter_scenes(scenes_list, map_name=None, room_name=None, combination_type=None, 
                 positions=None, agent_count=None):
    """
    根据条件筛选场景
    
    Args:
        scenes_list: 场景信息列表
        map_name: 地图名称（可选）
        room_name: 房间名称（可选）
        combination_type: 组合类型（可选）: 'face_to_face', 'adjacent_sides', 'same_side'
        positions: 位置列表（可选）: ['front', 'back'] 等
        agent_count: 人物数量（可选）
    
    Returns:
        list: 筛选后的场景列表
    """
    filtered = scenes_list
    
    if map_name:
        filtered = [s for s in filtered if s['map_name'] == map_name]
    
    if room_name:
        filtered = [s for s in filtered if s['room_name'] == room_name]
    
    if combination_type:
        filtered = [s for s in filtered if s['combination_type'] == combination_type]
    
    if positions:
        # 检查位置列表是否完全匹配
        filtered = [s for s in filtered if s['positions'] == positions]
    
    if agent_count is not None:
        filtered = [s for s in filtered if s['agent_count'] == agent_count]
    
    return filtered


def load_scenes_list(file_path, print_info=False):
    """
    从保存的文件中加载场景列表
    
    Args:
        file_path: 文件路径（支持 .json 或 .csv）
        print_info: 是否打印信息
    
    Returns:
        list: 场景信息列表
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        print(f"[ERROR] 文件不存在: {file_path}")
        return []
    
    scenes_list = []
    
    if file_path.suffix == '.csv':
        # 从CSV加载
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # 将JSON字符串转回列表/字典
                row['positions'] = json.loads(row['positions'])
                row['agents_info'] = json.loads(row['agents_info'])
                row['agent_count'] = int(row['agent_count'])
                scenes_list.append(row)
    else:
        # 从JSON加载
        with open(file_path, 'r', encoding='utf-8') as f:
            scenes_list = json.load(f)
    
    if print_info:
        print(f"[INFO] 从文件加载了 {len(scenes_list)} 个场景")
    
    return scenes_list

# ============== 基于场景信息重建功能（完整Pipeline集成）==============

def rebuild_scene_from_info(scene_info, grid_dir="./ownership/table_boundaries", 
                           log_dir="./ownership/logs_rebuild", max_item=9, 
                           min_table_area=0.4, auto_cleanup=True, print_info=False):
    """
    根据场景信息重建完整场景（包含人物、物品、动作、摄像头）
    
    完整Pipeline集成，包括：
    1. 打开地图，查找房间和桌子
    2. 加载网格数据
    3. 清空桌面
    4. 创建JSON保存目录
    5. 生成人物（基于positions，而非固定坐标）
    6. 使用网格系统放置物品
    7. 生成人物动作
    8. 创建摄像头并拍摄
    9. 保存所有数据到JSON
    10. 自动清理实体（如果开启）
    
    Args:
        scene_info: 场景信息字典（由 extract_scene_info_from_json 返回）
        grid_dir: 网格JSON文件目录
        log_dir: 日志保存目录
        max_item: 最大物品数量
        min_table_area: 最小桌子面积（用于验证）
        auto_cleanup: 是否自动清理实体（默认True）
        print_info: 是否打印详细信息
    
    Returns:
        dict: 重建结果 {
            'success': bool,
            'message': 结果信息
        }
    """
    try:
        # ========== 1. 读取场景信息 ==========
        map_name = scene_info['map_name']
        room_name = scene_info['room_name']
        table_id = scene_info['table_id']
        positions = scene_info['positions']
        agents_info = scene_info['agents_info']
        combination_type = scene_info.get('combination_type', 'unknown')
        
        if print_info:
            print(f"\n{'='*60}")
            print(f"[INFO] 开始重建场景:")
            print(f"  地图: {map_name}")
            print(f"  房间: {room_name}")
            print(f"  桌子ID: {table_id}")
            print(f"  组合类型: {combination_type}")
            print(f"  人物位置: {positions}")
            print(f"  人物数量: {len(agents_info)}")
            print(f"{'='*60}\n")
            
        # ========== 2. 打开地图 ==========
        with ts.TongSim(
            grpc_endpoint="127.0.0.1:5056",
            legacy_grpc_endpoint="127.0.0.1:50052",
        ) as ue:
            print(f"[PROCESSING] 正在打开地图: {map_name}")
            success = ue.open_level(map_name)
            if not success:
                return {
                    'success': False,
                    'message': f'[ERROR] 无法打开地图: {map_name}'
                }
            
            # ========== 3. 获取房间信息 ==========
            rooms = ue.spatical_manager.get_current_room_info()
            if not rooms:
                return {
                    'success': False,
                    'message': f'[ERROR] 地图 {map_name} 中没有找到房间信息'
                }
            
            room_bbox_dict = get_room_bbox(rooms)
            
            # 查找目标房间
            target_room_info = None
            for room_info in rooms:
                if room_info['room_name'] == room_name:
                    target_room_info = room_info
                    break
            
            if not target_room_info:
                return {
                    'success': False,
                    'message': f'[ERROR] 未找到房间: {room_name}'
                }
            
            print(f"[PROCESSING] 处理房间: {room_name}")
            room_bound = get_room_boundary(room_name, room_bbox_dict)
            
            # ========== 4. 查询房间内的桌子 ==========
            table_entitys = query_existing_objects_in_room(
                ue=ue, 
                room_bound=room_bound, 
                target_types=['coffeetable', 'diningTable', 'table', 'Table'], 
                object_name="桌子"
            )
            
            if not table_entitys:
                return {
                    'success': False,
                    'message': f'[ERROR] 房间 {room_name} 中没有找到桌子'
                }
            
            # 找到目标桌子
            target_table = None
            for table_entity in table_entitys:
                entity_base_id = str(table_entity.id)
                if table_id in entity_base_id or entity_base_id in table_id:
                    target_table = table_entity
                    break
            
            if not target_table:
                if print_info:
                    print(f"[WARNING] 未找到完全匹配的桌子 {table_id}，使用第一张桌子")
                target_table = table_entitys[0]
            
            print(f"[INFO] 找到桌子: {target_table.id}")
            
            # 验证桌子面积
            if not validate_table(target_table, min_table_area=min_table_area):
                return {
                    'success': False,
                    'message': f'[ERROR] 桌子面积不符合要求（最小: {min_table_area}）'
                }
            
            # ========== 5. 加载网格数据 ==========
            grid_data = load_table_grid_json(
                map_name=map_name,
                room_name=room_name,
                table_id=str(target_table.id),
                grid_dir=grid_dir
            )
            
            if not grid_data:
                return {
                    'success': False,
                    'message': f'[WARNING] 未找到桌子的网格数据，跳过'
                }
            
            print(f"[SUCCESS] 成功加载网格数据: {len(grid_data.get('safe_grids', []))} 个安全网格")
            
            # ========== 6. 查找并清空桌面 ==========
            on_table_items, nearby_items = find_objects_near_table(
                ue=ue,
                table_object=target_table,
                search_distance=120.0
            )
            
            if on_table_items:
                print(f"[INFO] 正在删除桌子上的 {len(on_table_items)} 个物品...")
                for item in on_table_items:
                    try:
                        ue.destroy_entity(item.id)
                    except Exception as e:
                        print(f"[WARNING] 删除物品 {item.id} 失败: {e}")
                print(f"[SUCCESS] 已清空桌面")
            
            # ========== 7. 创建保存目录和JSON文件（仅创建结构，暂不添加物品）==========
            # 提取地图编号
            map_num_match = re.search(r'_(\d+)$', map_name)
            map_num = int(map_num_match.group(1)) if map_num_match else 0
            
            # 构建文件夹名称：地图_房间_桌子ID_人物数量_位置组合
            # 例如: SDBP_Map_001_diningRoom_table1_2agents_front-back
            agent_count = len(agents_info)
            positions_str = '-'.join(positions)  # front-back 或 left-right 等
            table_id_clean = table_id.replace('_', '-')
            
            json_save_dir_name = f"{map_name}_{room_name}_{table_id_clean}_{agent_count}agents_{positions_str}"
            json_save_dir = os.path.join(log_dir, json_save_dir_name)
            json_file_path = create_scene_json_file(map_name, room_name, target_table, json_save_dir)
            
            # 注意：nearby_items的JSON添加将在人物生成后进行
            # 因为在人物生成过程中，椅子可能被删除和重新创建
            
            # ========== 8. 生成人物（基于positions）==========
            # 根据positions的方位信息生成人物配置
            num_agents = len(positions)
            
            print(f"\n[INFO] 根据位置信息生成人物配置:")
            print(f"  位置信息: {positions}")
            print(f"  人物数量: {num_agents}")
            
            # 使用 generate_agent_configuration 生成人物特征
            agent_blueprints, agent_sides, agent_is_sit, agent_traits = generate_agent_configuration(
                num_agents=num_agents,
                agent_sides=positions,  # 直接使用positions作为agent_sides
                sit_probability=0.75,   # 75%概率坐下
            )
            
            if print_info:
                print(f"\n[INFO] 人物生成配置:")
                for i in range(len(agent_blueprints)):
                    sit_status = "坐下" if agent_is_sit[i] else "站立"
                    print(f"  人物 {i+1}: {agent_traits[i]} ({agent_blueprints[i]}) - {agent_sides[i]} - {sit_status}")
            
            print(f"\n[PROCESSING] 开始生成人物...")
            agents, agent_features_list, updated_nearby_items = generate_and_spawn_agents(
                ue=ue,
                table_object=target_table,
                room_bound=room_bound,
                nearby_objects=nearby_items,
                agent_blueprints=agent_blueprints,
                agent_sides=agent_sides,
                agent_is_sit=agent_is_sit,
                agent_traits=agent_traits,
                min_distance=20,
                max_distance=50,
                min_agent_distance=60,
                safe_margin=15,
                max_chair_adjust_attempts=8,
                chair_move_step=5.0,
                print_info=print_info
            )
            
            # 更新nearby_items为最新状态（包含替换后的椅子）
            nearby_items = updated_nearby_items
            
            # ========== 8.5. 添加附近的物品到JSON（在人物生成后）==========
            # 现在nearby_items已包含最新的椅子状态
            if nearby_items:
                if print_info:
                    print(f"[INFO] 添加 {len(nearby_items)} 个附近物品到JSON...")
                add_entities_to_json(
                    json_file_path=json_file_path,
                    entities=nearby_items,
                    entity_type='object',
                    owner="room"
                )
            
            # 检查人物生成数量
            if len(agents) < 2:
                print(f"[CONTINUE] 未能生成足够的人物。成功生成: {len(agents)}, 需要: 2")
                # 清理
                for agent in agents:
                    try:
                        ue.destroy_entity(agent.id)
                    except:
                        pass
                if os.path.exists(json_file_path):
                    os.remove(json_file_path)
                    try:
                        os.rmdir(json_save_dir)
                    except OSError:
                        pass
                return {
                    'success': False,
                    'message': f'[ERROR] 未能生成足够人物: {len(agents)}/2'
                }
            
            ue.change_view_mode(ViewModeType.MANUAL_CONTROL_VIEW)
            
            # ========== 9. 使用网格系统放置物品 ==========
            print(f"\n[PROCESSING] 开始使用网格系统放置物品...")
            all_spawned_items, item_owners_list, item_features_list = spawn_items_on_grid(
                ue=ue,
                table_object=target_table,
                agents=agents,
                grid_data=grid_data,
                agent_features_list=agent_features_list,
                max_total_items=max_item,
                max_items_per_agent=3,
                print_info=True
            )
            
            total_spawned_items = len(all_spawned_items)
            print(f"[SUCCESS] 物品放置完成，共生成 {total_spawned_items} 个物品")
            
            # ========== 10. 保存物品信息到JSON ==========
            if all_spawned_items and item_owners_list and item_features_list:
                if len(all_spawned_items) == len(item_owners_list) == len(item_features_list):
                    complete_features_list = []
                    for owner, features in zip(item_owners_list, item_features_list):
                        complete_features = features.copy()
                        complete_features_list.append(complete_features)
                    
                    add_entities_to_json(
                        json_file_path=json_file_path,
                        entities=all_spawned_items,
                        entity_type='object',
                        owner=None,
                        features_list=complete_features_list
                    )
                    
                    # 更新owner字段
                    try:
                        with open(json_file_path, 'r', encoding='utf-8') as f:
                            scene_data = json.load(f)
                        
                        if 'objects' in scene_data:
                            objects_count = len(scene_data['objects'])
                            start_index = objects_count - len(all_spawned_items)
                            
                            for i, owner_id in enumerate(item_owners_list):
                                idx = start_index + i
                                if 0 <= idx < objects_count:
                                    scene_data['objects'][idx]['owner'] = owner_id
                        
                        with open(json_file_path, 'w', encoding='utf-8') as f:
                            json.dump(scene_data, f, indent=2, ensure_ascii=False)
                        
                        print(f"[SUCCESS] 已将 {len(all_spawned_items)} 个物品添加到JSON文件")
                    except Exception as e:
                        print(f"[ERROR] 更新物品owner字段失败: {e}")
            
            # ========== 11. 为人物生成随机动作 ==========
            print(f"\n[PROCESSING] 开始为人物生成随机动作...")
            action_stats = generate_actions_for_all_agents(
                agents=agents,
                agent_features_list=agent_features_list,
                all_spawned_items=all_spawned_items,
                item_owners_list=item_owners_list,
                item_features_list=item_features_list,
                action_probability=0.5,
                print_info=True
            )
            
            # ========== 12. 保存人物信息到JSON（包含动作信息）==========
            if agents and agent_features_list:
                add_entities_to_json(
                    json_file_path=json_file_path,
                    entities=agents,
                    entity_type='agent',
                    features_list=agent_features_list,
                    auto_detect_asset_type=False
                )
                print(f"[SUCCESS] 已将 {len(agents)} 个人物（含动作信息）添加到JSON文件")
            
            # ========== 13. 生成摄像头 ==========
            center_location = calculate_entities_center(agents=agents, items=all_spawned_items)
            camera_positions = generate_camera_positions(
                ue=ue,
                room_bound=room_bound,
                target_object=target_table,
                center_location=center_location,
                distance_range=[200, 300],
                height=[100, 250],
                agents=agents,
                num_cameras=8,
            )
            
            cameras = add_capture_camera(
                ue, 
                camera_positions, 
                center_location=center_location, 
                target_obj=target_table
            )
            print(f"[SUCCESS] 成功创建了 {len(cameras)} 个摄像头")
            
            if cameras:
                add_entities_to_json(
                    json_file_path=json_file_path, 
                    entities=cameras, 
                    entity_type='camera'
                )
            
            # 生成俯视摄像头
            top_camera_pos = generate_top_view_camera_position(
                room_bound=room_bound,
                agents=agents,
                items=all_spawned_items,
                margin_factor=1.5,
                safe_margin=30,
                print_info=False
            )
            
            top_camera = add_capture_camera(
                ue=ue,
                camera_positions=top_camera_pos,
                center_location=center_location, 
                target_obj=target_table,
                camera_name_prefix="TopCamera",
                print_info=False
            )
            
            if top_camera:
                add_entities_to_json(
                    json_file_path=json_file_path, 
                    entities=top_camera, 
                    entity_type='camera'
                )
            
            all_cameras = cameras + top_camera
            
            # ========== 14. 拍摄图像 ==========
            saved_images = capture_and_save_images(
                cameras=cameras,
                save_dir=json_save_dir,
                delay_before_capture=0.01
            )
            
            saved_images.update(capture_and_save_images(
                cameras=top_camera,
                save_dir=json_save_dir,
                delay_before_capture=0.01
            ))
            
            # ========== 15. 打印场景生成摘要 ==========
            print(f"\n{'='*60}")
            print(f"[SUCCESS] 场景重建完成: {json_save_dir_name}")
            print(f"{'='*60}")
            print(f"  地图: {map_name}")
            print(f"  房间: {room_name}")
            print(f"  桌子: {target_table.id}")
            print(f"  组合类型: {combination_type}")
            print(f"  人物数量: {len(agents)}")
            print(f"  物品总数: {total_spawned_items}")
            print(f"  摄像头数量: {len(all_cameras)}")
            print(f"  保存图像数量: {len(saved_images)}")
            print(f"  可用网格数: {len(grid_data.get('safe_grids', []))}")
            print(f"  JSON文件: {json_file_path}")
            print(f"{'='*60}\n")
            
            # ========== 16. 自动清理实体 ==========
            if auto_cleanup:
                print(f"[INFO] 开始清理场景实体...")
                # 清理人物
                for agent in agents:
                    try:
                        ue.destroy_entity(agent.id)
                    except:
                        pass
                # 清理物品
                for item in all_spawned_items:
                    try:
                        ue.destroy_entity(item.id)
                    except:
                        pass
                # 清理摄像头
                for camera in all_cameras:
                    try:
                        ue.destroy_entity(camera.id)
                    except:
                        pass
                print(f"[SUCCESS] 清理完成")
            
            return {
                'success': True,
                'message': f'[SUCCESS] 场景重建成功: {len(agents)} 人物, {total_spawned_items} 物品, {len(all_cameras)} 摄像头'
            }
    
    except Exception as e:
        error_msg = f'[ERROR] 重建场景失败: {str(e)}'
        print(error_msg)
        import traceback
        traceback.print_exc()
        
        return {
            'success': False,
            'message': error_msg
        }




# ============== JSON 场景重建与修改功能 ==============

def rebuild_agents_from_json(ue, json_file_path, print_info=False):
    """
    从 JSON 文件重新生成人物到场景中
    
    Args:
        ue: TongSim实例
        json_file_path: JSON文件路径
        print_info: 是否打印详细信息
    
    Returns:
        dict: 包含生成结果 {
            'success': bool,
            'agents': [生成的agent对象列表],
            'table': 桌子对象,
            'message': 结果信息
        }
    """
    try:
        # 读取 JSON 文件
        with open(json_file_path, 'r', encoding='utf-8') as f:
            scene_data = json.load(f)
        
        if print_info:
            print(f"[INFO] 正在从JSON重建人物: {json_file_path}")
        
        # 获取场景信息
        scene_info = scene_data.get('scene_info', {})
        map_name = scene_info.get('map_name')
        room_name = scene_info.get('room_name')
        table_id = scene_info.get('table_id')
        
        if not map_name or not table_id:
            return {
                'success': False,
                'agents': [],
                'table': None,
                'message': '[ERROR] JSON文件缺少必要的场景信息'
            }
        
        # 1. 打开地图
        print(f"[PROCESSING] 正在打开地图: {map_name}")
        success = ue.open_level(map_name)
        if not success:
            return {
                'success': False,
                'agents': [],
                'table': None,
                'message': f'[ERROR] 无法打开地图: {map_name}'
            }
        
        # 2. 获取房间信息
        rooms = ue.spatical_manager.get_current_room_info()
        if not rooms:
            return {
                'success': False,
                'agents': [],
                'table': None,
                'message': f'[ERROR] 地图 {map_name} 中没有找到房间信息'
            }
        
        # 获取房间边界框信息
        room_bbox_dict = get_room_bbox(rooms)
        
        # 查找目标房间
        target_room_info = None
        for room_info in rooms:
            if room_info['room_name'] == room_name:
                target_room_info = room_info
                break
        
        if not target_room_info:
            return {
                'success': False,
                'agents': [],
                'table': None,
                'message': f'[ERROR] 未找到房间: {room_name}'
            }
        
        print(f"[PROCESSING] 处理房间: {room_name}")
        room_bound = get_room_boundary(room_name, room_bbox_dict)
        
        # 3. 查询房间内的桌子
        table_entitys = query_existing_objects_in_room(
            ue=ue, 
            room_bound=room_bound, 
            target_types=['coffeetable', 'diningTable', 'table', 'Table'], 
            object_name="桌子"
        )
        
        if not table_entitys:
            return {
                'success': False,
                'agents': [],
                'table': None,
                'message': f'[ERROR] 房间 {room_name} 中没有找到桌子'
            }
        
        # 4. 找到目标桌子
        target_table = None
        for table_entity in table_entitys:
            if str(table_entity.id) == table_id:
                target_table = table_entity
                break
        
        if not target_table:
            print(f"[WARNING] 未找到ID为 {table_id} 的桌子，使用第一张桌子")
            target_table = table_entitys[0]
        
        print(f"[INFO] 找到桌子: {target_table.id}")
        
        # 5. 查找桌子附近的椅子（用于坐下）
        on_table_items, nearby_items = find_objects_near_table(
            ue=ue,
            table_object=target_table,
            search_distance=120.0,
            print_info=False
        )
        
        # 构建椅子ID映射
        chair_dict = {}
        for item in nearby_items:
            item_id = str(item.id)
            chair_dict[item_id] = item
            if print_info:
                print(f"[INFO] 找到附近物品: {item_id}")
        
        # 6. 读取人物信息并重新生成
        agents_data = scene_data.get('agents', [])
        if not agents_data:
            return {
                'success': False,
                'agents': [],
                'table': target_table,
                'message': '[WARNING] JSON中没有人物信息'
            }
        
        generated_agents = []
        
        for i, agent_data in enumerate(agents_data):
            try:
                agent_id = agent_data.get('id')
                base_id = agent_data.get('base_id')
                position = agent_data.get('position', {})
                rotation = agent_data.get('rotation', {})
                features = agent_data.get('features', {})
                
                if not base_id:
                    print(f"[WARNING] 人物 {i} 缺少base_id，跳过")
                    continue
                
                # 获取目标位置
                target_location = ts.Vector3(
                    position.get('x', 0),
                    position.get('y', 0),
                    position.get('z', 0)
                )
                
                # 获取最近的导航点
                random_position = ue.spatical_manager.get_nearest_nav_position(target_location=target_location)
                random_position.z = random_position.z + 70
                
                # 生成人物
                agent = ue.spawn_agent(
                    blueprint=base_id,
                    location=random_position,
                    desired_name=f"{base_id}_{i}",
                    quat=None,
                    scale=None
                )
                
                print(f"[INFO] 生成人物 {i+1}/{len(agents_data)}: {base_id} -> {agent.id}")
                
                # 处理人物状态
                status = features.get('status', 'standing')
                
                if status == 'sitting':
                    # 需要坐下
                    chair_id = features.get('chair_id')
                    
                    if not chair_id:
                        print(f"[WARNING] 人物 {i} 需要坐下但未指定椅子ID，改为站立")
                        # 改为站立
                        agent.do_action(ts.action.MoveToLocation(loc=target_location))
                        # 计算朝向
                        towards_quat = ts.Quaternion(
                            rotation.get('w', 1.0),
                            rotation.get('x', 0),
                            rotation.get('y', 0),
                            rotation.get('z', 0)
                        )
                        # 将四元数转换为朝向位置（简单方法：向前方偏移一点）
                        towards_position = ts.Vector3(
                            target_location.x + 100,
                            target_location.y,
                            target_location.z
                        )
                        agent.do_action(ts.action.TurnToLocation(loc=towards_position))
                        generated_agents.append(agent)
                        continue
                    
                    # 查找椅子实体
                    chair = chair_dict.get(chair_id)
                    
                    if not chair:
                        print(f"[WARNING] 未找到椅子 {chair_id}，人物 {i} 改为站立")
                        # 改为站立
                        agent.do_action(ts.action.MoveToLocation(loc=target_location))
                        towards_position = ts.Vector3(
                            target_location.x + 100,
                            target_location.y,
                            target_location.z
                        )
                        agent.do_action(ts.action.TurnToLocation(loc=towards_position))
                        generated_agents.append(agent)
                        continue
                    
                    # 执行坐下动作序列
                    agent.do_action(ts.action.MoveToObject(object_id=chair.id, speed=1000))
                    sit_result = agent.do_action(ts.action.SitDownToObject(object_id=chair.id))
                    
                    # 检查坐下是否成功
                    sit_success = False
                    if sit_result and len(sit_result) > 0:
                        for result in sit_result:
                            if hasattr(result, 'status') and result.status == 'end' and result.error_code == 0:
                                sit_success = True
                                break
                            elif hasattr(result, 'status') and result.status == 'error':
                                print(f"[WARNING] 人物 {i} 坐下失败: error_code={getattr(result, 'error_code', 'unknown')}")
                    
                    if sit_success:
                        # 坐下成功，执行转向
                        # 从旋转四元数计算朝向位置
                        towards_position = ts.Vector3(
                            target_location.x + 100,
                            target_location.y,
                            target_location.z
                        )
                        agent.do_action(ts.action.TurnToLocation(loc=towards_position))
                        generated_agents.append(agent)
                        
                        if print_info:
                            print(f"[SUCCESS] 人物 {i} 已坐在椅子 {chair_id} 上")
                    else:
                        # 坐下失败，改为站立
                        print(f"[WARNING] 人物 {i} 坐下失败，改为站立")
                        current_position = agent.get_location()
                        agent.do_action(ts.action.MoveToLocation(loc=current_position))
                        towards_position = ts.Vector3(
                            target_location.x + 100,
                            target_location.y,
                            target_location.z
                        )
                        agent.do_action(ts.action.TurnToLocation(loc=towards_position))
                        generated_agents.append(agent)
                
                else:
                    # 站立状态
                    agent.do_action(ts.action.MoveToLocation(loc=target_location))
                    
                    # 从旋转四元数计算朝向
                    towards_position = ts.Vector3(
                        target_location.x + 100,
                        target_location.y,
                        target_location.z
                    )
                    agent.do_action(ts.action.TurnToLocation(loc=towards_position))
                    generated_agents.append(agent)
                    
                    if print_info:
                        print(f"[SUCCESS] 人物 {i} 已站在位置 {target_location}")
            
            except Exception as e:
                print(f"[ERROR] 生成人物 {i} 失败: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # 返回结果
        return {
            'success': True,
            'agents': generated_agents,
            'table': target_table,
            'message': f'[SUCCESS] 成功重建 {len(generated_agents)}/{len(agents_data)} 个人物'
        }
    
    except Exception as e:
        print(f"[ERROR] 重建人物失败: {e}")
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'agents': [],
            'table': None,
            'message': f'[ERROR] 重建失败: {str(e)}'
        }


# ============== 精确场景重建功能（根据JSON完整恢复场景）==============
def rebuild_exact_scene_from_json(json_file_path, output_dir=None, print_info=True):
    """
    根据JSON文件精确重建完整场景（包括人物位置、旋转、动作和桌面物品）
    
    功能：
    1. 删除现有椅子并从JSON重建椅子（精确位置和旋转）
    2. 精确恢复人物的位置和旋转
    3. 人物坐下时自动寻找最近的椅子
    4. 精确恢复桌面物品的位置、旋转和scale
    5. 执行人物动作（使用新的物品ID映射）
    6. 生成摄像头并拍摄图像
    7. 保存新的场景JSON文件
    
    Args:
        json_file_path: 场景JSON文件路径（包含scene_info和objects数据）
        output_dir: 输出目录路径（可选），如果为None则使用JSON文件所在目录下的"rebuild"子目录
        print_info: 是否打印详细信息
    
    Returns:
        dict: 重建结果 {
            'success': bool,
            'message': str,
            'output_dir': str,  # 输出目录
            'json_path': str,   # 新的JSON文件路径
            'images': list      # 拍摄的图像列表
        }
    """
    try:
        # 检查输入文件
        if not os.path.exists(json_file_path):
            return {
                'success': False,
                'message': f'[ERROR] JSON文件不存在: {json_file_path}'
            }
        
        # 确定输出目录
        if output_dir is None:
            json_dir = os.path.dirname(json_file_path)
            output_dir = os.path.join(json_dir, 'rebuild')
        
        os.makedirs(output_dir, exist_ok=True)
        
        if print_info:
            print(f"\n{'='*60}")
            print(f"开始精确重建场景: {json_file_path}")
            print(f"输出目录: {output_dir}")
            print(f"{'='*60}")
        
        # ========== 1. 加载JSON数据 ==========
        with open(json_file_path, 'r', encoding='utf-8') as f:
            scene_data = json.load(f)
        
        scene_info = scene_data.get('scene_info', {})
        map_name = scene_info.get('map_name')
        room_name = scene_info.get('room_name')
        table_id = scene_info.get('table_id')
        
        if not all([map_name, room_name, table_id]):
            return {
                'success': False,
                'message': '[ERROR] JSON文件缺少必要的场景信息'
            }
        
        if print_info:
            print(f"[INFO] 场景信息: {map_name} - {room_name} - {table_id}")
        
        # ========== 2. 连接TongSim ==========
        if print_info:
            print(f"\n[PROCESSING] 正在连接TongSim...")
        
        with ts.TongSim(
            grpc_endpoint="127.0.0.1:5056",
            legacy_grpc_endpoint="127.0.0.1:50052",
        ) as ue:
            
            # ========== 3. 打开地图和房间 ==========
            print(f"{'='*60}")
            print(f"[PROCESSING] 正在打开地图和房间...")
            print(f"{'='*60}")
            
            success = ue.open_level(map_name)
            if not success:
                return {
                    'success': False,
                    'message': f'[WARNING] 无法打开地图: {map_name}'
                }
            
            # 获取房间信息
            rooms = ue.spatical_manager.get_current_room_info()
            room_bbox_dict = get_room_bbox(rooms)
            room_bound = get_room_boundary(room_name, room_bbox_dict)
            
            if not room_bound:
                return {
                    'success': False,
                    'message': f'[ERROR] 无法获取房间边界: {room_name}'
                }
            
            # ========== 4. 查找桌子 ==========
            print(f"[PROCESSING] 正在查找桌子: {table_id}...")
            
            # 查询房间内的桌子
            table_entitys = query_existing_objects_in_room(
                ue=ue, 
                room_bound=room_bound, 
                target_types=['coffeetable', 'diningTable', 'table', 'Table'], 
                object_name="桌子",
                print_info=False
            )
            
            if not table_entitys:
                return {
                    'success': False,
                    'message': f'[ERROR] 房间 {room_name} 中没有找到桌子'
                }
            
            # 找到目标桌子
            target_table = None
            for table_entity in table_entitys:
                entity_base_id = str(table_entity.id)
                if table_id in entity_base_id or entity_base_id in table_id:
                    target_table = table_entity
                    break
            
            if not target_table:
                return {
                    'success': False,
                    'message': f'[WARNING] 未找到完全匹配的桌子 {table_id}，使用第一张桌子'
                }
            
            print(f"[INFO] 找到桌子: {target_table.id}")
            
            # ========== 5. 查找附近物体并删除现有椅子 ==========
            print(f"\n[PROCESSING] 正在查找附近物体...")
            
            on_table_items, nearby_items = find_objects_near_table(
                ue=ue,
                table_object=target_table,
                search_distance=120.0,
                print_info=False
            )
            
            # 删除桌面上的物品
            if on_table_items:
                if print_info:
                    print(f"[INFO] 正在删除桌子上的 {len(on_table_items)} 个物品...")
                for item in on_table_items:
                    try:
                        ue.destroy_entity(item.id)
                    except Exception as e:
                        print(f"[WARNING] 删除物品失败: {e}")
            
            # 找出现有的椅子,删除所有现有椅子
            existed_chairs = filter_objects_by_type(objects_list=nearby_items, type_file_path='./ownership/object/chair.txt')
            if existed_chairs:
                if print_info:
                    print(f"[INFO] 正在删除 {len(existed_chairs)} 把现有椅子...")
                for chair in existed_chairs:
                    try:
                        ue.destroy_entity(chair.id)
                    except Exception as e:
                        print(f"[WARNING] 删除椅子失败: {e}")
            
            # ========== 6. 从JSON重建椅子 ==========
            if print_info:
                print(f"\n[PROCESSING] 开始从JSON重建椅子...")
            
            # 从JSON中提取椅子信息（owner为room的物品）
            room_objects = scene_data.get('objects', [])
            json_room_data = [obj for obj in room_objects 
                               if obj.get('type') == 'object' and obj.get('owner') == 'room']
            
            # 读取椅子类型列表
            chair_types = []
            try:
                with open('./ownership/object/chair.txt', 'r', encoding='utf-8') as f:
                    chair_types = [line.strip() for line in f if line.strip()]
            except Exception as e:
                print(f"[WARNING] 无法读取椅子类型文件: {e}")
            
            # 重建椅子
            rebuilt_chairs = []
            for chair_data in json_room_data:
                base_id = chair_data.get('base_id', '')
                
                # 检查base_id是否在椅子类型列表中
                is_chair = any(chair_type in base_id for chair_type in chair_types)
                
                if is_chair:
                    try:
                        pos = chair_data['position']
                        rot = chair_data['rotation']
                        
                        new_chair = ue.spawn_entity(
                            entity_type=ts.BaseObjectEntity,
                            blueprint=base_id,
                            location=ts.Vector3(pos['x'], pos['y'], pos['z']),
                            is_simulating_physics=True,
                            quat=ts.Quaternion(rot['w'], rot['x'], rot['y'], rot['z'])
                        )
                        
                        rebuilt_chairs.append(new_chair)
                        
                        if print_info:
                            print(f"[SUCCESS] 重建椅子: {base_id} at ({pos['x']:.1f}, {pos['y']:.1f})")
                    
                    except Exception as e:
                        print(f"[ERROR] 重建椅子失败 {base_id}: {e}")
            
            if print_info:
                print(f"[SUCCESS] 共重建 {len(rebuilt_chairs)} 把椅子")
            
            # 更新nearby_items：移除旧椅子，添加新椅子
            # 保留nearby_items中非椅子的物品（这些物品没有被删除）
            existed_chair_ids = {str(chair.id) for chair in existed_chairs}
            updated_nearby_items = [item for item in nearby_items if str(item.id) not in existed_chair_ids]
            
            # 添加新重建的椅子
            updated_nearby_items.extend(rebuilt_chairs)
            nearby_items = updated_nearby_items
            
            if print_info:
                print(f"[INFO] 更新nearby_items: 移除 {len(existed_chairs)} 把旧椅子，添加 {len(rebuilt_chairs)} 把新椅子")
                print(f"[INFO] nearby_items总数: {len(nearby_items)}")
            
            # ========== 7. 精确重建人物 ==========
            print(f"\n[PROCESSING] 开始精确重建人物...")
            
            # 从JSON中提取人物数据 - 注意：人物在 "agents" 字段，不在 "objects" 中
            agents_data = scene_data.get('agents', [])
            if not agents_data:
                return {
                    'success': False,
                    'message': '[ERROR] JSON中没有人物数据'
                }
            
            generated_agents = []
            agent_actions = []  # 存储需要执行的动作
            agent_features_list = []  # 存储人物特征
            
            for i, agent_data in enumerate(agents_data):
                try:
                    base_id = agent_data.get('base_id')
                    position = agent_data.get('position')
                    rotation = agent_data.get('rotation')
                    features = agent_data.get('features', {})
                    
                    if not all([base_id, position, rotation]):
                        print(f"[WARNING] 人物 {i} 数据不完整，跳过")
                        continue
                    
                    status = features.get('status', 'standing')
                    agent = None  # 初始化agent变量
                    sit_success = False
                    
                    # 处理人物状态
                    if status == 'sitting':
                        # 生成人物
                        agent = ue.spawn_agent(
                            blueprint=base_id,
                            location=ts.Vector3(position['x'], position['y'], position['z'] + 70),
                            desired_name=f"{base_id}_{i}",
                            quat=ts.Quaternion(rotation['w'], rotation['x'], rotation['y'], rotation['z']),
                            scale=None
                        )
                        # 需要坐下，找最近的椅子
                        target_location = ts.Vector3(position['x'], position['y'], position['z'])
                        
                        # 寻找最近的椅子
                        closest_chair = None
                        min_distance = float('inf')
                        
                        for chair in rebuilt_chairs:
                            chair_pos = chair.get_location()
                            distance = ((chair_pos.x - target_location.x)**2 + 
                                       (chair_pos.y - target_location.y)**2 + 
                                       (chair_pos.z - target_location.z)**2) ** 0.5
                            
                            if distance < min_distance:
                                min_distance = distance
                                closest_chair = chair
                        
                        if closest_chair:
                            # 移动到椅子并坐下
                            agent.do_action(ts.action.MoveToObject(object_id=closest_chair.id, speed=1000))
                            sit_result = agent.do_action(ts.action.SitDownToObject(object_id=closest_chair.id))
                            
                            # 检查坐下是否成功
                            if sit_result and len(sit_result) > 0:
                                for result in sit_result:
                                    if hasattr(result, 'status') and result.status == 'end' and result.error_code == 0:
                                        sit_success = True
                                        break
                            
                            if sit_success:
                                # 更新特征中的椅子ID
                                features['chair_id'] = closest_chair.id
                                print(f"[SUCCESS] 人物 {i}: {base_id} 成功坐在椅子 {closest_chair.id}")
                            else:
                                print(f"[WARNING] 人物 {i}: {base_id} 坐下失败，删除后重新创建为站立")
                                ue.destroy_entity(agent.id)
                                agent = None  # 标记需要重新创建
                        else:
                            print(f"[WARNING] 人物 {i}: {base_id} 没有找到可用椅子，删除后重新创建为站立")
                            ue.destroy_entity(agent.id)
                            agent = None  # 标记需要重新创建
                    
                    # 如果是站立状态，或者坐下失败需要重新创建
                    if status == 'standing' or (status == 'sitting' and not sit_success):
                        # 生成站立的人物
                        agent = ue.spawn_agent(
                            blueprint=base_id,
                            location=ts.Vector3(position['x'], position['y'], position['z'] + 70),
                            desired_name=f"{base_id}_{i}",
                            quat=ts.Quaternion(rotation['w'], rotation['x'], rotation['y'], rotation['z']),
                            scale=None
                        )
                        print(f"[SUCCESS] 人物 {i}: {base_id} 站立 at ({position['x']:.1f}, {position['y']:.1f})")
                    
                    # 确保agent创建成功后再添加到列表
                    if agent is not None:
                        generated_agents.append(agent)
                        
                        # 重新构建features（不直接使用JSON中的旧features）
                        # 只保留基础信息：type和status
                        new_features = {
                            'type': features.get('type', 'unknown'),
                            'status': 'sitting' if sit_success else 'standing'
                        }
                        
                        # 如果坐下成功，添加椅子ID
                        if sit_success:
                            new_features['chair_id'] = closest_chair.id
                        
                        agent_features_list.append(new_features)
                        
                        # 保存动作信息（稍后执行）
                        # 从JSON中读取原始动作类型，但不包含旧的item_id
                        action_type = features.get('action')
                        if action_type and action_type != 'none':
                            agent_actions.append({
                                'agent': agent,
                                'action_type': action_type,
                                'old_reach_item_id': features.get('reach_item_id'),  # 保存旧ID用于映射
                                'old_point_item_id': features.get('point_item_id')   # 保存旧ID用于映射
                            })
                    else:
                        print(f"[ERROR] 人物 {i}: {base_id} 创建失败")
                
                except Exception as e:
                    print(f"[ERROR] 生成人物 {i} 失败: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            if not generated_agents:
                return {
                    'success': False,
                    'message': '[ERROR] 没有成功生成任何人物'
                }
            
            # ========== 8. 精确重建桌面物品 ==========
            if print_info:
                print(f"\n[PROCESSING] 开始精确重建桌面物品...")
            
            # 只重建有owner且owner不是room的物品（桌面物品）
            table_items_data = [obj for obj in scene_data.get('objects', []) 
                               if obj.get('type') == 'object' 
                               and obj.get('owner') 
                               and obj.get('owner') != 'room']
            
            if print_info:
                print(f"[INFO] 找到 {len(table_items_data)} 个桌面物品")
            
            generated_items = []
            item_id_mapping = {}  # 旧ID到新ID的映射
            item_owners_list = []
            item_features_list = []
            
            from configs.item_config import ITEM_PROPERTIES
            
            for i, item_data in enumerate(table_items_data):
                try:
                    base_id = item_data.get('base_id')
                    position = item_data.get('position')
                    rotation = item_data.get('rotation')
                    old_id = item_data.get('id')
                    owner = item_data.get('owner')
                    features = item_data.get('features', {})
                    
                    if not all([base_id, position, rotation]):
                        print(f"[WARNING] 物品 {i} 数据不完整，跳过")
                        continue
                    
                    # 获取物品属性（用于缩放）
                    item_type = features.get('type', '')
                    scale = ts.Vector3(1, 1, 1)
                    
                    if item_type and item_type in ITEM_PROPERTIES:
                        scale = ITEM_PROPERTIES[item_type].get('scale', ts.Vector3(1, 1, 1))
                    
                    # 生成物品（启用物理）
                    item = ue.spawn_entity(
                        entity_type=ts.BaseObjectEntity,
                        blueprint=base_id,
                        location=ts.Vector3(position['x'], position['y'], position['z']),
                        is_simulating_physics=True,
                        scale=scale,
                        quat=ts.Quaternion(rotation['w'], rotation['x'], rotation['y'], rotation['z']),
                    )
                    
                    generated_items.append(item)
                    item_id_mapping[old_id] = item.id
                    item_owners_list.append(owner)
                    item_features_list.append(features)
                    
                    print(f"[SUCCESS] 物品 {i}: {base_id} (owner: {owner}) at ({position['x']:.1f}, {position['y']:.1f})")
                
                except Exception as e:
                    print(f"[ERROR] 生成物品 {i} 失败: {e}")
                    continue
            
            # ========== 9. 执行人物动作 ==========
            if agent_actions and print_info:
                print(f"\n[PROCESSING] 开始执行人物动作...")
            
            for action_info in agent_actions:
                try:
                    agent = action_info['agent']
                    action_type = action_info['action_type']
                    
                    # 找到对应的agent索引
                    agent_index = generated_agents.index(agent)
                    
                    if action_type == 'point_at_item':
                        old_item_id = action_info.get('old_point_item_id')
                        
                        # 映射到新物品ID
                        new_item_id = item_id_mapping.get(old_item_id)
                        
                        if new_item_id:
                            # 找到对应的物品对象
                            target_item = None
                            for item in generated_items:
                                if str(item.id) == str(new_item_id):
                                    target_item = item
                                    break
                            
                            if target_item:
                                from .action_util import action_point_at_item
                                
                                # action_point_at_item 需要的是 item 对象，不是 item_id
                                result = action_point_at_item(
                                    agent=agent,
                                    item=target_item,
                                    print_info=print_info
                                )
                                
                                # 更新agent_features_list
                                agent_features_list[agent_index]['action'] = 'point_at_item'
                                agent_features_list[agent_index]['point_item_id'] = str(target_item.id)
                                agent_features_list[agent_index]['action_success'] = result.get('success', False)
                                if 'hand_used' in result:
                                    agent_features_list[agent_index]['hand_used'] = result['hand_used']
                                
                                if print_info:
                                    success = result.get('success', False)
                                    status = "成功" if success else "失败"
                                    print(f"[INFO] 人物指向动作执行{status}: {agent.id} -> {target_item.id}")
                            else:
                                if print_info:
                                    print(f"[WARNING] 无法找到新物品对象: {new_item_id}")
                                # 标记动作失败
                                agent_features_list[agent_index]['action'] = 'none'
                                agent_features_list[agent_index]['action_success'] = False
                        else:
                            if print_info:
                                print(f"[WARNING] 无法映射旧物品ID: {old_item_id}")
                            # 标记动作失败
                            agent_features_list[agent_index]['action'] = 'none'
                            agent_features_list[agent_index]['action_success'] = False
                    
                    elif action_type == 'reach_item':
                        old_item_id = action_info.get('old_reach_item_id')
                        
                        # 映射到新物品ID
                        new_item_id = item_id_mapping.get(old_item_id)
                        
                        if new_item_id:
                            # 找到对应的物品对象
                            target_item = None
                            for item in generated_items:
                                if str(item.id) == str(new_item_id):
                                    target_item = item
                                    break
                            
                            if target_item:
                                from .action_util import action_reach_item
                                
                                # 获取人物状态
                                agent_status = agent_features_list[agent_index].get('status', 'standing')
                                
                                # action_reach_item 需要的是 item 对象
                                result = action_reach_item(
                                    agent=agent,
                                    item=target_item,
                                    agent_status=agent_status,
                                    print_info=print_info
                                )
                                
                                # 更新agent_features_list
                                agent_features_list[agent_index]['action'] = 'reach_item'
                                agent_features_list[agent_index]['reach_item_id'] = str(target_item.id)
                                agent_features_list[agent_index]['action_success'] = result.get('success', False)
                                if 'hand_used' in result:
                                    agent_features_list[agent_index]['hand_used'] = result['hand_used']
                                
                                if print_info:
                                    success = result.get('success', False)
                                    status = "成功" if success else "失败"
                                    print(f"[INFO] 人物伸手动作执行{status}: {agent.id} -> {target_item.id}")
                            else:
                                if print_info:
                                    print(f"[WARNING] 无法找到新物品对象: {new_item_id}")
                                # 标记动作失败
                                agent_features_list[agent_index]['action'] = 'none'
                                agent_features_list[agent_index]['action_success'] = False
                        else:
                            if print_info:
                                print(f"[WARNING] 无法映射旧物品ID: {old_item_id}")
                            # 标记动作失败
                            agent_features_list[agent_index]['action'] = 'none'
                            agent_features_list[agent_index]['action_success'] = False
                
                except Exception as e:
                    print(f"[ERROR] 执行动作失败: {e}")
                    import traceback
                    traceback.print_exc()
                    # 标记动作失败
                    try:
                        agent_index = generated_agents.index(agent)
                        agent_features_list[agent_index]['action'] = 'none'
                        agent_features_list[agent_index]['action_success'] = False
                    except:
                        pass
            
            # ========== 10. 生成摄像头并拍摄 ==========
            if print_info:
                print(f"\n[PROCESSING] 开始生成摄像头...")
            
            # 计算中心位置
            center_location = calculate_entities_center(agents=generated_agents, items=generated_items)
            
            # 生成环绕摄像头
            camera_positions = generate_camera_positions(
                ue=ue,
                room_bound=room_bound,
                target_object=target_table,
                center_location=center_location,
                distance_range=[200, 300],
                height=[100, 250],
                agents=generated_agents,
                num_cameras=8,
            )
            
            cameras = add_capture_camera(
                ue, 
                camera_positions, 
                center_location=center_location, 
                target_obj=target_table
            )
            
            if print_info:
                print(f"[SUCCESS] 成功创建了 {len(cameras)} 个摄像头")
            
            # 生成俯视摄像头
            top_camera_pos = generate_top_view_camera_position(
                room_bound=room_bound,
                agents=generated_agents,
                items=generated_items,
                margin_factor=1.5,
                safe_margin=30,
                print_info=False
            )
            
            top_camera = add_capture_camera(
                ue=ue,
                camera_positions=top_camera_pos,
                center_location=center_location, 
                target_obj=target_table,
                camera_name_prefix="TopCamera",
                print_info=False
            )
            
            all_cameras = cameras + top_camera
            
            # ========== 11. 拍摄图像 ==========
            if print_info:
                print(f"\n[PROCESSING] 开始拍摄图像...")
            
            saved_images = capture_and_save_images(
                cameras=cameras,
                save_dir=output_dir,
                delay_before_capture=0.01
            )
            
            saved_images.update(capture_and_save_images(
                cameras=top_camera,
                save_dir=output_dir,
                delay_before_capture=0.01
            ))
            
            if print_info:
                print(f"[SUCCESS] 保存了 {len(saved_images)} 张图像")
            
            # ========== 12. 保存新的JSON文件 ==========
            print(f"\n[PROCESSING] 开始保存JSON文件...")
            
            new_json_path = create_scene_json_file(
                map_name=map_name,
                room_name=room_name,
                table_entity=target_table,
                save_dir=output_dir
            )
            
            # 首先添加附近物品信息（包含重建的椅子和其他未删除的物品）
            if nearby_items:
                if print_info:
                    print(f"[INFO] 添加 {len(nearby_items)} 个附近物品到JSON（包含椅子和其他物品）")
                add_entities_to_json(
                    json_file_path=new_json_path,
                    entities=nearby_items,
                    entity_type='object',
                    owner='room'
                )
            
            # 添加桌面物品信息
            if generated_items and item_owners_list and item_features_list:
                if print_info:
                    print(f"[INFO] 添加 {len(generated_items)} 个桌面物品到JSON")
                # 组合features和owner
                complete_features = []
                for owner, features in zip(item_owners_list, item_features_list):
                    complete_features.append({'owner': owner, **features})
                
                add_entities_to_json(
                    json_file_path=new_json_path,
                    entities=generated_items,
                    entity_type='object',
                    owner=None,
                    features_list=complete_features
                )
            
            # 添加人物信息
            if generated_agents and agent_features_list:
                if print_info:
                    print(f"[INFO] 添加 {len(generated_agents)} 个人物到JSON")
                add_entities_to_json(
                    json_file_path=new_json_path,
                    entities=generated_agents,
                    entity_type='agent',
                    features_list=agent_features_list,
                    auto_detect_asset_type=False
                )
            
            # 添加摄像头信息
            if all_cameras:
                add_entities_to_json(
                    json_file_path=new_json_path,
                    entities=all_cameras,
                    entity_type='camera'
                )
            
            print(f"[SUCCESS] JSON文件已保存: {new_json_path}")
            
            # ========== 13. 清理实体 ==========
            if print_info:
                print(f"\n[INFO] 开始清理场景实体...")
            
            for agent in generated_agents:
                try:
                    ue.destroy_entity(agent.id)
                except:
                    pass
            
            for item in generated_items:
                try:
                    ue.destroy_entity(item.id)
                except:
                    pass
            
            for camera in all_cameras:
                try:
                    ue.destroy_entity(camera.id)
                except:
                    pass
            
            if print_info:
                print(f"[SUCCESS] 清理完成")
            
            # ========== 14. 返回结果 ==========
            result = {
                'success': True,
                'message': f'[SUCCESS] 场景重建完成: {len(generated_agents)} 人物, {len(generated_items)} 物品, {len(saved_images)} 图像',
                'output_dir': output_dir,
                'json_path': new_json_path,
                'images': list(saved_images.keys())
            }
            
            if print_info:
                print(f"\n{'='*60}")
                print(result['message'])
                print(f"输出目录: {output_dir}")
                print(f"{'='*60}\n")
            
            return result
    
    except Exception as e:
        error_msg = f'[ERROR] 精确重建场景失败: {str(e)}'
        print(error_msg)
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'message': error_msg
        }



# ============== 场景重建变化（原有函数）==============
# 人个数变化
# 人状态变化 sitting <-> standing
# 交换人的位置
# 交换人物蓝图
# 人动作变化 point_at_item, reach_item
# 桌面物品位置、旋转
# 桌面物品款式变化 根据人物特性变化
# 桌面物品的增减

# ============== 场景重建且变化（综合函数）==============
def rebuild_and_modify_scene_from_json(json_file_path, output_dir=None, 
                                       add_agent=False, placement_strategy='face_to_face', 
                                       reference_agent_index=0, new_agent_blueprint=None, 
                                       new_agent_trait=None, should_sit=True,
                                       change_agent_status=None,
                                       swap_agent_blueprints=None,
                                       replace_agent_blueprint=None,
                                       change_agent_action=None,
                                       change_item_type_count=0,
                                       adjust_item_count=0,
                                       move_item_count=0,
                                       print_info=True):
    """
    根据JSON文件重建场景并进行修改（基于rebuild_exact_scene_from_json）
    
    功能：
    1. 精确重建原始场景（椅子、人物、物品、动作）
    2. 可选：添加新人物
    3. 可选：改变人物状态（坐 ↔ 站）
    4. 可选：交换人物蓝图（与replace_agent_blueprint互斥）
    5. 可选：替换人物蓝图（与swap_agent_blueprints互斥）
    6. 可选：改变人物动作（point_at_item ↔ reach_item ↔ none）
    7. 可选：改变物品类型（根据其他人物的偏好随机替换）
    8. 可选：增加或减少桌面物品数量（随机生成或删除）
    9. 可选：移动物品到其他owner的区域（plate/platefood配对一起移动）
    10. 生成摄像头并拍摄图像
    11. 保存新的场景JSON文件
    
    Args:
        json_file_path: 场景JSON文件路径
        output_dir: 输出目录路径（可选）
        add_agent: 是否添加新人物（默认False）
        placement_strategy: 新人物放置策略 ('face_to_face', 'adjacent_sides', 'same_side')
        reference_agent_index: 参考人物的索引（默认0，指向位置而非ID）
        new_agent_blueprint: 新人物蓝图（可选，如果为None则自动选择不重复的蓝图）
        new_agent_trait: 新人物特性（可选，如果为None则根据蓝图推断）
        should_sit: 新人物是否坐下（默认True）
        change_agent_status: 需要改变状态的人物索引列表（可选），例如 [0, 2] 表示改变第0和第2个人物的状态
        swap_agent_blueprints: 需要交换蓝图的人物索引对（可选），例如 (0, 1) 表示交换第0和第1个人物的蓝图
                               ⚠️ 与 replace_agent_blueprint 互斥，只能使用其中一个
        replace_agent_blueprint: 需要替换蓝图的人物配置（可选），格式: (agent_index, new_blueprint)
                                例如 (0, 'SDBP_Aich_AIBaby_Lele_Shoes') 表示将索引0的人物替换为指定蓝图
                                ⚠️ 与 swap_agent_blueprints 互斥，只能使用其中一个
        change_agent_action: 需要改变动作的人物配置（可选），格式: {agent_index: new_action_type}
                           例如 {0: 'reach_item', 1: 'none', 2: 'point_at_item'}
                           - 'none': 取消动作
                           - 'point_at_item': 改为指向动作（如果原本是reach_item，会使用同一物品）
                           - 'reach_item': 改为伸手动作（如果原本是point_at_item，会随机选择owner物品）
        change_item_type_count: 需要改变类型的物品数量（默认0）
                              会随机选择指定数量的物品，根据其他人物的偏好替换物品类型
                              例如：如果设置为2，会随机选择2个物品进行类型替换
        adjust_item_count: 需要增加或减少的物品数量（默认0）
                          正数表示增加物品（例如 2 表示增加2个物品）
                          负数表示减少物品（例如 -2 表示删除2个物品）
                          0 表示不修改物品数量
                          ⚠️ 增加逻辑：在物品生成后，随机选择人物在其区域内生成新物品
                          ⚠️ 减少逻辑：在物品生成前，从table_items_data中随机删除指定数量
        move_item_count: 需要移动到其他owner区域的物品数量（默认0）
                        正数表示随机选择指定数量的物品，将其从当前owner的区域移动到其他owner的区域
                        例如：如果设置为2，会随机选择2个物品移动到不同的owner
                        ⚠️ plate/platefood配对会一起移动
                        ⚠️ 移动后物品的owner会改变
        print_info: 是否打印详细信息
    
    Returns:
        dict: 重建结果 {
            'success': bool,
            'message': str,
            'output_dir': str,
            'json_path': str,
            'images': list,
            'agent_count': int,  # 最终人物数量
            'added_agent': bool  # 是否成功添加了新人物
        }
    """
    try:
        # 检查输入文件
        if not os.path.exists(json_file_path):
            return {
                'success': False,
                'message': f'[ERROR] JSON文件不存在: {json_file_path}'
            }
        
        # 确定输出目录
        if output_dir is None:
            json_dir = os.path.dirname(json_file_path)
            output_dir = os.path.join(json_dir, 'rebuild_modified')
        
        os.makedirs(output_dir, exist_ok=True)
        
        if print_info:
            print(f"\n{'='*60}")
            print(f"开始重建并修改场景: {json_file_path}")
            print(f"输出目录: {output_dir}")
            if add_agent:
                print(f"将添加新人物: strategy={placement_strategy}, ref_index={reference_agent_index}")
            print(f"{'='*60}")
        
        # ========== 1. 加载JSON数据 ==========
        with open(json_file_path, 'r', encoding='utf-8') as f:
            scene_data = json.load(f)
        
        scene_info = scene_data.get('scene_info', {})
        map_name = scene_info.get('map_name')
        room_name = scene_info.get('room_name')
        table_id = scene_info.get('table_id')
        
        if not all([map_name, room_name, table_id]):
            return {
                'success': False,
                'message': '[ERROR] JSON文件缺少必要的场景信息'
            }
        
        if print_info:
            print(f"[INFO] 场景信息: {map_name} - {room_name} - {table_id}")
        
        # ========== 2. 连接TongSim ==========
        if print_info:
            print(f"\n[PROCESSING] 正在连接TongSim...")
        
        with ts.TongSim(
            grpc_endpoint="127.0.0.1:5056",
            legacy_grpc_endpoint="127.0.0.1:50052",
        ) as ue:
            
            # ========== 3. 打开地图和房间 ==========
            print(f"{'='*60}")
            print(f"[PROCESSING] 正在打开地图和房间...")
            print(f"{'='*60}")
            
            success = ue.open_level(map_name)
            if not success:
                return {
                    'success': False,
                    'message': f'[WARNING] 无法打开地图: {map_name}'
                }
            
            # 获取房间信息
            rooms = ue.spatical_manager.get_current_room_info()
            room_bbox_dict = get_room_bbox(rooms)
            room_bound = get_room_boundary(room_name, room_bbox_dict)
            
            if not room_bound:
                return {
                    'success': False,
                    'message': f'[ERROR] 无法获取房间边界: {room_name}'
                }
            
            # ========== 4. 查找桌子 ==========
            print(f"[PROCESSING] 正在查找桌子: {table_id}...")
            
            table_entitys = query_existing_objects_in_room(
                ue=ue, 
                room_bound=room_bound, 
                target_types=['coffeetable', 'diningTable', 'table', 'Table'], 
                object_name="桌子",
                print_info=False
            )
            
            if not table_entitys:
                return {
                    'success': False,
                    'message': f'[ERROR] 房间 {room_name} 中没有找到桌子'
                }
            
            target_table = None
            for table_entity in table_entitys:
                entity_base_id = str(table_entity.id)
                if table_id in entity_base_id or entity_base_id in table_id:
                    target_table = table_entity
                    break
            
            if not target_table:
                return {
                    'success': False,
                    'message': f'[WARNING] 未找到完全匹配的桌子 {table_id}'
                }
            
            print(f"[INFO] 找到桌子: {target_table.id}")
            
            # ========== 5. 查找附近物体并删除现有椅子 ==========
            print(f"\n[PROCESSING] 正在查找附近物体...")
            
            on_table_items, nearby_items = find_objects_near_table(
                ue=ue,
                table_object=target_table,
                search_distance=120.0,
                print_info=False
            )
            
            if on_table_items:
                if print_info:
                    print(f"[INFO] 正在删除桌子上的 {len(on_table_items)} 个物品...")
                for item in on_table_items:
                    try:
                        ue.destroy_entity(item.id)
                    except Exception as e:
                        print(f"[WARNING] 删除物品失败: {e}")
            
            existed_chairs = filter_objects_by_type(objects_list=nearby_items, type_file_path='./ownership/object/chair.txt')
            if existed_chairs:
                if print_info:
                    print(f"[INFO] 正在删除 {len(existed_chairs)} 把现有椅子...")
                for chair in existed_chairs:
                    try:
                        ue.destroy_entity(chair.id)
                    except Exception as e:
                        print(f"[WARNING] 删除椅子失败: {e}")
            
            # ========== 6. 从JSON重建椅子 ==========
            if print_info:
                print(f"\n[PROCESSING] 开始从JSON重建椅子...")
            
            room_objects = scene_data.get('objects', [])
            json_room_data = [obj for obj in room_objects 
                               if obj.get('type') == 'object' and obj.get('owner') == 'room']
            
            chair_types = []
            try:
                with open('./ownership/object/chair.txt', 'r', encoding='utf-8') as f:
                    chair_types = [line.strip() for line in f if line.strip()]
            except Exception as e:
                print(f"[WARNING] 无法读取椅子类型文件: {e}")
            
            rebuilt_chairs = []
            for chair_data in json_room_data:
                base_id = chair_data.get('base_id', '')
                is_chair = any(chair_type in base_id for chair_type in chair_types)
                
                if is_chair:
                    try:
                        pos = chair_data['position']
                        rot = chair_data['rotation']
                        
                        new_chair = ue.spawn_entity(
                            entity_type=ts.BaseObjectEntity,
                            blueprint=base_id,
                            location=ts.Vector3(pos['x'], pos['y'], pos['z']),
                            is_simulating_physics=True,
                            quat=ts.Quaternion(rot['w'], rot['x'], rot['y'], rot['z'])
                        )
                        
                        rebuilt_chairs.append(new_chair)
                        
                        if print_info:
                            print(f"[SUCCESS] 重建椅子: {base_id} at ({pos['x']:.1f}, {pos['y']:.1f})")
                    
                    except Exception as e:
                        print(f"[ERROR] 重建椅子失败 {base_id}: {e}")
            
            if print_info:
                print(f"[SUCCESS] 共重建 {len(rebuilt_chairs)} 把椅子")
            
            # 更新nearby_items
            existed_chair_ids = {str(chair.id) for chair in existed_chairs}
            updated_nearby_items = [item for item in nearby_items if str(item.id) not in existed_chair_ids]
            updated_nearby_items.extend(rebuilt_chairs)
            nearby_items = updated_nearby_items
            
            if print_info:
                print(f"[INFO] 更新nearby_items: {len(nearby_items)} 个物品")
            
            # ========== 6.5. 交换或替换人物蓝图（如果需要）==========
            agents_data = scene_data.get('agents', [])
            if not agents_data:
                return {
                    'success': False,
                    'message': '[ERROR] JSON中没有人物数据'
                }
            
            # 检查互斥性：swap_agent_blueprints 和 replace_agent_blueprint 不能同时使用
            if swap_agent_blueprints is not None and replace_agent_blueprint is not None:
                print(f"[WARNING] swap_agent_blueprints 和 replace_agent_blueprint 不能同时使用，将优先使用 replace_agent_blueprint")
                swap_agent_blueprints = None
            
            # 选项1: 交换人物蓝图（两个人物互换）
            if swap_agent_blueprints is not None:
                if not isinstance(swap_agent_blueprints, (tuple, list)) or len(swap_agent_blueprints) != 2:
                    print(f"[WARNING] swap_agent_blueprints 格式错误，应为包含两个索引的元组或列表，跳过交换")
                else:
                    idx1, idx2 = swap_agent_blueprints
                    
                    # 验证索引有效性
                    if 0 <= idx1 < len(agents_data) and 0 <= idx2 < len(agents_data):
                        # 获取两个人物的蓝图
                        blueprint1 = agents_data[idx1].get('base_id')
                        blueprint2 = agents_data[idx2].get('base_id')
                        
                        # 交换蓝图
                        agents_data[idx1]['base_id'] = blueprint2
                        agents_data[idx2]['base_id'] = blueprint1
                        
                        if print_info:
                            print(f"\n{'='*60}")
                            print(f"[PROCESSING] 交换人物蓝图")
                            print(f"{'='*60}")
                            print(f"  人物索引 {idx1}: {blueprint1} → {blueprint2}")
                            print(f"  人物索引 {idx2}: {blueprint2} → {blueprint1}")
                            print(f"  位置 {idx1}: ({agents_data[idx1]['position']['x']:.1f}, {agents_data[idx1]['position']['y']:.1f})")
                            print(f"  位置 {idx2}: ({agents_data[idx2]['position']['x']:.1f}, {agents_data[idx2]['position']['y']:.1f})")
                            print(f"  注意: 蓝图已交换，但位置、动作、状态等保持不变")
                            print(f"{'='*60}\n")
                    else:
                        print(f"[WARNING] 人物索引超出范围: idx1={idx1}, idx2={idx2}, 人物总数={len(agents_data)}，跳过交换")
            
            # 选项2: 替换人物蓝图（将某个人物替换为指定蓝图）
            elif replace_agent_blueprint is not None:
                if not isinstance(replace_agent_blueprint, (tuple, list)) or len(replace_agent_blueprint) != 2:
                    print(f"[WARNING] replace_agent_blueprint 格式错误，应为 (agent_index, new_blueprint)，跳过替换")
                else:
                    agent_idx, new_blueprint = replace_agent_blueprint
                    
                    # 验证索引有效性
                    if 0 <= agent_idx < len(agents_data):
                        # 获取原蓝图
                        old_blueprint = agents_data[agent_idx].get('base_id')
                        
                        # 替换蓝图
                        agents_data[agent_idx]['base_id'] = new_blueprint
                        
                        if print_info:
                            print(f"\n{'='*60}")
                            print(f"[PROCESSING] 替换人物蓝图")
                            print(f"{'='*60}")
                            print(f"  人物索引 {agent_idx}: {old_blueprint} → {new_blueprint}")
                            print(f"  位置: ({agents_data[agent_idx]['position']['x']:.1f}, {agents_data[agent_idx]['position']['y']:.1f})")
                            print(f"  注意: 蓝图已替换，但位置、动作、状态等保持不变")
                            print(f"{'='*60}\n")
                    else:
                        print(f"[WARNING] 人物索引超出范围: agent_idx={agent_idx}, 人物总数={len(agents_data)}，跳过替换")
            
            # ========== 7. 精确重建人物 ==========
            print(f"\n[PROCESSING] 开始精确重建人物...")
            
            generated_agents = []
            agent_actions = []
            agent_features_list = []
            agent_id_mapping = {}  # 添加agent ID映射：old_agent_id -> new_agent_id
            
            for i, agent_data in enumerate(agents_data):
                try:
                    base_id = agent_data.get('base_id')
                    position = agent_data.get('position')
                    rotation = agent_data.get('rotation')
                    features = agent_data.get('features', {})
                    old_agent_id = agent_data.get('id')  # 获取旧场景中的agent ID
                    
                    if not all([base_id, position, rotation]):
                        print(f"[WARNING] 人物 {i} 数据不完整，跳过")
                        continue
                    
                    status = features.get('status', 'standing')
                    agent = None
                    sit_success = False
                    
                    if status == 'sitting':
                        agent = ue.spawn_agent(
                            blueprint=base_id,
                            location=ts.Vector3(position['x'], position['y'], position['z'] + 70),
                            desired_name=f"{base_id}_{i}",
                            quat=ts.Quaternion(rotation['w'], rotation['x'], rotation['y'], rotation['z']),
                            scale=None
                        )
                        target_location = ts.Vector3(position['x'], position['y'], position['z'])
                        
                        closest_chair = None
                        min_distance = float('inf')
                        
                        for chair in rebuilt_chairs:
                            chair_pos = chair.get_location()
                            distance = ((chair_pos.x - target_location.x)**2 + 
                                       (chair_pos.y - target_location.y)**2 + 
                                       (chair_pos.z - target_location.z)**2) ** 0.5
                            
                            if distance < min_distance:
                                min_distance = distance
                                closest_chair = chair
                        
                        if closest_chair:
                            agent.do_action(ts.action.MoveToObject(object_id=closest_chair.id, speed=1000))
                            sit_result = agent.do_action(ts.action.SitDownToObject(object_id=closest_chair.id))
                            
                            if sit_result and len(sit_result) > 0:
                                for result in sit_result:
                                    if hasattr(result, 'status') and result.status == 'end' and result.error_code == 0:
                                        sit_success = True
                                        break
                            
                            if sit_success:
                                features['chair_id'] = closest_chair.id
                                print(f"[SUCCESS] 人物 {i}: {base_id} 成功坐在椅子 {closest_chair.id}")
                            else:
                                print(f"[WARNING] 人物 {i}: {base_id} 坐下失败，删除后重新创建为站立")
                                ue.destroy_entity(agent.id)
                                agent = None
                        else:
                            print(f"[WARNING] 人物 {i}: {base_id} 没有找到可用椅子，删除后重新创建为站立")
                            ue.destroy_entity(agent.id)
                            agent = None
                    
                    if status == 'standing' or (status == 'sitting' and not sit_success):
                        agent = ue.spawn_agent(
                            blueprint=base_id,
                            location=ts.Vector3(position['x'], position['y'], position['z'] + 70),
                            desired_name=f"{base_id}_{i}",
                            quat=ts.Quaternion(rotation['w'], rotation['x'], rotation['y'], rotation['z']),
                            scale=None
                        )
                        print(f"[SUCCESS] 人物 {i}: {base_id} 站立 at ({position['x']:.1f}, {position['y']:.1f})")
                    
                    if agent is not None:
                        generated_agents.append(agent)
                        
                        # 建立agent ID映射
                        if old_agent_id:
                            agent_id_mapping[old_agent_id] = str(agent.id)
                        
                        new_features = {
                            'type': features.get('type', 'unknown'),
                            'status': 'sitting' if sit_success else 'standing'
                        }
                        
                        if sit_success:
                            new_features['chair_id'] = closest_chair.id
                        
                        # 保留动作相关信息到 features
                        action_type = features.get('action', 'none')
                        if action_type and action_type != 'none':
                            new_features['action'] = action_type
                            if 'reach_item_id' in features:
                                new_features['reach_item_id'] = features.get('reach_item_id')
                            if 'point_item_id' in features:
                                new_features['point_item_id'] = features.get('point_item_id')
                        
                        # 始终添加到待执行动作列表（保持索引一致性）
                        agent_actions.append({
                            'agent': agent,
                            'action_type': action_type,
                            'old_reach_item_id': features.get('reach_item_id'),
                            'old_point_item_id': features.get('point_item_id')
                        })
                        
                        agent_features_list.append(new_features)
                    else:
                        print(f"[ERROR] 人物 {i}: {base_id} 创建失败")
                
                except Exception as e:
                    print(f"[ERROR] 生成人物 {i} 失败: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            if not generated_agents:
                return {
                    'success': False,
                    'message': '[ERROR] 没有成功生成任何人物'
                }
            
            # ========== 7.5a. 统计可用椅子（为添加新人物做准备）==========
            # 收集所有已被占用的椅子ID
            occupied_chair_ids = set()
            for features in agent_features_list:
                if features.get('status') == 'sitting':
                    chair_id = features.get('chair_id')
                    if chair_id:
                        occupied_chair_ids.add(str(chair_id))
            
            # 从重建的椅子中筛选出未被占用的椅子
            available_chairs = []
            for chair in rebuilt_chairs:
                if str(chair.id) not in occupied_chair_ids:
                    available_chairs.append(chair)
            
            if print_info:
                print(f"\n[INFO] 椅子占用情况统计:")
                print(f"  总椅子数: {len(rebuilt_chairs)}")
                print(f"  已占用: {len(occupied_chair_ids)}")
                print(f"  可用椅子: {len(available_chairs)}")
            
            # ========== 7.5b. 改变人物状态（如果需要）==========
            if change_agent_status is not None and len(change_agent_status) > 0:
                print(f"\n{'='*60}")
                print(f"[PROCESSING] 开始改变人物状态...")
                print(f"{'='*60}")
                
                import time
                import random
                from .agent_util import determine_object_side
                
                # 获取桌子的AABB边界
                table_aabb = target_table.get_world_aabb()
                table_min, table_max = fix_aabb_bounds(table_aabb)
                
                for agent_idx in change_agent_status:
                    if agent_idx < 0 or agent_idx >= len(generated_agents):
                        print(f"[WARNING] 人物索引 {agent_idx} 超出范围，跳过")
                        continue
                    
                    target_agent = generated_agents[agent_idx]
                    current_status = agent_features_list[agent_idx].get('status')
                    
                    if print_info:
                        print(f"\n[INFO] 处理人物 {agent_idx}: 当前状态={current_status}")
                    
                    # 情况1: 从坐着变为站立
                    if current_status == 'sitting':
                        try:
                            # 获取当前坐的椅子
                            current_chair_id = agent_features_list[agent_idx].get('chair_id')
                            chair_entity = None
                            
                            # 找到椅子实体
                            for chair in rebuilt_chairs:
                                if str(chair.id) == str(current_chair_id):
                                    chair_entity = chair
                                    break
                            
                            if not chair_entity:
                                print(f"[WARNING] 人物 {agent_idx} 的椅子未找到，跳过")
                                continue
                            
                            # 获取椅子位置
                            chair_pos = chair_entity.get_location()
                            agent_data = agents_data[agent_idx]
                            base_id = agent_data.get('base_id')
                            
                            # 使用导航系统找到椅子附近的可站立位置
                            final_position = ue.spatical_manager.get_nearest_nav_position(target_location=chair_pos)
                            
                            # 删除旧的人物实体
                            old_agent_id = target_agent.id
                            ue.destroy_entity(old_agent_id)
                            
                            # 计算朝向桌子的方向
                            table_target_x = random.uniform(table_min.x, table_max.x)
                            table_target_y = random.uniform(table_min.y, table_max.y)
                            towards_position = ts.Vector3(table_target_x, table_target_y, table_max.z)
                            
                            # 在新位置重新创建站立的人物
                            new_agent = ue.spawn_agent(
                                blueprint=base_id,
                                location=ts.Vector3(final_position.x, final_position.y, final_position.z + 70),
                                desired_name=f"{base_id}_{agent_idx}_standing",
                                quat=None,
                                scale=None
                            )
                            
                            # 移动和转向
                            new_agent.do_action(ts.action.MoveToLocation(loc=final_position))
                            new_agent.do_action(ts.action.TurnToLocation(loc=towards_position))
                            
                            # 更新人物列表和特征
                            generated_agents[agent_idx] = new_agent
                            agent_features_list[agent_idx] = {
                                'type': agent_features_list[agent_idx].get('type', 'unknown'),
                                'status': 'standing'
                            }
                            
                            # 释放椅子，添加到可用椅子列表
                            if current_chair_id and str(current_chair_id) in occupied_chair_ids:
                                occupied_chair_ids.remove(str(current_chair_id))
                                available_chairs.append(chair_entity)
                            
                            if print_info:
                                print(f"[SUCCESS] 人物 {agent_idx} 从坐着变为站立")
                        
                        except Exception as e:
                            print(f"[ERROR] 人物 {agent_idx} 状态改变失败: {e}")
                            import traceback
                            traceback.print_exc()
                    
                    # 情况2: 从站立变为坐着
                    elif current_status == 'standing':
                        try:
                            # 确定人物相对于桌子的方位
                            agent_side = determine_object_side(target_agent, target_table)
                            
                            if print_info:
                                print(f"[INFO] 人物 {agent_idx} 位于桌子的 {agent_side} 侧")
                            
                            # 找到同侧的可用椅子
                            same_side_chairs = []
                            for chair in available_chairs:
                                chair_side = determine_object_side(chair, target_table)
                                if chair_side == agent_side:
                                    same_side_chairs.append(chair)
                            
                            if not same_side_chairs:
                                if print_info:
                                    print(f"[ERROR] 人物 {agent_idx} 所在侧没有可用椅子，状态改变失败")
                                # 返回失败，让pipeline删除文件夹
                                return {
                                    'success': False,
                                    'message': f'[ERROR] 人物 {agent_idx} 无法坐下：所在侧没有可用椅子',
                                    'error_type': 'no_available_chair'
                                }
                            
                            # 选择最近的椅子
                            agent_pos = target_agent.get_location()
                            closest_chair = None
                            min_distance = float('inf')
                            
                            for chair in same_side_chairs:
                                chair_pos = chair.get_location()
                                distance = ((chair_pos.x - agent_pos.x)**2 + 
                                           (chair_pos.y - agent_pos.y)**2 + 
                                           (chair_pos.z - agent_pos.z)**2) ** 0.5
                                
                                if distance < min_distance:
                                    min_distance = distance
                                    closest_chair = chair
                            
                            if closest_chair:
                                # 移动到椅子并坐下
                                target_agent.do_action(ts.action.MoveToObject(object_id=closest_chair.id, speed=1000))
                                sit_result = target_agent.do_action(ts.action.SitDownToObject(object_id=closest_chair.id))
                                
                                # 检查坐下是否成功
                                sit_success = False
                                if sit_result and len(sit_result) > 0:
                                    for result in sit_result:
                                        if hasattr(result, 'status') and result.status == 'end' and result.error_code == 0:
                                            sit_success = True
                                            break
                                
                                if sit_success:
                                    # 获取原有特征信息
                                    features = agent_features_list[agent_idx]
                                    agent_type = features.get('type', 'unknown')
                                    
                                    # 更新特征列表（保留其他信息）
                                    agent_features_list[agent_idx] = {
                                        'type': agent_type,
                                        'status': 'sitting',
                                        'chair_id': closest_chair.id
                                    }
                                    
                                    # 处理动作：站立→坐下时，取消reach动作
                                    action_type = features.get('action')
                                    if action_type and action_type != 'none':
                                        # 如果是reach_item动作，取消该动作
                                        if action_type == 'reach_item':
                                            if print_info:
                                                print(f"[INFO] 人物 {agent_idx} 从站立变为坐着，取消 reach_item 动作")
                                            # 不添加到agent_actions，相当于取消
                                        # 如果是point_at_item动作，保留该动作
                                        elif action_type == 'point_at_item':
                                            if print_info:
                                                print(f"[INFO] 人物 {agent_idx} 从站立变为坐着，保留 point_at_item 动作")
                                            agent_features_list[agent_idx]['action'] = action_type
                                            agent_features_list[agent_idx]['point_item_id'] = features.get('point_item_id')
                                            # 添加到待执行动作列表
                                            agent_actions.append({
                                                'agent': target_agent,
                                                'action_type': action_type,
                                                'old_reach_item_id': features.get('reach_item_id'),
                                                'old_point_item_id': features.get('point_item_id')
                                            })
                                        else:
                                            # 其他动作类型也保留
                                            if print_info:
                                                print(f"[INFO] 人物 {agent_idx} 从站立变为坐着，保留 {action_type} 动作")
                                            agent_features_list[agent_idx]['action'] = action_type
                                            if 'reach_item_id' in features:
                                                agent_features_list[agent_idx]['reach_item_id'] = features.get('reach_item_id')
                                            if 'point_item_id' in features:
                                                agent_features_list[agent_idx]['point_item_id'] = features.get('point_item_id')
                                            agent_actions.append({
                                                'agent': target_agent,
                                                'action_type': action_type,
                                                'old_reach_item_id': features.get('reach_item_id'),
                                                'old_point_item_id': features.get('point_item_id')
                                            })
                                    
                                    # 从可用椅子列表中移除，添加到占用列表
                                    available_chairs.remove(closest_chair)
                                    occupied_chair_ids.add(str(closest_chair.id))
                                    
                                    if print_info:
                                        print(f"[SUCCESS] 人物 {agent_idx} 从站立变为坐着，椅子: {closest_chair.id}")
                                else:
                                    # 坐下失败，返回错误
                                    if print_info:
                                        print(f"[ERROR] 人物 {agent_idx} 坐下失败")
                                    return {
                                        'success': False,
                                        'message': f'[ERROR] 人物 {agent_idx} 坐下动作执行失败',
                                        'error_type': 'sit_action_failed'
                                    }
                        
                        except Exception as e:
                            print(f"[ERROR] 人物 {agent_idx} 状态改变失败: {e}")
                            import traceback
                            traceback.print_exc()
                
                if print_info:
                    print(f"\n[INFO] 状态改变完成，更新椅子占用情况:")
                    print(f"  已占用: {len(occupied_chair_ids)}")
                    print(f"  可用椅子: {len(available_chairs)}")
            
            # ========== 7.5c. 添加新人物（如果需要）==========
            added_agent_success = False
            if add_agent:
                print(f"\n{'='*60}")
                print(f"[PROCESSING] 开始添加新人物...")
                print(f"{'='*60}")
                
                # 如果没有指定蓝图，则从已有人物中排除重复的蓝图
                if new_agent_blueprint is None:
                    import random
                    from configs.agent_config import AGENT_BLUEPRINT_MAPPING
                    
                    # 收集已有人物的蓝图
                    existing_blueprints = set()
                    for agent_data in agents_data:
                        base_id = agent_data.get('base_id', '')
                        if base_id:
                            existing_blueprints.add(base_id)
                    
                    if print_info:
                        print(f"[INFO] 已有人物蓝图: {existing_blueprints}")
                    
                    # 收集所有可用的蓝图（不与已有蓝图重复）
                    available_blueprints = []
                    for trait, blueprints in AGENT_BLUEPRINT_MAPPING.items():
                        for blueprint in blueprints:
                            if blueprint not in existing_blueprints:
                                available_blueprints.append((blueprint, trait))
                    
                    if not available_blueprints:
                        # 如果所有蓝图都已使用，则从所有蓝图中随机选择
                        if print_info:
                            print(f"[WARNING] 所有蓝图已被使用，将随机选择任意蓝图")
                        all_blueprints = [(bp, trait) for trait, blueprints in AGENT_BLUEPRINT_MAPPING.items() for bp in blueprints]
                        new_agent_blueprint, new_agent_trait = random.choice(all_blueprints)
                    else:
                        new_agent_blueprint, auto_trait = random.choice(available_blueprints)
                        if new_agent_trait is None:
                            new_agent_trait = auto_trait
                    
                    if print_info:
                        print(f"[INFO] 选择新人物蓝图: {new_agent_blueprint}")
                        print(f"[INFO] 新人物特性: {new_agent_trait}")
                
                else:
                    # 检查指定的蓝图是否与已有蓝图重复
                    existing_blueprints = set()
                    for agent_data in agents_data:
                        base_id = agent_data.get('base_id', '')
                        if base_id:
                            existing_blueprints.add(base_id)
                    
                    if new_agent_blueprint in existing_blueprints:
                        if print_info:
                            print(f"[WARNING] 指定的蓝图 {new_agent_blueprint} 与已有人物重复，将重新选择")
                        
                        import random
                        from configs.agent_config import AGENT_BLUEPRINT_MAPPING
                        
                        available_blueprints = []
                        for trait, blueprints in AGENT_BLUEPRINT_MAPPING.items():
                            for blueprint in blueprints:
                                if blueprint not in existing_blueprints:
                                    available_blueprints.append((blueprint, trait))
                        
                        if available_blueprints:
                            new_agent_blueprint, auto_trait = random.choice(available_blueprints)
                            if new_agent_trait is None:
                                new_agent_trait = auto_trait
                            if print_info:
                                print(f"[INFO] 重新选择新人物蓝图: {new_agent_blueprint}")
                        else:
                            if print_info:
                                print(f"[WARNING] 无可用蓝图，保持原蓝图")
                    
                    # 根据蓝图推断特性
                    if new_agent_trait is None:
                        from configs.agent_config import AGENT_BLUEPRINT_MAPPING
                        for trait, blueprints in AGENT_BLUEPRINT_MAPPING.items():
                            if new_agent_blueprint in blueprints:
                                new_agent_trait = trait
                                break
                        if new_agent_trait is None:
                            new_agent_trait = 'unknown'
                        
                        if print_info:
                            print(f"[INFO] 推断新人物特性: {new_agent_trait}")
                
                # 使用add_agent_to_existing_scene添加新人物
                new_agent, new_agent_features, updated_nearby_items = add_agent_to_existing_scene(
                    ue=ue,
                    table_object=target_table,
                    room_bound=room_bound,
                    nearby_objects=nearby_items,
                    existing_agents=generated_agents,
                    placement_strategy=placement_strategy,
                    reference_agent_index=reference_agent_index,
                    new_agent_blueprint=new_agent_blueprint,
                    new_agent_trait=new_agent_trait,
                    should_sit=should_sit,
                    available_chairs=available_chairs,  # 传递可用椅子列表
                    min_distance=10,
                    max_distance=90,
                    min_agent_distance=60,
                    max_agent_distance=300,
                    safe_margin=15,
                    max_chair_adjust_attempts=8,
                    chair_move_step=5.0,
                    print_info=print_info
                )
                
                if new_agent is not None:
                    generated_agents.append(new_agent)
                    agent_features_list.append(new_agent_features)
                    nearby_items = updated_nearby_items
                    added_agent_success = True
                    
                    if print_info:
                        print(f"[SUCCESS] 成功添加新人物: {new_agent.id}")
                        print(f"[INFO] 最终人物数量: {len(generated_agents)}")
                else:
                    if print_info:
                        print(f"[WARNING] 添加新人物失败")
            
            # ========== 8. 精确重建桌面物品 ==========
            if print_info:
                print(f"\n[PROCESSING] 开始精确重建桌面物品...")
            
            table_items_data = [obj for obj in scene_data.get('objects', []) 
                               if obj.get('type') == 'object' 
                               and obj.get('owner') 
                               and obj.get('owner') != 'room']
            
            if print_info:
                print(f"[INFO] 找到 {len(table_items_data)} 个桌面物品")
            
            # ========== 8.3. 减少桌面物品（如果需要）==========
            removed_items_data = []
            if adjust_item_count < 0:
                remove_count = abs(adjust_item_count)
                remove_count = min(remove_count, len(table_items_data))
                
                if print_info:
                    print(f"\n{'='*60}")
                    print(f"[PROCESSING] 开始减少桌面物品...")
                    print(f"[INFO] 需要删除 {remove_count} 个物品")
                    print(f"{'='*60}")
                
                import random
                
                # 随机选择要删除的物品
                if remove_count > 0:
                    items_to_remove = random.sample(range(len(table_items_data)), remove_count)
                    items_to_remove = sorted(items_to_remove, reverse=True)  # 从大到小删除，避免索引错位
                    
                    for idx in items_to_remove:
                        removed_item = table_items_data.pop(idx)
                        removed_items_data.append(removed_item)
                        if print_info:
                            item_type = removed_item.get('features', {}).get('type', 'unknown')
                            owner = removed_item.get('owner', 'unknown')
                            print(f"[INFO] 删除物品 {idx}: type={item_type}, owner={owner}")
                    
                    if print_info:
                        print(f"[SUCCESS] 删除了 {len(removed_items_data)} 个物品")
                        print(f"[INFO] 剩余物品数: {len(table_items_data)}")
                        print(f"{'='*60}\n")
            
            # ========== 8.5. 修改物品类型（如果需要）==========
            if print_info:
                print(f"[DEBUG] 物品修改检查: change_item_type_count={change_item_type_count}, table_items数量={len(table_items_data)}")
            
            if change_item_type_count > 0 and len(table_items_data) > 0:
                print(f"\n{'='*60}")
                print(f"[PROCESSING] 开始修改物品类型...")
                print(f"[INFO] 需要修改 {change_item_type_count} 个物品")
                print(f"{'='*60}")
                
                import random
                from configs.item_config import AGENT_ITEM_MAPPING, COMMON_ITEMS, ITEM_BLUEPRINTS
                
                # 1. 建立 owner ID 到人物类型的映射
                owner_to_agent_type = {}
                for agent_data in agents_data:
                    agent_id = agent_data.get('id')
                    agent_type = agent_data.get('features', {}).get('type', 'unknown')
                    if agent_id:
                        owner_to_agent_type[agent_id] = agent_type
                
                # 2. 收集所有人物类型（用于选择其他人的偏好）
                all_agent_types = set(owner_to_agent_type.values())
                
                if print_info:
                    print(f"[INFO] 场景中的人物类型: {all_agent_types}")
                
                # 3. 识别 platefood 的配对关系（盘子和食物）
                platefood_pairs = {}  # {food_idx: plate_idx} 或 {plate_idx: food_idx}
                for i, item_data in enumerate(table_items_data):
                    item_type = item_data.get('features', {}).get('type', '')
                    owner = item_data.get('owner', '')
                    
                    if item_type == 'platefood' or item_type == 'plate':
                        # 查找同一owner的配对物品
                        for j, other_item in enumerate(table_items_data):
                            if i != j and other_item.get('owner') == owner:
                                other_type = other_item.get('features', {}).get('type', '')
                                
                                # platefood 配对 plate
                                if (item_type == 'platefood' and other_type == 'plate') or \
                                   (item_type == 'plate' and other_type == 'platefood'):
                                    platefood_pairs[i] = j
                                    platefood_pairs[j] = i
                                    break
                
                if print_info and platefood_pairs:
                    print(f"[INFO] 识别到 {len(platefood_pairs)//2} 对 platefood 配对")
                
                # 4. 收集可修改的物品索引（排除已经配对的盘子/食物，只保留一个代表）
                modifiable_items = []
                processed_pairs = set()
                
                for i, item_data in enumerate(table_items_data):
                    item_type = item_data.get('features', {}).get('type', '')
                    
                    # 如果是配对物品，只添加一次
                    if i in platefood_pairs:
                        pair_idx = platefood_pairs[i]
                        pair_key = tuple(sorted([i, pair_idx]))
                        
                        if pair_key not in processed_pairs:
                            processed_pairs.add(pair_key)
                            modifiable_items.append(i)  # 只添加第一个
                    else:
                        modifiable_items.append(i)
                
                # 5. 随机选择要修改的物品
                actual_change_count = min(change_item_type_count, len(modifiable_items))
                selected_indices = random.sample(modifiable_items, actual_change_count)
                
                if print_info:
                    print(f"[INFO] 随机选择 {actual_change_count} 个物品进行类型修改")
                
                # 6. 为每个选中的物品替换类型
                items_to_remove = set()  # 需要删除的物品索引（配对的另一半）
                
                for item_idx in selected_indices:
                    item_data = table_items_data[item_idx]
                    owner_id = item_data.get('owner', '')
                    old_item_type = item_data.get('features', {}).get('type', '')
                    old_base_id = item_data.get('base_id', '')
                    
                    # 获取owner的人物类型
                    owner_type = owner_to_agent_type.get(owner_id, 'unknown')
                    
                    # 收集其他人的偏好物品类型
                    other_types_items = []
                    for agent_type in all_agent_types:
                        if agent_type != owner_type:  # 排除自己的类型
                            other_types_items.extend(AGENT_ITEM_MAPPING.get(agent_type, []))
                    
                    # 添加通用物品
                    other_types_items.extend(COMMON_ITEMS)
                    
                    # 去重并排除当前物品类型
                    available_types = list(set(other_types_items))
                    if old_item_type in available_types:
                        available_types.remove(old_item_type)
                    
                    if not available_types:
                        if print_info:
                            print(f"[WARNING] 物品 {item_idx} 没有可替换的类型，跳过")
                        continue
                    
                    # 随机选择新类型
                    new_item_type = random.choice(available_types)
                    
                    # 从 ITEM_BLUEPRINTS 中获取对应的蓝图
                    new_blueprints = ITEM_BLUEPRINTS.get(new_item_type, [])
                    if not new_blueprints:
                        if print_info:
                            print(f"[WARNING] 物品类型 {new_item_type} 没有对应的蓝图，跳过")
                        continue
                    
                    new_base_id = random.choice(new_blueprints)
                    
                    # 更新物品数据
                    table_items_data[item_idx]['base_id'] = new_base_id
                    table_items_data[item_idx]['features']['type'] = new_item_type
                    
                    if print_info:
                        print(f"[INFO] 物品 {item_idx}: {old_item_type} ({old_base_id}) → {new_item_type} ({new_base_id})")
                        print(f"       Owner类型: {owner_type} → 替换为其他类型的偏好物品")
                    
                    # 如果是配对物品，标记另一半需要删除
                    if item_idx in platefood_pairs:
                        pair_idx = platefood_pairs[item_idx]
                        items_to_remove.add(pair_idx)
                        if print_info:
                            pair_type = table_items_data[pair_idx].get('features', {}).get('type', '')
                            print(f"       配对物品 {pair_idx} ({pair_type}) 将被删除")
                
                # 7. 删除需要移除的配对物品
                if items_to_remove:
                    # 从大到小排序索引，避免删除时索引错位
                    sorted_remove = sorted(items_to_remove, reverse=True)
                    for idx in sorted_remove:
                        removed_item = table_items_data.pop(idx)
                        if print_info:
                            removed_type = removed_item.get('features', {}).get('type', '')
                            print(f"[INFO] 删除配对物品 {idx} ({removed_type})")
                
                print(f"[SUCCESS] 完成 {actual_change_count} 个物品的类型修改")
                print(f"{'='*60}\n")
            else:
                if print_info:
                    if change_item_type_count == 0:
                        print(f"[INFO] 物品类型修改功能未启用 (change_item_type_count=0)")
                    elif len(table_items_data) == 0:
                        print(f"[WARNING] 场景中没有桌面物品，跳过物品修改")
            
            generated_items = []
            item_id_mapping = {}
            item_owners_list = []
            item_features_list = []
            
            from configs.item_config import ITEM_PROPERTIES
            
            for i, item_data in enumerate(table_items_data):
                try:
                    base_id = item_data.get('base_id')
                    position = item_data.get('position')
                    rotation = item_data.get('rotation')
                    old_id = item_data.get('id')
                    owner = item_data.get('owner')
                    features = item_data.get('features', {})
                    
                    if not all([base_id, position, rotation]):
                        print(f"[WARNING] 物品 {i} 数据不完整，跳过")
                        continue
                    
                    item_type = features.get('type', '')
                    scale = ts.Vector3(1, 1, 1)
                    
                    if item_type and item_type in ITEM_PROPERTIES:
                        scale = ITEM_PROPERTIES[item_type].get('scale', ts.Vector3(1, 1, 1))
                    
                    item = ue.spawn_entity(
                        entity_type=ts.BaseObjectEntity,
                        blueprint=base_id,
                        location=ts.Vector3(position['x'], position['y'], position['z']),
                        is_simulating_physics=True,
                        scale=scale,
                        quat=ts.Quaternion(rotation['w'], rotation['x'], rotation['y'], rotation['z']),
                    )
                    
                    generated_items.append(item)
                    item_id_mapping[old_id] = item.id
                    item_owners_list.append(owner)
                    item_features_list.append(features)
                    
                    print(f"[SUCCESS] 物品 {i}: {base_id} (owner: {owner}) at ({position['x']:.1f}, {position['y']:.1f})")
                
                except Exception as e:
                    print(f"[ERROR] 生成物品 {i} 失败: {e}")
                    continue
            
            # ========== 8.7. 增加桌面物品（如果需要）==========
            if adjust_item_count > 0:
                if print_info:
                    print(f"\n{'='*60}")
                    print(f"[PROCESSING] 开始增加桌面物品...")
                    print(f"[INFO] 需要增加 {adjust_item_count} 个物品")
                    print(f"{'='*60}")
                
                # 加载网格数据 - 使用load_table_grid_json函数
                from .item_util import load_table_grid_json
                
                grid_dir = './ownership/table_boundaries'
                # 处理table_id中可能包含的特殊字符
                clean_table_id = table_id.replace('/', '_')
                
                grid_data = load_table_grid_json(
                    map_name=map_name,
                    room_name=room_name,
                    table_id=clean_table_id,
                    grid_dir=grid_dir
                )
                
                if grid_data is None:
                    if print_info:
                        print(f"[ERROR] 无法加载网格数据")
                        print(f"[WARNING] 无法增加物品，跳过增加步骤")
                else:
                    try:
                        
                        # 准备existing_items_data（用于碰撞检测）
                        existing_items_for_adjust = []
                        for item, owner, features in zip(generated_items, item_owners_list, item_features_list):
                            item_loc = item.get_location()
                            item_rot = item.get_rotation()
                            existing_items_for_adjust.append({
                                'id': str(item.id),
                                # 'base_id': item.get_asset_id(),
                                'owner': owner,
                                'location': {'x': item_loc.x, 'y': item_loc.y, 'z': item_loc.z},
                                'rotation': {'w': item_rot.w, 'x': item_rot.x, 'y': item_rot.y, 'z': item_rot.z},
                                'features': features
                            })
                        
                        # 调用adjust_table_items_count增加物品
                        from .item_util import adjust_table_items_count
                        
                        new_items, new_owners, new_features, _ = adjust_table_items_count(
                            ue=ue,
                            table_object=target_table,
                            agents=generated_agents,
                            grid_data=grid_data,
                            existing_items_data=existing_items_for_adjust,
                            agent_features_list=agent_features_list,
                            adjust_count=adjust_item_count,
                            print_info=print_info
                        )
                        
                        # 将新生成的物品添加到列表中
                        if new_items:
                            generated_items.extend(new_items)
                            item_owners_list.extend(new_owners)
                            item_features_list.extend(new_features)
                            
                            # 为新物品建立ID映射（使用新ID作为键值）
                            for item in new_items:
                                item_id_mapping[str(item.id)] = item.id
                            
                            if print_info:
                                print(f"[SUCCESS] 成功增加 {len(new_items)} 个物品")
                                print(f"[INFO] 当前物品总数: {len(generated_items)}")
                        else:
                            if print_info:
                                print(f"[WARNING] 未能增加任何物品")
                        
                        print(f"{'='*60}\n")
                    
                    except Exception as e:
                        if print_info:
                            print(f"[ERROR] 增加物品失败: {e}")
                            import traceback
                            traceback.print_exc()
            
            # ========== 8.8. 移动物品到其他owner区域（如果需要）==========
            if move_item_count > 0 and len(generated_items) > 0:
                if print_info:
                    print(f"\n{'='*60}")
                    print(f"[PROCESSING] 开始移动物品到其他owner区域...")
                    print(f"[INFO] 需要移动 {move_item_count} 个物品")
                    print(f"{'='*60}")
                
                # 加载网格数据（如果之前已经加载过则复用）
                if 'grid_data' not in locals() or grid_data is None:
                    from .item_util import load_table_grid_json
                    
                    grid_dir = './ownership/table_boundaries'
                    clean_table_id = table_id.replace('/', '_')
                    
                    grid_data = load_table_grid_json(
                        map_name=map_name,
                        room_name=room_name,
                        table_id=clean_table_id,
                        grid_dir=grid_dir
                    )
                
                if grid_data is None:
                    if print_info:
                        print(f"[ERROR] 无法加载网格数据")
                        print(f"[WARNING] 无法移动物品，跳过移动步骤")
                else:
                    try:
                        # 准备物品数据（用于移动）
                        items_data_for_move = []
                        for item, owner, features in zip(generated_items, item_owners_list, item_features_list):
                            item_loc = item.get_location()
                            item_rot = item.get_rotation()
                            items_data_for_move.append({
                                'id': str(item.id),
                                'owner': owner,
                                'location': {'x': item_loc.x, 'y': item_loc.y, 'z': item_loc.z},
                                'rotation': {'w': item_rot.w, 'x': item_rot.x, 'y': item_rot.y, 'z': item_rot.z},
                                'features': features
                            })
                        
                        # 调用move_items_to_other_owners移动物品
                        from .item_util import move_items_to_other_owners
                        
                        moved_items_data, move_pairs = move_items_to_other_owners(
                            ue=ue,
                            table_object=target_table,
                            agents=generated_agents,
                            grid_data=grid_data,
                            existing_items_data=items_data_for_move,
                            agent_features_list=agent_features_list,
                            move_count=move_item_count,
                            print_info=print_info
                        )
                        
                        # 更新实际物品的位置和owner
                        if move_pairs:
                            for item_idx, old_owner, new_owner in move_pairs:
                                moved_data = moved_items_data[item_idx]
                                new_loc = moved_data['location']
                                
                                # 更新物品位置
                                item_entity = generated_items[item_idx]
                                item_entity.set_location(ts.Vector3(new_loc['x'], new_loc['y'], new_loc['z']))
                                
                                # 更新owner列表
                                item_owners_list[item_idx] = new_owner
                                
                                if print_info:
                                    print(f"[SUCCESS] 物品 {item_idx} 已移动并更新位置")
                            
                            if print_info:
                                print(f"[SUCCESS] 成功移动 {len(move_pairs)} 个物品")
                        
                        print(f"{'='*60}\n")
                    
                    except Exception as e:
                        if print_info:
                            print(f"[ERROR] 移动物品失败: {e}")
                            import traceback
                            traceback.print_exc()
            
            # ========== 9. 执行人物动作 ==========
            print(f"\n[PROCESSING] 开始执行人物动作...")
            
            # 首先处理动作修改（如果需要）
            if change_agent_action is not None and len(change_agent_action) > 0:
                print(f"\n{'='*60}")
                print(f"[PROCESSING] 开始修改人物动作...")
                print(f"{'='*60}")
                
                for agent_idx, new_action_type in change_agent_action.items():
                    if agent_idx < 0 or agent_idx >= len(agent_actions):
                        print(f"[WARNING] 人物索引 {agent_idx} 超出动作列表范围，跳过")
                        continue
                    
                    action_info = agent_actions[agent_idx]
                    old_action_type = action_info['action_type']
                    
                    if print_info:
                        print(f"\n[INFO] 修改人物 {agent_idx} 动作: {old_action_type} → {new_action_type}")
                    
                    # 情况1: 取消动作
                    if new_action_type == 'none':
                        action_info['action_type'] = 'none'
                        if print_info:
                            print(f"[INFO] 人物 {agent_idx} 取消动作")
                    
                    # 情况2: reach_item → point_at_item（使用同一物品）
                    elif old_action_type == 'reach_item' and new_action_type == 'point_at_item':
                        # 使用reach的物品ID作为point的物品ID
                        old_reach_item_id = action_info.get('old_reach_item_id')
                        action_info['action_type'] = 'point_at_item'
                        action_info['old_point_item_id'] = old_reach_item_id
                        if print_info:
                            print(f"[INFO] 人物 {agent_idx} 从reach_item改为point_at_item，目标物品: {old_reach_item_id}")
                    
                    # 情况3: point_at_item → reach_item（随机选择owner物品）
                    elif old_action_type == 'point_at_item' and new_action_type == 'reach_item':
                        agent = action_info['agent']
                        agent_id = str(agent.id)  # 新场景的agent ID
                        agent_status = agent_features_list[agent_idx].get('status', 'standing')
                        
                        # 找到属于该人物的所有物品
                        # 注意：item_owners_list中是旧ID，需要通过agent_id_mapping反向匹配
                        old_agent_id = None
                        for old_id, new_id in agent_id_mapping.items():
                            if new_id == agent_id:
                                old_agent_id = old_id
                                break
                        
                        if not old_agent_id:
                            if print_info:
                                print(f"[ERROR] 无法找到人物 {agent_idx} 的旧ID映射")
                            return {
                                'success': False,
                                'message': f'[ERROR] 人物 {agent_idx} 改变动作失败：无法找到ID映射',
                                'error_type': 'agent_id_mapping_failed'
                            }
                        
                        own_items = []
                        for i, owner in enumerate(item_owners_list):
                            if owner == old_agent_id:  # 使用旧ID匹配
                                item = generated_items[i]
                                item_id = str(item.id)
                                own_items.append((item, item_id))
                        
                        if not own_items:
                            if print_info:
                                print(f"[ERROR] 人物 {agent_idx} 没有自己的物品，无法执行reach_item动作")
                            return {
                                'success': False,
                                'message': f'[ERROR] 人物 {agent_idx} 改变动作失败：没有自己的物品',
                                'error_type': 'no_own_items_for_reach'
                            }
                        
                        # 如果是坐姿，需要筛选距离合适的物品
                        if agent_status == 'sitting':
                            max_reach_distance = 60.0
                            agent_location = agent.get_location()
                            
                            reachable_items = []
                            for item, item_id in own_items:
                                item_location = item.get_location()
                                dx = item_location.x - agent_location.x
                                dy = item_location.y - agent_location.y
                                distance = math.sqrt(dx*dx + dy*dy)
                                
                                if distance <= max_reach_distance:
                                    reachable_items.append((item, item_id, distance))
                            
                            if not reachable_items:
                                if print_info:
                                    print(f"[ERROR] 人物 {agent_idx} (坐姿) 没有可触及的物品（最大距离{max_reach_distance}cm）")
                                return {
                                    'success': False,
                                    'message': f'[ERROR] 人物 {agent_idx} 改变动作失败：坐姿下没有可触及的物品',
                                    'error_type': 'no_reachable_items_sitting'
                                }
                            
                            # 随机选择一个可触及的物品
                            chosen_item, chosen_item_id, distance = random.choice(reachable_items)
                            if print_info:
                                print(f"[INFO] 人物 {agent_idx} (坐姿) 随机选择物品 {chosen_item_id}，距离: {distance:.1f}cm")
                        
                        else:
                            # 站立状态，随机选择任意自己的物品
                            chosen_item, chosen_item_id = random.choice(own_items)
                            if print_info:
                                print(f"[INFO] 人物 {agent_idx} (站立) 随机选择物品 {chosen_item_id}")
                        
                        # 更新动作信息
                        action_info['action_type'] = 'reach_item'
                        action_info['old_reach_item_id'] = chosen_item_id
                        if print_info:
                            print(f"[INFO] 人物 {agent_idx} 从point_at_item改为reach_item，目标物品: {chosen_item_id}")
                    
                    # 情况4: 其他组合（保持原动作类型但改变目标）
                    elif old_action_type == new_action_type:
                        if print_info:
                            print(f"[INFO] 人物 {agent_idx} 动作类型未改变: {new_action_type}")
                    
                    else:
                        if print_info:
                            print(f"[WARNING] 不支持的动作转换: {old_action_type} → {new_action_type}")
            
            # 执行动作
            for action_info in agent_actions:
                try:
                    agent = action_info['agent']
                    action_type = action_info['action_type']
                    agent_index = generated_agents.index(agent)
                    
                    # 如果动作类型是'none'，跳过执行
                    if action_type == 'none':
                        agent_features_list[agent_index]['action'] = 'none'
                        if print_info:
                            print(f"[INFO] 人物 {agent_index} 无动作")
                        continue
                    
                    if action_type == 'point_at_item':
                        old_item_id = action_info.get('old_point_item_id')
                        new_item_id = item_id_mapping.get(old_item_id)
                        
                        if new_item_id:
                            target_item = None
                            for item in generated_items:
                                if str(item.id) == str(new_item_id):
                                    target_item = item
                                    break
                            
                            if target_item:
                                from .action_util import action_point_at_item
                                result = action_point_at_item(agent=agent, item=target_item, print_info=print_info)
                                
                                # 检查动作是否成功
                                if not result.get('success', False):
                                    if print_info:
                                        print(f"[ERROR] 人物 {agent_index} point_at_item动作执行失败")
                                    return {
                                        'success': False,
                                        'message': f'[ERROR] 人物 {agent_index} point_at_item动作执行失败',
                                        'error_type': 'point_action_failed'
                                    }
                                
                                agent_features_list[agent_index]['action'] = 'point_at_item'
                                agent_features_list[agent_index]['point_item_id'] = str(target_item.id)
                                agent_features_list[agent_index]['action_success'] = True
                                if 'hand_used' in result:
                                    agent_features_list[agent_index]['hand_used'] = result['hand_used']
                                
                                if print_info:
                                    print(f"[SUCCESS] 人物指向动作执行成功: {agent.id} -> {target_item.id}")
                            else:
                                if print_info:
                                    print(f"[ERROR] 无法找到新物品对象: {new_item_id}")
                                return {
                                    'success': False,
                                    'message': f'[ERROR] 人物 {agent_index} 找不到目标物品',
                                    'error_type': 'item_not_found'
                                }
                        else:
                            if print_info:
                                print(f"[ERROR] 无法映射旧物品ID: {old_item_id}")
                            return {
                                'success': False,
                                'message': f'[ERROR] 人物 {agent_index} 物品ID映射失败',
                                'error_type': 'item_mapping_failed'
                            }
                    
                    elif action_type == 'reach_item':
                        old_item_id = action_info.get('old_reach_item_id')
                        new_item_id = item_id_mapping.get(old_item_id)
                        
                        if new_item_id:
                            target_item = None
                            for item in generated_items:
                                if str(item.id) == str(new_item_id):
                                    target_item = item
                                    break
                            
                            if target_item:
                                from .action_util import action_reach_item
                                agent_status = agent_features_list[agent_index].get('status', 'standing')
                                result = action_reach_item(agent=agent, item=target_item, agent_status=agent_status, print_info=print_info)
                                
                                # 检查动作是否成功
                                if not result.get('success', False):
                                    if print_info:
                                        print(f"[ERROR] 人物 {agent_index} reach_item动作执行失败")
                                    return {
                                        'success': False,
                                        'message': f'[ERROR] 人物 {agent_index} reach_item动作执行失败',
                                        'error_type': 'reach_action_failed'
                                    }
                                
                                agent_features_list[agent_index]['action'] = 'reach_item'
                                agent_features_list[agent_index]['reach_item_id'] = str(target_item.id)
                                agent_features_list[agent_index]['action_success'] = True
                                if 'hand_used' in result:
                                    agent_features_list[agent_index]['hand_used'] = result['hand_used']
                                
                                if print_info:
                                    print(f"[SUCCESS] 人物伸手动作执行成功: {agent.id} -> {target_item.id}")
                            else:
                                if print_info:
                                    print(f"[ERROR] 无法找到新物品对象: {new_item_id}")
                                return {
                                    'success': False,
                                    'message': f'[ERROR] 人物 {agent_index} 找不到目标物品',
                                    'error_type': 'item_not_found'
                                }
                        else:
                            if print_info:
                                print(f"[ERROR] 无法映射旧物品ID: {old_item_id}")
                            return {
                                'success': False,
                                'message': f'[ERROR] 人物 {agent_index} 物品ID映射失败',
                                'error_type': 'item_mapping_failed'
                            }
                
                except Exception as e:
                    print(f"[ERROR] 执行动作失败: {e}")
                    import traceback
                    traceback.print_exc()
                    return {
                        'success': False,
                        'message': f'[ERROR] 人物动作执行异常: {str(e)}',
                        'error_type': 'action_execution_exception'
                    }
            
            # ========== 10. 生成摄像头并拍摄 ==========
            if print_info:
                print(f"\n[PROCESSING] 开始生成摄像头...")
            
            center_location = calculate_entities_center(agents=generated_agents, items=generated_items)
            
            camera_positions = generate_camera_positions(
                ue=ue, room_bound=room_bound, target_object=target_table,
                center_location=center_location, distance_range=[200, 300],
                height=[100, 250], agents=generated_agents, num_cameras=8
            )
            
            cameras = add_capture_camera(ue, camera_positions, center_location=center_location, target_obj=target_table)
            
            if print_info:
                print(f"[SUCCESS] 成功创建了 {len(cameras)} 个摄像头")
            
            top_camera_pos = generate_top_view_camera_position(
                room_bound=room_bound, agents=generated_agents, items=generated_items,
                margin_factor=1.5, safe_margin=30, print_info=False
            )
            
            top_camera = add_capture_camera(
                ue=ue, camera_positions=top_camera_pos, center_location=center_location,
                target_obj=target_table, camera_name_prefix="TopCamera", print_info=False
            )
            
            all_cameras = cameras + top_camera
            
            # ========== 11. 拍摄图像 ==========
            if print_info:
                print(f"\n[PROCESSING] 开始拍摄图像...")
            
            saved_images = capture_and_save_images(cameras=cameras, save_dir=output_dir, delay_before_capture=0.01)
            saved_images.update(capture_and_save_images(cameras=top_camera, save_dir=output_dir, delay_before_capture=0.01))
            
            if print_info:
                print(f"[SUCCESS] 保存了 {len(saved_images)} 张图像")
            
            # ========== 12. 保存新的JSON文件 ==========
            print(f"\n[PROCESSING] 开始保存JSON文件...")
            
            new_json_path = create_scene_json_file(map_name=map_name, room_name=room_name, table_entity=target_table, save_dir=output_dir)
            
            # 首先添加附近物品
            if nearby_items:
                if print_info:
                    print(f"[INFO] 添加 {len(nearby_items)} 个附近物品到JSON")
                add_entities_to_json(json_file_path=new_json_path, entities=nearby_items, entity_type='object', owner='room')
            
            # 添加桌面物品
            if generated_items and item_owners_list and item_features_list:
                if print_info:
                    print(f"[INFO] 添加 {len(generated_items)} 个桌面物品到JSON")
                complete_features = []
                for owner, features in zip(item_owners_list, item_features_list):
                    complete_features.append({'owner': owner, **features})
                add_entities_to_json(json_file_path=new_json_path, entities=generated_items, entity_type='object', owner=None, features_list=complete_features)
            
            # 添加人物
            if generated_agents and agent_features_list:
                if print_info:
                    print(f"[INFO] 添加 {len(generated_agents)} 个人物到JSON")
                add_entities_to_json(json_file_path=new_json_path, entities=generated_agents, entity_type='agent', features_list=agent_features_list, auto_detect_asset_type=False)
            
            # 添加摄像头
            if all_cameras:
                add_entities_to_json(json_file_path=new_json_path, entities=all_cameras, entity_type='camera')
            
            print(f"[SUCCESS] JSON文件已保存: {new_json_path}")
            
            # ========== 13. 清理实体 ==========
            if print_info:
                print(f"\n[INFO] 开始清理场景实体...")
            
            for agent in generated_agents:
                try:
                    ue.destroy_entity(agent.id)
                except:
                    pass
            
            for item in generated_items:
                try:
                    ue.destroy_entity(item.id)
                except:
                    pass
            
            for camera in all_cameras:
                try:
                    ue.destroy_entity(camera.id)
                except:
                    pass
            
            if print_info:
                print(f"[SUCCESS] 清理完成")
            
            # ========== 14. 返回结果 ==========
            result = {
                'success': True,
                'message': f'[SUCCESS] 场景重建完成: {len(generated_agents)} 人物, {len(generated_items)} 物品, {len(saved_images)} 图像',
                'output_dir': output_dir,
                'json_path': new_json_path,
                'images': list(saved_images.keys()),
                'agent_count': len(generated_agents),
                'added_agent': added_agent_success
            }
            
            if print_info:
                print(f"\n{'='*60}")
                print(result['message'])
                if add_agent:
                    print(f"新人物添加: {'成功' if added_agent_success else '失败'}")
                print(f"输出目录: {output_dir}")
                print(f"{'='*60}\n")
            
            return result
    
    except Exception as e:
        error_msg = f'[ERROR] 场景重建且修改失败: {str(e)}'
        print(error_msg)
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'message': error_msg
        }














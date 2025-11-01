import os
import re
import math
import random
import time
import glob
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
import numpy as np
import traceback

import tongsim as ts
from tongsim.type import ViewModeType

# Import from configs
from configs.item_config import (
    ITEM_BLUEPRINTS as item_blueprints,
    ITEM_PROPERTIES as item_properties,
    AGENT_ITEM_MAPPING as agent_item_mapping,
    COMMON_ITEMS as common_items,
    NON_REPEATING_ITEM_TYPES as non_repeating_item_types
)

# Import utility functions from utils modules
from utils.other_util import (
    get_room_bbox,
    get_room_boundary,
    get_area,
    validate_table,
    random_remove_table_items
)

from utils.query_util import (
    query_existing_objects_in_room,
    find_objects_near_table,
    find_objects_near_table_with_info
)

from utils.table_zone import (
    divide_table_into_zones,
    refine_zone_for_person
)

from utils.item_util import (
    load_table_grid_json,
    spawn_items_on_grid,
    spawn_items_on_grid_new
)

from utils.camera_util import (
    calculate_entities_center,
    generate_camera_positions,
    generate_top_view_camera_position,
    add_capture_camera,
    capture_and_save_images
)

from utils.agent_util import (
    generate_agent_configuration,
    plan_agents_around_table,
    execute_agent_plans,
    generate_and_spawn_agents,  # 新的优化函数
    extract_agents_and_features_from_complete_info
)

# Import JSON utility functions
from utils.json_util import (
    add_entities_to_json,
    create_scene_json_file,
    load_asset_info,
    get_asset_type_by_id
)

# Import action utility functions
from utils.action_util import (
    generate_actions_for_all_agents
)



# 创建人动作
# PointAtLocation 动作: 指向指定位置或取消指向指定位置。
# NodHead 动作: 点头。
# RaiseHand 动作: 举手。
# ShakeHead 动作: 摇头。 可以朝向其他人摇手
# WaveHand 动作: 挥手。
# RompPlay 动作: 把玩当前手上的物体（需要手上有物体）
# HandReach 动作: 手部伸向目标位置。 可以制作拿起物品的意图
# ReadBook 动作: 阅读书籍， 需要手上有书
# WipeQuad 动作：擦拭一个矩形区域。
# def make_agent_perform_action(agent, spawned_items=None):



# log
# [PROCESSING] 代表正常处理流程 代表核心处理步骤具体信息
# [INFO] 代表信息输出 代表一些辅助信息
# [CONTINUE] 代表跳过条件 条件不满足，不影响整体流程
# [WARNING] 代表警告信息 一般指的是逻辑错误，但是无关大雅
# [ERROR] 代表错误信息 一般指的是逻辑错误，但是会影响后续流程


# 待修改
# 物体离桌子距离，例如电脑应该近一些，贵重物品例如玻璃应该远一些
# 物体json文件重写

# pipline 
def run_pipline_table_with_agents_objects(map_range=None, min_room_area=4, min_table_area = 0.4, log_dir="./ownership/logs", 
                                          num_agents = None, agent_sides = None, max_item = 9):
    # 读取筛选后的场景列表
    try:
        with open('./ownership/object/selected_scenes.txt', 'r', encoding='utf-8') as f:
            selected_scenes = [line.strip() for line in f if line.strip()]
        print(f"[INFO] 已加载 {len(selected_scenes)} 个筛选场景")
    except FileNotFoundError:
        print("[WARNING] selected_scenes.txt 文件不存在，将处理所有地图")
        selected_scenes = []
        
    # 读取物品列表
    try:
        ASSET_OWL_DICT = {}
        # 在主程序开始时加载资产信息
        ASSET_JSON_PATH = "./objects_info.json"  # 你的资产信息JSON文件路径
        load_asset_info(ASSET_JSON_PATH)
    except FileNotFoundError:
        print("[WARNING] objects_info.json 文件不存在")
        

    with ts.TongSim(
        grpc_endpoint="127.0.0.1:5056",
        legacy_grpc_endpoint="127.0.0.1:50052",
        # grpc_endpoint="10.1.188.23:5056",
        # legacy_grpc_endpoint="10.1.188.23:50052",
    ) as ue:
        # 定义地图范围
        if map_range is None:
            map_range = range(0, 29)

        for map_num in map_range:
            # 格式化地图名称
            map_name = f"SDBP_Map_{map_num:03d}"

            # 检查是否在筛选列表中
            if selected_scenes and map_name not in selected_scenes:
                print(f"[CONTINUE] 跳过不在筛选列表中的地图: {map_name}")
                continue

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

                    success = ue.open_level(map_name)
                    if not success:
                        print(f"[WARNING] 无法打开地图: {map_name}，跳过")
                        continue

                    # 查询房间内的桌子
                    table_entitys = query_existing_objects_in_room(ue=ue, room_bound=room_bound, target_types=['coffeetable', 'diningTable', 'table', 'Table'], object_name="桌子")
                    # 处理多个桌子
                    if table_entitys:
                        print(f"[PROCESSING] 找到 {len(table_entitys)} 张桌子，开始处理...")
                        for i, table_entity in enumerate(table_entitys):
                            print(f"[PROCESSING] 处理第 {i+1} / {len(table_entitys)} 张桌子")

                            if not validate_table(table_entity, min_table_area=min_table_area):
                                print(f"[CONTINUE] 桌子面积不符合条件，跳过")
                                continue

                            on_table_items, nearby_items  = find_objects_near_table(
                                ue=ue,
                                table_object=table_entity,
                                search_distance=120.0
                            )

                            # 随机删除桌面物品
                            on_table_items = random_remove_table_items(
                                ue=ue,
                                table_object=table_entity,
                                on_table_items=on_table_items,
                                area_threshold=0.3,
                                max_item_count= 5
                            )

                            # 在桌子周围生成人物
                            agent_blueprints, agent_sides, agent_is_sit, agent_traits  = generate_agent_configuration(
                                sit_probability=0.75,  # 概率坐下
                                # agent_traits=['boy', 'girl', 'girl'],
                                agent_sides=agent_sides,
                                num_agents=num_agents,
                            )
                            agent_plans = plan_agents_around_table(
                                table_object=table_entity,
                                room_bound=room_bound,
                                agent_blueprints=agent_blueprints,
                                agent_sides=agent_sides,
                                agent_is_sit=agent_is_sit,
                                agent_traits=agent_traits,
                                nearby_objects=nearby_items,
                                min_distance=30,
                                max_distance=80,
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

                            # 创建保存目录和JSON文件
                            json_save_dir_name = f"table_scene_map{map_num:03d}_room_{room_name}_table{i+1}"
                            json_save_dir = os.path.join(log_dir, json_save_dir_name)
                            json_file_path = create_scene_json_file(map_name, room_name, table_entity, json_save_dir)

                            # 添加桌子上的物品到JSON
                            if on_table_items:
                                add_entities_to_json(
                                    json_file_path=json_file_path,
                                    entities=on_table_items,
                                    entity_type='object',
                                    owner="table"
                                )
                            
                            # 添加附近的物品到JSON
                            if nearby_items:
                                add_entities_to_json(
                                    json_file_path=json_file_path,
                                    entities=nearby_items,
                                    entity_type='object',
                                    owner="room"
                                )

                            # 生成人物
                            agents = execute_agent_plans(ue=ue, agent_plans=agent_plans, json_file_path=json_file_path, print_info=False)

                            ue.change_view_mode(ViewModeType.MANUAL_CONTROL_VIEW)

                            zones = divide_table_into_zones(table_object = table_entity, max_zone_length=160.0, 
                                                            zone_depth_ratio = 0.4, print_info=False)

                            zone_configs = [
                                refine_zone_for_person(
                                    zones, 
                                    table_entity, 
                                    agent, 
                                    handedness='right', 
                                    main_zone_min_width=50.0, 
                                    temp_zone_size=25.0, 
                                    print_info=False
                                )
                                for agent in agents
                            ]

                            item_configs = generate_item_configurations(
                                agents=agents,
                                zone_configs=zone_configs,
                                max_total_items=max_item,  # 桌面最多物品
                                max_items_per_agent=3,  # 每个人最多物品
                                print_info=False
                            )

                            total_spawned_items = 0
                            all_spawned_items = []
                            # 为每个配置生成物品
                            for config in item_configs:
                                spawned_items = spawn_items_in_person_zone(
                                    ue=ue,
                                    table_object=table_entity,
                                    target_agent=config['agent'],
                                    refined_zones=config['refined_zones'],
                                    zone_types=config['zone_types'],
                                    item_blueprints=config['item_blueprints'],
                                    scale=config['scale'],
                                    rotation_z=config['rotation_z'],
                                    rotation_x=config['rotation_x'],
                                    rotation_y=config['rotation_y'],
                                    on_table_items=on_table_items,
                                    max_distance=config['max_distance'],
                                    min_distance=config['min_distance'],
                                    safe_margin=config['safe_margin'],
                                    json_file_path=json_file_path,
                                    item_type=config['item_type'],
                                    print_info=False
                                )
                                total_spawned_items += len(spawned_items)
                                all_spawned_items.extend(spawned_items)

                            # 生成随机摄像头位置
                            center_location=calculate_entities_center(agents=agents, items=all_spawned_items)
                            camera_positions = generate_camera_positions(
                                ue=ue,
                                room_bound=room_bound,
                                target_object=table_entity,
                                center_location=center_location,
                                distance_range=[250, 400],  # 距离目标
                                height=[120, 250],  # 摄像头高度
                                agents=agents,
                                num_cameras=8,  # 生成摄像头个数
                            )

                            # 创建所有摄像头
                            cameras = add_capture_camera(ue, camera_positions, center_location=center_location, target_obj=table_entity)
                            print(f"成功创建了 {len(cameras)} 个摄像头")

                            # 添加摄像头到JSON
                            if cameras:
                                add_entities_to_json(json_file_path=json_file_path, entities=cameras, entity_type='camera')

                            # 生成俯视摄像头位置
                            top_camera_pos = generate_top_view_camera_position(
                                room_bound=room_bound,
                                agents=agents,
                                items=all_spawned_items,
                                margin_factor=1.5,  # 20%的额外边距
                                safe_margin=30,     # 距离天花板30单位
                                print_info=False
                            )

                            # 创建俯视摄像头
                            top_camera = add_capture_camera(
                                ue=ue,
                                camera_positions=top_camera_pos,  # 单个位置
                                center_location=center_location, 
                                target_obj=table_entity,
                                camera_name_prefix="TopCamera",
                                print_info=False
                            )

                            if top_camera:
                                add_entities_to_json(json_file_path=json_file_path, entities=top_camera, entity_type='camera')

                            # 拍摄图像
                            saved_images = capture_and_save_images(
                                cameras=cameras,
                                save_dir=json_save_dir,  # 自定义保存路径
                                delay_before_capture=0.01  # 拍摄前等待1秒让物理稳定
                            )
                            saved_images.update(capture_and_save_images(
                                cameras=top_camera,
                                save_dir=json_save_dir,  # 自定义保存路径
                                delay_before_capture=0.01  # 拍摄前等待1秒让物理稳定
                            ))
                            
                            print(f"[SUCCESS] 场景生成完成: {json_save_dir_name}")
                            print(f"  地图: {map_name}")
                            print(f"  房间: {room_name}")
                            print(f"  人物数量: {len(agents)}")
                            print(f"  物品总数: {total_spawned_items}")
                            print(f"  摄像头数量: {len(cameras)}")
                            print(f"  保存图像数量: {len(saved_images)}")

                            # time.sleep(10)
                            # 释放人物
                            [ue.destroy_entity(agent.id) for agent in agents]
                            # 释放物品
                            [ue.destroy_entity(item.id) for item in all_spawned_items] 

                    else:
                        print(f"[CONTINUE] 房间 {room_name} 没有桌子，跳过")
                        continue
                    
                    
            except Exception as e:
                print(f"[ERROR] 处理地图 {map_name} 时发生错误: {str(e)}")
                continue


# 新的 Pipeline: 遍历所有可能的两人位置组合
def run_pipeline_agent_positions(map_range=None, min_room_area=4, min_table_area=0.4, 
                                 base_log_dir="./ownership/agent_positions"):
    """
    遍历所有地图、房间、桌子，为每张桌子记录所有可能的两人位置组合
    
    组合类型:
    1. 面对面 (Face to Face): front-back, left-right
    2. 相邻边 (Adjacent Sides): front-left, front-right, back-left, back-right
    3. 并排站 (Same Side): front-front, back-back, left-left, right-right
    
    Args:
        map_range: 地图范围，默认为 range(0, 29)
        min_room_area: 最小房间面积阈值
        min_table_area: 最小桌子面积阈值
        base_log_dir: 保存 JSON 文件的基础目录
    """
    
    # 定义所有可能的两人位置组合
    # 第一种：面对面组合 (Face to Face)
    face_to_face_combinations = [
        ("front", "back"),
        ("left", "right")
    ]
    
    # 第二种：相邻边组合 (Adjacent Sides)
    adjacent_sides_combinations = [
        ("front", "left"),
        ("front", "right"),
        ("back", "left"),
        ("back", "right")
    ]
    
    # 第三种：并排站组合 (Same Side)
    same_side_combinations = [
        ("front", "front"),
        ("back", "back"),
        ("left", "left"),
        ("right", "right")
    ]
    
    # 合并所有组合
    all_combinations = face_to_face_combinations + adjacent_sides_combinations + same_side_combinations
    
    # 读取筛选后的场景列表
    try:
        with open('./ownership/object/selected_scenes.txt', 'r', encoding='utf-8') as f:
            selected_scenes = [line.strip() for line in f if line.strip()]
        print(f"[INFO] 已加载 {len(selected_scenes)} 个筛选场景")
    except FileNotFoundError:
        print("[WARNING] selected_scenes.txt 文件不存在，将处理所有地图")
        selected_scenes = []

    # 读取物品列表
    try:
        ASSET_OWL_DICT = {}
        # 在主程序开始时加载资产信息
        ASSET_JSON_PATH = "./objects_info.json"  # 你的资产信息JSON文件路径
        load_asset_info(ASSET_JSON_PATH)
    except FileNotFoundError:
        print("[WARNING] objects_info.json 文件不存在")
        
    with ts.TongSim(
        grpc_endpoint="127.0.0.1:5056",
        legacy_grpc_endpoint="127.0.0.1:50052",
    ) as ue:
        # 定义地图范围
        if map_range is None:
            map_range = range(0, 29)
        
        for map_num in map_range:
            # 格式化地图名称
            map_name = f"SDBP_Map_{map_num:03d}"
            
            # 检查是否在筛选列表中
            if selected_scenes and map_name not in selected_scenes:
                print(f"[CONTINUE] 跳过不在筛选列表中的地图: {map_name}")
                continue
            
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
                
                # 获取房间边界框信息
                room_bbox_dict = get_room_bbox(rooms)
                
                # 遍历当前地图的所有房间
                for room_info in rooms:
                    room_name = room_info['room_name']
                    
                    print(f"\n[PROCESSING] 处理地图 {map_name} 的房间: {room_name}")
                    room_bound = get_room_boundary(room_name, room_bbox_dict)
                    
                    # 面积小于阈值跳过
                    if get_area(room_bound) < min_room_area:
                        print(f"[CONTINUE] 房间 {room_name} 面积小于 {min_room_area} 平方米，跳过")
                        continue
                    
                    # 重新打开地图确保环境干净
                    success = ue.open_level(map_name)
                    if not success:
                        print(f"[WARNING] 无法打开地图: {map_name}，跳过")
                        continue
                    
                    # 查询房间内的桌子
                    table_entitys = query_existing_objects_in_room(
                        ue=ue, 
                        room_bound=room_bound, 
                        target_types=['coffeetable', 'diningTable', 'table', 'Table'], 
                        object_name="桌子"
                    )
                    
                    # 处理多个桌子
                    if table_entitys:
                        print(f"[PROCESSING] 找到 {len(table_entitys)} 张桌子，开始处理...")
                        for table_idx, table_entity in enumerate(table_entitys):
                            print(f"\n[PROCESSING] 处理第 {table_idx+1} / {len(table_entitys)} 张桌子")
                            
                            # 验证桌子是否符合条件
                            if not validate_table(table_entity, min_table_area=min_table_area):
                                print(f"[CONTINUE] 桌子面积不符合条件，跳过")
                                continue
                            
                            # 查找桌子附近的物品（用于碰撞检测）
                            on_table_items, nearby_items = find_objects_near_table(
                                ue=ue,
                                table_object=table_entity,
                                search_distance=120.0
                            )
                            
                            # 遍历所有位置组合
                            for combo_idx, (side1, side2) in enumerate(all_combinations):
                                print(f"\n  [COMBINATION {combo_idx+1}/{len(all_combinations)}] 尝试组合: {side1}-{side2}")
                                
                                # 重新打开地图以清理之前的人物
                                success = ue.open_level(map_name)
                                if not success:
                                    print(f"  [WARNING] 无法重新打开地图，跳过此组合")
                                    continue
                                
                                # 生成人物配置
                                agent_blueprints, agent_sides_config, agent_is_sit, agent_traits = generate_agent_configuration(
                                    sit_probability=1,
                                    agent_sides=[side1, side2],
                                    num_agents=2,
                                )
                                
                                # 规划人物位置
                                agent_plans = plan_agents_around_table(
                                    table_object=table_entity,
                                    room_bound=room_bound,
                                    agent_blueprints=agent_blueprints,
                                    agent_sides=agent_sides_config,
                                    agent_is_sit=agent_is_sit,
                                    agent_traits=agent_traits,
                                    nearby_objects=nearby_items,
                                    min_distance=30,
                                    max_distance=80,
                                    print_info=False
                                )
                                
                                # 检查规划是否成功
                                successful_plans = [plan for plan in agent_plans if plan.get('status') != 'failed']
                                if len(successful_plans) < 2:
                                    print(f"  [CONTINUE] 未能规划出2个人物位置（成功: {len(successful_plans)}），跳过此组合")
                                    continue
                                
                                # 确定组合类型
                                if (side1, side2) in face_to_face_combinations:
                                    combo_type = "face_to_face"
                                elif (side1, side2) in adjacent_sides_combinations:
                                    combo_type = "adjacent_sides"
                                elif (side1, side2) in same_side_combinations:
                                    combo_type = "same_side"
                                else:
                                    combo_type = "unknown"
                                
                                # 创建保存目录和JSON文件
                                json_save_dir_name = f"map{map_num:03d}_room_{room_name}_table{table_idx+1}_{combo_type}_{side1}_{side2}"
                                json_save_dir = os.path.join(base_log_dir, json_save_dir_name)
                                json_file_path = create_scene_json_file(map_name, room_name, table_entity, json_save_dir)

                                # 添加桌子上的物品到JSON
                                if on_table_items:
                                    add_entities_to_json(
                                        json_file_path=json_file_path,
                                        entities=on_table_items,
                                        entity_type='object',
                                        owner="table"
                                    )
                                
                                # 添加附近的物品到JSON
                                if nearby_items:
                                    add_entities_to_json(
                                        json_file_path=json_file_path,
                                        entities=nearby_items,
                                        entity_type='object',
                                        owner="room"
                                    )

                                # 添加组合类型信息到JSON
                                import json
                                with open(json_file_path, 'r', encoding='utf-8') as f:
                                    scene_data = json.load(f)
                                scene_data['agent_combination'] = {
                                    'type': combo_type,
                                    'positions': [side1, side2]
                                }
                                with open(json_file_path, 'w', encoding='utf-8') as f:
                                    json.dump(scene_data, f, indent=2, ensure_ascii=False)
                                
                                # 执行人物生成
                                agents = execute_agent_plans(
                                    ue=ue, 
                                    agent_plans=agent_plans, 
                                    json_file_path=json_file_path, 
                                    print_info=False
                                )

                                all_spawned_items = on_table_items
                                # 生成随机摄像头位置
                                center_location=calculate_entities_center(agents=agents, items=all_spawned_items)
                                camera_positions = generate_camera_positions(
                                    ue=ue,
                                    room_bound=room_bound,
                                    target_object=table_entity,
                                    center_location=center_location,
                                    distance_range=[250, 400],  # 距离目标
                                    height=[120, 250],  # 摄像头高度
                                    agents=agents,
                                    num_cameras=2,  # 生成摄像头个数
                                )

                                # 创建所有摄像头
                                cameras = add_capture_camera(ue, camera_positions, center_location=center_location, target_obj=table_entity)
                                print(f"成功创建了 {len(cameras)} 个摄像头")

                                # 添加摄像头到JSON
                                if cameras:
                                    add_entities_to_json(json_file_path=json_file_path, entities=cameras, entity_type='camera')

                                # 拍摄图像
                                saved_images = capture_and_save_images(
                                    cameras=cameras,
                                    save_dir=json_save_dir,  # 自定义保存路径
                                    delay_before_capture=0.01  # 拍摄前等待1秒让物理稳定
                                )
                                
                                print(f"  [SUCCESS] 成功生成组合 {side1}-{side2}")
                                print(f"    保存路径: {json_save_dir_name}")
                                print(f"    人物数量: {len(agents)}")
                                
                                # 可选：短暂等待以确保保存完成
                                time.sleep(0.1)
                                
                                # 清理人物
                                [ue.destroy_entity(agent.id) for agent in agents]
                        
                    else:
                        print(f"[CONTINUE] 房间 {room_name} 没有桌子，跳过")
                        continue
            
            except Exception as e:
                print(f"[ERROR] 处理地图 {map_name} 时发生错误: {str(e)}")
                import traceback
                traceback.print_exc()
                continue
    
    print("\n[DONE] 所有位置组合处理完成")


# 新的 Pipeline: 遍历所有可能的三人位置组合
def run_pipeline_agent_positions_three_agents(map_range=None, min_room_area=4, min_table_area=0.4, 
                                              base_log_dir="./ownership/agent_positions_3agents"):
    """
    遍历所有地图、房间、桌子，为每张桌子记录所有可能的三人位置组合
    
    三人组合（占据桌子的三个边）:
    1. front-back-left
    2. front-back-right
    3. front-left-right
    4. back-left-right
    
    Args:
        map_range: 地图范围，默认为 range(0, 29)
        min_room_area: 最小房间面积阈值
        min_table_area: 最小桌子面积阈值
        base_log_dir: 保存 JSON 文件的基础目录
    """
    
    # 定义所有可能的三人位置组合（桌子四个边选三个）
    three_agent_combinations = [
        ("front", "back", "left"),
        ("front", "back", "right"),
        ("front", "left", "right"),
        ("back", "left", "right")
    ]
    
    # 读取筛选后的场景列表
    try:
        with open('./ownership/object/selected_scenes.txt', 'r', encoding='utf-8') as f:
            selected_scenes = [line.strip() for line in f if line.strip()]
        print(f"[INFO] 已加载 {len(selected_scenes)} 个筛选场景")
    except FileNotFoundError:
        print("[WARNING] selected_scenes.txt 文件不存在，将处理所有地图")
        selected_scenes = []
    
    # 读取物品列表
    try:
        ASSET_OWL_DICT = {}
        # 在主程序开始时加载资产信息
        ASSET_JSON_PATH = "./objects_info.json"
        load_asset_info(ASSET_JSON_PATH)
    except FileNotFoundError:
        print("[WARNING] objects_info.json 文件不存在")
    
    with ts.TongSim(
        grpc_endpoint="127.0.0.1:5056",
        legacy_grpc_endpoint="127.0.0.1:50052",
    ) as ue:
        # 定义地图范围
        if map_range is None:
            map_range = range(0, 29)
        
        for map_num in map_range:
            # 格式化地图名称
            map_name = f"SDBP_Map_{map_num:03d}"
            
            # 检查是否在筛选列表中
            if selected_scenes and map_name not in selected_scenes:
                print(f"[CONTINUE] 跳过不在筛选列表中的地图: {map_name}")
                continue
            
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
                
                # 获取房间边界框信息
                room_bbox_dict = get_room_bbox(rooms)
                
                # 遍历当前地图的所有房间
                for room_info in rooms:
                    room_name = room_info['room_name']
                    
                    print(f"\n[PROCESSING] 处理地图 {map_name} 的房间: {room_name}")
                    room_bound = get_room_boundary(room_name, room_bbox_dict)
                    
                    # 面积小于阈值跳过
                    if get_area(room_bound) < min_room_area:
                        print(f"[CONTINUE] 房间 {room_name} 面积小于 {min_room_area} 平方米，跳过")
                        continue
                    
                    # 重新打开地图确保环境干净
                    success = ue.open_level(map_name)
                    if not success:
                        print(f"[WARNING] 无法打开地图: {map_name}，跳过")
                        continue
                    
                    # 查询房间内的桌子
                    table_entitys = query_existing_objects_in_room(
                        ue=ue, 
                        room_bound=room_bound, 
                        target_types=['coffeetable', 'diningTable', 'table', 'Table'], 
                        object_name="桌子"
                    )
                    
                    # 处理多个桌子
                    if table_entitys:
                        print(f"[PROCESSING] 找到 {len(table_entitys)} 张桌子，开始处理...")
                        for table_idx, table_entity in enumerate(table_entitys):
                            print(f"\n[PROCESSING] 处理第 {table_idx+1} / {len(table_entitys)} 张桌子")
                            
                            # 验证桌子是否符合条件
                            if not validate_table(table_entity, min_table_area=min_table_area):
                                print(f"[CONTINUE] 桌子面积不符合条件，跳过")
                                continue
                            
                            # 查找桌子附近的物品（用于碰撞检测）
                            on_table_items, nearby_items = find_objects_near_table(
                                ue=ue,
                                table_object=table_entity,
                                search_distance=120.0
                            )
                            
                            # 遍历所有位置组合
                            for combo_idx, (side1, side2, side3) in enumerate(three_agent_combinations):
                                print(f"\n  [COMBINATION {combo_idx+1}/{len(three_agent_combinations)}] 尝试组合: {side1}-{side2}-{side3}")
                                
                                # 重新打开地图以清理之前的人物
                                success = ue.open_level(map_name)
                                if not success:
                                    print(f"  [WARNING] 无法重新打开地图，跳过此组合")
                                    continue
                                
                                # 生成人物配置（三个人）
                                agent_blueprints, agent_sides_config, agent_is_sit, agent_traits = generate_agent_configuration(
                                    sit_probability=0.75,  # 75%概率坐下
                                    agent_sides=[side1, side2, side3],
                                    num_agents=3,
                                )
                                
                                # 规划人物位置
                                agent_plans = plan_agents_around_table(
                                    table_object=table_entity,
                                    room_bound=room_bound,
                                    agent_blueprints=agent_blueprints,
                                    agent_sides=agent_sides_config,
                                    agent_is_sit=agent_is_sit,
                                    agent_traits=agent_traits,
                                    nearby_objects=nearby_items,
                                    min_distance=30,
                                    max_distance=80,
                                    print_info=False
                                )
                                
                                # 检查规划是否成功（至少需要3个人）
                                successful_plans = [plan for plan in agent_plans if plan.get('status') != 'failed']
                                if len(successful_plans) < 3:
                                    print(f"  [CONTINUE] 未能规划出3个人物位置（成功: {len(successful_plans)}），跳过此组合")
                                    continue
                                
                                # 创建保存目录和JSON文件
                                json_save_dir_name = f"map{map_num:03d}_room_{room_name}_table{table_idx+1}_three_{side1}_{side2}_{side3}"
                                json_save_dir = os.path.join(base_log_dir, json_save_dir_name)
                                json_file_path = create_scene_json_file(map_name, room_name, table_entity, json_save_dir)
                                
                                # 添加桌子上的物品到JSON
                                if on_table_items:
                                    add_entities_to_json(
                                        json_file_path=json_file_path,
                                        entities=on_table_items,
                                        entity_type='object',
                                        owner="table"
                                    )
                                
                                # 添加附近的物品到JSON
                                if nearby_items:
                                    add_entities_to_json(
                                        json_file_path=json_file_path,
                                        entities=nearby_items,
                                        entity_type='object',
                                        owner="room"
                                    )
                                
                                # 添加组合类型信息到JSON
                                import json
                                with open(json_file_path, 'r', encoding='utf-8') as f:
                                    scene_data = json.load(f)
                                scene_data['agent_combination'] = {
                                    'type': 'three_agents',
                                    'positions': [side1, side2, side3],
                                    'description': f'{side1}-{side2}-{side3}'
                                }
                                with open(json_file_path, 'w', encoding='utf-8') as f:
                                    json.dump(scene_data, f, indent=2, ensure_ascii=False)
                                
                                # 执行人物生成
                                agents = execute_agent_plans(
                                    ue=ue, 
                                    agent_plans=agent_plans, 
                                    json_file_path=json_file_path, 
                                    print_info=False
                                )
                                
                                all_spawned_items = on_table_items
                                # 生成随机摄像头位置
                                center_location = calculate_entities_center(agents=agents, items=all_spawned_items)
                                camera_positions = generate_camera_positions(
                                    ue=ue,
                                    room_bound=room_bound,
                                    target_object=table_entity,
                                    center_location=center_location,
                                    distance_range=[250, 400],  # 距离目标
                                    height=[120, 250],  # 摄像头高度
                                    agents=agents,
                                    num_cameras=3,  # 生成3个摄像头
                                )
                                
                                # 创建所有摄像头
                                cameras = add_capture_camera(ue, camera_positions, center_location=center_location, target_obj=table_entity)
                                print(f"成功创建了 {len(cameras)} 个摄像头")
                                
                                # 添加摄像头到JSON
                                if cameras:
                                    add_entities_to_json(json_file_path=json_file_path, entities=cameras, entity_type='camera')
                                
                                # 拍摄图像
                                saved_images = capture_and_save_images(
                                    cameras=cameras,
                                    save_dir=json_save_dir,
                                    delay_before_capture=0.01
                                )
                                
                                print(f"  [SUCCESS] 成功生成组合 {side1}-{side2}-{side3}")
                                print(f"    保存路径: {json_save_dir_name}")
                                print(f"    人物数量: {len(agents)}")
                                print(f"    摄像头数量: {len(cameras)}")
                                print(f"    保存图像数量: {len(saved_images)}")
                                
                                # 可选：短暂等待以确保保存完成
                                time.sleep(0.1)
                                
                                # 清理人物
                                [ue.destroy_entity(agent.id) for agent in agents]
                        
                    else:
                        print(f"[CONTINUE] 房间 {room_name} 没有桌子，跳过")
                        continue
            
            except Exception as e:
                print(f"[ERROR] 处理地图 {map_name} 时发生错误: {str(e)}")
                import traceback
                traceback.print_exc()
                continue
    
    print("\n[DONE] 所有三人位置组合处理完成")




# 新的 Pipeline: 基于网格的物品放置系统
def run_pipeline_table_with_grid_items(map_range=None, min_room_area=4, min_table_area=0.4, 
                                       log_dir="./ownership/logs_grid", grid_dir="./ownership/table_boundaries",
                                       num_agents=None, agent_sides=None, max_item=9):
    """
    基于网格JSON数据在桌面上放置物品的Pipeline
    
    与原有pipeline的主要区别：
    - 使用 load_table_grid_json 加载网格数据
    - 使用 spawn_items_on_grid 替代原有的物品生成逻辑
    - 物品放置更加精确和可控
    
    Args:
        map_range: 地图范围
        min_room_area: 最小房间面积
        min_table_area: 最小桌子面积
        log_dir: 日志保存目录
        grid_dir: 网格JSON文件目录
        num_agents: 人物数量
        agent_sides: 人物站位
        max_item: 最大物品数量
    """
    # 读取筛选后的场景列表
    try:
        with open('./ownership/object/selected_scenes.txt', 'r', encoding='utf-8') as f:
            selected_scenes = [line.strip() for line in f if line.strip()]
        print(f"[INFO] 已加载 {len(selected_scenes)} 个筛选场景")
    except FileNotFoundError:
        print("[WARNING] selected_scenes.txt 文件不存在，将处理所有地图")
        selected_scenes = []
        
    # 读取物品列表
    try:
        ASSET_OWL_DICT = {}
        # 在主程序开始时加载资产信息
        ASSET_JSON_PATH = "./objects_info.json"
        load_asset_info(ASSET_JSON_PATH)
    except FileNotFoundError:
        print("[WARNING] objects_info.json 文件不存在")
        
    with ts.TongSim(
        grpc_endpoint="127.0.0.1:5056",
        legacy_grpc_endpoint="127.0.0.1:50052",
    ) as ue:
        # 定义地图范围
        if map_range is None:
            map_range = range(0, 300)

        for map_num in map_range:
            # 格式化地图名称
            map_name = f"SDBP_Map_{map_num:03d}"

            # 检查是否在筛选列表中
            if selected_scenes and map_name not in selected_scenes:
                print(f"[CONTINUE] 跳过不在筛选列表中的地图: {map_name}")
                continue

            # 打开地图
            print(f"\n{'='*60}")
            print(f"[PROCESSING] 正在打开地图: {map_name}")
            print(f"{'='*60}")
            success = ue.open_level(map_name)
            if not success:
                print(f"[WARNING] 无法打开地图: {map_name}，跳过")
                time.sleep(2)
                continue
            
            try:
                # 获取房间信息
                rooms = ue.spatical_manager.get_current_room_info()
                if not rooms:
                    print(f"[CONTINUE] 地图 {map_name} 中没有找到房间信息，跳过")
                    continue
                
                # 获取房间边界框信息
                room_bbox_dict = get_room_bbox(rooms)
                
                # 遍历当前地图的所有房间
                for room_info in rooms:
                    room_name = room_info['room_name']
                    
                    print(f"\n[PROCESSING] 处理地图 {map_name} 的房间: {room_name}")
                    room_bound = get_room_boundary(room_name, room_bbox_dict)

                    # 面积小于阈值跳过
                    if get_area(room_bound) < min_room_area:
                        print(f"[CONTINUE] 房间 {room_name} 面积小于 {min_room_area} 平方米，跳过")
                        continue

                    # 重新打开地图确保环境干净
                    success = ue.open_level(map_name)
                    if not success:
                        print(f"[WARNING] 无法打开地图: {map_name}，跳过")
                        continue

                    # 查询房间内的桌子
                    table_entitys = query_existing_objects_in_room(
                        ue=ue, 
                        room_bound=room_bound, 
                        target_types=['coffeetable', 'diningTable', 'table', 'Table'], 
                        object_name="桌子"
                    )
                    
                    # 处理多个桌子
                    if table_entitys:
                        print(f"[PROCESSING] 找到 {len(table_entitys)} 张桌子，开始处理...")
                        for i, table_entity in enumerate(table_entitys):
                            print(f"\n[PROCESSING] 处理第 {i+1} / {len(table_entitys)} 张桌子: {table_entity.id}")

                            # 验证桌子是否符合条件
                            if not validate_table(table_entity, min_table_area=min_table_area):
                                print(f"[CONTINUE] 桌子面积不符合条件，跳过")
                                continue

                            # ========== 加载网格数据 ==========
                            table_id = str(table_entity.id)
                            grid_data = load_table_grid_json(
                                map_name=map_name,
                                room_name=room_name,
                                table_id=table_id,
                                grid_dir=grid_dir
                            )
                            if not grid_data:
                                print(f"[WARNING] 未找到桌子 {table_id} 的网格数据，跳过")
                                continue
                            print(f"[SUCCESS] 成功加载网格数据: {len(grid_data.get('safe_grids', []))} 个安全网格")

                            # ========== 查找桌子附近的物品（使用新函数）==========
                            on_table_items_info, nearby_items_info = find_objects_near_table_with_info(
                                ue=ue,
                                table_object=table_entity,
                                search_distance=120.0,
                                print_info=False
                            )
                            
                            # 转换为旧格式（提取entity字段）
                            on_table_items = [item_info['entity'] for item_info in on_table_items_info]
                            
                            print(f"[INFO] 找到桌上物品 {len(on_table_items_info)} 个，附近物品 {len(nearby_items_info)} 个")

                            # ========== 删除桌子上的所有物品（清空桌面）==========
                            if on_table_items:
                                print(f"[INFO] 正在删除桌子上的 {len(on_table_items)} 个物品...")
                                for item in on_table_items:
                                    try:
                                        ue.destroy_entity(item.id)
                                    except Exception as e:
                                        print(f"[WARNING] 删除物品 {item.id} 失败: {e}")
                                print(f"[SUCCESS] 已清空桌面")

                            # ========== 生成人物配置 -- 重要人物配置参数 ========== 
                            agent_blueprints, agent_sides_config, agent_is_sit, agent_traits = generate_agent_configuration(
                                sit_probability=0.75,
                                agent_sides=agent_sides,
                                num_agents=num_agents,
                            )
                            
                            # 使用新的优化版本直接生成人物（现在返回agents和agent_features_list）
                            agents_complete_info, nearby_items_info = generate_and_spawn_agents(
                                ue=ue,
                                table_object=table_entity,
                                room_bound=room_bound,
                                nearby_objects=nearby_items_info,
                                agent_blueprints=agent_blueprints,
                                agent_sides=agent_sides_config,
                                agent_is_sit=agent_is_sit,
                                agent_traits=agent_traits,
                                min_distance=20,
                                max_distance=50,
                                min_agent_distance=60,
                                safe_margin=15,
                                max_chair_adjust_attempts=8,
                                chair_move_step=5.0,
                                print_info=False
                            )
                            agents, agent_features_list = extract_agents_and_features_from_complete_info(agents_complete_info)

                            # 创建保存目录和JSON文件
                            json_save_dir_name = f"table_scene_map{map_num:03d}_room_{room_name}_table{i+1}"
                            json_save_dir = os.path.join(log_dir, json_save_dir_name)
                            json_file_path = create_scene_json_file(map_name, room_name, table_entity, json_save_dir)

                            nearby_items = [item_info['entity'] for item_info in nearby_items_info]
                            # 添加附近的物品到JSON
                            if nearby_items:
                                add_entities_to_json(
                                    json_file_path=json_file_path,
                                    entities=nearby_items,
                                    entity_type='object',
                                    owner="room"
                                )
                                
                            # 检查条件：生成的人物数量必须>=2
                            agent_num = 2
                            if len(agents) < agent_num:
                                print(f"[CONTINUE] 未能生成足够的人物，结束。成功生成: {len(agents)}, 需要: {agent_num}")
                                # 释放人物
                                for agent in agents:
                                    try:
                                        ue.destroy_entity(agent.id)
                                    except:
                                        pass

                                # 删除json表格以及文件夹
                                if os.path.exists(json_file_path):
                                    os.remove(json_file_path)   
                                    try:
                                        os.rmdir(json_save_dir)
                                    except OSError:
                                        pass

                                continue

                            ue.change_view_mode(ViewModeType.MANUAL_CONTROL_VIEW)

                            # ========== 使用网格系统放置物品（替换原有的物品生成逻辑）==========
                            print(f"\n[PROCESSING] 开始使用网格系统放置物品...")
                            all_spawned_items, item_owners_list, item_features_list = spawn_items_on_grid_new(
                                ue=ue,
                                table_object=table_entity,
                                agents=agents,
                                grid_data=grid_data,
                                agent_features_list=agent_features_list,  # 传入人物特征列表
                                max_total_items=max_item,
                                max_items_per_agent=3,
                                print_info=True
                            )
                            
                            total_spawned_items = len(all_spawned_items)
                            print(f"[SUCCESS] 物品放置完成，共生成 {total_spawned_items} 个物品")
                            
                            # ========== 保存物品信息到JSON ==========
                            if all_spawned_items and item_owners_list and item_features_list:
                                # 验证列表长度一致性
                                if len(all_spawned_items) == len(item_owners_list) == len(item_features_list):
                                    # 构建完整的features_list，每个元素包含owner和type信息
                                    complete_features_list = []
                                    for owner, features in zip(item_owners_list, item_features_list):
                                        complete_features = features.copy()  # 复制原有的features
                                        complete_features_list.append(complete_features)
                                    
                                    # 批量添加所有物品到JSON
                                    add_entities_to_json(
                                        json_file_path=json_file_path,
                                        entities=all_spawned_items,
                                        entity_type='object',
                                        owner=None,  # 不使用统一owner
                                        features_list=complete_features_list
                                    )
                                    
                                    # 使用item_owners_list更新JSON中每个物品的owner字段
                                    try:
                                        with open(json_file_path, 'r', encoding='utf-8') as f:
                                            scene_data = json.load(f)
                                        
                                        # 更新objects列表中的owner
                                        if 'objects' in scene_data:
                                            # 获取最后添加的物品（应该是我们刚刚添加的）
                                            objects_count = len(scene_data['objects'])
                                            start_index = objects_count - len(all_spawned_items)
                                            
                                            for i, owner_id in enumerate(item_owners_list):
                                                idx = start_index + i
                                                if 0 <= idx < objects_count:
                                                    scene_data['objects'][idx]['owner'] = owner_id
                                        
                                        # 保存更新后的JSON
                                        with open(json_file_path, 'w', encoding='utf-8') as f:
                                            json.dump(scene_data, f, indent=2, ensure_ascii=False)
                                        
                                        print(f"[SUCCESS] 已将 {len(all_spawned_items)} 个物品添加到JSON文件")
                                    except Exception as e:
                                        print(f"[ERROR] 更新物品owner字段失败: {e}")
                                else:
                                    print(f"[ERROR] 物品列表长度不一致：spawned_items={len(all_spawned_items)}, "
                                          f"owners={len(item_owners_list)}, features={len(item_features_list)}")

                            # ========== 为人物生成随机动作 ==========
                            print(f"\n[PROCESSING] 开始为人物生成随机动作...")
                            action_stats = generate_actions_for_all_agents(
                                agents=agents,
                                agent_features_list=agent_features_list,
                                all_spawned_items=all_spawned_items,
                                item_owners_list=item_owners_list,
                                item_features_list=item_features_list,
                                action_probability=0.5,  # 50%的概率执行动作
                                print_info=True
                            )
                            
                            # ========== 保存人物信息到JSON（包含动作信息）==========
                            if agents and agent_features_list:
                                add_entities_to_json(
                                    json_file_path=json_file_path,
                                    entities=agents,
                                    entity_type='agent',
                                    features_list=agent_features_list,
                                    auto_detect_asset_type=False
                                )
                                print(f"[SUCCESS] 已将 {len(agents)} 个人物（含动作信息）添加到JSON文件")

                            # 生成随机摄像头位置
                            center_location = calculate_entities_center(agents=agents, items=all_spawned_items)
                            camera_positions = generate_camera_positions(
                                ue=ue,
                                room_bound=room_bound,
                                target_object=table_entity,
                                center_location=center_location,
                                distance_range=[200, 300],
                                height=[100, 250],
                                agents=agents,
                                num_cameras=8,
                            )

                            # 创建所有摄像头
                            cameras = add_capture_camera(
                                ue, 
                                camera_positions, 
                                center_location=center_location, 
                                target_obj=table_entity
                            )
                            print(f"[SUCCESS] 成功创建了 {len(cameras)} 个摄像头")

                            # 添加摄像头到JSON
                            if cameras:
                                add_entities_to_json(
                                    json_file_path=json_file_path, 
                                    entities=cameras, 
                                    entity_type='camera'
                                )

                            # 生成俯视摄像头位置
                            top_camera_pos = generate_top_view_camera_position(
                                room_bound=room_bound,
                                agents=agents,
                                items=all_spawned_items,
                                margin_factor=1.5,
                                safe_margin=30,
                                print_info=False
                            )

                            # 创建俯视摄像头
                            top_camera = add_capture_camera(
                                ue=ue,
                                camera_positions=top_camera_pos,
                                center_location=center_location, 
                                target_obj=table_entity,
                                camera_name_prefix="TopCamera",
                                print_info=False
                            )

                            if top_camera:
                                add_entities_to_json(
                                    json_file_path=json_file_path, 
                                    entities=top_camera, 
                                    entity_type='camera'
                                )

                            # 拍摄图像
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
                            
                            # 打印场景生成摘要
                            print(f"\n{'='*60}")
                            print(f"[SUCCESS] 场景生成完成: {json_save_dir_name}")
                            print(f"{'='*60}")
                            print(f"  地图: {map_name}")
                            print(f"  房间: {room_name}")
                            print(f"  桌子: {table_id}")
                            print(f"  人物数量: {len(agents)}")
                            print(f"  物品总数: {total_spawned_items}")
                            print(f"  摄像头数量: {len(cameras) + len(top_camera)}")
                            print(f"  保存图像数量: {len(saved_images)}")
                            print(f"  可用网格数: {len(grid_data.get('safe_grids', []))}")
                            print(f"{'='*60}\n")

                            # 释放人物
                            for agent in agents:
                                try:
                                    ue.destroy_entity(agent.id)
                                except:
                                    pass
                            
                            # 释放物品
                            for item in all_spawned_items:
                                try:
                                    ue.destroy_entity(item.id)
                                except:
                                    pass

                    else:
                        print(f"[CONTINUE] 房间 {room_name} 没有桌子，跳过")
                        continue
                    
            except Exception as e:
                print(f"[ERROR] 处理地图 {map_name} 时发生错误: {str(e)}")
                traceback.print_exc()
                continue
        
        print("\n[DONE] 基于网格的物品放置Pipeline完成")


# 批量重建场景 Pipeline
def run_pipeline_rebuild_scenes(scenes_list_file="./ownership/rebulid_scene/scenes_list.json", 
                                grid_dir="./ownership/table_boundaries",
                                log_dir="./ownership/logs_rebuild", 
                                max_item=5, filters=None, print_info=True):
    """
    从场景列表文件批量重建场景
    
    参考 run_pipeline_table_with_grid_items 的结构，但使用已保存的场景信息
    
    Args:
        scenes_list_file: 场景列表JSON文件路径
        grid_dir: 网格数据目录
        log_dir: 重建结果保存目录
        max_item: 最大物品数量
        filters: 筛选条件（可选），例如:
            {
                'combination_type': 'face_to_face',
                'agent_count': 2,
                'map_name': 'SDBP_Map_001'
            }
        print_info: 是否打印详细信息
    """
    # 读取场景列表
    from utils.rebuild import load_scenes_list, filter_scenes, rebuild_scene_from_info
    
    print(f"\n{'='*70}")
    print(f"[INFO] 开始批量重建场景")
    print(f"{'='*70}")
    print(f"  场景列表文件: {scenes_list_file}")
    print(f"  网格目录: {grid_dir}")
    print(f"  保存目录: {log_dir}")
    print(f"  最大物品数: {max_item}")
    print(f"{'='*70}\n")
    
    # 1. 加载场景列表
    scenes_list = load_scenes_list(scenes_list_file, print_info=print_info)
    
    if not scenes_list:
        print("[ERROR] 场景列表为空")
        return
    
    # 2. 应用筛选条件
    if filters:
        scenes_list = filter_scenes(
            scenes_list,
            map_name=filters.get('map_name'),
            room_name=filters.get('room_name'),
            combination_type=filters.get('combination_type'),
            positions=filters.get('positions'),
            agent_count=filters.get('agent_count')
        )
        print(f"[INFO] 筛选后剩余 {len(scenes_list)} 个场景\n")
    
    # 3. 批量处理
    total = len(scenes_list)
    success_count = 0
    failed_count = 0
    
    for i, scene_info in enumerate(scenes_list, 1):
        try:
            print(f"\n{'#'*70}")
            print(f"# 处理场景 {i}/{total}")
            print(f"{'#'*70}")
            
            # 重建场景（自动清理）
            result = rebuild_scene_from_info(
                scene_info=scene_info,
                grid_dir=grid_dir,
                log_dir=log_dir,
                max_item=max_item,
                auto_cleanup=True,  # 自动清理
                print_info=print_info
            )
            
            if result['success']:
                success_count += 1
                print(f"[SUCCESS] 场景 {i}/{total} 重建成功")
            else:
                failed_count += 1
                print(f"[FAILED] 场景 {i}/{total} 重建失败: {result['message']}")
        
        except Exception as e:
            failed_count += 1
            print(f"[ERROR] 场景 {i}/{total} 处理异常: {str(e)}")
            import traceback
            traceback.print_exc()
            continue
    
    # 4. 打印最终汇总（在所有场景处理完成后）
    print(f"\n{'='*70}")
    print(f"[DONE] 批量重建完成")
    print(f"{'='*70}")
    print(f"  总场景数: {total}")
    print(f"  成功: {success_count}")
    print(f"  失败: {failed_count}")
    print(f"  成功率: {success_count/total*100:.1f}%" if total > 0 else "  成功率: 0.0%")
    print(f"{'='*70}\n")


# 遍历添加新人物的 Pipeline
def run_pipeline_add_agent_variations(json_file_path, base_output_dir=None, 
                                      enable_add_agent=False, enable_change_status=False, 
                                      enable_swap_blueprints=False, enable_replace_blueprint=False,
                                      enable_change_action=False, enable_change_item_type=False,
                                      item_type_change_counts=None,
                                      adjust_item_count=0,
                                      move_item_count=0,
                                      print_info=True):
    """
    遍历所有可能的参数组合，为场景添加新人物和/或改变人物状态和/或交换/替换人物蓝图和/或改变人物动作和/或改变物品类型和/或增减物品数量和/或移动物品
    
    遍历策略：
    1. swap_agent_blueprints: 遍历所有可能的人物蓝图交换对（可选，与enable_replace_blueprint互斥）
    2. replace_agent_blueprint: 遍历所有可能的人物蓝图替换（可选，与enable_swap_blueprints互斥）
    3. change_agent_status: 遍历所有人物的状态改变（可选）
    4. change_agent_action: 遍历所有人物的动作改变（可选）
    5. change_item_type_count: 遍历所有指定的物品类型修改数量（可选）
    6. move_item_count: 移动物品到其他owner区域（可选）
    7. reference_agent_index: 遍历所有已有人物作为参考（可选）
    8. placement_strategy: 遍历 'face_to_face' 和 'same_side'
    8. new_agent_trait: 遍历所有不重复的蓝图
    
    Args:
        json_file_path: 原始场景JSON文件路径
        base_output_dir: 输出基础目录（可选）
        enable_add_agent: 是否启用添加新人物的遍历（默认False）
        enable_change_status: 是否启用改变人物状态的遍历（默认False）
        enable_swap_blueprints: 是否启用交换人物蓝图的遍历（默认False）
                               ⚠️ 与 enable_replace_blueprint 互斥
        enable_replace_blueprint: 是否启用替换人物蓝图的遍历（默认False）
                                 ⚠️ 与 enable_swap_blueprints 互斥
        enable_change_action: 是否启用改变人物动作的遍历（默认False）
        enable_change_item_type: 是否启用改变物品类型的遍历（默认False）
        item_type_change_counts: 物品类型修改数量列表（可选），例如 [1, 2, 3] 表示遍历修改1个、2个、3个物品
                                如果为None且enable_change_item_type=True，将根据场景中物品数量自动生成
        print_info: 是否打印详细信息
        
    示例：
        # 只添加新人物
        run_pipeline_add_agent_variations(..., enable_add_agent=True)
        
        # 只改变状态
        run_pipeline_add_agent_variations(..., enable_change_status=True)
        
        # 只交换蓝图
        run_pipeline_add_agent_variations(..., enable_swap_blueprints=True)
        
        # 只替换蓝图
        run_pipeline_add_agent_variations(..., enable_replace_blueprint=True)
        
        # 只改变动作
        run_pipeline_add_agent_variations(..., enable_change_action=True)
        
        # 只改变物品类型
        run_pipeline_add_agent_variations(..., enable_change_item_type=True, item_type_change_counts=[1, 2])
        
        # 替换蓝图 + 改变状态 + 改变动作 + 改变物品类型
        run_pipeline_add_agent_variations(..., enable_replace_blueprint=True, enable_change_status=True, 
                                         enable_change_action=True, enable_change_item_type=True,
                                         item_type_change_counts=[1, 2, 3])
        
        # 只重建原场景，不做任何修改
        run_pipeline_add_agent_variations(..., enable_add_agent=False, enable_change_status=False, enable_swap_blueprints=False)
    """
    from utils.rebuild import rebuild_and_modify_scene_from_json
    from configs.agent_config import AGENT_BLUEPRINT_MAPPING
    
    # 检查输入文件
    if not os.path.exists(json_file_path):
        print(f"[ERROR] JSON文件不存在: {json_file_path}")
        return
    
    # 确定输出基础目录
    if base_output_dir is None:
        json_dir = os.path.dirname(json_file_path)
        base_output_dir = os.path.join(json_dir, 'add_agent_variations')
    
    os.makedirs(base_output_dir, exist_ok=True)
    
    print(f"\n{'='*70}")
    print(f"[INFO] 开始遍历场景修改")
    print(f"{'='*70}")
    print(f"  输入JSON: {json_file_path}")
    print(f"  输出目录: {base_output_dir}")
    print(f"  交换人物蓝图: {'启用' if enable_swap_blueprints else '禁用'}")
    print(f"  替换人物蓝图: {'启用' if enable_replace_blueprint else '禁用'}")
    print(f"  添加新人物: {'启用' if enable_add_agent else '禁用'}")
    print(f"  改变人物状态: {'启用' if enable_change_status else '禁用'}")
    print(f"  改变人物动作: {'启用' if enable_change_action else '禁用'}")
    print(f"  改变物品类型: {'启用' if enable_change_item_type else '禁用'}")
    print(f"{'='*70}\n")
    
    # 检查互斥性
    if enable_swap_blueprints and enable_replace_blueprint:
        print(f"[ERROR] enable_swap_blueprints 和 enable_replace_blueprint 不能同时启用")
        return
    
    # 检查：如果所有功能都禁用，只重建一次原场景
    if not enable_add_agent and not enable_change_status and not enable_swap_blueprints and not enable_replace_blueprint and not enable_change_action and not enable_change_item_type:
        print(f"[INFO] 所有功能都禁用，将只重建原场景一次")
        
        output_dir = os.path.join(base_output_dir, "original_rebuild")
        
        try:
            result = rebuild_and_modify_scene_from_json(
                json_file_path=json_file_path,
                output_dir=output_dir,
                change_agent_status=None,
                add_agent=False,
                swap_agent_blueprints=None,
                change_agent_action=None,
                change_item_type_count=0,
                adjust_item_count=adjust_item_count,  # ✅ 传递物品调整参数
                move_item_count=move_item_count,  # ✅ 传递物品移动参数
                print_info=print_info
            )
            
            if result.get('success'):
                print(f"[SUCCESS] 原场景重建完成")
                print(f"  最终人物数: {result.get('agent_count', 0)}")
            else:
                print(f"[FAILED] 原场景重建失败: {result.get('message')}")
        
        except Exception as e:
            print(f"[ERROR] 原场景重建异常: {str(e)}")
            import traceback
            traceback.print_exc()
        
        return
    
    # 1. 读取JSON文件，获取已有人物和椅子信息
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            scene_data = json.load(f)
    except Exception as e:
        print(f"[ERROR] 读取JSON文件失败: {e}")
        return
    
    agents_data = scene_data.get('agents', [])
    if not agents_data:
        print(f"[ERROR] JSON中没有人物数据")
        return
    
    # 获取已有人物的蓝图
    existing_blueprints = set()
    for agent_data in agents_data:
        base_id = agent_data.get('base_id', '')
        if base_id:
            existing_blueprints.add(base_id)
    
    print(f"[INFO] 已有人物数量: {len(agents_data)}")
    print(f"[INFO] 已有人物蓝图: {existing_blueprints}\n")
    
    # 2. 生成蓝图交换或替换选项：根据开关决定是否遍历（互斥）
    blueprint_modification_options = []
    
    if enable_swap_blueprints:
        # 选项A: 生成所有可能的人物对交换 (i, j)，其中 i < j
        blueprint_modification_options = [None]  # 首先添加不交换的选项
        for i in range(len(agents_data)):
            for j in range(i + 1, len(agents_data)):
                blueprint_modification_options.append(('swap', (i, j)))
        print(f"[INFO] 蓝图交换选项: {len(blueprint_modification_options)} 个 (包括不交换)")
        if len(blueprint_modification_options) > 1:
            swap_pairs = [opt[1] for opt in blueprint_modification_options if opt is not None]
            print(f"[INFO] 交换对: {swap_pairs}")
    
    elif enable_replace_blueprint:
        # 选项B: 生成所有可能的人物蓝图替换
        blueprint_modification_options = [None]  # 首先添加不替换的选项
        
        # 遍历每个人物
        for agent_idx in range(len(agents_data)):
            current_blueprint = agents_data[agent_idx].get('base_id', '')
            
            # 遍历所有可用的蓝图
            for trait, blueprints in AGENT_BLUEPRINT_MAPPING.items():
                for blueprint in blueprints:
                    # 只有当新蓝图与当前蓝图不同时才添加
                    if blueprint != current_blueprint:
                        blueprint_modification_options.append(('replace', (agent_idx, blueprint)))
        
        print(f"[INFO] 蓝图替换选项: {len(blueprint_modification_options)} 个 (包括不替换)")
        if len(blueprint_modification_options) > 1:
            print(f"[INFO] 可替换组合数: {len(blueprint_modification_options) - 1} 个")
            # 打印每个人物可替换的蓝图数量
            for agent_idx in range(len(agents_data)):
                current_blueprint = agents_data[agent_idx].get('base_id', '')
                replace_count = sum(1 for opt in blueprint_modification_options 
                                   if opt is not None and opt[0] == 'replace' 
                                   and opt[1][0] == agent_idx)
                print(f"  人物 {agent_idx} ({current_blueprint}): {replace_count} 种可替换蓝图")
    
    else:
        blueprint_modification_options = [None]  # 只有不修改的选项
        print(f"[INFO] 蓝图交换/替换功能已禁用")
    
    # 3. 收集可用的蓝图（不与已有蓝图重复）- 仅在启用添加人物时需要
    available_blueprints = []
    if enable_add_agent:
        for trait, blueprints in AGENT_BLUEPRINT_MAPPING.items():
            for blueprint in blueprints:
                if blueprint not in existing_blueprints:
                    available_blueprints.append((blueprint, trait))
        
        if not available_blueprints:
            print(f"[WARNING] 所有蓝图已被使用，将使用所有蓝图")
            available_blueprints = [
                (bp, trait) 
                for trait, blueprints in AGENT_BLUEPRINT_MAPPING.items() 
                for bp in blueprints
            ]
        
        print(f"[INFO] 可用蓝图数量: {len(available_blueprints)}")
    else:
        print(f"[INFO] 添加新人物功能已禁用，跳过蓝图收集")
    
    # 4. 定义遍历参数
    placement_strategies = ['face_to_face', 'same_side']
    reference_agent_indices = list(range(len(agents_data)))
    
    # 状态改变选项：根据开关决定是否遍历
    if enable_change_status:
        change_status_options = [None]  # 不改变状态
        for i in range(len(agents_data)):
            change_status_options.append([i])  # 改变第i个人的状态
        print(f"[INFO] 状态改变选项: {len(change_status_options)} 个 (包括不改变)")
    else:
        change_status_options = [None]  # 只有不改变状态的选项
        print(f"[INFO] 状态改变功能已禁用")
    
    # 动作改变选项：根据开关决定是否遍历
    if enable_change_action:
        # 定义可用的动作类型
        available_action_types = ['point_at_item', 'reach_item', 'none']
        
        # 首先为每个人物生成所有可能的动作选项（包括保持原动作）
        per_agent_action_options = []
        for agent_idx in range(len(agents_data)):
            agent_data = agents_data[agent_idx]
            current_action = agent_data.get('features', {}).get('action', 'none')
            
            # 为该人物生成所有可能的动作（包括当前动作表示不改变）
            agent_options = [None]  # None表示保持原动作
            for new_action in available_action_types:
                if new_action != current_action:
                    agent_options.append(new_action)
            
            per_agent_action_options.append(agent_options)
            
            if print_info:
                print(f"[INFO] 人物 {agent_idx} (当前动作: {current_action}): {len(agent_options)} 种动作选项（包括不改变）")
        
        # 生成所有可能的动作组合（笛卡尔积）
        import itertools
        all_action_combinations = list(itertools.product(*per_agent_action_options))
        
        # 将组合转换为change_action格式
        change_action_options = []
        for combination in all_action_combinations:
            # combination 是一个元组，例如 (None, 'reach_item', None) 表示只改变第1个人物
            action_dict = {}
            for agent_idx, new_action in enumerate(combination):
                if new_action is not None:
                    action_dict[agent_idx] = new_action
            
            # 如果action_dict为空，表示所有人物都不改变动作
            if not action_dict:
                change_action_options.append(None)
            else:
                change_action_options.append(action_dict)
        
        print(f"[INFO] 动作改变选项: {len(change_action_options)} 个（所有人物动作的笛卡尔积）")
        if len(change_action_options) > 1:
            print(f"[INFO] 组合详情:")
            print(f"  - 不改变任何动作: 1 个")
            print(f"  - 改变至少一个人物动作: {len(change_action_options) - 1} 个")
            
            # 统计每种类型的组合数量
            single_change = sum(1 for opt in change_action_options if opt and len(opt) == 1)
            multi_change = sum(1 for opt in change_action_options if opt and len(opt) > 1)
            print(f"  - 只改变一个人物: {single_change} 个")
            print(f"  - 同时改变多个人物: {multi_change} 个")
    else:
        change_action_options = [None]  # 只有不改变动作的选项
        print(f"[INFO] 动作改变功能已禁用")
    
    # 物品类型改变：极简逻辑，启用就传2，不启用就不处理
    # 不需要遍历，不需要参数，固定传2
    if enable_change_item_type:
        print(f"[INFO] 物品类型改变功能已启用: 固定修改2个物品")
    else:
        print(f"[INFO] 物品类型改变功能已禁用")
    
    # 添加新人物选项：根据开关决定是否遍历
    if enable_add_agent:
        print(f"[INFO] 参考人物索引: {reference_agent_indices}")
        print(f"[INFO] 放置策略: {placement_strategies}")
        print(f"[INFO] 可用蓝图: {len(available_blueprints)} 个")
    else:
        # 如果不添加新人物，只执行一次（不遍历参考人物、策略、蓝图）
        reference_agent_indices = [0]  # 只执行一次
        placement_strategies = ['face_to_face']  # 占位，不会真正使用
        available_blueprints = [('placeholder', 'placeholder')]  # 占位，不会真正使用
        print(f"[INFO] 添加新人物功能已禁用")
    
    print()
    
    # 5. 开始遍历
    total_combinations = 0
    success_count = 0
    failed_count = 0
    
    for blueprint_mod in blueprint_modification_options:
        # 确定蓝图修改的描述（用于目录名）
        if blueprint_mod is None:
            mod_type = None
            mod_desc = "no_modify"
            swap_blueprints_param = None
            replace_blueprint_param = None
        elif blueprint_mod[0] == 'swap':
            mod_type = 'swap'
            idx1, idx2 = blueprint_mod[1]
            mod_desc = f"swap_{idx1}_{idx2}"
            swap_blueprints_param = blueprint_mod[1]
            replace_blueprint_param = None
        else:  # blueprint_mod[0] == 'replace'
            mod_type = 'replace'
            agent_idx, new_bp = blueprint_mod[1]
            # 从蓝图名称中提取简短标识（最后一部分）
            bp_short = new_bp.split('_')[-1] if '_' in new_bp else new_bp[:10]
            mod_desc = f"replace_{agent_idx}_{bp_short}"
            swap_blueprints_param = None
            replace_blueprint_param = blueprint_mod[1]
        
        for change_status in change_status_options:
            # 确定状态改变的描述（用于目录名）
            if change_status is None:
                status_change_desc = "no_change"
            else:
                status_change_desc = f"change_{change_status[0]}"
            
            for change_action in change_action_options:
                # 确定动作改变的描述（用于目录名）
                if change_action is None:
                    action_change_desc = "no_action_change"
                else:
                    # change_action 格式: {agent_idx: new_action_type, ...}
                    # 支持多个人物同时改变动作
                    action_parts = []
                    for agent_idx, new_action in sorted(change_action.items()):
                        # 简化动作名称
                        action_short = {'point_at_item': 'point', 'reach_item': 'reach', 'none': 'none'}
                        action_desc = action_short.get(new_action, new_action[:5])
                        action_parts.append(f"{agent_idx}{action_desc}")
                    action_change_desc = f"action_{'_'.join(action_parts)}"
                
                # 物品类型改变：不需要循环，直接处理
                for ref_index in reference_agent_indices:
                        for strategy in placement_strategies:
                            for new_blueprint, new_trait in available_blueprints:
                                total_combinations += 1
                                
                                # 简化逻辑：添加的新人物总是尝试坐下
                                # 函数内部会根据椅子可用性自动处理
                                should_sit = True
                                
                                # 构建输出目录名称
                                dir_parts = []
                                
                                # 添加蓝图修改信息（交换或替换）
                                if enable_swap_blueprints or enable_replace_blueprint:
                                    dir_parts.append(mod_desc)
                                
                                # 添加状态改变信息
                                if enable_change_status:
                                    dir_parts.append(status_change_desc)
                                
                                # 添加动作改变信息
                                if enable_change_action:
                                    dir_parts.append(action_change_desc)
                                
                                # 添加物品类型改变信息（固定修改2个）
                                if enable_change_item_type:
                                    dir_parts.append("item_change_2")
                                
                                # 添加新人物信息
                                if enable_add_agent:
                                    dir_parts.append(f"ref{ref_index}_{strategy}_{new_trait}_{new_blueprint.split('_')[-1]}_sit")
                                
                                # 如果没有任何功能启用，使用默认名称
                                if not dir_parts:
                                    output_dir_name = "rebuild"
                                else:
                                    output_dir_name = "_".join(dir_parts)
                                
                                output_dir = os.path.join(base_output_dir, output_dir_name)
                                
                                if print_info:
                                    print(f"\n{'='*70}")
                                    print(f"[PROCESSING] 组合 {total_combinations}:")
                                    if enable_swap_blueprints or enable_replace_blueprint:
                                        print(f"  蓝图修改: {mod_desc} (类型: {mod_type if mod_type else '无'})")
                                    if enable_change_status:
                                        print(f"  状态改变: {status_change_desc}")
                                    if enable_change_action:
                                        if change_action:
                                            # 显示所有改变的人物
                                            action_changes = []
                                            for agent_idx, new_action in change_action.items():
                                                action_changes.append(f"人物{agent_idx}→{new_action}")
                                            print(f"  动作改变: {', '.join(action_changes)}")
                                        else:
                                            print(f"  动作改变: 无")
                                    if enable_change_item_type:
                                        print(f"  物品类型改变: 修改 2 个物品")
                                    if enable_add_agent:
                                        print(f"  参考人物索引: {ref_index}")
                                        print(f"  放置策略: {strategy}")
                                        print(f"  新人物蓝图: {new_blueprint}")
                                        print(f"  新人物特性: {new_trait}")
                                        print(f"  新人物坐下: {should_sit}")
                                    print(f"  输出目录: {output_dir}")
                                    print(f"{'='*70}")
                            
                                try:
                                    # 极简逻辑：启用就传2，不启用就传0
                                    actual_item_change_count = 2 if enable_change_item_type else 0
                                    
                                    # 调用重建并修改函数
                                    result = rebuild_and_modify_scene_from_json(
                                        json_file_path=json_file_path,
                                        output_dir=output_dir,
                                        swap_agent_blueprints=swap_blueprints_param,
                                        replace_agent_blueprint=replace_blueprint_param,
                                        change_agent_status=change_status if enable_change_status else None,
                                        change_agent_action=change_action if enable_change_action else None,
                                        change_item_type_count=actual_item_change_count,
                                        adjust_item_count=adjust_item_count,  # ✅ 新增：物品数量调整
                                        move_item_count=move_item_count,  # ✅ 新增：物品位置移动
                                        add_agent=enable_add_agent,
                                        placement_strategy=strategy if enable_add_agent else 'face_to_face',
                                        reference_agent_index=ref_index if enable_add_agent else 0,
                                        new_agent_blueprint=new_blueprint if enable_add_agent else None,
                                        new_agent_trait=new_trait if enable_add_agent else None,
                                        should_sit=should_sit if enable_add_agent else True,
                                        print_info=print_info
                                        )
                                    
                                    if result.get('success'):
                                        success_count += 1
                                        if print_info:
                                            print(f"[SUCCESS] 组合 {total_combinations} 完成")
                                            if enable_swap_blueprints or enable_replace_blueprint:
                                                print(f"  蓝图修改: {mod_desc}")
                                            if enable_change_status:
                                                print(f"  状态改变: {status_change_desc}")
                                            if enable_change_action:
                                                if change_action:
                                                    # 显示所有改变的人物
                                                    action_changes = []
                                                    for agent_idx, new_action in change_action.items():
                                                        action_changes.append(f"人物{agent_idx}→{new_action}")
                                                    print(f"  动作改变: {', '.join(action_changes)}")
                                            if enable_change_item_type:
                                                print(f"  物品类型改变: 修改了 2 个物品")
                                            if enable_add_agent:
                                                added_agent = result.get('added_agent', False)
                                                print(f"  新人物添加: {'成功' if added_agent else '失败'}")
                                            print(f"  最终人物数: {result.get('agent_count', 0)}")
                                    else:
                                        failed_count += 1
                                        error_type = result.get('error_type', 'unknown')
                                        
                                        if print_info:
                                            print(f"[FAILED] 组合 {total_combinations} 失败: {result.get('message')}")
                                            print(f"  错误类型: {error_type}")
                                        
                                        # 删除失败的输出文件夹
                                        if os.path.exists(output_dir):
                                            try:
                                                import shutil
                                                shutil.rmtree(output_dir)
                                                if print_info:
                                                    print(f"[INFO] 已删除失败的输出文件夹: {output_dir}")
                                            except Exception as del_err:
                                                if print_info:
                                                    print(f"[WARNING] 删除文件夹失败: {del_err}")
                                
                                except Exception as e:
                                    failed_count += 1
                                    if print_info:
                                        print(f"[ERROR] 组合 {total_combinations} 异常: {str(e)}")
                                        import traceback
                                        traceback.print_exc()
                                    
                                    # 删除异常的输出文件夹
                                    if os.path.exists(output_dir):
                                        try:
                                            import shutil
                                            shutil.rmtree(output_dir)
                                            if print_info:
                                                print(f"[INFO] 已删除异常的输出文件夹: {output_dir}")
                                        except Exception as del_err:
                                            if print_info:
                                                print(f"[WARNING] 删除文件夹失败: {del_err}")
    
    # 6. 打印最终汇总
    print(f"\n{'='*70}")
    print(f"[DONE] 遍历完成")
    print(f"{'='*70}")
    print(f"  总组合数: {total_combinations}")
    print(f"  成功: {success_count}")
    print(f"  失败: {failed_count}")
    print(f"  成功率: {success_count/total_combinations*100:.1f}%" if total_combinations > 0 else "  成功率: 0.0%")
    print(f"  输出目录: {base_output_dir}")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    # ===== 原有Pipeline（基于分区的随机放置）=====
    # run_pipline_table_with_agents_objects(map_range=range(200, 201), log_dir="./ownership/2agents_1_allmap/", num_agents=2, max_item=4)
    # run_pipline_table_with_agents_objects(map_range=range(1, 300), log_dir="./ownership/4agents_1_allmap/", num_agents=4)
    
    # ===== 新Pipeline（基于网格的精确放置）=====
    # 测试单个地图
    run_pipeline_table_with_grid_items(map_range=range(5, 6), log_dir="./ownership/logs_grid_test/", num_agents=2, max_item=5)
    
    # 批量处理所有地图
    # run_pipeline_table_with_grid_items(map_range=range(1, 300), log_dir="./ownership/logs_grid_allmap/", num_agents=4, max_item=9)

    # ===== 两人位置组合 Pipeline =====
    # run_pipeline_agent_positions(map_range=range(243, 300), base_log_dir="./ownership/agent_positions_allmap_v3/")
    
    # # ===== 三人位置组合 Pipeline =====
    # run_pipeline_agent_positions_three_agents(map_range=range(1, 300), base_log_dir="./ownership/agent_positions_3agents_allmap/")
    
    # run_pipeline_table_with_grid_items(map_range=range(1, 300), log_dir="./ownership/try5/", num_agents=2, max_item=5)
    # run_pipeline_table_with_grid_items(map_range=range(1, 300), log_dir="./ownership/try6/", num_agents=2, max_item=5)
    # run_pipeline_rebuild_scenes(log_dir="./ownership/logs_rebuild2")
    
    # ===== 遍历添加新人物 Pipeline =====
    # 测试单个场景
    # run_pipeline_add_agent_variations(
    #     json_file_path="./ownership/logs_rebuild/SDBP_Map_005_kitchen_BP-DiningTable-03-C-0_2agents_back-right/scene_data.json",
    #     base_output_dir="./ownership/add_agent_test2/",
    #     enable_add_agent=False, 
    #     enable_change_status=False, 
    #     enable_swap_blueprints=False, 
    #     enable_replace_blueprint=False, 
    #     enable_change_action=False,
    #     enable_change_item_type=False,  # 启用物品类型改变
    #     item_type_change_counts=[2, 2],  # 只修改1个和2个物品（不包含0，不生成不修改的场景）
    #     adjust_item_count=0,
    #     move_item_count=2,
    #     print_info=True
    # )
    pass







import tongsim as ts
import random
import math
import time
import json
import os
import glob

from configs.agent_config import get_agent_trait
from configs.item_config import (
    ITEM_BLUEPRINTS as item_blueprints,
    ITEM_PROPERTIES as item_properties,
    AGENT_ITEM_MAPPING as agent_item_mapping,
    COMMON_ITEMS as common_items,
    NON_REPEATING_ITEM_TYPES as non_repeating_item_types,
    SITTING_ITEM_WEIGHT_BOOST as sitting_item_weight_boost,
    REPEATABLE_BLUEPRINTS as repeatable_blueprints
)
from configs.composed_item import (
    ITEM_CHAIN_RULES,
    get_chain_grids
)

# Import utility functions from other_util.py
from .other_util import (
    fix_aabb_bounds,
    check_position_in_bbox,
    check_item_overlap,
    is_bbox_contained,
    determine_object_side,
)

from .orientation_util import ( 
    look_at_rotation
)


# 桌子分区
def divide_table_into_zones(table_object, max_zone_length=200.0, zone_depth_ratio = 0.4, print_info=False):
    """
    将桌子划分为多个功能分区
    
    Args:
        table_object: 桌子对象
        target_agent: 目标人物对象（可选，用于确定主要朝向）
        zone_depth_ratio: 分区深度比例
        max_zone_length: 单个区域最大长度，超过此长度会自动拆分
        print_info: 是否打印分区信息
    
    Returns:
        dict: 分区信息字典，key为分区名称，value为分区边界框
    """

    # 获取桌子的世界AABB边界和位置
    table_aabb = table_object.get_world_aabb()
    table_min, table_max = fix_aabb_bounds(table_aabb)
    
    # 计算桌子尺寸
    table_width = table_max.x - table_min.x  # X方向宽度
    table_depth = table_max.y - table_min.y  # Y方向深度
    table_height = table_max.z - table_min.z  # Z方向高度
    
    zones = {}
    
    # 定义四个基本方向的分区
    sides = ['front', 'back', 'right', 'left']

    for side in sides:
        # 根据方向确定分区边界
        if side == 'front':
            # 前分区：从桌子前边缘向内部延伸
            zone_min = ts.Vector3(table_min.x, table_max.y - table_depth * zone_depth_ratio, table_max.z)
            zone_max = ts.Vector3(table_max.x, table_max.y, table_max.z)
            zone_width = table_width
            
        elif side == 'back':
            # 后分区：从桌子后边缘向内部延伸
            zone_min = ts.Vector3(table_min.x, table_min.y, table_max.z)
            zone_max = ts.Vector3(table_max.x, table_min.y + table_depth * zone_depth_ratio, table_max.z)
            zone_width = table_width
            
        elif side == 'right':
            # 右分区：从桌子右边缘（最小X值）向内部延伸
            # X轴：左正右负，所以右边缘是min.x（更负的值）
            zone_min = ts.Vector3(table_min.x, table_min.y, table_max.z)
            zone_max = ts.Vector3(table_min.x + table_width * zone_depth_ratio, table_max.y, table_max.z)
            zone_width = table_depth
            
        elif side == 'left':
            # 左分区：从桌子左边缘（最大X值）向内部延伸
            # X轴：左正右负，所以左边缘是max.x（更正的值）
            zone_min = ts.Vector3(table_max.x - table_width * zone_depth_ratio, table_min.y, table_max.z)
            zone_max = ts.Vector3(table_max.x, table_max.y, table_max.z)
            zone_width = table_depth
        
        # 检查是否需要拆分区域
        if zone_width > max_zone_length:
            
            if side in ['front', 'back']:
                mid_point = (zone_min.x + zone_max.x) / 2
                # X轴方向拆分（左正右负）
                # 左侧子区域（X值较大，更正的值）
                zone_left_min = ts.Vector3(mid_point, zone_min.y, zone_max.z)
                zone_left_max = ts.Vector3(zone_max.x, zone_max.y, zone_max.z)
                
                # 右侧子区域（X值较小，更负的值）
                zone_right_min = ts.Vector3(zone_min.x, zone_min.y, zone_max.z)
                zone_right_max = ts.Vector3(mid_point, zone_max.y, zone_max.z)
                
                zones[f'{side}_left'] = {'min': zone_left_min, 'max': zone_left_max, 'side': side}
                zones[f'{side}_right'] = {'min': zone_right_min, 'max': zone_right_max, 'side': side}
                
            else:
                mid_point = (zone_min.y + zone_max.y) / 2
                # 前侧子区域（Y值较大）
                zone_front_min = ts.Vector3(zone_min.x, mid_point, zone_max.z)
                zone_front_max = ts.Vector3(zone_max.x, zone_max.y, zone_max.z)
                
                # 后侧子区域（Y值较小）
                zone_back_min = ts.Vector3(zone_min.x, zone_min.y, zone_max.z)
                zone_back_max = ts.Vector3(zone_max.x, mid_point, zone_max.z)
                
                zones[f'{side}_front'] = {'min': zone_front_min, 'max': zone_front_max, 'side': side}
                zones[f'{side}_back'] = {'min': zone_back_min, 'max': zone_back_max, 'side': side}
                
        else:
            # 不需要拆分，使用完整区域
            zones[side] = {'min': zone_min, 'max': zone_max, 'side': side}
    
    # 打印分区信息
    if print_info:
        print(f"[INFO] 桌子尺寸: 宽{table_width:.1f} × 深{table_depth:.1f} × 高{table_height:.1f}")
        print("分区信息:")
        for zone_name, zone_data in zones.items():
            zone_size = (
                zone_data['max'].x - zone_data['min'].x,
                zone_data['max'].y - zone_data['min'].y
            )
            main_flag = " (主要)" if zone_data.get('is_main', False) else ""
            print(f"  {zone_name}: {zone_size[0]:.1f}×{zone_size[1]:.1f}{main_flag}")
            print(f"  {zone_data['min'], zone_data['max']}")
    
    return zones

# 根据人物位置对分区进行更细致的划分
def refine_zone_for_person(zone_bbox, table_object, target_agent, handedness='right', main_zone_min_width=50.0, temp_zone_size=40.0, print_info=False):
    """
    根据人物位置对分区进行更细致的划分
    
    Args:
        zone_bbox: 原始分区边界框 {'min': Vector3, 'max': Vector3, 'side': str}
        table_object: 桌子对象
        target_agent: 目标人物对象
        handedness: 利手信息 ('right'或'left')
        temp_zone_size: 临时区域大小
        main_zone_min_width: 最小工作区尺寸
        print_info: 是否打印信息
    
    Returns:
        dict: 细化后的分区信息
    """
    # 得出人物的side
    agent_side = determine_object_side(target_agent, table_object)
    
    if agent_side == 'unknown':
        print("[WARNING] 无法确定人物位置，使用默认分区")
        return {}
    
    # 先尝试精确匹配基础side（如front、back、left、right）
    if agent_side in zone_bbox:
        # 直接匹配基础分区
        agent_zone_data = zone_bbox[agent_side]
        agent_zone_name = agent_side
    else:
        # 处理细分分区的情况
        # 根据人物的基本方向找到相关的细分分区
        related_zones = {}
        for zone_name, zone_data in zone_bbox.items():
            if agent_side in zone_name: # 匹配细分区域  如 left_front, right_back 等
                related_zones[zone_name] = zone_data
        
        if len(related_zones) > 0:
            # 获取人物位置
            agent_pos = target_agent.get_location()
            agent_x, agent_y, agent_z = agent_pos.x, agent_pos.y, agent_pos.z
            
            # 根据人物的基本方向确定判断逻辑
            if agent_side in ['left', 'right']:
                # 对于左右分区，需要判断人物在前后方向的位置
                # 计算桌子在Y方向的中点
                table_aabb = table_object.get_world_aabb()
                table_min, table_max = fix_aabb_bounds(table_aabb)
                table_center_y = (table_min.y + table_max.y) / 2
                
                if agent_y > table_center_y:
                    # 人物在桌子的前侧
                    target_zone_name = f"{agent_side}_front"
                else:
                    # 人物在桌子的后侧
                    target_zone_name = f"{agent_side}_back"
                
                # 检查目标分区是否存在
                if target_zone_name in related_zones:
                    agent_zone_data = related_zones[target_zone_name]
                    agent_zone_name = target_zone_name
                else:
                    # 报错：目标分区不存在，说明分区划分逻辑有问题
                    raise ValueError(f"[ERROR] 目标分区 '{target_zone_name}' 不存在！可用的相关分区: {list(related_zones.keys())}")
                    
            elif agent_side in ['front', 'back']:
                # 对于前后分区，需要判断人物在左右方向的位置
                # 计算桌子在X方向的中点
                table_aabb = table_object.get_world_aabb()
                table_min, table_max = fix_aabb_bounds(table_aabb)
                table_center_x = (table_min.x + table_max.x) / 2
                
                if agent_x > table_center_x:
                    # X轴左正右负，agent_x > table_center_x 表示在桌子左侧
                    target_zone_name = f"{agent_side}_left"
                else:
                    # agent_x < table_center_x 表示在桌子右侧
                    target_zone_name = f"{agent_side}_right"
                
                # 检查目标分区是否存在
                if target_zone_name in related_zones:
                    agent_zone_data = related_zones[target_zone_name]
                    agent_zone_name = target_zone_name
                else:
                    # 报错：目标分区不存在，说明分区划分逻辑有问题
                    raise ValueError(f"[ERROR] 目标分区 '{target_zone_name}' 不存在！可用的相关分区: {list(related_zones.keys())}")
                    
        else:
            # 报错：没有找到任何相关分区，说明分区划分或方向判断有问题
            raise ValueError(f"错误：没有找到与方向 '{agent_side}' 相关的任何分区！所有可用分区: {list(zone_bbox.keys())}")

    # 获取匹配的分区信息
    zone_min = agent_zone_data['min']
    zone_max = agent_zone_data['max']
    zone_side = agent_zone_data['side']
    
    # 计算分区尺寸
    zone_width = zone_max.x - zone_min.x
    zone_depth = zone_max.y - zone_min.y

    # 计算桌子中心
    table_aabb = table_object.get_world_aabb()
    table_min, table_max = fix_aabb_bounds(table_aabb)
    table_center_x = (table_min.x + table_max.x) / 2
    table_center_y = (table_min.y + table_max.y) / 2
    
    # 确定利手侧（常用区域侧）
    # 注意：利手是相对于人的视角，而不是桌子的绝对方向
    dominant_side = handedness

    refined_zones = {}
    # 根据分区方向确定划分逻辑
    if zone_side in ['front', 'back']:
        # 前后分区：沿X轴划分（宽度方向）
        total_width = zone_width
        
        # 确保主工作区最小宽度
        main_zone_width = max(main_zone_min_width, total_width * 0.5)
        main_zone_width = min(main_zone_width, total_width)
        
        # 计算剩余宽度
        remaining_width = total_width - main_zone_width
        min_ramaining_width = 20.0  # 最小剩余宽度，避免过窄区域
        
        # 如果剩余宽度为10，只创建主工作区
        if remaining_width <= min_ramaining_width:
            # 主工作区
            main_zone_min = ts.Vector3(zone_min.x, zone_min.y, zone_min.z)
            main_zone_max = ts.Vector3(zone_max.x, zone_max.y, zone_max.z)
            
            refined_zones['main'] = {'min': main_zone_min, 'max': main_zone_max, 'type': 'main', 'area': get_area([main_zone_min.x, main_zone_min.y, main_zone_min.z, main_zone_max.x, main_zone_max.y, main_zone_max.z])}
        else:
            # 计算各区域起始位置（居中布置）
            main_zone_start_x = zone_min.x + remaining_width / 2
            main_zone_end_x = main_zone_start_x + main_zone_width
                
            # 常用区域和非常用区域（深度一致）
            # 根据人物位置和利手确定常用区域位置
            if agent_side == 'front':
                # 人在桌子前面
                if dominant_side == 'right':
                    # 右利手：常用区域在桌子左边（靠近xmin）
                    infrequent_zone_min = ts.Vector3(zone_min.x, zone_min.y, zone_min.z)
                    infrequent_zone_max = ts.Vector3(main_zone_start_x, zone_max.y, zone_max.z)
                    
                    frequent_zone_min = ts.Vector3(main_zone_end_x, zone_min.y, zone_min.z)
                    frequent_zone_max = ts.Vector3(zone_max.x, zone_max.y, zone_max.z)
                else:
                    # 左利手：常用区域在桌子右边（靠近xmax）
                    infrequent_zone_min = ts.Vector3(main_zone_end_x, zone_min.y, zone_min.z)
                    infrequent_zone_max = ts.Vector3(zone_max.x, zone_max.y, zone_max.z)
                    
                    frequent_zone_min = ts.Vector3(zone_min.x, zone_min.y, zone_min.z)
                    frequent_zone_max = ts.Vector3(main_zone_start_x, zone_max.y, zone_max.z)
            else:
                # 人在桌子后面（面对桌子）
                if dominant_side == 'right':
                    # 右利手：常用区域在桌子右边（靠近xmax）
                    infrequent_zone_min = ts.Vector3(main_zone_end_x, zone_min.y, zone_min.z)
                    infrequent_zone_max = ts.Vector3(zone_max.x, zone_max.y, zone_max.z)
                    
                    frequent_zone_min = ts.Vector3(zone_min.x, zone_min.y, zone_min.z)
                    frequent_zone_max = ts.Vector3(main_zone_start_x, zone_max.y, zone_max.z)
                else:
                    # 左利手：常用区域在桌子左边（靠近xmin）
                    infrequent_zone_min = ts.Vector3(zone_min.x, zone_min.y, zone_min.z)
                    infrequent_zone_max = ts.Vector3(main_zone_start_x, zone_max.y, zone_max.z)
                    
                    frequent_zone_min = ts.Vector3(main_zone_end_x, zone_min.y, zone_min.z)
                    frequent_zone_max = ts.Vector3(zone_max.x, zone_max.y, zone_max.z)
            
            # 主工作区
            main_zone_min = ts.Vector3(main_zone_start_x, zone_min.y, zone_min.z)
            main_zone_max = ts.Vector3(main_zone_end_x, zone_max.y, zone_max.z)

            # 构建返回结果
            refined_zones['main'] = {'min': main_zone_min, 'max': main_zone_max, 'type': 'main', 'area': get_area([main_zone_min.x, main_zone_min.y, main_zone_min.z, main_zone_max.x, main_zone_max.y, main_zone_max.z])}
            refined_zones['frequent'] = {'min': frequent_zone_min, 'max': frequent_zone_max, 'type': 'frequent', 'area': get_area([frequent_zone_min.x, frequent_zone_min.y, frequent_zone_min.z, frequent_zone_max.x, frequent_zone_max.y, frequent_zone_max.z])}
            refined_zones['infrequent'] = {'min': infrequent_zone_min, 'max': infrequent_zone_max, 'type': 'infrequent', 'area': get_area([infrequent_zone_min.x, infrequent_zone_min.y, infrequent_zone_min.z, infrequent_zone_max.x, infrequent_zone_max.y, infrequent_zone_max.z])}
    else:
        # 左右分区：沿Y轴划分（深度方向）
        total_depth = zone_depth
        
        # 确保主工作区最小宽度
        main_zone_depth = max(main_zone_min_width, total_depth * 0.5)
        main_zone_depth = min(main_zone_depth, total_depth)
        
        # 计算剩余深度
        remaining_depth = total_depth - main_zone_depth
        min_ramaining_width = 20.0  # 最小剩余宽度，避免过窄区域

        # 如果剩余深度为min_ramaining_width，只创建主工作区
        if remaining_depth <= min_ramaining_width:
            # 主工作区
            main_zone_min = ts.Vector3(zone_min.x, zone_min.y, zone_min.z)
            main_zone_max = ts.Vector3(zone_max.x, zone_max.y, zone_max.z)
            
            refined_zones['main'] = {'min': main_zone_min, 'max': main_zone_max, 'type': 'main', 'area': get_area([main_zone_min.x, main_zone_min.y, main_zone_min.z, main_zone_max.x, main_zone_max.y, main_zone_max.z])}
        else:        
            # 计算各区域起始位置（居中布置）
            main_zone_start_y = zone_min.y + remaining_depth / 2
            main_zone_end_y = main_zone_start_y + main_zone_depth

            # 常用区域和非常用区域（深度一致）
            # 根据人物位置和利手确定常用区域位置
            if agent_side == 'left':
                # 人在桌子左侧
                if dominant_side == 'right':
                    # 右利手：常用区域在桌子后边（靠近ymin）
                    frequent_zone_min = ts.Vector3(zone_min.x, zone_min.y, zone_min.z)
                    frequent_zone_max = ts.Vector3(zone_max.x, main_zone_start_y, zone_max.z)
                    
                    infrequent_zone_min = ts.Vector3(zone_min.x, main_zone_end_y, zone_min.z)
                    infrequent_zone_max = ts.Vector3(zone_max.x, zone_max.y, zone_max.z)
                else:
                    # 左利手：常用区域在桌子前边（靠近ymax）
                    frequent_zone_min = ts.Vector3(zone_min.x, main_zone_end_y, zone_min.z)
                    frequent_zone_max = ts.Vector3(zone_max.x, zone_max.y, zone_max.z)
                    
                    infrequent_zone_min = ts.Vector3(zone_min.x, zone_min.y, zone_min.z)
                    infrequent_zone_max = ts.Vector3(zone_max.x, main_zone_start_y, zone_max.z)
            else:
                # 人在桌子右侧
                if dominant_side == 'right':
                    # 右利手：常用区域在桌子前边（靠近ymax）
                    frequent_zone_min = ts.Vector3(zone_min.x, main_zone_end_y, zone_min.z)
                    frequent_zone_max = ts.Vector3(zone_max.x, zone_max.y, zone_max.z)
                    
                    infrequent_zone_min = ts.Vector3(zone_min.x, zone_min.y, zone_min.z)
                    infrequent_zone_max = ts.Vector3(zone_max.x, main_zone_start_y, zone_max.z)
                else:
                    # 左利手：常用区域在桌子后边（靠近ymin）
                    frequent_zone_min = ts.Vector3(zone_min.x, zone_min.y, zone_min.z)
                    frequent_zone_max = ts.Vector3(zone_max.x, main_zone_start_y, zone_max.z)
                    
                    infrequent_zone_min = ts.Vector3(zone_min.x, main_zone_end_y, zone_min.z)
                    infrequent_zone_max = ts.Vector3(zone_max.x, zone_max.y, zone_max.z)
            
            # 主工作区
            main_zone_min = ts.Vector3(zone_min.x, main_zone_start_y, zone_min.z)
            main_zone_max = ts.Vector3(zone_max.x, main_zone_end_y, zone_max.z)

            # 构建返回结果
            refined_zones['main'] = {'min': main_zone_min, 'max': main_zone_max, 'type': 'main', 'area': get_area([main_zone_min.x, main_zone_min.y, main_zone_min.z, main_zone_max.x, main_zone_max.y, main_zone_max.z])}
            refined_zones['frequent'] = {'min': frequent_zone_min, 'max': frequent_zone_max, 'type': 'frequent', 'area': get_area([frequent_zone_min.x, frequent_zone_min.y, frequent_zone_min.z, frequent_zone_max.x, frequent_zone_max.y, frequent_zone_max.z])}
            refined_zones['infrequent'] = {'min': infrequent_zone_min, 'max': infrequent_zone_max, 'type': 'infrequent', 'area': get_area([infrequent_zone_min.x, infrequent_zone_min.y, infrequent_zone_min.z, infrequent_zone_max.x, infrequent_zone_max.y, infrequent_zone_max.z])}

    # 临时区域（如果需要）
    if temp_zone_size > 0:
        # 判断分区类型
        if '_' not in agent_zone_name:
            # 基础分区（front、back、left、right）
            if zone_side in ['front', 'back']:
                # 前后分区
                if agent_side == 'front':
                    # 人在前面
                    if dominant_side == 'right':
                        # 右利手：临时区域放在左上角（Xmax, Ymax）
                        temp_zone_min = ts.Vector3(zone_max.x - temp_zone_size, zone_max.y - temp_zone_size, zone_min.z)
                        temp_zone_max = ts.Vector3(zone_max.x, zone_max.y, zone_max.z)
                    else:
                        # 左利手：临时区域放在右上角（Xmin, Ymax）
                        temp_zone_min = ts.Vector3(zone_min.x, zone_max.y - temp_zone_size, zone_min.z)
                        temp_zone_max = ts.Vector3(zone_min.x + temp_zone_size, zone_max.y, zone_max.z)
                else:
                    # 人在后面
                    if dominant_side == 'right':
                        # 右利手：临时区域放在右下角（Xmax, Ymin）
                        temp_zone_min = ts.Vector3(zone_max.x - temp_zone_size, zone_min.y, zone_min.z)
                        temp_zone_max = ts.Vector3(zone_max.x, zone_min.y + temp_zone_size, zone_max.z)
                    else:
                        # 左利手：临时区域放在左下角（Xmin, Ymin）
                        temp_zone_min = ts.Vector3(zone_min.x, zone_min.y, zone_min.z)
                        temp_zone_max = ts.Vector3(zone_min.x + temp_zone_size, zone_min.y + temp_zone_size, zone_max.z)
            else:
                # 左右分区
                if agent_side == 'left':
                    # 人在左侧
                    if dominant_side == 'right':
                        # 右利手：临时区域放在左下角（Xmax, Ymin）
                        temp_zone_min = ts.Vector3(zone_max.x - temp_zone_size, zone_min.y, zone_min.z)
                        temp_zone_max = ts.Vector3(zone_max.x, zone_min.y + temp_zone_size, zone_max.z)
                    else:
                        # 左利手：临时区域放在左上角（Xmax, Ymax）
                        temp_zone_min = ts.Vector3(zone_max.x - temp_zone_size, zone_max.y - temp_zone_size, zone_min.z)
                        temp_zone_max = ts.Vector3(zone_max.x, zone_max.y, zone_max.z)
                else:
                    # 人在右侧
                    if dominant_side == 'right':
                        # 右利手：临时区域放在右上角（Xmin, Ymax）
                        temp_zone_min = ts.Vector3(zone_min.x, zone_max.y - temp_zone_size, zone_min.z)
                        temp_zone_max = ts.Vector3(zone_min.x + temp_zone_size, zone_max.y, zone_max.z)
                    else:
                        # 左利手：临时区域放在右下角（Xmin, Ymin）
                        temp_zone_min = ts.Vector3(zone_min.x, zone_min.y, zone_min.z)
                        temp_zone_max = ts.Vector3(zone_min.x + temp_zone_size, zone_min.y + temp_zone_size, zone_max.z)
        else:
            # 细分分区（front_left、right_front等）- 与利手无关
            if 'front' in agent_zone_name and 'left' in agent_zone_name:
                # front_left: 临时区域放在左上角（Xmax, Ymax）
                temp_zone_min = ts.Vector3(zone_max.x - temp_zone_size, zone_max.y - temp_zone_size, zone_min.z)
                temp_zone_max = ts.Vector3(zone_max.x, zone_max.y, zone_max.z)
            elif 'front' in agent_zone_name and 'right' in agent_zone_name:
                # front_right: 临时区域放在右上角（Xmin, Ymax）
                temp_zone_min = ts.Vector3(zone_min.x, zone_max.y - temp_zone_size, zone_min.z)
                temp_zone_max = ts.Vector3(zone_min.x + temp_zone_size, zone_max.y, zone_max.z)
            elif 'back' in agent_zone_name and 'left' in agent_zone_name:
                # back_left: 临时区域放在左下角（Xmax, Ymin）
                temp_zone_min = ts.Vector3(zone_max.x - temp_zone_size, zone_min.y, zone_min.z)
                temp_zone_max = ts.Vector3(zone_max.x, zone_min.y + temp_zone_size, zone_max.z)
            elif 'back' in agent_zone_name and 'right' in agent_zone_name:
                # back_right: 临时区域放在右下角（Xmin, Ymin）
                temp_zone_min = ts.Vector3(zone_min.x, zone_min.y, zone_min.z)
                temp_zone_max = ts.Vector3(zone_min.x + temp_zone_size, zone_min.y + temp_zone_size, zone_max.z)
            elif 'left' in agent_zone_name and 'front' in agent_zone_name:
                # left_front: 临时区域放在左上角（Xmax, Ymax）
                temp_zone_min = ts.Vector3(zone_max.x - temp_zone_size, zone_max.y - temp_zone_size, zone_min.z)
                temp_zone_max = ts.Vector3(zone_max.x, zone_max.y, zone_max.z)
            elif 'left' in agent_zone_name and 'back' in agent_zone_name:
                # left_back: 临时区域放在左下角（Xmax, Ymin）
                temp_zone_min = ts.Vector3(zone_max.x - temp_zone_size, zone_min.y, zone_min.z)
                temp_zone_max = ts.Vector3(zone_max.x, zone_min.y + temp_zone_size, zone_max.z)
            elif 'right' in agent_zone_name and 'front' in agent_zone_name:
                # right_front: 临时区域放在右上角（Xmin, Ymax）
                temp_zone_min = ts.Vector3(zone_min.x, zone_max.y - temp_zone_size, zone_min.z)
                temp_zone_max = ts.Vector3(zone_min.x + temp_zone_size, zone_max.y, zone_max.z)
            elif 'right' in agent_zone_name and 'back' in agent_zone_name:
                # right_back: 临时区域放在右下角（Xmin, Ymin）
                temp_zone_min = ts.Vector3(zone_min.x, zone_min.y, zone_min.z)
                temp_zone_max = ts.Vector3(zone_min.x + temp_zone_size, zone_min.y + temp_zone_size, zone_max.z)
        
        refined_zones['temporary'] = {'min': temp_zone_min, 'max': temp_zone_max, 'type': 'temporary', 'area': get_area([temp_zone_min.x, temp_zone_min.y, temp_zone_min.z, temp_zone_max.x, temp_zone_max.y, temp_zone_max.z])}

    # 打印分区信息
    if print_info:
        print(f"[INFO] 人物专属分区 (侧: {zone_side}, 利手: {handedness}), 桌子分区: {agent_zone_name}:")
        for zone_name, zone_data in refined_zones.items():
            zone_size_x = zone_data['max'].x - zone_data['min'].x
            zone_size_y = zone_data['max'].y - zone_data['min'].y
            print(f"  {zone_name}: {zone_size_x:.1f}×{zone_size_y:.1f}")
            print(f"    {zone_data['min']}, {zone_data['max']}")
    
    return refined_zones


# ============== 物品生成相关函数(过去版本，现在停用) ==============
# 为每个agent生成物品配置
def generate_item_configurations(agents, zone_configs, max_total_items=5, max_items_per_agent=3, max_items_per_zone=1, print_info=False):
    """
    为每个agent生成物品配置
    
    Args:
        agents: 人物对象列表
        zone_configs: zone配置列表
        max_total_items: 桌面最大物品总数
        max_items_per_agent: 每个人物最多物品数量
        max_items_per_zone: 每个分区最多物品数量
        print_info: 是否打印调试信息
    
    Returns:
        list: 物品配置列表，每个元素为字典格式
    """

    # 检查配置完整性
    if not all([item_blueprints, item_properties, agent_item_mapping, common_items, non_repeating_item_types]):
        raise ValueError("[ERROR] 物品配置加载失败")


    # 检查agents和zone_configs长度是否匹配
    if len(agents) != len(zone_configs):
        raise ValueError("[ERROR] agents和zone_configs长度必须一致")

    # 第一步：确定每个人物类型
    agent_types = {}
    for agent in agents:
        agent_id = str(getattr(agent, 'id', ''))
        agent_type = get_agent_trait(agent_id) or 'unknown'
        
        if agent_type == 'unknown':
            print(f"[WARNING] 无法识别人物类型 {agent_id}")
        
        agent_types[agent] = agent_type

    # 初始化数据结构
    all_configs = []
    used_items = set()  # 已使用的物品
    used_item_types = set()  # 已使用的非重复物品类型
    # agent_occupied_zones = {agent: set() for agent in agents}  # 每个人物已占用的分区
    agent_item_count = {agent: 0 for agent in agents}  # 每个人物的物品数量

    agent_zone_occupancy = {}
    for agent in agents:
        agent_zone_occupancy[agent] = {
            'main': 0,
            'frequent': 0,
            'infrequent': 0,
            'temporary': 0
        }

    # 合并特定偏好和通用物品
    all_item_preferences = {}
    # 为每个人物类型创建偏好配置
    for agent_type in agent_item_mapping.keys():
        all_item_preferences[agent_type] = []
        
        # 添加特定物品
        for item_type in agent_item_mapping[agent_type]:
            if item_type in item_properties:
                all_item_preferences[agent_type].append({
                    'types': [item_type],
                    **item_properties[item_type]
                })
        
        # 添加通用物品
        for item_type in common_items:
            if item_type in item_properties:
                all_item_preferences[agent_type].append({
                    'types': [item_type],
                    **item_properties[item_type]
                })
    # 确保unknown类型存在
    if 'unknown' not in all_item_preferences:
        all_item_preferences['unknown'] = [{
            'types': ['book'],
            **item_properties['book']
        }]

    # 第二步：循环生成物品配置
    attempt_count = 0
    max_attempts = max_total_items * 10000  # 设置最大尝试次数，避免无限循环
    while len(all_configs) < max_total_items and attempt_count < max_attempts:
        attempt_count += 1
        # 如果所有人物都已达到最大物品数量，提前结束
        if all(count >= max_items_per_agent for count in agent_item_count.values()):
            if print_info:
                print("[CONTINUE] 所有人物均已达到最大物品数量，停止生成")
            break

        # 过滤掉已经被使用的非重复物品类型
        available_item_types = [t for t in item_blueprints.keys() 
                            if item_blueprints[t] and 
                            (t not in non_repeating_item_types or t not in used_item_types)]
        if not available_item_types:
            if print_info:
                print("[CONTINUE] 没有可用的物品类型，停止生成")
            break
        item_type = random.choice(available_item_types)

        # 随机选择一个具体的物品
        available_items = [i for i in item_blueprints[item_type] if i not in used_items]
        if not available_items:
            if print_info:
                print(f"[CONTINUE] 物品类型 {item_type} 没有可用的物品，重新选择类型")
            continue
        item = random.choice(available_items)

        # 找到所有可能喜欢这个物品的人物类型
        possible_agent_types = []
        for agent_type, prefs in all_item_preferences.items():
            for pref in prefs:
                if item_type in pref['types']:
                    if agent_type not in possible_agent_types:
                        possible_agent_types.append(agent_type)
                    break

        # 找到符合条件的人物
        valid_agents = []
        for agent in agents:
            if (agent_types[agent] in possible_agent_types and agent_item_count[agent] < max_items_per_agent):
                valid_agents.append(agent)
        if not valid_agents:
            if print_info:
                print(f"[CONTINUE] 没有符合条件的人物来放置物品 {item}，重新选择物品")
            continue
        # 随机选择一个有效人物
        agent = random.choice(valid_agents)
        agent_type = agent_types[agent]
        
        # 找到这个人物类型对这个物品的偏好设置
        preference_settings = []
        for pref in all_item_preferences[agent_type]:
            if item_type in pref['types']:
                preference_settings.append(pref)
        if not preference_settings:
            if print_info:
                print(f"[CONTINUE] 人物类型 {agent_type} 没有偏好设置来放置物品 {item}，重新选择人物")
            continue
        # 随机选择一个偏好设置
        preference = random.choice(preference_settings)

        # 找到对应的zone_config
        agent_idx = agents.index(agent)
        zone_config = zone_configs[agent_idx]

        # 找到可用的区域类型
        available_zone_types = list(zone_config.keys()) # 获取当前人物实际存在的分区类型
        available_zones = []
        # 如果只有main分区，允许frequent/infrequent类型的物品放在main中
        if 'frequent' not in available_zone_types and 'infrequent' not in available_zone_types:
            # 创建偏好区域的副本
            adjusted_zones = preference['zone_types'].copy()
            
            # 将frequent和infrequent替换为main（如果main存在）
            if 'main' in available_zone_types:
                # 替换逻辑：将frequent/infrequent替换为main
                adjusted_zones = ['main' if zone in ['frequent', 'infrequent'] else zone for zone in adjusted_zones]
                adjusted_zones = list(set(adjusted_zones)) # 去重

            # 只保留实际存在的分区
            available_zones = [zone for zone in adjusted_zones if zone in available_zone_types]
        else:
            # 有多个分区时，只允许放在实际存在的分区中
            available_zones = [zone for zone in preference['zone_types'] if zone in available_zone_types]
        
        # 过滤掉已经被占用的区域
        # available_zones = [zone for zone in available_zones if zone not in agent_occupied_zones[agent]]

        available_zones = [zone for zone in available_zones  if agent_zone_occupancy[agent][zone] < max_items_per_zone]
        if not available_zones:
            if print_info:
                print(f"[CONTINUE] 人物 {agent.id} 的所有偏好区域均已被占用，重新选择人物")
            continue
        
        # 随机选择一个区域类型
        zone_type = random.choice(available_zones)

        # 旋转角度处理
        rotation_z = random.randint(0, 360) if preference['rotation_z'] == 360 else preference['rotation_z']

        # 创建配置
        item_config = {
            'agent': agent,
            'refined_zones': zone_config,
            'zone_types': [zone_type],
            'item_blueprints': [item],
            'scale': preference['scale'],
            'rotation_z': rotation_z,
            'rotation_x': preference['rotation_x'],
            'rotation_y': preference['rotation_y'],
            'max_distance': 150.0,
            'min_distance': 10.0,
            'safe_margin': preference.get('safe_margin', 4.0),  # 使用物品特定的安全边距
            'item_type': item_type
        }

        # 更新状态
        used_items.add(item)    # 添加到已使用物品集合
        # agent_occupied_zones[agent].add(zone_type) # 占用该区域 一个区域只能放一个物品
        agent_zone_occupancy[agent][zone_type] += 1
        agent_item_count[agent] += 1    # 该人物物品数量+1
        all_configs.append(item_config)

        # 如果是非重复物品类型，添加到已使用类型集合
        if item_type in non_repeating_item_types:
            used_item_types.add(item_type)

    return all_configs

# 根据特定的分区生成物品
def spawn_items_in_person_zone(ue, table_object, target_agent, refined_zones, zone_types, item_blueprints, scale=ts.Vector3(1, 1, 1), 
                               rotation_z=0, rotation_x=0, rotation_y=0, on_table_items=None, max_distance=90.0, min_distance=10.0, 
                               safe_margin=5.0, safe_margin_table = 12, json_file_path=None, item_type=None, print_info=False):
    """
    在人物专属分区内生成物品
    
    Args:
        ue: TongSim实例
        table_object: 桌子对象
        target_agent: 目标人物对象
        item_blueprints: 物品蓝图列表
        refined_zones: 细化后的分区信息
        zone_types: 指定的分区类型
        rotation: 旋转角度
        on_table_items: 桌子上已有的物品列表
        max_distance: 物品离桌子靠人一侧的最大距离
        min_distance: 物品离桌子靠人一侧的最小距离
        safe_margin: 物品离其他物品的安全距离
        print_info: 是否打印信息
    
    Returns:
        list: 生成的物品对象列表
    """

    if on_table_items is None:
        on_table_items = []
    
    # 检查zone_type是否有效
    valid_zones = []
    for zone_type in zone_types:
        if zone_type in refined_zones:
            valid_zones.append(zone_type)
        else:
            raise ValueError(f"[ERROR] 分区类型 '{zone_type}' 不存在于细化分区中")
    
    # 获取桌子的AABB和表面高度
    table_aabb = table_object.get_world_aabb()
    table_min, table_max = fix_aabb_bounds(table_aabb)
    table_surface_z = table_max.z

    # 获取目标人物位置
    target_pos = target_agent.get_location()
    
    # 获取已知物品的AABB列表
    existing_aabbs = []
    for item in on_table_items:
        item_aabb = item.get_world_aabb()
        item_min, item_max = fix_aabb_bounds(item_aabb)
        existing_aabbs.append((item_min, item_max))

    spawned_items = []
    item_aabbs = existing_aabbs.copy()  # 复制已知物品的AABB
    
    # 为每个蓝图生成一个物品
    for i, blueprint in enumerate(item_blueprints):
        item_placed = False
        attempts = 0
        max_attempts=100

        # 根据物品索引选择分区类型
        zone_type = valid_zones[i % len(valid_zones)]
        zone_data = refined_zones[zone_type]
        # 获取分区边界
        zone_min = zone_data['min']
        zone_max = zone_data['max']

        # 尝试在分区内放置物品
        while not item_placed and attempts < max_attempts:
            attempts += 1

            # 在选择的区域表面随机生成位置
            item_x = random.uniform(zone_min.x, zone_max.x)
            item_y = random.uniform(zone_min.y, zone_max.y)
            item_z = table_surface_z + 50.0  # 放在桌面之上
            
            item_location = ts.Vector3(item_x, item_y, item_z)

            # 获取人物相对于桌子的位置
            agent_side = determine_object_side(target_agent, table_object)
            
            # 计算并调整物品位置
            if agent_side in ['front', 'back']:
                # 计算分区y方向的范围
                zone_y_range = abs(zone_max.y - zone_min.y)
                
                if agent_side == 'front':
                    # 如果分区范围小于最小距离要求
                    if zone_y_range < min_distance:
                        if print_info:
                            print(f"[DEBUG] 分区范围({zone_y_range:.1f})小于最小距离要求({min_distance:.1f})，使用分区最大值")
                        item_y = zone_min.y 
                    else:
                        # 计算到前边缘的距离
                        edge_distance = abs(item_y - table_max.y)
                        if edge_distance > max_distance or edge_distance < min_distance:
                            continue
                else:  # back
                    if zone_y_range < min_distance:
                        if print_info:
                            print(f"[DEBUG] 分区范围({zone_y_range:.1f})小于最小距离要求({min_distance:.1f})，使用分区最小值")
                        item_y = zone_max.y 
                    else:
                        edge_distance = abs(item_y - table_min.y)
                        if edge_distance > max_distance or edge_distance < min_distance:
                            continue
            else:  # left or right
                # 计算分区x方向的范围
                zone_x_range = abs(zone_max.x - zone_min.x)
                
                if agent_side == 'left':
                    if zone_x_range < min_distance:
                        if print_info:
                            print(f"[DEBUG] 分区范围({zone_x_range:.1f})小于最小距离要求({min_distance:.1f})，使用分区最大值")
                        item_x = zone_min.x 
                    else:
                        edge_distance = abs(item_x - table_max.x)
                        if edge_distance > max_distance or edge_distance < min_distance:
                            continue
                else:  # right
                    if zone_x_range < min_distance:
                        if print_info:
                            print(f"[DEBUG] 分区范围({zone_x_range:.1f})小于最小距离要求({min_distance:.1f})，使用分区最小值")
                        item_x = zone_max.x 
                    else:
                        edge_distance = abs(item_x - table_min.x)
                        if edge_distance > max_distance or edge_distance < min_distance:
                            continue
            
            # 更新物品位置
            item_location = ts.Vector3(item_x, item_y, item_z)

            # 检查是否与其他物品重叠
            overlap_found_pre = False
            for existing_min, existing_max in item_aabbs:
                if check_position_in_bbox(item_location, existing_min, existing_max, safe_margin, False):
                    overlap_found_pre = True
                    break
            if overlap_found_pre:
                continue

            target_tem_pos = ts.Vector3(target_pos.x, target_pos.y, item_z)
            rotation_quat = look_at_rotation(item_location, target_tem_pos)

            # 创建绕各个轴的旋转四元数
            def create_axis_rotation(angle_degrees, axis):
                """创建绕指定轴旋转的四元数"""
                angle_rad = math.radians(angle_degrees) / 2
                if axis == 'x':
                    return ts.Quaternion(
                        math.cos(angle_rad),  # w
                        math.sin(angle_rad),  # x
                        0,                    # y
                        0                     # z
                    )
                elif axis == 'y':
                    return ts.Quaternion(
                        math.cos(angle_rad),  # w
                        0,                    # x
                        math.sin(angle_rad),  # y
                        0                     # z
                    )
                elif axis == 'z':
                    return ts.Quaternion(
                        math.cos(angle_rad),  # w
                        0,                    # x
                        0,                    # y
                        math.sin(angle_rad)   # z
                    )
            
            # 创建各个轴的旋转
            x_rotation = create_axis_rotation(rotation_x, 'x')
            y_rotation = create_axis_rotation(rotation_y, 'y')
            z_rotation = create_axis_rotation(rotation_z, 'z')

            # 组合所有旋转（注意旋转顺序很重要，这里使用Z->Y->X的顺序）
            final_rotation = rotation_quat * z_rotation * y_rotation * x_rotation

            # 生成物品
            item_obj = ue.spawn_entity(
                entity_type=ts.BaseObjectEntity,
                blueprint=blueprint,
                location=item_location,
                is_simulating_physics=False,
                scale=scale,
                quat=final_rotation
            )
            
            # 等待物理引擎稳定
            time.sleep(0.01)
            
            # 获取物品的边界框
            item_aabb = item_obj.get_world_aabb()
            item_min, item_max = fix_aabb_bounds(item_aabb)
            
            # 检查是否与其他物品重叠
            overlap_found = False
            for existing_min, existing_max in item_aabbs:
                if check_item_overlap(
                    item_min, item_max, 
                    existing_min, existing_max, 
                    safe_margin=safe_margin
                ):
                    overlap_found = True
                    break
            if overlap_found:
                ue.destroy_entity(item_obj.id)
                continue
            
            # 检查物品是否完全在桌子上（考虑安全边距）
            if not is_bbox_contained(
                item_min, item_max,  # 物品的边界框
                table_min, table_max,  # 桌子的边界框
                safe_margin=safe_margin_table,  # 可以根据需要调整安全边距
                check_z_axis=False  # Z轴通常不需要检查，因为物品在桌子上
            ):
                ue.destroy_entity(item_obj.id)
                continue
            
            item_x = random.uniform(zone_min.x, zone_max.x)
            item_y = random.uniform(zone_min.y, zone_max.y)
            item_z = table_surface_z + 1.0

            item_location = ts.Vector3(item_x, item_y, item_z)
            # 成功放置物品  删除再放置物品(有物理引擎)
            ue.destroy_entity(item_obj.id)
            item_obj = ue.spawn_entity(
                entity_type=ts.BaseObjectEntity,
                blueprint=blueprint,
                location=item_location,
                is_simulating_physics=True,
                scale=scale,
                quat=final_rotation
            )

            time.sleep(2.0)
            # 落地检测
            item_position = item_obj.get_location()
            if abs(item_position.z - table_min.z) < abs(item_position.z - table_surface_z) or abs(item_position.z - table_surface_z) > 40:
                ue.destroy_entity(item_obj.id)
                attempts += 5
                if print_info:
                    print("物品掉落在地下，重新生成")
                continue

            # 对特定物品进行旋转检测
            if item_type in ['drink', 'milk', 'wine', 'computer', 'cup']:
                # 获取当前物品的旋转
                current_rotation = item_obj.get_rotation()
                
                # 手动计算四元数点积
                dot_product = (current_rotation.w * final_rotation.w + 
                             current_rotation.x * final_rotation.x + 
                             current_rotation.y * final_rotation.y + 
                             current_rotation.z * final_rotation.z)
                
                # 确保dot_product在[-1, 1]范围内
                dot_product = max(-1.0, min(1.0, dot_product))
                
                # 计算旋转角度（弧度）
                angle_rad = 2 * math.acos(abs(dot_product))
                # 转换为角度
                rotation_diff = math.degrees(angle_rad)
                
                # 如果旋转差异超过阈值
                if rotation_diff > 15:
                    ue.destroy_entity(item_obj.id)
                    # if print_info:
                    #     print(f"[WARNING] {item_type} 旋转变化过大 ({rotation_diff:.1f}度)，重新生成")
                    print(f"[WARNING] {item_type} 旋转变化过大 ({rotation_diff:.1f}度)，重新生成")
                    continue

            # 成功生成物品后，立即添加到JSON文件
            if json_file_path and item_type:
                # 构建特征信息
                features =  [{'type': item_type}]
                
                # 立即添加到JSON
                add_entities_to_json(
                    json_file_path=json_file_path,
                    entities=[item_obj],  # 单个物品列表
                    entity_type='object',
                    owner=str(target_agent.id),  # 设置所有者
                    features_list=features  # 添加物品类型特征
                )

            spawned_items.append(item_obj)
            item_aabbs.append((item_min, item_max))
            item_placed = True

            # 同时更新传入的 on_table_items
            if on_table_items is not None:
                on_table_items.append(item_obj)
            if print_info:
                print(f"[PROCESSING] 物品 {blueprint} 位置: {item_location} "
                      f"生成成功在 {zone_type} 区域, min: {zone_min} max: {zone_max}, 到{agent_side}边缘距离: {edge_distance:.1f}")
        
        if not item_placed:
            print(f"[CONTINUE] {max_attempts} 次尝试后 无法放置物品 {blueprint} 在 {zone_type} 区域, min: {zone_min} max: {zone_max}")
    
    return spawned_items


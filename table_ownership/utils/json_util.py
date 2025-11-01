import tongsim as ts
import json
import os
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

# 导入人物配置模块
from configs.agent_config import extract_base_agent_id, get_agent_trait

# Import utility functions from other_util.py
from .other_util import fix_aabb_bounds

# 全局变量，存储资产信息（只保留ID和owl类型的映射）
ASSET_OWL_DICT = {}

import json
from typing import List, Dict, Any, Optional
def add_entities_to_json(json_file_path: str, entities: List[Any], entity_type: str, owner: Optional[str] = None, 
                         features: Optional[Dict[str, Any]] = None, features_list: Optional[List[Dict[str, Any]]] = None,
                         auto_detect_asset_type: bool = True) -> bool:
    """
    添加实体信息到现有的JSON文件中
    
    Args:
        json_file_path: JSON文件路径
        entities: 实体对象列表
        entity_type: 实体类型 ('object', 'agent', 'camera')
        owner: 所有者信息（可选）
        features: 统一的特征信息（可选，适用于所有实体）
        features_list: 每个实体的特征信息列表（可选，与entities一一对应）
        auto_detect_asset_type: 是否自动检测资产类型
    
    Returns:
        bool: 是否成功添加
    """

    if not entities:
        print("[INFO] 没有实体需要添加到JSON")
        return True
    
    try:
        # 读取现有JSON文件
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 确保objects字段存在
        if "objects" not in data:
            data["objects"] = []
        
        # 根据实体类型确定目标列表
        if entity_type == 'object':
            target_list = data.setdefault("objects", [])
        elif entity_type == 'agent':
            target_list = data.setdefault("agents", [])
        elif entity_type == 'camera':
            target_list = data.setdefault("cameras", [])
        else:
            raise ValueError(f"不支持的实体类型: {entity_type}。支持的类型: 'object', 'agent', 'camera'")

        # 检查features_list长度是否匹配
        if features_list and len(features_list) != len(entities):
            print(f"[WARNING] 特征列表长度({len(features_list)})与实体数量({len(entities)})不匹配，将不使用特征列表")
            features_list = None

        added_count = 0

        # 处理每个实体
        for i, entity in enumerate(entities):
            # 获取实体基本信息
            entity_id = str(entity.id)
            entity_location = entity.get_location()
            entity_rotation = entity.get_rotation()
            
            # 创建基础实体信息
            entity_info = {
                "id": entity_id,
                "type": entity_type,
                "position": {
                    "x": float(entity_location.x),
                    "y": float(entity_location.y),
                    "z": float(entity_location.z)
                },
                "rotation": {
                    "x": float(entity_rotation.x),
                    "y": float(entity_rotation.y),
                    "z": float(entity_rotation.z),
                    "w": float(getattr(entity_rotation, 'w', 1.0))
                }
            }
            
            # 根据实体类型添加额外信息
            if entity_type in ['object', 'agent']:
                base_id = None
                if entity_type == 'object':
                    # 对于物品：匹配 _任意字符_数字 的模式
                    pattern = r'(_[^_]+_\d+)$'
                    match = re.search(pattern, entity_id)
                    if match:
                        base_id = entity_id[:match.start()]
                elif entity_type == 'agent':
                    # 使用agent_config模块提取基础ID
                    base_id = extract_base_agent_id(entity_id)
                    # # 获取人物特性
                    # agent_trait = get_agent_trait(base_id)
                    # if agent_trait:
                    #     entity_info['agent_trait'] = agent_trait
                
                if base_id:
                    entity_info['base_id'] = base_id

            
            # 添加所有者信息（如果提供）
            if owner:
                entity_info["owner"] = owner
            
            # 如果启用了自动检测资产类型
            if auto_detect_asset_type and entity_type == 'object':
                asset_type = get_asset_type_by_id(entity_id)
                entity_info['asset_type'] = asset_type

            if features_list:
                # 使用每个实体单独的特征
                entity_info["features"] = features_list[i]
            elif features:  # 支持features参数
                # 使用统一的特征
                entity_info["features"] = features

            # 对于objc添加AABB边界
            if entity_type == 'object':
                try:
                    aabb = entity.get_world_aabb()
                    aabb_min, aabb_max = fix_aabb_bounds(aabb)
                    entity_info["aabb_bounds"] = {
                        "min": {
                            "x": float(aabb_min.x),
                            "y": float(aabb_min.y),
                            "z": float(aabb_min.z)
                        },
                        "max": {
                            "x": float(aabb_max.x),
                            "y": float(aabb_max.y),
                            "z": float(aabb_max.z)
                        }
                    }
                except Exception as e:
                    print(f"[WARNING] 无法获取实体 {entity_id} 的AABB边界: {e}")
                    
            # 根据实体类型添加到对应的列表
            if entity_type == 'object':
                target_list = data.setdefault("objects", [])
            elif entity_type == 'agent':
                target_list = data.setdefault("agents", [])
            elif entity_type == 'camera':
                target_list = data.setdefault("cameras", [])
            else:
                raise ValueError(f"不支持的实体类型: {entity_type}")
            
            # 添加到目标列表
            target_list.append(entity_info)
            added_count += 1

        # 保存更新后的JSON文件
        with open(json_file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"[SUCCESS] 成功添加 {added_count} 个 {entity_type} 到JSON文件: {json_file_path}")
        return True
    
    except Exception as e:
        print(f"[ERROR] 添加物品到JSON文件时出错: {e}")
        return False

def create_scene_json_file(map_name, room_name, table_entity, save_dir):
    """
    创建场景JSON文件并初始化基本信息
    
    Args:
        map_name: 地图名称
        room_name: 房间名称
        table_entity: 桌子实体
        save_dir: 保存目录
    
    Returns:
        str: JSON文件路径
    """
    # 创建目录
    os.makedirs(save_dir, exist_ok=True)
    
    # JSON文件路径
    json_file_path = os.path.join(save_dir, "scene_data.json")
    
    # 获取桌子信息
    table_location = table_entity.get_location()
    table_rotation = table_entity.get_rotation()
    table_aabb = table_entity.get_world_aabb()
    table_min, table_max = fix_aabb_bounds(table_aabb)

    # 获取实体基本信息
    table_entity_id = str(table_entity.id)
    
    base_id = table_entity_id
    pattern = r'(_[^_]+_\d+)$'  # 匹配 _任意字符_数字 的模式
    match = re.search(pattern, table_entity_id)
    if match:
        base_id = table_entity_id[:match.start()]

    # 创建基础JSON结构
    scene_data = {
        "scene_info": {
            "map_name": map_name,
            "room_name": room_name,
            "table_id": table_entity_id,
            "base_id": base_id,
            "position": {
                "x": float(table_location.x),
                "y": float(table_location.y),
                "z": float(table_location.z)
            },
            "rotation": {
                "x": float(table_rotation.x),
                "y": float(table_rotation.y),
                "z": float(table_rotation.z),
                "w": float(getattr(table_rotation, 'w', 1.0))
            },
            "aabb_bounds": {
                "min": {
                    "x": float(table_min.x),
                    "y": float(table_min.y),
                    "z": float(table_min.z)
                },
                "max": {
                    "x": float(table_max.x),
                    "y": float(table_max.y),
                    "z": float(table_max.z)
                }
            }
        },
        "objects": [],
        "agents": [],
        "cameras": [],
        "timestamps": {
            "start_time": datetime.now().isoformat(),
            "end_time": None
        }
    }
    
    # 保存JSON文件
    with open(json_file_path, 'w', encoding='utf-8') as f:
        json.dump(scene_data, f, indent=2, ensure_ascii=False)
    
    print(f"[PROCESSING] 创建场景JSON文件: {json_file_path}")
    return json_file_path

# 全局变量，存储资产信息（只保留ID和owl类型的映射）
def load_asset_info(asset_json_path: str) -> Dict[str, str]:
    """
    加载资产信息JSON文件并构建简化的查找字典（只保留ID->owl映射）
    
    Args:
        asset_json_path: 资产信息JSON文件路径
    
    Returns:
        Dict[str, str]: 简化的资产信息字典 {asset_id: owl_type}
    """
    global ASSET_OWL_DICT
    
    try:
        with open(asset_json_path, 'r', encoding='utf-8') as f:
            asset_data = json.load(f)
        
        # 只提取需要的字段：ID -> owl类型
        ASSET_OWL_DICT = {}
        for asset_id, asset_info in asset_data.items():
            owl_type = asset_info.get('owl', asset_info.get('Type', 'unknown'))
            ASSET_OWL_DICT[asset_id] = owl_type
        
        print(f"[SUCCESS] 成功加载 {len(ASSET_OWL_DICT)} 个资产信息")
        return ASSET_OWL_DICT
    except Exception as e:
        print(f"[ERROR] 加载资产信息文件失败: {e}")
        return {}

def get_asset_type_by_id(entity_id: str) -> str:
    """
    根据实体ID直接获取资产类型（合并了提取基础ID和匹配的功能）
    
    Args:
        entity_id: 实体ID
    
    Returns:
        str: 资产类型，如果找不到返回 "unknown"
    """
    if not ASSET_OWL_DICT:
        return "unknown"
    
    # 第一步：提取基础ID（移除最后两个_的部分）
    base_id = entity_id
    pattern = r'(_[^_]+_\d+)$'  # 匹配 _任意字符_数字 的模式
    match = re.search(pattern, entity_id)
    if match:
        base_id = entity_id[:match.start()]
    
    # 第二步：直接匹配
    if base_id in ASSET_OWL_DICT:
        return ASSET_OWL_DICT[base_id]
    
    # 第三步：如果直接匹配失败，尝试部分匹配
    # 检查base_id是否包含任何已知的资产ID
    for asset_id, owl_type in ASSET_OWL_DICT.items():
        if asset_id in base_id:
            return owl_type
    
    # 第四步：如果部分匹配也失败，尝试前缀匹配
    for asset_id, owl_type in ASSET_OWL_DICT.items():
        if base_id.startswith(asset_id) or asset_id.startswith(base_id):
            return owl_type
    
    # 第五步：如果所有匹配都失败，返回unknown
    return "unknown"


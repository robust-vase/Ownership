
import re

# 获得从物品id中提取蓝图信息
def get_blueprint_from_entity_id(entity_id: str) -> str:
    """
    从实体ID中提取蓝图ID
    
    Args:
        entity_id: 实体ID字符串
        
    Returns:
        str: 提取的蓝图ID
    """
    # 匹配 _任意字符_数字 的模式
    pattern = r'(_[^_]+_\d+)$'
    match = re.search(pattern, entity_id)
    if match:
        return entity_id[:match.start()]
    return entity_id

# 根据类型文件筛选物品列表
def filter_objects_by_type(objects_list, type_file_path, print_info=False):
    """
    根据类型文件筛选物品列表
    
    Args:
        objects_list: 物品实体列表
        type_file_path: 包含类型ID的txt文件路径
    
    Returns:
        list: 属于指定类型的物品子列表
    """
    # 读取类型文件
    try:
        with open(type_file_path, 'r', encoding='utf-8') as f:
            type_ids = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"[ERROR] 类型文件 {type_file_path} 不存在")
        return []
    
    # 创建匹配的实体列表
    matched_objects = []
    
    for obj in objects_list:
        obj_id = obj.id
        
        # 移除后缀
        base_id = get_blueprint_from_entity_id(obj_id)
        
        # 检查基础ID是否在类型列表中
        if base_id in type_ids:
            matched_objects.append(obj)
            if print_info == True:
                print(f"[PROCESSING] 匹配成功: {obj_id} -> 基础ID: {base_id}")
        else:
            if print_info == True:
                print(f"[PROCESSING] 不匹配: {obj_id} -> 基础ID: {base_id}")
    
    print(f"\n[PROCESSING] 筛选结果: 共 {len(objects_list)} 个物品, 其中 {len(matched_objects)} 个匹配指定类型")
    return matched_objects


# 根据类型文件筛选物品信息列表（新格式）
def filter_objects_info_by_type(objects_info_list, type_file_path, print_info=False):
    """
    根据类型文件筛选物品信息列表（支持完整信息格式）
    
    新格式支持包含以下字段的字典：
    - id: 物品ID
    - type: 物品类型
    - location: 位置信息
    - rotation: 旋转信息
    - entity: 实体对象
    - direction: 方向信息（可选）
    - entity_min/entity_max: AABB边界（可选）
    
    Args:
        objects_info_list: 物品信息字典列表
        type_file_path: 包含类型ID的txt文件路径
        print_info: 是否打印详细信息
    
    Returns:
        list: 属于指定类型的物品信息子列表
    """
    # 读取类型文件
    try:
        with open(type_file_path, 'r', encoding='utf-8') as f:
            type_ids = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"[ERROR] 类型文件 {type_file_path} 不存在")
        return []
    
    # 创建匹配的物品信息列表
    matched_objects_info = []
    
    for obj_info in objects_info_list:
        # 获取物品ID
        obj_id = obj_info.get('id', '')
        
        if not obj_id:
            if print_info:
                print(f"[WARNING] 物品信息缺少ID字段，跳过")
            continue
        
        # 移除后缀，提取基础ID
        base_id = get_blueprint_from_entity_id(obj_id)
        
        # 检查基础ID是否在类型列表中
        if base_id in type_ids:
            matched_objects_info.append(obj_info)
            if print_info:
                obj_type = obj_info.get('type', 'Unknown')
                print(f"[PROCESSING] 匹配成功: {obj_id} -> 基础ID: {base_id}, 类型: {obj_type}")
        else:
            if print_info:
                obj_type = obj_info.get('type', 'Unknown')
                print(f"[PROCESSING] 不匹配: {obj_id} -> 基础ID: {base_id}, 类型: {obj_type}")
    
    if print_info:
        print(f"\n[PROCESSING] 筛选结果: 共 {len(objects_info_list)} 个物品信息, 其中 {len(matched_objects_info)} 个匹配指定类型")
    
    return matched_objects_info

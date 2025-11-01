"""
物品配置和相关工具函数
"""
import os
from typing import List, Dict, Any
import tongsim as ts

def read_item_file(filename: str) -> List[str]:
    """
    读取物品文件列表
    
    Args:
        filename: 文件路径
        
    Returns:
        List[str]: 物品列表
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"[ERROR] 文件 {filename} 不存在")
        return []

# 非重复物品类型列表（这些类型的物品每个只能出现一次）
NON_REPEATING_ITEM_TYPES = ['computer', 'glasses', 'wine']

# 坐下状态物品权重加成（这些物品在人物坐下时更容易被选中）
SITTING_ITEM_WEIGHT_BOOST = {
    'computer': 3.0,
    'opened_magazine': 3.0,
    'opened_book': 3.0
}

# 可重复使用的蓝图（这些蓝图可以多次生成）
REPEATABLE_BLUEPRINTS = [
    'BP_Phone',
    'BP_Plate',
    'BP_Decoration_Book_Magazine',
    'BP_Magazine_01'
]

# 物品蓝图定义
ITEM_BLUEPRINTS = {
    'smallcup': ['BP_Cup_Kitchen_003', 'BP_Flex_Cup_Kitchen_2'],
    'bigcup': ["BP_Cup_Coffee_01", "BP_Cup_Mug", 'BP_Cup_Mug_White'],
    'pinkcup': ['BP_Cup_Mug_Red', 'BP_Flex_Cup_Kitchen'],
    'winecup': ["BP_Cup_04", "BP_Cup_05"],
    'book': read_item_file("./ownership/object/mybook.txt"),
    'opened_magazine': ["BP_Decoration_Book_Magazine"],
    'opened_book': ["BP_Magazine_01"],
    'computer': ["BP_Laptop_01"],
    'pen': read_item_file("./ownership/object/mypen.txt"),
    'snack': read_item_file("./ownership/object/snack.txt"),
    'platefood': read_item_file("./ownership/object/platefood.txt"),
    'drink': read_item_file("./ownership/object/mydrink.txt"),
    'milk': read_item_file("./ownership/object/mymilk.txt"),
    'wine': read_item_file("./ownership/object/mywine.txt"),
    'toy': read_item_file("./ownership/object/mytoy.txt"),
    'doll': ["BP_Doll_Sofia", "BP_Doll_ncteague", 'BP_Toy_Pig', 'BP_Toy_Bear_01'],
    'boytoy': read_item_file("./ownership/object/boytoy.txt"),
    'phone': ["BP_Phone"],
    'glasses': ["BP_Decor_Eyeglasses01Frame01"],
    'mousepad': ["BP_Mouse_01"],
    'plate': ["BP_Plate", 'BP_Plate_01', "BP_Plate_02_TL"]
}

# 物品属性表
ITEM_PROPERTIES = {
    'smallcup': {
        'zone_types': ['frequent', 'infrequent'],
        'rotation_z': 270,
        'rotation_x': 0,
        'rotation_y': 0,
        'scale': ts.Vector3(0.8, 0.8, 0.8),
        'safe_margin': 3.0,
        'min_distance': 0.0,
        'max_distance': 30.0  # 杯子需要放在比较近的地方
    },
    'bigcup': {
        'zone_types': ['frequent', 'infrequent'],
        'rotation_z': 270,
        'rotation_x': 0,
        'rotation_y': 0,
        'scale': ts.Vector3(0.9, 0.9, 0.9),
        'safe_margin': 3.0,
        'min_distance': 0.0,
        'max_distance': 30.0  # 杯子需要放在比较近的地方
    },
    'pinkcup': {
        'zone_types': ['frequent', 'infrequent'],
        'rotation_z': 270,
        'rotation_x': 0,
        'rotation_y': 0,
        'scale': ts.Vector3(0.7, 0.7, 0.7),
        'safe_margin': 3.0,
        'min_distance': 0.0,
        'max_distance': 30.0  # 杯子需要放在比较近的地方
    },
    'winecup': {
        'zone_types': ['frequent', 'infrequent'],
        'rotation_z': 360,
        'rotation_x': 0,
        'rotation_y': 0,
        'scale': ts.Vector3(0.9, 0.9, 0.9),
        'safe_margin': 3.0,
        'min_distance': 0.0,
        'max_distance': 30.0  # 杯子需要放在比较近的地方
    },
    'book': {
        'zone_types': ['main', 'frequent', 'infrequent'],
        'rotation_z': -90,
        'rotation_x': 90,
        'rotation_y': 0,
        'scale': ts.Vector3(0.8, 0.8, 0.8),
        'safe_margin': 7.0,
        'min_distance': 0.0,
        'max_distance': 40.0  # 书可以放在较远的地方
    },
    'opened_magazine': {
        'zone_types': ['main'],
        'rotation_z': 180,
        'rotation_x': 0,
        'rotation_y': 0,
        'scale': ts.Vector3(0.8, 0.8, 0.8),
        'safe_margin': 5.0,
        'min_distance': 0.0,
        'max_distance': 30.0  # 书可以放在较远的地方
    },
    'opened_book': {
        'zone_types': ['main'],
        'rotation_z': 180,
        'rotation_x': 0,
        'rotation_y': 0,
        'scale': ts.Vector3(0.8, 0.8, 0.8),
        'safe_margin': 5.0,
        'min_distance': 0.0,
        'max_distance': 30.0  # 书可以放在较远的地方
    },
    'computer': {
        'zone_types': ['main'],
        'rotation_z': -90,
        'rotation_x': 0,
        'rotation_y': 0,
        'scale': ts.Vector3(0.7, 0.7, 0.7),
        'safe_margin': 8.0,
        'min_distance': 10.0,  # 电脑需要留出足够的空间
        'max_distance': 50.0  # 电脑可以放在较远的地方
    },
    'pen': {
        'zone_types': ['main', 'frequent', 'infrequent'],
        'rotation_z': 360,
        'rotation_x': 90,
        'rotation_y': 0,
        'scale': ts.Vector3(1, 1, 1),
        'safe_margin': 2.0,
        'min_distance': 0.0,
        'max_distance': 30.0
    },
    'snack': {
        'zone_types': ['frequent', 'infrequent'],
        'rotation_z': 360,
        'rotation_x': 0,
        'rotation_y': 0,
        'scale': ts.Vector3(0.6, 0.6, 0.6),
        'safe_margin': 4.0,
        'min_distance': 0.0,
        'max_distance': 40.0  # 食物需要放在比较近的地方
    },
    'platefood': {
        'zone_types': ['frequent', 'infrequent'],
        'rotation_z': 360,
        'rotation_x': 0,
        'rotation_y': 0,
        'scale': ts.Vector3(0.6, 0.6, 0.6),
        'safe_margin': 4.0,
        'min_distance': 0.0,
        'max_distance': 40.0  # 食物需要放在比较近的地方
    },
    'drink': {
        'zone_types': ['frequent', 'infrequent'],
        'rotation_z': 360,
        'rotation_x': 0,
        'rotation_y': 0,
        'scale': ts.Vector3(0.15, 0.15, 0.15),
        'safe_margin': 5.0,
        'min_distance': 0.0,
        'max_distance': 30.0  # 饮品需要放在比较近的地方
    },
    'milk': {
        'zone_types': ['frequent', 'infrequent'],
        'rotation_z': 360,
        'rotation_x': 0,
        'rotation_y': 0,
        'scale': ts.Vector3(0.8, 0.8, 0.8),
        'safe_margin': 5.0,
        'min_distance': 10.0,
        'max_distance': 50.0  # 牛奶需要放在比较近的地方
    },
    'wine': {
        'zone_types': ['main'],
        'rotation_z': 360,
        'rotation_x': 0,
        'rotation_y': 0,
        'scale': ts.Vector3(1, 1, 1),
        'safe_margin': 0.0,
        'min_distance': 40.0,  # 酒瓶需要留出足够的空间
        'max_distance': 100.0  # 酒瓶可以放在较远的地方
    },
    'toy': {
        'zone_types': ['main', 'frequent', 'infrequent'],
        'rotation_z': 360,
        'rotation_x': 0,
        'rotation_y': 0,
        'scale': ts.Vector3(0.75, 0.75, 0.75),
        'safe_margin': 3.0,
        'min_distance': 0.0,
        'max_distance': 30.0
    },
    'doll': {
        'zone_types': ['main', 'frequent', 'infrequent'],
        'rotation_z': 360,
        'rotation_x': 0,
        'rotation_y': 0,
        'scale': ts.Vector3(0.75, 0.75, 0.75),
        'safe_margin': 3.0,
        'min_distance': 0.0,
        'max_distance': 30.0
    },
    'boytoy': {
        'zone_types': ['main', 'frequent', 'infrequent'],
        'rotation_z': 360,
        'rotation_x': 0,
        'rotation_y': 0,
        'scale': ts.Vector3(0.75, 0.75, 0.75),
        'safe_margin': 3.0,
        'min_distance': 0.0,
        'max_distance': 30.0
    },
    'phone': {
        'zone_types': ['frequent', 'infrequent', 'temporary'],
        'rotation_z': 90,
        'rotation_x': 90,
        'rotation_y': -90,
        'scale': ts.Vector3(0.6, 0.6, 0.6),
        'safe_margin': 3.0,
        'min_distance': 0.0,
        'max_distance': 30.0
    },
    'glasses': {
        'zone_types': ['frequent', 'infrequent'],
        'rotation_z': 90,
        'rotation_x': 0,
        'rotation_y': 0,
        'scale': ts.Vector3(0.65, 0.65, 0.65),
        'safe_margin': 5.0,
        'min_distance': 0.0,
        'max_distance': 30.0
    },
    'mousepad': {
        'zone_types': ['frequent', 'infrequent'],
        'rotation_z': 90,
        'rotation_x': 0,
        'rotation_y': 0,
        'scale': ts.Vector3(1, 1, 1),
        'safe_margin': 5.0,
        'min_distance': 0.0,
        'max_distance': 30.0
    },
}

# 人物与物品的对应关系表
AGENT_ITEM_MAPPING = {
    'girl': ['smallcup', 'snack', 'book', 'toy', 'drink', 'doll', 'pinkcup'],
    'boy': ['smallcup', 'snack', 'book', 'toy', 'drink', 'boytoy'],
    'woman': ['bigcup', 'snack', 'computer', 'phone', 'glasses', 'drink', 'opened_magazine', 'pinkcup'],
    'man': ['bigcup', 'snack', 'computer', 'phone', 'glasses', 'drink', 'wine', 'opened_magazine'],
    'grandpa': ['bigcup', 'book', 'glasses', 'wine', 'opened_magazine'],
    'unknown': ['book']
}

# 通用物品（所有人都可能拥有）
COMMON_ITEMS = ['platefood', 'pen', 'milk', 'opened_book']

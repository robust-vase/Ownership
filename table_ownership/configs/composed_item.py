"""
物品连锁生成配置
定义物品之间的关联关系和生成规则
"""

# 连锁物品生成规则
ITEM_CHAIN_RULES = {
    # 书本连锁规则：生成笔
    'book': [
        {
            'chain_item': 'pen',
            'probability': 0.6,
            'direction': 'right',  # 相对于人的右边
            'max_range': 2  # 最大范围1层
        }
    ],
    
    'opened_magazine': [
        {
            'chain_item': 'pen',
            'probability': 0.6,
            'direction': 'right',
            'max_range': 2
        }
    ],

    'opened_book': [
        {
            'chain_item': 'pen',
            'probability': 0.6,
            'direction': 'right',
            'max_range': 2
        }
    ],
    
    # 饮料连锁规则：生成杯子
    'milk': [
        {
            'chain_item': 'smallcup',
            'probability': 0.6,
            'direction': 'around',  # 四周
            'max_range': 2  # 最大范围2层
        },
        {
            'chain_item': 'bigcup',
            'probability': 0.6,
            'direction': 'around',
            'max_range': 2
        },
        {
            'chain_item': 'platefood',  # 连锁食物
            'probability': 0.5,
            'direction': 'around',
            'max_range': 2
        }
    ],
    
    'drink': [
        {
            'chain_item': 'snack',  # 连锁零食
            'probability': 0.6,
            'direction': 'around',
            'max_range': 2
        }
    ],
    
    'wine': [
        {
            'chain_item': 'winecup',  # 随机选择酒杯
            'probability': 0.4,
            'direction': 'around',
            'max_range': 1
        }
    ],
    
    # 零食连锁规则：生成饮料
    'snack': [
        {
            'chain_item': 'drink',
            'probability': 0.6,
            'direction': 'around',
            'max_range': 2
        },
        {
            'chain_item': 'milk',
            'probability': 0.4,
            'direction': 'around',
            'max_range': 2
        }
    ],
    
    # 食物连锁规则：生成牛奶
    'platefood': [
        {
            'chain_item': 'milk',
            'probability': 0.5,
            'direction': 'around',
            'max_range': 2
        }
    ],
    
    # 电脑连锁规则：生成鼠标、杯子、手机、眼镜
    'computer': [
        {
            'chain_item': 'mousepad',
            'probability': 0.8,
            'direction': 'right',  # 鼠标在右边
            'max_range': 1
        },
        {
            'chain_item': 'bigcup',  # 大杯子
            'probability': 0.6,
            'direction': 'around',
            'max_range': 2
        },
        {
            'chain_item': 'phone',
            'probability': 0.8,
            'direction': 'around',  # 手机在四周
            'max_range': 2
        },
        {
            'chain_item': 'glasses',  # 眼镜
            'probability': 0.5,
            'direction': 'around',  # 眼镜在四周
            'max_range': 2
        }
    ]
}

# 方向映射表：将相对于人的方向转换为网格坐标偏移
# 根据人在桌子的哪一侧，计算实际的网格偏移
def get_direction_mapping(agent_side):
    """
    根据人物站位获取方向映射
    
    Args:
        agent_side: 人物相对于桌子的位置 ('front', 'back', 'left', 'right')
    
    Returns:
        dict: 方向映射字典 {'right': (dx, dy), 'left': (dx, dy), ...}
    """
    # 坐标系：X轴左正右负，Y轴前正后负
    
    if agent_side == 'front':
        # 人在前面（Y较大）
        # 人的右边 = 桌子的左边（X更小）
        # 人的左边 = 桌子的右边（X更大）
        # 人的前方 = 桌子的后面（Y更小）
        # 人的后方 = 桌子的前面（Y更大）
        return {
            'right': (-1, 0),   # 人的右边 = X减小
            'left': (1, 0),     # 人的左边 = X增大
            'front': (0, -1),   # 人的前方 = Y减小（朝向桌子）
            'back': (0, 1)      # 人的后方 = Y增大（远离桌子）
        }
    
    elif agent_side == 'back':
        # 人在后面（Y较小）
        # 人的右边 = 桌子的右边（X更大）
        # 人的左边 = 桌子的左边（X更小）
        # 人的前方 = 桌子的前面（Y更大）
        # 人的后方 = 桌子的后面（Y更小）
        return {
            'right': (1, 0),    # 人的右边 = X增大
            'left': (-1, 0),    # 人的左边 = X减小
            'front': (0, 1),    # 人的前方 = Y增大（朝向桌子）
            'back': (0, -1)     # 人的后方 = Y减小（远离桌子）
        }
    
    elif agent_side == 'left':
        # 人在左侧（X较大）
        # 人的右边 = 桌子的后面（Y更小）
        # 人的左边 = 桌子的前面（Y更大）
        # 人的前方 = 桌子的右边（X更小）
        # 人的后方 = 桌子的左边（X更大）
        return {
            'right': (0, -1),   # 人的右边 = Y减小
            'left': (0, 1),     # 人的左边 = Y增大
            'front': (-1, 0),   # 人的前方 = X减小（朝向桌子）
            'back': (1, 0)      # 人的后方 = X增大（远离桌子）
        }
    
    elif agent_side == 'right':
        # 人在右侧（X较小）
        # 人的右边 = 桌子的前面（Y更大）
        # 人的左边 = 桌子的后面（Y更小）
        # 人的前方 = 桌子的左边（X更大）
        # 人的后方 = 桌子的右边（X更小）
        return {
            'right': (0, 1),    # 人的右边 = Y增大
            'left': (0, -1),    # 人的左边 = Y减小
            'front': (1, 0),    # 人的前方 = X增大（朝向桌子）
            'back': (-1, 0)     # 人的后方 = X减小（远离桌子）
        }
    
    else:
        # 默认映射
        return {
            'right': (-1, 0),
            'left': (1, 0),
            'front': (0, -1),
            'back': (0, 1)
        }


def get_chain_grids(current_grid, direction, max_range, agent_side, all_grids):
    """
    获取连锁物品可以放置的网格列表
    
    新规则：在指定方向上，允许上下浮动一个格子，搜索多层范围
    例如：current_grid=(5,0), direction='right'(对应桌子back，即-Y), max_range=2
    结果：[(5,-1), (4,-1), (6,-1), (5,-2), (4,-2), (6,-2)]
    
    Args:
        current_grid: 当前物品所在网格 {'grid_x': x, 'grid_y': y, ...}
        direction: 相对于人的方向 ('right', 'left', 'front', 'back', 'around')
        max_range: 最大范围（在指定方向上的层数）
        agent_side: 人物站位 ('front', 'back', 'left', 'right')
        all_grids: 所有可用网格列表
    
    Returns:
        list: 可放置的网格列表
    """
    current_grid_x = current_grid['grid_x']
    current_grid_y = current_grid['grid_y']
    
    # 获取方向映射
    direction_map = get_direction_mapping(agent_side)
    
    candidate_grids = []
    
    if direction == 'around':
        # 四周搜索：使用曼哈顿距离
        for grid in all_grids:
            grid_x = grid['grid_x']
            grid_y = grid['grid_y']
            
            # 计算曼哈顿距离
            manhattan_dist = abs(grid_x - current_grid_x) + abs(grid_y - current_grid_y)
            
            if 1 <= manhattan_dist <= max_range:
                candidate_grids.append(grid)
    
    else:
        # 特定方向搜索
        if direction not in direction_map:
            return []
        
        dx, dy = direction_map[direction]
        
        # 在指定方向上，逐层搜索（每层允许上下浮动1格）
        for layer in range(1, max_range + 1):
            # 主方向上的偏移
            main_x = current_grid_x + dx * layer
            main_y = current_grid_y + dy * layer
            
            # 确定垂直方向（上下浮动）
            if dx != 0:
                # 主方向是X轴，垂直方向是Y轴
                perpendicular_axis = 'y'
                for float_offset in [-1, 0, 1]:
                    target_x = main_x
                    target_y = main_y + float_offset
                    
                    # 查找匹配的网格
                    for grid in all_grids:
                        if grid['grid_x'] == target_x and grid['grid_y'] == target_y:
                            candidate_grids.append(grid)
                            break
            else:
                # 主方向是Y轴，垂直方向是X轴
                perpendicular_axis = 'x'
                for float_offset in [-1, 0, 1]:
                    target_x = main_x + float_offset
                    target_y = main_y
                    
                    # 查找匹配的网格
                    for grid in all_grids:
                        if grid['grid_x'] == target_x and grid['grid_y'] == target_y:
                            candidate_grids.append(grid)
                            break
    
    return candidate_grids

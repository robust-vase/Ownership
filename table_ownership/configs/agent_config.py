"""
人物配置和相关工具函数
"""
import re
from typing import Optional

# 人物蓝图映射表
AGENT_BLUEPRINT_MAPPING = {
    'girl': ["SDBP_Aich_AIBabyV7_Shoes", "SDBP_Aich_AIBaby_Lele_Shoes"],
    'boy': ["SDBP_Aich_AIBaby_Tiantian_90"],
    'woman': ["SDBP_Aich_Liyuxia"],
    'grandpa': ["SDBP_Aich_Yeye"],
    'man': ["SDBP_Aich_Zhanghaoran"]
}

# 创建反向映射：从蓝图到特性
BLUEPRINT_TO_TRAIT = {
    blueprint: trait 
    for trait, blueprints in AGENT_BLUEPRINT_MAPPING.items() 
    for blueprint in blueprints
}

def extract_base_agent_id(entity_id: str) -> str:
    """
    从完整的实体ID中提取基础人物ID
    
    Args:
        entity_id: 完整的实体ID
        
    Returns:
        str: 基础人物ID（去除唯一标识部分后的ID）
    """
    pattern = r'(_\d+_[A-F0-9]{32,})$'
    match = re.search(pattern, entity_id)
    if match:
        return entity_id[:match.start()]
    return entity_id

def get_agent_trait(agent_id: str) -> Optional[str]:
    """
    根据人物ID获取其特性（girl, boy, woman等）
    
    Args:
        agent_id: 人物ID或蓝图名
        
    Returns:
        Optional[str]: 人物特性，如果未找到则返回None
    """
    # 先尝试直接从蓝图映射中获取
    if agent_id in BLUEPRINT_TO_TRAIT:
        return BLUEPRINT_TO_TRAIT[agent_id]
    
    # 提取基础ID后再次尝试
    base_id = extract_base_agent_id(agent_id)
    return BLUEPRINT_TO_TRAIT.get(base_id)

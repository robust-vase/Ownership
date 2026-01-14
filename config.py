"""
Configuration Module
====================
Centralized configuration for the ownership annotation tool.
"""
from pathlib import Path
import os
import secrets

# ==================== Paths ====================
# SCENES_ROOT_PATH = os.getenv('SCENES_ROOT', r"C:\Users\Vase\Desktop\result\swap")
# SCENES_ROOT = Path(SCENES_ROOT_PATH)

# Github 仓库
BASE_DIR = Path(__file__).resolve().parent
SCENES_ROOT = BASE_DIR / 'swap'

# ==================== Server ====================
SERVER_HOST = '0.0.0.0'
SERVER_PORT = int(os.getenv('PORT', 5001))
DEBUG_MODE = os.getenv('DEBUG', 'true').lower() == 'true'

# ==================== Security ====================
# CRITICAL: Set this in environment variable for production!
# Generate a secure key: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY = os.getenv('SECRET_KEY', None)
if SECRET_KEY is None:
    # Auto-generate for development (will change on restart - sessions won't persist)
    SECRET_KEY = secrets.token_hex(32)
    print("[WARNING] Using auto-generated SECRET_KEY. Set SECRET_KEY env var for production!")

# ==================== Scene Processing ====================
SCENE_DATA_FILENAME = "scene_data.json"
IMAGE_WIDTH = 4096
IMAGE_HEIGHT = 4096
FOV = 90.0

# ==================== Filtering ====================
EXCLUDED_OWNERS = {'room', 'public'}
EXCLUDED_TYPES = {'wall', 'window'}

# ==================== Visual Mapping (Anti-Bias) ====================
# Map specific internal types to neutral display labels to avoid semantic priming.
DISPLAY_CATEGORY_MAPPING = {
    # Toys
    'toy': 'Toy',
    'boytoy': 'Toy',
    'doll': 'Toy',
    
    # Cups
    'bigcup': 'Cup',
    'pinkcup': 'Cup',
    'winecup': 'Cup',
    
    # Food
    'snack': 'Food',
    'platefood': 'Food',
    
    # Drinks
    'drink': 'Drink',
    'milk': 'Drink',
    'wine': 'Drink',
    'juice': 'Drink',
    
    # Bags
    'redbag': 'Bag',
    'schoolbag': 'Bag',
    
    # Optional: Normalize others to Title Case if needed, or leave as fallback
    'book': 'Book',
    'opened_book': 'Opened Book',
    'opened_magazine': 'Opened Book',
    'newspaper': 'Newspaper',

    'computer': 'Computer',
    'pen': 'Pen',
    'phone': 'Phone',
    'radio': 'Radio',
    'mousepad': 'Mouse',

    'mirror': 'Mirror',
    'perfume': 'Perfume',
    'comb': 'Comb',
    'lipstick': 'Lipstick',
    'glasses': 'Glasses',
    'cap': 'Cap',

    'plate': 'Plate',
    
}


# Agent Blueprint to Role Mapping
AGENT_BLUEPRINT_MAPPING = {
    'girl': ["SDBP_Aich_AIBabyV7_Shoes", "SDBP_Aich_AIBaby_Lele_Shoes", "BP_Aich_AIBabyV7", "BP_Aich_AIBaby_Lele"],
    'boy': ["SDBP_Aich_AIBaby_Tiantian_90", "SDBP_Aich_Liuhaoxuan", "SDBP_Aich_Liuhaoyu", "SDBP_Aich_Weiguo",
            "BP_Aich_Tiantian", "BP_Aich_Liuhaoxuan", "BP_Aich_Liuhaoyu", "BP_Aich_Weiguo"],
    'woman': ["SDBP_Aich_Liyuxia", "SDBP_Aich_Liqiuyue", "SDBP_Aich_Jiangshuyan", "BP_Aich_Liyuxia", "BP_Aich_Liqiuyue", "BP_Aich_Jiangshuyan"],
    'grandpa': ["SDBP_Aich_Yeye", "BP_Aich_Yeye"],
    'grandma': ["SDBP_Aich_Nainai", "BP_Aich_Nainai"],
    'boy_teenager': ["SDBP_Aich_Yanzihao", "SDBP_Aich_Zhaoyuhang", "BP_Aich_Yanzihao", "BP_Aich_Zhaoyuhang"],
    'girl_teenager': ["SDBP_Aich_Yanzihan", "BP_Aich_Yanzihan"],
    'man': ["SDBP_Aich_Zhanghaoran", "SDBP_Aich_Shenxin", "BP_Aich_Zhanghaoran", "BP_Aich_Shenxin"],
}

# Fixed Color Palette by Gender/Role
# ROLE_COLORS = {
#     'girl': '#FF69B4',          # HotPink
#     'girl_teenager': '#FF1493', # DeepPink
#     'woman': '#DA70D6',         # Orchid
#     'grandma': '#8B008B',       # DarkMagenta
#     'boy': '#00BFFF',           # DeepSkyBlue
#     'boy_teenager': '#4682B4',  # SteelBlue
#     'man': '#0000CD',           # MediumBlue
#     'grandpa': '#008080',       # Teal
# }
ROLE_COLORS = {
    'girl': '#000000',
    'girl_teenager': '#000000',
    'woman': '#000000',
    'grandma': '#000000',
    'boy': '#000000',
    'boy_teenager': '#000000',
    'man': '#000000',
    'grandpa': '#000000',
}

# ==================== Scene Scanning ====================
def scan_scenes(base_path):
    """
    Detect scenes: base_path can be a single scene or contain multiple scenes.
    
    Returns:
        List of {'name': str, 'path': Path}
    """
    base_path = Path(base_path)
    if not base_path.exists():
        return []
    
    if (base_path / SCENE_DATA_FILENAME).exists():
        return [{'name': base_path.name, 'path': base_path}]
    
    scenes = []
    for item in sorted(base_path.iterdir()):
        if item.is_dir() and (item / SCENE_DATA_FILENAME).exists():
            scenes.append({'name': item.name, 'path': item})
    
    return scenes

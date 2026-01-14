"""
Ownership Manager
=================
Participant data management with file locking for concurrent access.
Safe for multi-user web deployment.
"""
import json
import os
import uuid
import random
import fcntl  # Unix file locking (use portalocker on Windows if needed)
import threading
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
import config

DATA_ROOT = Path("participants_data")
DATA_ROOT.mkdir(exist_ok=True)
BLOCKED_FILE = DATA_ROOT / "blocked_users.json"

# Thread lock for additional safety
_file_locks = {}
_lock_mutex = threading.Lock()


def _get_file_lock(file_path):
    """Get or create a threading lock for a specific file."""
    with _lock_mutex:
        if file_path not in _file_locks:
            _file_locks[file_path] = threading.Lock()
        return _file_locks[file_path]


@contextmanager
def safe_file_access(file_path, mode='r'):
    """
    Context manager for safe concurrent file access.
    Uses both threading lock and file system lock.
    
    Usage:
        with safe_file_access(path, 'r+') as f:
            data = json.load(f)
            # modify data
            f.seek(0)
            json.dump(data, f)
            f.truncate()
    """
    thread_lock = _get_file_lock(str(file_path))
    
    with thread_lock:
        # Ensure file exists for reading modes
        if 'r' in mode and not Path(file_path).exists():
            yield None
            return
            
        with open(file_path, mode, encoding='utf-8') as f:
            try:
                # Try to use fcntl (Unix)
                if 'w' in mode or '+' in mode:
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                else:
                    fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                yield f
            except (ImportError, AttributeError, OSError):
                # fcntl not available (Windows) - rely on thread lock only
                yield f
            finally:
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                except:
                    pass


def get_blocked_list():
    """Thread-safe blocked list retrieval."""
    if not BLOCKED_FILE.exists():
        return []
    with safe_file_access(BLOCKED_FILE, 'r') as f:
        if f:
            return json.load(f)
    return []


def block_user(ip_address):
    """Thread-safe IP blocking."""
    thread_lock = _get_file_lock(str(BLOCKED_FILE))
    
    with thread_lock:
        blocked = []
        if BLOCKED_FILE.exists():
            with open(BLOCKED_FILE, 'r', encoding='utf-8') as f:
                blocked = json.load(f)
        
        if ip_address not in blocked:
            blocked.append(ip_address)
            with open(BLOCKED_FILE, 'w', encoding='utf-8') as f:
                json.dump(blocked, f, indent=2)


def is_blocked(ip_address):
    return ip_address in get_blocked_list()

def init_participant_file(demographics, all_scene_names):
    """
    初始化用户文件：
    1. 存入人口统计学信息
    2. 生成随机的实验场景顺序
    """
    user_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:6]}"
    
    # 随机打乱场景顺序，保证每个人做的顺序不一样
    random.shuffle(all_scene_names)
    
    data = {
        "user_id": user_id,
        "start_time": datetime.now().isoformat(),
        "demographics": demographics,
        "scene_order": all_scene_names, # 预先决定好的顺序
        "completed_scenes": [],         # 已经做完的场景名
        "experiments": []               # 具体数据
    }
    
    file_path = DATA_ROOT / f"{user_id}.json"
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    return user_id

def get_next_scene(user_id):
    """
    获取用户的下一个场景 (线程安全)。
    返回: (scene_name, current_index, total_count)
    如果全部做完，返回 (None, -1, total)
    """
    file_path = DATA_ROOT / f"{user_id}.json"
    
    with safe_file_access(file_path, 'r') as f:
        if not f:
            return None, 0, 0
        data = json.load(f)
    
    order = data['scene_order']
    completed = set(data['completed_scenes'])
    
    total = len(order)
    current_idx = len(completed) + 1
    
    # 按顺序找第一个没做过的
    for scene in order:
        if scene not in completed:
            return scene, current_idx, total
            
    return None, total, total # 全部完成


def save_participant_results(user_id, scene_name, items_data, duration_ms=None):
    """线程安全的结果保存。"""
    file_path = DATA_ROOT / f"{user_id}.json"
    thread_lock = _get_file_lock(str(file_path))
    
    with thread_lock:
        # Read
        with open(file_path, 'r', encoding='utf-8') as f:
            user_data = json.load(f)
        
        # 记录数据
        formatted_results = []
        for item in items_data:
            record = {
                "object_id": item.get('object_id'),
                "agent_left_id": item.get('agent_a_id'),
                "agent_right_id": item.get('agent_b_id'),
                "slider_value": item.get('slider_value')
            }
            formatted_results.append(record)
        
        # 移除旧数据（如果重复提交）
        user_data["experiments"] = [exp for exp in user_data["experiments"] if exp["scene"] != scene_name]
        
        new_entry = {
            "scene": scene_name,
            "save_timestamp": datetime.now().isoformat(),
            "duration_ms": duration_ms,
            "results": formatted_results
        }
        user_data["experiments"].append(new_entry)
        
        # 标记该场景为已完成
        if scene_name not in user_data["completed_scenes"]:
            user_data["completed_scenes"].append(scene_name)
        
        # Write
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(user_data, f, indent=2, ensure_ascii=False)
        
    return True
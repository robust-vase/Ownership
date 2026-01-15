"""
Ownership Manager
=================
Participant data management with file locking for concurrent access.
Safe for multi-user web deployment on both Windows and Unix.
"""
import json
import os
import sys
import uuid
import random
import threading
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager


# Cross-platform file locking
if sys.platform == 'win32':
    import msvcrt
    def _lock_file(f, exclusive=True):
        """Windows file locking using msvcrt."""
        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK if exclusive else msvcrt.LK_LOCK, 1)
    def _unlock_file(f):
        """Windows file unlocking."""
        try:
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        except:
            pass
else:
    import fcntl
    def _lock_file(f, exclusive=True):
        """Unix file locking using fcntl."""
        fcntl.flock(f.fileno(), fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
    def _unlock_file(f):
        """Unix file unlocking."""
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)

# Import config from parent directory
import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).parent.parent))
import config

DATA_ROOT = Path(__file__).parent.parent / "participants_data"
DATA_ROOT.mkdir(exist_ok=True)
BLOCKED_FILE = DATA_ROOT / "blocked_users.json"
GLOBAL_STATE_FILE = DATA_ROOT / "global_pool_state.json"

POOL_STATUS_FILE = DATA_ROOT / "pool_status.json"

# ==================== Admin/Stats Functions ====================

def get_admin_stats():
    """
    获取管理员仪表板所需的所有统计数据。
    Returns: (pool_status, participants_summary, config_info)
    """
    # 1. Pool status
    pool_status = _get_pool_status()
    
    # 2. Participants summary
    participants = []
    for user_file in sorted(DATA_ROOT.glob("*.json"), reverse=True):
        if user_file.name in ["blocked_users.json", "global_pool_state.json", "pool_status.json"]:
            continue
        try:
            with open(user_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Determine status
            pool = data.get('assigned_pool')
            completed_count = len(data.get('completed_scenes', []))
            total_count = len(data.get('scene_order', []))
            is_completed = data.get('is_fully_completed', False)
            
            if pool is None:
                status = "Tutorial"
            elif is_completed:
                status = "Completed"
            elif completed_count > 0:
                status = "In-Progress"
            else:
                status = "Abandoned"
            
            participants.append({
                "user_id": data.get('user_id', user_file.stem),
                "pool": pool or "-",
                "completed": completed_count,
                "total": total_count,
                "status": status,
                "start_time": data.get('start_time', 'N/A')[:16].replace('T', ' '),
                "demographics": data.get('demographics', {})
            })
        except Exception as e:
            print(f"Error reading {user_file}: {e}")
            continue
    
    # 3. Config info
    scenes = config.scan_scenes(config.SCENES_ROOT)
    config_info = {
        "scenes_root": str(config.SCENES_ROOT),
        "total_scenes": len(scenes),
        "scenes_per_pool": len(scenes) // 6 if scenes else 20,
        "target_per_pool": 10  # 你可以在 config.py 中设置
    }
    
    return pool_status, participants[:50], config_info  # 最多返回50个最近的用户


def reset_pool_status():
    """重置所有池子的计数（管理员用）"""
    initial_status = {str(i): {"started": 0, "completed": 0} for i in range(1, 7)}
    with open(POOL_STATUS_FILE, 'w', encoding='utf-8') as f:
        json.dump(initial_status, f, indent=2)
    return initial_status

# ==================== Pool Status Functions ====================

def _get_pool_status():
    """读取池子状态，如果不存在则初始化 (1-6号池子)"""
    if not POOL_STATUS_FILE.exists():
        # 初始化结构：每个池子都有 started 和 completed 计数
        initial_status = {str(i): {"started": 0, "completed": 0} for i in range(1, 7)}
        with safe_file_access(POOL_STATUS_FILE, 'w') as f:
            json.dump(initial_status, f, indent=2)
        return initial_status
        
    with safe_file_access(POOL_STATUS_FILE, 'r') as f:
        return json.load(f)

def _update_pool_status(pool_id, action="started"):
    """
    更新池子计数。
    action: "started" (分配时+1) 或 "completed" (全部做完时+1)
    """
    with safe_file_access(POOL_STATUS_FILE, 'r+') as f:
        data = json.load(f)
        pool_key = str(pool_id)
        
        if pool_key in data:
            data[pool_key][action] += 1
            
        f.seek(0)
        json.dump(data, f, indent=2)
        f.truncate()

def assign_pool_strategy(user_id):
    """
    [核心逻辑] 分配策略：优先分配‘完成数’最少的池子。
    如果完成数一样，优先分配‘开始数’最少的（避免并发时拥挤）。
    """
    # 1. 获取当前状态
    status = _get_pool_status() # {"1": {"started": 5, "completed": 3}, ...}
    
    # 2. 转换为列表并排序
    # 排序优先级：
    #   1. completed (升序): 优先填补还没做完的空缺 (最重要！)
    #   2. started (升序): 如果完成数一样，选当前正在做的人少的
    pools = []
    for pid, counts in status.items():
        pools.append({
            "id": pid,
            "started": counts["started"],
            "completed": counts["completed"]
        })
    
    # 为了避免总是分配给 ID 1，先随机打乱，再排序
    random.shuffle(pools)
    # 先按 started 排序 (次要条件)
    pools.sort(key=lambda x: x['started'])
    # 再按 completed 排序 (主要条件，Python sort 是稳定的)
    pools.sort(key=lambda x: x['completed'])
    
    # 3. 选中第一个（也就是完成数最少的那个）
    best_pool = pools[0]['id']
    
    # 4. 更新该 Pool 的 started 计数
    _update_pool_status(best_pool, "started")
    
    # 5. 更新用户的 assigned_pool 字段并写入题目
    import config # 延迟导入避免循环引用
    all_scenes_in_pool = config.get_scenes_in_pool(best_pool)
    random.shuffle(all_scenes_in_pool)
    
    user_file = DATA_ROOT / f"{user_id}.json"
    
    with safe_file_access(user_file, 'r+') as f:
        user_data = json.load(f)
        user_data['assigned_pool'] = best_pool
        user_data['scene_order'] = all_scenes_in_pool
        # 此时才有了题目，之前是空的
        
        f.seek(0)
        json.dump(user_data, f, indent=2, ensure_ascii=False)
        f.truncate()
        
    print(f"[ALLOCATION] User {user_id} assigned to Pool {best_pool} (Current Completes: {pools[0]['completed']})")
    return best_pool

def mark_user_completed(user_id):
    """
    当用户做完所有题目时调用。
    更新 pool_status 的 completed 计数。
    """
    user_file = DATA_ROOT / f"{user_id}.json"
    pool_id = None
    already_marked = False
    
    with safe_file_access(user_file, 'r+') as f:
        user_data = json.load(f)
        pool_id = user_data.get('assigned_pool')
        
        # 防止重复刷新导致重复计数
        if user_data.get('is_fully_completed'):
            already_marked = True
        else:
            user_data['is_fully_completed'] = True
            f.seek(0)
            json.dump(user_data, f, indent=2)
            f.truncate()
            
    if pool_id and not already_marked:
        _update_pool_status(pool_id, "completed")
        print(f"[COMPLETION] User {user_id} finished Pool {pool_id}. Stats updated.")


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
    Works on both Windows and Unix.
    
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
                exclusive = 'w' in mode or '+' in mode
                _lock_file(f, exclusive)
                yield f
            except (OSError, IOError):
                # Locking failed, proceed without file lock (thread lock still active)
                yield f
            finally:
                try:
                    _unlock_file(f)
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


def _get_next_pool_assignment():
    """
    获取下一个要分配的 Pool ID (1-6)，并更新全局计数器。
    线程安全 + 进程安全。
    """
    # 确保文件存在
    if not GLOBAL_STATE_FILE.exists():
        with safe_file_access(GLOBAL_STATE_FILE, 'w') as f:
            json.dump({"next_pool": 1}, f)

    assigned_pool = 1
    
    with safe_file_access(GLOBAL_STATE_FILE, 'r+') as f:
        if f:
            try:
                data = json.load(f)
                current = data.get("next_pool", 1)
                assigned_pool = current
                
                # 计算下一个 (1->2->3->4->5->6->1)
                next_val = current + 1
                if next_val > 6:
                    next_val = 1
                
                # 写回
                f.seek(0)
                json.dump({"next_pool": next_val}, f)
                f.truncate()
            except Exception as e:
                print(f"Error rotating pool: {e}")
                pass
    
    return str(assigned_pool)


def init_participant_file(demographics):
    """
    [修改后] 初始化用户：只存人口学信息，不分配题目，不分配 Pool。
    只有通过 Tutorial 后才会分配。
    """
    user_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(uuid.uuid4())[:6]}"
    
    data = {
        "user_id": user_id,
        "start_time": datetime.now().isoformat(),
        "assigned_pool": None,  # 暂时为空
        "demographics": demographics,
        "scene_order": [],      # 暂时为空
        "completed_scenes": [],         
        "experiments": [],
        "is_fully_completed": False # 标记是否完赛
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
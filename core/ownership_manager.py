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
import statistics
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

# 每个池子的目标完成人数上限 (可通过环境变量覆盖)
TARGET_COMPLETED_PER_POOL = int(os.getenv('TARGET_PER_POOL', 20))

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
    available_pools = _detect_available_pools()
    num_pools = len(available_pools)
    config_info = {
        "scenes_root": str(config.SCENES_ROOT),
        "total_scenes": len(scenes),
        "num_pools": num_pools,
        "scenes_per_pool": len(scenes) // num_pools if scenes and num_pools > 0 else 20,
        "target_per_pool": TARGET_COMPLETED_PER_POOL
    }
    
    return pool_status, participants[:50], config_info  # 最多返回50个最近的用户


def reset_pool_status():
    """重置所有池子的计数（管理员用）"""
    available_pools = _detect_available_pools()
    initial_status = {pid: {"started": 0, "completed": 0} for pid in available_pools}
    with open(POOL_STATUS_FILE, 'w', encoding='utf-8') as f:
        json.dump(initial_status, f, indent=2)
    # 同时重置全局索引
    with open(GLOBAL_STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump({"last_pool_index": -1}, f, indent=2)
    return initial_status


def get_participant_details(user_id):
    """
    获取单个参与者的详细数据。
    
    Args:
        user_id: 用户ID字符串
        
    Returns:
        Dict with user data including experiments and demographics,
        or None if user not found.
    """
    file_path = DATA_ROOT / f"{user_id}.json"
    
    if not file_path.exists():
        return None
    
    try:
        with safe_file_access(file_path, 'r') as f:
            if f:
                data = json.load(f)
                return {
                    "user_id": data.get("user_id"),
                    "start_time": data.get("start_time"),
                    "assigned_pool": data.get("assigned_pool"),
                    "demographics": data.get("demographics", {}),
                    "experiments": data.get("experiments", []),
                    "completed_scenes": data.get("completed_scenes", []),
                    "total_scenes": len(data.get("scene_order", [])),
                    "is_fully_completed": data.get("is_fully_completed", False)
                }
    except Exception as e:
        print(f"Error reading participant {user_id}: {e}")
        return None
    
    return None


def get_pool_aggregate_stats(pool_id):
    """
    获取特定池子的聚合统计数据。
    
    Args:
        pool_id: 池子ID字符串 (e.g., "1", "2")
        
    Returns:
        Dict structure:
        {
            "scene_name_A": {
                "object_1": {"mean": 55.2, "std_dev": 12.5, "n": 10},
                "object_2": {"mean": 80.0, "std_dev": 8.3, "n": 10}
            },
            ...
        }
    """
    pool_id = str(pool_id)
    aggregated = {}  # scene_name -> object_id -> list of values
    
    # Iterate through all participant files
    for user_file in DATA_ROOT.glob("*.json"):
        if user_file.name in ["blocked_users.json", "global_pool_state.json", "pool_status.json"]:
            continue
            
        try:
            with open(user_file, 'r', encoding='utf-8') as f:
                user_data = json.load(f)
            
            # Filter by pool
            if user_data.get('assigned_pool') != pool_id:
                continue
            
            # CRITICAL: Only count fully completed participants for statistics
            if not user_data.get('is_fully_completed', False):
                continue
            
            # Process experiments
            for experiment in user_data.get('experiments', []):
                scene_name = experiment.get('scene')
                if not scene_name:
                    continue
                    
                if scene_name not in aggregated:
                    aggregated[scene_name] = {}
                
                for result in experiment.get('results', []):
                    obj_id = result.get('object_id')
                    slider_val = result.get('slider_value')
                    
                    if obj_id is None or slider_val is None:
                        continue
                    
                    if obj_id not in aggregated[scene_name]:
                        aggregated[scene_name][obj_id] = []
                    
                    aggregated[scene_name][obj_id].append(slider_val)
                    
        except Exception as e:
            print(f"Error processing {user_file}: {e}")
            continue
    
    # Calculate mean, std_dev, n for each object
    result = {}
    for scene_name, objects in aggregated.items():
        result[scene_name] = {}
        for obj_id, values in objects.items():
            if values:
                n = len(values)
                mean_val = sum(values) / n
                # Calculate standard deviation (sample std dev if n > 1)
                if n > 1:
                    std_dev = statistics.stdev(values)
                else:
                    std_dev = 0.0
                result[scene_name][obj_id] = {
                    "mean": round(mean_val, 2),
                    "std_dev": round(std_dev, 2),
                    "n": n
                }
    
    return result


def get_all_participant_files():
    """
    获取所有参与者JSON文件的路径列表（用于打包下载）。
    
    Returns:
        List of Path objects for all participant JSON files.
    """
    files = []
    for user_file in DATA_ROOT.glob("*.json"):
        if user_file.name not in ["blocked_users.json", "global_pool_state.json", "pool_status.json"]:
            files.append(user_file)
    return files

# ==================== Pool Status Functions ====================

def _detect_available_pools():
    """动态检测 question_pool 文件夹中有多少个池子"""
    pool_ids = []
    if config.SCENES_ROOT.exists():
        for item in sorted(config.SCENES_ROOT.iterdir()):
            if item.is_dir() and item.name.isdigit():
                pool_ids.append(item.name)
    return pool_ids if pool_ids else ["1"]  # 至少返回一个默认池子


def _get_pool_status():
    """读取池子状态，如果不存在则根据实际池子数量初始化"""
    available_pools = _detect_available_pools()
    
    if not POOL_STATUS_FILE.exists():
        # 根据实际检测到的池子数量初始化
        initial_status = {pid: {"started": 0, "completed": 0} for pid in available_pools}
        with safe_file_access(POOL_STATUS_FILE, 'w') as f:
            json.dump(initial_status, f, indent=2)
        return initial_status
    
    with safe_file_access(POOL_STATUS_FILE, 'r') as f:
        existing_status = json.load(f)
    
    # 确保所有检测到的池子都在状态中
    updated = False
    for pid in available_pools:
        if pid not in existing_status:
            existing_status[pid] = {"started": 0, "completed": 0}
            updated = True
    
    if updated:
        with safe_file_access(POOL_STATUS_FILE, 'w') as f:
            json.dump(existing_status, f, indent=2)
    
    return existing_status

def _update_pool_status(pool_id, action="started"):
    """
    更新池子计数。
    action: "started" (分配时+1) 或 "completed" (全部做完时+1)
    """
    with safe_file_access(POOL_STATUS_FILE, 'r+') as f:
        if f is None:
            print(f"[ERROR] Pool status file not found, initializing...")
            _get_pool_status()  # This will create the file
            return
        data = json.load(f)
        pool_key = str(pool_id)
        
        if pool_key in data:
            data[pool_key][action] += 1
            
        f.seek(0)
        json.dump(data, f, indent=2)
        f.truncate()

def assign_pool_strategy(user_id):
    """
    [核心逻辑] 严格轮询分配策略：
    1. 动态检测可用池子数量
    2. 使用全局计数器严格按顺序分配 (1 -> 2 -> 3 -> ... -> N -> 1)
    3. 如果某个池子已达到完成上限，跳过它
    """
    # 1. 获取当前状态和可用池子
    status = _get_pool_status()  # {"1": {"started": 5, "completed": 3}, ...}
    available_pools = sorted(status.keys(), key=int)  # ["1", "2", "3", ...]
    num_pools = len(available_pools)
    
    if num_pools == 0:
        raise Exception("No pools available in question_pool folder!")
    
    # 2. 获取全局计数器 (上次分配的池子索引)
    last_index = _get_global_pool_index()
    
    # 3. 从上次位置开始，找下一个可用的池子
    best_pool = None
    attempts = 0
    
    while attempts < num_pools:
        # 计算下一个池子索引 (严格轮询)
        next_index = (last_index + 1) % num_pools
        candidate_pool = available_pools[next_index]
        
        # 检查是否已达到完成上限
        pool_completed = status.get(candidate_pool, {}).get("completed", 0)
        
        if pool_completed < TARGET_COMPLETED_PER_POOL:
            # 这个池子还没满，选中它
            best_pool = candidate_pool
            _set_global_pool_index(next_index)  # 更新全局计数器
            break
        else:
            # 这个池子满了，尝试下一个
            last_index = next_index
            attempts += 1
    
    # 如果所有池子都满了，使用完成数最少的那个（兜底逻辑）
    if best_pool is None:
        print(f"[WARNING] All pools have reached target ({TARGET_COMPLETED_PER_POOL}). Using least-filled pool.")
        pools_sorted = sorted(status.items(), key=lambda x: x[1].get("completed", 0))
        best_pool = pools_sorted[0][0]
    
    # 4. 更新该 Pool 的 started 计数
    _update_pool_status(best_pool, "started")
    
    # 5. 更新用户的 assigned_pool 字段并写入题目
    all_scenes_in_pool = config.get_scenes_in_pool(best_pool)
    random.shuffle(all_scenes_in_pool)
    
    user_file = DATA_ROOT / f"{user_id}.json"
    
    with safe_file_access(user_file, 'r+') as f:
        if f is None:
            raise Exception(f"User file not found: {user_file}. Please ensure the user has completed login.")
        user_data = json.load(f)
        user_data['assigned_pool'] = best_pool
        user_data['scene_order'] = all_scenes_in_pool
        # 此时才有了题目，之前是空的
        
        f.seek(0)
        json.dump(user_data, f, indent=2, ensure_ascii=False)
        f.truncate()
    
    pool_completed = status.get(best_pool, {}).get("completed", 0)
    print(f"[ALLOCATION] User {user_id} assigned to Pool {best_pool} (Completed: {pool_completed}/{TARGET_COMPLETED_PER_POOL})")
    return best_pool


def _get_global_pool_index():
    """获取全局池子分配索引（上次分配的是哪个池子）"""
    if not GLOBAL_STATE_FILE.exists():
        return -1  # 初始值，第一次分配时 +1 = 0，即从第一个池子开始
    
    try:
        with safe_file_access(GLOBAL_STATE_FILE, 'r') as f:
            if f:
                data = json.load(f)
                return data.get("last_pool_index", -1)
    except Exception:
        pass
    return -1


def _set_global_pool_index(index):
    """更新全局池子分配索引"""
    with safe_file_access(GLOBAL_STATE_FILE, 'w') as f:
        json.dump({"last_pool_index": index}, f, indent=2)

def mark_user_completed(user_id):
    """
    当用户做完所有题目时调用。
    更新 pool_status 的 completed 计数。
    """
    user_file = DATA_ROOT / f"{user_id}.json"
    pool_id = None
    already_marked = False
    
    with safe_file_access(user_file, 'r+') as f:
        if f is None:
            print(f"[ERROR] User file not found for mark_user_completed: {user_file}")
            return
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
    使用 participant_id 作为主要标识，添加时间戳后缀确保唯一性。
    """
    # 使用用户填写的 participant_id，加上时间戳确保唯一性
    participant_id = demographics.get('participant_id', 'unknown')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_suffix = str(uuid.uuid4())[:4]  # 短后缀防止同一秒内重复
    
    # 格式: participantID_timestamp_suffix (e.g., zhangsan1234_20260119_153022_a1b2)
    user_id = f"{participant_id}_{timestamp}_{unique_suffix}"
    
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


def get_upcoming_scenes(user_id, count=3):
    """
    获取用户接下来的几个场景名称（用于预加载）。
    返回: list of scene_names (不包含当前正在做的)
    """
    file_path = DATA_ROOT / f"{user_id}.json"
    
    with safe_file_access(file_path, 'r') as f:
        if not f:
            return []
        data = json.load(f)
    
    order = data['scene_order']
    completed = set(data['completed_scenes'])
    
    # 找到所有未完成的场景
    remaining = [scene for scene in order if scene not in completed]
    
    # 跳过当前正在做的（第一个），返回接下来的几个
    if len(remaining) > 1:
        return remaining[1:count+1]
    return []


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
            # CRITICAL: Ensure slider_value=50 (Unsure) is preserved as integer
            raw_slider = item.get('slider_value')
            if raw_slider is None:
                slider_val = 50  # Default to 50 (Unsure) if missing
            else:
                slider_val = int(raw_slider)  # Ensure it's always an integer
            
            record = {
                "object_id": item.get('object_id'),
                "agent_left_id": item.get('agent_a_id'),
                "agent_right_id": item.get('agent_b_id'),
                "slider_value": slider_val  # Always store as int, including 50
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
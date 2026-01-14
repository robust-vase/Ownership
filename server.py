"""
Server
======
Flask entry point.
Includes Session Management for Participants.
"""
from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for
from flask_cors import CORS
import json
import re
from pathlib import Path
import os

import config
from generators.page_generators import generate_html_page
from generators.guide_page_generator import generate_guide_html
from generators.login_generator import generate_login_html
from core.ownership_manager import init_participant_file, save_participant_results, get_next_scene, block_user, is_blocked

app = Flask(__name__)
CORS(app)

# Github 仓库
GITHUB_USER = "robust-vase"  # 你的用户名
REPO_NAME = "Ownership"      # 你的仓库名


# ================= CRITICAL CONFIG =================
# Secret Key loaded from config (environment variable or auto-generated)
app.secret_key = config.SECRET_KEY
# ===================================================

def parse_camera_id(filename):
    name = filename.replace('.png', '').replace('.jpg', '')
    name = re.sub(r'_(rgb|depth|seg|normal)$', '', name)
    return name

def find_camera(scene_data, camera_id):
    for camera in scene_data.get('cameras', []):
        if camera.get('id') == camera_id:
            return camera
    return None

def get_first_image(scene_path):
    for img in sorted(scene_path.glob('*.png')):
        if 'TopCamera' not in img.name:
            return img.name
    return None

# --- NEW: LOGIN ROUTES ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    # 0. 防刷检查
    client_ip = request.remote_addr
    if is_blocked(client_ip):
         return "<h1>Access Denied</h1><p>Based on previous sessions, you are not eligible for this experiment.</p>"

    if request.method == 'GET':
        return generate_login_html()
    
    try:
        demographics = {
            "gender": request.form.get('gender'),
            "dob": request.form.get('dob'),
            "status": request.form.get('status'),
            "education": request.form.get('education'),
            "nationality": request.form.get('nationality'),
            "ip_address": client_ip # 记录IP
        }
        
        # 1. 获取所有场景列表
        all_scenes_info = config.scan_scenes(config.SCENES_ROOT)
        all_scene_names = [s['name'] for s in all_scenes_info]
        
        if not all_scene_names:
            return "Server Error: No scenes configured.", 500

        # 2. 初始化文件 (立即保存人口信息)
        user_id = init_participant_file(demographics, all_scene_names)
        
        session['user_id'] = user_id
        session['user_role'] = 'participant'
        
        return redirect('/tutorial') 
        
    except Exception as e:
        return generate_login_html(error_message=f"Error: {str(e)}")
    

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# 新增：教程失败接口
@app.route('/fail_screening', methods=['POST'])
def fail_screening():
    client_ip = request.remote_addr
    block_user(client_ip) # 加入黑名单
    session.clear()
    return jsonify({"status": "blocked"})

# --- MODIFIED: MAIN ROUTES (Protected) ---

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    
    # 自动获取下一个场景
    scene_name, current_idx, total_count = get_next_scene(user_id)
    
    # 如果没有场景了，说明做完了
    if scene_name is None:
        return "<h1>Experiment Completed</h1><p>Thank you for your participation!</p>"
    
    # 加载场景数据 (和之前一样)
    scenes = config.scan_scenes(config.SCENES_ROOT)
    scene_info = next((s for s in scenes if s['name'] == scene_name), None)
    
    # ... (加载 scene_data, camera_data 代码保持不变) ...
    scene_path = scene_info['path']
    scene_data_path = scene_path / config.SCENE_DATA_FILENAME
    with open(scene_data_path, 'r', encoding='utf-8') as f:
        scene_data = json.load(f)
    image_name = get_first_image(scene_path) # 假设这个函数还在
    camera_id = parse_camera_id(image_name)
    camera_data = find_camera(scene_data, camera_id)
    # image_url = f"/scenes/{scene_name}/{image_name}"

    # Github 仓库
    image_url = f"https://raw.githubusercontent.com/{GITHUB_USER}/{REPO_NAME}/main/swap/{scene_name}/{image_name}"
    # 注意：这里我们不再传 available_scenes 给前端选择，而是传进度
    html = generate_html_page(
        scene_data, camera_data, image_name, image_url,
        scene_name, 
        current_idx, total_count # 传递进度参数
    )
    return html

@app.route('/tutorial')
def tutorial():
    # Tutorial also requires login? Usually yes for experiments.
    if 'user_id' not in session:
        return redirect('/login')
        
    # (保留原有的 Tutorial 逻辑，省略加载代码...)
    # 辅助函数：加载单个场景数据
    def load_scene_context(scene_dir_name):
        base_path = Path(__file__).parent / 'guide_data' / scene_dir_name
        data_path = base_path / 'scene_data.json'
        if not data_path.exists(): return None
        with open(data_path, 'r', encoding='utf-8') as f:
            scene_data = json.load(f)
        image_files = list(base_path.glob('*.png')) + list(base_path.glob('*.jpg'))
        if not image_files: return None
        image_name = image_files[0].name
        camera_id = parse_camera_id(image_name)
        camera_data = find_camera(scene_data, camera_id)
        if not camera_data: return None
        return {
            'scene_data': scene_data,
            'camera_data': camera_data,
            'image_url': f"/guide_images/{scene_dir_name}/{image_name}" 
        }

    ctx_1 = load_scene_context('guide_1')
    ctx_2 = load_scene_context('guide_2')
    
    if not ctx_1 or not ctx_2: return "Tutorial data missing", 404
    
    html = generate_guide_html(ctx_1, ctx_2)
    return html

# --- MODIFIED: SAVE ROUTE (User Centric) ---

@app.route('/save_ownerships', methods=['POST'])
def save_ownerships_route():
    if 'user_id' not in session:
        return jsonify({"error": "Session expired"}), 401

    try:
        data = request.json
        scene_name = data.get('scene')
        annotations = data.get('annotations', [])
        duration = data.get('duration_ms', 0)
        user_id = session['user_id']
        
        save_participant_results(user_id, scene_name, annotations, duration)
        
        # 返回 reload 指令，前端收到后刷新，index() 就会自动分发下一个场景
        return jsonify({
            "status": "success",
            "action": "reload" 
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ... (Keep existing static file routes: /scenes, /guide_images, etc.) ...
@app.route('/guide_images/<path:subpath>')
def serve_guide_image(subpath):
    base_dir = Path(__file__).parent / 'guide_data'
    return send_from_directory(base_dir, subpath)

@app.route('/scenes/<path:filepath>')
def serve_scene_file(filepath):
    full_path = config.SCENES_ROOT / filepath
    # ... (Keep logic) ...
    return send_from_directory(str(full_path.parent), full_path.name)

@app.route('/api/scenes')
def list_scenes():
    scenes = config.scan_scenes(config.SCENES_ROOT)
    return jsonify({"scenes": [s['name'] for s in scenes]})

if __name__ == '__main__':
    print(f"[INFO] Starting server on {config.SERVER_HOST}:{config.SERVER_PORT}")
    print(f"[INFO] Debug mode: {config.DEBUG_MODE}")
    app.run(host=config.SERVER_HOST, port=config.SERVER_PORT, debug=config.DEBUG_MODE)

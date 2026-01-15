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
from generators.admin_generator import generate_admin_html
from core.ownership_manager import (
    init_participant_file, 
    save_participant_results, 
    get_next_scene, 
    assign_pool_strategy,
    mark_user_completed,
    block_user, 
    is_blocked,
    get_admin_stats,
    reset_pool_status
)

app = Flask(__name__)
CORS(app)

# Github 仓库
GITHUB_USER = "robust-vase"
REPO_NAME = "Ownership"
# Cloudflare R2 公共 Bucket URL
R2_BUCKET_URL = "https://pub-173f52ca79174a20a448405a46dd40e0.r2.dev"

# ================= CRITICAL CONFIG =================
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

@app.route('/api/start_main_experiment', methods=['POST'])
def start_main_experiment():
    """
    只有当 Tutorial Step 9 (Check) 成功通过后，前端JS调用此接口。
    此时才正式分配 Pool。
    """
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
        
    user_id = session['user_id']
    try:
        # 这里调用 manager 分配 Pool
        pool_id = assign_pool_strategy(user_id)
        return jsonify({"status": "success", "pool": pool_id})
    except Exception as e:
        print(f"Error assigning pool: {e}")
        return jsonify({"error": str(e)}), 500

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
            "ip_address": client_ip
        }
        
        # 只初始化用户，不分配题目
        user_id = init_participant_file(demographics)
        
        session['user_id'] = user_id
        session['user_role'] = 'participant'
        
        return redirect('/tutorial') 
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return generate_login_html(error_message=f"Error: {str(e)}")
    
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

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
    
    # 如果还没有分配题目（total_count为0），说明没过教程，踢回教程
    if total_count == 0 and scene_name is None: 
         return redirect('/tutorial')
    
    # 如果没有场景了，说明做完了
    if scene_name is None:
        exit_fs_script = "<script>if(document.exitFullscreen) { document.exitFullscreen().catch(e=>{}); }</script>"
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Experiment Completed</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                    background: #f4f6f8;
                    height: 100vh;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    margin: 0;
                }}
                .card {{
                    background: white;
                    padding: 40px;
                    border-radius: 16px;
                    box-shadow: 0 10px 25px rgba(0,0,0,0.1);
                    text-align: center;
                    max-width: 500px;
                }}
                h1 {{ color: #2d3748; margin-bottom: 16px; }}
                p {{ color: #718096; line-height: 1.6; margin-bottom: 24px; }}
                .check-icon {{ font-size: 64px; margin-bottom: 20px; display: block; }}
            </style>
        </head>
        <body>
            <div class="card">
                <span class="check-icon">🎉</span>
                <h1>Session Completed</h1>
                <p>You have successfully completed all the assigned scenes.<br>Thank you for your contribution to our research!</p>
                <p style="font-size: 14px; color: #a0aec0;">You may now close this window.</p>
            </div>
            {exit_fs_script}
        </body>
        </html>
        """
    
    # 加载场景数据
    scenes = config.scan_scenes(config.SCENES_ROOT)
    scene_info = next((s for s in scenes if s['name'] == scene_name), None)
    
    if not scene_info:
        return f"Error: Scene {scene_name} not found on server.", 404

    scene_path = scene_info['path']
    scene_data_path = scene_path / config.SCENE_DATA_FILENAME
    
    with open(scene_data_path, 'r', encoding='utf-8') as f:
        scene_data = json.load(f)
        
    image_name = get_first_image(scene_path)
    camera_id = parse_camera_id(image_name)
    camera_data = find_camera(scene_data, camera_id)
    
    # === 关键修改 ===
    # 获取该场景所属的 pool (例如 "1", "2")
    pool_id = scene_info.get('pool', '')
    
    # 构建 URL 时加入 pool_id
    # 结果变成: /scenes/1/batch_8/TopCamera_rgb.png
    if pool_id:
        image_url = f"/scenes/{pool_id}/{scene_name}/{image_name}"
    else:
        # 兼容以前没有 Pool 的情况
        image_url = f"/scenes/{scene_name}/{image_name}"
    # ===============

    html = generate_html_page(
        scene_data, camera_data, image_name, image_url,
        scene_name, 
        current_idx, total_count
    )
    return html


@app.route('/tutorial')
def tutorial():
    if 'user_id' not in session:
        return redirect('/login')
        
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
    ctx_3 = load_scene_context('guide_3')

    if not ctx_1 or not ctx_2 or not ctx_3: 
        return "Tutorial data missing (Check guide_1, guide_2, guide_3 folder structure)", 404
    
    html = generate_guide_html(ctx_1, ctx_2, ctx_3)
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
        
        # 检查是否还有下一题
        next_scene, _, _ = get_next_scene(user_id)
        
        # 如果 next_scene 为 None，说明刚刚保存的是最后一题 -> 标记完赛
        if next_scene is None:
            mark_user_completed(user_id)
        
        return jsonify({
            "status": "success",
            "action": "reload" 
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== ADMIN ROUTES ====================

@app.route('/admin')
def admin_dashboard():
    """管理员仪表板 - 查看所有池子状态和用户进度"""
    # 简单的密码保护 (生产环境应该用更安全的方式)
    admin_key = request.args.get('key', '')
    if admin_key != 'brain2026':  # 你可以改成环境变量
        return "Unauthorized. Use ?key=YOUR_ADMIN_KEY", 401
    
    pool_status, participants, config_info = get_admin_stats()
    return generate_admin_html(pool_status, participants, config_info)


@app.route('/admin/reset', methods=['POST'])
def admin_reset():
    """重置池子计数（谨慎使用）"""
    admin_key = request.args.get('key', '')
    if admin_key != 'brain2026':
        return jsonify({"error": "Unauthorized"}), 401
    
    new_status = reset_pool_status()
    return jsonify({"status": "reset", "new_status": new_status})


@app.route('/api/pool_status')
def api_pool_status():
    """API: 获取池子状态 JSON"""
    pool_status, _, _ = get_admin_stats()
    return jsonify(pool_status)


# ==================== STATIC FILE ROUTES ====================

@app.route('/guide_images/<path:subpath>')
def serve_guide_image(subpath):
    base_dir = Path(__file__).parent / 'guide_data'
    return send_from_directory(base_dir, subpath)

@app.route('/scenes/<path:filepath>')
def serve_scene_file(filepath):
    full_path = config.SCENES_ROOT / filepath
    return send_from_directory(str(full_path.parent), full_path.name)

@app.route('/api/scenes')
def list_scenes():
    scenes = config.scan_scenes(config.SCENES_ROOT)
    return jsonify({"scenes": [s['name'] for s in scenes]})

if __name__ == '__main__':
    print(f"[INFO] Starting server on {config.SERVER_HOST}:{config.SERVER_PORT}")
    print(f"[INFO] Debug mode: {config.DEBUG_MODE}")
    app.run(host=config.SERVER_HOST, port=config.SERVER_PORT, debug=config.DEBUG_MODE)
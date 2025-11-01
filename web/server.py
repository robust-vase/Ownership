"""
Simple Flask Server
Handles save requests for object ownership relationships
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import json
from pathlib import Path
from ownership_manager import save_all_ownerships_from_web
from main_page_generator import generate_main_page_html
from scene_visualization import process_scene_data
from generate_html import scan_scene_folders

app = Flask(__name__)
CORS(app)  # Allow cross-origin requests

# Configure static file directories
STATIC_FOLDER = os.path.dirname(os.path.abspath(__file__))
# Image directory (parent directory / logs / ...)
LOGS_FOLDER = os.path.join(os.path.dirname(STATIC_FOLDER), 'logs')
BASE_SCENES_FOLDER = os.path.join(LOGS_FOLDER, '4agents_9_allmap')


@app.route('/')
def index():
    """Return main page"""
    return send_from_directory(STATIC_FOLDER, 'dashboard.html')


@app.route('/logs/<path:filepath>')
def serve_images(filepath):
    """Serve image files from logs directory"""
    print(f"[DEBUG] Requesting image: {filepath}")
    full_path = os.path.join(LOGS_FOLDER, filepath)
    print(f"[DEBUG] Full image path: {full_path}")
    print(f"[DEBUG] File exists: {os.path.exists(full_path)}")
    
    if not os.path.exists(full_path):
        print(f"[ERROR] Image not found: {full_path}")
        return jsonify({"error": "Image not found"}), 404
    
    directory = os.path.dirname(full_path)
    filename = os.path.basename(full_path)
    return send_from_directory(directory, filename)


@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory(STATIC_FOLDER, filename)


@app.route('/save_all_ownerships', methods=['POST'])
def save_all_ownerships():
    """
    Batch save object ownership relationships
    
    Request body format:
    {
        "ownerships": [
            {
                "object_id": "Object ID",
                "object_name": "Object Name",
                "owner_id": "Owner ID",
                "owner_name": "Owner Name"
            },
            ...
        ],
        "session_id": "Optional Session ID"
    }
    """
    try:
        data = request.get_json()
        result = save_all_ownerships_from_web(data)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "message": "Server is running"
    }), 200


@app.route('/load_scene', methods=['GET'])
def load_scene():
    """
    Load a specific scene by name
    
    Query parameters:
        scene: Scene folder name (e.g., table_scene_map001_room_diningRoom_table1)
    
    Returns:
        Complete HTML page with the selected scene loaded
    """
    try:
        scene_name = request.args.get('scene')
        if not scene_name:
            return jsonify({"error": "Scene name is required"}), 400
        
        print(f"\n[INFO] Loading scene: {scene_name}")
        
        # Construct paths
        scene_path = Path(BASE_SCENES_FOLDER) / scene_name
        scene_json_path = scene_path / 'scene_data.json'
        
        if not scene_json_path.exists():
            return jsonify({"error": f"Scene not found: {scene_name}"}), 404
        
        # Load scene data
        with open(scene_json_path, 'r', encoding='utf-8') as f:
            scene_data = json.load(f)
        
        # Get all available scenes
        all_scenes = scan_scene_folders(Path(BASE_SCENES_FOLDER))
        
        # Generate HTML with new scene
        html_content = generate_main_page_html(
            scene_data, 
            scene_path,
            all_scenes,
            scene_name
        )
        
        # Save to dashboard.html
        output_path = Path(STATIC_FOLDER) / 'dashboard.html'
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"[INFO] Scene loaded successfully: {scene_name}")
        
        return jsonify({
            "success": True,
            "scene": scene_name,
            "message": "Scene loaded successfully"
        }), 200
        
    except Exception as e:
        print(f"[ERROR] Failed to load scene: {str(e)}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == '__main__':
    print("=" * 60)
    print("Object Ownership Management Server")
    print("=" * 60)
    print(f"Access URL: http://localhost:5000")
    print(f"Dashboard: http://localhost:5000/dashboard.html")
    print(f"Save Directory: ./ownership_data/")
    print("=" * 60)
    print("\n[DEBUG] File Path Configuration:")
    print(f"  Static Folder: {STATIC_FOLDER}")
    print(f"  Logs Folder: {LOGS_FOLDER}")
    print(f"  Logs Folder Exists: {os.path.exists(LOGS_FOLDER)}")
    
    # List available image directories
    if os.path.exists(LOGS_FOLDER):
        print(f"\n[DEBUG] Available directories in logs folder:")
        for item in os.listdir(LOGS_FOLDER):
            item_path = os.path.join(LOGS_FOLDER, item)
            if os.path.isdir(item_path):
                print(f"  - {item}/")
                # Check for subdirectories
                subdirs = [d for d in os.listdir(item_path) if os.path.isdir(os.path.join(item_path, d))]
                if subdirs:
                    for subdir in subdirs[:3]:  # Show first 3 subdirectories
                        print(f"    - {subdir}/")
    else:
        print(f"\n[WARNING] Logs folder does not exist: {LOGS_FOLDER}")
    
    print("=" * 60)
    print("\nPress Ctrl+C to stop the server\n")
    
    # Create save directory
    os.makedirs('ownership_data', exist_ok=True)
    
    # Start server
    app.run(host='0.0.0.0', port=5000, debug=True)

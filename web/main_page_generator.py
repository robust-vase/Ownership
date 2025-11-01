"""
主页面生成器
负责整体布局框架的生成，调用各个子模块生成具体内容
"""
import json
from pathlib import Path
from scene_visualization import process_scene_data
from projection_calculator import calculate_all_projections
from camera_panel_generator import generate_camera_panel_html, generate_camera_bbox_script
from topcamera_panel_generator import generate_topcamera_panel_html, generate_topcamera_script
from scene_panel_generator import (
    generate_scene_panel_html, 
    generate_scene_visualization_script,
    generate_scene_interaction_script
)


def get_image_files(directory_path, pattern):
    """Get image files matching pattern from directory"""
    image_files = []
    directory = Path(directory_path)
    
    print(f"[DEBUG] Searching for images in: {directory}")
    print(f"[DEBUG] Directory exists: {directory.exists()}")
    print(f"[DEBUG] Pattern: {pattern}")
    
    if directory.exists():
        if "Camera" in pattern and "TopCamera" not in pattern:
            # Match all Camera_N_rgb.png files (excluding TopCamera)
            for file in directory.glob("*_rgb.png"):
                if "Camera_" in file.name and "TopCamera" not in file.name:
                    image_files.append(file)
                    print(f"[DEBUG] Found Camera image: {file.name}")
        elif "TopCamera" in pattern:
            # Match all TopCamera_*_rgb.png files
            for file in directory.glob("*TopCamera*_rgb.png"):
                image_files.append(file)
                print(f"[DEBUG] Found TopCamera image: {file.name}")
    else:
        print(f"[WARNING] Directory does not exist: {directory}")
    
    print(f"[DEBUG] Total {pattern} images found: {len(image_files)}")
    return sorted(image_files)


def generate_css_styles():
    """生成CSS样式"""
    return """
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: Arial, sans-serif;
                background-color: #f5f5f5;
            }
            
            .header {
                background-color: #2c3e50;
                color: white;
                padding: 15px;
                text-align: center;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            
            .scene-selector {
                background-color: #34495e;
                color: white;
                padding: 12px 20px;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                gap: 10px;
            }
            
            .scene-selector label {
                font-weight: bold;
                font-size: 14px;
            }
            
            .scene-selector select {
                padding: 6px 12px;
                border-radius: 4px;
                border: 1px solid #bdc3c7;
                font-size: 14px;
                min-width: 300px;
            }
            
            .scene-selector button {
                padding: 6px 16px;
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 14px;
                font-weight: bold;
                transition: background-color 0.3s;
            }
            
            .scene-selector button:hover {
                background-color: #2980b9;
            }
            
            .scene-selector #next-scene-btn {
                background-color: #27ae60;
            }
            
            .scene-selector #next-scene-btn:hover {
                background-color: #229954;
            }
            
            .main-container {
                display: grid;
                grid-template-columns: 1fr 1fr;
                grid-template-rows: 1fr;
                gap: 15px;
                padding: 15px;
                height: calc(100vh - 80px);
            }
            
            .right-panel {
                display: flex;
                flex-direction: column;
                gap: 15px;
                overflow-y: auto;
                overflow-x: hidden;
            }
            
            .scene-panel {
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                padding: 20px;
                height: auto;
                min-height: 500px;
                flex-shrink: 0;
            }
            
            .camera-panel {
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                padding: 20px;
                overflow-y: auto;
                display: flex;
                flex-direction: column;
            }
            
            .match-panel {
                background: white;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                padding: 20px;
                min-height: 400px;
                height: auto;
                display: flex;
                flex-direction: column;
                flex-shrink: 0;
            }
            
            .agent-tags-container {
                width: 20%;
                display: flex;
                flex-direction: column;
                gap: 12px;
                flex-shrink: 0;
            }
            
            .agent-tag-box {
                border: 3px solid;
                border-radius: 8px;
                padding: 15px;
                text-align: center;
                font-weight: bold;
                font-size: 14px;
                color: white;
                transition: all 0.3s ease;
                cursor: pointer;
                position: relative;
                min-height: 80px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .agent-tag-box.highlight {
                transform: scale(1.1);
                box-shadow: 0 4px 16px rgba(0,0,0,0.3);
            }
            
            .topcamera-image-container {
                width: 80%;
                position: relative;
                flex-shrink: 0;
            }
            
            .camera-panel::-webkit-scrollbar {
                width: 10px;
            }
            
            .camera-panel::-webkit-scrollbar-track {
                background: #f1f1f1;
                border-radius: 5px;
            }
            
            .camera-panel::-webkit-scrollbar-thumb {
                background: #888;
                border-radius: 5px;
            }
            
            .camera-panel::-webkit-scrollbar-thumb:hover {
                background: #555;
            }
            
            .right-panel::-webkit-scrollbar {
                width: 10px;
            }
            
            .right-panel::-webkit-scrollbar-track {
                background: #f1f1f1;
                border-radius: 5px;
            }
            
            .right-panel::-webkit-scrollbar-thumb {
                background: #888;
                border-radius: 5px;
            }
            
            .right-panel::-webkit-scrollbar-thumb:hover {
                background: #555;
            }
            
            .panel-title {
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 15px;
                color: #2c3e50;
                border-bottom: 2px solid #3498db;
                padding-bottom: 8px;
                flex-shrink: 0;
            }
            
            #scene-visualization {
                width: 100%;
                height: 700px;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            
            .image-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 15px;
                padding-right: 5px;
            }
            
            .image-container {
                background: #f8f9fa;
                border-radius: 6px;
                padding: 10px;
                text-align: center;
                border: 1px solid #e9ecef;
                transition: transform 0.2s ease;
                position: relative;
            }
            
            .image-container:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            }
            
            .camera-image {
                width: 100%;
                height: auto;
                border-radius: 4px;
                cursor: pointer;
                display: block;
            }
            
            .image-wrapper {
                position: relative;
                display: inline-block;
                width: 100%;
            }
            
            .bbox-overlay {
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                pointer-events: all;
            }
            
            .bbox-rect {
                fill: #4CAF50;
                stroke: #4CAF50;
                stroke-width: 1;
                stroke-opacity: 0.3;
                fill-opacity: 0.02;
                transition: all 0.3s ease;
            }
            
            .bbox-rect.highlighted {
                stroke: #2E7D32;
                stroke-width: 2.5;
                stroke-opacity: 1.0;
                fill-opacity: 0.3;
            }
            
            .bbox-label {
                font-size: 6px;
                fill: #4CAF50;
                opacity: 0.6;
                font-weight: bold;
                transition: all 0.3s ease;
                pointer-events: none;
            }
            
            .bbox-label.highlighted {
                font-size: 10px;
                fill: #2E7D32;
                opacity: 1.0;
            }
            
            .bbox-label-bg {
                fill: white;
                opacity: 0;
                transition: all 0.3s ease;
            }
            
            .bbox-label-bg.highlighted {
                fill: white;
                opacity: 0.95;
                stroke: #2E7D32;
                stroke-width: 1;
            }
            
            .image-label {
                margin-top: 8px;
                font-size: 12px;
                color: #666;
                font-weight: 500;
            }
            
            .match-image {
                width: 100%;
                height: auto;
                max-width: 100%;
                object-fit: contain;
                border-radius: 4px;
                border: 1px solid #ddd;
                display: block;
            }
            
            .bbox-group {
                cursor: pointer;
            }
            
            .bbox-group.dragging {
                cursor: move;
            }
            
            /* Scene Visualization Styles */
            .table { fill: #9E9E9E; opacity: 0.3; stroke: #9E9E9E; stroke-width: 2; }
            .room-object { fill: #2196F3; }
            .personal-object { fill: #4CAF50; }
            .agent { fill: #FF9800; }
            .camera { fill: #F44336; }
            .object-bounds {
                fill: none;
                stroke-width: 1;
                opacity: 0.5;
            }
            .room-bounds { stroke: #2196F3; fill: #2196F3; fill-opacity: 0.15; }
            .personal-bounds { 
                stroke: #4CAF50; 
                fill: #4CAF50; 
                fill-opacity: 0.02; 
                stroke-opacity: 0.3;
                stroke-width: 1;
                transition: all 0.3s ease;
                cursor: pointer;
            }
            .personal-bounds.highlighted { 
                fill-opacity: 0.3; 
                stroke-opacity: 1.0;
                stroke-width: 2.5;
                stroke: #2E7D32;
            }
            .personal-bounds.clicked {
                fill-opacity: 0.3;
                stroke-opacity: 1.0;
                stroke-width: 2.5;
                stroke: #2E7D32;
            }
            .personal-object { 
                fill-opacity: 0.4;
                transition: all 0.3s ease;
                cursor: pointer;
            }
            .personal-object.highlighted { 
                fill-opacity: 1.0;
            }
            .personal-object.clicked {
                fill-opacity: 1.0;
            }
            .label {
                font-size: 8px;
                font-weight: bold;
                pointer-events: none;
            }
            .personal-label {
                font-size: 6px;
                opacity: 0.6;
                transition: all 0.3s ease;
            }
            .personal-label.highlighted {
                font-size: 10px;
                opacity: 1.0;
                fill: #2E7D32;
            }
            .personal-label.clicked {
                font-size: 10px;
                opacity: 1.0;
                fill: #2E7D32;
            }
            .label-bg {
                fill: white;
                opacity: 0.8;
                transition: all 0.3s ease;
            }
            .personal-label-bg {
                fill: white;
                opacity: 0;
                transition: all 0.3s ease;
            }
            .personal-label.highlighted + .personal-label-bg {
                opacity: 0.95;
                stroke: #2E7D32;
                stroke-width: 1;
            }
            .direction-arrow {
                stroke-width: 2;
                fill: none;
            }
        </style>
    """


def generate_main_page_html(scene_data, images_directory, scene_folders=None, current_scene=None):
    """
    Generate main page HTML content
    
    Args:
        scene_data: Scene data dictionary
        images_directory: Image directory path
        scene_folders: List of available scene folder names
        current_scene: Current scene folder name
    
    Returns:
        Complete HTML string
    """
    
    print("\n" + "=" * 60)
    print("Generating Dashboard HTML")
    print("=" * 60)
    
    # Process scene data
    processed_data = process_scene_data(scene_data)
    
    # Calculate all projections
    projections = calculate_all_projections(scene_data)
    
    # Get image file lists
    camera_images = get_image_files(images_directory, "Camera")
    topcamera_images = get_image_files(images_directory, "TopCamera")
    
    # Extract scene folder name from images_directory
    scene_folder_name = Path(images_directory).name
    
    # Image relative path - updated to work with Flask server
    # The server will serve images from /logs/<path>
    images_relative_path = f"/logs/4agents_9_allmap/{scene_folder_name}"
    
    print(f"\n[INFO] Image Configuration:")
    print(f"  Relative Path in HTML: {images_relative_path}")
    print(f"  Camera Images Count: {len(camera_images)}")
    print(f"  TopCamera Images Count: {len(topcamera_images)}")
    print("=" * 60 + "\n")
    
    # Generate scene selector HTML
    scene_selector_html = ""
    if scene_folders and len(scene_folders) > 1:
        options_html = "\n".join([
            f'<option value="{folder}" {"selected" if folder == current_scene else ""}>{folder}</option>'
            for folder in scene_folders
        ])
        scene_selector_html = f"""
        <div class="scene-selector">
            <label for="scene-select">Select Scene:</label>
            <select id="scene-select">
                {options_html}
            </select>
            <button id="load-scene-btn" onclick="loadSelectedScene()">Load Scene</button>
            <button id="next-scene-btn" onclick="loadNextScene()" style="margin-left: 10px;">Next Scene →</button>
            <span id="scene-status" style="margin-left: 15px; color: #666;"></span>
        </div>
        """
    
    # 生成HTML结构
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Scene Analysis Dashboard</title>
        <script src="https://d3js.org/d3.v7.min.js"></script>
        {generate_css_styles()}
    </head>
    <body>
        <div class="header">
            <h1>Scene Analysis Dashboard</h1>
        </div>
        
        {scene_selector_html}
        
        <div class="main-container">
            {generate_camera_panel_html(camera_images, images_relative_path, projections)}
            
            <!-- 右侧：匹配区域和场景平面图（整体滚动） -->
            <div class="right-panel">
                {generate_topcamera_panel_html(topcamera_images, images_relative_path)}
                {generate_scene_panel_html()}
            </div>
        </div>
        
        <script>
            // 全局数据
            const projections = {json.dumps(projections)};
            let currentSceneName = "{scene_folder_name}";
            const allScenes = {json.dumps(scene_folders if scene_folders else [])};
            
            {generate_scene_visualization_script(processed_data)}
            {generate_camera_bbox_script(len(camera_images))}
            {generate_topcamera_script()}
            {generate_scene_interaction_script()}
            
            // Scene loading functions
            function loadSelectedScene() {{
                const select = document.getElementById('scene-select');
                const sceneName = select.value;
                loadScene(sceneName);
            }}
            
            function loadNextScene() {{
                const currentIndex = allScenes.indexOf(currentSceneName);
                if (currentIndex >= 0 && currentIndex < allScenes.length - 1) {{
                    const nextScene = allScenes[currentIndex + 1];
                    loadScene(nextScene);
                }} else {{
                    updateSceneStatus('Already at the last scene', 'warning');
                }}
            }}
            
            function loadScene(sceneName) {{
                updateSceneStatus('Loading scene...', 'loading');
                
                fetch(`/load_scene?scene=${{encodeURIComponent(sceneName)}}`)
                    .then(response => {{
                        if (!response.ok) {{
                            throw new Error('Failed to load scene');
                        }}
                        return response.json();
                    }})
                    .then(data => {{
                        // Reload the page with new scene data
                        window.location.href = `/dashboard.html?scene=${{encodeURIComponent(sceneName)}}`;
                    }})
                    .catch(error => {{
                        console.error('Error loading scene:', error);
                        updateSceneStatus('Failed to load scene', 'error');
                    }});
            }}
            
            function updateSceneStatus(message, type) {{
                const statusSpan = document.getElementById('scene-status');
                if (statusSpan) {{
                    statusSpan.textContent = message;
                    statusSpan.style.color = type === 'error' ? '#e74c3c' : 
                                             type === 'warning' ? '#f39c12' :
                                             type === 'loading' ? '#3498db' : '#27ae60';
                }}
            }}
            
            // 初始化bbox交互（TopCamera的拖动交互在drawTopCamera内部自动设置）
            setTimeout(() => {{
                setupBboxInteractions();
            }}, 100);
            
            // 窗口大小改变时重新绘制
            window.addEventListener('resize', () => {{
                const cameraCount = {len(camera_images)};
                for (let i = 0; i < cameraCount; i++) {{
                    drawBboxOnCamera(i, `bbox-svg-${{i}}`, `camera-img-${{i}}`);
                }}
                drawTopCamera();  // TopCamera内部会自动调用setupBboxInteractions()
                
                // 只需要为相机图片重新绑定交互
                setTimeout(() => {{
                    setupBboxInteractions();
                }}, 100);
            }});
        </script>
    </body>
    </html>
    """
    
    return html_content

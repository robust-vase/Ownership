"""
Page Generators
===============
HTML generation logic separated into camera view and matching panel.
REFACTORED: Now uses centralized data_processor for scene processing.
"""
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data_processor import process_scene_data
from static_assets.ui_components import render_common_css, render_left_panel_html, render_right_panel_html, render_core_script


def generate_html_page(scene_data, camera_data, image_filename, image_url, scene_name, current_idx, total_count):
    """
    Generate complete HTML page.
    Args:
        scene_data: Scene data dictionary
        camera_data: Camera parameters
        image_filename: Image filename (unused but kept for API compatibility)
        image_url: URL to the scene image
        scene_name: Name of the scene
        current_idx: Current scene number (1-based)
        total_count: Total number of scenes
    """
    # Use centralized data processor - eliminates ~100 lines of duplicate code!
    objects_data, agents_data, agent_labels = process_scene_data(
        scene_data, camera_data, 
        use_display_mapping=True, 
        filter_empty_plates=True
    )
    
    # Generate HTML
    objects_json = json.dumps(objects_data, ensure_ascii=False)
    agents_json = json.dumps(agents_data, ensure_ascii=False)
    agent_labels_json = json.dumps(agent_labels, ensure_ascii=False)
    
    html = _build_html_template(
        image_url, scene_name, 
        objects_json, agents_json, agent_labels_json, 
        current_idx, total_count
    )
    
    return html


def _build_html_template(image_url, scene_name, objects_json, agents_json, agent_labels_json, current_idx, total_count):
    """Build complete HTML template using reusable UI components."""
    
    common_css = render_common_css()
    left_panel = render_left_panel_html(image_url)
    # 修改按钮文本，提示用户会自动进入下一张
    right_panel = render_right_panel_html(submit_button_text="Save & Next")
    
    # 核心脚本：包含保存逻辑
    core_script = render_core_script(objects_json, agents_json, agent_labels_json, include_save_function=True)
    
    # 页面专属 CSS：进度条样式
    page_specific_css = """
        .progress-indicator {
            background: rgba(0, 0, 0, 0.05);
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 600;
            color: #555;
            border: 1px solid rgba(0, 0, 0, 0.1);
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .progress-indicator span {
            font-variant-numeric: tabular-nums;
        }
    """
    
    # 页面专属脚本：全屏恢复逻辑
    page_specific_script = f"""
        const currentScene = '{scene_name}';
        const startTime = Date.now(); // 记录开始时间用于统计 duration
        
        // 尝试维持全屏体验
        window.addEventListener('load', () => {{
            // 这里可以检测全屏状态，必要时提示用户
            // console.log("Scene loaded. Index: {current_idx}/{total_count}");
        }});
        
        // 点击页面任何空白处尝试恢复全屏（可选，为了不打扰用户暂不强制执行）
        /*
        document.addEventListener('click', () => {{
            if (!document.fullscreenElement && document.documentElement.requestFullscreen) {{
                // document.documentElement.requestFullscreen().catch(e => {{}});
            }}
        }});
        */
    """
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Experiment - {current_idx}/{total_count}</title>
    <style>
        {common_css}
        {page_specific_css}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧠 Experiment</h1>
        <div class="progress-indicator">
            <span>Scene {current_idx} / {total_count}</span>
        </div>
    </div>
    
    <div class="container">
        {left_panel}
        {right_panel}
    </div>
    
    <script>
        {core_script}
        {page_specific_script}
    </script>
</body>
</html>
"""
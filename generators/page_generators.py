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
    right_panel = render_right_panel_html(submit_button_text="Save & Next")
    
    core_script = render_core_script(objects_json, agents_json, agent_labels_json, include_save_function=True)
    
    # --- 新增：专注模式（前5秒）的 CSS ---
    focus_mode_css = """
        /* 默认状态（5秒后）：进度条样式 */
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
        .progress-indicator span { font-variant-numeric: tabular-nums; }

        /* === FOCUS MODE (前3秒加载时) === */
        
        /* 1. 改变布局容器：从 Grid 变为 Flex 居中 */
        body.focus-mode .container {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh; /* 占满全屏 */
            padding: 0;
            margin: 0;
            width: 100vw;
        }

        /* 2. 隐藏干扰元素：右侧面板、顶部导航、图片上的框 */
        body.focus-mode #right-panel-wrapper { display: none !important; }
        body.focus-mode .header { display: none !important; }
        body.focus-mode #svgOverlay { display: none !important; } /* 隐藏框框，只看纯图 */
        
        /* 3. 调整左侧面板样式：去边框、去阴影、透明背景 */
        body.focus-mode #left-panel-wrapper {
            width: auto;
            height: 100%;
            max-width: 100%;
            background: transparent;
            border: none;
            box-shadow: none;
            border-radius: 0;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        
        /* 4. 隐藏左侧面板的标题栏（Camera View字样） */
        body.focus-mode #left-panel-wrapper .panel-header { display: none; }
        
        /* 5. 图片容器调整 */
        body.focus-mode #imageContainer {
            background: transparent;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        /* 6. 图片核心样式：高度占满，宽度自适应，保持比例 */
        body.focus-mode img.camera-image {
            height: 98vh; /* 留一点点边距看起来舒服，或者用 100vh */
            width: auto;
            max-width: 98vw;
            object-fit: contain;
            box-shadow: 0 0 50px rgba(0,0,0,0.1); /* 给图片加一点悬浮感 */
        }
    """
    
    # --- 新增：控制 5秒 逻辑的 JS ---
    page_logic_script = f"""
        const currentScene = '{scene_name}';
        const startTime = Date.now(); 
        
        // 页面加载时执行
        window.addEventListener('load', () => {{
            // 1. 立即添加 focus-mode 类 (实际上我们在 body 标签里直接写 class="focus-mode" 防止闪烁)
            
            // 2. 设置 5秒 定时器
            setTimeout(() => {{
                exitFocusMode();
            }}, 5000);
        }});
        
        function exitFocusMode() {{
            // 移除 CSS 类，恢复默认布局
            document.body.classList.remove('focus-mode');
            
            // 重要：因为布局发生了剧烈变化（图片大小变了），
            // 必须通知 SVG 重新计算覆盖层的大小和位置
            if (typeof adjustSVGSize === 'function') {{
                //稍微延迟一下等待 CSS transition 结束（如果有的话），这里直接执行通常也行
                setTimeout(adjustSVGSize, 50); 
            }}
        }}
    """
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Experiment - {current_idx}/{total_count}</title>
    <style>
        {common_css}
        {focus_mode_css}
    </style>
</head>
<body class="focus-mode">
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
        {page_logic_script}
    </script>
</body>
</html>
"""
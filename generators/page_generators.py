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
from core.translations import get_text
from core.ui_components import render_common_css, render_left_panel_html, render_right_panel_html, render_core_script
import config

import random

# Attention Check Questions - imported from centralized config
ATTENTION_CHECK_QUESTIONS = config.ATTENTION_CHECK_QUESTIONS


def should_inject_attention_check(current_idx):
    """
    Attention check injection logic:
    Triggers at specific indices defined in config.ATTENTION_CHECK_INDICES
    
    Rules for attention check failures:
    - Failures at indices 5, 10, 15: Terminate experiment immediately
    - Failures at indices 20, 25: Log but continue (forgiveness rule)
    """
    return current_idx in config.ATTENTION_CHECK_INDICES


def generate_html_page(scene_data, camera_data, image_filename, image_url, scene_name, current_idx, total_count, lang='en'):
    """
    Generate complete HTML page.
    """
    # Use centralized data processor with language support
    objects_data, agents_data, agent_labels = process_scene_data(
        scene_data, camera_data, 
        use_display_mapping=True, 
        filter_empty_plates=True,
        lang=lang
    )
    
    # --- Attention Check Injection Logic ---
    attention_check_meta = {}  # Will be passed to JS for validation
    
    # 检测是否应该插入陷阱题
    if should_inject_attention_check(current_idx):
        check = random.choice(ATTENTION_CHECK_QUESTIONS)
        check_id = f"attention_check_{current_idx}"
        question_text = check['question_zh'] if lang == 'zh' else check['question_en']
        
        # 创建一个“伪装”物品
        # is_attention_check=True 会让它在 ui_components.py 中：
        # 1. 不会在 SVG 图片上画框（renderVisuals 会跳过）
        # 2. 会在右侧列表显示（populateObjectList 正常渲染）
        stealth_name = "检测" if lang == 'zh' else "Check" # 使用听起来很中性的名字
        attention_obj = {
            "id": check_id,
            "display_name": stealth_name,
            "label": stealth_name,
            "polygon": [[0, 0], [0, 0], [0, 0]],  # 空坐标，确保无视觉干扰
            "question": question_text, # 这里会覆盖默认的 "Who owns this?"
            "is_attention_check": True
        }
        
        # 随机插入到列表中间（混淆视听）
        if len(objects_data) >= 3:
            insert_pos = random.randint(1, len(objects_data) - 1)
        elif len(objects_data) == 2:
            insert_pos = 1
        else:
            insert_pos = 0
        objects_data.insert(insert_pos, attention_obj)
        
        # 记录正确答案规则，传给前端 JS
        attention_check_meta[check_id] = {"target": check['target']}
    
    # Generate HTML
    objects_json = json.dumps(objects_data, ensure_ascii=False)
    agents_json = json.dumps(agents_data, ensure_ascii=False)
    agent_labels_json = json.dumps(agent_labels, ensure_ascii=False)
    attention_meta_json = json.dumps(attention_check_meta, ensure_ascii=False)
    
    html = _build_html_template(
        image_url, scene_name, 
        objects_json, agents_json, agent_labels_json, 
        current_idx, total_count,
        lang=lang,
        attention_meta_json=attention_meta_json
    )
    
    return html


def _build_html_template(image_url, scene_name, objects_json, agents_json, agent_labels_json, current_idx, total_count, lang='en', attention_meta_json='{}'):
    """Build complete HTML template using reusable UI components."""
    
    # Get translated strings
    t = lambda key: get_text(lang, f"experiment.{key}")
    page_title = get_text(lang, 'experiment.page_title')
    header_text = t('header')
    scene_progress = get_text(lang, 'experiment.scene_progress', current=current_idx, total=total_count)
    submit_text = t('submit_button')
    camera_view = t('camera_view')
    ownership_panel = t('ownership_panel')
    
    # UI translations for core script
    ui_translations = {
        'ownership_question': t('ownership_question'),
        'slider_unsure': t('slider_unsure'),
        'confirm_button': t('confirm_button'),
        'locked_button': '已锁定' if lang == 'zh' else 'Locked'
    }
    
    common_css = render_common_css()
    left_panel = render_left_panel_html(image_url, panel_header=camera_view)
    right_panel = render_right_panel_html(submit_button_text=submit_text, panel_header=ownership_panel)
    
    # 核心脚本：这里面包含了 Attention Check 的验证逻辑
    core_script = render_core_script(objects_json, agents_json, agent_labels_json, include_save_function=True, lang=lang, translations=ui_translations)
    
    # 专注模式 CSS
    focus_mode_css = """
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

        body.focus-mode .container {
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            padding: 0;
            margin: 0;
            width: 100vw;
        }
        body.focus-mode #right-panel-wrapper { display: none !important; }
        body.focus-mode .header { display: none !important; }
        body.focus-mode #svgOverlay { display: none !important; }
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
        body.focus-mode #left-panel-wrapper .panel-header { display: none; }
        body.focus-mode #imageContainer {
            background: transparent;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        body.focus-mode img.camera-image {
            height: 98vh;
            width: auto;
            max-width: 98vw;
            object-fit: contain;
            box-shadow: 0 0 50px rgba(0,0,0,0.1);
        }
    """
    
    # 页面逻辑脚本：控制5秒倒计时 + 全屏保护
    page_logic_script = f"""
        // === GLOBAL STATE (use var to avoid redeclaration errors during soft update) ===
        window.currentScene = '{scene_name}';
        window.startTime = Date.now();
        window.currentSceneIdx = {current_idx}; 
        window.attentionCheckMeta = {attention_meta_json};
        
        // === CRITICAL: Transitioning flag for fullscreen protection ===
        // Only set to false here if not already in a transition
        if (typeof window.isTransitioning === 'undefined') {{
            window.isTransitioning = false;
        }}
        
        // === FULLSCREEN CHECK WITH TRANSITION PROTECTION ===
        window.checkFullscreenStatus = function() {{
            // CRITICAL: Do NOT show overlay if we're transitioning between scenes
            if (window.isTransitioning === true) {{
                console.log('[Fullscreen] Check skipped - transitioning...');
                return;
            }}
            
            var overlay = document.getElementById('fullscreen-overlay');
            if (overlay) {{
                var isFullscreen = !!(document.fullscreenElement || document.webkitFullscreenElement || document.mozFullScreenElement || document.msFullscreenElement);
                if (!isFullscreen) {{
                    overlay.style.display = 'flex';
                }} else {{
                    overlay.style.display = 'none';
                }}
            }}
        }};
        
        // === EXIT FOCUS MODE (5 second delay) ===
        window.exitFocusMode = function() {{
            document.body.classList.remove('focus-mode');
            if (typeof window.adjustSVGSize === 'function') {{
                setTimeout(window.adjustSVGSize, 100); 
            }}
        }};
        
        // === SCENE LIFECYCLE - WAIT FOR IMAGE ===
        window.startSceneLifecycle = function() {{
            console.log('[Lifecycle] Starting scene lifecycle for:', window.currentScene);
            
            var img = document.getElementById('cameraImage');
            
            var initScene = function() {{
                console.log('[Lifecycle] Image ready, initializing visuals...');
                try {{
                    if (typeof window.initSceneVisuals === 'function') {{
                        window.initSceneVisuals();
                    }}
                }} catch(e) {{
                    console.error('[Lifecycle] initSceneVisuals error:', e);
                }}
                
                // Only check fullscreen if not transitioning
                if (!window.isTransitioning) {{
                    window.checkFullscreenStatus();
                }}
                
                // Schedule exit from focus mode
                setTimeout(function() {{
                    window.exitFocusMode();
                }}, 5000);
                
                // Clear transitioning flag after everything is set up
                window.isTransitioning = false;
            }};
            
            // Wait for image if not loaded
            if (img) {{
                if (img.complete && img.naturalWidth > 0) {{
                    initScene();
                }} else {{
                    console.log('[Lifecycle] Waiting for image to load...');
                    img.onload = initScene;
                    img.onerror = function() {{
                        console.warn('[Lifecycle] Image load error, proceeding anyway');
                        initScene();
                    }};
                    // Safety timeout
                    setTimeout(function() {{
                        if (window.isTransitioning !== false) {{
                            console.warn('[Lifecycle] Image timeout, forcing init');
                            initScene();
                        }}
                    }}, 10000);
                }}
            }} else {{
                initScene();
            }}
        }};
        
        // === INITIAL PAGE LOAD ===
        if (document.readyState === 'loading') {{
            window.addEventListener('load', window.startSceneLifecycle);
        }} else {{
            window.startSceneLifecycle();
        }}
        
        // === FULLSCREEN EVENT LISTENERS (only bind once) ===
        if (!window.fullscreenListenerBound) {{
            var fsHandler = function() {{
                // Delay check slightly to avoid race conditions
                setTimeout(function() {{
                    window.checkFullscreenStatus();
                }}, 100);
            }};
            document.addEventListener('fullscreenchange', fsHandler);
            document.addEventListener('webkitfullscreenchange', fsHandler);
            document.addEventListener('mozfullscreenchange', fsHandler);
            document.addEventListener('MSFullscreenChange', fsHandler);
            window.fullscreenListenerBound = true;
        }}
        
        // === RESUME BUTTON LISTENER (only bind once) ===
        if (!window.resumeBtnListenerBound) {{
            document.addEventListener('click', function(e) {{
                if (e.target && e.target.id === 'resume-btn') {{
                    var docEl = document.documentElement;
                    var requestFS = docEl.requestFullscreen || docEl.webkitRequestFullscreen || docEl.mozRequestFullScreen || docEl.msRequestFullscreen;
                    if (requestFS) {{
                        requestFS.call(docEl).then(function() {{
                            var overlay = document.getElementById('fullscreen-overlay');
                            if (overlay) overlay.style.display = 'none';
                        }}).catch(function(err) {{
                            console.error('[Fullscreen] Request failed:', err);
                        }});
                    }}
                }}
            }});
            window.resumeBtnListenerBound = true;
        }}
        
        // ==================== 图片预加载 ====================
        window.preloadedImages = window.preloadedImages || {{}};
        
        function preloadImages() {{
            fetch('/api/preload_images?count=3')
                .then(function(res) {{ return res.json(); }})
                .then(function(data) {{
                    if (data.urls && data.urls.length > 0) {{
                        console.log('[Preload] Starting to preload', data.urls.length, 'images');
                        data.urls.forEach(function(url, idx) {{
                            if (!window.preloadedImages[url]) {{
                                var img = new Image();
                                img.onload = function() {{
                                    console.log('[Preload] Cached:', url);
                                    window.preloadedImages[url] = true;
                                }};
                                img.onerror = function() {{
                                    console.warn('[Preload] Failed:', url);
                                }};
                                img.src = url;
                            }}
                        }});
                    }}
                }})
                .catch(function(err) {{ console.warn('[Preload] API error:', err); }});
        }}
        
        // 页面加载后 1 秒开始预加载
        setTimeout(preloadImages, 1000);
    """

    fullscreen_overlay_css = """
        #fullscreen-overlay {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.95);
            z-index: 9999;
            justify-content: center;
            align-items: center;
            flex-direction: column;
        }
        #fullscreen-overlay .overlay-content {
            text-align: center;
            color: white;
        }
        #fullscreen-overlay h2 {
            font-size: 28px;
            margin-bottom: 20px;
        }
        #fullscreen-overlay p {
            font-size: 16px;
            color: #aaa;
            margin-bottom: 30px;
        }
        #resume-btn {
            padding: 16px 48px;
            font-size: 18px;
            font-weight: 600;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            transition: background 0.2s;
        }
        #resume-btn:hover {
            background: #5a67d8;
        }
    """
    
    fs_title = get_text(lang, 'fullscreen.title')
    fs_message = get_text(lang, 'fullscreen.message')
    fs_button = get_text(lang, 'fullscreen.button')
    
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_title} - {current_idx}/{total_count}</title>
    <style>
        {common_css}
        {focus_mode_css}
        {fullscreen_overlay_css}
    </style>
</head>
<body class="focus-mode">
    <div id="fullscreen-overlay">
        <div class="overlay-content">
            <h2>{fs_title}</h2>
            <p>{fs_message}</p>
            <button id="resume-btn">{fs_button}</button>
        </div>
    </div>
    
    <div class="header">
        <h1>{header_text}</h1>
        <div class="progress-indicator">
            <span>{scene_progress}</span>
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
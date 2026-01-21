"""
UI Components
=============
Reusable HTML/CSS/JS components for the ownership annotation tool.
Modified: Button under slider, 2/3 Slider Width, Softer Gradient.
"""


def render_common_css():
    """
    Generate common CSS shared by both main and guide pages.
    """
    return """
        :root {
            --bg-color: #f4f6f8;
            --panel-bg: #ffffff;
            --text-primary: #1a1a1a;
            --text-secondary: #666666;
            --accent-black: #222222;
            --border-color: #e0e0e0;
            --shadow-sm: 0 2px 8px rgba(0,0,0,0.04);
            --shadow-md: 0 8px 24px rgba(0,0,0,0.08);
            --radius: 12px;
            
            /* CV Colors */
            --bbox-color: #00ffff; /* Cyan is high contrast */
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: var(--bg-color);
            color: var(--text-primary);
            height: 100vh; /* Full Viewport Height */
            display: flex;
            flex-direction: column;
            overflow: hidden; /* Disable Body Scroll */
        }
        
        /* === HEADER (COMPACT) === */
        .header {
            background: var(--panel-bg);
            padding: 10px 24px; /* Reduced padding to save vertical space */
            box-shadow: var(--shadow-sm);
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            z-index: 10;
            flex-shrink: 0;
            height: 60px; /* Fixed height to ensure stability */
        }
        
        .header h1 { 
            font-size: 18px; 
            font-weight: 700;
            color: var(--accent-black);
            display: flex;
            align-items: center;
            gap: 10px;
        }

        /* === LAYOUT (MAXIMIZED) === */
        .container {
            display: grid;
            grid-template-columns: 1fr 1fr; 
            gap: 16px; /* Reduced gap */
            padding: 12px; /* Minimal padding around the screen */
            flex: 1; /* Take all remaining vertical space */
            overflow: hidden;
            max-width: 100%; /* Use full width */
            margin: 0;
            width: 100%;
            height: calc(100vh - 60px); /* Explicit calculation helps mostly */
        }
        
        .panel {
            background: var(--panel-bg);
            border-radius: var(--radius);
            box-shadow: var(--shadow-sm);
            overflow: hidden;
            display: flex;
            flex-direction: column;
            border: 1px solid rgba(0,0,0,0.03);
            height: 100%; /* Fill the grid cell */
        }
        
        .panel-header {
            background: #ffffff;
            color: var(--accent-black);
            padding: 12px 20px; /* Compact header */
            font-size: 14px;
            font-weight: 700;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            gap: 8px;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            flex-shrink: 0;
        }
        
        /* === LEFT PANEL: CAMERA VIEW (FULL SIZE) === */
        .image-container {
            flex: 1;
            position: relative;
            background: #fafafa;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
            padding: 0; /* REMOVED PADDING: Image touches edges */
        }
        
        .camera-image {
            width: 100%;
            height: 100%;
            display: block;
            object-fit: contain; /* Magic property: Maximize size without cropping/scrolling */
        }
        
        .svg-overlay {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            pointer-events: none;
        }

        /* === DIMMING EFFECT === */
        body.dimmed-mode .object-polygon {
            opacity: 0.1; 
            stroke-width: 1;
            transition: all 0.3s ease;
        }
        
        body.dimmed-mode .object-polygon.active-spotlight {
            opacity: 1; 
            stroke-width: 4;
            filter: drop-shadow(0 0 8px var(--bbox-color));
            z-index: 10;
        }
        
        body.dimmed-mode .object-item {
            opacity: 0.4; 
            transition: all 0.3s ease;
        }
        
        body.dimmed-mode .object-item.active-spotlight {
            opacity: 1;
            transform: scale(1.01);
            box-shadow: 0 8px 24px rgba(0,0,0,0.12);
            z-index: 10;
            border-color: #000;
        }

        /* === BBOX STYLING === */
        .object-polygon {
            fill: rgba(0, 255, 255, 0.05);
            stroke: var(--bbox-color);     
            stroke-width: 2;
            cursor: pointer;
            pointer-events: all;
            transition: all 0.2s ease;
            stroke-dasharray: 4; 
            filter: drop-shadow(0 0 2px rgba(0,0,0,0.5));
        }
        
        .object-polygon:hover, .object-polygon.highlighted {
            fill: rgba(0, 255, 255, 0.2);
            stroke: #ffffff; 
            stroke-width: 3;
            stroke-dasharray: 0;
            filter: drop-shadow(0 0 5px var(--bbox-color));
        }

        /* Agent Labels */
        .agent-label {
            font-size: 60px; 
            font-family: 'Arial Black', sans-serif;
            font-weight: 900;
            text-anchor: middle;
            dominant-baseline: middle;
            pointer-events: none;
            fill: #000000; 
            paint-order: stroke;
            stroke: #ffffff;
            stroke-width: 6px;
            stroke-linejoin: round;
            filter: drop-shadow(0 2px 3px rgba(0,0,0,0.3));
            z-index: 100;
        }
        
        .agent-label-bg { display: none; } 
        
        .agent-hull {
            fill: none;
            stroke-width: 2px;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.2s;
        }

        /* === RIGHT PANEL: CONTROLS === */
        .matching-content {
            flex: 1;
            overflow-y: auto;
            padding: 20px; /* Reduced slightly */
            background: #f8f9fa;
        }
        
        .matching-content::-webkit-scrollbar { width: 8px; }
        .matching-content::-webkit-scrollbar-track { background: #f1f1f1; }
        .matching-content::-webkit-scrollbar-thumb { background: #ccc; border-radius: 4px; }
        .matching-content::-webkit-scrollbar-thumb:hover { background: #bbb; }
        
        .section-title {
            font-size: 12px;
            font-weight: 700;
            color: #999;
            margin-bottom: 12px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .object-list { 
            display: flex; 
            flex-direction: column; 
            gap: 16px; 
        }
        
        /* === CARD DESIGN === */
        .object-item {
            background: #ffffff;
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 20px;
            transition: all 0.2s cubic-bezier(0.25, 0.8, 0.25, 1);
            position: relative;
            box-shadow: 0 2px 6px rgba(0,0,0,0.02);
        }
        
        .object-item:hover, .object-item.highlighted {
            border-color: #000;
            transform: translateY(-2px);
            box-shadow: 0 8px 20px rgba(0,0,0,0.08);
        }
        
        .object-header-row {
            display: flex;
            justify-content: flex-start;
            align-items: baseline; 
            flex-wrap: wrap;       
            gap: 12px;
            margin-bottom: 12px;   
        }
        
        .object-name {
            font-size: 20px;
            font-weight: 700;
            color: #000;
            display: flex;
            align-items: center;
            gap: 8px;
            white-space: nowrap;
            -webkit-user-select: none;
            user-select: none;
            cursor: default;
        }
        
        .object-name::before {
            content: '';
            display: block;
            width: 8px;
            height: 8px;
            background: #000;
            border-radius: 50%;
        }

        .object-question-inline {
            font-size: 14px;
            color: #777;
            font-weight: 400;
            line-height: 1.4;
            -webkit-user-select: none;
            user-select: none;
            cursor: default;
        }

        /* === SLIDER AREA (FIXED: SEPARATED LABELS) === */
        .slider-container { padding: 0; }
        
        /* Grid Layout: [Label 80px] [Slider Space] [Label 80px] */
        .slider-row {
            display: grid;
            grid-template-columns: minmax(80px, max-content) 1fr minmax(80px, max-content);
            gap: 16px;
            align-items: center;
            margin-bottom: 12px;
            width: 100%;
        }
        
        .agent-label-text {
            font-size: 20px;
            font-weight: 700;
            text-align: center;
            color: #000;
            white-space: nowrap;
            -webkit-user-select: none; /* 兼容 Chrome/Safari */
            user-select: none;         /* 标准属性 */
            cursor: default;           /* 鼠标变成标准箭头，而不是文本输入的 I 型 */
        }
        
        /* Inside the middle column, restrict width to 70% to create "2/3" look */
        .slider-track-wrap {
            position: relative;
            width: 70%; 
            margin: 0 auto; /* Center in the middle column */
            height: 40px;
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
        }

        /* Slider Styling */
        .confidence-slider {
            -webkit-appearance: none;
            width: 100%;
            height: 8px;
            border-radius: 4px;
            background: linear-gradient(90deg, #363636 0%, #ffffff 50%, #363636 100%);
            border: 1px solid #ccc;
            outline: none;
            cursor: pointer;
            z-index: 2;
            margin-top: 5px;
        }
        
        .confidence-slider::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            background: #ffffff;
            border: 3px solid #363636; 
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            cursor: pointer;
            transition: transform 0.1s;
        }
        
        .confidence-slider::-webkit-slider-thumb:hover {
            transform: scale(1.15);
        }

        .slider-ticks {
            position: relative;
            width: 100%;
            height: 16px;
            margin-top: 8px;
        }

        .tick-label {
            position: absolute;
            font-size: 10px;
            font-family: 'Monaco', monospace;
            color: #999; /* 稍微变淡非主要刻度 */
            font-weight: 500; 
            transform: translateX(-50%);
            top: 0;
            white-space: nowrap; /* 防止文字换行 */
            -webkit-user-select: none;
            user-select: none;
        }
        
        .tick-label.middle {
            color: #999;         /* 改为灰色，与40/60一致 */
            font-weight: 500;    /* 改为正常粗细 */
            font-size: 11px;     /* 改为10px，与40/60一致 */
            font-family: 'Monaco', monospace; /* 改为等宽字体，与数字一致 */
            z-index: 2;
        }

        .tick-label.start { left: 0%; transform: translateX(0); }
        .tick-label.end { left: 100%; transform: translateX(-100%); }

        .confidence-value { display: none; }

        .button-row {
            display: flex;
            justify-content: center;
            margin-top: 4px;
        }

        .confirm-button {
            padding: 8px 32px;
            background: #f0f0f0;
            border: 1px solid #ccc;
            color: #333;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            white-space: nowrap;
        }
        
        .confirm-button:hover {
            background: #e0e0e0;
            border-color: #bbb;
        }
        
        .confirm-button.confirmed {
            background: #1a1a1a;
            color: #fff;
            border-color: #1a1a1a;
        }
        
        .confirmed-item {
            background: #fdfdfd;
            border-color: #888;
        }

        /* === FOOTER === */
        .submit-section {
            padding: 20px;
            background: #fff;
            border-top: 1px solid var(--border-color);
            flex-shrink: 0;
        }
        
        .submit-button {
            width: 100%;
            padding: 16px;
            background: #1a1a1a;
            color: #fff;
            border: none;
            border-radius: 12px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.1s, box-shadow 0.2s;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }
        
        .submit-button:hover {
            background: #000;
            transform: translateY(-1px);
        }
        
        .submit-button:disabled {
            background: #e0e0e0;
            color: #999;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        
        .status-message {
            margin-top: 15px;
            text-align: center;
            font-size: 13px;
            padding: 10px;
            border-radius: 8px;
            display: none;
        }
        .status-message.success { background: #f0fff4; color: #2f855a; }
        .status-message.error { background: #fff5f5; color: #c53030; }

        /* === MOBILE BLOCKER (新增) === */
        #mobile-blocker {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: #f4f6f8;
            z-index: 2147483647; /* 确保层级最高，盖住一切 */
            display: none; /* 默认隐藏，JS检测到才显示 */
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            padding: 30px;
        }
        #mobile-blocker .icon { font-size: 80px; margin-bottom: 24px; }
        #mobile-blocker h1 { font-size: 24px; color: #1a1a1a; margin-bottom: 16px; font-weight: 700; }
        #mobile-blocker p { font-size: 16px; color: #666; line-height: 1.6; max-width: 500px; }
        
        /* 额外的 CSS 媒体查询保险 (防止 JS 失效) */
        /* 如果屏幕宽度小于 768px (一般手机竖屏)，直接隐藏主要内容 */
        @media (max-width: 768px) {
            .container, .header { display: none !important; }
        }

    """


def render_left_panel_html(image_url, panel_header="📷 Camera View"):
    """
    Generate Left Panel HTML (Camera View).
    Added ID 'left-panel-wrapper' for focus mode control.
    """
    return f"""
        <div class="panel" id="left-panel-wrapper">
            <div class="panel-header">
                {panel_header}
            </div>
            <div class="image-container" id="imageContainer">
                <img src="{image_url}" alt="Camera View" class="camera-image" id="cameraImage">
                <svg class="svg-overlay" id="svgOverlay"></svg>
            </div>
        </div>
    """


def render_right_panel_html(submit_button_text="Save Assignments", submit_onclick="saveOwnerships()", panel_header="🎚️ Ownership Assignment"):
    """
    Generate Right Panel HTML (Object List).
    Added ID 'right-panel-wrapper' for focus mode control.
    """
    return f"""
        <div class="panel" id="right-panel-wrapper">
            <div class="panel-header">
                {panel_header}
            </div>
            <div class="matching-content">
                <div class="section">
                    <div class="section-title">Detected Objects</div>
                    <div class="object-list" id="objectList"></div>
                </div>
            </div>
            
            <div class="submit-section">
                <button class="submit-button" onclick="{submit_onclick}" disabled>
                    {submit_button_text}
                </button>
                <div class="status-message" id="statusMessage"></div>
            </div>
        </div>
    """


def render_core_script(objects_json, agents_json, agent_labels_json, include_save_function=True, lang='en', translations=None):
    """
    Generate core JavaScript.
    REFACTORED: Removed window.addEventListener('load') dependency for DOM swapping support.
    
    Args:
        objects_json: JSON string of objects data
        agents_json: JSON string of agents data
        agent_labels_json: JSON string of agent labels
        include_save_function: Whether to include the save function
        lang: Language code ('en' or 'zh')
        translations: Dict with translated strings (ownership_question, slider_unsure, confirm_button)
    """
    # Default translations
    if translations is None:
        translations = {
            'ownership_question': 'Who do you think this is more likely to belong to?' if lang == 'en' else '你认为这个物品更可能属于谁？',
            'slider_unsure': 'Unsure' if lang == 'en' else '不确定',
            'confirm_button': 'Confirm' if lang == 'en' else '确认',
            'locked_button': 'Locked' if lang == 'en' else '已锁定'
        }
    
    ownership_question = translations.get('ownership_question', 'Who do you think this is more likely to belong to?')
    slider_unsure = translations.get('slider_unsure', 'Unsure')
    confirm_text = translations.get('confirm_button', 'Confirm')
    locked_text = translations.get('locked_button', 'Locked')
    
    save_function = """
        function saveOwnerships() {
            var btn = document.querySelector('.submit-button');
            btn.textContent = 'Saving...';
            btn.disabled = true;
            
            // === CRITICAL: Set transitioning flag to protect fullscreen ===
            window.isTransitioning = true;
            
            var duration = (typeof window.startTime !== 'undefined') ? (Date.now() - window.startTime) : 0;
            var currentIdx = (typeof window.currentSceneIdx !== 'undefined') ? window.currentSceneIdx : 1;
            
            var payload = {
                scene: typeof window.currentScene !== 'undefined' ? window.currentScene : 'unknown',
                duration_ms: duration,
                timestamp: Date.now(),
                annotations: [],
                attention_failed: false
            };
            
            // Validate Attention Checks
            var attentionFailed = false;
            for (var objId in window.ownerships) {
                if (window.ownerships.hasOwnProperty(objId) && window.confirmations[objId] && objId.indexOf('attention_check_') === 0) {
                    var val = window.ownerships[objId].confidence;
                    var checkMeta = window.attentionCheckMeta ? window.attentionCheckMeta[objId] : null;
                    if (checkMeta) {
                        var passed = false;
                        if (checkMeta.target === 'left_0') passed = val < 5;
                        else if (checkMeta.target === 'right_100') passed = val > 95;
                        else if (checkMeta.target === 'gt_75') passed = val > 75;
                        else if (checkMeta.target === 'lt_25') passed = val < 25;
                        
                        if (!passed) {
                            attentionFailed = true;
                            // Strict Mode (scenes < 20): Immediate termination
                            // Grace Mode (scenes >= 20): Log and continue
                            if (currentIdx < 20) {
                                // Early attention failure - redirect to exit page
                                fetch('/save_ownerships', {
                                    method: 'POST',
                                    headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({ 
                                        status: 'failed_attention', 
                                        scene: payload.scene,
                                        current_idx: currentIdx  // Pass current index for server-side decision
                                    })
                                }).then(function(res) { return res.json(); }).then(function(data) {
                                    if (data.action === 'redirect') {
                                        // Redirect to exit page
                                        window.isTransitioning = false;
                                        window.location.href = data.url;
                                    } else if (data.action === 'reload') {
                                        // Grace mode - continue
                                        console.log('[Attention] Grace mode - continuing...');
                                        window.isTransitioning = false;
                                        btn.disabled = false;
                                        btn.textContent = 'Save & Next';
                                    }
                                }).catch(function(err) {
                                    console.error('[Attention Check] Network error:', err);
                                    window.isTransitioning = false;
                                    btn.disabled = false;
                                    btn.textContent = 'Save & Next';
                                });
                                return;
                            } else {
                                // Grace mode - allow continue with warning
                                console.log('[Attention] Grace mode - scene ' + currentIdx + ' - allowing continue');
                                payload.attention_failed = true;
                            }
                        }
                    }
                }
            }

            for (var objId2 in window.ownerships) {
                if (window.ownerships.hasOwnProperty(objId2) && window.confirmations[objId2]) {
                    payload.annotations.push({
                        object_id: objId2,
                        primary_owner_id: window.ownerships[objId2].owner,
                        confidence: window.ownerships[objId2].confidence,
                        agent_a_id: window.agentA.id,
                        agent_b_id: window.agentB.id,
                        slider_value: window.ownerships[objId2].confidence 
                    });
                }
            }

            fetch('/save_ownerships', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
            .then(function(response) { return response.json(); })
            .then(function(data) {
                if (data.status === 'success') {
                    if (data.action === 'redirect') {
                        // Completion or forced redirect - allowed to exit fullscreen
                        window.isTransitioning = false;
                        window.location.href = data.url;
                        return;
                    }
                    
                    if (data.action === 'reload') {
                        btn.textContent = 'Loading next scene...';
                        performSoftUpdate();
                    }
                } else {
                    window.isTransitioning = false;
                    btn.disabled = false;
                    btn.textContent = 'Save & Next';
                    console.error('[Save] Server error:', data.error);
                    showRetryMessage('Save failed. Please try again.');
                }
            })
            .catch(function(error) {
                console.error('[Save] Network error:', error);
                window.isTransitioning = false;
                btn.disabled = false;
                btn.textContent = 'Save & Next';
                showRetryMessage('Network error. Please check your connection and try again.');
            });
        }
        
        // === NON-INTRUSIVE ERROR MESSAGE ===
        function showRetryMessage(msg) {
            var statusDiv = document.querySelector('.status-message');
            if (statusDiv) {
                statusDiv.textContent = msg;
                statusDiv.className = 'status-message error';
                statusDiv.style.display = 'block';
                setTimeout(function() { statusDiv.style.display = 'none'; }, 5000);
            } else {
                console.warn('[UI] Status message element not found, alerting instead.');
                alert(msg);
            }
        }
        
        // === SOFT UPDATE WITH FULL PROTECTION ===
        function performSoftUpdate() {
            fetch('/', { method: 'GET', credentials: 'same-origin' })
                .then(function(res) { return res.text(); })
                .then(function(html) {
                    try {
                        var parser = new DOMParser();
                        var newDoc = parser.parseFromString(html, 'text/html');
                        
                        // === STEP 1: Update DOM (preserving fullscreen elements) ===
                        var oldHeader = document.querySelector('.header');
                        var newHeader = newDoc.querySelector('.header');
                        if (oldHeader && newHeader) {
                            oldHeader.innerHTML = newHeader.innerHTML;
                        }
                        
                        var oldContainer = document.querySelector('.container');
                        var newContainer = newDoc.querySelector('.container');
                        if (oldContainer && newContainer) {
                            oldContainer.innerHTML = newContainer.innerHTML;
                        }
                        
                        // === STEP 2: Preserve focus-mode class ===
                        var currentClasses = document.body.className.split(' ').filter(function(c) { return c.trim(); });
                        var newClasses = newDoc.body.className.split(' ').filter(function(c) { return c.trim(); });
                        var hasFocusMode = currentClasses.indexOf('focus-mode') !== -1;
                        var finalClasses = newClasses.slice();
                        if (hasFocusMode && finalClasses.indexOf('focus-mode') === -1) {
                            finalClasses.push('focus-mode');
                        }
                        // Remove dimmed-mode from previous scene
                        finalClasses = finalClasses.filter(function(c) { return c !== 'dimmed-mode'; });
                        document.body.className = finalClasses.join(' ');
                        
                        // === STEP 3: Extract scripts for later execution ===
                        var scriptsContent = [];
                        var scripts = newDoc.querySelectorAll('script');
                        scripts.forEach(function(s) {
                            if (s.textContent && s.textContent.trim()) {
                                scriptsContent.push(s.textContent);
                            }
                        });
                        
                        // === STEP 4: Wait for new image to load before executing scripts ===
                        var newImage = document.getElementById('cameraImage');
                        if (newImage) {
                            // Check if image is already cached/loaded
                            if (newImage.complete && newImage.naturalWidth > 0) {
                                console.log('[SoftUpdate] Image already loaded, executing scripts...');
                                executeNewScripts(scriptsContent);
                            } else {
                                // Wait for image to load
                                console.log('[SoftUpdate] Waiting for image to load...');
                                newImage.onload = function() {
                                    console.log('[SoftUpdate] Image loaded, executing scripts...');
                                    executeNewScripts(scriptsContent);
                                };
                                newImage.onerror = function() {
                                    console.error('[SoftUpdate] Image failed to load, executing scripts anyway...');
                                    executeNewScripts(scriptsContent);
                                };
                                // Safety timeout - execute after 8 seconds max
                                setTimeout(function() {
                                    if (window.isTransitioning) {
                                        console.warn('[SoftUpdate] Image load timeout, forcing script execution...');
                                        executeNewScripts(scriptsContent);
                                    }
                                }, 8000);
                            }
                        } else {
                            console.warn('[SoftUpdate] No cameraImage found, executing scripts...');
                            executeNewScripts(scriptsContent);
                        }
                        
                    } catch (parseErr) {
                        console.error('[SoftUpdate] DOM parsing error:', parseErr);
                        handleSoftUpdateError();
                    }
                })
                .catch(function(err) {
                    console.error('[SoftUpdate] Fetch failed:', err);
                    handleSoftUpdateError();
                });
        }
        
        // === SCRIPT EXECUTION WITH ERROR PROTECTION ===
        function executeNewScripts(scriptsContent) {
            try {
                // Clean up old script tags we may have added
                var oldInjectedScripts = document.querySelectorAll('script[data-injected="true"]');
                oldInjectedScripts.forEach(function(s) { s.remove(); });
                
                // Execute each script in a try-catch
                scriptsContent.forEach(function(content, idx) {
                    try {
                        var newScript = document.createElement('script');
                        newScript.setAttribute('data-injected', 'true');
                        newScript.textContent = content;
                        document.body.appendChild(newScript);
                    } catch (scriptErr) {
                        console.error('[SoftUpdate] Script ' + idx + ' execution error:', scriptErr);
                        // Don't break - continue with other scripts
                    }
                });
                
                // Mark transition complete
                window.isTransitioning = false;
                console.log('[SoftUpdate] Scene transition complete.');
                
            } catch (err) {
                console.error('[SoftUpdate] Script execution failed:', err);
                handleSoftUpdateError();
            }
        }
        
        // === ERROR HANDLER - NO RELOAD, JUST RETRY BUTTON ===
        function handleSoftUpdateError() {
            window.isTransitioning = false;
            var btn = document.querySelector('.submit-button');
            if (btn) {
                btn.disabled = false;
                btn.textContent = 'Retry';
            }
            showRetryMessage('Scene loading failed. Click Retry to try again.');
            // Do NOT call window.location.reload() - this would exit fullscreen!
        }
    """ if include_save_function else ""
    
    return f"""

        (function checkDeviceCompatibility() {{
            // 1. 检测 User Agent (是否是移动设备)
            const isMobileUA = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
            
            // 2. 检测屏幕宽度 (是否小于 1024px，通常 iPad 横屏或 PC 是 1024+)
            // 这里设置 900 是一个比较宽松的界限，防止误杀小屏笔记本
            const isSmallScreen = window.innerWidth < 900;
            
            if (isMobileUA || isSmallScreen) {{
                // 创建遮罩层
                const blocker = document.createElement('div');
                blocker.id = 'mobile-blocker';
                blocker.innerHTML = `
                    <div class="icon">💻</div>
                    <h1>Computer Only / 仅限电脑</h1>
                    <p><strong>Please open this link on a Computer (Desktop/Laptop).</strong><br>
                    This experiment requires a mouse and a large screen to function correctly.</p>
                    <div style="margin-top:20px; padding-top:20px; border-top:1px solid #ddd; width:100%; max-width:300px;">
                        <p style="font-size:14px;">本实验需要鼠标和大屏幕操作。<br>检测到您正在使用手机/平板或屏幕过小，已被禁止访问。</p>
                    </div>
                `;
                document.body.appendChild(blocker);
                blocker.style.display = 'flex';
                
                // 强制隐藏其他内容
                document.querySelectorAll('.container, .header').forEach(el => el.style.display = 'none');
                
                // 停止后续脚本执行 (抛出一个假错误终止执行)
                throw new Error("Mobile device detected - Experiment halted.");
            }}
        }})();

        // DATA INITIALIZATION
        // Note: Using var or assigning to window ensures variables persist/update correctly during swaps
        window.objects = {objects_json};
        window.agents = {agents_json};
        window.agentLabels = {agent_labels_json};
        window.ownerships = {{}};
        window.confirmations = {{}};
        
        window.agentA = window.agents[0] || {{ id: 'unknown', display_name: 'agent_a', color: '#000000' }};
        window.agentB = window.agents[1] || {{ id: 'unknown', display_name: 'agent_b', color: '#000000' }};
        
        // --- CORE INITIALIZATION FUNCTION ---
        // This function will be called by page_generators.py immediately
        window.initSceneVisuals = function() {{
            renderVisuals();
            populateObjectList();
            adjustSVGSize();
        }};
        
        window.addEventListener('resize', adjustSVGSize);
        
        function adjustSVGSize() {{
            const img = document.getElementById('cameraImage');
            const svg = document.getElementById('svgOverlay');
            if(img && svg) {{
                svg.style.width = img.clientWidth + 'px';
                svg.style.height = img.clientHeight + 'px';
                svg.setAttribute('width', img.clientWidth);
                svg.setAttribute('height', img.clientHeight);
                svg.setAttribute('viewBox', '0 0 4096 4096');
            }}
        }}
        
        function renderVisuals() {{
            // ... (Inside content remains exactly the same as before) ...
            const svg = document.getElementById('svgOverlay');
            if(!svg) return;
            svg.innerHTML = '';
            
            window.agents.forEach(agent => {{
                if (agent.hull && agent.hull.length >= 3) {{
                    const hull = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
                    const points = agent.hull.map(p => `${{p[0]}},${{p[1]}}`).join(' ');
                    hull.setAttribute('points', points);
                    hull.setAttribute('class', 'agent-hull');
                    hull.setAttribute('data-agent-id', agent.id);
                    hull.style.stroke = agent.color; 
                    svg.appendChild(hull);
                }}
            }});
            
            window.objects.forEach(obj => {{
                if (obj.is_attention_check) return;
                const polygon = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
                const points = obj.polygon.map(p => `${{p[0]}},${{p[1]}}`).join(' ');
                polygon.setAttribute('points', points);
                polygon.setAttribute('class', 'object-polygon');
                polygon.setAttribute('data-id', obj.id);
                polygon.addEventListener('mouseenter', () => {{ 
                    highlightObject(obj.id, true);
                    enableDimMode(obj.id);
                }});
                polygon.addEventListener('mouseleave', () => {{ 
                    highlightObject(obj.id, false);
                    disableDimMode();
                }});
                polygon.addEventListener('click', () => scrollToObject(obj.id));
                svg.appendChild(polygon);
            }});
            
            window.agentLabels.forEach(agent => {{
                const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                text.setAttribute('x', agent.x);
                text.setAttribute('y', agent.y);
                text.setAttribute('class', 'agent-label');
                text.textContent = agent.display_name || agent.label;
                svg.appendChild(text);
            }});
        }}
        
        function populateObjectList() {{
            // ... (Inside content remains exactly the same as before, just change objects to window.objects) ...
            const list = document.getElementById('objectList');
            if(!list) return;
            list.innerHTML = '';
            
            window.objects.forEach(obj => {{
                // ... (Keep existing item creation logic) ...
                // COPY ALL YOUR EXISTING populateObjectList CODE HERE
                // BUT MAKE SURE TO USE window.ownerships, window.agentA, etc.
                // ---------------------------------------------------------
                // Simulating the content for brevity in this answer, 
                // BUT YOU SHOULD KEEP THE FULL LOGIC from your previous file.
                // Just ensuring 'const objects' is accessed via 'window.objects' inside here
                
                const item = document.createElement('div');
                item.className = 'object-item';
                item.setAttribute('data-id', obj.id);

                // ... (Create Header) ...
                const headerRow = document.createElement('div');
                headerRow.className = 'object-header-row';
                const name = document.createElement('div');
                name.className = 'object-name';
                name.textContent = (obj.display_name || obj.label || obj.id || '').toString();
                
                const questionSpan = document.createElement('span');
                questionSpan.className = 'object-question-inline';
                if (obj.is_attention_check && obj.question) {{
                    questionSpan.textContent = obj.question;
                }} else {{
                    questionSpan.textContent = `{ownership_question}`;
                }}
                
                headerRow.appendChild(name);
                headerRow.appendChild(questionSpan);

                // ... (Create Slider) ...
                const sliderContainer = document.createElement('div');
                sliderContainer.className = 'slider-container';
                const sliderRow = document.createElement('div');
                sliderRow.className = 'slider-row';

                const labelLeft = document.createElement('div');
                labelLeft.className = 'agent-label-text';
                // labelLeft.textContent = window.agentA.display_name;
                if (obj.is_attention_check) {{
                    labelLeft.textContent = '0'; // 或者 'Left'
                    labelLeft.style.color = '#999'; // 稍微变灰一点，表示这是刻度而非人名
                }} else {{
                    labelLeft.textContent = window.agentA.display_name;
                }}

                const trackWrap = document.createElement('div');
                trackWrap.className = 'slider-track-wrap';

                const slider = document.createElement('input');
                slider.type = 'range';
                slider.className = 'confidence-slider';
                slider.min = '0';
                slider.max = '100';
                slider.value = '50';

                const ticksContainer = document.createElement('div');
                ticksContainer.className = 'slider-ticks';
                for (let t = 0; t <= 100; t += 10) {{
                    const tick = document.createElement('div');
                    if (t === 50) {{
                        tick.className = 'tick-label middle';
                        tick.textContent = "{slider_unsure}";
                    }} else {{  
                        tick.className = 'tick-label' + (t === 0 ? ' start' : (t === 100 ? ' end' : ''));
                        tick.textContent = String(t);
                    }}
                    tick.style.left = `${{t}}%`;
                    ticksContainer.appendChild(tick);
                }}
                
                trackWrap.appendChild(slider);
                trackWrap.appendChild(ticksContainer);

                const labelRight = document.createElement('div');
                labelRight.className = 'agent-label-text';
                // labelRight.textContent = window.agentB.display_name;
                if (obj.is_attention_check) {{
                    labelRight.textContent = '100'; // 或者 'Right'
                    labelRight.style.color = '#999';
                }} else {{
                    labelRight.textContent = window.agentB.display_name;
                }}

                const confirmBtn = document.createElement('button');
                confirmBtn.className = 'confirm-button';
                // Default button shows "50" (or Unsure text for value 50)
                confirmBtn.innerHTML = '<span>○</span> {slider_unsure}'; 
                
                const buttonRow = document.createElement('div');
                buttonRow.className = 'button-row';
                buttonRow.appendChild(confirmBtn);

                // Helper: Update button text based on value
                const updateButtonText = (value, isLocked) => {{
                    if (isLocked) {{
                        // Locked state: show checkmark + value
                        const displayText = (value === 50) ? '{slider_unsure}' : value;
                        confirmBtn.innerHTML = `<span>✓</span> ${{displayText}}`;
                    }} else {{
                        // Unlocked state: show circle + value
                        const displayText = (value === 50) ? '{slider_unsure}' : value;
                        confirmBtn.innerHTML = `<span>○</span> ${{displayText}}`;
                    }}
                }};

                // Listeners
                slider.addEventListener('input', (e) => {{
                    const value = parseInt(e.target.value);
                    if (value < 50) {{
                        window.ownerships[obj.id] = {{ owner: window.agentA.id, confidence: value }};
                    }} else {{
                        window.ownerships[obj.id] = {{ owner: window.agentB.id, confidence: value }};
                    }}
                    
                    // Dynamic button label: show current value while dragging
                    updateButtonText(value, false);
                    
                    // Hull opacity logic
                    document.querySelectorAll('.agent-hull').forEach(h => h.style.opacity = 0);
                    let targetAgent = (value < 50) ? window.agentA : (value > 50 ? window.agentB : null);
                    if(targetAgent) {{
                         const th = document.querySelector(`.agent-hull[data-agent-id="${{targetAgent.id}}"]`);
                         if(th) th.style.opacity = Math.abs(value - 50) / 50;
                    }}
                }});
                
                // Auto-lock on slider release (change event)
                // CRITICAL: This MUST fire for ALL values including 50 (Unsure)
                slider.addEventListener('change', (e) => {{
                    const value = parseInt(e.target.value);
                    
                    // ALWAYS record ownership, even for value 50
                    // For value 50, we treat it as "unsure" but still a valid decision
                    if (value < 50) {{
                        window.ownerships[obj.id] = {{ owner: window.agentA.id, confidence: value }};
                    }} else if (value > 50) {{
                        window.ownerships[obj.id] = {{ owner: window.agentB.id, confidence: value }};
                    }} else {{
                        // value === 50: Explicitly unsure, but still a valid choice
                        window.ownerships[obj.id] = {{ owner: null, confidence: 50 }};
                    }}
                    
                    // ALWAYS auto-lock on release, regardless of value
                    window.confirmations[obj.id] = true;
                    confirmBtn.classList.add('confirmed');
                    updateButtonText(value, true);
                    slider.disabled = true;
                    item.classList.add('confirmed-item');
                    disableDimMode();
                    checkAllConfirmed();
                }});

                slider.addEventListener('mousedown', () => {{ enableDimMode(obj.id); }});
                slider.addEventListener('mouseup', () => {{ disableDimMode(); }});
                slider.addEventListener('touchstart', () => {{ enableDimMode(obj.id); }});
                slider.addEventListener('touchend', () => {{ disableDimMode(); }});

                // Toggle logic: Click to Unlock (if locked) or Lock (if unlocked)
                confirmBtn.addEventListener('click', () => {{
                    const currentValue = parseInt(slider.value);
                    if (window.confirmations[obj.id]) {{
                        // Currently locked -> Unlock
                        window.confirmations[obj.id] = false;
                        confirmBtn.classList.remove('confirmed');
                        updateButtonText(currentValue, false);
                        slider.disabled = false;
                        item.classList.remove('confirmed-item');
                    }} else {{
                        // Currently unlocked -> Lock (for users who want to confirm 50/Unsure without dragging)
                        if (!window.ownerships[obj.id]) {{
                            window.ownerships[obj.id] = {{ owner: null, confidence: 50 }};
                        }}
                        window.confirmations[obj.id] = true;
                        confirmBtn.classList.add('confirmed');
                        updateButtonText(currentValue, true);
                        slider.disabled = true;
                        item.classList.add('confirmed-item');
                    }}
                    checkAllConfirmed();
                }});

                sliderRow.appendChild(labelLeft);
                sliderRow.appendChild(trackWrap);
                sliderRow.appendChild(labelRight);
                sliderContainer.appendChild(sliderRow);
                sliderContainer.appendChild(buttonRow);
                item.appendChild(headerRow);
                item.appendChild(sliderContainer);
                
                if (!obj.is_attention_check) {{
                    item.addEventListener('mouseenter', () => {{ 
                        highlightObject(obj.id, true);
                        enableDimMode(obj.id);
                    }});
                    item.addEventListener('mouseleave', () => {{ 
                        highlightObject(obj.id, false);
                        disableDimMode();
                    }});
                }}
                list.appendChild(item);
            }});
            checkAllConfirmed();
        }}
        
        function checkAllConfirmed() {{
            const totalCount = window.objects.length;
            const confirmedCount = Object.values(window.confirmations).filter(v => v === true).length;
            const saveBtn = document.querySelector('.submit-button');
            if (saveBtn) {{
                saveBtn.disabled = !(confirmedCount === totalCount && totalCount > 0);
            }}
        }}

        function highlightObject(objectId, highlight) {{
            const polygon = document.querySelector(`.object-polygon[data-id="${{objectId}}"]`);
            const listItem = document.querySelector(`.object-item[data-id="${{objectId}}"]`);
            if (polygon) polygon.classList.toggle('highlighted', highlight);
            if (listItem) listItem.classList.toggle('highlighted', highlight);
        }}
        
        function enableDimMode(activeObjectId) {{
            document.body.classList.add('dimmed-mode');
            const polygon = document.querySelector(`.object-polygon[data-id="${{activeObjectId}}"]`);
            const listItem = document.querySelector(`.object-item[data-id="${{activeObjectId}}"]`);
            if (polygon) polygon.classList.add('active-spotlight');
            if (listItem) listItem.classList.add('active-spotlight');
        }}
        
        function disableDimMode() {{
            document.body.classList.remove('dimmed-mode');
            document.querySelectorAll('.active-spotlight').forEach(el => el.classList.remove('active-spotlight'));
        }}
        
        function scrollToObject(objectId) {{
            const item = document.querySelector(`.object-item[data-id="${{objectId}}"]`);
            if (item) {{
                item.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                item.classList.add('highlighted');
                setTimeout(() => item.classList.remove('highlighted'), 2000);
            }}
        }}

        {save_function}
    """


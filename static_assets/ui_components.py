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
            color: #000000; 
            font-weight: 700; 
            transform: translateX(-50%);
            top: 0;
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
    """


def render_left_panel_html(image_url):
    """
    Generate Left Panel HTML (Camera View).
    """
    return f"""
        <div class="panel">
            <div class="panel-header">
                <span>📷</span> Camera View
            </div>
            <div class="image-container" id="imageContainer">
                <img src="{image_url}" alt="Camera View" class="camera-image" id="cameraImage">
                <svg class="svg-overlay" id="svgOverlay"></svg>
            </div>
        </div>
    """


def render_right_panel_html(submit_button_text="Save Assignments", submit_onclick="saveOwnerships()"):
    """
    Generate Right Panel HTML (Object List).
    """
    return f"""
        <div class="panel">
            <div class="panel-header">
                <span>📝</span> Ownership Assignment
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


def render_core_script(objects_json, agents_json, agent_labels_json, include_save_function=True):
    """
    Generate core JavaScript.
    """
    save_function = """
            
        function saveOwnerships() {
            const btn = document.querySelector('.submit-button');
            btn.textContent = 'Saving...';
            btn.disabled = true;
            
            // 计算耗时
            const duration = (typeof startTime !== 'undefined') ? (Date.now() - startTime) : 0;
            
            const payload = {
                scene: typeof currentScene !== 'undefined' ? currentScene : 'unknown',
                duration_ms: duration, // 发送耗时
                timestamp: Date.now(), // 点击保存的时间点
                annotations: []
            };

            for (const [objId, data] of Object.entries(ownerships)) {
                if (confirmations[objId]) {
                    payload.annotations.push({
                        object_id: objId,
                        primary_owner_id: data.owner,
                        confidence: data.confidence,
                        agent_a_id: agentA.id,
                        agent_b_id: agentB.id,
                        slider_value: data.confidence 
                    });
                }
            }

            fetch('/save_ownerships', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // ★ 修改这里：如果服务器要求 reload，则刷新页面
                    if (data.action === 'reload') {
                        btn.textContent = 'Saved! Loading next...';
                        window.location.reload(); // 刷新 -> 服务器路由 index() -> 发送下一个场景
                    } else {
                        // 原有的逻辑
                        const statusMsg = document.getElementById('statusMessage');
                        statusMsg.textContent = 'Saved successfully!';
                        statusMsg.className = 'status-message success';
                        statusMsg.style.display = 'block';
                    }
                } else {
                    // Error handling...
                    btn.disabled = false;
                    btn.textContent = 'Save & Next';
                    alert('Error saving: ' + data.error);
                }
            })
            .catch(error => {
                btn.disabled = false;
                btn.textContent = 'Save & Next';
                alert('Network Error');
            });
        }

    """ if include_save_function else ""
    
    return f"""
        const objects = {objects_json};
        const agents = {agents_json};
        const agentLabels = {agent_labels_json};
        const ownerships = {{}};
        const confirmations = {{}};
        
        let agentA = agents[0] || {{ id: 'unknown', display_name: 'agent_a', color: '#000000' }};
        let agentB = agents[1] || {{ id: 'unknown', display_name: 'agent_b', color: '#000000' }};
        
        window.addEventListener('load', () => {{
            renderVisuals();
            populateObjectList();
            adjustSVGSize();
        }});
        
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
            const svg = document.getElementById('svgOverlay');
            if(!svg) return;
            svg.innerHTML = '';
            
            // Agents Hulls
            agents.forEach(agent => {{
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
            
            // Objects
            objects.forEach(obj => {{
                const polygon = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
                const points = obj.polygon.map(p => `${{p[0]}},${{p[1]}}`).join(' ');
                polygon.setAttribute('points', points);
                polygon.setAttribute('class', 'object-polygon');
                polygon.setAttribute('data-id', obj.id);
                
                // Add dim mode logic here
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
            
            // Agent Labels
            agentLabels.forEach(agent => {{
                const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                text.setAttribute('x', agent.x);
                text.setAttribute('y', agent.y);
                text.setAttribute('class', 'agent-label');
                text.textContent = agent.display_name || agent.label;
                svg.appendChild(text);
            }});
        }}
        
        function populateObjectList() {{
            const list = document.getElementById('objectList');
            if(!list) return;
            list.innerHTML = '';
            
            objects.forEach(obj => {{
                const item = document.createElement('div');
                item.className = 'object-item';
                item.setAttribute('data-id', obj.id);
                
                // Header Row (Flex)
                const headerRow = document.createElement('div');
                headerRow.className = 'object-header-row';
                
                const name = document.createElement('div');
                name.className = 'object-name';
                const objLabel = (obj.display_name || obj.label || obj.id || '').toString();
                name.textContent = objLabel;
                
                // Question Inline
                const questionSpan = document.createElement('span');
                questionSpan.className = 'object-question-inline';
                questionSpan.textContent = `Who do you think the ${{objLabel}} is more likely to belong to?`;
                
                headerRow.appendChild(name);
                headerRow.appendChild(questionSpan);
                
                // Slider Section
                const sliderContainer = document.createElement('div');
                sliderContainer.className = 'slider-container';
                
                const sliderRow = document.createElement('div');
                sliderRow.className = 'slider-row';
                
                const labelLeft = document.createElement('div');
                labelLeft.className = 'agent-label-text';
                labelLeft.textContent = agentA.display_name;
                
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
                    tick.className = 'tick-label' + (t === 0 ? ' start' : (t === 100 ? ' end' : ''));
                    tick.textContent = String(t);
                    tick.style.left = `${{t}}%`;
                    ticksContainer.appendChild(tick);
                }}
                
                trackWrap.appendChild(slider);
                trackWrap.appendChild(ticksContainer);
                
                const labelRight = document.createElement('div');
                labelRight.className = 'agent-label-text';
                labelRight.textContent = agentB.display_name;
                
                const confirmBtn = document.createElement('button');
                confirmBtn.className = 'confirm-button';
                confirmBtn.innerHTML = '<span>○</span> Confirm'; 
                confirmBtn.setAttribute('data-id', obj.id);
                
                // Button Row
                const buttonRow = document.createElement('div');
                buttonRow.className = 'button-row';
                buttonRow.appendChild(confirmBtn);

                // Slider Logic
                slider.addEventListener('input', (e) => {{
                    const value = parseInt(e.target.value);
                    
                    if (value < 50) {{
                        ownerships[obj.id] = {{ owner: agentA.id, confidence: value }};
                    }} else {{
                        ownerships[obj.id] = {{ owner: agentB.id, confidence: value }};
                    }}
                    
                    document.querySelectorAll('.agent-hull').forEach(h => h.style.opacity = 0);
                    let targetAgent = (value < 50) ? agentA : (value > 50 ? agentB : null);
                    if(targetAgent) {{
                         const th = document.querySelector(`.agent-hull[data-agent-id="${{targetAgent.id}}"]`);
                         if(th) th.style.opacity = Math.abs(value - 50) / 50;
                    }}
                }});
                
                // Add dim mode when adjusting slider
                slider.addEventListener('mousedown', () => {{ enableDimMode(obj.id); }});
                slider.addEventListener('mouseup', () => {{ disableDimMode(); }});
                slider.addEventListener('touchstart', () => {{ enableDimMode(obj.id); }});
                slider.addEventListener('touchend', () => {{ disableDimMode(); }});
                
                confirmBtn.addEventListener('click', () => {{
                    if (confirmations[obj.id]) {{
                        confirmations[obj.id] = false;
                        confirmBtn.classList.remove('confirmed');
                        confirmBtn.innerHTML = '<span>○</span> Confirm';
                        slider.disabled = false;
                        item.classList.remove('confirmed-item');
                    }} else {{
                        confirmations[obj.id] = true;
                        confirmBtn.classList.add('confirmed');
                        confirmBtn.innerHTML = '<span>●</span> Locked';
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
                
                // Add dim mode logic for item hover
                item.addEventListener('mouseenter', () => {{ 
                    highlightObject(obj.id, true);
                    enableDimMode(obj.id);
                }});
                item.addEventListener('mouseleave', () => {{ 
                    highlightObject(obj.id, false);
                    disableDimMode();
                }});

                list.appendChild(item);
            }});
            
            checkAllConfirmed();
        }}
        
        function checkAllConfirmed() {{
            const totalCount = objects.length;
            const confirmedCount = Object.values(confirmations).filter(v => v === true).length;
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
        
        // --- NEW DIMMING FUNCTIONS ---
        function enableDimMode(activeObjectId) {{
            document.body.classList.add('dimmed-mode');
            
            const polygon = document.querySelector(`.object-polygon[data-id="${{activeObjectId}}"]`);
            const listItem = document.querySelector(`.object-item[data-id="${{activeObjectId}}"]`);
            
            if (polygon) polygon.classList.add('active-spotlight');
            if (listItem) listItem.classList.add('active-spotlight');
        }}
        
        function disableDimMode() {{
            document.body.classList.remove('dimmed-mode');
            document.querySelectorAll('.active-spotlight').forEach(el => {{
                el.classList.remove('active-spotlight');
            }});
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


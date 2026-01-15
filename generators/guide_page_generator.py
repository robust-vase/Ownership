"""
Guide Page Generator
====================
Dual-Scene Tutorial with Turing Test Validation.
REFACTORED: Now uses centralized data_processor for scene processing.
"""
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.data_processor import process_scene_data
from static_assets.ui_components import render_common_css, render_left_panel_html, render_right_panel_html, render_core_script

def generate_guide_html(ctx_1, ctx_2, ctx_3): # 接收三个场景
    """Entry point to generate the HTML."""
    
    # 定义处理函数
    def proc(ctx):
        if not ctx: return [], [], []
        return process_scene_data(ctx['scene_data'], ctx['camera_data'], use_display_mapping=False, filter_empty_plates=False)

    # 处理数据
    obj1, agt1, lbl1 = proc(ctx_1)
    obj2, agt2, lbl2 = proc(ctx_2)
    obj3, agt3, lbl3 = proc(ctx_3) # 处理场景 3
    
    # 转 JSON
    scene1_json = json.dumps({'objects': obj1, 'agents': agt1, 'agent_labels': lbl1, 'image_url': ctx_1['image_url']}, ensure_ascii=False)
    scene2_json = json.dumps({'objects': obj2, 'agents': agt2, 'agent_labels': lbl2, 'image_url': ctx_2['image_url']}, ensure_ascii=False)
    scene3_json = json.dumps({'objects': obj3, 'agents': agt3, 'agent_labels': lbl3, 'image_url': ctx_3['image_url']}, ensure_ascii=False)

    return _build_tutorial_template(scene1_json, scene2_json, scene3_json)


def _build_tutorial_template(scene1_json, scene2_json, scene3_json):
    common_css = render_common_css()
    
    # 这里的 left_panel 内容会被 loadScene 动态替换，但 ID 必须正确
    left_panel = """
        <div class="panel" id="left-panel-wrapper">
            <div class="panel-header">📷 Camera View</div>
            <div class="image-container" id="imageContainer">
                <img src="" alt="Camera View" class="camera-image" id="cameraImage">
                <svg class="svg-overlay" id="svgOverlay"></svg>
            </div>
        </div>
    """
    
    # 右侧面板结构
    right_panel = """
        <div class="panel" id="right-panel-wrapper">
            <div class="panel-header">🎚️ Ownership Assignment</div>
            <div class="matching-content" id="matching-content">
                <div class="section">
                    <div class="section-title">Visible Objects</div>
                    <div class="object-list" id="objectList"></div>
                </div>
            </div>
            <div class="submit-section" id="submit-section">
                <button class="submit-button" id="submit-btn" disabled>Save Assignments</button>
            </div>
        </div>
    """
    
    # 初始化核心脚本（先给空数组，避免未定义错误）
    core_script = render_core_script("[]", "[]", "[]", include_save_function=False)

    # === 合并 CSS: Tutorial CSS + Focus Mode CSS ===
    tutorial_css = """
        /* === FOCUS MODE CSS (Copied from page_generators.py) === */
        /* 1. 改变布局容器：从 Grid 变为 Flex 居中 */
        body.focus-mode .container { display: flex; justify-content: center; align-items: center; height: 100vh; padding: 0; margin: 0; width: 100vw; }
        /* 2. 隐藏干扰元素 */
        body.focus-mode #right-panel-wrapper { display: none !important; }
        body.focus-mode .header { display: none !important; }
        body.focus-mode #svgOverlay { display: none !important; }
        /* 3. 左侧面板样式 */
        body.focus-mode #left-panel-wrapper { width: auto; height: 100%; max-width: 100%; background: transparent; border: none; box-shadow: none; border-radius: 0; display: flex; flex-direction: column; justify-content: center; }
        body.focus-mode #left-panel-wrapper .panel-header { display: none; }
        /* 4. 图片容器 */
        body.focus-mode #imageContainer { background: transparent; height: 100%; display: flex; align-items: center; justify-content: center; }
        body.focus-mode img.camera-image { height: 98vh; width: auto; max-width: 98vw; object-fit: contain; box-shadow: 0 0 50px rgba(0,0,0,0.1); }

        /* === TUTORIAL SPECIFIC CSS === */
        #tutorial-backdrop { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); backdrop-filter: blur(5px); z-index: 9998; display: none; transition: all 0.4s ease; }
        #tutorial-backdrop.active { display: block; }
        
        #tutorial-modal { position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background: white; border-radius: 16px; box-shadow: 0 20px 60px rgba(0,0,0,0.5); z-index: 11000; max-width: 600px; width: 90%; max-height: 85vh; overflow-y: auto; display: none; transition: all 0.4s ease; }
        #tutorial-modal.active { display: block; animation: modalFadeIn 0.4s ease; }
        @keyframes modalFadeIn { from { opacity: 0; transform: translate(-50%, -45%); } to { opacity: 1; transform: translate(-50%, -50%); } }
        
        .modal-header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 24px 32px; border-radius: 16px 16px 0 0; }
        .modal-step-badge { background: rgba(255,255,255,0.25); padding: 6px 14px; border-radius: 16px; font-size: 13px; font-weight: 700; display: inline-block; margin-bottom: 12px; }
        .modal-title { font-size: 26px; font-weight: 700; margin: 0; line-height: 1.3; }
        .modal-content { padding: 32px; }
        .modal-text { font-size: 16px; line-height: 1.8; color: #333; margin-bottom: 20px; }
        .modal-actions { padding: 24px 32px; border-top: 1px solid #eee; display: flex; justify-content: flex-end; }
        
        .tutorial-btn { padding: 12px 24px; border: none; border-radius: 8px; font-size: 16px; font-weight: 600; cursor: pointer; transition: all 0.2s; }
        .tutorial-btn-primary { background: #667eea; color: white; }
        .tutorial-btn-primary:hover { background: #5568d3; }
        
        .concept-comparison { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 24px 0; }
        .concept-card { border: 2px solid #e0e0e0; border-radius: 12px; padding: 16px; text-align: center; }
        .concept-card.wrong { border-color: #ff6b6b; background: #fff5f5; }
        .concept-card.correct { border-color: #51cf66; background: #f0fff4; }
        
        /* Visibility Classes */
        #left-panel-wrapper { position: relative; z-index: 1; transition: none; }
        body.left-panel-visible #left-panel-wrapper { z-index: 10000; opacity: 1 !important; box-shadow: 0 0 30px rgba(0,0,0,0.3); }
        body.spotlight-mode #right-panel-wrapper { opacity: 0.1; pointer-events: none; transition: opacity 0.3s; }
        
        /* Specific Steps */
        body.step-3 #tutorial-modal { left: auto !important; right: 5% !important; transform: translateY(-50%) !important; top: 50% !important; max-width: 450px; }
        body.step-8-modal #tutorial-modal { left: auto !important; right: 5% !important; transform: translateY(-50%) !important; top: 50% !important; max-width: 500px; }
        
        body.step-4 #right-panel-wrapper { opacity: 1; }
        body.step-4 #objectList { opacity: 1; }
        body.step-4 .object-item { opacity: 0.1; pointer-events: none; filter: blur(2px); }
        body.step-4 .object-item:first-child { opacity: 1 !important; pointer-events: auto !important; filter: none !important; position: relative; z-index: 10005; background: white; box-shadow: 0 0 0 4px #667eea, 0 0 50px rgba(0,0,0,0.5); transform: scale(1.02); }
        
        body.step-5 #right-panel-wrapper, body.step-8 #right-panel-wrapper { opacity: 1 !important; pointer-events: auto !important; z-index: 9990; }
        
        body.step-6 #right-panel-wrapper { opacity: 1 !important; pointer-events: auto !important; }
        body.step-6 .matching-content { opacity: 0.3; }
        body.step-6 #submit-section { position: relative; z-index: 10005; opacity: 1 !important; pointer-events: auto !important; background: white; box-shadow: 0 0 0 1000px rgba(0,0,0,0.85); border-radius: 8px; }
        
        .tutorial-tooltip { position: fixed; background: white; padding: 20px 24px; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.2); z-index: 11000; max-width: 350px; display: none; }
        .tutorial-tooltip.active { display: block; animation: tooltipFadeIn 0.3s ease; }
        @keyframes tooltipFadeIn { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }
        
        .quiz-section { margin: 20px 0; }
        .quiz-question { font-size: 15px; font-weight: 600; color: #333; margin-bottom: 12px; }
        .quiz-options { display: flex; gap: 12px; margin-bottom: 8px; }
        .quiz-option { flex: 1; padding: 10px 16px; border: 2px solid #e0e0e0; border-radius: 8px; background: white; cursor: pointer; text-align: center; font-weight: 500; transition: all 0.2s; }
        .quiz-option:hover { border-color: #667eea; background: #f8f9ff; }
        .quiz-option.selected { border-color: #667eea; background: #667eea; color: white; }
        .quiz-error { color: #ff6b6b; font-size: 13px; font-weight: 600; margin-top: 5px; display: none; }
        .quiz-error.active { display: block; }
    """

    tutorial_script = f"""
        const scene1Data = {scene1_json};
        const scene2Data = {scene2_json};
        const scene3Data = {scene3_json}; // Simulation Data
        
        let currentStep = 0;
        let currentSceneIndex = 1;
        
        window.addEventListener('load', () => {{
            loadScene(1);
            initTutorial();
            
            window.addEventListener('resize', () => {{
                if (currentStep === 4) positionTooltipForStep4();
                if (currentStep === 6) positionTooltipForStep6();
            }});
        }});
        
        function loadScene(index) {{
            console.log("Loading Scene " + index);
            currentSceneIndex = index;
            let data;
            if (index === 1) data = scene1Data;
            else if (index === 2) data = scene2Data;
            else data = scene3Data;
            
            if (typeof objects !== 'undefined' && Array.isArray(objects)) {{
                objects.length = 0;
                objects.push(...data.objects);
            }}
            
            if (typeof agents !== 'undefined' && Array.isArray(agents)) {{
                agents.length = 0;
                agents.push(...data.agents);
            }}
            
            if (typeof agentLabels !== 'undefined' && Array.isArray(agentLabels)) {{
                agentLabels.length = 0;
                agentLabels.push(...data.agent_labels);
            }}
            
            if (agents.length >= 2) {{
                agentA = agents[0];
                agentB = agents[1];
            }}
            
            if (typeof confirmations !== 'undefined') {{
                for (const prop of Object.keys(confirmations)) delete confirmations[prop];
            }}
            if (typeof ownerships !== 'undefined') {{
                for (const prop of Object.keys(ownerships)) delete ownerships[prop];
            }}

            const img = document.getElementById('cameraImage');
            if (img) img.src = data.image_url;
            
            const list = document.getElementById('objectList');
            if (list) list.innerHTML = '';
            const svg = document.getElementById('svgOverlay');
            if (svg) svg.innerHTML = '';
            
            if (typeof renderVisuals === 'function') renderVisuals();
            if (typeof populateObjectList === 'function') populateObjectList();
            if (typeof adjustSVGSize === 'function') adjustSVGSize();
            if (typeof updateSubmitButton === 'function') checkAllConfirmed(); // Important: reset button state
        }}
        
        function initTutorial() {{ showStep(1); }}
        
        function showStep(step) {{
            currentStep = step;
            const backdrop = document.getElementById('tutorial-backdrop');
            const modal = document.getElementById('tutorial-modal');
            const tooltip = document.getElementById('tutorial-tooltip');
            const stepBadge = document.getElementById('step-badge');
            const stepTitle = document.getElementById('step-title');
            const stepContent = document.getElementById('step-content');
            const nextBtn = document.getElementById('next-btn');
            
            // Clean slate
            document.body.className = ''; 
            modal.style.left = ''; modal.style.transform = ''; modal.style.right = '';
            if (tooltip) tooltip.classList.remove('active');
            nextBtn.style.display = 'block';
            nextBtn.disabled = false;
            
            // --- Steps 1-8 (Keep as is, simplified for brevity here) ---
            if (step === 1) {{
                backdrop.classList.add('active'); modal.classList.add('active');
                stepBadge.textContent = 'Step 1 / 11'; // Update total count
                stepTitle.innerHTML = 'Welcome';
                stepContent.innerHTML = `<p class="modal-text">Welcome to the <strong>Ownership Cognition Experiment</strong>.<br>For the best experience, switch to full screen.</p>`;
                nextBtn.textContent = 'Enter Fullscreen';
                nextBtn.onclick = () => {{
                    if (document.documentElement.requestFullscreen) {{
                        document.documentElement.requestFullscreen().catch(e=>{{}});
                    }}
                    showStep(2);
                }};
            }} else if (step === 2) {{
                backdrop.classList.add('active'); modal.classList.add('active');
                stepBadge.textContent = 'Step 2 / 11';
                stepTitle.innerHTML = 'Visual Judgment';
                stepContent.innerHTML = `
                    <p class="modal-text">We focus on <strong>Psychological Ownership</strong> based on visual intuition.</p>
                    <div class="concept-comparison">
                        <div class="concept-card wrong"><div>🚫</div><div>No External Clues</div><div style="font-size:12px;color:#888">Don't guess who bought it</div></div>
                        <div class="concept-card correct"><div>👓</div><div>Visual Intuition</div><div style="font-size:12px;color:#888">Judge based on the image</div></div>
                    </div>
                `;
                nextBtn.textContent = 'I Understand';
                nextBtn.onclick = () => showStep(3);
            }} else if (step === 3) {{
                document.body.classList.add('left-panel-visible', 'step-3');
                backdrop.classList.add('active'); modal.classList.add('active');
                stepBadge.textContent = 'Step 3 / 11';
                stepTitle.innerHTML = 'Scene Explanation';
                stepContent.innerHTML = `<p class="modal-text">In this scene, you see <strong>Two People</strong> and <strong>Objects</strong> on the table.</p><p class="modal-text">Task: Judge who owns each object.</p>`;
                nextBtn.textContent = 'Next';
                nextBtn.onclick = () => showStep(4);
            }} else if (step === 4) {{
                document.body.classList.add('left-panel-visible', 'spotlight-mode', 'step-4');
                modal.classList.remove('active'); backdrop.classList.add('active');
                tooltip.classList.add('active');
                positionTooltipForStep4();

                tooltip.innerHTML = `
                    <h3>Control Panel Guide</h3>
                    <p>The slider represents the <strong>probability</strong> of ownership.</p>
                    <ul style="line-height: 1.6;">
                        <li>← <strong>Closer to Left</strong>: Higher probability it belongs to the <strong>Left Person</strong>.</li>
                        <li>→ <strong>Closer to Right</strong>: Higher probability it belongs to the <strong>Right Person</strong>.</li>
                        <li><strong>Middle</strong>: Unsure, Ambiguous, or Shared.</li>
                    </ul>
                    <p style="margin-top:10px; font-size: 13px; color: #666;">
                        <em>(The further you drag, the more certain you are.)</em>
                    </p>
                    <p><strong>Action: Drag the slider to indicate your confidence, then click "Confirm".</strong></p>
                `;

            }} else if (step === 5) {{
                backdrop.classList.add('active'); modal.classList.add('active');
                stepBadge.textContent = 'Step 5 / 11';
                stepTitle.innerHTML = 'Complete All';
                stepContent.innerHTML = `<p class="modal-text">Assign ownership for <strong>ALL remaining objects</strong>.</p>`;
                nextBtn.textContent = 'OK';
                nextBtn.onclick = () => {{
                    modal.classList.remove('active'); backdrop.classList.remove('active');
                    document.body.classList.add('left-panel-visible', 'step-5');
                }};
            }} else if (step === 6) {{
                document.body.classList.add('step-6');
                backdrop.classList.add('active');
                tooltip.classList.add('active');
                positionTooltipForStep6();
                tooltip.innerHTML = `<h3>Proceed</h3><p>Click <strong>Save Assignments</strong>.</p>`;
            }} else if (step === 7) {{
                tooltip.classList.remove('active');
                backdrop.classList.add('active'); modal.classList.add('active');
                stepBadge.textContent = 'Step 7 / 11';
                stepTitle.innerHTML = 'Practice Test';
                stepContent.innerHTML = `<p class="modal-text">Now, a <strong>check scene</strong>. Rely on intuition.</p>`;
                nextBtn.textContent = 'Start Test';
                nextBtn.onclick = () => {{ loadScene(2); showStep(8); }};
            }} else if (step === 8) {{
                document.body.classList.add('left-panel-visible', 'step-8-modal', 'spotlight-mode');
                backdrop.classList.add('active'); modal.classList.add('active');
                stepBadge.textContent = 'Step 8 / 11';
                stepTitle.innerHTML = 'Practice Scene';
                stepContent.innerHTML = `
                    <p class="modal-text">Quick Check:</p>
                    <div class="quiz-section">
                        <div class="quiz-question">1. Who took the green dinosaur toy?</div>
                        <div class="quiz-options"><button class="quiz-option" data-q="q1" data-a="girl">Girl</button><button class="quiz-option" data-q="q1" data-a="boy">Boy</button></div>
                        <div class="quiz-error" id="q1-error">✗ Incorrect</div>
                    </div>
                    <div class="quiz-section">
                        <div class="quiz-question">2. Pink pig doll closer to?</div>
                        <div class="quiz-options"><button class="quiz-option" data-q="q2" data-a="girl">Girl</button><button class="quiz-option" data-q="q2" data-a="boy">Boy</button></div>
                        <div class="quiz-error" id="q2-error">✗ Incorrect</div>
                    </div>`;
                nextBtn.textContent = 'Start'; nextBtn.disabled = true;
                
                const correct = {{ q1: 'boy', q2: 'girl' }};
                const user = {{}};
                setTimeout(() => {{
                    document.querySelectorAll('.quiz-option').forEach(opt => {{
                        opt.onclick = function() {{
                            const q = this.dataset.q;
                            document.querySelectorAll(`[data-q="${{q}}"]`).forEach(o => o.classList.remove('selected'));
                            this.classList.add('selected');
                            user[q] = this.dataset.a;
                            const err = document.getElementById(q + '-error');
                            if (user[q] === correct[q]) err.classList.remove('active'); else err.classList.add('active');
                            nextBtn.disabled = !Object.keys(correct).every(k => user[k] === correct[k]);
                        }};
                    }});
                }}, 100);
                nextBtn.onclick = () => {{ modal.classList.remove('active'); backdrop.classList.remove('active'); document.body.className = ''; document.body.classList.add('left-panel-visible', 'step-8'); }};

            // === UPDATED: Step 9 (Disclaimer) ===
            }} else if (step === 9) {{
                backdrop.classList.add('active'); modal.classList.add('active');
                stepBadge.textContent = 'Step 9 / 11';
                stepTitle.innerHTML = 'Disclaimer';
                stepContent.innerHTML = `<div style="background:#fff3cd;padding:15px;border-radius:8px;margin-bottom:15px"><strong>Note:</strong> There are no right or wrong answers. Rely on first intuition.</div><p class="modal-text">No moral judgment involved. Ignore external characteristics.</p>`;
                nextBtn.textContent = 'Next: Simulation';
                nextBtn.onclick = () => {{ showStep(11); }}; // Jump to Simulation Intro
            
            // === UPDATED: Step 10 (Fail) ===
            }} else if (step === 10) {{
                if(document.exitFullscreen) document.exitFullscreen().catch(e=>{{}}); // Exit Fullscreen
                fetch('/fail_screening', {{ method: 'POST' }});
                backdrop.classList.add('active'); modal.classList.add('active');
                stepBadge.textContent = 'Session Ended';
                stepBadge.style.background = '#ff6b6b';
                stepTitle.innerHTML = 'Thank You';
                stepContent.innerHTML = `<p class="modal-text">Based on your responses, your visual interpretation differs significantly from the baseline required.</p><p class="modal-text">You may close this window.</p>`;
                nextBtn.style.display = 'none';
                
            // === NEW: Step 11 (Simulation Intro) ===
            }} else if (step === 11) {{
                backdrop.classList.add('active'); modal.classList.add('active');
                document.querySelector('.container').style.opacity = '0.1'; 
                stepBadge.textContent = 'Step 10 / 11';
                stepTitle.innerHTML = 'Workflow Simulation';
                stepContent.innerHTML = `
                    <p class="modal-text">We will now simulate the <strong>Real Experiment Workflow</strong>.</p>
                    <p class="modal-text"><strong>Your Task:</strong></p>
                    <ol style="margin-bottom:20px; line-height:1.6; padding-left:20px;">
                        <li><strong>Observation (5s):</strong> The image will be shown in full size. Please observe the people and objects carefully.</li>
                        <li><strong>Annotation:</strong> Assign ownership for the items on the table.</li>
                    </ol>
                    <div style="font-size:13px; color:#666; background:#f5f5f5; padding:10px; border-radius:6px;">
                        <em>* This is a practice run. Data will not be recorded.</em>
                    </div>
                `;
                nextBtn.textContent = 'Start Simulation';
                nextBtn.onclick = () => {{
                     document.querySelector('.container').style.opacity = '1';
                     loadScene(3); 
                     showStep(12); 
                }};

            // === NEW: Step 12 (Focus Mode -> Interaction) ===
            }} else if (step === 12) {{
                modal.classList.remove('active'); 
                backdrop.classList.remove('active');
                document.body.classList.add('focus-mode');
                
                setTimeout(() => {{
                    document.body.classList.remove('focus-mode');
                    if (typeof adjustSVGSize === 'function') setTimeout(adjustSVGSize, 50);
                }}, 5000);

            // === NEW: Step 13 (Final Ready) ===
            }} else if (step === 13) {{
                backdrop.classList.add('active'); modal.classList.add('active');
                stepBadge.textContent = 'Step 11 / 11';
                stepTitle.innerHTML = 'Ready for Experiment';
                stepContent.innerHTML = `
                    <div style="text-align:center; margin-bottom:20px;">
                        <span style="font-size:40px;">🚀</span>
                    </div>
                    <p class="modal-text">You have completed the tutorial.</p>
                    <p class="modal-text">There are approximately <strong>20 scenes</strong> in the main experiment.</p>
                    <p class="modal-text">Please maintain the same level of attention. Thank you!</p>
                `;
                nextBtn.textContent = 'Start Main Experiment';
                nextBtn.classList.remove('tutorial-btn-primary');
                nextBtn.style.background = '#000';
                nextBtn.style.color = '#fff';
                
                nextBtn.onclick = () => {{
                    nextBtn.disabled = true;
                    nextBtn.textContent = 'Allocating Scenes...';
                    
                    fetch('/api/start_main_experiment', {{ method: 'POST' }})
                    .then(res => res.json())
                    .then(data => {{
                        if(data.status === 'success') {{
                            window.location.href = '/'; 
                        }} else {{
                            alert('Error initializing experiment: ' + (data.error || 'Unknown error'));
                            nextBtn.disabled = false;
                            nextBtn.textContent = 'Start Main Experiment';
                        }}
                    }})
                    .catch(err => {{
                        alert('Network Error');
                        nextBtn.disabled = false;
                        nextBtn.textContent = 'Start Main Experiment';
                    }});
                }};
            }}
        }}

        // --- Logic Updates ---
        
        function positionTooltipForStep4() {{ 
            const tooltip = document.getElementById('tutorial-tooltip');
            const firstItem = document.querySelector('.object-item:first-child');
            if (tooltip && firstItem) {{
                const rect = firstItem.getBoundingClientRect();
                tooltip.style.top = (rect.bottom + 20) + 'px'; tooltip.style.bottom = 'auto'; tooltip.style.right = (window.innerWidth - rect.right) + 'px';
            }}
        }}
        function positionTooltipForStep6() {{ 
            const tooltip = document.getElementById('tutorial-tooltip');
            const submitSection = document.getElementById('submit-section');
            if (tooltip && submitSection) {{
                const rect = submitSection.getBoundingClientRect();
                tooltip.style.top = 'auto'; tooltip.style.bottom = (window.innerHeight - rect.top + 20) + 'px'; tooltip.style.right = '20px';
            }}
        }}

        function validateAttentionCheck() {{
            if (!agentA || !agentB || !Array.isArray(objects) || objects.length === 0) return false;
            for (const obj of objects) {{
                const el = document.querySelector(`.object-item[data-id="${{obj.id}}"] input.confidence-slider`);
                if (!el) return false;
                const v = parseInt(el.value, 10);
                if (v >= 49 && v <= 51) return false;
                const predictedOwner = (v < 49) ? agentA.id : agentB.id;
                if ((predictedOwner || '').toLowerCase() !== (obj.owner || '').toLowerCase()) return false;
            }}
            return true;
        }}

        // 覆盖原始检查函数
        if (typeof checkAllConfirmed !== 'undefined') {{
            const originalCheckAllConfirmed = checkAllConfirmed;
            checkAllConfirmed = function() {{
                originalCheckAllConfirmed();
                if (currentSceneIndex === 1) {{
                    if (currentStep === 4 && objects.length > 0 && confirmations[objects[0].id]) showStep(5);
                    if (currentStep === 5) {{
                        const totalCount = objects.length;
                        const confirmedCount = Object.values(confirmations).filter(v => v === true).length;
                        if (confirmedCount === totalCount && totalCount > 0) showStep(6);
                    }}
                }}
            }};
        }}
        
        document.addEventListener('DOMContentLoaded', () => {{
            const saveBtn = document.getElementById('submit-btn');
            if (saveBtn) {{
                saveBtn.addEventListener('click', (e) => {{
                    // Scene 1: Tutorial -> Intermission
                    if (currentSceneIndex === 1 && currentStep === 6) {{
                        e.preventDefault(); e.stopPropagation();
                        showStep(7); 
                    }}
                    // Scene 2: Check -> Pass/Fail
                    else if (currentSceneIndex === 2 && currentStep === 8) {{
                        e.preventDefault(); e.stopImmediatePropagation();
                        const passed = validateAttentionCheck();
                        showStep(passed ? 9 : 10);
                    }}
                    // Scene 3: Simulation -> Final Ready (NEW)
                    else if (currentSceneIndex === 3) {{
                        e.preventDefault(); e.stopPropagation();
                        showStep(13);
                    }}
                }});
            }}
        }});
    """
    
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tutorial - Ownership Tool</title>
    <style>
        {common_css}
        {tutorial_css}
    </style>
</head>
<body>
    <div id="tutorial-backdrop" class="active"></div>
    <div id="tutorial-modal" class="active">
        <div class="modal-header">
            <div class="modal-step-badge" id="step-badge">Step 1 / 11</div>
            <h2 class="modal-title" id="step-title">Welcome</h2>
        </div>
        <div class="modal-content" id="step-content">Loading...</div>
        <div class="modal-actions">
            <button class="tutorial-btn tutorial-btn-primary" id="next-btn">Next</button>
        </div>
    </div>
    <div id="tutorial-tooltip" class="tutorial-tooltip"></div>

    <div class="header">
        <h1>Object Ownership Tool</h1>
        <div class="tutorial-badge">🎓 Tutorial Mode</div>
    </div>
    
    <div class="container">
        {left_panel}
        {right_panel}
    </div>
    
    <script>
        {core_script}
        {tutorial_script}
    </script>
</body>
</html>
"""



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
from core.translations import get_text
from static_assets.ui_components import render_common_css, render_left_panel_html, render_right_panel_html, render_core_script

def generate_guide_html(ctx_1, ctx_2, ctx_3, lang='en'): # 接收三个场景 + 语言
    """Entry point to generate the HTML."""
    
    # 定义处理函数 (with language support)
    def proc(ctx):
        if not ctx: return [], [], []
        return process_scene_data(ctx['scene_data'], ctx['camera_data'], use_display_mapping=False, filter_empty_plates=False, lang=lang)

    # 处理数据
    obj1, agt1, lbl1 = proc(ctx_1)
    obj2, agt2, lbl2 = proc(ctx_2)
    obj3, agt3, lbl3 = proc(ctx_3) # 处理场景 3
    
    # 转 JSON
    scene1_json = json.dumps({'objects': obj1, 'agents': agt1, 'agent_labels': lbl1, 'image_url': ctx_1['image_url']}, ensure_ascii=False)
    scene2_json = json.dumps({'objects': obj2, 'agents': agt2, 'agent_labels': lbl2, 'image_url': ctx_2['image_url']}, ensure_ascii=False)
    scene3_json = json.dumps({'objects': obj3, 'agents': agt3, 'agent_labels': lbl3, 'image_url': ctx_3['image_url']}, ensure_ascii=False)

    return _build_tutorial_template(scene1_json, scene2_json, scene3_json, lang)


def _build_tutorial_template(scene1_json, scene2_json, scene3_json, lang='en'):
    common_css = render_common_css()
    
    # Helper function for translations
    t = lambda key: get_text(lang, f"tutorial.{key}")
    
    # Get translated panel headers
    camera_view = get_text(lang, 'experiment.camera_view')
    ownership_panel = get_text(lang, 'experiment.ownership_panel')
    save_btn_text = t('save_button')
    
    # 这里的 left_panel 内容会被 loadScene 动态替换，但 ID 必须正确
    left_panel = f"""
        <div class="panel" id="left-panel-wrapper">
            <div class="panel-header">{camera_view}</div>
            <div class="image-container" id="imageContainer">
                <img src="" alt="Camera View" class="camera-image" id="cameraImage">
                <svg class="svg-overlay" id="svgOverlay"></svg>
            </div>
        </div>
    """
    
    # 右侧面板结构
    right_panel = f"""
        <div class="panel" id="right-panel-wrapper">
            <div class="panel-header">{ownership_panel}</div>
            <div class="matching-content" id="matching-content">
                <div class="section">
                    <div class="section-title">Visible Objects</div>
                    <div class="object-list" id="objectList"></div>
                </div>
            </div>
            <div class="submit-section" id="submit-section">
                <button class="submit-button" id="submit-btn" disabled>{save_btn_text}</button>
            </div>
        </div>
    """
    
    # 初始化核心脚本（先给空数组，避免未定义错误）
    # UI translations for core script
    ui_translations = {
        'ownership_question': get_text(lang, 'experiment.ownership_question'),
        'slider_unsure': get_text(lang, 'experiment.slider_unsure'),
        'confirm_button': get_text(lang, 'experiment.confirm_button'),
        'locked_button': '已锁定' if lang == 'zh' else 'Locked'
    }
    core_script = render_core_script("[]", "[]", "[]", include_save_function=False, lang=lang, translations=ui_translations)

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

    # Build translations object for JavaScript
    i18n = {
        'step1_badge': t('step1_badge'),
        'step1_title': t('step1_title'),
        'step1_content': t('step1_content'),
        'step1_button': t('step1_button'),
        'step2_badge': t('step2_badge'),
        'step2_title': t('step2_title'),
        'step2_content': t('step2_content'),
        'step2_wrong_label': t('step2_wrong_label'),
        'step2_wrong_hint': t('step2_wrong_hint'),
        'step2_correct_label': t('step2_correct_label'),
        'step2_correct_hint': t('step2_correct_hint'),
        'step2_button': t('step2_button'),
        'step3_badge': t('step3_badge'),
        'step3_title': t('step3_title'),
        'step3_content': t('step3_content'),
        'next_button': t('next_button'),
        'step4_tooltip_title': t('step4_tooltip_title'),
        'step4_tooltip_content': t('step4_tooltip_content'),
        'step5_badge': t('step5_badge'),
        'step5_title': t('step5_title'),
        'step5_content': t('step5_content'),
        'step5_button': t('step5_button'),
        'step6_tooltip_title': t('step6_tooltip_title'),
        'step6_tooltip_content': t('step6_tooltip_content'),
        'step7_badge': t('step7_badge'),
        'step7_title': t('step7_title'),
        'step7_content': t('step7_content'),
        'step7_button': t('step7_button'),
        'step8_badge': t('step8_badge'),
        'step8_title': t('step8_title'),
        'step8_intro': t('step8_intro'),
        'step8_q1': t('step8_q1'),
        'step8_q2': t('step8_q2'),
        'step8_option_girl': t('step8_option_girl'),
        'step8_option_boy': t('step8_option_boy'),
        'step8_error': t('step8_error'),
        'step8_button': t('step8_button'),
        'step9_badge': t('step9_badge'),
        'step9_title': t('step9_title'),
        'step9_note': t('step9_note'),
        'step9_content': t('step9_content'),
        'step9_button': t('step9_button'),
        'step10_badge': t('step10_badge'),
        'step10_title': t('step10_title'),
        'step10_content': t('step10_content'),
        'step11_badge': t('step11_badge'),
        'step11_title': t('step11_title'),
        'step11_content': t('step11_content'),
        'step11_button': t('step11_button'),
        'step13_badge': t('step13_badge'),
        'step13_title': t('step13_title'),
        'step13_content': t('step13_content'),
        'step13_button': t('step13_button'),
        'step13_allocating': t('step13_allocating'),
        'error_init': get_text(lang, 'errors.init_error'),
        'error_network': get_text(lang, 'errors.network_error'),
    }
    i18n_json = json.dumps(i18n, ensure_ascii=False)

    tutorial_script = f"""
        const scene1Data = {scene1_json};
        const scene2Data = {scene2_json};
        const scene3Data = {scene3_json}; // Simulation Data
        const i18n = {i18n_json}; // Translations
        
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
                stepBadge.textContent = i18n.step1_badge;
                stepTitle.innerHTML = i18n.step1_title;
                stepContent.innerHTML = `<p class="modal-text">${{i18n.step1_content}}</p>`;
                nextBtn.textContent = i18n.step1_button;
                nextBtn.onclick = () => {{
                    if (document.documentElement.requestFullscreen) {{
                        document.documentElement.requestFullscreen().catch(e=>{{}});
                    }}
                    showStep(2);
                }};
            }} else if (step === 2) {{
                backdrop.classList.add('active'); modal.classList.add('active');
                stepBadge.textContent = i18n.step2_badge;
                stepTitle.innerHTML = i18n.step2_title;
                stepContent.innerHTML = `
                    <p class="modal-text">${{i18n.step2_content}}</p>
                    <div class="concept-comparison">
                        <div class="concept-card wrong"><div>🚫</div><div>${{i18n.step2_wrong_label}}</div><div style="font-size:12px;color:#888">${{i18n.step2_wrong_hint}}</div></div>
                        <div class="concept-card correct"><div>👓</div><div>${{i18n.step2_correct_label}}</div><div style="font-size:12px;color:#888">${{i18n.step2_correct_hint}}</div></div>
                    </div>
                `;
                nextBtn.textContent = i18n.step2_button;
                nextBtn.onclick = () => showStep(3);
            }} else if (step === 3) {{
                document.body.classList.add('left-panel-visible', 'step-3');
                backdrop.classList.add('active'); modal.classList.add('active');
                stepBadge.textContent = i18n.step3_badge;
                stepTitle.innerHTML = i18n.step3_title;
                stepContent.innerHTML = i18n.step3_content;
                nextBtn.textContent = i18n.next_button;
                nextBtn.onclick = () => showStep(4);
            }} else if (step === 4) {{
                document.body.classList.add('left-panel-visible', 'spotlight-mode', 'step-4');
                modal.classList.remove('active'); backdrop.classList.add('active');
                tooltip.classList.add('active');
                positionTooltipForStep4();

                tooltip.innerHTML = `<h3>${{i18n.step4_tooltip_title}}</h3>${{i18n.step4_tooltip_content}}`;

            }} else if (step === 5) {{
                backdrop.classList.add('active'); modal.classList.add('active');
                stepBadge.textContent = i18n.step5_badge;
                stepTitle.innerHTML = i18n.step5_title;
                stepContent.innerHTML = i18n.step5_content;
                nextBtn.textContent = i18n.step5_button;
                nextBtn.onclick = () => {{
                    modal.classList.remove('active'); backdrop.classList.remove('active');
                    document.body.classList.add('left-panel-visible', 'step-5');
                }};
            }} else if (step === 6) {{
                document.body.classList.add('step-6');
                backdrop.classList.add('active');
                tooltip.classList.add('active');
                positionTooltipForStep6();
                tooltip.innerHTML = `<h3>${{i18n.step6_tooltip_title}}</h3><p>${{i18n.step6_tooltip_content}}</p>`;
            }} else if (step === 7) {{
                tooltip.classList.remove('active');
                backdrop.classList.add('active'); modal.classList.add('active');
                stepBadge.textContent = i18n.step7_badge;
                stepTitle.innerHTML = i18n.step7_title;
                stepContent.innerHTML = i18n.step7_content;
                nextBtn.textContent = i18n.step7_button;
                nextBtn.onclick = () => {{ loadScene(2); showStep(8); }};
            }} else if (step === 8) {{
                document.body.classList.add('left-panel-visible', 'step-8-modal', 'spotlight-mode');
                backdrop.classList.add('active'); modal.classList.add('active');
                stepBadge.textContent = i18n.step8_badge;
                stepTitle.innerHTML = i18n.step8_title;
                stepContent.innerHTML = `
                    <p class="modal-text">${{i18n.step8_intro}}</p>
                    <div class="quiz-section">
                        <div class="quiz-question">${{i18n.step8_q1}}</div>
                        <div class="quiz-options"><button class="quiz-option" data-q="q1" data-a="girl">${{i18n.step8_option_girl}}</button><button class="quiz-option" data-q="q1" data-a="boy">${{i18n.step8_option_boy}}</button></div>
                        <div class="quiz-error" id="q1-error">${{i18n.step8_error}}</div>
                    </div>
                    <div class="quiz-section">
                        <div class="quiz-question">${{i18n.step8_q2}}</div>
                        <div class="quiz-options"><button class="quiz-option" data-q="q2" data-a="girl">${{i18n.step8_option_girl}}</button><button class="quiz-option" data-q="q2" data-a="boy">${{i18n.step8_option_boy}}</button></div>
                        <div class="quiz-error" id="q2-error">${{i18n.step8_error}}</div>
                    </div>`;
                nextBtn.textContent = i18n.step8_button; nextBtn.disabled = true;
                
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
                stepBadge.textContent = i18n.step9_badge;
                stepTitle.innerHTML = i18n.step9_title;
                stepContent.innerHTML = `<div style="background:#fff3cd;padding:15px;border-radius:8px;margin-bottom:15px">${{i18n.step9_note}}</div>${{i18n.step9_content}}`;
                nextBtn.textContent = i18n.step9_button;
                nextBtn.onclick = () => {{ showStep(11); }}; // Jump to Simulation Intro
            
            // === UPDATED: Step 10 (Fail) ===
            }} else if (step === 10) {{
                if(document.exitFullscreen) document.exitFullscreen().catch(e=>{{}}); // Exit Fullscreen
                fetch('/fail_screening', {{ method: 'POST' }});
                backdrop.classList.add('active'); modal.classList.add('active');
                stepBadge.textContent = i18n.step10_badge;
                stepBadge.style.background = '#ff6b6b';
                stepTitle.innerHTML = i18n.step10_title;
                stepContent.innerHTML = i18n.step10_content;
                nextBtn.style.display = 'none';
                
            // === NEW: Step 11 (Simulation Intro) ===
            }} else if (step === 11) {{
                backdrop.classList.add('active'); modal.classList.add('active');
                document.querySelector('.container').style.opacity = '0.1'; 
                stepBadge.textContent = i18n.step11_badge;
                stepTitle.innerHTML = i18n.step11_title;
                stepContent.innerHTML = i18n.step11_content;
                nextBtn.textContent = i18n.step11_button;
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
                stepBadge.textContent = i18n.step13_badge;
                stepTitle.innerHTML = i18n.step13_title;
                stepContent.innerHTML = i18n.step13_content;
                nextBtn.textContent = i18n.step13_button;
                nextBtn.classList.remove('tutorial-btn-primary');
                nextBtn.style.background = '#000';
                nextBtn.style.color = '#fff';
                
                nextBtn.onclick = () => {{
                    nextBtn.disabled = true;
                    nextBtn.textContent = i18n.step13_allocating;
                    
                    fetch('/api/start_main_experiment', {{ method: 'POST' }})
                    .then(res => res.json())
                    .then(data => {{
                        if(data.status === 'success') {{
                            window.location.href = '/'; 
                        }} else {{
                            alert(i18n.error_init + ': ' + (data.error || 'Unknown error'));
                            nextBtn.disabled = false;
                            nextBtn.textContent = i18n.step13_button;
                        }}
                    }})
                    .catch(err => {{
                        alert(i18n.error_network);
                        nextBtn.disabled = false;
                        nextBtn.textContent = i18n.step13_button;
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
    
    # Get page-level translations
    page_title = t('page_title')
    header_title = t('header')
    mode_badge = t('mode_badge')
    step1_badge_init = t('step1_badge')
    step1_title_init = t('step1_title')
    next_button_init = t('next_button')
    
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_title}</title>
    <style>
        {common_css}
        {tutorial_css}
    </style>
</head>
<body>
    <div id="tutorial-backdrop" class="active"></div>
    <div id="tutorial-modal" class="active">
        <div class="modal-header">
            <div class="modal-step-badge" id="step-badge">{step1_badge_init}</div>
            <h2 class="modal-title" id="step-title">{step1_title_init}</h2>
        </div>
        <div class="modal-content" id="step-content">Loading...</div>
        <div class="modal-actions">
            <button class="tutorial-btn tutorial-btn-primary" id="next-btn">{next_button_init}</button>
        </div>
    </div>
    <div id="tutorial-tooltip" class="tutorial-tooltip"></div>

    <div class="header">
        <h1>{header_title}</h1>
        <div class="tutorial-badge">{mode_badge}</div>
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



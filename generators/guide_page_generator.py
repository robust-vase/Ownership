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

def generate_guide_html(ctx_1, ctx_2):
    """Entry point to generate the HTML."""
    # Process both scenes using centralized data processor
    # Tutorial uses raw names (use_display_mapping=False) for simplicity
    obj1, agt1, lbl1 = process_scene_data(
        ctx_1['scene_data'], ctx_1['camera_data'],
        use_display_mapping=False, filter_empty_plates=False
    )
    obj2, agt2, lbl2 = process_scene_data(
        ctx_2['scene_data'], ctx_2['camera_data'],
        use_display_mapping=False, filter_empty_plates=False
    )
    
    # Create JSON payloads
    scene1_json = json.dumps({
        'objects': obj1, 'agents': agt1, 'agent_labels': lbl1, 'image_url': ctx_1['image_url']
    }, ensure_ascii=False)
    
    scene2_json = json.dumps({
        'objects': obj2, 'agents': agt2, 'agent_labels': lbl2, 'image_url': ctx_2['image_url']
    }, ensure_ascii=False)

    return _build_tutorial_template(scene1_json, scene2_json)

def _build_tutorial_template(scene1_json, scene2_json):
    common_css = render_common_css()
    
    # Initialize UI Components
    left_panel = render_left_panel_html("") 
    
    right_panel = """
        <div class="panel" id="right-panel">
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
    
    # Initialize Core Script with empty arrays
    core_script = render_core_script("[]", "[]", "[]", include_save_function=False)

    tutorial_css = """
        /* Base Tutorial Styles */
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
        .concept-card div:first-child { font-size: 40px; margin-bottom: 10px; }
        
        /* Visibility Classes */
        #left-panel { position: relative; z-index: 1; transition: none; }
        body.left-panel-visible #left-panel { z-index: 10000; opacity: 1 !important; box-shadow: 0 0 30px rgba(0,0,0,0.3); }
        body.spotlight-mode #right-panel { opacity: 0.1; pointer-events: none; transition: opacity 0.3s; }
        
        /* Step 3: Modal on Right */
        body.step-3 #tutorial-modal { 
            left: auto !important;
            right: 5% !important;
            transform: translateY(-50%) !important;
            top: 50% !important;
            max-width: 450px;
        }
        
        /* Step 8: Modal on Right (similar to Step 3) */
        body.step-8-modal #tutorial-modal { 
            left: auto !important;
            right: 5% !important;
            transform: translateY(-50%) !important;
            top: 50% !important;
            max-width: 500px;
        }
        
        /* Step 4: Highlight First Item */
        body.step-4 #right-panel { opacity: 1; }
        body.step-4 #objectList { opacity: 1; }
        body.step-4 .object-item { opacity: 0.1; pointer-events: none; filter: blur(2px); }
        body.step-4 .object-item:first-child { opacity: 1 !important; pointer-events: auto !important; filter: none !important; position: relative; z-index: 10005; background: white; box-shadow: 0 0 0 4px #667eea, 0 0 50px rgba(0,0,0,0.5); transform: scale(1.02); }
        
        /* Step 5 & 8: Full interaction */
        body.step-5 #right-panel,
        body.step-8 #right-panel { opacity: 1 !important; pointer-events: auto !important; z-index: 9990; }
        
        /* Step 6: Highlight Save (NO spotlight-mode blocking!) */
        body.step-6 #right-panel { opacity: 1 !important; pointer-events: auto !important; }
        body.step-6 .matching-content { opacity: 0.3; }
        body.step-6 #submit-section { position: relative; z-index: 10005; opacity: 1 !important; pointer-events: auto !important; background: white; box-shadow: 0 0 0 1000px rgba(0,0,0,0.85); border-radius: 8px; }
        
        .tutorial-tooltip { position: fixed; background: white; padding: 20px 24px; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,0.2); z-index: 11000; max-width: 350px; display: none; }
        .tutorial-tooltip.active { display: block; animation: tooltipFadeIn 0.3s ease; }
        .tutorial-tooltip h3 { margin: 0 0 10px 0; color: #667eea; }
        .tutorial-tooltip ul { padding-left: 20px; margin: 10px 0; }
        @keyframes tooltipFadeIn { from { opacity: 0; transform: translateY(-10px); } to { opacity: 1; transform: translateY(0); } }
        
        /* Validation Quiz Styles */
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
        // Inject Data from Python
        const scene1Data = {scene1_json};
        const scene2Data = {scene2_json};
        
        let currentStep = 0;
        let currentSceneIndex = 1;
        
        window.addEventListener('load', () => {{
            console.log("Window loaded, initializing tutorial...");
            loadScene(1);
            initTutorial();
            
            window.addEventListener('resize', () => {{
                if (currentStep === 4) positionTooltipForStep4();
                if (currentStep === 6) positionTooltipForStep6();
            }});
        }});
        
        // --- SCENE LOADING ---
        function loadScene(index) {{
            console.log("Loading Scene " + index);
            currentSceneIndex = index;
            const data = (index === 1) ? scene1Data : scene2Data;
            
            // 1. Update Core Data Arrays (In-place)
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
            
            // 2. CRITICAL FIX: Update global Agent references for Core Script logic
            if (agents.length >= 2) {{
                agentA = agents[0];
                agentB = agents[1];
            }}
            
            // 3. Reset State
            if (typeof confirmations !== 'undefined') {{
                for (const prop of Object.keys(confirmations)) delete confirmations[prop];
            }}
            if (typeof ownerships !== 'undefined') {{
            for (const prop of Object.keys(ownerships)) delete ownerships[prop];
            }}

            if (typeof assignments !== 'undefined') {{
                for (const prop of Object.keys(assignments)) delete assignments[prop];
            }}
            
            // 4. Update UI
            const img = document.getElementById('cameraImage');
            if (img) img.src = data.image_url;
            
            // Force Re-render
            const list = document.getElementById('objectList');
            if (list) list.innerHTML = '';
            const svg = document.getElementById('svgOverlay');
            if (svg) svg.innerHTML = '';
            
            if (typeof renderVisuals === 'function') renderVisuals();
            if (typeof populateObjectList === 'function') populateObjectList();
            if (typeof adjustSVGSize === 'function') adjustSVGSize();
            if (typeof updateSubmitButton === 'function') updateSubmitButton();
        }}
        
        function initTutorial() {{ showStep(1); }}
        
        // --- STEP LOGIC ---
        function showStep(step) {{
            console.log("Showing Step: " + step);
            currentStep = step;
            const backdrop = document.getElementById('tutorial-backdrop');
            const modal = document.getElementById('tutorial-modal');
            const tooltip = document.getElementById('tutorial-tooltip');
            const stepBadge = document.getElementById('step-badge');
            const stepTitle = document.getElementById('step-title');
            const stepContent = document.getElementById('step-content');
            const nextBtn = document.getElementById('next-btn');
            
            // Reset Visual State
            document.body.className = ''; 
            modal.style.left = ''; modal.style.transform = ''; modal.style.right = '';
            if (tooltip) tooltip.classList.remove('active');
            nextBtn.style.display = 'block';
            
            // Step 1: Welcome
            if (step === 1) {{
                backdrop.classList.add('active'); modal.classList.add('active');
                stepBadge.textContent = 'Step 1 / 9';
                stepTitle.innerHTML = 'Welcome';
                stepContent.innerHTML = `<p class="modal-text">Welcome to the <strong>Ownership Cognition Experiment</strong>.<br>For the best experience, switch to full screen.</p>`;
                nextBtn.textContent = 'Enter Fullscreen';
                nextBtn.disabled = false;
                nextBtn.onclick = () => {{
                    if (document.documentElement.requestFullscreen) {{
                        document.documentElement.requestFullscreen().catch(e=>{{}});
                    }}
                    showStep(2);
                }};
            
            // Step 2: Concept
            }} else if (step === 2) {{
                backdrop.classList.add('active'); modal.classList.add('active');
                stepBadge.textContent = 'Step 2 / 9';
                stepTitle.innerHTML = 'Visual Judgment';
                stepContent.innerHTML = `
                    <p class="modal-text">We focus on <strong>Psychological Ownership</strong> based on visual intuition.</p>
                    <div class="concept-comparison">
                        <div class="concept-card wrong"><div>🚫</div><div>No External Clues</div><div style="font-size:12px;color:#888">Don't guess who bought it</div></div>
                        <div class="concept-card correct"><div>👓</div><div>Visual Intuition</div><div style="font-size:12px;color:#888">Judge based on the image</div></div>
                    </div>
                    <p class="modal-text">Simply look at the image: <strong>If you feel an object belongs to someone right now, then it does.</strong></p>
                `;
                nextBtn.textContent = 'I Understand';
                nextBtn.onclick = () => showStep(3);
            
            // Step 3: Scene 1 Explain (Modal on Right)
            }} else if (step === 3) {{
                document.body.classList.add('left-panel-visible');
                document.body.classList.add('step-3'); // Triggers CSS right-align
                backdrop.classList.add('active'); modal.classList.add('active');
                
                stepBadge.textContent = 'Step 3 / 9';
                stepTitle.innerHTML = 'Scene Explanation';
                stepContent.innerHTML = `<p class="modal-text">In this scene, you see <strong>Two People</strong> and <strong>Objects</strong> on the table.</p><p class="modal-text">Your task is to judge <strong>who owns each object</strong> based on the visual context.</p><p class="modal-text" style="font-size:14px;color:#666">(Scene visible on left)</p>`;
                nextBtn.textContent = 'Next';
                nextBtn.onclick = () => showStep(4);
            
            // Step 4: Spotlight Slider
            }} else if (step === 4) {{
                document.body.classList.add('left-panel-visible');
                document.body.classList.add('spotlight-mode', 'step-4');
                modal.classList.remove('active'); backdrop.classList.add('active');
                
                tooltip.classList.add('active');
                positionTooltipForStep4();
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
            // Step 5: Complete All (Scene 1)
            }} else if (step === 5) {{
                backdrop.classList.add('active'); modal.classList.add('active');
                stepBadge.textContent = 'Step 5 / 9';
                stepTitle.innerHTML = 'Complete All';
                stepContent.innerHTML = `<p class="modal-text">Great! Now assign ownership for <strong>ALL remaining objects</strong> in this list.</p>`;
                nextBtn.textContent = 'OK, Let me do it';
                nextBtn.onclick = () => {{
                    modal.classList.remove('active'); backdrop.classList.remove('active');
                    document.body.classList.add('left-panel-visible'); 
                    document.body.classList.add('step-5'); // Interactive
                }};
            
            // Step 6: Save Button (Scene 1)
            }} else if (step === 6) {{
                document.body.classList.add('step-6');
                // NO spotlight-mode - we need the save button clickable!
                backdrop.classList.add('active');
                
                tooltip.classList.add('active');
                positionTooltipForStep6();
                tooltip.innerHTML = `<h3>Proceed</h3><p>All items confirmed! Click <strong>Save Assignments</strong> to move to the next stage.</p>`;
            
            // Step 7: INTERMISSION (Blurred)
            }} else if (step === 7) {{
                tooltip.classList.remove('active');
                backdrop.classList.add('active'); modal.classList.add('active');
                
                stepBadge.textContent = 'Step 7 / 9';
                stepTitle.innerHTML = 'Practice Test';
                stepContent.innerHTML = `
                    <p class="modal-text">You have completed the tutorial.</p>
                    <p class="modal-text"><strong>Now, we will show you a new scene.</strong></p>
                    <p class="modal-text">Please rely on your intuition to assign ownership for the items in this new scene. This helps us verify your understanding.</p>
                `;
                nextBtn.textContent = 'Start Test';
                nextBtn.onclick = () => {{
                    loadScene(2); // SWITCH TO SCENE 2 (Turing Test)
                    showStep(8);
                }};
            
            // Step 8: Scene 2 Interaction (Interactive - Turing Test Scene)
            }} else if (step === 8) {{
                // Show modal on the right with quiz questions
                document.body.classList.add('left-panel-visible', 'step-8-modal', 'spotlight-mode');
                backdrop.classList.add('active');
                modal.classList.add('active');
                
                stepBadge.textContent = 'Step 8 / 9';
                stepTitle.innerHTML = 'Practice Scene';
                stepContent.innerHTML = `
                    <p class="modal-text">Before proceeding, please answer these questions based on what you see:</p>
                    
                    <div class="quiz-section">
                        <div class="quiz-question">1. Who took the green dinosaur toy?</div>
                        <div class="quiz-options">
                            <button class="quiz-option" data-question="q1" data-answer="girl">Girl</button>
                            <button class="quiz-option" data-question="q1" data-answer="boy">Boy</button>
                        </div>
                        <div class="quiz-error" id="q1-error">✗ Incorrect answer</div>
                    </div>
                    
                    <div class="quiz-section">
                        <div class="quiz-question">2. Who is the pink pig doll closer to?</div>
                        <div class="quiz-options">
                            <button class="quiz-option" data-question="q2" data-answer="girl">Girl</button>
                            <button class="quiz-option" data-question="q2" data-answer="boy">Boy</button>
                        </div>
                        <div class="quiz-error" id="q2-error">✗ Incorrect answer</div>
                    </div>
                `;
                nextBtn.textContent = 'Start';
                nextBtn.style.display = 'block';
                nextBtn.disabled = true; // Initially disabled
                
                // Quiz validation logic
                const correctAnswers = {{ q1: 'boy', q2: 'girl' }};
                const userAnswers = {{}};
                
                setTimeout(() => {{
                    const options = document.querySelectorAll('.quiz-option');
                    options.forEach(opt => {{
                        opt.addEventListener('click', function() {{
                            const question = this.getAttribute('data-question');
                            const answer = this.getAttribute('data-answer');
                            
                            // Clear previous selection for this question
                            document.querySelectorAll(`[data-question="${{question}}"]`).forEach(o => o.classList.remove('selected'));
                            this.classList.add('selected');
                            
                            // Store answer
                            userAnswers[question] = answer;
                            
                            // Check answer immediately
                            const errorEl = document.getElementById(question + '-error');
                            if (answer === correctAnswers[question]) {{
                                errorEl.classList.remove('active');
                            }} else {{
                                errorEl.classList.add('active');
                            }}
                            
                            // Enable Start button only if both answers are correct
                            const allCorrect = Object.keys(correctAnswers).every(q => userAnswers[q] === correctAnswers[q]);
                            nextBtn.disabled = !allCorrect;
                        }});
                    }});
                }}, 100);
                
                nextBtn.onclick = () => {{
                    // Remove modal and backdrop to enable interaction
                    modal.classList.remove('active'); 
                    backdrop.classList.remove('active');
                    document.body.className = '';
                    // Enable full panel interaction
                    document.body.classList.add('left-panel-visible', 'step-8');
                }};
            
            // Step 9: Disclaimer (Success)
            }} else if (step === 9) {{
                backdrop.classList.add('active'); modal.classList.add('active');
                stepBadge.textContent = 'Step 9 / 9';
                stepTitle.innerHTML = 'Disclaimer';
                stepContent.innerHTML = `<div style="background:#fff3cd;padding:15px;border-radius:8px;margin-bottom:15px"><strong>Note:</strong> There are no right or wrong answers. Please rely on your first intuition.</div><p class="modal-text">This experiment does not involve moral judgment. Please ignore external characteristics.</p>`;
                nextBtn.textContent = 'Start Experiment';
                nextBtn.onclick = () => {{ window.location.href = '/'; }};
            
            // Step 10: Fail
            }} else if (step === 10) {{
                // ★ CRITICAL FIX: Double braces {{ }} for f-string escaping
                fetch('/fail_screening', {{ method: 'POST' }});

                backdrop.classList.add('active'); modal.classList.add('active');
                stepBadge.textContent = 'Session Ended';
                stepBadge.style.background = '#ff6b6b';
                stepTitle.innerHTML = 'Thank You';
                stepContent.innerHTML = `<p class="modal-text">Based on your responses, your visual interpretation differs significantly from the baseline required.</p><p class="modal-text">You may close this window.</p>`;
                nextBtn.style.display = 'none';
            }}
        }}
        
        // --- HELPERS ---
        function positionTooltipForStep4() {{
            const tooltip = document.getElementById('tutorial-tooltip');
            const firstItem = document.querySelector('.object-item:first-child');
            if (tooltip && firstItem) {{
                const rect = firstItem.getBoundingClientRect();
                tooltip.style.top = (rect.bottom + 20) + 'px';
                tooltip.style.bottom = 'auto';
                tooltip.style.right = (window.innerWidth - rect.right) + 'px';
            }}
        }}

        function positionTooltipForStep6() {{
            const tooltip = document.getElementById('tutorial-tooltip');
            const submitSection = document.getElementById('submit-section');
            if (tooltip && submitSection) {{
                const rect = submitSection.getBoundingClientRect();
                tooltip.style.top = 'auto';
                tooltip.style.bottom = (window.innerHeight - rect.top + 20) + 'px';
                tooltip.style.right = '20px';
            }}
        }}

        function validateAttentionCheck() {{
            const norm = (s) => String(s || '').trim().toLowerCase();

            const getSliderValue = (objId) => {{
                const el = document.querySelector(`.object-item[data-id="${{objId}}"] input.confidence-slider`);
                if (!el) return null;
                const v = parseInt(el.value, 10);
                return Number.isFinite(v) ? v : null;
            }};

            // 如果不是练习场景/不需要检查，可以直接 return true（按你实际逻辑改）
            // if (currentSceneIndex !== 2) return true;

            if (!agentA || !agentB || !Array.isArray(objects) || objects.length === 0) return false;

            for (const obj of objects) {{
                const v = getSliderValue(obj.id);
                if (v === null) return false;

                // 49~51 都算“没给出明确答案”
                if (v >= 49 && v <= 51) return false;

                const predictedOwner = (v < 49) ? agentA.id : agentB.id;

                if (norm(predictedOwner) !== norm(obj.owner)) {{
                return false;
                }}
            }}

            return true;
        }}

        // --- HOOKS ---
        const originalCheckAllConfirmed = checkAllConfirmed;
        checkAllConfirmed = function() {{
            originalCheckAllConfirmed();
            
            // Auto-advance logic ONLY for Scene 1 (Tutorial)
            if (currentSceneIndex === 1) {{
                if (currentStep === 4 && objects.length > 0 && confirmations[objects[0].id]) {{
                    showStep(5);
                }}
                if (currentStep === 5) {{
                    const totalCount = objects.length;
                    const confirmedCount = Object.values(confirmations).filter(v => v === true).length;
                    if (confirmedCount === totalCount && totalCount > 0) showStep(6);
                }}
            }}
        }};
        
        document.addEventListener('DOMContentLoaded', () => {{
            const saveBtn = document.getElementById('submit-btn');
            if (saveBtn) {{
                saveBtn.addEventListener('click', (e) => {{
                    if (currentSceneIndex === 1 && currentStep === 6) {{
                        e.preventDefault(); e.stopPropagation();
                        showStep(7); // Go to Intermission
                    }}

                    else if (currentSceneIndex === 2 && currentStep === 8) {{
                    e.preventDefault();
                    e.stopImmediatePropagation(); // ✅ 比 stopPropagation 更彻底
                    const passed = validateAttentionCheck();
                    showStep(passed ? 9 : 10);
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
            <div class="modal-step-badge" id="step-badge">Step 1 / 9</div>
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
        <div class="panel" id="left-panel">
            <div class="panel-header">📷 Camera View</div>
            <div class="image-container" id="imageContainer">
                <img src="" alt="Camera View" class="camera-image" id="cameraImage">
                <svg class="svg-overlay" id="svgOverlay"></svg>
            </div>
        </div>
        {right_panel}
    </div>
    
    <script>
        {core_script}
        {tutorial_script}
    </script>
</body>
</html>
"""
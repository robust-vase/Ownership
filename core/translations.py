"""
Translations Module
===================
Centralized i18n dictionary for English and Chinese.
Usage: get_text(lang, key_path) where key_path is "section.key" format.
"""

TRANSLATIONS = {
    # ============================================================
    # LOGIN PAGE
    # ============================================================
    "login": {
        "page_title": {
            "en": "Participant Registration",
            "zh": "参与者注册"
        },
        "header": {
            "en": "🧠 Cognition Experiment",
            "zh": "🧠 认知实验"
        },
        "form_title": {
            "en": "Participant Info",
            "zh": "参与者信息"
        },
        "participant_id": {
            "en": "Participant ID (Name Pinyin + Last 4 digits of Phone)",
            "zh": "被试ID (姓名拼音+手机尾号后四位)"
        },
        "participant_id_placeholder": {
            "en": "e.g. Toy1234",
            "zh": "例如: ZhangSan1234"
        },
        "consent_title": {
            "en": "Informed Consent",
            "zh": "知情同意书"
        },
        "consent_content": {
            "en": "This experiment is conducted for academic research purposes. Your data will be kept strictly confidential. <br><br><strong>Note: To receive payment upon completion, you will be required to provide your Bank Account Number and Branch Name.</strong>",
            "zh": "本实验仅用于学术研究目的。您的数据将被严格保密，仅用于科学分析。参与完全自愿，您可以随时退出而不会受到任何影响。<br><br><strong>特别声明：在完成实验后，我们需要您填写本人的银行卡账号以及开户行等信息，以便后续为您发放实验报酬。</strong>点击“开始实验”即表示您同意参与并知悉上述事项。"
        },
        "consent_checkbox": {
            "en": "I have read and agree to the above informed consent",
            "zh": "我已阅读并同意以上知情同意书"
        },
        "gender": {
            "en": "Gender",
            "zh": "性别"
        },
        "gender_male": {
            "en": "Male",
            "zh": "男"
        },
        "gender_female": {
            "en": "Female",
            "zh": "女"
        },
        "dob": {
            "en": "Date of Birth",
            "zh": "出生年月"
        },
        "status": {
            "en": "Current Status",
            "zh": "身份"
        },
        "status_student": {
            "en": "Student",
            "zh": "在校学生"
        },
        "status_employed": {
            "en": "Employed",
            "zh": "在职人员"
        },
        "status_other": {
            "en": "Other",
            "zh": "其他"
        },
        "education": {
            "en": "Education Level",
            "zh": "最高学历"
        },
        "edu_high_school": {
            "en": "High School",
            "zh": "高中/中专"
        },
        "edu_bachelor": {
            "en": "Bachelor",
            "zh": "本科"
        },
        "edu_master": {
            "en": "Master",
            "zh": "硕士"
        },
        "edu_phd": {
            "en": "PhD",
            "zh": "博士"
        },
        "edu_other": {
            "en": "Other",
            "zh": "其他"
        },
        "nationality": {
            "en": "Nationality",
            "zh": "国籍"
        },
        "select_placeholder": {
            "en": "Select...",
            "zh": "请选择..."
        },
        "submit_button": {
            "en": "Start Experiment",
            "zh": "开始实验"
        },
        "lang_switcher": {
            "en": "中文",
            "zh": "English"
        }
    },
    
    # ============================================================
    # COUNTRY OPTIONS
    # ============================================================
    "countries": {
        "china": {"en": "China", "zh": "中国"},
        "usa": {"en": "United States", "zh": "美国"},
        "uk": {"en": "United Kingdom", "zh": "英国"},
        "australia": {"en": "Australia", "zh": "澳大利亚"},
        "canada": {"en": "Canada", "zh": "加拿大"},
        "germany": {"en": "Germany", "zh": "德国"},
        "france": {"en": "France", "zh": "法国"},
        "japan": {"en": "Japan", "zh": "日本"},
        "south_korea": {"en": "South Korea", "zh": "韩国"},
        "india": {"en": "India", "zh": "印度"},
        "russia": {"en": "Russia", "zh": "俄罗斯"},
        "brazil": {"en": "Brazil", "zh": "巴西"},
        "other": {"en": "Other", "zh": "其他"}
    },
    
    # ============================================================
    # MAIN EXPERIMENT PAGE
    # ============================================================
    "experiment": {
        "page_title": {
            "en": "Experiment",
            "zh": "实验"
        },
        "header": {
            "en": "🧠 Experiment",
            "zh": "🧠 实验"
        },
        "scene_progress": {
            "en": "Scene {current} / {total}",
            "zh": "场景 {current} / {total}"
        },
        "submit_button": {
            "en": "Save & Next",
            "zh": "保存并继续"
        },
        "camera_view": {
            "en": "📷 Camera View",
            "zh": "📷 相机视角"
        },
        "ownership_panel": {
            "en": "🎚️ Ownership Assignment",
            "zh": "🎚️ 所有权判断"
        },
        "visible_objects": {
            "en": "Visible Objects",
            "zh": "可见物品"
        },
        "confirm_button": {
            "en": "Confirm",
            "zh": "锁定"
        },
        "ownership_question": {
            "en": "Who do you think this is more likely to belong to?",
            "zh": "你认为这个物品更可能属于谁？"
        },
        "slider_unsure": {
            "en": "Unsure",
            "zh": "不确定"
        }
    },
    
    # ============================================================
    # COMPLETION PAGE
    # ============================================================
    "complete": {
        "title": {
            "en": "Session Completed",
            "zh": "实验完成"
        },
        "message": {
            "en": "You have successfully completed all the assigned scenes.",
            "zh": "您已成功完成所有分配的场景。"
        },
        "thanks": {
            "en": "Thank you for your contribution to our research!",
            "zh": "感谢您对我们研究的贡献！"
        },
        "close_hint": {
            "en": "You may now close this window.",
            "zh": "您现在可以关闭此窗口。"
        }
    },
    
    # ============================================================
    # TUTORIAL / GUIDE PAGE
    # ============================================================
    "tutorial": {
        "page_title": {
            "en": "Tutorial - Ownership Tool",
            "zh": "教程 - 所有权工具"
        },
        "header": {
            "en": "Object Ownership Tool",
            "zh": "物品所有权工具"
        },
        "mode_badge": {
            "en": "🎓 Tutorial Mode",
            "zh": "🎓 教程模式"
        },
        "save_button": {
            "en": "Save Assignments",
            "zh": "保存判断"
        },
        "next_button": {
            "en": "Next",
            "zh": "下一步"
        },
        
        # Step 1
        "step1_badge": {
            "en": "Step 1 / 11",
            "zh": "第 1 / 11 步"
        },
        "step1_title": {
            "en": "Welcome",
            "zh": "欢迎"
        },
        "step1_content": {
            "en": "Welcome to the <strong>Experiment</strong>.<br>For the best experience, switch to full screen.",
            "zh": "欢迎参加<strong>实验</strong>。<br>为了获得最佳体验，请切换到全屏模式。"
        },
        "step1_button": {
            "en": "Enter Fullscreen",
            "zh": "进入全屏"
        },
        
        # Step 2
        "step2_badge": {
            "en": "Step 2 / 11",
            "zh": "第 2 / 11 步"
        },
        "step2_title": {
            "en": "Visual Judgment",
            "zh": "视觉判断"
        },
        "step2_content": {
            "en": "Welcome to the experiment. In this study, you will see a series of daily life images featuring objects on a table. Your task is to judge the ownership of these objects (who they are more likely to belong to) based on your intuition.",
            "zh": "欢迎参加本实验，在本实验中，你将看到一系列生活化的关于桌面物品的图片。你的任务是基于你的直觉，判断图片中物品的所有权<strong>（物品更有可能是谁的） </strong>。"
        },
        "step2_wrong_label": {
            "en": "No External Clues",
            "zh": "不要依赖外部线索"
        },
        "step2_wrong_hint": {
            "en": "Don't guess who bought it",
            "zh": "不要过度揣测"
        },
        "step2_correct_label": {
            "en": "Follow Intuition to judge",
            "zh": "根据直觉做出判断"
        },
        "step2_correct_hint": {
            "en": "Judge based on the image",
            "zh": "根据图像做出符合你直觉的判断"
        },
        "step2_button": {
            "en": "I Understand",
            "zh": "我明白了"
        },
        
        # Step 3
        "step3_badge": {
            "en": "Step 3 / 11",
            "zh": "第 3 / 11 步"
        },
        "step3_title": {
            "en": "Scene Explanation",
            "zh": "场景说明"
        },
        "step3_content": {
            "en": "<p class=\"modal-text\">In this scene, you see <strong>Two People</strong> and <strong>Objects</strong> on the table.</p><p class=\"modal-text\">Task: Judge who owns each object.</p>",
            "zh": "<p class=\"modal-text\">在这个场景中，您可以看到<strong>两个人</strong>和桌上的<strong>物品</strong>。</p><p class=\"modal-text\"><strong>任务</strong>：判断每个物品属于谁。</p>"
        },
        
        # Step 4
        "step4_tooltip_title": {
            "en": "Control Panel Guide",
            "zh": "控制面板指南"
        },
        "step4_tooltip_content": {
            "en": """<p>The slider represents the <strong>probability</strong> of ownership.</p>
                <ul style="line-height: 1.6;">
                    <li>← <strong>Closer to Left</strong>: Higher probability it belongs to the <strong>Left Person</strong>.</li>
                    <li>→ <strong>Closer to Right</strong>: Higher probability it belongs to the <strong>Right Person</strong>.</li>
                    <li><strong>Middle</strong>: Unsure, Ambiguous, or Shared.</li>
                </ul>
                <p style="margin-top:10px; font-size: 13px; color: #666;">
                    <em>(The further you drag, the more certain you are.)</em>
                </p>
                <p><strong>Action: Drag the slider to indicate your confidence, then click "Confirm".</strong></p>""",
            "zh": """<p>滑块表示物品所有权的<strong>可能性</strong>。</p>
                <ul style="line-height: 1.6;">
                    <li>← <strong>靠近左边</strong>：更可能属于<strong>左边的人</strong>。</li>
                    <li>→ <strong>靠近右边</strong>：更可能属于<strong>右边的人</strong>。</li>
                    <li><strong>中间</strong>：不确定、模糊或共享。</li>
                </ul>
                <p style="margin-top:10px; font-size: 13px; color: #666;">
                    <em>（拖动越远，表示您越确定。）</em>
                </p>
                <hr style="margin: 12px 0; border: 0; border-top: 1px solid #eee;">
                <p><strong>如何锁定答案：</strong></p>
                <ul style="line-height: 1.6;">
                    <li><strong>自动锁定：</strong>拖动滑块，松开鼠标后会自动锁定。</li>
                    <li style="color: #d9534f;"><strong>手动锁定：</strong>如果您选择<strong>“不确定”（中间位置）</strong>，请直接手动点击下方的<strong>“锁定”按钮</strong>。</li>
                </ul>
                """
        },
        
        # Step 5 - Modify Choice (Unlock/Re-lock)
        "step5_badge": {
            "en": "Step 5 / 11",
            "zh": "第 5 / 11 步"
        },
        "step5_title": {
            "en": "Modify Choice",
            "zh": "修改已锁定的判断"
        },
        "step5_content": {
            "en": "<p class=\"modal-text\">This item is already <strong>locked</strong> (simulating a completed task).</p><p class=\"modal-text\">If you want to change it, click the black <strong>'Locked' button</strong> to unlock it, then drag the slider again.</p>",
            "zh": "<p class=\"modal-text\">此物品已被<strong>锁定</strong>（模拟自动完成）。</p><p class=\"modal-text\">如需修改，请点击已锁定的<strong>黑色按钮</strong>进行解锁，然后重新拖动滑块。</p>"
        },
        "step5_button": {
            "en": "I Understand",
            "zh": "我明白了"
        },
        
        # Step 6
        "step6_tooltip_title": {
            "en": "Proceed",
            "zh": "继续"
        },
        "step6_tooltip_content": {
            "en": "Click <strong>Save Assignments</strong>.",
            "zh": "点击<strong>保存判断</strong>。"
        },
        
        # Step 7
        "step7_badge": {
            "en": "Step 7 / 11",
            "zh": "第 7 / 11 步"
        },
        "step7_title": {
            "en": "Practice Test",
            "zh": "练习测试"
        },
        "step7_content": {
            "en": "<p class=\"modal-text\">Now, a <strong>check scene</strong>. Rely on intuition.</p>",
            "zh": "<p class=\"modal-text\">现在进行一个<strong>练习场景</strong>。请依靠直觉判断。</p>"
        },
        "step7_button": {
            "en": "Start Test",
            "zh": "开始测试"
        },
        
        # Step 8
        "step8_badge": {
            "en": "Step 8 / 11",
            "zh": "第 8 / 11 步"
        },
        "step8_title": {
            "en": "Practice Scene",
            "zh": "练习场景"
        },
        "step8_intro": {
            "en": "Quick Check:",
            "zh": "快速检查："
        },
        "step8_q1": {
            "en": "1. Who took the green dinosaur toy?",
            "zh": "1. 谁拿走了绿色恐龙玩具？"
        },
        "step8_q2": {
            "en": "2. Pink pig doll closer to?",
            "zh": "2. 粉色小猪娃娃更靠近谁？"
        },
        "step8_option_girl": {
            "en": "Girl",
            "zh": "小女孩"
        },
        "step8_option_boy": {
            "en": "Boy",
            "zh": "小男孩"
        },
        "step8_error": {
            "en": "✗ Incorrect",
            "zh": "✗ 不正确"
        },
        "step8_button": {
            "en": "Start",
            "zh": "开始"
        },
        
        # Step 9
        "step9_badge": {
            "en": "Step 9 / 11",
            "zh": "第 9 / 11 步"
        },
        "step9_title": {
            "en": "Disclaimer",
            "zh": "注意事项"
        },
        "step9_note": {
            "en": "<strong>Note:</strong> There are no right or wrong answers. Rely on first intuition.",
            "zh": "<strong>注意：</strong>没有对错之分，请依靠第一直觉。"
        },
        "step9_content": {
            "en": "<p class=\"modal-text\">Just follow your gut feeling - don't overthink it!</p>",
            "zh": "<p class=\"modal-text\">请跟随你的直觉，认真作答！</p>"
        },
        "step9_button": {
            "en": "Next: Practice",
            "zh": "下一步：练习"
        },
        
        # Step 10 (Fail)
        "step10_badge": {
            "en": "Session Ended",
            "zh": "实验结束"
        },
        "step10_title": {
            "en": "Thank You",
            "zh": "谢谢"
        },
        "step10_content": {
            "en": "<p class=\"modal-text\">Based on your responses, your visual interpretation differs significantly from the baseline required.</p><p class=\"modal-text\">You may close this window.</p>",
            "zh": "<p class=\"modal-text\">根据您的回答，您的视觉解读与所需的基准存在显著差异。</p><p class=\"modal-text\">您可以关闭此窗口。</p>"
        },
        
        # Step 11 (Simulation Intro)
        "step11_badge": {
            "en": "Step 10 / 11",
            "zh": "第 10 / 11 步"
        },
        "step11_title": {
            "en": "Workflow Simulation",
            "zh": "实验练习"
        },
        "step11_content": {
            "en": """<p class="modal-text">We will now simulate the <strong>Real Experiment Workflow</strong>.</p>
                <p class="modal-text"><strong>Your Task:</strong></p>
                <ol style="margin-bottom:20px; line-height:1.6; padding-left:20px;">
                    <li><strong>Observation (5s):</strong> The image will be shown in full size. Please observe the people and objects carefully.</li>
                    <li><strong>Annotation:</strong> Assign ownership for the items on the table.</li>
                </ol>
                <div style="font-size:13px; color:#666; background:#f5f5f5; padding:10px; border-radius:6px;">
                    <em>* This is a practice run. Data will not be recorded.</em>
                </div>""",
            "zh": """<p class="modal-text">现在我们将模拟<strong>真实实验流程</strong>。</p>
                <p class="modal-text"><strong>您的任务：</strong></p>
                <ol style="margin-bottom:20px; line-height:1.6; padding-left:20px;">
                    <li><strong>观察（5秒）：</strong>图像将以全尺寸显示。请仔细观察人物和物品。</li>
                    <li><strong>标注：</strong>为桌上的物品分配所有权。</li>
                </ol>
                <div style="font-size:13px; color:#666; background:#f5f5f5; padding:10px; border-radius:6px;">
                    <em>* 这是练习，数据不会被记录。</em>
                </div>"""
        },
        "step11_button": {
            "en": "Start Simulation",
            "zh": "开始练习"
        },
        
        # Step 13 (Final Ready)
        "step13_badge": {
            "en": "Step 11 / 11",
            "zh": "第 11 / 11 步"
        },
        "step13_title": {
            "en": "Ready for Experiment",
            "zh": "准备开始实验"
        },
        "step13_content": {
            "en": """<div style="text-align:center; margin-bottom:20px;">
                    <span style="font-size:40px;">🚀</span>
                </div>
                <p class="modal-text">You have completed the tutorial.</p>
                <p class="modal-text">There are approximately <strong>24 scenes</strong> in the main experiment, expected to take about 15 minutes.</p>
                <p class="modal-text">Please maintain the same level of attention. Thank you!</p>""",
            "zh": """<div style="text-align:center; margin-bottom:20px;">
                    <span style="font-size:40px;">🚀</span>
                </div>
                <p class="modal-text">您已完成教程。</p>
                <p class="modal-text">正式实验大约有 <strong>24 个场景</strong>，预计 15 分钟。</p>
                <p class="modal-text">请你在实验中保持注意力，认真完成实验！</p>"""
        },
        "step13_button": {
            "en": "Start Main Experiment",
            "zh": "开始正式实验"
        },
        "step13_allocating": {
            "en": "Allocating Scenes...",
            "zh": "正在分配场景..."
        }
    },
    
    # ============================================================
    # ERROR MESSAGES
    # ============================================================
    "errors": {
        "access_denied_title": {
            "en": "Access Denied",
            "zh": "访问被拒绝"
        },
        "access_denied_message": {
            "en": "Based on previous sessions, you are not eligible for this experiment.",
            "zh": "根据之前的会话记录，您不符合参与此实验的条件。"
        },
        "init_error": {
            "en": "Error initializing experiment",
            "zh": "实验初始化错误"
        },
        "network_error": {
            "en": "Network Error",
            "zh": "网络错误"
        },
        "unknown_error": {
            "en": "Unknown error",
            "zh": "未知错误"
        }
    },
    
    # ============================================================
    # FULLSCREEN OVERLAY
    # ============================================================
    "fullscreen": {
        "title": {
            "en": "Fullscreen Required",
            "zh": "需要全屏模式"
        },
        "message": {
            "en": "This experiment requires fullscreen mode for accurate data collection.",
            "zh": "本实验需要全屏模式以确保数据收集的准确性。"
        },
        "button": {
            "en": "Click to Resume Experiment",
            "zh": "点击继续实验"
        }
    },
    
    # ============================================================
    # ATTENTION CHECK FAIL (Legacy - kept for backwards compatibility)
    # ============================================================
    "attention_fail": {
        "title": {
            "en": "Experiment Ended",
            "zh": "实验结束"
        },
        "message": {
            "en": "Thank you for your participation. The experiment session has ended.",
            "zh": "感谢您的参与。实验已结束。"
        }
    },
    
    # ============================================================
    # COMPLETION PAGES (Success, Tutorial Fail, Attention Fail)
    # ============================================================
    "completion": {
        # Success Page
        "success_title": {
            "en": "Experiment Completed",
            "zh": "实验完成"
        },
        "success_header": {
            "en": "Congratulations!",
            "zh": "恭喜您！"
        },
        "success_message": {
            "en": "You have successfully completed all scenes in this experiment.",
            "zh": "您已成功完成本实验的所有场景。"
        },
        "payment_form_title": {
            "en": "Payment Information",
            "zh": "支付信息"
        },
        "field_real_name": {
            "en": "Real Name",
            "zh": "真实姓名"
        },
        "field_phone": {
            "en": "Phone Number",
            "zh": "手机号"
        },
        "field_id_number": {
            "en": "ID Number",
            "zh": "身份证号"
        },
        "field_bank_branch": {
            "en": "Bank Branch",
            "zh": "开户行"
        },
        "field_bank_account": {
            "en": "Bank Account Number",
            "zh": "银行卡号"
        },
        "placeholder_name": {
            "en": "Enter your legal name",
            "zh": "请输入您的真实姓名"
        },
        "placeholder_phone": {
            "en": "11-digit phone number",
            "zh": "11位手机号码"
        },
        "placeholder_id": {
            "en": "18-digit ID number",
            "zh": "18位身份证号"
        },
        "placeholder_bank": {
            "en": "e.g., CCB Hangzhou Branch",
            "zh": "例如：建设银行杭州分行"
        },
        "placeholder_account": {
            "en": "Your bank card number",
            "zh": "您的银行卡号"
        },
        "submit_payment": {
            "en": "Submit Payment Info",
            "zh": "提交支付信息"
        },
        "submitting": {
            "en": "Submitting...",
            "zh": "提交中..."
        },
        "payment_success": {
            "en": "Payment information submitted successfully! You will receive payment within 3-5 business days.",
            "zh": "支付信息提交成功！您将在3-5个工作日内收到报酬。"
        },
        "submitted": {
            "en": "Submitted",
            "zh": "已提交"
        },
        "payment_note": {
            "en": "Your personal information will only be used for payment purposes and will be kept strictly confidential.",
            "zh": "您的个人信息仅用于支付报酬，将被严格保密。"
        },
        "close_hint": {
            "en": "You may now close this window.",
            "zh": "您现在可以关闭此窗口。"
        },
        
        # Tutorial Fail Page
        "tutorial_fail_title": {
            "en": "Session Ended",
            "zh": "实验结束"
        },
        "tutorial_fail_header": {
            "en": "Thank You for Your Time",
            "zh": "感谢您的参与"
        },
        "tutorial_fail_message": {
            "en": "Based on your responses, your visual interpretation differs significantly from the baseline required for this study. Unfortunately, you are not eligible to continue with the main experiment. Thank you for your interest.",
            "zh": "很遗憾，您未通过我们实验的筛选。感谢您的参与。"
        },
        
        # Attention Fail Page
        "attention_fail_title": {
            "en": "Experiment Terminated",
            "zh": "实验终止"
        },
        "attention_fail_header": {
            "en": "Experiment Terminated",
            "zh": "实验已终止"
        },
        "attention_fail_message": {
            "en": "The experiment has been terminated due to inconsistent responses on attention check questions.",
            "zh": "很遗憾，您错过了我们的注意筛选，实验已经被中止。"
        },
        "attention_fail_note": {
            "en": "If you believe this is an error, please contact the research team with your participant ID.",
            "zh": "如果您认为这是一个错误，请联系研究团队并提供您的参与者ID。"
        },
        
        # Generic Page
        "generic_title": {
            "en": "Session Ended",
            "zh": "会话结束"
        },
        "generic_header": {
            "en": "Session Ended",
            "zh": "会话结束"
        },
        "generic_message": {
            "en": "Your session has ended. Thank you for your participation.",
            "zh": "您的会话已结束。感谢您的参与。"
        }
    },
    
    # ============================================================
    # AGENT ROLE LABELS (for display in experiment)
    # ============================================================
    "agent_roles": {
        "girl": {"en": "Girl", "zh": "小女孩"},
        "boy": {"en": "Boy", "zh": "小男孩"},
        "woman": {"en": "Woman", "zh": "成年女人"},
        "man": {"en": "Man", "zh": "成年男人"},
        "grandma": {"en": "Grandma", "zh": "奶奶"},
        "grandpa": {"en": "Grandpa", "zh": "爷爷"},
        "girl_teenager": {"en": "Teen Girl", "zh": "少女"},
        "boy_teenager": {"en": "Teen Boy", "zh": "少年"},
        "person": {"en": "Person", "zh": "人"}
    },
    
    # ============================================================
    # OBJECT CATEGORY LABELS (for display in experiment)
    # ============================================================
    "object_categories": {
        # Toys
        "Toy": {"en": "Toy", "zh": "玩具"},
        # Cups
        "Cup": {"en": "Cup", "zh": "杯子"},
        # Food
        "Food": {"en": "Food", "zh": "食物"},
        # Drinks
        "Drink": {"en": "Drink", "zh": "饮料"},
        # Bags
        "Bag": {"en": "Bag", "zh": "包"},
        # Books & Reading
        "Book": {"en": "Book", "zh": "书"},
        "Opened Book": {"en": "Opened Book", "zh": "打开的书"},
        "Newspaper": {"en": "Newspaper", "zh": "报纸"},
        # Electronics
        "Computer": {"en": "Computer", "zh": "电脑"},
        "Pen": {"en": "Pen", "zh": "笔"},
        "Phone": {"en": "Phone", "zh": "手机"},
        "Radio": {"en": "Radio", "zh": "收音机"},
        "Mouse": {"en": "Mouse", "zh": "鼠标"},
        # Personal items
        "Mirror": {"en": "Mirror", "zh": "镜子"},
        "Perfume": {"en": "Perfume", "zh": "香水"},
        "Comb": {"en": "Comb", "zh": "梳子"},
        "Lipstick": {"en": "Lipstick", "zh": "口红"},
        "Glasses": {"en": "Glasses", "zh": "眼镜"},
        "Cap": {"en": "Cap", "zh": "帽子"},
        # Kitchen
        "Plate": {"en": "Plate", "zh": "盘子"}
    }
}


def get_text(lang: str, key_path: str, **kwargs) -> str:
    """
    Retrieve a translated string.
    
    Args:
        lang: Language code ('en' or 'zh')
        key_path: Dot-separated path like "login.gender" or "tutorial.step1_title"
        **kwargs: Format variables for string interpolation
        
    Returns:
        Translated string, or the key_path if not found
    """
    # Import config for DEFAULT_LANGUAGE
    import config
    if lang not in ('en', 'zh'):
        lang = config.DEFAULT_LANGUAGE  # Default to config setting (Chinese)
    
    keys = key_path.split('.')
    value = TRANSLATIONS
    
    try:
        for key in keys:
            value = value[key]
        
        # Get the language-specific text
        text = value.get(lang, value.get('en', key_path))
        
        # Apply string formatting if kwargs provided
        if kwargs:
            text = text.format(**kwargs)
        
        return text
    except (KeyError, TypeError):
        return key_path


def get_country_options(lang: str) -> list:
    """
    Get country options for the given language.
    Returns list of dicts with 'value' and 'label'.
    """
    countries_data = TRANSLATIONS.get("countries", {})
    options = []
    for key, names in countries_data.items():
        label = names.get(lang, names.get('en', key))
        # Use English value as the stored value for consistency
        value = names.get('en', key)
        options.append({"value": value, "label": label})
    return options

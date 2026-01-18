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
            "en": "Welcome to the <strong>Ownership Cognition Experiment</strong>.<br>For the best experience, switch to full screen.",
            "zh": "欢迎参加<strong>所有权认知实验</strong>。<br>为了获得最佳体验，请切换到全屏模式。"
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
            "en": "We focus on <strong>Psychological Ownership</strong> based on visual intuition.",
            "zh": "我们关注基于视觉直觉的<strong>心理所有权</strong>。"
        },
        "step2_wrong_label": {
            "en": "No External Clues",
            "zh": "不要依赖外部线索"
        },
        "step2_wrong_hint": {
            "en": "Don't guess who bought it",
            "zh": "不要猜测背后是谁买的"
        },
        "step2_correct_label": {
            "en": "Visual Intuition",
            "zh": "视觉直觉"
        },
        "step2_correct_hint": {
            "en": "Judge based on the image",
            "zh": "根据图像判断"
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
            "zh": "<p class=\"modal-text\">在这个场景中，您可以看到<strong>两个人</strong>和桌上的<strong>物品</strong>。</p><p class=\"modal-text\">任务：判断每个物品属于谁。</p>"
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
            "zh": """<p>滑块表示所有权的<strong>可能性</strong>。</p>
                <ul style="line-height: 1.6;">
                    <li>← <strong>靠近左边</strong>：更可能属于<strong>左边的人</strong>。</li>
                    <li>→ <strong>靠近右边</strong>：更可能属于<strong>右边的人</strong>。</li>
                    <li><strong>中间</strong>：不确定、模糊或共享。</li>
                </ul>
                <p style="margin-top:10px; font-size: 13px; color: #666;">
                    <em>（拖动越远，表示您越确定。）</em>
                </p>
                <p><strong>操作：拖动滑块表示您的判断，然后点击"确认"。</strong></p>"""
        },
        
        # Step 5
        "step5_badge": {
            "en": "Step 5 / 11",
            "zh": "第 5 / 11 步"
        },
        "step5_title": {
            "en": "Complete All",
            "zh": "完成所有判断"
        },
        "step5_content": {
            "en": "<p class=\"modal-text\">Assign ownership for <strong>ALL remaining objects</strong>.</p>",
            "zh": "<p class=\"modal-text\">为<strong>所有剩余物品</strong>分配所有权。</p>"
        },
        "step5_button": {
            "en": "OK",
            "zh": "好的"
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
            "zh": "<p class=\"modal-text\">现在进行一个<strong>检查场景</strong>。请依靠直觉判断。</p>"
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
            "en": "<p class=\"modal-text\">No moral judgment involved. Ignore external characteristics.</p>",
            "zh": "<p class=\"modal-text\">不涉及道德判断。请忽略外部特征。</p>"
        },
        "step9_button": {
            "en": "Next: Simulation",
            "zh": "下一步：模拟"
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
            "zh": "工作流模拟"
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
            "zh": "开始模拟"
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
                <p class="modal-text">There are approximately <strong>20 scenes</strong> in the main experiment.</p>
                <p class="modal-text">Please maintain the same level of attention. Thank you!</p>""",
            "zh": """<div style="text-align:center; margin-bottom:20px;">
                    <span style="font-size:40px;">🚀</span>
                </div>
                <p class="modal-text">您已完成教程。</p>
                <p class="modal-text">正式实验大约有 <strong>20 个场景</strong>。</p>
                <p class="modal-text">请保持同样的注意力。谢谢！</p>"""
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
    # ATTENTION CHECK FAIL
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

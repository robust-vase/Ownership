"""
Login Page Generator
====================
Generates the participant registration form.
Collecting: Participant ID, Gender, DOB (Year-Month), Status, Education.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ui_components import render_common_css
from core.translations import get_text

def generate_login_html(error_message=None, lang='zh'):
    common_css = render_common_css()
    
    # Get translated text
    t = lambda key: get_text(lang, f"login.{key}")
    
    # Determine the other language for switcher
    other_lang = 'zh' if lang == 'en' else 'en'
    switch_label = t('lang_switcher')
    
    # Generate year options (2015 as start, going back to 1950)
    year_options = "".join([f'<option value="{y}">{y}</option>' for y in range(2015, 1949, -1)])
    
    # Generate month options
    month_options = "".join([f'<option value="{m:02d}">{m}</option>' for m in range(1, 13)])

    login_css = """
        /* === 关键修改：强制允许滚动，适配小屏幕 === */
        body {
            overflow-y: auto !important; /* 覆盖全局的 hidden 设置 */
            min-height: 100vh;
            padding-bottom: 60px; /* 底部留出空间，防止按钮贴底 */
            background-attachment: fixed; /* 背景固定 */
        }

        .login-container {
            max-width: 540px;
            margin: 40px auto;
            background: white;
            padding: 40px;
            border-radius: 16px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            position: relative;
        }

        /* 针对垂直高度较小的屏幕（如笔记本）进行优化 */
        @media (max-height: 800px) {
            .login-container {
                margin: 20px auto; /* 减小顶部距离 */
                padding: 25px;     /* 减小内边距 */
            }
            .header {
                padding: 10px 0;   /* 压缩头部 */
            }
            h2 {
                margin-bottom: 15px; /* 压缩标题间距 */
                font-size: 22px;
            }
            .consent-box {
                padding: 10px;
                margin-bottom: 15px;
            }
        }

        .form-group { margin-bottom: 20px; }
        .form-label { display: block; margin-bottom: 8px; font-weight: 600; color: #333; }
        .form-control {
            width: 100%; padding: 12px; border: 1px solid #ddd;
            border-radius: 8px; font-size: 16px; box-sizing: border-box;
            transition: border-color 0.2s;
        }
        .form-control:focus { border-color: #667eea; outline: none; }
        .form-control::placeholder { color: #aaa; }
        
        .btn-primary {
            width: 100%; padding: 14px; background: #1a1a1a;
            color: white; border: none; border-radius: 8px;
            font-size: 16px; font-weight: 600; cursor: pointer;
            margin-top: 20px;
            transition: all 0.2s;
        }
        .btn-primary:hover { background: #000; transform: translateY(-1px); }
        .btn-primary:disabled { background: #ccc; cursor: not-allowed; transform: none; }
        
        .error-msg { color: #e53e3e; background: #fff5f5; padding: 10px; border-radius: 6px; margin-bottom: 20px; text-align: center; }
        h2 { text-align: center; margin-bottom: 30px; color: #1a1a1a; }
        
        .lang-switcher {
            position: absolute;
            top: 20px;
            right: 20px;
            padding: 8px 16px;
            background: rgba(255,255,255,0.9);
            border: 1px solid #ddd;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 600;
            color: #333;
            text-decoration: none;
            transition: all 0.2s;
            z-index: 10;
        }
        .lang-switcher:hover {
            background: #f0f0f0;
            border-color: #ccc;
        }
        .dob-row {
            display: flex;
            gap: 12px;
        }
        .dob-row select {
            flex: 1;
        }
        .consent-box {
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 10px;
            padding: 16px;
            margin-bottom: 20px;
        }
        .consent-title {
            font-weight: 600;
            color: #333;
            margin-bottom: 10px;
            font-size: 15px;
        }
        .consent-content {
            font-size: 13px;
            color: #555;
            line-height: 1.6;
            margin-bottom: 12px;
            max-height: 150px;       /* 如果内容太长，内部也可以滚 */
            overflow-y: auto;        /* 允许知情同意书内部滚动 */
        }
        .consent-checkbox {
            display: flex;
            align-items: flex-start;
            gap: 10px;
        }
        .consent-checkbox input {
            margin-top: 3px;
            width: 18px;
            height: 18px;
            cursor: pointer;
            flex-shrink: 0;
        }
        .consent-checkbox label {
            font-size: 14px;
            color: #333;
            cursor: pointer;
            line-height: 1.5;
        }
    """

    error_html = f'<div class="error-msg">{error_message}</div>' if error_message else ''

    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{t('page_title')}</title>
    <style>
        {common_css}
        {login_css}
    </style>
</head>
<body>
    <a href="/login?lang={other_lang}" class="lang-switcher">{switch_label}</a>
    
    <div class="header">
        <h1>{t('header')}</h1>
    </div>
    
    <div class="login-container">
        <h2>{t('form_title')}</h2>
        {error_html}
        
        <div class="consent-box">
            <div class="consent-title">{t('consent_title')}</div>
            <div class="consent-content">{t('consent_content')}</div>
            <div class="consent-checkbox">
                <input type="checkbox" id="consent-check" required>
                <label for="consent-check">{t('consent_checkbox')}</label>
            </div>
        </div>
        
        <form method="POST" action="/login?lang={lang}" id="login-form">
            <input type="hidden" name="language" value="{lang}">
            
            <div class="form-group">
                <label class="form-label">{t('participant_id')}</label>
                <input type="text" name="participant_id" class="form-control" 
                       placeholder="{t('participant_id_placeholder')}" required>
            </div>
            
            <div class="form-group">
                <label class="form-label">{t('gender')}</label>
                <select name="gender" class="form-control" required>
                    <option value="" disabled selected>{t('select_placeholder')}</option>
                    <option value="Male">{t('gender_male')}</option>
                    <option value="Female">{t('gender_female')}</option>
                </select>
            </div>        

            <div class="form-group">
                <label class="form-label">{t('dob')}</label>
                <div class="dob-row">
                    <select name="dob_year" class="form-control" required>
                        <option value="" disabled selected>{"Year" if lang == 'en' else "年"}</option>
                        {year_options}
                    </select>
                    <select name="dob_month" class="form-control" required>
                        <option value="" disabled selected>{"Month" if lang == 'en' else "月"}</option>
                        {month_options}
                    </select>
                </div>
            </div>

            <div class="form-group">
                <label class="form-label">{t('status')}</label>
                <select name="status" class="form-control" required>
                    <option value="" disabled selected>{t('select_placeholder')}</option>
                    <option value="Student">{t('status_student')}</option>
                    <option value="Employed">{t('status_employed')}</option>
                    <option value="Other">{t('status_other')}</option>
                </select>
            </div>

            <div class="form-group">
                <label class="form-label">{t('education')}</label>
                <select name="education" class="form-control" required>
                    <option value="" disabled selected>{t('select_placeholder')}</option>
                    <option value="High School">{t('edu_high_school')}</option>
                    <option value="Bachelor">{t('edu_bachelor')}</option>
                    <option value="Master">{t('edu_master')}</option>
                    <option value="PhD">{t('edu_phd')}</option>
                    <option value="Other">{t('edu_other')}</option>
                </select>
            </div>

            <button type="submit" class="btn-primary" id="submit-btn" disabled>{t('submit_button')}</button>
        </form>
    </div>
    
    <script>
        // Enable submit button only when consent is checked
        const consentCheck = document.getElementById('consent-check');
        const submitBtn = document.getElementById('submit-btn');
        
        consentCheck.addEventListener('change', function() {{
            submitBtn.disabled = !this.checked;
        }});
    </script>
</body>
</html>
"""


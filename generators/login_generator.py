"""
Login Page Generator
====================
Generates the participant registration form.
Collecting: Gender, DOB, Status, Education, Nationality.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from static_assets.ui_components import render_common_css
from core.translations import get_text, get_country_options

def generate_login_html(error_message=None, lang='zh'):
    common_css = render_common_css()
    
    # Build country options from translations
    countries = get_country_options(lang)
    country_options = "".join([f'<option value="{c["value"]}">{c["label"]}</option>' for c in countries])
    
    # Get translated text
    t = lambda key: get_text(lang, f"login.{key}")
    
    # Determine the other language for switcher
    other_lang = 'zh' if lang == 'en' else 'en'
    switch_label = t('lang_switcher')

    login_css = """
        .login-container {
            max-width: 500px;
            margin: 60px auto;
            background: white;
            padding: 40px;
            border-radius: 16px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }
        .form-group { margin-bottom: 20px; }
        .form-label { display: block; margin-bottom: 8px; font-weight: 600; color: #333; }
        .form-control {
            width: 100%; padding: 12px; border: 1px solid #ddd;
            border-radius: 8px; font-size: 16px; box-sizing: border-box;
            transition: border-color 0.2s;
        }
        .form-control:focus { border-color: #667eea; outline: none; }
        .btn-primary {
            width: 100%; padding: 14px; background: #1a1a1a;
            color: white; border: none; border-radius: 8px;
            font-size: 16px; font-weight: 600; cursor: pointer;
            margin-top: 20px;
        }
        .btn-primary:hover { background: #000; }
        .error-msg { color: #e53e3e; background: #fff5f5; padding: 10px; border-radius: 6px; margin-bottom: 20px; text-align: center; }
        h2 { text-align: center; margin-bottom: 30px; color: #1a1a1a; }
        .hint { font-size: 12px; color: #666; margin-top: 4px; }
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
        }
        .lang-switcher:hover {
            background: #f0f0f0;
            border-color: #ccc;
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
        <form method="POST" action="/login?lang={lang}">
            <input type="hidden" name="language" value="{lang}">
            
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
                <input type="date" name="dob" class="form-control" required>
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

            <div class="form-group">
                <label class="form-label">{t('nationality')}</label>
                <select name="nationality" class="form-control" required>
                    <option value="" disabled selected>{t('select_placeholder')}</option>
                    {country_options}
                </select>
            </div>

            <button type="submit" class="btn-primary">{t('submit_button')}</button>
        </form>
    </div>
</body>
</html>
"""
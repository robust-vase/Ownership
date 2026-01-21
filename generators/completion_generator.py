"""
Completion Page Generator
=========================
Generates HTML pages for experiment completion, tutorial failure, and attention check failure.
"""
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.translations import get_text


def generate_completion_html(status: str, lang: str = 'en') -> str:
    """
    Generate completion/exit page HTML based on status.
    
    Args:
        status: One of 'success', 'tutorial_fail', 'attention_fail'
        lang: Language code ('en' or 'zh')
        
    Returns:
        Complete HTML string
    """
    if status == 'success':
        return _generate_success_page(lang)
    elif status == 'tutorial_fail':
        return _generate_tutorial_fail_page(lang)
    elif status == 'attention_fail':
        return _generate_attention_fail_page(lang)
    else:
        return _generate_generic_end_page(lang)


def _generate_success_page(lang: str) -> str:
    """Generate success page with payment form."""
    t = lambda key: get_text(lang, f"completion.{key}")
    
    page_title = t('success_title')
    header_icon = "🎉"
    header_text = t('success_header')
    congrats_msg = t('success_message')
    form_title = t('payment_form_title')
    
    # Form field labels
    real_name_label = t('field_real_name')
    phone_label = t('field_phone')
    id_number_label = t('field_id_number')
    bank_branch_label = t('field_bank_branch')
    bank_account_label = t('field_bank_account')
    submit_btn = t('submit_payment')
    submitting_text = t('submitting')
    success_msg = t('payment_success')
    
    # Placeholders
    name_placeholder = t('placeholder_name')
    phone_placeholder = t('placeholder_phone')
    id_placeholder = t('placeholder_id')
    bank_placeholder = t('placeholder_bank')
    account_placeholder = t('placeholder_account')
    
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }}
        .card {{
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 500px;
            width: 100%;
            overflow: hidden;
        }}
        .card-header {{
            background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
            color: white;
            padding: 40px 30px;
            text-align: center;
        }}
        .card-header .icon {{ font-size: 64px; margin-bottom: 16px; display: block; }}
        .card-header h1 {{ font-size: 28px; font-weight: 700; margin-bottom: 8px; }}
        .card-header p {{ font-size: 16px; opacity: 0.9; }}
        .card-body {{
            padding: 30px;
        }}
        .form-title {{
            font-size: 18px;
            font-weight: 600;
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #eee;
        }}
        .form-group {{
            margin-bottom: 20px;
        }}
        .form-group label {{
            display: block;
            font-size: 14px;
            font-weight: 600;
            color: #555;
            margin-bottom: 8px;
        }}
        .form-group input {{
            width: 100%;
            padding: 14px 16px;
            font-size: 16px;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            transition: all 0.2s;
            outline: none;
        }}
        .form-group input:focus {{
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }}
        .form-group input::placeholder {{
            color: #aaa;
        }}
        .submit-btn {{
            width: 100%;
            padding: 16px;
            font-size: 16px;
            font-weight: 600;
            color: white;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border: none;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.2s;
            margin-top: 10px;
        }}
        .submit-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }}
        .submit-btn:disabled {{
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }}
        .status-message {{
            margin-top: 15px;
            padding: 12px;
            border-radius: 8px;
            text-align: center;
            font-size: 14px;
            display: none;
        }}
        .status-message.success {{
            background: #d4edda;
            color: #155724;
            display: block;
        }}
        .status-message.error {{
            background: #f8d7da;
            color: #721c24;
            display: block;
        }}
        .note {{
            margin-top: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
            font-size: 13px;
            color: #666;
            line-height: 1.6;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="card-header">
            <span class="icon">{header_icon}</span>
            <h1>{header_text}</h1>
            <p>{congrats_msg}</p>
        </div>
        <div class="card-body">
            <h2 class="form-title">💳 {form_title}</h2>
            <form id="payment-form">
                <div class="form-group">
                    <label for="real_name">{real_name_label} *</label>
                    <input type="text" id="real_name" name="real_name" required placeholder="{name_placeholder}">
                </div>
                <div class="form-group">
                    <label for="phone">{phone_label} *</label>
                    <input type="tel" id="phone" name="phone" required placeholder="{phone_placeholder}" pattern="[0-9]{{11}}">
                </div>
                <div class="form-group">
                    <label for="id_number">{id_number_label} *</label>
                    <input type="text" id="id_number" name="id_number" required placeholder="{id_placeholder}">
                </div>
                <div class="form-group">
                    <label for="bank_branch">{bank_branch_label} *</label>
                    <input type="text" id="bank_branch" name="bank_branch" required placeholder="{bank_placeholder}">
                </div>
                <div class="form-group">
                    <label for="bank_account">{bank_account_label} *</label>
                    <input type="text" id="bank_account" name="bank_account" required placeholder="{account_placeholder}">
                </div>
                <button type="submit" class="submit-btn" id="submit-btn">{submit_btn}</button>
            </form>
            <div class="status-message" id="status-message"></div>
            <div class="note">
                {get_text(lang, 'completion.payment_note')}
            </div>
        </div>
    </div>
    
    <script>
        document.getElementById('payment-form').addEventListener('submit', function(e) {{
            e.preventDefault();
            
            const btn = document.getElementById('submit-btn');
            const statusMsg = document.getElementById('status-message');
            
            btn.disabled = true;
            btn.textContent = '{submitting_text}';
            statusMsg.className = 'status-message';
            statusMsg.style.display = 'none';
            
            const formData = {{
                real_name: document.getElementById('real_name').value.trim(),
                phone: document.getElementById('phone').value.trim(),
                id_number: document.getElementById('id_number').value.trim(),
                bank_branch: document.getElementById('bank_branch').value.trim(),
                bank_account: document.getElementById('bank_account').value.trim()
            }};
            
            fetch('/api/submit_payment', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify(formData),
                credentials: 'same-origin'
            }})
            .then(res => res.json())
            .then(data => {{
                if (data.status === 'success') {{
                    statusMsg.className = 'status-message success';
                    statusMsg.textContent = '{success_msg}';
                    statusMsg.style.display = 'block';
                    btn.textContent = '✓ {get_text(lang, "completion.submitted")}';
                    // Disable form
                    document.querySelectorAll('#payment-form input').forEach(input => input.disabled = true);
                }} else {{
                    throw new Error(data.error || 'Unknown error');
                }}
            }})
            .catch(err => {{
                statusMsg.className = 'status-message error';
                statusMsg.textContent = err.message;
                statusMsg.style.display = 'block';
                btn.disabled = false;
                btn.textContent = '{submit_btn}';
            }});
        }});
    </script>
</body>
</html>
"""


def _generate_tutorial_fail_page(lang: str) -> str:
    """Generate tutorial failure page (visual check failed)."""
    t = lambda key: get_text(lang, f"completion.{key}")
    
    page_title = t('tutorial_fail_title')
    header_text = t('tutorial_fail_header')
    message = t('tutorial_fail_message')
    
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f4f6f8;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }}
        .card {{
            background: white;
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            max-width: 500px;
            width: 100%;
            padding: 50px 40px;
            text-align: center;
        }}
        .icon {{ font-size: 64px; margin-bottom: 24px; }}
        h1 {{ 
            font-size: 24px; 
            color: #2d3748; 
            margin-bottom: 16px;
            font-weight: 700;
        }}
        p {{ 
            font-size: 16px; 
            color: #718096; 
            line-height: 1.7;
            margin-bottom: 24px;
        }}
        .hint {{
            font-size: 14px;
            color: #a0aec0;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">📋</div>
        <h1>{header_text}</h1>
        <p>{message}</p>
        <div class="hint">{get_text(lang, 'completion.close_hint')}</div>
    </div>
    <script>
        // Exit fullscreen if active
        if (document.exitFullscreen) {{
            document.exitFullscreen().catch(e => {{}});
        }}
    </script>
</body>
</html>
"""


def _generate_attention_fail_page(lang: str) -> str:
    """Generate attention check failure page."""
    t = lambda key: get_text(lang, f"completion.{key}")
    
    page_title = t('attention_fail_title')
    header_text = t('attention_fail_header')
    message = t('attention_fail_message')
    
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_title}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f4f6f8;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }}
        .card {{
            background: white;
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            max-width: 500px;
            width: 100%;
            padding: 50px 40px;
            text-align: center;
        }}
        .icon {{ font-size: 64px; margin-bottom: 24px; }}
        h1 {{ 
            font-size: 24px; 
            color: #2d3748; 
            margin-bottom: 16px;
            font-weight: 700;
        }}
        p {{ 
            font-size: 16px; 
            color: #718096; 
            line-height: 1.7;
            margin-bottom: 24px;
        }}
        .warning-box {{
            background: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 8px;
            padding: 15px;
            margin-top: 20px;
            font-size: 14px;
            color: #856404;
        }}
        .hint {{
            font-size: 14px;
            color: #a0aec0;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">⚠️</div>
        <h1>{header_text}</h1>
        <p>{message}</p>
        <div class="warning-box">{get_text(lang, 'completion.attention_fail_note')}</div>
        <div class="hint">{get_text(lang, 'completion.close_hint')}</div>
    </div>
    <script>
        // Exit fullscreen if active
        if (document.exitFullscreen) {{
            document.exitFullscreen().catch(e => {{}});
        }}
    </script>
</body>
</html>
"""


def _generate_generic_end_page(lang: str) -> str:
    """Generate a generic end page for unknown status."""
    t = lambda key: get_text(lang, f"completion.{key}")
    
    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{t('generic_title')}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f4f6f8;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }}
        .card {{
            background: white;
            padding: 40px;
            border-radius: 16px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            text-align: center;
        }}
        h1 {{ color: #2d3748; margin-bottom: 16px; }}
        p {{ color: #718096; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>{t('generic_header')}</h1>
        <p>{t('generic_message')}</p>
    </div>
</body>
</html>
"""

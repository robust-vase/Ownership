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

def generate_login_html(error_message=None):
    common_css = render_common_css()
    
    # 国家列表 (按常用和字母排序)
    countries = [
        "China (中国)", "United States (美国)", "United Kingdom (英国)", 
        "Australia (澳大利亚)", "Canada (加拿大)", "Germany (德国)", 
        "France (法国)", "Japan (日本)", "South Korea (韩国)", 
        "India (印度)", "Russia (俄罗斯)", "Brazil (巴西)",
        "Other (其他)"
    ]
    country_options = "".join([f'<option value="{c}">{c}</option>' for c in countries])

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
    """

    error_html = f'<div class="error-msg">{error_message}</div>' if error_message else ''

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Participant Registration</title>
    <style>
        {common_css}
        {login_css}
    </style>
</head>
<body>
    <div class="header">
        <h1>🧠 Cognition Experiment</h1>
    </div>
    
    <div class="login-container">
        <h2>Participant Info</h2>
        {error_html}
        <form method="POST" action="/login">
            
            <div class="form-group">
                <label class="form-label">Gender (性别)</label>
                <select name="gender" class="form-control" required>
                    <option value="" disabled selected>Select...</option>
                    <option value="Male">Male (男)</option>
                    <option value="Female">Female (女)</option>
                    </select>
            </div>        

            <div class="form-group">
                <label class="form-label">Date of Birth (出生年月)</label>
                <input type="date" name="dob" class="form-control" required>
            </div>

            <div class="form-group">
                <label class="form-label">Current Status (身份)</label>
                <select name="status" class="form-control" required>
                    <option value="" disabled selected>Select...</option>
                    <option value="Student">Student (在校学生)</option>
                    <option value="Employed">Employed (在职人员)</option>
                    <option value="Other">Other (其他)</option>
                </select>
            </div>

            <div class="form-group">
                <label class="form-label">Education Level (最高学历)</label>
                <select name="education" class="form-control" required>
                    <option value="" disabled selected>Select...</option>
                    <option value="High School">High School (高中/中专)</option>
                    <option value="Bachelor">Bachelor (本科)</option>
                    <option value="Master">Master (硕士)</option>
                    <option value="PhD">PhD (博士)</option>
                    <option value="Other">Other (其他)</option>
                </select>
            </div>

            <div class="form-group">
                <label class="form-label">Nationality (国籍)</label>
                <select name="nationality" class="form-control" required>
                    <option value="" disabled selected>Select...</option>
                    {country_options}
                </select>
            </div>

            <button type="submit" class="btn-primary">Start Experiment</button>
        </form>
    </div>
</body>
</html>
"""
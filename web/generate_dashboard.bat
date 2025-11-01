@echo off
REM Generate Dashboard HTML with Scene Selector
echo ============================================================
echo Generating Dashboard HTML
echo ============================================================
echo.

D:\ProgramData\miniconda3\Scripts\conda.exe run -p C:\Users\Vase\.conda\envs\tongsim --no-capture-output python "%~dp0generate_html.py"

echo.
echo ============================================================
echo Generation Complete!
echo ============================================================
echo.
pause

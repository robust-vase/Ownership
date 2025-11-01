@echo off
REM Start Flask Server with Scene Selector Feature
echo ============================================================
echo Starting Flask Server
echo ============================================================
echo.
echo Server will be available at:
echo   http://localhost:5000/dashboard.html
echo.
echo Press Ctrl+C to stop the server
echo ============================================================
echo.

D:\ProgramData\miniconda3\Scripts\conda.exe run -p C:\Users\Vase\.conda\envs\tongsim --no-capture-output python "%~dp0server.py"

@echo off
cd /d "%~dp0"
echo Starting Desktop Companion...
python main.py
if errorlevel 1 (
    echo.
    echo [ERROR] App exited with an error. Check config.json.
    pause
)

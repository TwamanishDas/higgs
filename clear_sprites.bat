@echo off
cd /d "%~dp0"
echo Clearing cached sprites...
if exist sprites\ (
    del /q sprites\*.gif >nul 2>&1
    del /q sprites\*.png >nul 2>&1
    echo Done. Sprites will re-download as HD on next run.
) else (
    echo No sprites folder found.
)
pause

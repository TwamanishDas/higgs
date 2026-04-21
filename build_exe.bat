@echo off
cd /d "%~dp0"
echo ============================================
echo  Building standalone .exe with PyInstaller
echo ============================================

python -m pip install pyinstaller --quiet

pyinstaller --noconfirm --onedir --windowed ^
    --name "DesktopCompanion" ^
    --add-data "config.json;." ^
    --hidden-import "win32timezone" ^
    --hidden-import "pkg_resources.py2_warn" ^
    main.py

echo.
if exist "dist\DesktopCompanion\DesktopCompanion.exe" (
    echo [OK] Build successful!
    echo Output: dist\DesktopCompanion\
    echo Copy the entire dist\DesktopCompanion\ folder to run on any Windows machine.
    echo Edit config.json inside that folder with your Azure credentials.
) else (
    echo [ERROR] Build failed. Check output above.
)
pause

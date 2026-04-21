@echo off
echo ============================================
echo  Desktop Companion - Setup
echo ============================================

:: ---- Check for Python ----
python --version >nul 2>&1
if errorlevel 1 goto install_python

:: Verify version is 3.11+
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
for /f "tokens=1,2 delims=." %%a in ("%PYVER%") do (
    set PY_MAJOR=%%a
    set PY_MINOR=%%b
)
if %PY_MAJOR% LSS 3 goto install_python
if %PY_MAJOR% EQU 3 if %PY_MINOR% LSS 11 goto install_python

echo [OK] Python %PYVER% found.
goto deps

:install_python
echo [INFO] Python 3.11 not found. Downloading installer...

:: Use PowerShell to download the Python 3.11 installer
set PYTHON_URL=https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe
set PYTHON_INSTALLER=%TEMP%\python-3.11.9-amd64.exe

powershell -NoProfile -Command ^
    "Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%PYTHON_INSTALLER%' -UseBasicParsing"

if not exist "%PYTHON_INSTALLER%" (
    echo [ERROR] Download failed. Check your internet connection.
    echo Manually install Python 3.11+ from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [INFO] Running Python installer (silent, adds to PATH)...
"%PYTHON_INSTALLER%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0

:: Reload PATH so python is findable in this session
call refreshenv >nul 2>&1
set "PATH=%LOCALAPPDATA%\Programs\Python\Python311;%LOCALAPPDATA%\Programs\Python\Python311\Scripts;%PATH%"

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python install succeeded but python is not on PATH yet.
    echo Please close this window, open a new Command Prompt, and run setup.bat again.
    pause
    exit /b 1
)

echo [OK] Python installed successfully.

:deps
:: Upgrade pip silently
echo Upgrading pip...
python -m pip install --upgrade pip --quiet

:: Install dependencies
echo Installing dependencies...
python -m pip install -r requirements.txt

if errorlevel 1 (
    echo [ERROR] Failed to install dependencies. See errors above.
    pause
    exit /b 1
)

echo.
echo ============================================
echo  Setup complete!
echo.
echo  NEXT STEP: Open config.json and fill in:
echo    - azure.endpoint
echo    - azure.api_key
echo    - azure.deployment
echo.
echo  Then run:  run.bat
echo ============================================
pause

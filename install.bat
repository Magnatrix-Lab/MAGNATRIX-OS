@echo off
REM MAGNATRIX-OS Windows Installer
REM Private Uncensored Agentic AI Operating System

title MAGNATRIX-OS Installer

echo.
echo  __  __                                   _       ____   _____ ____
echo ^|  \/  ^| __ _ _ __ ___  _   _ _ __   __ _^| ^|_ ___/ ___^| ^|_   _/ ___^|
echo ^| ^|\/ ^| ^|/ _^' ^| ^'_ \ _ \^| ^| ^| ^| ^'_ \ / _^' ^| __/ _ \___ \   ^| ^| \___ echo ^| ^|  ^| ^| (_^| ^| ^| ^| ^| ^|^| ^| ^|^| ^| ^| ^| ^| ^| ^| ^| ^| ^| ^|  __/___) ^|  ^| ^|  ___)^|
echo ^|_^|  ^|_^|\__,_^|_^| ^|_^| ^|_^|\__,_^|_^| ^|_^|\__, ^|\__\___^|____/   ^|_^| ^|____/
echo                                      ^|___/
echo.
echo MAGNATRIX-OS Installer for Windows
echo ===================================
echo.

set INSTALL_DIR=%USERPROFILE%\MAGNATRIX-OS
set DATA_DIR=%USERPROFILE%\.magnatrix
set PYTHON_MIN=3.10

echo [INFO] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERR] Python not found. Please install Python 3.10+ from https://python.org
    pause
    exit /b 1
)

for /f "tokens=2" %%a in ('python --version') do set PYVER=%%a
echo [OK] Python %PYVER% found

echo [INFO] Checking Git...
git --version >nul 2>&1
if errorlevel 1 (
    echo [ERR] Git not found. Please install Git from https://git-scm.com
    pause
    exit /b 1
)
echo [OK] Git found

echo [INFO] Cloning repository...
if exist "%INSTALL_DIR%\.git" (
    echo [INFO] Existing install found, updating...
    cd /d "%INSTALL_DIR%"
    git fetch origin
    git reset --hard origin/main
) else (
    rmdir /s /q "%INSTALL_DIR%" 2>nul
    git clone --depth 1 https://github.com/Magnatrix-Lab/MAGNATRIX-OS.git "%INSTALL_DIR%"
)
echo [OK] Repository ready

echo [INFO] Setting up data directory...
mkdir "%DATA_DIR%\models" 2>nul
mkdir "%DATA_DIR%\knowledge" 2>nul
mkdir "%DATA_DIR%\logs" 2>nul
mkdir "%DATA_DIR%\config" 2>nul
mkdir "%DATA_DIR%epos" 2>nul
mkdir "%DATA_DIR%ault" 2>nul
echo [OK] Data directory ready

echo [INFO] Creating Python virtual environment...
cd /d "%INSTALL_DIR%"
python -m venv .venv 2>nul
if not exist ".venv\Scriptsctivate.bat" (
    echo [ERR] Failed to create virtual environment
    pause
    exit /b 1
)
echo [OK] Virtual environment created

echo [INFO] Installing Python dependencies...
call .venv\Scriptsctivate.bat
pip install --no-cache-dir --upgrade pip setuptools wheel >nul 2>&1
pip install --no-cache-dir -e . >nul 2>&1
echo [OK] Dependencies installed

echo [INFO] Creating launcher...
set LAUNCHER=%USERPROFILE%\.localin\magnatrix.bat
mkdir "%USERPROFILE%\.localin" 2>nul
(
echo @echo off
echo set INSTALL_DIR=%INSTALL_DIR%
echo set DATA_DIR=%DATA_DIR%
echo cd /d "%%INSTALL_DIR%%"
echo call .venv\Scriptsctivate.bat
echo if "%%1"=="boot" (
echo     python magnatrix.py boot %%*
echo ^) else if "%%1"=="status" (
echo     python magnatrix.py status
echo ^) else if "%%1"=="test" (
echo     python testsun_all_tests.py
echo ^) else if "%%1"=="update" (
echo     git fetch origin ^&^& git reset --hard origin/main
echo     pip install --no-cache-dir -e . ^>nul 2^>^&1
echo     echo MAGNATRIX-OS updated.
echo ^) else (
echo     echo MAGNATRIX-OS — Super AI Control Interface
echo     echo Usage: magnatrix ^<command^>
echo     echo   boot     Start MAGNATRIX-OS
echo     echo   test     Run tests
echo     echo   status   Show layer status
echo     echo   update   Update to latest
echo     echo   help     Show this help
echo ^)
) > "%LAUNCHER%"
echo [OK] Launcher installed: %LAUNCHER%

echo.
echo =========================================
echo MAGNATRIX-OS installed successfully!
echo =========================================
echo.
echo Installation: %INSTALL_DIR%
echo Data:         %DATA_DIR%
echo Launcher:     %LAUNCHER%
echo.
echo Quick start:
echo   magnatrix boot     Start MAGNATRIX-OS
echo   magnatrix status   Show system status
echo   magnatrix test     Run tests
echo.
pause

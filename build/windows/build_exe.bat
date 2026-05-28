@echo off
REM MAGNATRIX-OS Windows Build Script
REM ═══════════════════════════════════
REM Builds .exe folder via PyInstaller.
REM Requires: Python 3.11+, PyInstaller, pillow, pystray
REM
REM Usage:  build_exe.bat [clean]

setlocal EnableDelayedExpansion

echo ============================================
echo  MAGNATRIX-OS Windows Build
echo ============================================

set REPO_ROOT=%~dp0..\..
cd /d "%REPO_ROOT%"

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH
    exit /b 1
)

:: Install build deps if missing
echo [1/5] Installing build dependencies...
python -m pip install -q pyinstaller pillow pystray websockets aiohttp httpx 2>nul

:: Clean previous build if requested
if /i "%1"=="clean" (
    echo [CLEAN] Removing old build artifacts...
    rmdir /s /q build\windows\build 2>nul
    rmdir /s /q dist\MAGNATRIX-OS 2>nul
)

:: Generate icon if missing
set ICON_PATH=%~dp0magnatrix.ico
if not exist "%ICON_PATH%" (
    echo [2/5] Generating icon stub...
    python -c "import PIL.Image as Image; img=Image.new('RGB',(64,64),'black'); img.save('%~dp0magnatrix.ico')" 2>nul
    if not exist "%ICON_PATH%" (
        echo [WARN] Could not generate icon — using default
    )
)

:: Build
echo [3/5] Running PyInstaller...
python -m PyInstaller --clean "%~dp0magnatrix.spec" --distpath "%~dp0dist" --workpath "%~dp0build" -y
if errorlevel 1 (
    echo [ERROR] PyInstaller build failed
    exit /b 1
)

echo [4/5] Build complete!
echo Output: %~dp0dist\MAGNATRIX-OS\MAGNATRIX-OS.exe

:: Optional: Build NSIS installer
echo [5/5] Checking NSIS...
where makensis >nul 2>&1
if errorlevel 0 (
    echo Building installer...
    makensis "%~dp0installer.nsi"
    if exist "%~dp0dist\MAGNATRIX-OS-Setup.exe" (
        echo Installer: %~dp0dist\MAGNATRIX-OS-Setup.exe
    )
) else (
    echo [SKIP] NSIS not found — skipping installer. Install NSIS from https://nsis.sourceforge.io/
)

echo ============================================
echo  Build finished successfully!
echo ============================================
pause
endlocal

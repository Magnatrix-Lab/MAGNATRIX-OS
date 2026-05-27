#requires -Version 5.1
# ═══════════════════════════════════════════════════════════════════════════════
# MAGNATRIX-OS Installer — Windows PowerShell
# ═══════════════════════════════════════════════════════════════════════════════
# Usage:
#   iwr -useb https://raw.githubusercontent.com/Magnatrix-Lab/MAGNATRIX-OS/main/install.ps1 | iex
#   # Or locally:
#   .\install.ps1
# ═══════════════════════════════════════════════════════════════════════════════

param(
    [string]$InstallDir = "$env:USERPROFILE\MAGNATRIX-OS",
    [string]$DataDir = "$env:USERPROFILE\.magnatrix"
)

$ErrorActionPreference = "Stop"

function Write-Info    { param($m) Write-Host "[INFO] $m" -ForegroundColor Cyan }
function Write-Ok      { param($m) Write-Host "[OK]   $m" -ForegroundColor Green }
function Write-Warn    { param($m) Write-Host "[WARN] $m" -ForegroundColor Yellow }
function Write-Err     { param($m) Write-Host "[ERR]  $m" -ForegroundColor Red }

function Check-Deps {
    Write-Info "Checking dependencies..."
    $missing = @()

    # Python
    $py = Get-Command python -ErrorAction SilentlyContinue
    if (-not $py) {
        $py = Get-Command python3 -ErrorAction SilentlyContinue
    }
    if (-not $py) {
        $missing += "python3"
    } else {
        $ver = & $py.Source -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
        if ([version]$ver -lt [version]"3.10") {
            Write-Err "Python $ver found, but >= 3.10 required"
            $missing += "python3 (>= 3.10)"
        }
    }

    # Git
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        $missing += "git"
    }

    # Docker (optional)
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
        Write-Warn "Docker not found. Docker mode unavailable."
    }

    if ($missing.Count -gt 0) {
        Write-Err "Missing dependencies: $($missing -join ', ')"
        Write-Info "Install with winget:"
        Write-Info "  winget install Python.Python.3.12 Git.Git Docker.DockerDesktop"
        exit 1
    }
    Write-Ok "All required dependencies present"
}

function Clone-Repo {
    if (Test-Path "$InstallDir\.git") {
        Write-Info "Existing installation found — updating..."
        Set-Location $InstallDir
        git fetch origin
        git reset --hard origin/main
    } else {
        Write-Info "Cloning MAGNATRIX-OS..."
        if (Test-Path $InstallDir) { Remove-Item -Recurse -Force $InstallDir }
        git clone --depth 1 "https://github.com/Magnatrix-Lab/MAGNATRIX-OS.git" $InstallDir
    }
    Write-Ok "Repository ready"
}

function Setup-DataDir {
    Write-Info "Setting up data directory: $DataDir"
    $dirs = @("models","knowledge","logs","config","repos","vault")
    foreach ($d in $dirs) {
        New-Item -ItemType Directory -Force -Path "$DataDir\$d" | Out-Null
    }
    Write-Ok "Data directory ready"
}

function Setup-Python {
    Write-Info "Setting up Python environment..."
    Set-Location $InstallDir
    if (-not (Test-Path ".venv")) {
        & (Get-Command python).Source -m venv .venv
    }
    .\.venv\Scripts\Activate.ps1
    python -m pip install --no-cache-dir --upgrade pip setuptools wheel
    python -m pip install --no-cache-dir -e ".[all]"
    Write-Ok "Python environment ready"
}

function Build-Engines {
    # C++ (requires Visual Studio or MinGW)
    Write-Info "Checking C++ build tools..."
    if (Get-Command cmake -ErrorAction SilentlyContinue) {
        Set-Location "$InstallDir\trading\cpp_hft_engine"
        New-Item -ItemType Directory -Force -Path "build" | Out-Null
        Set-Location build
        cmake .. -DCMAKE_BUILD_TYPE=Release 2>$null
        if ($LASTEXITCODE -eq 0) {
            cmake --build . --config Release 2>$null
            if ($LASTEXITCODE -eq 0) { Write-Ok "C++ engine built" }
            else { Write-Warn "C++ build failed — Python fallback active" }
        } else {
            Write-Warn "CMake failed — C++ Python fallback active"
        }
    } else {
        Write-Warn "CMake not found — C++ Python fallback active"
    }

    # Rust
    Write-Info "Checking Rust..."
    if (Get-Command cargo -ErrorAction SilentlyContinue) {
        Set-Location "$InstallDir\security\rust_crypto_engine"
        cargo build --release 2>$null
        if ($LASTEXITCODE -eq 0) { Write-Ok "Rust engine built" }
        else { Write-Warn "Rust build failed — Python fallback active" }
    } else {
        Write-Warn "Cargo not found — Rust Python fallback active"
    }
}

function Run-Tests {
    Write-Info "Running tests..."
    Set-Location $InstallDir
    .\.venv\Scripts\Activate.ps1
    python tests\run_all_tests.py 2>$null
    if ($LASTEXITCODE -eq 0) { Write-Ok "All tests passed" }
    else { Write-Warn "Some tests failed (non-blocking)" }
}

function Create-Launcher {
    Write-Info "Creating launcher..."
    $binDir = "$env:USERPROFILE\.local\bin"
    New-Item -ItemType Directory -Force -Path $binDir | Out-Null

    $launcher = @'
@echo off
set INSTALL_DIR=%MAGNATRIX_INSTALL_DIR%
if "%INSTALL_DIR%"=="" set INSTALL_DIR=%USERPROFILE%\MAGNATRIX-OS
set DATA_DIR=%MAGNATRIX_DATA_DIR%
if "%DATA_DIR%"=="" set DATA_DIR=%USERPROFILE%\.magnatrix

cd /d "%INSTALL_DIR%"

if "%~1"=="boot" (
    call .venv\Scripts\activate.bat
    python magnatrix.py boot %*
) else if "%~1"=="docker" (
    docker compose up -d
) else if "%~1"=="test" (
    call .venv\Scripts\activate.bat
    python tests\run_all_tests.py
) else if "%~1"=="stop" (
    docker compose down 2>nul
    taskkill /F /IM "python.exe" 2>nul
) else if "%~1"=="status" (
    call .venv\Scripts\activate.bat
    python magnatrix.py status
) else if "%~1"=="update" (
    cd /d "%INSTALL_DIR%"
    git fetch origin && git reset --hard origin/main
    call .venv\Scripts\activate.bat
    pip install --no-cache-dir -e ".[all]"
    echo MAGNATRIX-OS updated.
) else (
    echo MAGNATRIX-OS — Super AI Control Interface
    echo Usage: magnatrix ^<command^>
    echo   boot     Start MAGNATRIX-OS
    echo   docker   Start with Docker Compose
    echo   test     Run all tests
    echo   stop     Stop MAGNATRIX-OS
    echo   status   Show layer status
    echo   update   Update to latest
)
'@

    Set-Content -Path "$binDir\magnatrix.bat" -Value $launcher
    Write-Ok "Launcher installed: $binDir\magnatrix.bat"
    Write-Info "Add to PATH: [Environment]::SetEnvironmentVariable('Path', "$binDir;" + \$env:Path, 'User')"
}

function Main {
    Write-Host ""
    Write-Host "  __  __                                   _       ____   _____ ____" -ForegroundColor Cyan
    Write-Host " |  \/  | __ _ _ __ ___  _   _ _ __   __ _| |_ ___/ ___| |_   _/ ___|" -ForegroundColor Cyan
    Write-Host " | |\/| |/ _' | '_ \` _ \| | | | '_ \ / _' | __/ _ \___ \   | | \___ \ " -ForegroundColor Cyan
    Write-Host " | |  | | (_| | | | | | | |_| | | | | (_| | ||  __/___) |  | |  ___) |" -ForegroundColor Cyan
    Write-Host " |_|  |_|\__,_|_| |_| |_|\__,_|_| |_|\__, |\__\___|____/   |_| |____/" -ForegroundColor Cyan
    Write-Host "                                      |___/" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "MAGNATRIX-OS Installer — Windows" -ForegroundColor Cyan
    Write-Host "=================================" -ForegroundColor Cyan
    Write-Host ""

    Check-Deps
    Clone-Repo
    Setup-DataDir
    Setup-Python
    Build-Engines
    Run-Tests
    Create-Launcher

    Write-Host ""
    Write-Host "MAGNATRIX-OS installed successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Info "Installation:  $InstallDir"
    Write-Info "Data:          $DataDir"
    Write-Info "Launcher:      $env:USERPROFILE\.local\bin\magnatrix.bat"
    Write-Host ""
    Write-Info "Quick start:"
    Write-Info "  magnatrix boot     Start MAGNATRIX-OS"
    Write-Info "  magnatrix docker   Start with Docker"
    Write-Info "  magnatrix test     Run tests"
    Write-Host ""
}

Main

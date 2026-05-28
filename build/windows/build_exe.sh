#!/usr/bin/env bash
# MAGNATRIX-OS Cross-Platform Build Script
# ════════════════════════════════════════
# Builds Windows .exe via Wine + PyInstaller from Linux.
# Also supports native Linux/macOS app bundle.
#
# Usage:  bash build_exe.sh [target]
#   target: windows | linux | macos | all

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TARGET="${1:-windows}"
BUILD_DIR="${SCRIPT_DIR}/build"
DIST_DIR="${SCRIPT_DIR}/dist"

echo "============================================"
echo "  MAGNATRIX-OS Build — target=${TARGET}"
echo "============================================"

# ── Helper: build via system python ───────────────────────────────────────
build_native() {
    local platform="$1"
    echo "[INFO] Building for ${platform}..."
    cd "${REPO_ROOT}"

    python3 -m pip install -q pyinstaller pillow pystray 2>/dev/null || true

    python3 -m PyInstaller \
        --clean \
        --distpath "${DIST_DIR}" \
        --workpath "${BUILD_DIR}" \
        -y \
        "${SCRIPT_DIR}/magnatrix.spec"

    echo "[OK] ${platform} build complete: ${DIST_DIR}/MAGNATRIX-OS/"
}

# ── Helper: build via Wine ────────────────────────────────────────────────
build_wine() {
    echo "[INFO] Building Windows .exe via Wine..."

    # Check wine
    if ! command -v wine &>/dev/null; then
        echo "[ERROR] Wine not installed. Install: sudo apt install wine64"
        exit 1
    fi

    # Setup wineprefix
    export WINEPREFIX="${BUILD_DIR}/wineprefix"
    export WINEDEBUG=-all
    mkdir -p "${WINEPREFIX}"

    # Download Python for Windows if not present
    WIN_PYTHON_DIR="${BUILD_DIR}/python-win"
    if [ ! -d "${WIN_PYTHON_DIR}" ]; then
        echo "[INFO] Downloading Windows Python..."
        mkdir -p "${WIN_PYTHON_DIR}"
        PY_URL="https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip"
        curl -L -o "${BUILD_DIR}/python.zip" "${PY_URL}" || {
            echo "[WARN] Could not download Python — using system Python instead"
            build_native linux
            return
        }
        unzip -q "${BUILD_DIR}/python.zip" -d "${WIN_PYTHON_DIR}"
        rm -f "${BUILD_DIR}/python.zip"
    fi

    # Install PyInstaller in Wine
    echo "[INFO] Installing PyInstaller via Wine pip..."
    wine "${WIN_PYTHON_DIR}/python.exe" -m pip install pyinstaller pillow pystray 2>/dev/null || true

    # Run PyInstaller via Wine
    echo "[INFO] Running PyInstaller via Wine..."
    wine "${WIN_PYTHON_DIR}/python.exe" -m PyInstaller \
        --clean \
        --distpath "${DIST_DIR}" \
        --workpath "${BUILD_DIR}" \
        -y \
        "${SCRIPT_DIR}/magnatrix.spec"

    echo "[OK] Windows build complete (Wine): ${DIST_DIR}/MAGNATRIX-OS/"
}

# ── Main ───────────────────────────────────────────────────────────────────
case "${TARGET}" in
    windows)
        if command -v wine &>/dev/null; then
            build_wine
        else
            echo "[WARN] Wine not available — falling back to native Linux build"
            build_native linux
        fi
        ;;
    linux)
        build_native linux
        ;;
    macos)
        build_native macos
        ;;
    all)
        build_native linux
        if command -v wine &>/dev/null; then
            build_wine
        fi
        ;;
    *)
        echo "Usage: $0 [windows|linux|macos|all]"
        exit 1
        ;;
esac

# ── NSIS installer (if on Linux with makensis) ─────────────────────────────
if command -v makensis &>/dev/null; then
    echo "[INFO] Building NSIS installer..."
    makensis "${SCRIPT_DIR}/installer.nsi"
fi

echo "============================================"
echo "  Build finished!"
echo "  Output: ${DIST_DIR}/MAGNATRIX-OS/"
echo "============================================"

#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════════
# MAGNATRIX-OS Debian Package Builder
# ═══════════════════════════════════════════════════════════════════════════════

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VERSION="${1:-0.9.5-alpha}"
DEB_DIR="$REPO_ROOT/packages/deb"
BUILD_DIR="$DEB_DIR/magnatrix-os-$VERSION"

log() { echo "[DEB] $*"; }

# ── Clean & Create Structure ──────────────────────────────────────────────────
log "Building .deb package v$VERSION..."
rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR/DEBIAN"
mkdir -p "$BUILD_DIR/opt/magnatrix"
mkdir -p "$BUILD_DIR/usr/bin"
mkdir -p "$BUILD_DIR/usr/share/applications"
mkdir -p "$BUILD_DIR/usr/share/icons/hicolor/256x256/apps"

# ── Copy Files ────────────────────────────────────────────────────────────────
log "Copying source files..."
cp -r "$REPO_ROOT/ai" "$BUILD_DIR/opt/magnatrix/"
cp -r "$REPO_ROOT/browser_ext" "$BUILD_DIR/opt/magnatrix/"
cp -r "$REPO_ROOT/collective_brain" "$BUILD_DIR/opt/magnatrix/"
cp -r "$REPO_ROOT/config" "$BUILD_DIR/opt/magnatrix/"
cp -r "$REPO_ROOT/governance" "$BUILD_DIR/opt/magnatrix/"
cp -r "$REPO_ROOT/identity" "$BUILD_DIR/opt/magnatrix/"
cp -r "$REPO_ROOT/kernel" "$BUILD_DIR/opt/magnatrix/"
cp -r "$REPO_ROOT/knowledge" "$BUILD_DIR/opt/magnatrix/"
cp -r "$REPO_ROOT/p2p_mesh" "$BUILD_DIR/opt/magnatrix/"
cp -r "$REPO_ROOT/runtime" "$BUILD_DIR/opt/magnatrix/"
cp -r "$REPO_ROOT/security" "$BUILD_DIR/opt/magnatrix/"
cp -r "$REPO_ROOT/tests" "$BUILD_DIR/opt/magnatrix/"
cp -r "$REPO_ROOT/trading" "$BUILD_DIR/opt/magnatrix/"
cp -r "$REPO_ROOT/website" "$BUILD_DIR/opt/magnatrix/"
cp "$REPO_ROOT/magnatrix.py" "$BUILD_DIR/opt/magnatrix/"
cp "$REPO_ROOT/magnatrix.toml" "$BUILD_DIR/opt/magnatrix/"
cp "$REPO_ROOT/pyproject.toml" "$BUILD_DIR/opt/magnatrix/"
cp "$REPO_ROOT/README.md" "$BUILD_DIR/opt/magnatrix/"
cp "$REPO_ROOT/Makefile" "$BUILD_DIR/opt/magnatrix/"
cp "$REPO_ROOT/LICENSE" "$BUILD_DIR/opt/magnatrix/" 2>/dev/null || true

# ── Symlink ───────────────────────────────────────────────────────────────────
ln -sf /opt/magnatrix/magnatrix.py "$BUILD_DIR/usr/bin/magnatrix"

# ── Desktop Entry ───────────────────────────────────────────────────────────
cat > "$BUILD_DIR/usr/share/applications/magnatrix-os.desktop" << 'EOF'
[Desktop Entry]
Name=MAGNATRIX-OS
Comment=Private Uncensored Agentic AI OS
Exec=/usr/bin/magnatrix boot
Icon=magnatrix-os
Terminal=true
Type=Application
Categories=Development;AI;Science;
StartupNotify=true
EOF

# ── Control File ─────────────────────────────────────────────────────────────
cat > "$BUILD_DIR/DEBIAN/control" << EOF
Package: magnatrix-os
Version: $VERSION
Section: utils
Priority: optional
Architecture: all
Depends: python3 (>= 3.10), python3-pip, python3-venv, git, docker.io | docker-ce, docker-compose | docker-compose-plugin
Recommends: cmake, cargo, build-essential
Maintainer: Magnatrix Lab <contact@magnatrix.io>
Description: MAGNATRIX-OS — Private Uncensored Agentic AI OS
 15-layer agentic operating system with HFT trading,
 P2P mesh, local LLM, governance, and self-improvement.
EOF

# ── Preinst ──────────────────────────────────────────────────────────────────
cat > "$BUILD_DIR/DEBIAN/preinst" << 'EOF'
#!/bin/bash
set -e
if [ "$1" = "install" ] || [ "$1" = "upgrade" ]; then
    echo "[MAGNATRIX] Preparing installation..."
    mkdir -p /var/lib/magnatrix
    chmod 755 /var/lib/magnatrix
fi
EOF
chmod 755 "$BUILD_DIR/DEBIAN/preinst"

# ── Postinst ────────────────────────────────────────────────────────────────
cat > "$BUILD_DIR/DEBIAN/postinst" << 'EOF'
#!/bin/bash
set -e
cd /opt/magnatrix
python3 -m venv .venv 2>/dev/null || true
.venv/bin/pip install --upgrade pip 2>/dev/null || true
.venv/bin/pip install -e "." 2>/dev/null || true
echo "[MAGNATRIX] Installation complete. Run: magnatrix help"
EOF
chmod 755 "$BUILD_DIR/DEBIAN/postinst"

# ── Build ────────────────────────────────────────────────────────────────────
log "Building package..."
cd "$DEB_DIR"
dpkg-deb --build "magnatrix-os-$VERSION"

DEB_FILE="$DEB_DIR/magnatrix-os-${VERSION}_all.deb"
if [ -f "$DEB_FILE" ]; then
    log "Package built: $DEB_FILE"
    ls -lh "$DEB_FILE"
else
    log "Build failed — checking..."
    ls -la "$DEB_DIR/"
fi

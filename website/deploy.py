#!/usr/bin/env python3
"""
deploy_website.py — MAGNATRIX Website Deployer untuk Hostinger

Mendukung 3 mode deployment:
  1. VPS (Docker)     → Gunakan hostinger/deploy-on-vps GitHub Action
  2. Shared Hosting   → Static files via FTP/SSH upload
  3. Local Preview    → python3 -m http.server

Usage:
  python deploy_website.py --mode local --port 8080
  python deploy_website.py --mode build
  python deploy_website.py --mode vps --api-key HOSTINGER_API_KEY --vm-id VM_ID
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Dict, Optional


WEBSITE_DIR = Path(__file__).parent
REPO_ROOT = WEBSITE_DIR.parent
BUILD_DIR = WEBSITE_DIR / "dist"


def build_static() -> Path:
    """Build static website ke dist/ directory."""
    print("[BUILD] Building static website...")
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    BUILD_DIR.mkdir(parents=True, exist_ok=True)

    # Copy semua file dari website/
    for item in WEBSITE_DIR.iterdir():
        if item.name in ("dist", "deploy.py", "__pycache__"):
            continue
        dest = BUILD_DIR / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)

    # Pastikan index.html ada di root
    index = BUILD_DIR / "index.html"
    if not index.exists():
        # Fallback: gunakan yang ada
        pass

    # Buat .htaccess untuk shared hosting (rewrite ke index.html)
    htaccess = BUILD_DIR / ".htaccess"
    htaccess.write_text("""RewriteEngine On
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule ^(.*)$ index.html [L,QSA]
""")

    print(f"[BUILD] Static site ready at: {BUILD_DIR}")
    print(f"[BUILD] Total files: {sum(1 for _ in BUILD_DIR.rglob('*') if _.is_file())}")
    return BUILD_DIR


def build_zip() -> Path:
    """Build ZIP archive untuk upload via File Manager."""
    build_static()
    zip_path = WEBSITE_DIR / "magnatrix-website.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in BUILD_DIR.rglob("*"):
            if file.is_file():
                arcname = file.relative_to(BUILD_DIR)
                zf.write(file, arcname)
    size = zip_path.stat().st_size / 1024
    print(f"[ZIP] Archive created: {zip_path} ({size:.1f} KB)")
    print("[ZIP] Upload ke Hostinger File Manager → public_html/ lalu extract")
    return zip_path


def preview_local(port: int = 8080) -> None:
    """Jalankan local preview server."""
    build_static()
    os.chdir(BUILD_DIR)
    print(f"[PREVIEW] Starting server at http://localhost:{port}")
    print("[PREVIEW] Press Ctrl+C to stop")
    subprocess.run([sys.executable, "-m", "http.server", str(port)], cwd=str(BUILD_DIR))


def generate_github_actions_vps(api_key: str, vm_id: str) -> str:
    """Generate GitHub Actions workflow untuk deploy ke Hostinger VPS."""
    workflow = f"""name: Deploy Website to Hostinger VPS

on:
  push:
    branches: [ main ]
    paths:
      - 'website/**'
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Build Static Site
        run: |
          cd website
          python3 deploy.py --mode build

      - name: Deploy to Hostinger VPS
        uses: hostinger/deploy-on-vps@v2
        with:
          api-key: ${{{{ secrets.HOSTINGER_API_KEY }}}}
          virtual-machine: ${{{{ vars.HOSTINGER_VM_ID }}}}
          project-name: magnatrix-website
          docker-compose-path: website/docker-compose.yml
          environment-variables: |
            NODE_ENV=production
            PORT=80
"""
    return workflow


def generate_docker_compose() -> str:
    """Generate docker-compose.yml untuk website deployment."""
    return """version: "3.8"

services:
  magnatrix-website:
    image: nginx:alpine
    container_name: magnatrix-website
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./dist:/usr/share/nginx/html:ro
      - ./nginx.conf:/etc/nginx/conf.d/default.conf:ro
    restart: unless-stopped
    networks:
      - magnatrix-net

networks:
  magnatrix-net:
    external: true
"""


def generate_nginx_conf() -> str:
    """Generate nginx.conf untuk static site."""
    return """server {
    listen 80;
    server_name magnatrix.io www.magnatrix.io;
    root /usr/share/nginx/html;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml;

    # Cache static assets
    location ~* \\.(css|js|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # SPA fallback
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
}
"""


def setup_vps_deploy() -> None:
    """Setup semua file untuk VPS deployment."""
    build_static()

    # Write docker-compose.yml
    dc_file = WEBSITE_DIR / "docker-compose.yml"
    dc_file.write_text(generate_docker_compose())
    print(f"[VPS] Created: {dc_file}")

    # Write nginx.conf
    nginx_file = WEBSITE_DIR / "nginx.conf"
    nginx_file.write_text(generate_nginx_conf())
    print(f"[VPS] Created: {nginx_file}")

    # Write GitHub Actions workflow
    workflow_dir = REPO_ROOT / ".github" / "workflows"
    workflow_dir.mkdir(parents=True, exist_ok=True)
    workflow_file = workflow_dir / "deploy-website.yml"
    workflow_file.write_text(generate_github_actions_vps("${{ secrets.HOSTINGER_API_KEY }}", "${{ vars.HOSTINGER_VM_ID }}"))
    print(f"[VPS] Created: {workflow_file}")

    print("""
[VPS] Setup selesai. Langkah berikutnya:
  1. Pastikan Hostinger VPS punya Docker terinstall
  2. Set secrets di GitHub:
     - HOSTINGER_API_KEY = API key dari hPanel
     - HOSTINGER_VM_ID   = VM ID dari dashboard VPS
  3. Push ke main branch → auto-deploy via GitHub Actions
  4. Atau deploy manual: cd website && docker-compose up -d
""")


def main() -> None:
    parser = argparse.ArgumentParser(description="MAGNATRIX Website Deployer")
    parser.add_argument("--mode", choices=["build", "zip", "preview", "vps-setup", "shared"], default="build",
                        help="Deployment mode")
    parser.add_argument("--port", type=int, default=8080, help="Port untuk preview mode")
    parser.add_argument("--api-key", help="Hostinger API key (untuk VPS mode)")
    parser.add_argument("--vm-id", help="Hostinger VM ID (untuk VPS mode)")
    args = parser.parse_args()

    if args.mode == "build":
        build_static()
        print("[DONE] Static site ready in website/dist/")

    elif args.mode == "zip":
        build_zip()
        print("[DONE] Upload magnatrix-website.zip ke Hostinger File Manager")

    elif args.mode == "preview":
        preview_local(args.port)

    elif args.mode == "vps-setup":
        setup_vps_deploy()
        print("[DONE] VPS deployment files ready")

    elif args.mode == "shared":
        zip_path = build_zip()
        print(f"""
[SHARED HOSTING] Deploy instructions:
  1. Login ke hPanel Hostinger
  2. Buka File Manager → public_html/
  3. Delete semua file WordPress lama (backup dulu!)
  4. Upload {zip_path.name}
  5. Right-click → Extract ke public_html/
  6. Clear browser cache dan cek magnatrix.io
""")


if __name__ == "__main__":
    main()

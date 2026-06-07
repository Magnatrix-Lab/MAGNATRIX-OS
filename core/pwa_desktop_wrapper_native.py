#!/usr/bin/env python3
"""
PWA + Desktop Wrapper Module for MAGNATRIX-OS
Generates PWA manifest, service worker, Electron wrapper.
Pure stdlib — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class PWAEngine:
    """Generate PWA assets: manifest, service worker, icons."""

    def __init__(self, app_name: str = "MAGNATRIX-OS", theme_color: str = "#6366f1", 
                 background_color: str = "#0a0a0f", start_url: str = "/") -> None:
        self.app_name = app_name
        self.theme_color = theme_color
        self.background_color = background_color
        self.start_url = start_url
        self.version = "1.0.0"

    def generate_manifest(self) -> str:
        """Generate web app manifest JSON."""
        manifest = {
            "name": self.app_name,
            "short_name": "MAGNATRIX",
            "description": "Private, uncensored AI operating system",
            "start_url": self.start_url,
            "display": "standalone",
            "background_color": self.background_color,
            "theme_color": self.theme_color,
            "orientation": "any",
            "scope": "/",
            "icons": [
                {"src": "/icon-72.png", "sizes": "72x72", "type": "image/png"},
                {"src": "/icon-96.png", "sizes": "96x96", "type": "image/png"},
                {"src": "/icon-128.png", "sizes": "128x128", "type": "image/png"},
                {"src": "/icon-144.png", "sizes": "144x144", "type": "image/png"},
                {"src": "/icon-152.png", "sizes": "152x152", "type": "image/png"},
                {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png"},
                {"src": "/icon-384.png", "sizes": "384x384", "type": "image/png"},
                {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
            ],
            "categories": ["productivity", "developer", "utilities"],
            "screenshots": [
                {
                    "src": "/screenshot-wide.png",
                    "sizes": "1280x720",
                    "type": "image/png",
                    "form_factor": "wide",
                    "label": "Dashboard Overview",
                },
                {
                    "src": "/screenshot-narrow.png",
                    "sizes": "390x844",
                    "type": "image/png",
                    "form_factor": "narrow",
                    "label": "Mobile Dashboard",
                },
            ],
            "shortcuts": [
                {
                    "name": "Chat",
                    "short_name": "Chat",
                    "description": "Open AI chat",
                    "url": "/?panel=chat",
                    "icons": [{"src": "/icon-chat.png", "sizes": "96x96"}],
                },
                {
                    "name": "Modules",
                    "short_name": "Modules",
                    "description": "View system modules",
                    "url": "/?panel=modules",
                    "icons": [{"src": "/icon-modules.png", "sizes": "96x96"}],
                },
            ],
            "related_applications": [],
            "prefer_related_applications": False,
        }
        return json.dumps(manifest, indent=2, ensure_ascii=False)

    def generate_service_worker(self, cache_name: str = "magnatrix-v1") -> str:
        """Generate a service worker with offline caching and background sync."""
        return """/* MAGNATRIX-OS Service Worker */
const CACHE_NAME = "magnatrix-v1";
const STATIC_ASSETS = [
  "/",
  "/dashboard.html",
  "/manifest.json",
  "/icon-192.png",
  "/icon-512.png",
];
const API_CACHE = "magnatrix-api-v1";

// Install: cache static assets
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

// Activate: clean old caches
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((k) => k !== CACHE_NAME && k !== API_CACHE).map((k) => caches.delete(k))
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch: serve from cache or network
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== "GET") return;

  // API calls: stale-while-revalidate
  if (url.pathname.startsWith("/api/")) {
    event.respondWith(
      caches.open(API_CACHE).then((cache) => {
        return cache.match(request).then((cached) => {
          const fetchPromise = fetch(request).then((networkResponse) => {
            if (networkResponse.ok) cache.put(request, networkResponse.clone());
            return networkResponse;
          }).catch(() => cached);
          return cached || fetchPromise;
        });
      })
    );
    return;
  }

  // Static assets: cache-first
  event.respondWith(
    caches.match(request).then((cached) => {
      return cached || fetch(request).then((response) => {
        if (response.ok) {
          const clone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
        }
        return response;
      });
    }).catch(() => {
      // Fallback for HTML
      if (request.mode === "navigate") {
        return caches.match("/dashboard.html");
      }
    })
  );
});

// Background sync: queue failed requests
self.addEventListener("sync", (event) => {
  if (event.tag === "sync-chat") {
    event.waitUntil(syncChatMessages());
  }
});

async function syncChatMessages() {
  const queue = await getSyncQueue();
  for (const item of queue) {
    try {
      await fetch(item.url, { method: item.method, headers: item.headers, body: item.body });
      await removeFromQueue(item.id);
    } catch (e) {
      console.error("Sync failed:", e);
    }
  }
}

async function getSyncQueue() {
  return new Promise((resolve) => {
    const request = indexedDB.open("magnatrix-db", 1);
    request.onupgradeneeded = (e) => {
      const db = e.target.result;
      if (!db.objectStoreNames.contains("syncQueue")) {
        db.createObjectStore("syncQueue", { keyPath: "id", autoIncrement: true });
      }
    };
    request.onsuccess = (e) => {
      const db = e.target.result;
      const tx = db.transaction("syncQueue", "readonly");
      const store = tx.objectStore("syncQueue");
      const getAll = store.getAll();
      getAll.onsuccess = () => resolve(getAll.result || []);
    };
  });
}

async function removeFromQueue(id) {
  return new Promise((resolve) => {
    const request = indexedDB.open("magnatrix-db", 1);
    request.onsuccess = (e) => {
      const db = e.target.result;
      const tx = db.transaction("syncQueue", "readwrite");
      const store = tx.objectStore("syncQueue");
      store.delete(id);
      tx.oncomplete = resolve;
    };
  });
}

// Push notifications
self.addEventListener("push", (event) => {
  const data = event.data ? event.data.json() : {};
  const title = data.title || "MAGNATRIX-OS";
  const options = {
    body: data.body || "New notification",
    icon: "/icon-192.png",
    badge: "/icon-72.png",
    tag: data.tag || "default",
    requireInteraction: false,
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(
    clients.matchAll({ type: "window" }).then((clientList) => {
      if (clientList.length > 0) {
        clientList[0].focus();
      } else {
        clients.openWindow("/");
      }
    })
  );
});
"""

    def generate_offline_page(self) -> str:
        """Generate offline fallback page."""
        return """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Offline - MAGNATRIX-OS</title>
<style>
body{background:#0a0a0f;color:#e2e8f0;font-family:system-ui;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;text-align:center}
.card{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);padding:40px;border-radius:12px;max-width:400px}
h1{font-size:24px;margin-bottom:12px}p{color:#64748b;margin-bottom:24px}
.retry-btn{background:linear-gradient(135deg,#6366f1,#a855f7);border:none;padding:10px 20px;border-radius:8px;color:white;cursor:pointer;font-size:14px}
</style></head><body>
<div class="card"><h1>Offline</h1><p>You are currently offline. Some features may not be available.</p><button class="retry-btn" onclick="location.reload()">Retry</button></div>
</body></html>"""

    def generate_html_snippet(self) -> str:
        """Generate HTML snippet to register the service worker."""
        return """<script>
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js').then(reg => {
    console.log('[PWA] Service worker registered:', reg.scope);
    // Request background sync
    if ('sync' in reg) {
      reg.sync.register('sync-chat').catch(() => {});
    }
    // Request push notification permission
    if ('Notification' in window) {
      Notification.requestPermission().then(perm => {
        console.log('[PWA] Notification permission:', perm);
      });
    }
  }).catch(err => console.error('[PWA] SW registration failed:', err));
}
let deferredPrompt;
window.addEventListener('beforeinstallprompt', (e) => {
  e.preventDefault();
  deferredPrompt = e;
  console.log('[PWA] Install prompt available');
});
</script>"""

    def save_all(self, output_dir: str) -> Dict[str, str]:
        """Generate and save all PWA assets to directory."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        files = {
            "manifest.json": self.generate_manifest(),
            "sw.js": self.generate_service_worker(),
            "offline.html": self.generate_offline_page(),
            "pwa-snippet.html": self.generate_html_snippet(),
        }
        for name, content in files.items():
            (out / name).write_text(content, encoding="utf-8")
        return {k: str(out / k) for k in files}


class DesktopWrapper:
    """Generate Electron desktop wrapper for MAGNATRIX-OS."""

    def __init__(self, app_name: str = "MAGNATRIX-OS", window_width: int = 1400, 
                 window_height: int = 900, server_port: int = 8080) -> None:
        self.app_name = app_name
        self.width = window_width
        self.height = window_height
        self.port = server_port

    def generate_package_json(self) -> str:
        """Generate Electron package.json."""
        pkg = {
            "name": "magnatrix-desktop",
            "version": "1.0.0",
            "description": "Desktop app for MAGNATRIX-OS",
            "main": "main.js",
            "scripts": {
                "start": "electron .",
                "build": "electron-builder",
                "pack": "electron-builder --dir",
            },
            "build": {
                "appId": "com.magnatrix.os",
                "productName": "MAGNATRIX-OS",
                "directories": {"output": "dist"},
                "files": ["main.js", "preload.js", "icon.ico", "icon.png"],
                "mac": {"target": ["dmg"]},
                "win": {"target": ["nsis"]},
                "linux": {"target": ["AppImage", "deb"]},
            },
            "devDependencies": {
                "electron": "^28.0.0",
                "electron-builder": "^24.0.0",
            },
        }
        return json.dumps(pkg, indent=2, ensure_ascii=False)

    def generate_main_js(self) -> str:
        """Generate Electron main process script."""
        return """const { app, BrowserWindow, ipcMain, dialog, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

let mainWindow;
let serverProcess;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400, height: 900,
    title: 'MAGNATRIX-OS',
    icon: path.join(__dirname, 'icon.png'),
    backgroundColor: '#0a0a0f',
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  mainWindow.once('ready-to-show', () => mainWindow.show());

  // Load the dashboard
  const startUrl = process.env.MAGNATRIX_URL || 'http://127.0.0.1:8080';
  mainWindow.loadURL(startUrl);

  // Open external links in browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  mainWindow.on('closed', () => { mainWindow = null; });
}

function startServer() {
  const python = process.platform === 'win32' ? 'python' : 'python3';
  const serverPath = path.join(__dirname, 'core', 'web_dashboard_server_native.py');
  serverProcess = spawn(python, [serverPath], { cwd: path.join(__dirname) });
  serverProcess.stdout.on('data', (d) => console.log('[Server]', d.toString().trim()));
  serverProcess.stderr.on('data', (d) => console.error('[Server]', d.toString().trim()));
}

app.whenReady().then(() => {
  startServer();
  // Wait for server to start
  setTimeout(createWindow, 2000);

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (serverProcess) serverProcess.kill();
  if (process.platform !== 'darwin') app.quit();
});

app.on('before-quit', () => {
  if (serverProcess) serverProcess.kill();
});

// IPC handlers
ipcMain.handle('get-app-version', () => '1.0.0');
ipcMain.handle('select-file', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openFile'],
    filters: [
      { name: 'Documents', extensions: ['txt', 'pdf', 'csv', 'json', 'md'] },
      { name: 'All Files', extensions: ['*'] },
    ],
  });
  return result.filePaths;
});
ipcMain.handle('show-notification', (_, title, body) => {
  if (mainWindow) {
    mainWindow.webContents.send('notification', { title, body });
  }
});
"""

    def generate_preload_js(self) -> str:
        """Generate Electron preload script for secure bridge."""
        return """const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  getAppVersion: () => ipcRenderer.invoke('get-app-version'),
  selectFile: () => ipcRenderer.invoke('select-file'),
  showNotification: (title, body) => ipcRenderer.invoke('show-notification', title, body),
  onNotification: (callback) => ipcRenderer.on('notification', (_, data) => callback(data)),
  platform: process.platform,
});
"""

    def generate_icon_svg(self) -> str:
        """Generate SVG icon for Electron app."""
        return """<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">
  <defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stop-color="#6366f1"/><stop offset="100%" stop-color="#a855f7"/></linearGradient></defs>
  <rect width="512" height="512" rx="128" fill="#0a0a0f"/>
  <rect x="32" y="32" width="448" height="448" rx="96" fill="url(#g)" opacity="0.9"/>
  <text x="256" y="320" text-anchor="middle" font-family="system-ui,sans-serif" font-weight="700" font-size="240" fill="white">M</text>
</svg>"""

    def save_all(self, output_dir: str) -> Dict[str, str]:
        """Generate and save all Electron wrapper files."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        files = {
            "package.json": self.generate_package_json(),
            "main.js": self.generate_main_js(),
            "preload.js": self.generate_preload_js(),
            "icon.svg": self.generate_icon_svg(),
        }
        for name, content in files.items():
            (out / name).write_text(content, encoding="utf-8")
        return {k: str(out / k) for k in files}


class PWADesktopManager:
    """Unified manager for both PWA and Desktop wrapper."""

    def __init__(self, app_name: str = "MAGNATRIX-OS", repo_root: Optional[str] = None) -> None:
        self.app_name = app_name
        self.root = Path(repo_root) if repo_root else Path.cwd()
        self.pwa = PWAEngine(app_name)
        self.desktop = DesktopWrapper(app_name)

    def generate_all(self, output_dir: Optional[str] = None) -> Dict[str, Any]:
        out = Path(output_dir) if output_dir else self.root / "desktop"
        pwa_dir = out / "pwa"
        desktop_dir = out / "electron"
        pwa_files = self.pwa.save_all(pwa_dir)
        desktop_files = self.desktop.save_all(desktop_dir)
        return {
            "output_dir": str(out),
            "pwa": pwa_files,
            "desktop": desktop_files,
        }

    def inject_pwa_into_dashboard(self, dashboard_path: str) -> bool:
        """Inject PWA registration snippet into dashboard HTML."""
        path = Path(dashboard_path)
        if not path.exists():
            return False
        html = path.read_text(encoding="utf-8")
        # Add manifest link
        if "manifest.json" not in html:
            html = html.replace("<head>", '<head>\n<link rel="manifest" href="/manifest.json">')
        # Add theme-color
        if "theme-color" not in html:
            html = html.replace("<head>", '<head>\n<meta name="theme-color" content="#6366f1">')
        # Add PWA snippet before </body>
        snippet = self.pwa.generate_html_snippet()
        if "serviceWorker.register" not in html:
            html = html.replace("</body>", snippet + "\n</body>")
        path.write_text(html, encoding="utf-8")
        return True

    def stats(self) -> Dict[str, Any]:
        return {
            "pwa_manifest_size": len(self.pwa.generate_manifest()),
            "service_worker_size": len(self.pwa.generate_service_worker()),
            "desktop_package_size": len(self.desktop.generate_package_json()),
            "desktop_main_size": len(self.desktop.generate_main_js()),
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    print("=== PWA + Desktop Wrapper Demo ===\n")
    manager = PWADesktopManager()
    result = manager.generate_all("/tmp/magnatrix-desktop")
    print(f"Generated to: {result['output_dir']}")
    print(f"\nPWA files:")
    for name, path in result["pwa"].items():
        print(f"  {name}: {path}")
    print(f"\nDesktop files:")
    for name, path in result["desktop"].items():
        print(f"  {name}: {path}")
    print(f"\nStats: {manager.stats()}")


if __name__ == "__main__":
    _demo()

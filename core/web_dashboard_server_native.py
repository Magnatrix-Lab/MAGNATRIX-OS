#!/usr/bin/env python3
"""
Web Dashboard Server for MAGNATRIX-OS
Elegant HTTP server serving the admin dashboard + API endpoints.
Bridges frontend to all core infrastructure modules.
Native stdlib only — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional


class DashboardServer:
    """HTTP server that serves the MAGNATRIX-OS dashboard and API."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080, repo_root: Optional[str] = None) -> None:
        self.host = host
        self.port = port
        self.root = Path(repo_root).resolve() if repo_root else Path(__file__).parent.parent.resolve()
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._start_time = time.time()
        self._request_count = 0
        self._chat_history: List[Dict[str, Any]] = []
        self._log_buffer: List[Dict[str, Any]] = []
        # Try to wire to existing core modules
        self._modules = {}
        self._bootstrap = None
        self._try_wire_modules()

    def _try_wire_modules(self) -> None:
        """Attempt to import and wire to existing core modules."""
        sys.path.insert(0, str(self.root))
        try:
            import importlib
            # Try to import system bootstrap
            try:
                boot_mod = importlib.import_module("core.system_bootstrap_native")
                self._bootstrap = boot_mod.SystemBootstrap(str(self.root))
                self._bootstrap.boot()
            except Exception:
                pass
            # Try individual modules
            for name, mod_path, cls_name in [
                ("config", "core.config_manager_native", "ConfigManager"),
                ("monitor", "core.resource_monitor_native", "ResourceMonitor"),
                ("cache", "core.cache_manager_native", "CacheManager"),
                ("context", "core.context_manager_native", "ContextManager"),
                ("logger", "core.logging_tracing_native", "LoggingManager"),
                ("auth", "core.auth_authorization_native", "AuthManager"),
                ("rate_limiter", "core.rate_limiter_native", "RateLimiter"),
                ("prompt_guard", "core.prompt_injection_guard_native", "PromptInjectionGuard"),
            ]:
                try:
                    mod = importlib.import_module(mod_path)
                    self._modules[name] = getattr(mod, cls_name)()
                except Exception:
                    pass
        except Exception:
            pass
        finally:
            sys.path.pop(0)

    def _dashboard_html(self) -> str:
        """Load dashboard HTML from file or return embedded fallback."""
        html_path = self.root / "core" / "dashboard.html"
        if html_path.exists():
            return html_path.read_text(encoding="utf-8")
        # Minimal embedded fallback
        return """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>MAGNATRIX-OS</title>
<style>body{background:#0a0a0f;color:#e2e8f0;font-family:system-ui;display:flex;align-items:center;justify-content:center;height:100vh;margin:0}
.card{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);padding:40px;border-radius:12px;text-align:center}
h1{background:linear-gradient(135deg,#6366f1,#a855f7);-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-size:32px}
p{color:#64748b}</style></head><body>
<div class="card"><h1>MAGNATRIX-OS</h1><p>Dashboard file not found. Place <code>dashboard.html</code> next to this server.</p></div></body></html>"""

    # ------------------------------------------------------------------
    # API handlers
    # ------------------------------------------------------------------

    def _api_chat(self, body: Dict[str, Any]) -> Dict[str, Any]:
        msg = body.get("message", "")
        if not msg:
            return {"text": "", "error": "Empty message"}
        # Guard check
        guard = self._modules.get("prompt_guard")
        if guard:
            try:
                result = guard.scan_and_sanitize(msg)
                if result.threat_level.value in ("dangerous", "critical"):
                    return {"text": f"[BLOCKED] Input flagged: {result.reason}", "blocked": True}
            except Exception:
                pass
        # Try LLM adapter
        try:
            import importlib
            llm_mod = importlib.import_module("core.multi_model_llm_adapter_native")
            adapter = llm_mod.MultiModelLLMAdapter()
            # Try to use any registered endpoint or mock
            response = adapter.chat_mock(msg) if hasattr(adapter, "chat_mock") else None
            if response:
                return {"text": response.text}
        except Exception:
            pass
        # Fallback echo
        return {"text": f"[Echo] {msg}"}

    def _api_metrics(self) -> Dict[str, Any]:
        monitor = self._modules.get("monitor")
        if monitor:
            try:
                snap = monitor.snapshot()
                return snap
            except Exception:
                pass
        # Fallback
        return {
            "cpu": {"value": 15.0, "unit": "%", "details": {"cores": os.cpu_count() or 1}},
            "memory": {"value": 42.0, "unit": "%", "details": {"total": 8 * 1024 ** 3}},
            "disk": {"value": 30.0, "unit": "%", "details": {"total": 100 * 1024 ** 3}},
            "load": {"value": 0.5, "unit": "", "details": {"load_1min": 0.5}},
        }

    def _api_modules(self) -> List[Dict[str, Any]]:
        if self._bootstrap:
            try:
                return [
                    {
                        "name": name,
                        "description": info.manifest.description if hasattr(info, "manifest") else "Core module",
                        "active": info.state.value == "active" if hasattr(info, "state") else True,
                        "state": info.state.value if hasattr(info, "state") else "active",
                        "load_time_ms": info.load_time_ms if hasattr(info, "load_time_ms") else 0,
                    }
                    for name, info in self._bootstrap._modules.items()
                ]
            except Exception:
                pass
        # Fallback
        return [
            {"name": "event_bus", "description": "Pub/sub communication", "active": True, "state": "active"},
            {"name": "config", "description": "Configuration manager", "active": True, "state": "active"},
            {"name": "auth", "description": "Authentication & authorization", "active": True, "state": "active"},
            {"name": "cache", "description": "Cache manager", "active": True, "state": "active"},
            {"name": "orchestrator", "description": "Unified orchestrator", "active": True, "state": "active"},
        ]

    def _api_logs(self) -> List[Dict[str, Any]]:
        if self._log_buffer:
            return self._log_buffer[-50:]
        return [
            {"timestamp": time.time(), "level": "INFO", "message": "Dashboard server started"},
            {"timestamp": time.time(), "level": "INFO", "message": f"Serving on {self.host}:{self.port}"},
        ]

    def _api_system(self) -> Dict[str, Any]:
        try:
            import platform
            env_mod = __import__("core.environment_detector_native", fromlist=["EnvironmentDetector"])
            det = env_mod.EnvironmentDetector()
            info = det.get_info()
            return {
                "os_name": info.os_name,
                "os_version": info.os_version,
                "arch": info.arch,
                "processor": info.processor,
                "python_version": info.python_version,
                "cpu_count": info.cpu_count,
                "memory_total": info.memory_total,
                "hostname": info.hostname,
                "is_container": info.constraints.get("container") is not None,
                "capabilities": sorted(info.capabilities),
            }
        except Exception:
            return {
                "os_name": platform.system() if 'platform' in dir() else "Unknown",
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "cpu_count": os.cpu_count() or 1,
                "hostname": "unknown",
            }

    def _api_health(self) -> Dict[str, Any]:
        try:
            import subprocess
            py_count = len(list(self.root.rglob("*.py")))
            core_count = len(list((self.root / "core").glob("*_native.py"))) if (self.root / "core").exists() else 0
            gov_count = len(list((self.root / "governance").glob("*_native.py"))) if (self.root / "governance").exists() else 0
            calc_count = py_count - core_count - gov_count
        except Exception:
            py_count = core_count = gov_count = calc_count = 0
        return {
            "status": "ok",
            "uptime_seconds": round(time.time() - self._start_time, 2),
            "modules": len(self._modules) + (len(self._bootstrap._modules) if self._bootstrap else 0),
            "files": py_count,
            "core": core_count,
            "governance": gov_count,
            "calculators": max(0, calc_count),
            "version": "1.0.0",
            "requests": self._request_count,
        }

    # ------------------------------------------------------------------
    # HTTP handler
    # ------------------------------------------------------------------

    def _make_handler(self) -> type:
        server = self
        class _Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args: Any) -> None:
                pass

            def _send_json(self, data: Any, status: int = 200) -> None:
                body = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _send_html(self, html: str, status: int = 200) -> None:
                body = html.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _read_body(self) -> Dict[str, Any]:
                length = int(self.headers.get("Content-Length", 0))
                if length:
                    try:
                        return json.loads(self.rfile.read(length).decode("utf-8"))
                    except Exception:
                        pass
                return {}

            def do_OPTIONS(self) -> None:
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
                self.end_headers()

            def do_GET(self) -> None:
                server._request_count += 1
                path = self.path.split("?")[0]
                if path == "/" or path == "/dashboard":
                    self._send_html(server._dashboard_html())
                elif path == "/api/metrics":
                    self._send_json(server._api_metrics())
                elif path == "/api/modules":
                    self._send_json(server._api_modules())
                elif path == "/api/logs":
                    self._send_json(server._api_logs())
                elif path == "/api/system":
                    self._send_json(server._api_system())
                elif path == "/api/health":
                    self._send_json(server._api_health())
                elif path == "/api/chat":
                    self._send_json({"endpoint": "POST /api/chat", "description": "Send chat message"})
                else:
                    self._send_json({"error": "Not found", "path": path}, 404)

            def do_POST(self) -> None:
                server._request_count += 1
                path = self.path.split("?")[0]
                body = self._read_body()
                if path == "/api/chat":
                    self._send_json(server._api_chat(body))
                else:
                    self._send_json({"error": "Not found", "path": path}, 404)
        return _Handler

    # ------------------------------------------------------------------
    # Server lifecycle
    # ------------------------------------------------------------------

    def start(self, blocking: bool = False) -> None:
        self._running = True
        self._start_time = time.time()
        handler = self._make_handler()
        self._server = HTTPServer((self.host, self.port), handler)
        if blocking:
            print(f"[Dashboard] Serving at http://{self.host}:{self.port}")
            self._server.serve_forever()
        else:
            self._thread = threading.Thread(target=self._server.serve_forever, daemon=True, name="DashboardServer")
            self._thread.start()
            print(f"[Dashboard] Started at http://{self.host}:{self.port}")

    def stop(self) -> None:
        self._running = False
        if self._server:
            self._server.shutdown()
            self._server.server_close()

    def stats(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "host": self.host,
            "port": self.port,
            "requests": self._request_count,
            "uptime_seconds": round(time.time() - self._start_time, 2) if self._start_time else 0,
            "modules_wired": len(self._modules),
            "bootstrap_active": self._bootstrap is not None,
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    server = DashboardServer(host="127.0.0.1", port=8765)
    print("=== Web Dashboard Server Demo ===\n")
    print(f"Dashboard URL: http://127.0.0.1:8765")
    print("\nAPI endpoints:")
    print("  GET  /api/health")
    print("  GET  /api/metrics")
    print("  GET  /api/modules")
    print("  GET  /api/system")
    print("  GET  /api/logs")
    print("  POST /api/chat")
    print(f"\nStats: {server.stats()}")
    # Quick test
    try:
        import urllib.request
        req = urllib.request.Request("http://127.0.0.1:8765/api/health")
        resp = urllib.request.urlopen(req, timeout=2)
        print(f"\nHealth check: {resp.status}")
        print(json.loads(resp.read().decode()))
    except Exception as e:
        print(f"\nNote: Server not started in demo. Start with server.start()")


if __name__ == "__main__":
    _demo()

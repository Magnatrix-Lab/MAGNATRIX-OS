#!/usr/bin/env python3
"""
Dashboard Production — MAGNATRIX-OS Real-Time Interactive Web Dashboard
=======================================================================
HTTP server with SSE streaming, inline HTML/CSS/JS, metrics collection.
Pure stdlib. No external assets.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations

import json
import os
import threading
import time
import urllib.parse
from dataclasses import dataclass, field
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, List, Optional, Tuple, Union


class MetricsCollector:
    """
    Collect system metrics using only stdlib.
    
    Reads /proc/stat, /proc/meminfo, os.statvfs, os.getloadavg.
    """

    def __init__(self, history_limit: int = 300):
        self.history_limit = history_limit
        self._cpu_history: List[Tuple[float, float]] = []  # (timestamp, percent)
        self._mem_history: List[Tuple[float, float]] = []  # (timestamp, percent)
        self._lock = threading.Lock()
        self._last_cpu_times: Optional[Tuple[int, int]] = None

    def collect(self) -> Dict[str, Any]:
        """Collect all system metrics."""
        return {
            "cpu": self.cpu_percent(),
            "memory": self.memory_usage(),
            "disk": self.disk_usage(),
            "load": self.load_average(),
            "timestamp": time.time(),
        }

    def cpu_percent(self) -> float:
        """Get CPU usage percentage."""
        try:
            with open("/proc/stat", "r") as f:
                line = f.readline()
            fields = line.split()[1:]
            user, nice, system, idle = int(fields[0]), int(fields[1]), int(fields[2]), int(fields[3])
            total = user + nice + system + idle
            idle_time = idle
            
            if self._last_cpu_times:
                last_total, last_idle = self._last_cpu_times
                total_diff = total - last_total
                idle_diff = idle_time - last_idle
                if total_diff > 0:
                    cpu_percent = (1 - idle_diff / total_diff) * 100
                else:
                    cpu_percent = 0.0
            else:
                cpu_percent = 0.0
            
            self._last_cpu_times = (total, idle_time)
            
            with self._lock:
                self._cpu_history.append((time.time(), cpu_percent))
                if len(self._cpu_history) > self.history_limit:
                    self._cpu_history.pop(0)
            
            return round(cpu_percent, 2)
        except Exception:
            return 0.0

    def memory_usage(self) -> Dict[str, Any]:
        """Get memory usage."""
        try:
            with open("/proc/meminfo", "r") as f:
                lines = f.readlines()
            mem_total = 0
            mem_available = 0
            for line in lines:
                if line.startswith("MemTotal:"):
                    mem_total = int(line.split()[1]) * 1024
                elif line.startswith("MemAvailable:"):
                    mem_available = int(line.split()[1]) * 1024
                elif line.startswith("MemFree:") and mem_available == 0:
                    mem_available = int(line.split()[1]) * 1024
            
            used = mem_total - mem_available if mem_total > 0 else 0
            percent = (used / mem_total * 100) if mem_total > 0 else 0
            
            with self._lock:
                self._mem_history.append((time.time(), percent))
                if len(self._mem_history) > self.history_limit:
                    self._mem_history.pop(0)
            
            return {
                "total": mem_total,
                "used": used,
                "available": mem_available,
                "percent": round(percent, 2),
            }
        except Exception:
            return {"total": 0, "used": 0, "available": 0, "percent": 0.0}

    def disk_usage(self) -> Dict[str, Any]:
        """Get disk usage for repo root."""
        try:
            stat = os.statvfs(".")
            total = stat.f_blocks * stat.f_frsize
            free = stat.f_bavail * stat.f_frsize
            used = total - free
            percent = (used / total * 100) if total > 0 else 0
            return {
                "total": total,
                "used": used,
                "free": free,
                "percent": round(percent, 2),
            }
        except Exception:
            return {"total": 0, "used": 0, "free": 0, "percent": 0.0}

    def load_average(self) -> List[float]:
        """Get system load average."""
        try:
            return list(os.getloadavg())
        except Exception:
            return [0.0, 0.0, 0.0]

    def get_history(self) -> Dict[str, List[Tuple[float, float]]]:
        with self._lock:
            return {
                "cpu": list(self._cpu_history),
                "memory": list(self._mem_history),
            }


class DashboardHTML:
    """
    Generate self-contained dashboard HTML with inline CSS and JS.
    """

    def generate(self, system_status: Dict[str, Any]) -> str:
        """Generate the full dashboard HTML."""
        return f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MAGNATRIX-OS Dashboard</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: 'Segoe UI', system-ui, monospace; background: #0a0a1a; color: #e0e0e0; }}
.header {{ background: linear-gradient(135deg, #1a1a3e, #2a2a5e); padding: 20px; border-bottom: 2px solid #4CAF50; }}
.header h1 {{ font-size: 24px; color: #4CAF50; }}
.header .subtitle {{ color: #888; font-size: 14px; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 15px; padding: 20px; }}
.card {{ background: #1a1a3e; border-radius: 8px; padding: 15px; border: 1px solid #2a2a5e; }}
.card h3 {{ color: #4CAF50; margin-bottom: 10px; font-size: 14px; text-transform: uppercase; }}
.status-badge {{ display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: bold; }}
.status-active {{ background: #1b5e20; color: #4CAF50; }}
.status-error {{ background: #5e1b1b; color: #f44336; }}
.status-loading {{ background: #5e5e1b; color: #ffeb3b; }}
.metric-value {{ font-size: 32px; font-weight: bold; color: #4CAF50; }}
.metric-label {{ font-size: 12px; color: #888; }}
.log-panel {{ background: #0a0a1a; border: 1px solid #2a2a5e; border-radius: 4px; padding: 10px; height: 200px; overflow-y: auto; font-family: monospace; font-size: 12px; }}
.log-entry {{ margin: 2px 0; padding: 2px 4px; border-left: 3px solid transparent; }}
.log-info {{ border-left-color: #2196F3; }}
.log-warn {{ border-left-color: #ff9800; }}
.log-error {{ border-left-color: #f44336; }}
.control-btn {{ background: #2a2a5e; color: #e0e0e0; border: 1px solid #4CAF50; padding: 8px 16px; border-radius: 4px; cursor: pointer; margin: 5px; }}
.control-btn:hover {{ background: #4CAF50; color: #0a0a1a; }}
.chart-container {{ height: 150px; background: #0a0a1a; border-radius: 4px; padding: 10px; }}
.module-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px; }}
.module-card {{ padding: 10px; border-radius: 6px; font-size: 12px; cursor: pointer; transition: transform 0.2s; }}
.module-card:hover {{ transform: translateY(-2px); }}
.module-active {{ background: #1b5e20; border: 1px solid #4CAF50; }}
.module-error {{ background: #5e1b1b; border: 1px solid #f44336; }}
.module-loading {{ background: #5e5e1b; border: 1px solid #ffeb3b; }}
.module-name {{ font-weight: bold; }}
.module-time {{ color: #888; font-size: 10px; }}
.refresh-indicator {{ position: fixed; top: 10px; right: 10px; width: 10px; height: 10px; border-radius: 50%; background: #4CAF50; animation: pulse 2s infinite; }}
@keyframes pulse {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0.3; }} 100% {{ opacity: 1; }} }}
#connection-status {{ color: #888; font-size: 12px; }}
</style>
</head><body>
<div class="header">
  <h1>MAGNATRIX-OS</h1>
  <div class="subtitle">Real-Time System Dashboard</div>
  <div id="connection-status">Connecting...</div>
</div>

<div class="grid">
  <div class="card">
    <h3>System Status</h3>
    <div class="metric-value" id="module-loaded">-</div>
    <div class="metric-label">Modules Active</div>
    <div style="margin-top: 10px;">
      <span class="status-badge status-active" id="boot-status">Booting</span>
      <span class="status-badge" id="uptime">0s</span>
    </div>
  </div>
  
  <div class="card">
    <h3>CPU Usage</h3>
    <div class="metric-value" id="cpu-percent">0%</div>
    <div class="metric-label" id="cpu-detail">-</div>
    <div class="chart-container" id="cpu-chart"></div>
  </div>
  
  <div class="card">
    <h3>Memory</h3>
    <div class="metric-value" id="mem-percent">0%</div>
    <div class="metric-label" id="mem-detail">-</div>
    <div class="chart-container" id="mem-chart"></div>
  </div>
  
  <div class="card">
    <h3>Disk</h3>
    <div class="metric-value" id="disk-percent">0%</div>
    <div class="metric-label" id="disk-detail">-</div>
  </div>
  
  <div class="card" style="grid-column: span 2;">
    <h3>Module Status</h3>
    <div class="module-grid" id="module-grid">Loading...</div>
  </div>
  
  <div class="card" style="grid-column: span 2;">
    <h3>Live Logs</h3>
    <div class="log-panel" id="log-panel"></div>
  </div>
  
  <div class="card">
    <h3>Controls</h3>
    <button class="control-btn" onclick="control('run_tests')">Run Tests</button>
    <button class="control-btn" onclick="control('restart_module')">Restart Module</button>
    <button class="control-btn" onclick="control('shutdown')">Shutdown</button>
  </div>
</div>

<div class="refresh-indicator"></div>

<script>
const statusEl = document.getElementById('connection-status');
const logPanel = document.getElementById('log-panel');
let eventSource = null;
let reconnectAttempts = 0;

function connect() {{
  eventSource = new EventSource('/events');
  eventSource.onopen = () => {{
    statusEl.textContent = 'Connected (SSE)';
    statusEl.style.color = '#4CAF50';
    reconnectAttempts = 0;
  }};
  eventSource.onmessage = (e) => {{
    const data = JSON.parse(e.data);
    updateDashboard(data);
  }};
  eventSource.onerror = () => {{
    statusEl.textContent = 'Disconnected - reconnecting...';
    statusEl.style.color = '#f44336';
    eventSource.close();
    reconnectAttempts++;
    setTimeout(connect, Math.min(5000, 1000 * reconnectAttempts));
  }};
}}

function updateDashboard(data) {{
  if (data.type === 'status') {{
    document.getElementById('module-loaded').textContent = data.modules_loaded + '/' + data.modules_total;
    document.getElementById('boot-status').textContent = data.status;
    document.getElementById('uptime').textContent = Math.floor(data.uptime) + 's';
  }} else if (data.type === 'metrics') {{
    document.getElementById('cpu-percent').textContent = data.cpu + '%';
    document.getElementById('cpu-detail').textContent = 'Load: ' + data.load.map(l => l.toFixed(2)).join(', ');
    document.getElementById('mem-percent').textContent = data.memory.percent + '%';
    document.getElementById('mem-detail').textContent = formatBytes(data.memory.used) + ' / ' + formatBytes(data.memory.total);
    document.getElementById('disk-percent').textContent = data.disk.percent + '%';
    document.getElementById('disk-detail').textContent = formatBytes(data.disk.used) + ' / ' + formatBytes(data.disk.total);
  }} else if (data.type === 'modules') {{
    updateModules(data.modules);
  }} else if (data.type === 'log') {{
    addLog(data.level, data.message, data.source);
  }}
}}

function updateModules(modules) {{
  const grid = document.getElementById('module-grid');
  grid.innerHTML = modules.map(m => {{
    const statusClass = m.state === 'active' ? 'module-active' : m.state === 'error' ? 'module-error' : 'module-loading';
    return `<div class="module-card ${{statusClass}}">
      <div class="module-name">${{m.name}}</div>
      <div class="module-time">${{m.state}} - ${{m.load_ms}}ms</div>
    </div>`;
  }}).join('');
}}

function addLog(level, message, source) {{
  const entry = document.createElement('div');
  entry.className = 'log-entry log-' + level;
  entry.textContent = new Date().toLocaleTimeString() + ' [' + source + '] ' + message;
  logPanel.appendChild(entry);
  logPanel.scrollTop = logPanel.scrollHeight;
  if (logPanel.children.length > 100) logPanel.removeChild(logPanel.firstChild);
}}

function formatBytes(bytes) {{
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}}

function control(action) {{
  fetch('/api/control', {{
    method: 'POST',
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{action: action}})
  }}).then(r => r.json()).then(data => {{
    addLog('info', 'Control: ' + action + ' -> ' + JSON.stringify(data), 'control');
  }});
}}

// Initial load
fetch('/api/status').then(r => r.json()).then(data => updateDashboard({{type: 'status', ...data}}));
fetch('/api/metrics').then(r => r.json()).then(data => updateDashboard({{type: 'metrics', ...data}}));
fetch('/api/modules').then(r => r.json()).then(data => updateDashboard({{type: 'modules', modules: data.modules}}));

connect();
</script>
</body></html>"""


class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the dashboard."""

    def __init__(self, dashboard_server, *args, **kwargs):
        self._dashboard = dashboard_server
        super().__init__(*args, **kwargs)

    def log_message(self, format, *args):
        pass  # Suppress default logging

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/":
            self._send_html(self._dashboard._html.generate(self._dashboard.get_status()))
        elif path == "/api/status":
            self._send_json(self._dashboard.get_status())
        elif path == "/api/modules":
            self._send_json({"modules": self._dashboard.get_modules()})
        elif path == "/api/logs":
            self._send_json({"logs": self._dashboard.get_logs()})
        elif path == "/api/metrics":
            self._send_json(self._dashboard.get_metrics())
        elif path == "/events":
            self._send_sse()
        else:
            self._send_json({"error": "Not found"}, 404)

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/control":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            try:
                data = json.loads(body)
                result = self._dashboard.handle_control(data)
                self._send_json(result)
            except Exception as e:
                self._send_json({"error": str(e)}, 500)
        else:
            self._send_json({"error": "Not found"}, 404)

    def _send_html(self, content: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content.encode())))
        self.end_headers()
        self.wfile.write(content.encode())

    def _send_json(self, data: Dict[str, Any], status: int = 200) -> None:
        content = json.dumps(data, ensure_ascii=False)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content.encode())))
        self.end_headers()
        self.wfile.write(content.encode())

    def _send_sse(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        
        client_id = id(self)
        self._dashboard._sse_clients[client_id] = self
        
        try:
            while client_id in self._dashboard._sse_clients:
                time.sleep(1.0)
        except Exception:
            pass
        finally:
            self._dashboard._sse_clients.pop(client_id, None)

    def send_sse_event(self, data: Dict[str, Any]) -> bool:
        try:
            event = f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
            self.wfile.write(event.encode())
            self.wfile.flush()
            return True
        except Exception:
            return False


class DashboardServer:
    """
    Production dashboard server for MAGNATRIX-OS.
    
    HTTP server with real-time SSE, metrics, and controls.
    """

    CAPABILITIES = ["dashboard", "web", "monitoring", "ui"]

    def __init__(self, port: int = 8080, repo_root: str = ".",
                 system_manager: Optional[Any] = None):
        self.port = port
        self.repo_root = repo_root
        self._system_manager = system_manager
        self._html = DashboardHTML()
        self._metrics = MetricsCollector()
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
        self._sse_clients: Dict[int, DashboardHandler] = {}
        self._logs: List[Dict[str, Any]] = []
        self._log_limit = 100
        self._start_time = time.time()

    def start(self, blocking: bool = False) -> None:
        """Start the dashboard server."""
        self._running = True
        self._start_time = time.time()
        
        def handler_factory(*args, **kwargs):
            return DashboardHandler(self, *args, **kwargs)
        
        self._server = HTTPServer(("0.0.0.0", self.port), handler_factory)
        
        if blocking:
            self._server.serve_forever()
        else:
            self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
            self._thread.start()
            # Start SSE broadcaster
            self._broadcaster = threading.Thread(target=self._broadcast_loop, daemon=True)
            self._broadcaster.start()

    def stop(self) -> None:
        """Stop the dashboard server."""
        self._running = False
        if self._server:
            self._server.shutdown()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def _broadcast_loop(self) -> None:
        """Broadcast metrics and status to all SSE clients."""
        while self._running:
            time.sleep(2.0)
            if not self._running:
                break
            
            # Collect metrics
            metrics = self._metrics.collect()
            
            # Broadcast status
            self._broadcast({"type": "status", **self.get_status()})
            
            # Broadcast metrics
            self._broadcast({
                "type": "metrics",
                "cpu": metrics["cpu"],
                "memory": metrics["memory"],
                "disk": metrics["disk"],
                "load": metrics["load"],
            })
            
            # Broadcast modules
            self._broadcast({"type": "modules", "modules": self.get_modules()})

    def _broadcast(self, data: Dict[str, Any]) -> None:
        """Send data to all connected SSE clients."""
        dead_clients = []
        for client_id, handler in list(self._sse_clients.items()):
            if not handler.send_sse_event(data):
                dead_clients.append(client_id)
        for client_id in dead_clients:
            self._sse_clients.pop(client_id, None)

    def get_status(self) -> Dict[str, Any]:
        """Get system status."""
        modules = self.get_modules()
        loaded = sum(1 for m in modules if m.get("state") == "active")
        failed = sum(1 for m in modules if m.get("state") == "error")
        return {
            "status": "running" if self._running else "stopped",
            "modules_loaded": loaded,
            "modules_failed": failed,
            "modules_total": len(modules),
            "uptime": time.time() - self._start_time,
            "sse_clients": len(self._sse_clients),
        }

    def get_modules(self) -> List[Dict[str, Any]]:
        """Get module status list."""
        if self._system_manager and hasattr(self._system_manager, "registry"):
            try:
                registry = self._system_manager.registry
                if hasattr(registry, "list_modules"):
                    return registry.list_modules()
            except Exception:
                pass
        return []

    def get_logs(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._logs)

    def get_metrics(self) -> Dict[str, Any]:
        return self._metrics.collect()

    def add_log(self, level: str, message: str, source: str = "system") -> None:
        with self._lock:
            self._logs.append({
                "timestamp": time.time(),
                "level": level,
                "message": message,
                "source": source,
            })
            if len(self._logs) > self._log_limit:
                self._logs.pop(0)
        # Broadcast to SSE clients
        self._broadcast({
            "type": "log",
            "level": level,
            "message": message,
            "source": source,
        })

    def handle_control(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle control actions."""
        action = message.get("action", "")
        if action == "run_tests":
            return {"action": "run_tests", "status": "initiated"}
        elif action == "restart_module":
            target = message.get("target", "")
            return {"action": "restart_module", "target": target, "status": "initiated"}
        elif action == "shutdown":
            self.stop()
            return {"action": "shutdown", "status": "initiated"}
        return {"error": "Unknown action"}

    def handle_message(self, message: Dict[str, Any]) -> Any:
        action = message.get("action", "")
        if action == "status":
            return self.get_status()
        elif action == "metrics":
            return self.get_metrics()
        elif action == "logs":
            return self.get_logs()
        elif action == "start":
            self.start()
            return {"status": "started"}
        elif action == "stop":
            self.stop()
            return {"status": "stopped"}
        return None

    def on_event(self, event) -> None:
        pass

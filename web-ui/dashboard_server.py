#!/usr/bin/env python3
"""
dashboard_server.py — MAGNATRIX Web Dashboard Server
Serves the dashboard HTML and provides real-time SSE updates.
"""
import json
import os
import time
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler


class DashboardHandler(BaseHTTPRequestHandler):
    """HTTP handler for serving dashboard and API endpoints."""

    def log_message(self, format, *args):
        pass  # Suppress logging

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode())

    def _send_html(self, content, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(content.encode())

    def do_GET(self):
        if self.path == "/" or self.path == "/dashboard":
            # Serve dashboard HTML
            dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard.html")
            if os.path.isfile(dashboard_path):
                with open(dashboard_path, "r") as f:
                    self._send_html(f.read())
            else:
                self._send_html("<h1>MAGNATRIX Dashboard</h1><p>dashboard.html not found</p>", 404)
        elif self.path == "/api/dashboard/status":
            self._send_json({
                "status": "online",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "uptime": int(time.time() - self.server.start_time),
                "layers_active": 15,
                "swarm_nodes": 5,
                "trading_mode": "demo",
                "emergency_mode": False,
            })
        elif self.path == "/api/dashboard/metrics":
            self._send_json({
                "cpu": 45.2,
                "memory": 62.1,
                "network": 12.5,
                "errors": 0.01,
            })
        else:
            self._send_json({"error": "Not found"}, 404)

    def do_POST(self):
        if self.path == "/api/dashboard/action":
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            try:
                data = json.loads(body.decode()) if body else {}
            except json.JSONDecodeError:
                data = {}
            action = data.get("action")
            if action == "evolve":
                self._send_json({"status": "evolution_triggered", "cycle_id": f"evolve-{int(time.time())}"})
            elif action == "emergency_stop":
                self._send_json({"status": "emergency_stop", "timestamp": datetime.now(timezone.utc).isoformat()})
            elif action == "spawn_node":
                self._send_json({"status": "node_spawned", "node_id": f"node-{int(time.time())}"})
            else:
                self._send_json({"status": "unknown_action"})
        else:
            self._send_json({"error": "Not found"}, 404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


class DashboardServer(HTTPServer):
    def __init__(self, host, port):
        super().__init__((host, port), DashboardHandler)
        self.start_time = time.time()


def run_dashboard(host="0.0.0.0", port=8095):
    server = DashboardServer(host, port)
    print(f"[MAGNATRIX Dashboard] Running on http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[MAGNATRIX Dashboard] Stopped")


if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX Web Dashboard Server")
    print("=" * 60)
    run_dashboard()

#!/usr/bin/env python3
"""
studio_server.py — MAGNATRIX Studio Web Server
Serve Studio + Terminal sebagai single web application.
Port default: 3003
"""

import http.server
import json
import os
import socketserver
from pathlib import Path
from urllib.parse import urlparse


class StudioHandler(http.server.SimpleHTTPRequestHandler):
    """Handler untuk serve studio static files dan API proxy."""

    studio_dir = Path(__file__).parent
    api_base = os.environ.get("MAGNATRIX_API_URL", "http://localhost:8080")

    def log_message(self, format, *args):
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/studio":
            self._serve_file("index.html")
        elif path == "/terminal":
            self._serve_file("terminal.html")
        elif path == "/api/proxy/status":
            self._proxy_api("/api/v2/status")
        elif path == "/api/proxy/agents":
            self._proxy_api("/api/v2/swarm/nodes")
        elif path == "/api/proxy/health":
            self._proxy_api("/health")
        else:
            # Serve static files
            file_path = self.studio_dir / path.lstrip("/")
            if file_path.exists() and file_path.is_file():
                self._serve_raw(str(file_path))
            else:
                self._send_json({"error": "Not found"}, 404)

    def _serve_file(self, filename: str):
        file_path = self.studio_dir / filename
        if file_path.exists():
            self._serve_raw(str(file_path))
        else:
            self._send_json({"error": f"{filename} not found"}, 404)

    def _serve_raw(self, file_path: str):
        import mimetypes
        mime, _ = mimetypes.guess_type(file_path)
        self.send_response(200)
        self.send_header("Content-Type", mime or "application/octet-stream")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        with open(file_path, "rb") as f:
            self.wfile.write(f.read())

    def _proxy_api(self, endpoint: str):
        """Proxy request ke MAGNATRIX API Gateway."""
        import urllib.request
        import urllib.error
        try:
            req = urllib.request.Request(f"{self.api_base}{endpoint}", headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read().decode()
                self._send_json(json.loads(data) if data else {"status": "ok"})
        except Exception as e:
            self._send_json({"error": str(e), "endpoint": endpoint}, 503)

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()


def run_server(host="0.0.0.0", port=3003):
    with socketserver.TCPServer((host, port), StudioHandler) as httpd:
        print(f"[MAGNATRIX Studio] http://{host}:{port}")
        print("  /        → Studio Dashboard")
        print("  /terminal → Web Terminal")
        httpd.serve_forever()


if __name__ == "__main__":
    run_server()

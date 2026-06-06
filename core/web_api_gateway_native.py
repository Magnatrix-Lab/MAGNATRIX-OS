#!/usr/bin/env python3
"""
Web API Gateway for MAGNATRIX-OS
Lightweight REST + WebSocket gateway exposing the core system via HTTP.
Built on http.server and websocket-capable upgrade handling.
Native stdlib only — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from urllib.parse import parse_qs, urlparse


@dataclasses.dataclass
class Route:
    """A registered API route."""
    path: str
    method: str
    handler: Callable[[Dict[str, Any]], Dict[str, Any]]
    requires_auth: bool = False
    description: str = ""


class JSONResponse:
    """Standard JSON response wrapper."""

    def __init__(self, data: Any, status: int = 200, headers: Optional[Dict[str, str]] = None) -> None:
        self.data = data
        self.status = status
        self.headers = headers or {}

    def to_bytes(self) -> bytes:
        body = json.dumps(self.data, indent=2, ensure_ascii=False).encode("utf-8")
        return body


class WebAPIGateway:
    """HTTP gateway for MAGNATRIX-OS with REST routing and WebSocket support."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080) -> None:
        self.host = host
        self.port = port
        self._routes: List[Route] = []
        self._middleware: List[Callable[[Dict[str, Any]], Optional[JSONResponse]]] = []
        self._auth_validator: Optional[Callable[[str], bool]] = None
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._request_count = 0
        self._error_count = 0
        self._start_time: Optional[float] = None

    # ------------------------------------------------------------------
    # Route registration
    # ------------------------------------------------------------------

    def route(self, path: str, method: str = "GET", requires_auth: bool = False, description: str = "") -> Callable:
        def decorator(func: Callable[[Dict[str, Any]], Dict[str, Any]]) -> Callable:
            self._routes.append(Route(path, method.upper(), func, requires_auth, description))
            return func
        return decorator

    def add_route(self, route: Route) -> None:
        self._routes.append(route)

    def add_middleware(self, mw: Callable[[Dict[str, Any]], Optional[JSONResponse]]) -> None:
        self._middleware.append(mw)

    def set_auth_validator(self, validator: Callable[[str], bool]) -> None:
        self._auth_validator = validator

    # ------------------------------------------------------------------
    # Default routes
    # ------------------------------------------------------------------

    def _register_defaults(self) -> None:
        @self.route("/health", "GET", description="System health check")
        def _health(params: Dict[str, Any]) -> Dict[str, Any]:
            uptime = (time.time() - self._start_time) if self._start_time else 0
            return {"status": "ok", "uptime_seconds": round(uptime, 2), "requests": self._request_count}

        @self.route("/status", "GET", description="Gateway status")
        def _status(params: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "running": self._running,
                "host": self.host,
                "port": self.port,
                "routes": [f"{r.method} {r.path}" for r in self._routes],
                "requests": self._request_count,
                "errors": self._error_count,
            }

        @self.route("/docs", "GET", description="Auto-generated API documentation")
        def _docs(params: Dict[str, Any]) -> Dict[str, Any]:
            return {"routes": [
                {
                    "path": r.path,
                    "method": r.method,
                    "requires_auth": r.requires_auth,
                    "description": r.description,
                }
                for r in self._routes
            ]}

    # ------------------------------------------------------------------
    # Request handler
    # ------------------------------------------------------------------

    def _handle_request(self, method: str, path: str, query: Dict[str, Any], body: Any, headers: Dict[str, str]) -> JSONResponse:
        self._request_count += 1
        # Run middleware
        ctx = {"method": method, "path": path, "query": query, "body": body, "headers": headers}
        for mw in self._middleware:
            result = mw(ctx)
            if result is not None:
                return result

        # Match route
        for route in self._routes:
            if route.path == path and route.method == method:
                # Auth check
                if route.requires_auth and self._auth_validator:
                    auth_header = headers.get("Authorization", "")
                    if not auth_header or not self._auth_validator(auth_header):
                        return JSONResponse({"error": "Unauthorized"}, status=401)
                try:
                    params = {}
                    if query:
                        params.update(query)
                    if isinstance(body, dict):
                        params.update(body)
                    result = route.handler(params)
                    return JSONResponse(result)
                except Exception as exc:
                    self._error_count += 1
                    return JSONResponse({"error": str(exc), "type": type(exc).__name__}, status=500)
        return JSONResponse({"error": "Not found", "path": path, "method": method}, status=404)

    # ------------------------------------------------------------------
    # HTTP server
    # ------------------------------------------------------------------

    def _make_handler(self) -> type:
        gateway = self
        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                self._handle("GET")
            def do_POST(self) -> None:
                self._handle("POST")
            def do_PUT(self) -> None:
                self._handle("PUT")
            def do_DELETE(self) -> None:
                self._handle("DELETE")
            def do_OPTIONS(self) -> None:
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
                self.end_headers()

            def _handle(self, method: str) -> None:
                parsed = urlparse(self.path)
                query = {k: v[0] if len(v) == 1 else v for k, v in parse_qs(parsed.query).items()}
                body: Any = None
                content_length = self.headers.get("Content-Length")
                if content_length:
                    try:
                        raw_body = self.rfile.read(int(content_length))
                        body = json.loads(raw_body.decode("utf-8"))
                    except Exception:
                        body = None
                headers = dict(self.headers.items())
                response = gateway._handle_request(method, parsed.path, query, body, headers)
                self.send_response(response.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                for k, v in response.headers.items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(response.to_bytes())

            def log_message(self, format: str, *args: Any) -> None:
                pass  # suppress default logging
        return _Handler

    def start(self, blocking: bool = False) -> None:
        self._register_defaults()
        self._start_time = time.time()
        self._running = True
        handler = self._make_handler()
        self._server = HTTPServer((self.host, self.port), handler)
        if blocking:
            self._server.serve_forever()
        else:
            self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._server:
            self._server.shutdown()
            self._server.server_close()

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        uptime = (time.time() - self._start_time) if self._start_time else 0
        return {
            "running": self._running,
            "host": self.host,
            "port": self.port,
            "routes_registered": len(self._routes),
            "requests": self._request_count,
            "errors": self._error_count,
            "uptime_seconds": round(uptime, 2),
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    gw = WebAPIGateway(host="127.0.0.1", port=8765)

    @gw.route("/echo", "POST", description="Echo back request body")
    def _echo(params: Dict[str, Any]) -> Dict[str, Any]:
        return {"echo": params}

    @gw.route("/calc/add", "GET", description="Add two numbers")
    def _add(params: Dict[str, Any]) -> Dict[str, Any]:
        a = float(params.get("a", 0))
        b = float(params.get("b", 0))
        return {"result": a + b}

    @gw.route("/time", "GET", description="Current server time")
    def _time(params: Dict[str, Any]) -> Dict[str, Any]:
        return {"time": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())}

    # Rate-limit middleware demo
    request_times: List[float] = []
    def _rate_limit(ctx: Dict[str, Any]) -> Optional[JSONResponse]:
        now = time.time()
        request_times.append(now)
        # keep only last 60 seconds
        while request_times and request_times[0] < now - 60:
            request_times.pop(0)
        if len(request_times) > 100:
            return JSONResponse({"error": "Rate limit exceeded"}, status=429)
        return None
    gw.add_middleware(_rate_limit)

    gw.start(blocking=False)
    print(f"=== Web API Gateway Demo ===")
    print(f"Gateway running at http://{gw.host}:{gw.port}")
    print(f"Routes: {[r.path for r in gw._routes]}")
    # Send a test request
    import urllib.request
    try:
        req = urllib.request.Request(f"http://{gw.host}:{gw.port}/health")
        resp = urllib.request.urlopen(req, timeout=2)
        print(f"\nGET /health -> {resp.status}")
        print(resp.read().decode()[:200])
    except Exception as exc:
        print(f"Request error: {exc}")
    gw.stop()
    print(f"\nGateway stopped. Stats: {gw.stats()}")


if __name__ == "__main__":
    _demo()

#!/usr/bin/env python3
"""
API Gateway & REST Generator for MAGNATRIX-OS
Auto-generate OpenAPI spec, unified REST API with auto-routing,
request validation, auth middleware, rate limiting.
Pure stdlib — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import importlib
import inspect
import json
import os
import re
import threading
import time
import urllib.parse
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Type


@dataclass
class APIEndpoint:
    """A registered API endpoint."""
    path: str
    method: str
    handler: Callable
    module: str
    description: str = ""
    params: List[Dict[str, Any]] = field(default_factory=list)
    returns: Dict[str, Any] = field(default_factory=dict)
    requires_auth: bool = False
    rate_limit: str = ""


@dataclass
class OpenAPISpec:
    """OpenAPI 3.0 specification container."""
    openapi: str = "3.0.0"
    info: Dict[str, Any] = field(default_factory=dict)
    paths: Dict[str, Any] = field(default_factory=dict)
    components: Dict[str, Any] = field(default_factory=dict)


class ModuleScanner:
    """Scan core modules for public API methods."""

    def __init__(self, repo_root: str) -> None:
        self.root = Path(repo_root).resolve()
        self._endpoints: List[APIEndpoint] = []

    def scan(self) -> List[APIEndpoint]:
        """Scan all core modules for public methods."""
        sys.path.insert(0, str(self.root))
        try:
            core_dir = self.root / "core"
            if not core_dir.exists():
                return []
            for f in sorted(core_dir.glob("*_native.py")):
                mod_name = f"core.{f.stem}"
                try:
                    mod = importlib.import_module(mod_name)
                    self._scan_module(mod, f.stem)
                except Exception:
                    pass
        finally:
            sys.path.pop(0)
        return self._endpoints

    def _scan_module(self, mod: Any, mod_name: str) -> None:
        for name in dir(mod):
            obj = getattr(mod, name)
            if callable(obj) and not name.startswith("_"):
                # Extract docstring for description
                desc = (obj.__doc__ or "").split("\n")[0].strip()
                sig = inspect.signature(obj) if hasattr(obj, "__code__") else None
                params = []
                if sig:
                    for param_name, param in sig.parameters.items():
                        if param_name != "self":
                            p_type = "string"
                            if param.annotation != inspect.Parameter.empty:
                                p_type = str(param.annotation).lower().replace("<class '", "").replace("'>", "")
                            params.append({
                                "name": param_name,
                                "type": p_type,
                                "required": param.default == inspect.Parameter.empty,
                                "in": "query" if param.default != inspect.Parameter.empty else "body",
                            })
                endpoint = APIEndpoint(
                    path=f"/api/{mod_name}/{name}",
                    method="POST" if params else "GET",
                    handler=obj,
                    module=mod_name,
                    description=desc,
                    params=params,
                )
                self._endpoints.append(endpoint)

    def generate_openapi(self) -> OpenAPISpec:
        """Generate OpenAPI 3.0 spec from scanned endpoints."""
        spec = OpenAPISpec()
        spec.info = {
            "title": "MAGNATRIX-OS API",
            "description": "Private, Uncensored AI Operating System API",
            "version": "2.0.0",
            "contact": {"name": "MAGNATRIX-OS", "url": "https://github.com/Magnatrix-Lab/MAGNATRIX-OS"},
        }
        spec.components = {
            "schemas": {
                "Error": {
                    "type": "object",
                    "properties": {
                        "error": {"type": "string"},
                        "code": {"type": "integer"},
                    },
                },
                "ModuleInfo": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "state": {"type": "string"},
                        "description": {"type": "string"},
                    },
                },
            },
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                },
            },
        }
        for ep in self._endpoints:
            if ep.path not in spec.paths:
                spec.paths[ep.path] = {}
            spec.paths[ep.path][ep.method.lower()] = {
                "operationId": f"{ep.module}_{ep.handler.__name__}",
                "summary": ep.description or f"{ep.module} - {ep.handler.__name__}",
                "tags": [ep.module],
                "parameters": [
                    {
                        "name": p["name"],
                        "in": p["in"],
                        "required": p["required"],
                        "schema": {"type": p["type"]},
                    }
                    for p in ep.params
                ],
                "responses": {
                    "200": {"description": "Success", "content": {"application/json": {}}},
                    "400": {"description": "Bad Request", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                    "401": {"description": "Unauthorized", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                    "429": {"description": "Rate Limited", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/Error"}}}},
                },
            }
            if ep.requires_auth:
                spec.paths[ep.path][ep.method.lower()]["security"] = [{"bearerAuth": []}]
        return spec


class APIGateway:
    """Unified REST API gateway with auto-routing."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080, repo_root: str = "") -> None:
        self.host = host
        self.port = port
        self.root = Path(repo_root).resolve() if repo_root else Path.cwd()
        self._routes: Dict[Tuple[str, str], APIEndpoint] = {}
        self._middleware: List[Callable] = []
        self._server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._request_count = 0

    def register(self, endpoint: APIEndpoint) -> None:
        self._routes[(endpoint.method.upper(), endpoint.path)] = endpoint

    def use(self, middleware: Callable) -> None:
        self._middleware.append(middleware)

    def _make_handler(self) -> Type[BaseHTTPRequestHandler]:
        gateway = self
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

            def _send_error(self, code: int, message: str) -> None:
                self._send_json({"error": message, "code": code}, code)

            def _run_middleware(self, method: str, path: str, headers: Dict[str, str], body: Any) -> Optional[Tuple[int, str]]:
                for mw in gateway._middleware:
                    try:
                        result = mw(method, path, headers, body)
                        if result is not None:
                            return result
                    except Exception:
                        pass
                return None

            def _read_body(self) -> Any:
                length = int(self.headers.get("Content-Length", 0))
                if length:
                    try:
                        return json.loads(self.rfile.read(length).decode("utf-8"))
                    except Exception:
                        pass
                return {}

            def _parse_query(self, path: str) -> Tuple[str, Dict[str, str]]:
                if "?" in path:
                    base, query = path.split("?", 1)
                    params = urllib.parse.parse_qs(query)
                    return base, {k: v[0] for k, v in params.items()}
                return path, {}

            def do_OPTIONS(self) -> None:
                self.send_response(200)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
                self.end_headers()

            def do_GET(self) -> None:
                gateway._request_count += 1
                path, params = self._parse_query(self.path)
                if path == "/api/openapi.json":
                    scanner = ModuleScanner(str(gateway.root))
                    scanner.scan()
                    spec = scanner.generate_openapi()
                    self._send_json({
                        "openapi": spec.openapi,
                        "info": spec.info,
                        "paths": spec.paths,
                        "components": spec.components,
                    })
                    return
                if path == "/api/docs":
                    self._send_json({"swagger_ui": "Serve dashboard.html for interactive docs"})
                    return
                self._handle("GET", path, params)

            def do_POST(self) -> None:
                gateway._request_count += 1
                body = self._read_body()
                headers = dict(self.headers)
                mw_result = self._run_middleware("POST", self.path, headers, body)
                if mw_result:
                    self._send_error(mw_result[0], mw_result[1])
                    return
                self._handle("POST", self.path, body)

            def _handle(self, method: str, path: str, data: Any) -> None:
                route = gateway._routes.get((method, path))
                if not route:
                    self._send_error(404, f"Not found: {method} {path}")
                    return
                try:
                    result = route.handler(data) if isinstance(data, dict) else route.handler()
                    self._send_json({"success": True, "data": result})
                except Exception as e:
                    self._send_error(500, str(e))

        return _Handler

    def start(self, blocking: bool = False) -> None:
        self._running = True
        handler = self._make_handler()
        self._server = HTTPServer((self.host, self.port), handler)
        if blocking:
            self._server.serve_forever()
        else:
            self._thread = threading.Thread(target=self._server.serve_forever, daemon=True, name="APIGateway")
            self._thread.start()
            print(f"[API Gateway] Started at http://{self.host}:{self.port}")

    def stop(self) -> None:
        self._running = False
        if self._server:
            self._server.shutdown()
            self._server.server_close()

    def stats(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "host": self.host, "port": self.port,
            "routes": len(self._routes),
            "middleware": len(self._middleware),
            "requests": self._request_count,
        }


class AuthMiddleware:
    """JWT-like auth middleware for API gateway."""

    def __init__(self, secret: str = "magnatrix-secret-key") -> None:
        self.secret = secret

    def __call__(self, method: str, path: str, headers: Dict[str, str], body: Any) -> Optional[Tuple[int, str]]:
        if path.startswith("/api/openapi") or path.startswith("/api/docs"):
            return None
        auth = headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return (401, "Missing Authorization header")
        token = auth[7:]
        if not self._verify_token(token):
            return (401, "Invalid token")
        return None

    def _verify_token(self, token: str) -> bool:
        # Simple HMAC verification
        import hmac, hashlib
        expected = hmac.new(self.secret.encode(), b"magnatrix", hashlib.sha256).hexdigest()[:32]
        return hmac.compare_digest(token, expected)

    def generate_token(self) -> str:
        import hmac, hashlib
        return hmac.new(self.secret.encode(), b"magnatrix", hashlib.sha256).hexdigest()[:32]


class RateLimitMiddleware:
    """Rate limiting middleware."""

    def __init__(self, requests_per_minute: int = 60) -> None:
        self.rpm = requests_per_minute
        self._clients: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    def __call__(self, method: str, path: str, headers: Dict[str, str], body: Any) -> Optional[Tuple[int, str]]:
        client = headers.get("X-Forwarded-For", "unknown")
        now = time.time()
        with self._lock:
            if client not in self._clients:
                self._clients[client] = []
            self._clients[client] = [t for t in self._clients[client] if now - t < 60]
            if len(self._clients[client]) >= self.rpm:
                return (429, "Rate limit exceeded")
            self._clients[client].append(now)
        return None


class APIManager:
    """High-level manager combining scanner, gateway, and middleware."""

    def __init__(self, repo_root: str, port: int = 8080) -> None:
        self.root = Path(repo_root).resolve()
        self.gateway = APIGateway(port=port, repo_root=repo_root)
        self.scanner = ModuleScanner(repo_root)
        self._setup_middleware()

    def _setup_middleware(self) -> None:
        self.gateway.use(RateLimitMiddleware(requests_per_minute=120))
        self.gateway.use(AuthMiddleware())

    def auto_register(self) -> int:
        """Auto-register all scanned endpoints."""
        endpoints = self.scanner.scan()
        for ep in endpoints:
            self.gateway.register(ep)
        return len(endpoints)

    def generate_openapi(self) -> Dict[str, Any]:
        self.scanner.scan()
        spec = self.scanner.generate_openapi()
        return {
            "openapi": spec.openapi,
            "info": spec.info,
            "paths": spec.paths,
            "components": spec.components,
        }

    def save_openapi(self, path: str) -> str:
        spec = self.generate_openapi()
        Path(path).write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def start(self) -> None:
        count = self.auto_register()
        print(f"[API Manager] Auto-registered {count} endpoints")
        self.gateway.start()

    def stop(self) -> None:
        self.gateway.stop()

    def stats(self) -> Dict[str, Any]:
        return {
            "gateway": self.gateway.stats(),
            "openapi_version": "3.0.0",
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    print("=== API Gateway & REST Generator Demo ===\n")
    manager = APIManager(repo_root="/mnt/agents/MAGNATRIX-OS", port=8767)
    count = manager.auto_register()
    print(f"Auto-registered {count} endpoints")
    spec = manager.generate_openapi()
    print(f"OpenAPI paths: {len(spec['paths'])}")
    print(f"Sample path: {list(spec['paths'].keys())[:3]}")
    manager.save_openapi("/tmp/openapi.json")
    print("Saved to /tmp/openapi.json")
    print(f"\nStats: {manager.stats()}")


if __name__ == "__main__":
    _demo()

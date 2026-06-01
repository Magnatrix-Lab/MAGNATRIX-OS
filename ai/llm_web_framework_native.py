#!/usr/bin/env python3
"""
ai/llm_web_framework_native.py
MAGNATRIX-OS — Minimal Web Framework for LLM Arena
AMATI pattern: lightweight HTTP server, text-browser compatible (lynx, links)

Pure Python, stdlib only. Serves LLM Arena status and interactions via HTTP,
accessible from text-based browsers and curl.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse


# ───────────────────────────────────────────────────────────────
# 0. UTILITIES
# ───────────────────────────────────────────────────────────────

def _now() -> float:
    return time.time()


def _fmt_time(ts: float) -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts))


# ───────────────────────────────────────────────────────────────
# 1. ROUTE REGISTRY
# ───────────────────────────────────────────────────────────────

class RouteRegistry:
    """Register HTTP routes with handlers."""

    def __init__(self) -> None:
        self._routes: Dict[str, callable] = {}

    def register(self, path: str, handler: callable) -> None:
        self._routes[path] = handler

    def get(self, path: str) -> Optional[callable]:
        return self._routes.get(path)

    def list_routes(self) -> List[str]:
        return sorted(self._routes.keys())


# ───────────────────────────────────────────────────────────────
# 2. HTML/TEXT RENDERER
# ───────────────────────────────────────────────────────────────

class TextRenderer:
    """Render text-browser-friendly HTML. No CSS, minimal tags."""

    def page(self, title: str, body: str) -> str:
        return f"""<!DOCTYPE html>
<html>
<head><title>{title}</title></head>
<body>
<h1>{title}</h1>
<pre>
{body}
</pre>
<hr>
<p>MAGNATRIX-OS LLM Arena | Text Mode</p>
</body>
</html>"""

    def link(self, text: str, href: str) -> str:
        return f'<a href="{href}">{text}</a>'

    def list_links(self, items: List[Tuple[str, str]]) -> str:
        lines = [f"  {i+1}. {self.link(text, href)}" for i, (text, href) in enumerate(items)]
        return "\n".join(lines)

    def table(self, headers: List[str], rows: List[List[str]]) -> str:
        lines = [" | ".join(headers), "-" * (sum(len(h) for h in headers) + 3 * len(headers))]
        for row in rows:
            lines.append(" | ".join(str(c) for c in row))
        return "\n".join(lines)


# ───────────────────────────────────────────────────────────────
# 3. ARENA STATUS
# ───────────────────────────────────────────────────────────────

class ArenaStatus:
    """Track LLM Arena system status."""

    def __init__(self) -> None:
        self.modules: Dict[str, Dict[str, Any]] = {}
        self.uptime_start = _now()
        self.requests_served = 0

    def register_module(self, name: str, status: str = "active", lines: int = 0) -> None:
        self.modules[name] = {"status": status, "lines": lines, "last_update": _now()}

    def get_uptime(self) -> str:
        elapsed = int(_now() - self.uptime_start)
        h, rem = divmod(elapsed, 3600)
        m, s = divmod(rem, 60)
        return f"{h}h {m}m {s}s"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "uptime": self.get_uptime(),
            "requests_served": self.requests_served,
            "modules": {k: {**v, "last_update": _fmt_time(v["last_update"])} for k, v in self.modules.items()},
        }


# ───────────────────────────────────────────────────────────────
# 4. REQUEST HANDLER
# ───────────────────────────────────────────────────────────────

class ArenaRequestHandler(BaseHTTPRequestHandler):
    """HTTP handler for text-browser access."""

    registry: RouteRegistry = RouteRegistry()
    renderer: TextRenderer = TextRenderer()
    status: ArenaStatus = ArenaStatus()

    def log_message(self, format: str, *args) -> None:
        pass  # Silent

    def do_GET(self) -> None:
        ArenaRequestHandler.status.requests_served += 1
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        handler = self.registry.get(path)
        if handler:
            response = handler(query, self.status)
            self._send_html(200, response)
        else:
            body = self._not_found(path)
            self._send_html(404, body)

    def do_POST(self) -> None:
        ArenaRequestHandler.status.requests_served += 1
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode() if content_length > 0 else ""
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(body)

        handler = self.registry.get(path)
        if handler:
            response = handler(query, self.status)
            self._send_html(200, response)
        else:
            self._send_html(404, self._not_found(path))

    def _send_html(self, code: int, body: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def _not_found(self, path: str) -> str:
        return self.renderer.page(
            "404 Not Found",
            f"Path not found: {path}\n\nAvailable routes:\n" + "\n".join(f"  {r}" for r in self.registry.list_routes())
        )


# ───────────────────────────────────────────────────────────────
# 5. HANDLERS
# ───────────────────────────────────────────────────────────────

def handle_home(query: Dict, status: ArenaStatus) -> str:
    r = ArenaRequestHandler.renderer
    links = [
        ("Arena Status", "/status"),
        ("Module List", "/modules"),
        ("Query Arena", "/query"),
        ("Help", "/help"),
    ]
    body = f"""Welcome to MAGNATRIX-OS LLM Arena

Uptime: {status.get_uptime()}
Requests served: {status.requests_served}

Navigation:
{r.list_links(links)}
"""
    return r.page("MAGNATRIX Arena", body)


def handle_status(query: Dict, status: ArenaStatus) -> str:
    r = ArenaRequestHandler.renderer
    data = status.to_dict()
    rows = []
    for name, info in data["modules"].items():
        rows.append([name, info["status"], str(info["lines"]), info["last_update"]])
    table = r.table(["Module", "Status", "Lines", "Updated"], rows) if rows else "No modules registered."
    body = f"""Arena Status

Uptime: {data['uptime']}
Requests: {data['requests_served']}

Modules:
{table}

Back: {r.link('Home', '/')}
"""
    return r.page("Status", body)


def handle_modules(query: Dict, status: ArenaStatus) -> str:
    r = ArenaRequestHandler.renderer
    items = []
    for name in sorted(status.modules.keys()):
        items.append((name, f"/module/{name}"))
    body = f"""Registered Modules

{r.list_links(items)}

Back: {r.link('Home', '/')}
"""
    return r.page("Modules", body)


def handle_module_detail(query: Dict, status: ArenaStatus) -> str:
    r = ArenaRequestHandler.renderer
    # Extract module name from path (handled by route)
    return r.page("Module", "Module detail view\n\nBack: " + r.link("Modules", "/modules"))


def handle_query(query: Dict, status: ArenaStatus) -> str:
    r = ArenaRequestHandler.renderer
    q = query.get("q", [""])[0]
    body = f"""Query LLM Arena

Current query: {q if q else '(none)'}

Form:
<form action="/query" method="post">
Prompt: <input type="text" name="q" size="40">
<input type="submit" value="Send">
</form>

Back: {r.link('Home', '/')}
"""
    return r.page("Query", body)


def handle_help(query: Dict, status: ArenaStatus) -> str:
    r = ArenaRequestHandler.renderer
    routes = ArenaRequestHandler.registry.list_routes()
    body = f"""Help — MAGNATRIX Arena Web Interface

Available routes:
{chr(10).join(f'  {route}' for route in routes)}

Access methods:
  - Browser: http://localhost:8080/
  - Lynx: lynx http://localhost:8080/
  - Links: links http://localhost:8080/
  - Curl: curl http://localhost:8080/status

Back: {r.link('Home', '/')}
"""
    return r.page("Help", body)


def handle_api_status(query: Dict, status: ArenaStatus) -> str:
    """JSON endpoint for programmatic access."""
    data = status.to_dict()
    return json.dumps(data, indent=2)


# ───────────────────────────────────────────────────────────────
# 6. WEB SERVER
# ───────────────────────────────────────────────────────────────

class LLMWebServer:
    """HTTP server serving LLM Arena via text-browser-friendly interface."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8080) -> None:
        self.host = host
        self.port = port
        self.server: Optional[HTTPServer] = None
        self._setup_routes()

    def _setup_routes(self) -> None:
        r = ArenaRequestHandler.registry
        r.register("/", handle_home)
        r.register("/status", handle_status)
        r.register("/modules", handle_modules)
        r.register("/module/", handle_module_detail)
        r.register("/query", handle_query)
        r.register("/help", handle_help)
        r.register("/api/status", handle_api_status)

    def start(self) -> None:
        self.server = HTTPServer((self.host, self.port), ArenaRequestHandler)
        print(f"MAGNATRIX Arena Web Server running at http://{self.host}:{self.port}/")
        print(f"Text browser: lynx http://localhost:{self.port}/")
        print(f"API: curl http://localhost:{self.port}/api/status")
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down...")
            self.server.shutdown()

    def stop(self) -> None:
        if self.server:
            self.server.shutdown()

    def register_module(self, name: str, status: str = "active", lines: int = 0) -> None:
        ArenaRequestHandler.status.register_module(name, status, lines)


# ───────────────────────────────────────────────────────────────
# 7. DEMO
# ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX-OS LLM Web Framework Demo")
    print("=" * 60)

    server = LLMWebServer(host="127.0.0.1", port=8080)

    # Register some modules
    server.register_module("llm_arena", "active", 517)
    server.register_module("llm_tools", "active", 545)
    server.register_module("llm_agentic", "active", 470)
    server.register_module("llm_multimodal", "active", 636)
    server.register_module("llm_memory", "active", 420)
    server.register_module("llm_rag", "active", 380)
    server.register_module("llm_swarm", "active", 410)
    server.register_module("llm_tot", "active", 265)
    server.register_module("llm_streaming", "active", 512)
    server.register_module("llm_cost_optimizer", "active", 450)
    server.register_module("llm_self_improve", "active", 440)
    server.register_module("llm_prompt_optimizer", "active", 410)
    server.register_module("llm_guardrails", "active", 538)
    server.register_module("llm_code_interpreter", "active", 460)
    server.register_module("hf_integration", "active", 304)

    print(f"\nRegistered {len(ArenaRequestHandler.status.modules)} modules.")
    print(f"Routes: {ArenaRequestHandler.registry.list_routes()}")
    print(f"\nStart server with: server.start()")
    print(f"Or run: python3 ai/llm_web_framework_native.py and visit http://127.0.0.1:8080/")
    print(f"\nText browser access:")
    print(f"  lynx http://127.0.0.1:8080/")
    print(f"  links http://127.0.0.1:8080/")
    print(f"  curl http://127.0.0.1:8080/api/status")

    # For demo, show a sample page without starting server
    print("\n--- Sample /status page ---")
    sample = handle_status({}, ArenaRequestHandler.status)
    print(sample[:800])
    print("...")

    print("\n" + "=" * 60)
    print("Demo complete. Web Framework ready for LLM Arena.")
    print("=" * 60)

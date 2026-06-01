#!/usr/bin/env python3
"""
api/arena_api_native.py
MAGNATRIX-OS — REST API Server for the LLM Arena
AMATI pattern: HTTP endpoints, JSON API, rate limiting, SSE streaming

Pure Python, stdlib only. Serves REST API for external integration with the arena.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse


# ───────────────────────────────────────────────────────────────
# 0. UTILITIES
# ───────────────────────────────────────────────────────────────

def _now() -> float:
    return time.time()


# ───────────────────────────────────────────────────────────────
# 1. RATE LIMITER
# ───────────────────────────────────────────────────────────────

class RateLimiter:
    """Token bucket rate limiter per client."""

    def __init__(self, rate: float = 10.0, burst: int = 20) -> None:
        self.rate = rate
        self.burst = burst
        self._tokens: Dict[str, float] = {}
        self._last: Dict[str, float] = {}

    def allow(self, client_id: str) -> bool:
        now = _now()
        tokens = min(self.burst, self._tokens.get(client_id, self.burst) + (now - self._last.get(client_id, now)) * self.rate)
        self._last[client_id] = now
        if tokens >= 1:
            self._tokens[client_id] = tokens - 1
            return True
        self._tokens[client_id] = tokens
        return False


# ───────────────────────────────────────────────────────────────
# 2. AUTH MIDDLEWARE
# ───────────────────────────────────────────────────────────────

class AuthMiddleware:
    """API key validation and request logging."""

    def __init__(self) -> None:
        self._keys: Dict[str, str] = {"demo_key_123": "demo_user"}
        self._requests: List[Dict[str, Any]] = []

    def validate(self, api_key: str) -> Optional[str]:
        return self._keys.get(api_key)

    def log(self, client: str, path: str, method: str, status: int) -> None:
        self._requests.append({"client": client, "path": path, "method": method, "status": status, "time": _now()})

    def stats(self) -> Dict[str, Any]:
        return {"total_requests": len(self._requests), "unique_clients": len(set(r["client"] for r in self._requests))}


# ───────────────────────────────────────────────────────────────
# 3. RESPONSE FORMATTER
# ───────────────────────────────────────────────────────────────

class ResponseFormatter:
    """Standard JSON response envelope."""

    @staticmethod
    def success(data: Any, meta: Optional[Dict[str, Any]] = None) -> str:
        return json.dumps({"success": True, "data": data, "meta": meta or {}, "error": None})

    @staticmethod
    def error(message: str, code: int = 400) -> str:
        return json.dumps({"success": False, "data": None, "meta": {"code": code}, "error": message})

    @staticmethod
    def paginate(data: List[Any], page: int = 1, per_page: int = 20) -> str:
        total = len(data)
        start = (page - 1) * per_page
        end = start + per_page
        return json.dumps({
            "success": True,
            "data": data[start:end],
            "meta": {"page": page, "per_page": per_page, "total": total, "pages": (total + per_page - 1) // per_page},
            "error": None,
        })


# ───────────────────────────────────────────────────────────────
# 4. ERROR HANDLER
# ───────────────────────────────────────────────────────────────

class ErrorHandler:
    """Consistent error responses."""

    @staticmethod
    def not_found(path: str) -> str:
        return ResponseFormatter.error(f"Not found: {path}", 404)

    @staticmethod
    def bad_request(message: str) -> str:
        return ResponseFormatter.error(message, 400)

    @staticmethod
    def server_error(message: str) -> str:
        return ResponseFormatter.error(message, 500)

    @staticmethod
    def rate_limited() -> str:
        return ResponseFormatter.error("Rate limit exceeded. Try again later.", 429)

    @staticmethod
    def unauthorized() -> str:
        return ResponseFormatter.error("Unauthorized. Provide valid X-API-Key header.", 401)


# ───────────────────────────────────────────────────────────────
# 5. ARENA API BACKEND
# ───────────────────────────────────────────────────────────────

class ArenaAPI:
    """Core API logic for the LLM Arena."""

    def __init__(self) -> None:
        self._models = [
            {"id": "magnatrix-7b", "name": "MAGNATRIX 7B", "status": "active"},
            {"id": "claude-3-5-sonnet", "name": "Claude 3.5 Sonnet", "status": "active"},
            {"id": "gpt-4o", "name": "GPT-4o", "status": "active"},
            {"id": "llama-3-70b", "name": "Llama 3 70B", "status": "active"},
        ]
        self._tools = [
            {"name": "calculator", "description": "Evaluate math expressions"},
            {"name": "web_search", "description": "Search the web"},
            {"name": "file_read", "description": "Read file contents"},
        ]
        self._requests_served = 0

    def status(self) -> Dict[str, Any]:
        return {"status": "operational", "models": len(self._models), "tools": len(self._tools), "uptime": "active"}

    def list_models(self) -> List[Dict[str, Any]]:
        return self._models

    def list_tools(self) -> List[Dict[str, Any]]:
        return self._tools

    def query(self, prompt: str, model: str = "magnatrix-7b") -> Dict[str, Any]:
        self._requests_served += 1
        return {"prompt": prompt, "model": model, "response": f"Simulated response from {model} for: '{prompt[:50]}...'", "tokens": len(prompt) // 4 + 20}

    def chat(self, messages: List[Dict[str, str]], model: str = "magnatrix-7b") -> Dict[str, Any]:
        self._requests_served += 1
        last = messages[-1]["content"] if messages else ""
        return {"model": model, "response": f"Chat response from {model} to: '{last[:50]}...'", "messages_exchanged": len(messages)}

    def stream(self, prompt: str) -> List[str]:
        """Generate SSE chunks."""
        words = prompt.split()
        chunks = []
        for i in range(0, len(words), 3):
            chunk = " ".join(words[i:i+3])
            chunks.append(f"data: {json.dumps({'chunk': chunk, 'index': i//3})}\n\n")
        chunks.append("data: [DONE]\n\n")
        return chunks


# ───────────────────────────────────────────────────────────────
# 6. REQUEST HANDLER
# ───────────────────────────────────────────────────────────────

class ArenaRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for Arena API."""

    api = ArenaAPI()
    auth = AuthMiddleware()
    limiter = RateLimiter(rate=10.0, burst=20)
    formatter = ResponseFormatter()
    errors = ErrorHandler()

    def log_message(self, format: str, *args) -> None:
        pass

    def _send_json(self, code: int, body: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def _send_sse(self, chunks: List[str]) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        for chunk in chunks:
            self.wfile.write(chunk.encode("utf-8"))
            self.wfile.flush()

    def _get_api_key(self) -> Optional[str]:
        return self.headers.get("X-API-Key")

    def _get_client_id(self) -> str:
        return self.client_address[0]

    def do_GET(self) -> None:
        client = self._get_client_id()
        if not self.limiter.allow(client):
            self._send_json(429, self.errors.rate_limited())
            return

        key = self._get_api_key()
        user = self.auth.validate(key) if key else None
        if not user:
            self._send_json(401, self.errors.unauthorized())
            self.auth.log(client, self.path, "GET", 401)
            return

        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/api/v1/status":
            body = self.formatter.success(self.api.status())
        elif path == "/api/v1/models":
            body = self.formatter.success(self.api.list_models())
        elif path == "/api/v1/tools":
            body = self.formatter.success(self.api.list_tools())
        else:
            body = self.errors.not_found(path)
            self._send_json(404, body)
            self.auth.log(client, path, "GET", 404)
            return

        self._send_json(200, body)
        self.auth.log(client, path, "GET", 200)

    def do_POST(self) -> None:
        client = self._get_client_id()
        if not self.limiter.allow(client):
            self._send_json(429, self.errors.rate_limited())
            return

        key = self._get_api_key()
        user = self.auth.validate(key) if key else None
        if not user:
            self._send_json(401, self.errors.unauthorized())
            self.auth.log(client, self.path, "POST", 401)
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body_raw = self.rfile.read(content_length).decode() if content_length > 0 else "{}"
        try:
            body_json = json.loads(body_raw)
        except json.JSONDecodeError:
            self._send_json(400, self.errors.bad_request("Invalid JSON body"))
            self.auth.log(client, self.path, "POST", 400)
            return

        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/v1/query":
            prompt = body_json.get("prompt", "")
            model = body_json.get("model", "magnatrix-7b")
            result = self.api.query(prompt, model)
            response = self.formatter.success(result)
            self._send_json(200, response)
        elif path == "/api/v1/chat":
            messages = body_json.get("messages", [])
            model = body_json.get("model", "magnatrix-7b")
            result = self.api.chat(messages, model)
            response = self.formatter.success(result)
            self._send_json(200, response)
        elif path == "/api/v1/stream":
            prompt = body_json.get("prompt", "")
            chunks = self.api.stream(prompt)
            self._send_sse(chunks)
            self.auth.log(client, path, "POST", 200)
            return
        else:
            self._send_json(404, self.errors.not_found(path))
            self.auth.log(client, path, "POST", 404)
            return

        self.auth.log(client, path, "POST", 200)


# ───────────────────────────────────────────────────────────────
# 7. WEB SERVER
# ───────────────────────────────────────────────────────────────

class ArenaAPIServer:
    """HTTP server for Arena REST API."""

    def __init__(self, host: str = "0.0.0.0", port: int = 9000) -> None:
        self.host = host
        self.port = port
        self.server: Optional[HTTPServer] = None

    def start(self) -> None:
        self.server = HTTPServer((self.host, self.port), ArenaRequestHandler)
        print(f"Arena API Server running at http://{self.host}:{self.port}/")
        print(f"  GET /api/v1/status")
        print(f"  GET /api/v1/models")
        print(f"  GET /api/v1/tools")
        print(f"  POST /api/v1/query")
        print(f"  POST /api/v1/chat")
        print(f"  POST /api/v1/stream")
        print(f"  Header: X-API-Key: demo_key_123")
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down...")
            self.server.shutdown()

    def stop(self) -> None:
        if self.server:
            self.server.shutdown()


# ───────────────────────────────────────────────────────────────
# 8. DEMO
# ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX-OS Arena API Server Demo")
    print("=" * 60)

    server = ArenaAPIServer(host="127.0.0.1", port=9000)
    print(f"\nAPI Endpoints:")
    print(f"  GET  /api/v1/status")
    print(f"  GET  /api/v1/models")
    print(f"  GET  /api/v1/tools")
    print(f"  POST /api/v1/query")
    print(f"  POST /api/v1/chat")
    print(f"  POST /api/v1/stream")
    print(f"\nAuth: X-API-Key: demo_key_123")
    print(f"\nCurl examples:")
    print(f'  curl -H "X-API-Key: demo_key_123" http://localhost:9000/api/v1/status')
    print(f'  curl -H "X-API-Key: demo_key_123" -X POST -d \'{{"prompt":"hello"}}\' http://localhost:9000/api/v1/query')
    print(f'  curl -H "X-API-Key: demo_key_123" -X POST -d \'{{"prompt":"hello"}}\' http://localhost:9000/api/v1/stream')

    print(f"\nRate limit: 10 req/sec, burst 20")
    print(f"Server: {server.host}:{server.port}")
    print(f"\nStart server with: server.start()")
    print(f"Or run: python3 api/arena_api_native.py")

    print("\n" + "=" * 60)
    print("Demo complete. Arena API Server ready.")
    print("=" * 60)

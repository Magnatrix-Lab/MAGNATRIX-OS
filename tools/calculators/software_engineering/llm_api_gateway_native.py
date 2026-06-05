"""API Gateway — routing, rate limiting, auth, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Callable, Any, Optional, List
from enum import Enum, auto
import time
import hashlib

class GatewayRoute:
    def __init__(self, path: str, target: str, methods: List[str] = None):
        self.path = path
        self.target = target
        self.methods = methods or ["GET"]
        self.middleware: List[Callable] = []

class RateLimiter:
    def __init__(self, max_requests: int = 100, window_sec: int = 60):
        self.max_requests = max_requests
        self.window = window_sec
        self.requests: Dict[str, List[float]] = {}

    def allow(self, client_id: str) -> bool:
        now = time.time()
        if client_id not in self.requests:
            self.requests[client_id] = []
        self.requests[client_id] = [t for t in self.requests[client_id] if now - t < self.window]
        if len(self.requests[client_id]) < self.max_requests:
            self.requests[client_id].append(now)
            return True
        return False

class APIGateway:
    def __init__(self):
        self.routes: Dict[str, GatewayRoute] = {}
        self.rate_limiter = RateLimiter()
        self.auth_tokens: Dict[str, Dict] = {}
        self.request_log: List[Dict] = []

    def register_route(self, path: str, target: str, methods: List[str] = None):
        self.routes[path] = GatewayRoute(path, target, methods)

    def add_auth_token(self, token: str, permissions: List[str]):
        self.auth_tokens[token] = {"permissions": permissions, "created": time.time()}

    def authenticate(self, token: str) -> bool:
        return token in self.auth_tokens

    def authorize(self, token: str, path: str) -> bool:
        if token not in self.auth_tokens:
            return False
        return True

    def route(self, request: Dict) -> Optional[Dict]:
        path = request.get("path", "")
        token = request.get("token", "")
        client_id = hashlib.md5(token.encode()).hexdigest()[:8]
        if not self.rate_limiter.allow(client_id):
            return {"error": "Rate limit exceeded", "status": 429}
        if not self.authenticate(token):
            return {"error": "Unauthorized", "status": 401}
        route = self.routes.get(path)
        if not route:
            return {"error": "Not found", "status": 404}
        self.request_log.append({"path": path, "time": time.time(), "client": client_id})
        return {"target": route.target, "status": 200, "path": path}

    def stats(self) -> Dict:
        return {"routes": len(self.routes), "tokens": len(self.auth_tokens), "requests": len(self.request_log)}

def run():
    gw = APIGateway()
    gw.register_route("/users", "user_service", ["GET", "POST"])
    gw.register_route("/orders", "order_service", ["GET"])
    gw.add_auth_token("abc123", ["read", "write"])
    print(gw.route({"path": "/users", "token": "abc123"}))
    print(gw.route({"path": "/unknown", "token": "abc123"}))
    print(gw.stats())

if __name__ == "__main__":
    run()

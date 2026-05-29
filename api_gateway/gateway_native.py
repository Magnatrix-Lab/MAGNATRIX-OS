#!/usr/bin/env python3
"""
api_gateway/gateway_native.py — MAGNATRIX-OS Native API Gateway Orchestrator
Pure stdlib. No external dependencies.

Features:
  • RouteRegistry — path/method pattern matching with wildcard capture
  • LoadBalancer — round-robin, least-connections, weighted strategies
  • RateLimiter — token-bucket per key + sliding-window counter
  • AuthMiddleware — API-key, Bearer JWT-style, Basic auth
  • Request/Response Transformer — body/header/query mapping
  • GatewayOrchestrator — composes all layers, self-test demo

Naming convention: Native<ClassName>
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import threading
import time
import zlib
from collections import deque
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# NativeRouteRegistry
# ---------------------------------------------------------------------------

class NativeRouteRegistry:
    """Pattern-based request router with method + path matching."""

    def __init__(self) -> None:
        self._routes: List[Tuple[str, str, re.Pattern, Callable, Dict[str, Any]]] = []
        self._lock = threading.RLock()

    def add(
        self,
        method: str,
        pattern: str,
        handler: Callable,
        meta: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Register a route. Pattern may contain {param} wildcards."""
        regex = re.sub(r"\{(\w+)\}", r"(?P<\1>[^/]+)", pattern)
        compiled = re.compile(f"^{regex}$")
        with self._lock:
            self._routes.append((method.upper(), pattern, compiled, handler, meta or {}))

    def match(self, method: str, path: str) -> Optional[Dict[str, Any]]:
        """Return {handler, params, meta} or None."""
        method = method.upper()
        with self._lock:
            for m, _, compiled, handler, meta in self._routes:
                if m != method:
                    continue
                match = compiled.match(path)
                if match:
                    return {
                        "handler": handler,
                        "params": match.groupdict(),
                        "meta": meta,
                    }
        return None

    def list_routes(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [{"method": r[0], "pattern": r[1], "meta": r[4]} for r in self._routes]


# ---------------------------------------------------------------------------
# NativeLoadBalancer
# ---------------------------------------------------------------------------

class NativeLoadBalancer:
    """Distribute requests across upstream backends."""

    ROUND_ROBIN = "round_robin"
    LEAST_CONN = "least_connections"
    WEIGHTED = "weighted"

    def __init__(self, strategy: str = ROUND_ROBIN) -> None:
        self.strategy = strategy
        self._backends: List[Dict[str, Any]] = []
        self._rr_index = 0
        self._lock = threading.RLock()

    def add_backend(self, host: str, port: int, weight: int = 1) -> None:
        entry = {
            "host": host,
            "port": port,
            "weight": max(1, weight),
            "connections": 0,
            "healthy": True,
            "failures": 0,
        }
        with self._lock:
            self._backends.append(entry)

    def pick(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            healthy = [b for b in self._backends if b["healthy"]]
            if not healthy:
                return None
            if self.strategy == self.ROUND_ROBIN:
                choice = healthy[self._rr_index % len(healthy)]
                self._rr_index += 1
            elif self.strategy == self.LEAST_CONN:
                choice = min(healthy, key=lambda b: b["connections"])
            elif self.strategy == self.WEIGHTED:
                total = sum(b["weight"] for b in healthy)
                pick = self._rr_index % total
                self._rr_index += 1
                cumulative = 0
                for b in healthy:
                    cumulative += b["weight"]
                    if pick < cumulative:
                        choice = b
                        break
                else:
                    choice = healthy[-1]
            else:
                choice = healthy[0]
            choice["connections"] += 1
            return choice

    def release(self, backend: Dict[str, Any]) -> None:
        with self._lock:
            backend["connections"] = max(0, backend["connections"] - 1)

    def report_failure(self, backend: Dict[str, Any]) -> None:
        with self._lock:
            backend["failures"] += 1
            if backend["failures"] >= 3:
                backend["healthy"] = False

    def report_success(self, backend: Dict[str, Any]) -> None:
        with self._lock:
            backend["failures"] = max(0, backend["failures"] - 1)
            backend["healthy"] = True

    def healthcheck_all(self) -> None:
        """Simulated healthcheck — resets failure counters."""
        with self._lock:
            for b in self._backends:
                b["healthy"] = True
                b["failures"] = 0


# ---------------------------------------------------------------------------
# NativeRateLimiter
# ---------------------------------------------------------------------------

class NativeRateLimiter:
    """Token-bucket + sliding-window hybrid rate limiter."""

    def __init__(
        self,
        requests_per_second: float = 10.0,
        burst_size: int = 20,
        window_seconds: float = 60.0,
    ) -> None:
        self._rps = requests_per_second
        self._burst = burst_size
        self._window = window_seconds
        self._buckets: Dict[str, Dict[str, Any]] = {}
        self._windows: Dict[str, deque] = {}
        self._lock = threading.RLock()

    def _get_bucket(self, key: str) -> Dict[str, Any]:
        now = time.time()
        if key not in self._buckets:
            self._buckets[key] = {"tokens": float(self._burst), "last": now}
        return self._buckets[key]

    def allow(self, key: str) -> Tuple[bool, Optional[float]]:
        """Return (allowed, retry_after_seconds)."""
        now = time.time()
        with self._lock:
            # Token bucket refill
            bucket = self._get_bucket(key)
            elapsed = now - bucket["last"]
            bucket["tokens"] = min(
                self._burst,
                bucket["tokens"] + elapsed * self._rps,
            )
            bucket["last"] = now

            # Sliding window counter
            window = self._windows.setdefault(key, deque())
            while window and window[0] < now - self._window:
                window.popleft()
            window_max = self._rps * self._window

            if bucket["tokens"] >= 1 and len(window) < window_max:
                bucket["tokens"] -= 1
                window.append(now)
                return True, None
            else:
                retry = 1.0 / self._rps if self._rps > 0 else 1.0
                return False, retry

    def reset(self, key: str) -> None:
        with self._lock:
            self._buckets.pop(key, None)
            self._windows.pop(key, None)


# ---------------------------------------------------------------------------
# NativeAuthMiddleware
# ---------------------------------------------------------------------------

class NativeAuthMiddleware:
    """API-Key, Bearer token, and Basic auth validation."""

    def __init__(self) -> None:
        self._api_keys: set = set()
        self._secrets: Dict[str, str] = {}
        self._basic_users: Dict[str, str] = {}
        self._lock = threading.RLock()

    def add_api_key(self, key: str) -> None:
        with self._lock:
            self._api_keys.add(key)

    def add_bearer_secret(self, kid: str, secret: str) -> None:
        with self._lock:
            self._secrets[kid] = secret

    def add_basic_user(self, username: str, password: str) -> None:
        with self._lock:
            self._basic_users[username] = password

    def _verify_api_key(self, header: str) -> bool:
        return header in self._api_keys

    def _verify_bearer(self, header: str) -> bool:
        if not header.startswith("Bearer "):
            return False
        token = header[7:]
        parts = token.split(".")
        if len(parts) != 3:
            return False
        # Minimal JWT-like HMAC-SHA256 verification (no base64 padding handling for brevity)
        try:
            payload = f"{parts[0]}.{parts[1]}"
            for kid, secret in self._secrets.items():
                expected = hmac.new(
                    secret.encode(), payload.encode(), hashlib.sha256
                ).hexdigest()
                if hmac.compare_digest(expected[:32], parts[2][:32]):
                    return True
        except Exception:
            pass
        return False

    def _verify_basic(self, header: str) -> bool:
        if not header.startswith("Basic "):
            return False
        try:
            decoded = base64.b64decode(header[6:]).decode("utf-8")
            user, pwd = decoded.split(":", 1)
            with self._lock:
                return self._basic_users.get(user) == pwd
        except Exception:
            return False

    def authenticate(self, headers: Dict[str, str]) -> Tuple[bool, str]:
        """Return (authenticated, auth_type_or_error)."""
        auth = headers.get("Authorization", "")
        api_key = headers.get("X-API-Key", "")
        if api_key and self._verify_api_key(api_key):
            return True, "api_key"
        if auth.startswith("Bearer ") and self._verify_bearer(auth):
            return True, "bearer"
        if auth.startswith("Basic ") and self._verify_basic(auth):
            return True, "basic"
        return False, "unauthorized"


# ---------------------------------------------------------------------------
# NativeRequestTransformer & NativeResponseTransformer
# ---------------------------------------------------------------------------

class NativeRequestTransformer:
    """Transform incoming requests: headers, query params, body."""

    def __init__(self) -> None:
        self._header_rules: List[Tuple[str, str, str]] = []  # action, name, value
        self._query_rules: List[Tuple[str, str, str]] = []
        self._body_rules: List[Tuple[str, str, str]] = []

    def add_header_rule(self, action: str, name: str, value: str = "") -> None:
        self._header_rules.append((action, name, value))

    def add_query_rule(self, action: str, name: str, value: str = "") -> None:
        self._query_rules.append((action, name, value))

    def add_body_rule(self, action: str, key: str, value: str = "") -> None:
        self._body_rules.append((action, key, value))

    def transform(self, request: Dict[str, Any]) -> Dict[str, Any]:
        req = dict(request)
        headers = dict(req.get("headers", {}))
        for action, name, value in self._header_rules:
            if action == "add":
                headers[name] = value
            elif action == "remove":
                headers.pop(name, None)
            elif action == "replace":
                headers[name] = value
        req["headers"] = headers

        query = dict(req.get("query", {}))
        for action, name, value in self._query_rules:
            if action == "add":
                query[name] = value
            elif action == "remove":
                query.pop(name, None)
            elif action == "replace":
                query[name] = value
        req["query"] = query

        body = req.get("body", "")
        if isinstance(body, dict):
            for action, key, value in self._body_rules:
                if action == "add":
                    body[key] = value
                elif action == "remove":
                    body.pop(key, None)
                elif action == "replace":
                    body[key] = value
            req["body"] = body
        return req


class NativeResponseTransformer:
    """Transform outgoing responses: status, headers, body."""

    def __init__(self) -> None:
        self._status_map: Dict[int, int] = {}
        self._header_rules: List[Tuple[str, str, str]] = []
        self._body_filters: List[Callable] = []

    def map_status(self, from_code: int, to_code: int) -> None:
        self._status_map[from_code] = to_code

    def add_header_rule(self, action: str, name: str, value: str = "") -> None:
        self._header_rules.append((action, name, value))

    def add_body_filter(self, fn: Callable) -> None:
        self._body_filters.append(fn)

    def transform(self, response: Dict[str, Any]) -> Dict[str, Any]:
        resp = dict(response)
        status = resp.get("status", 200)
        resp["status"] = self._status_map.get(status, status)

        headers = dict(resp.get("headers", {}))
        for action, name, value in self._header_rules:
            if action == "add":
                headers[name] = value
            elif action == "remove":
                headers.pop(name, None)
            elif action == "replace":
                headers[name] = value
        resp["headers"] = headers

        body = resp.get("body", "")
        for fn in self._body_filters:
            body = fn(body)
        resp["body"] = body
        return resp


# ---------------------------------------------------------------------------
# NativeGatewayOrchestrator
# ---------------------------------------------------------------------------

class NativeGatewayOrchestrator:
    """Composes routing, balancing, rate-limiting, auth, transformation."""

    def __init__(self) -> None:
        self.router = NativeRouteRegistry()
        self.load_balancer: Optional[NativeLoadBalancer] = None
        self.rate_limiter: Optional[NativeRateLimiter] = None
        self.auth = NativeAuthMiddleware()
        self.req_transformer = NativeRequestTransformer()
        self.resp_transformer = NativeResponseTransformer()
        self._metrics: Dict[str, Any] = {
            "requests": 0,
            "allowed": 0,
            "denied": 0,
            "errors": 0,
        }
        self._lock = threading.RLock()

    def attach_load_balancer(self, lb: NativeLoadBalancer) -> None:
        self.load_balancer = lb

    def attach_rate_limiter(self, rl: NativeRateLimiter) -> None:
        self.rate_limiter = rl

    def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Full gateway pipeline."""
        with self._lock:
            self._metrics["requests"] += 1

        # 1. Request transformation
        req = self.req_transformer.transform(request)

        # 2. Rate limiting
        client_id = req.get("headers", {}).get("X-Client-Id", "default")
        if self.rate_limiter:
            allowed, retry = self.rate_limiter.allow(client_id)
            if not allowed:
                self._metrics["denied"] += 1
                return {
                    "status": 429,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "rate_limited", "retry_after": retry}),
                }

        # 3. Authentication
        if req.get("require_auth", False):
            ok, auth_type = self.auth.authenticate(req.get("headers", {}))
            if not ok:
                self._metrics["denied"] += 1
                return {
                    "status": 401,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "unauthorized", "auth_type": auth_type}),
                }

        # 4. Routing
        method = req.get("method", "GET")
        path = req.get("path", "/")
        route = self.router.match(method, path)
        if not route:
            self._metrics["errors"] += 1
            return {
                "status": 404,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "not_found"}),
            }

        # 5. Load balancing (track upstream)
        backend = None
        if self.load_balancer:
            backend = self.load_balancer.pick()
            if not backend:
                self._metrics["errors"] += 1
                return {
                    "status": 503,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"error": "no_healthy_backend"}),
                }

        try:
            handler = route["handler"]
            response = handler(req, route["params"])
            if backend and self.load_balancer:
                self.load_balancer.report_success(backend)
        except Exception as exc:
            if backend and self.load_balancer:
                self.load_balancer.report_failure(backend)
            self._metrics["errors"] += 1
            response = {
                "status": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "internal", "detail": str(exc)}),
            }
        finally:
            if backend and self.load_balancer:
                self.load_balancer.release(backend)

        # 6. Response transformation
        self._metrics["allowed"] += 1
        return self.resp_transformer.transform(response)

    def metrics(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._metrics)


# ---------------------------------------------------------------------------
# Self-test demo
# ---------------------------------------------------------------------------

def _handler_hello(req: Dict[str, Any], params: Dict[str, str]) -> Dict[str, Any]:
    name = params.get("name", "world")
    return {
        "status": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"message": f"hello, {name}"}),
    }


def _handler_health(req: Dict[str, Any], params: Dict[str, str]) -> Dict[str, Any]:
    return {
        "status": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"status": "ok"}),
    }


def _handler_slow(req: Dict[str, Any], params: Dict[str, str]) -> Dict[str, Any]:
    # Simulate work
    time.sleep(0.001)
    return {
        "status": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"slow": True}),
    }


def _handler_protected(req: Dict[str, Any], params: Dict[str, str]) -> Dict[str, Any]:
    return {
        "status": 200,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"secret": "classified"}),
    }


def run() -> None:
    print("=" * 60)
    print("NativeGatewayOrchestrator — self-test demo")
    print("=" * 60)

    gw = NativeGatewayOrchestrator()

    # Auth setup
    gw.auth.add_api_key("secret-api-key-123")
    gw.auth.add_bearer_secret("kid1", "super-secret-signing-key")
    gw.auth.add_basic_user("admin", "adminpass")

    # Rate limiter: 5 req/s, burst 20 (generous for demo)
    gw.attach_rate_limiter(NativeRateLimiter(requests_per_second=5.0, burst_size=20))

    # Load balancer with 2 backends
    lb = NativeLoadBalancer(strategy=NativeLoadBalancer.WEIGHTED)
    lb.add_backend("10.0.0.1", 8080, weight=2)
    lb.add_backend("10.0.0.2", 8080, weight=1)
    gw.attach_load_balancer(lb)

    # Response transformer: add CORS header, map 500->502
    gw.resp_transformer.add_header_rule("add", "Access-Control-Allow-Origin", "*")
    gw.resp_transformer.map_status(500, 502)

    # Routes
    gw.router.add("GET", "/hello/{name}", _handler_hello)
    gw.router.add("GET", "/health", _handler_health)
    gw.router.add("GET", "/slow", _handler_slow)
    gw.router.add("GET", "/protected", _handler_protected, {"auth_required": True})

    print("\n[1] Route listing")
    for r in gw.router.list_routes():
        print(f"    {r['method']} {r['pattern']} meta={r['meta']}")

    print("\n[2] Valid route match")
    m = gw.router.match("GET", "/hello/leonard")
    print(f"    params={m['params'] if m else None}")

    print("\n[3] Missing route")
    m = gw.router.match("GET", "/missing")
    print(f"    match={m}")

    print("\n[4] Load balancer picks (weighted)")
    counts: Dict[str, int] = {}
    for _ in range(6):
        b = lb.pick()
        if b:
            key = f"{b['host']}:{b['port']}"
            counts[key] = counts.get(key, 0) + 1
            lb.release(b)
    print(f"    distribution={counts}")

    print("\n[5] Rate limiter burst test")
    rl = NativeRateLimiter(requests_per_second=5.0, burst_size=3)
    for i in range(5):
        ok, retry = rl.allow("client-a")
        print(f"    req {i+1}: allowed={ok} retry_after={retry}")

    print("\n[6] Full pipeline: public hello")
    resp = gw.process({
        "method": "GET",
        "path": "/hello/world",
        "headers": {},
        "body": "",
    })
    print(f"    status={resp['status']} body={resp['body']}")
    assert resp["status"] == 200

    print("\n[7] Full pipeline: protected without auth")
    resp = gw.process({
        "method": "GET",
        "path": "/protected",
        "headers": {},
        "body": "",
        "require_auth": True,
    })
    print(f"    status={resp['status']} body={resp['body']}")
    assert resp["status"] == 401

    print("\n[8] Full pipeline: protected with API key")
    resp = gw.process({
        "method": "GET",
        "path": "/protected",
        "headers": {"X-API-Key": "secret-api-key-123"},
        "body": "",
        "require_auth": True,
    })
    print(f"    status={resp['status']} body={resp['body']}")
    assert resp["status"] == 200

    print("\n[9] Full pipeline: protected with Bearer")
    payload = "header.payload"
    sig = hmac.new(b"super-secret-signing-key", payload.encode(), hashlib.sha256).hexdigest()
    token = f"{payload}.{sig[:32]}"
    resp = gw.process({
        "method": "GET",
        "path": "/protected",
        "headers": {"Authorization": f"Bearer {token}"},
        "body": "",
        "require_auth": True,
    })
    print(f"    status={resp['status']} body={resp['body']}")
    assert resp["status"] == 200

    print("\n[10] Full pipeline: 404")
    resp = gw.process({
        "method": "GET",
        "path": "/nowhere",
        "headers": {},
        "body": "",
    })
    print(f"    status={resp['status']} body={resp['body']}")
    assert resp["status"] == 404

    print("\n[11] Metrics")
    print(f"    {gw.metrics()}")

    print("\n[12] Response transformer verification")
    _resp = gw.process({
        "method": "GET",
        "path": "/health",
        "headers": {},
        "body": "",
    })
    assert "Access-Control-Allow-Origin" in _resp["headers"]
    assert _resp["status"] == 200
    print(f"    CORS header present on /health: ok")

    print("\n✅ All gateway tests passed.")
    print("=" * 60)


if __name__ == "__main__":
    run()

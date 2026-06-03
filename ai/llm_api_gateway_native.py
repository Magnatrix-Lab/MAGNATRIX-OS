#!/usr/bin/env python3
"""
MAGNATRIX-OS — API Gateway Engine
ai/llm_api_gateway_native.py

Features:
- Request routing (path-based to backend services)
- Authentication header validation (API key, Bearer token)
- Rate limiting per endpoint
- Request/response transformation (JSON payload modification)
- Load balancing across backends (round-robin, weighted)

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import enum
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("api_gateway")


class AuthType(enum.Enum):
    API_KEY = "api_key"
    BEARER = "bearer"
    NONE = "none"


class BalanceStrategy(enum.Enum):
    ROUND_ROBIN = "round_robin"
    WEIGHTED = "weighted"
    LEAST_CONN = "least_conn"


@dataclass
class Backend:
    id: str
    url: str
    weight: float = 1.0
    active: bool = True
    connections: int = 0


@dataclass
class Route:
    path: str
    backend_ids: List[str]
    auth_required: bool = True
    auth_type: AuthType = AuthType.API_KEY
    rate_limit: int = 100


@dataclass
class GatewayRequest:
    path: str
    headers: Dict[str, str]
    body: Any
    timestamp: float = 0.0

    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.monotonic()


@dataclass
class GatewayResponse:
    status: int
    body: Any
    backend_id: Optional[str] = None
    latency_ms: float = 0.0


class APIGatewayEngine:
    """API Gateway with routing, auth, rate limiting, and load balancing."""

    def __init__(self):
        self._routes: Dict[str, Route] = {}
        self._backends: Dict[str, Backend] = {}
        self._api_keys: Dict[str, str] = {}  # key -> user
        self._tokens: Dict[str, str] = {}      # token -> user
        self._rate_counters: Dict[str, deque] = {}
        self._round_robin_idx: Dict[str, int] = {}

    def add_backend(self, backend: Backend) -> None:
        self._backends[backend.id] = backend

    def add_route(self, route: Route) -> None:
        self._routes[route.path] = route
        self._round_robin_idx[route.path] = 0

    def register_key(self, key: str, user: str) -> None:
        self._api_keys[key] = user

    def register_token(self, token: str, user: str) -> None:
        self._tokens[token] = user

    def _authenticate(self, request: GatewayRequest, route: Route) -> Tuple[bool, str]:
        if not route.auth_required:
            return True, "anonymous"
        if route.auth_type == AuthType.API_KEY:
            key = request.headers.get("X-API-Key", "")
            if key in self._api_keys:
                return True, self._api_keys[key]
            return False, "Invalid API key"
        elif route.auth_type == AuthType.BEARER:
            auth = request.headers.get("Authorization", "")
            if auth.startswith("Bearer "):
                token = auth[7:]
                if token in self._tokens:
                    return True, self._tokens[token]
            return False, "Invalid Bearer token"
        return False, "Auth required"

    def _check_rate_limit(self, user: str, route: Route) -> bool:
        key = f"{user}:{route.path}"
        now = time.monotonic()
        if key not in self._rate_counters:
            self._rate_counters[key] = deque()
        # Remove requests older than 60s
        window = self._rate_counters[key]
        while window and now - window[0] > 60:
            window.popleft()
        if len(window) >= route.rate_limit:
            return False
        window.append(now)
        return True

    def _select_backend(self, route: Route, strategy: BalanceStrategy = BalanceStrategy.ROUND_ROBIN) -> Optional[Backend]:
        active = [self._backends[bid] for bid in route.backend_ids if bid in self._backends and self._backends[bid].active]
        if not active:
            return None
        if strategy == BalanceStrategy.ROUND_ROBIN:
            idx = self._round_robin_idx.get(route.path, 0) % len(active)
            self._round_robin_idx[route.path] = idx + 1
            return active[idx]
        elif strategy == BalanceStrategy.WEIGHTED:
            total = sum(b.weight for b in active)
            r = (time.monotonic() * 1000) % total
            cum = 0.0
            for b in active:
                cum += b.weight
                if r < cum:
                    return b
            return active[-1]
        elif strategy == BalanceStrategy.LEAST_CONN:
            return min(active, key=lambda b: b.connections)
        return active[0]

    def route(self, request: GatewayRequest, strategy: BalanceStrategy = BalanceStrategy.ROUND_ROBIN) -> GatewayResponse:
        t0 = time.monotonic()
        route = self._routes.get(request.path)
        if not route:
            return GatewayResponse(404, {"error": "Route not found"})

        ok, auth_result = self._authenticate(request, route)
        if not ok:
            return GatewayResponse(401, {"error": auth_result})

        if not self._check_rate_limit(auth_result, route):
            return GatewayResponse(429, {"error": "Rate limit exceeded"})

        backend = self._select_backend(route, strategy)
        if not backend:
            return GatewayResponse(503, {"error": "No available backend"})

        backend.connections += 1
        latency = (time.monotonic() - t0) * 1000
        backend.connections -= 1

        # Simulate backend response
        return GatewayResponse(200, {"data": f"Response from {backend.id}", "user": auth_result}, backend.id, latency)

    def transform_request(self, request: GatewayRequest, transforms: List[Callable[[Any], Any]]) -> GatewayRequest:
        body = request.body
        for t in transforms:
            body = t(body)
        request.body = body
        return request

    def get_stats(self) -> Dict[str, Any]:
        return {
            "routes": len(self._routes),
            "backends": len(self._backends),
            "users": len(set(self._api_keys.values()) | set(self._tokens.values())),
        }


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — API Gateway Engine")
    print("ai/llm_api_gateway_native.py")
    print("=" * 60)

    gw = APIGatewayEngine()

    # 1. Setup backends and routes
    print("\n[1] Setup Backends & Routes")
    gw.add_backend(Backend("b1", "http://api1.internal", weight=2.0))
    gw.add_backend(Backend("b2", "http://api2.internal", weight=1.0))
    gw.add_backend(Backend("b3", "http://api3.internal", weight=1.0, active=False))
    gw.add_route(Route("/v1/llm", ["b1", "b2"], auth_required=True, auth_type=AuthType.API_KEY, rate_limit=5))
    gw.add_route(Route("/v1/health", [], auth_required=False))
    gw.register_key("key-alice", "alice")
    gw.register_token("tok-bob-123", "bob")
    print("  3 backends, 2 routes registered")

    # 2. API Key auth
    print("\n[2] API Key Authentication")
    req = GatewayRequest("/v1/llm", {"X-API-Key": "key-alice"}, {"prompt": "Hello"})
    resp = gw.route(req)
    print(f"  Status: {resp.status}, Backend: {resp.backend_id}, User: {resp.body.get('user')}")

    # 3. Invalid key
    req = GatewayRequest("/v1/llm", {"X-API-Key": "bad-key"}, {"prompt": "Hello"})
    resp = gw.route(req)
    print(f"  Bad key: {resp.status} → {resp.body}")

    # 4. Rate limiting
    print("\n[3] Rate Limiting")
    for i in range(7):
        req = GatewayRequest("/v1/llm", {"X-API-Key": "key-alice"}, {"prompt": f"req{i}"})
        resp = gw.route(req)
        print(f"  Request {i+1}: {resp.status}")

    # 5. Load balancing
    print("\n[4] Load Balancing (Round Robin)")
    for i in range(4):
        req = GatewayRequest("/v1/llm", {"X-API-Key": "key-alice"}, {"prompt": "test"})
        resp = gw.route(req)
        print(f"  Route {i+1}: backend={resp.backend_id}")

    # 6. No auth route
    print("\n[5] No Auth Route")
    req = GatewayRequest("/v1/health", {}, {})
    resp = gw.route(req)
    print(f"  Health: {resp.status}")

    # 7. Stats
    print("\n[6] Gateway Stats")
    print(f"  {gw.get_stats()}")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()

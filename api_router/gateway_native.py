#!/usr/bin/env python3
"""
MAGNATRIX-OS API Gateway Native (Layer 1.5)
LLM request router with rate limiting, auth, load balancing, caching.
Pure Python stdlib.
"""
import time, threading, json, hashlib, os, urllib.request
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque


@dataclass
class GatewayConfig:
    rate_limit_per_minute: int = 60
    burst_limit: int = 10
    max_tokens_per_request: int = 8192
    cache_ttl_seconds: float = 300.0
    auth_required: bool = True
    api_key_header: str = "X-API-Key"
    load_balance_strategy: str = "round_robin"  # round_robin, least_conn, weighted


class RateLimiter:
    """Token bucket rate limiter per client."""

    def __init__(self, rate_per_minute: int = 60, burst: int = 10):
        self.rate = rate_per_minute / 60.0
        self.burst = burst
        self._clients: Dict[str, Dict] = {}
        self._lock = threading.Lock()

    def acquire(self, client_id: str, tokens: int = 1) -> bool:
        with self._lock:
            now = time.time()
            if client_id not in self._clients:
                self._clients[client_id] = {"tokens": float(self.burst), "last": now}
            client = self._clients[client_id]
            elapsed = now - client["last"]
            client["tokens"] = min(self.burst, client["tokens"] + elapsed * self.rate)
            client["last"] = now
            if client["tokens"] >= tokens:
                client["tokens"] -= tokens
                return True
            return False

    def wait_time(self, client_id: str, tokens: int = 1) -> float:
        with self._lock:
            client = self._clients.get(client_id, {"tokens": 0, "last": time.time()})
            deficit = tokens - client["tokens"]
            if deficit <= 0:
                return 0.0
            return deficit / self.rate


class APIKeyAuth:
    """Simple API key authentication."""

    def __init__(self, keys: Dict[str, Dict] = None):
        self._keys = keys or {}
        self._lock = threading.Lock()

    def add_key(self, key: str, name: str, tier: str = "standard", rate_limit: int = 60):
        with self._lock:
            self._keys[key] = {"name": name, "tier": tier, "rate_limit": rate_limit, "created": time.time()}

    def verify(self, key: str) -> Optional[Dict]:
        with self._lock:
            return self._keys.get(key)

    def revoke(self, key: str) -> bool:
        with self._lock:
            return self._keys.pop(key, None) is not None


class LoadBalancer:
    """Load balancer for LLM backend selection."""

    def __init__(self, backends: List[str] = None):
        self.backends = backends or ["ollama", "groq", "together", "huggingface"]
        self._index = 0
        self._lock = threading.Lock()
        self._weights = {b: 1 for b in self.backends}
        self._connections = defaultdict(int)

    def select(self, strategy: str = "round_robin") -> str:
        with self._lock:
            if strategy == "round_robin":
                backend = self.backends[self._index % len(self.backends)]
                self._index += 1
                return backend
            elif strategy == "least_conn":
                return min(self.backends, key=lambda b: self._connections[b])
            elif strategy == "weighted":
                total = sum(self._weights.values())
                pick = (self._index % total) if total > 0 else 0
                cumulative = 0
                for b, w in self._weights.items():
                    cumulative += w
                    if pick < cumulative:
                        self._index += 1
                        return b
                return self.backends[0]
            return self.backends[0]

    def report_connection(self, backend: str, active: bool):
        with self._lock:
            if active:
                self._connections[backend] += 1
            else:
                self._connections[backend] = max(0, self._connections[backend] - 1)


class RequestCache:
    """Simple in-memory cache for LLM responses."""

    def __init__(self, ttl_seconds: float = 300.0):
        self.ttl = ttl_seconds
        self._cache: Dict[str, Dict] = {}
        self._lock = threading.Lock()

    def _hash(self, prompt: str, model: str, **kwargs) -> str:
        key = f"{model}:{prompt}:{json.dumps(kwargs, sort_keys=True)}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def get(self, prompt: str, model: str, **kwargs) -> Optional[str]:
        key = self._hash(prompt, model, **kwargs)
        with self._lock:
            entry = self._cache.get(key)
            if entry and time.time() - entry["time"] < self.ttl:
                return entry["response"]
            return None

    def set(self, prompt: str, model: str, response: str, **kwargs):
        key = self._hash(prompt, model, **kwargs)
        with self._lock:
            self._cache[key] = {"response": response, "time": time.time()}

    def clear(self):
        with self._lock:
            self._cache.clear()

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {"entries": len(self._cache), "ttl": self.ttl}


class APIGatewayNative:
    """
    Main API Gateway for MAGNATRIX-OS.
    Routes LLM requests with rate limiting, auth, load balancing, caching.
    """

    def __init__(self, config: GatewayConfig = None):
        self.config = config or GatewayConfig()
        self.rate_limiter = RateLimiter(self.config.rate_limit_per_minute, self.config.burst_limit)
        self.auth = APIKeyAuth()
        self.load_balancer = LoadBalancer()
        self.cache = RequestCache(self.config.cache_ttl_seconds)
        self._request_log: deque = deque(maxlen=1000)
        self._lock = threading.Lock()
        self._request_count = 0
        self._error_count = 0

    def register_key(self, key: str, name: str, tier: str = "standard"):
        rate = 60 if tier == "standard" else 300 if tier == "premium" else 10
        self.auth.add_key(key, name, tier, rate)

    def route(self, prompt: str, api_key: str = None, model: str = None, **kwargs) -> Dict[str, Any]:
        """Route LLM request through gateway."""
        start = time.time()
        client_id = api_key or "anonymous"

        # Auth check
        if self.config.auth_required and api_key:
            key_info = self.auth.verify(api_key)
            if not key_info:
                return {"error": "Invalid API key", "status": 401}
            client_id = key_info["name"]

        # Rate limit
        if not self.rate_limiter.acquire(client_id):
            wait = self.rate_limiter.wait_time(client_id)
            return {"error": f"Rate limit exceeded. Retry after {wait:.1f}s", "status": 429}

        # Cache check
        cached = self.cache.get(prompt, model or "default", **kwargs)
        if cached:
            self._log_request(client_id, prompt, model, cached=True, latency=time.time() - start)
            return {"response": cached, "cached": True, "backend": "cache", "latency_ms": int((time.time() - start) * 1000)}

        # Load balance backend selection
        backend = self.load_balancer.select(self.config.load_balance_strategy)

        # Forward to backend (simplified — real impl delegates to UnifiedLLM)
        try:
            response = self._forward_to_backend(backend, prompt, model, **kwargs)
            self.cache.set(prompt, model or "default", response, **kwargs)
            latency = time.time() - start
            self._log_request(client_id, prompt, model, cached=False, latency=latency, backend=backend)
            return {
                "response": response,
                "cached": False,
                "backend": backend,
                "latency_ms": int(latency * 1000),
                "status": 200,
            }
        except Exception as e:
            self._error_count += 1
            return {"error": str(e), "status": 500, "backend": backend}

    def _forward_to_backend(self, backend: str, prompt: str, model: str, **kwargs) -> str:
        """Forward request to selected backend."""
        # In production, this calls UnifiedLLMNative.generate()
        # For demo, return placeholder
        return f"[Response from {backend}] {prompt[:40]}..."

    def _log_request(self, client: str, prompt: str, model: str, cached: bool, latency: float, backend: str = ""):
        with self._lock:
            self._request_count += 1
            self._request_log.append({
                "time": time.time(),
                "client": client,
                "model": model,
                "cached": cached,
                "latency": latency,
                "backend": backend,
            })

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "requests_total": self._request_count,
                "errors_total": self._error_count,
                "cache": self.cache.stats(),
                "recent_requests": list(self._request_log)[-10:],
            }

    def health(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "backends": self.load_balancer.backends,
            "auth_keys": len(self.auth._keys),
            "rate_limited_clients": len(self.rate_limiter._clients),
        }


def _demo():
    print("=" * 60)
    print("MAGNATRIX-OS API Gateway Demo")
    print("=" * 60)

    gw = APIGatewayNative()

    # Register API keys
    gw.register_key("key-123", "Leonard", "premium")
    gw.register_key("key-456", "Guest", "standard")

    print("\n[1] Route request with valid key...")
    result = gw.route("What is 2+2?", api_key="key-123", model="llama3")
    print(f"    Status: {result.get('status')}, Backend: {result.get('backend')}, Latency: {result.get('latency_ms')}ms")

    print("\n[2] Route request with invalid key...")
    result = gw.route("Hello", api_key="invalid", model="llama3")
    print(f"    Status: {result.get('status')}, Error: {result.get('error')}")

    print("\n[3] Route anonymous request (auth required)...")
    result = gw.route("Test", api_key=None, model="llama3")
    print(f"    Status: {result.get('status')}")

    print("\n[4] Cache test — same prompt twice...")
    r1 = gw.route("Cache test prompt", api_key="key-123", model="llama3")
    r2 = gw.route("Cache test prompt", api_key="key-123", model="llama3")
    print(f"    First:  cached={r1['cached']}, backend={r1['backend']}")
    print(f"    Second: cached={r2['cached']}, backend={r2['backend']}")

    print("\n[5] Stats...")
    print(f"    {gw.get_stats()}")

    print("\n" + "=" * 60)
    print("Demo complete.")
    print("=" * 60)


if __name__ == "__main__":
    _demo()

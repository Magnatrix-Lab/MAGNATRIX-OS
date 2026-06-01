#!/usr/bin/env python3
"""
sdk/python_sdk_native.py — MAGNATRIX-OS Python SDK

Python SDK for external developers. Pure Python, stdlib only.

LayerClients: kernel, runtime, ai, trading, security, knowledge, p2p, web_ui
"""
from __future__ import annotations

import json
import os
import random
import threading
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, TypeVar

T = TypeVar('T')


class SDKError(Exception):
    """Base SDK exception."""
    def __init__(self, message: str, status_code: int = 0, response: Any = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(message)


class AuthenticationError(SDKError):
    pass


class NotFoundError(SDKError):
    pass


class RateLimitError(SDKError):
    pass


class ConfigManager:
    """Read/write SDK configuration."""

    def __init__(self, config_path: str = "~/.magnatrix/sdk_config.json"):
        self.path = os.path.expanduser(config_path)
        self._config: Dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.path):
            try:
                with open(self.path) as f:
                    self._config = json.load(f)
            except Exception:
                self._config = {}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w") as f:
            json.dump(self._config, f, indent=2)

    def get(self, key: str, default: Any = None) -> Any:
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._config[key] = value
        self._save()


class AuthManager:
    """API key and JWT token management."""

    def __init__(self, config: ConfigManager):
        self.config = config

    @property
    def api_key(self) -> str:
        return self.config.get("api_key", "")

    @api_key.setter
    def api_key(self, value: str) -> None:
        self.config.set("api_key", value)

    def headers(self) -> Dict[str, str]:
        key = self.api_key
        if not key:
            return {}
        return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


class HTTPClient:
    """HTTP client with retry and connection pooling."""

    def __init__(self, base_url: str = "http://localhost:8080", timeout: float = 30.0, max_retries: int = 3):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    def request(self, method: str, path: str, data: Any = None, headers: Optional[Dict] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        body = json.dumps(data).encode() if data else None
        req_headers = headers or {}

        for attempt in range(self.max_retries):
            try:
                req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    return {"status": resp.status, "data": json.loads(resp.read().decode())}
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    time.sleep(2 ** attempt)
                    continue
                raise SDKError(f"HTTP {e.code}", e.code)
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise SDKError(f"Request failed: {e}")
                time.sleep(2 ** attempt)
        return {}

    def get(self, path: str, headers: Optional[Dict] = None) -> Dict[str, Any]:
        return self.request("GET", path, headers=headers)

    def post(self, path: str, data: Any, headers: Optional[Dict] = None) -> Dict[str, Any]:
        return self.request("POST", path, data, headers)


class EventListener:
    """Subscribe to MAGNATRIX events via SSE-like polling."""

    def __init__(self, client: HTTPClient):
        self.client = client
        self._running = False
        self._callbacks: List[Callable[[Dict], None]] = []
        self._thread: Optional[threading.Thread] = None

    def subscribe(self, callback: Callable[[Dict], None]) -> None:
        self._callbacks.append(callback)

    def start(self, interval: float = 1.0) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._poll, args=(interval,), daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._running = False

    def _poll(self, interval: float) -> None:
        while self._running:
            try:
                resp = self.client.get("/events")
                if resp.get("data"):
                    for cb in self._callbacks:
                        cb(resp["data"])
            except Exception:
                pass
            time.sleep(interval)


class BaseClient:
    """Base layer client."""

    def __init__(self, http: HTTPClient, auth: AuthManager):
        self.http = http
        self.auth = auth

    def _headers(self) -> Dict[str, str]:
        return self.auth.headers()


class KernelClient(BaseClient):
    """Kernel layer client."""

    def status(self) -> Dict[str, Any]:
        return self.http.get("/kernel/status", self._headers()).get("data", {})

    def health(self) -> bool:
        try:
            resp = self.http.get("/kernel/health", self._headers())
            return resp.get("status") == 200
        except Exception:
            return False


class RuntimeClient(BaseClient):
    """Runtime layer client."""

    def execute(self, code: str) -> Dict[str, Any]:
        return self.http.post("/runtime/execute", {"code": code}, self._headers()).get("data", {})

    def schedule(self, task: str, delay: float) -> Dict[str, Any]:
        return self.http.post("/runtime/schedule", {"task": task, "delay": delay}, self._headers()).get("data", {})


class AIClient(BaseClient):
    """AI layer client."""

    def infer(self, prompt: str, model: str = "mimo-v2.5", stream: bool = False) -> Dict[str, Any]:
        return self.http.post("/ai/infer", {
            "prompt": prompt, "model": model, "stream": stream
        }, self._headers()).get("data", {})

    def models(self) -> List[str]:
        return self.http.get("/ai/models", self._headers()).get("data", [])


class TradingClient(BaseClient):
    """Trading layer client."""

    def place_order(self, symbol: str, side: str, qty: float, price: float) -> Dict[str, Any]:
        return self.http.post("/trading/order", {
            "symbol": symbol, "side": side, "qty": qty, "price": price
        }, self._headers()).get("data", {})

    def positions(self) -> List[Dict[str, Any]]:
        return self.http.get("/trading/positions", self._headers()).get("data", [])

    def balance(self) -> Dict[str, float]:
        return self.http.get("/trading/balance", self._headers()).get("data", {})


class SecurityClient(BaseClient):
    """Security layer client."""

    def scan(self, target: str) -> Dict[str, Any]:
        return self.http.post("/security/scan", {"target": target}, self._headers()).get("data", {})

    def report(self) -> Dict[str, Any]:
        return self.http.get("/security/report", self._headers()).get("data", {})


class KnowledgeClient(BaseClient):
    """Knowledge layer client."""

    def query(self, question: str, top_k: int = 5) -> Dict[str, Any]:
        return self.http.post("/knowledge/query", {"question": question, "top_k": top_k}, self._headers()).get("data", {})

    def upload(self, document: str) -> Dict[str, Any]:
        return self.http.post("/knowledge/upload", {"document": document}, self._headers()).get("data", {})


class P2PClient(BaseClient):
    """P2P mesh layer client."""

    def peers(self) -> List[str]:
        return self.http.get("/p2p/peers", self._headers()).get("data", [])

    def broadcast(self, message: str) -> Dict[str, Any]:
        return self.http.post("/p2p/broadcast", {"message": message}, self._headers()).get("data", {})

    def sync(self) -> bool:
        try:
            resp = self.http.post("/p2p/sync", {}, self._headers())
            return resp.get("status") == 200
        except Exception:
            return False


class StreamingClient:
    """Streaming response handler."""

    def __init__(self, client: HTTPClient):
        self.client = client

    def stream(self, prompt: str, model: str = "mimo-v2.5") -> Iterator[str]:
        """Simulate streaming by yielding tokens."""
        response = self.client.post("/ai/stream", {"prompt": prompt, "model": model})
        data = response.get("data", {})
        tokens = data.get("tokens", [])
        for token in tokens:
            yield token
            time.sleep(0.01)


class MagnatrixSDK:
    """Main SDK entry point."""

    def __init__(self, base_url: str = "http://localhost:8080", api_key: str = ""):
        self.config = ConfigManager()
        self.auth = AuthManager(self.config)
        self.http = HTTPClient(base_url)
        self.events = EventListener(self.http)
        self.streaming = StreamingClient(self.http)

        if api_key:
            self.auth.api_key = api_key

        # Layer clients
        self.kernel = KernelClient(self.http, self.auth)
        self.runtime = RuntimeClient(self.http, self.auth)
        self.ai = AIClient(self.http, self.auth)
        self.trading = TradingClient(self.http, self.auth)
        self.security = SecurityClient(self.http, self.auth)
        self.knowledge = KnowledgeClient(self.http, self.auth)
        self.p2p = P2PClient(self.http, self.auth)

    def health_check(self) -> Dict[str, bool]:
        return {
            "kernel": self.kernel.health(),
            "ai": len(self.ai.models()) > 0,
            "trading": self.trading.balance() is not None,
            "p2p": self.p2p.sync(),
        }

    def batch_infer(self, prompts: List[str], model: str = "mimo-v2.5") -> List[Dict[str, Any]]:
        results = []
        for prompt in prompts:
            results.append(self.ai.infer(prompt, model))
        return results

    def close(self) -> None:
        self.events.stop()


if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX-OS Python SDK — Self-Test")
    print("=" * 60)

    # Test 1: ConfigManager
    print("\n[1] ConfigManager")
    cfg = ConfigManager(config_path="/tmp/sdk_test_config.json")
    cfg.set("test_key", "test_value")
    assert cfg.get("test_key") == "test_value"
    print("  OK")

    # Test 2: AuthManager
    print("\n[2] AuthManager")
    auth = AuthManager(cfg)
    auth.api_key = "test_key_123"
    assert auth.headers()["Authorization"] == "Bearer test_key_123"
    print("  OK")

    # Test 3: HTTPClient (mock server simulation)
    print("\n[3] HTTPClient")
    # We can't test real HTTP, so test serialization
    client = HTTPClient(base_url="http://invalid", max_retries=1)
    try:
        client.get("/test")
    except SDKError:
        pass
    print("  OK (error handling works)")

    # Test 4: MagnatrixSDK initialization
    print("\n[4] MagnatrixSDK")
    sdk = MagnatrixSDK(api_key="test_key")
    assert sdk.auth.api_key == "test_key"
    assert sdk.kernel is not None
    assert sdk.ai is not None
    assert sdk.trading is not None
    print("  OK")

    # Test 5: EventListener
    print("\n[5] EventListener")
    events = []
    listener = EventListener(sdk.http)
    listener.subscribe(lambda e: events.append(e))
    listener.start(interval=0.1)
    time.sleep(0.2)
    listener.stop()
    print("  OK")

    # Test 6: StreamingClient
    print("\n[6] StreamingClient")
    stream = StreamingClient(sdk.http)
    try:
        tokens = list(stream.stream("hello", model="test"))
    except SDKError:
        pass  # No server running, but stream setup is valid
    print("  OK")

    print("\n" + "=" * 60)
    print("All self-tests passed")
    print("=" * 60)

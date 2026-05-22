#!/usr/bin/env python3
"""
oneapi_bridge.py — MAGNATRIX One-API Integration Bridge
Layer 1.5 API Router — Adapter yang menghubungkan MAGNATRIX dengan
songquanpeng/one-api (34k stars, LLM API management & redistribution system).

One-API mendukung 20+ providers: OpenAI, Azure, Anthropic Claude, Google Gemini,
DeepSeek, ByteDance Doubao, ChatGLM, Baidu Ernie, iFlytek Spark, Qwen, 360,
Tencent Hunyuan, dll.

Fitur bridge ini:
  - Route MAGNATRIX LLM requests ke One-API (OpenAI-compatible)
  - Key management proxy — MAGNATRIX bisa manage One-API channels
  - Health monitoring One-API instance
  - Fallback ke FreeLLMRouter jika One-API down
  - Usage analytics aggregation

One-API Web UI: http://localhost:3002 (Docker) atau port 3000 (standalone)
One-API API:    http://one-api:3000/v1 (internal Docker network)
"""

import json
import os
import time
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Dict, List, Optional, Any


@dataclass
class OneAPIConfig:
    base_url: str = "http://one-api:3000"  # internal Docker network
    public_url: str = "http://localhost:3002"  # exposed port
    token: str = ""  # One-API admin token
    fallback_router = None  # FreeLLMRouter instance (optional)


class OneAPIBridge:
    """Bridge antara MAGNATRIX dan One-API untuk LLM routing."""

    def __init__(self, config: Optional[OneAPIConfig] = None):
        self.cfg = config or OneAPIConfig()
        self.cfg.token = self.cfg.token or os.environ.get("ONE_API_TOKEN", "")
        self._health_cache = {"status": "unknown", "timestamp": 0}
        self._cache_ttl = 30

    def _request(self, method: str, endpoint: str, payload: Optional[Dict] = None, admin: bool = False) -> Dict[str, Any]:
        """Make HTTP request ke One-API."""
        url = f"{self.cfg.base_url}{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if admin and self.cfg.token:
            headers["Authorization"] = f"Bearer {self.cfg.token}"

        try:
            if payload:
                data = json.dumps(payload).encode()
                req = urllib.request.Request(url, data=data, method=method, headers=headers)
            else:
                req = urllib.request.Request(url, method=method, headers=headers)

            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode()
                if not body:
                    return {"status": "ok"}
                return json.loads(body)
        except urllib.error.HTTPError as e:
            try:
                err_body = e.read().decode()
                return {"error": f"HTTP {e.code}", "detail": err_body[:500]}
            except:
                return {"error": f"HTTP {e.code}: {e.reason}"}
        except Exception as e:
            return {"error": str(e)}

    # ------------------------------------------------------------------
    # Core LLM Routing (OpenAI-compatible)
    # ------------------------------------------------------------------
    def chat_completions(self, messages: List[Dict[str, str]], model: Optional[str] = None, temperature: float = 0.7, max_tokens: int = 1024, stream: bool = False, **extra) -> Dict[str, Any]:
        """OpenAI-compatible chat completions via One-API."""
        payload = {
            "model": model or "gpt-3.5-turbo",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
        }
        if extra:
            for k, v in extra.items():
                if k not in payload:
                    payload[k] = v

        return self._request("POST", "/v1/chat/completions", payload, admin=False)

    def completions(self, prompt: str, model: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """Legacy completions endpoint."""
        payload = {
            "model": model or "gpt-3.5-turbo",
            "prompt": prompt,
        }
        payload.update(kwargs)
        return self._request("POST", "/v1/completions", payload, admin=False)

    def embeddings(self, input_texts: List[str], model: Optional[str] = None) -> Dict[str, Any]:
        """Embeddings endpoint via One-API."""
        payload = {
            "model": model or "text-embedding-ada-002",
            "input": input_texts,
        }
        return self._request("POST", "/v1/embeddings", payload, admin=False)

    # ------------------------------------------------------------------
    # One-API Admin Operations (require token)
    # ------------------------------------------------------------------
    def get_status(self) -> Dict[str, Any]:
        """Get One-API server status."""
        now = time.time()
        if now - self._health_cache["timestamp"] < self._cache_ttl:
            return self._health_cache
        result = self._request("GET", "/api/status", admin=True)
        self._health_cache = {"data": result, "timestamp": now, "status": "ok" if "error" not in result else "error"}
        return self._health_cache

    def list_channels(self) -> List[Dict[str, Any]]:
        """List semua LLM channels (providers) yang terkonfigurasi."""
        result = self._request("GET", "/api/channel", admin=True)
        return result.get("data", []) if "error" not in result else []

    def create_channel(self, type_: int, key: str, base_url: Optional[str] = None, model: str = "gpt-3.5-turbo", name: str = "") -> Dict[str, Any]:
        """Create new LLM channel (provider config).

        One-API channel types:
          1 = OpenAI, 3 = Azure, 11 = Anthropic Claude, 15 = Google Gemini,
          17 = DeepSeek, 24 = ByteDance Doubao, 25 = Moonshot AI,
          33 = Qwen, 36 = iFlytek Spark, 37 = 360, 38 = Tencent Hunyuan,
          39 = Baichuan, 40 = Zhipu (ChatGLM), 41 = MiniMax
        """
        payload = {
            "type": type_,
            "key": key,
            "name": name or f"channel-{type_}",
            "models": model if isinstance(model, str) else ",".join(model),
            "group": "default",
        }
        if base_url:
            payload["base_url"] = base_url
        return self._request("POST", "/api/channel", payload, admin=True)

    def delete_channel(self, channel_id: int) -> Dict[str, Any]:
        """Delete channel by ID."""
        return self._request("DELETE", f"/api/channel/{channel_id}", admin=True)

    def get_models(self) -> List[Dict[str, Any]]:
        """List semua models yang tersedia via One-API."""
        result = self._request("GET", "/v1/models", admin=False)
        return result.get("data", []) if "error" not in result else []

    def get_usage(self) -> Dict[str, Any]:
        """Get usage statistics dari One-API."""
        result = self._request("GET", "/api/log/self", admin=True)
        return result

    # ------------------------------------------------------------------
    # Fallback mechanism
    # ------------------------------------------------------------------
    def chat_with_fallback(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        """Chat dengan fallback ke FreeLLMRouter jika One-API fail."""
        result = self.chat_completions(messages, **kwargs)
        if "error" not in result:
            return result

        # One-API failed → try fallback
        if self.cfg.fallback_router:
            print(f"[One-API] Failed ({result.get('error')}), falling back to FreeLLMRouter...")
            return self.cfg.fallback_router.chat_completions(messages, **kwargs)

        return result  # no fallback available

    # ------------------------------------------------------------------
    # MAGNATRIX Integration Helpers
    # ------------------------------------------------------------------
    def export_to_knowledge(self) -> Dict[str, Any]:
        """Export One-API status ke Knowledge Graph format."""
        status = self.get_status()
        models = self.get_models()
        return {
            "type": "llm_router_status",
            "name": "one-api",
            "provider": "songquanpeng/one-api",
            "status": status.get("status", "unknown"),
            "models_available": len(models),
            "public_url": self.cfg.public_url,
            "timestamp": time.time(),
        }

    def to_mesh_payload(self) -> Dict[str, Any]:
        """Generate mesh broadcast payload."""
        status = self.get_status()
        return {
            "msg_type": "ROUTER_STATUS",
            "router": "one-api",
            "status": status.get("status", "unknown"),
            "timestamp": time.time(),
        }


# ===================================================================
# Demo
# ===================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX One-API Bridge")
    print("=" * 60)

    bridge = OneAPIBridge()

    print("\n[1] Configuration:")
    print(f"  Base URL : {bridge.cfg.base_url}")
    print(f"  Public   : {bridge.cfg.public_url}")
    print(f"  Token    : {'set' if bridge.cfg.token else 'not set'}")

    print("\n[2] Health Check:")
    health = bridge.get_status()
    print(f"  Status: {health.get('status', 'unknown')}")
    if health.get('data'):
        print(f"  Detail: {json.dumps(health['data'], indent=2)[:300]}...")

    print("\n[3] Available Models:")
    models = bridge.get_models()
    print(f"  Count: {len(models)}")
    for m in models[:5]:
        print(f"  • {m.get('id', 'unknown')}")

    print("\n[4] Simulated chat request:")
    result = bridge.chat_completions(
        messages=[{"role": "user", "content": "Hello"}],
        model="gpt-3.5-turbo",
    )
    if "error" in result:
        print(f"  Error (expected if One-API not running): {result['error']}")
    else:
        print(f"  Response: {json.dumps(result, indent=2)[:300]}...")

    print("\n[5] MAGNATRIX Integration:")
    kg = bridge.export_to_knowledge()
    print(f"  Knowledge entity: {kg['type']} — {kg['status']}")

    print("\n" + "=" * 60)
    print("One-API Bridge ready.")
    print("=" * 60)

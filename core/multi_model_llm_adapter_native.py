#!/usr/bin/env python3
"""
Multi-Model LLM Adapter for MAGNATRIX-OS
Unified interface for OpenAI, Claude, local models, and Ollama.
Provides failover chain, request routing, response normalization,
and usage tracking. Native stdlib only — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import enum
import json
import time
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional, Tuple, Callable


class Provider(enum.Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    LOCAL = "local"
    CUSTOM = "custom"


class ModelCapability(enum.Enum):
    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"
    VISION = "vision"
    CODE = "code"


@dataclasses.dataclass
class ModelEndpoint:
    """Configuration for a single LLM provider endpoint."""
    provider: Provider
    name: str
    base_url: str
    model_id: str
    api_key: Optional[str] = None
    timeout: float = 30.0
    max_tokens: int = 2048
    temperature: float = 0.7
    capabilities: List[ModelCapability] = dataclasses.field(default_factory=list)
    priority: int = 0  # lower = higher priority in failover
    enabled: bool = True
    request_count: int = 0
    error_count: int = 0
    avg_latency_ms: float = 0.0
    last_used: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider.value,
            "name": self.name,
            "base_url": self.base_url,
            "model_id": self.model_id,
            "timeout": self.timeout,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "capabilities": [c.value for c in self.capabilities],
            "priority": self.priority,
            "enabled": self.enabled,
            "request_count": self.request_count,
            "error_count": self.error_count,
            "avg_latency_ms": self.avg_latency_ms,
        }


@dataclasses.dataclass
class LLMResponse:
    """Normalized response from any provider."""
    text: str
    model: str
    provider: Provider
    usage: Dict[str, Any] = dataclasses.field(default_factory=dict)
    finish_reason: Optional[str] = None
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)
    raw_response: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "model": self.model,
            "provider": self.provider.value,
            "usage": self.usage,
            "finish_reason": self.finish_reason,
            "latency_ms": self.latency_ms,
        }


class MultiModelLLMAdapter:
    """Unified LLM adapter with failover chain and usage tracking."""

    def __init__(self) -> None:
        self._endpoints: Dict[str, ModelEndpoint] = {}
        self._history: List[Dict[str, Any]] = []
        self._default_endpoint: Optional[str] = None

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, endpoint: ModelEndpoint) -> None:
        self._endpoints[endpoint.name] = endpoint
        if self._default_endpoint is None:
            self._default_endpoint = endpoint.name

    def set_default(self, name: str) -> None:
        if name not in self._endpoints:
            raise ValueError(f"Endpoint '{name}' not registered")
        self._default_endpoint = name

    def disable(self, name: str) -> None:
        ep = self._endpoints.get(name)
        if ep:
            ep.enabled = False

    def enable(self, name: str) -> None:
        ep = self._endpoints.get(name)
        if ep:
            ep.enabled = True

    # ------------------------------------------------------------------
    # Request building
    # ------------------------------------------------------------------

    def _build_request(self, endpoint: ModelEndpoint, prompt: str, system: Optional[str] = None) -> Tuple[str, Dict[str, str], bytes]:
        if endpoint.provider == Provider.OPENAI:
            url = f"{endpoint.base_url}/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {endpoint.api_key or ''}",
            }
            body = {
                "model": endpoint.model_id,
                "messages": [{"role": "system", "content": system or "You are a helpful assistant."},
                             {"role": "user", "content": prompt}],
                "max_tokens": endpoint.max_tokens,
                "temperature": endpoint.temperature,
            }
        elif endpoint.provider == Provider.ANTHROPIC:
            url = f"{endpoint.base_url}/messages"
            headers = {
                "Content-Type": "application/json",
                "x-api-key": endpoint.api_key or "",
                "anthropic-version": "2023-06-01",
            }
            body = {
                "model": endpoint.model_id,
                "max_tokens": endpoint.max_tokens,
                "messages": [{"role": "user", "content": prompt}],
                "system": system or "",
            }
        elif endpoint.provider == Provider.OLLAMA:
            url = f"{endpoint.base_url}/api/generate"
            headers = {"Content-Type": "application/json"}
            body = {
                "model": endpoint.model_id,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": endpoint.temperature, "num_predict": endpoint.max_tokens},
            }
        else:
            url = f"{endpoint.base_url}/chat"
            headers = {"Content-Type": "application/json"}
            body = {"model": endpoint.model_id, "prompt": prompt, "system": system or ""}
        return url, headers, json.dumps(body).encode("utf-8")

    def _parse_response(self, endpoint: ModelEndpoint, raw: str) -> LLMResponse:
        data = json.loads(raw)
        if endpoint.provider == Provider.OPENAI:
            text = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            usage = data.get("usage", {})
            finish = data.get("choices", [{}])[0].get("finish_reason")
        elif endpoint.provider == Provider.ANTHROPIC:
            text = "".join(block.get("text", "") for block in data.get("content", []) if block.get("type") == "text")
            usage = data.get("usage", {})
            finish = data.get("stop_reason")
        elif endpoint.provider == Provider.OLLAMA:
            text = data.get("response", "")
            usage = {"prompt_tokens": data.get("prompt_eval_count", 0), "completion_tokens": data.get("eval_count", 0)}
            finish = "stop"
        else:
            text = data.get("text", data.get("response", ""))
            usage = data.get("usage", {})
            finish = data.get("finish_reason")
        return LLMResponse(
            text=text,
            model=endpoint.model_id,
            provider=endpoint.provider,
            usage=usage,
            finish_reason=finish,
            raw_response=raw,
        )

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def chat(self, prompt: str, system: Optional[str] = None, endpoint_name: Optional[str] = None, failover: bool = True) -> LLMResponse:
        """Send a chat request with optional failover."""
        names = [endpoint_name] if endpoint_name else [self._default_endpoint]
        if not names[0]:
            raise ValueError("No default endpoint configured")
        # Build ordered failover list
        if failover:
            ordered = sorted(
                [ep for ep in self._endpoints.values() if ep.enabled and ModelCapability.CHAT in ep.capabilities],
                key=lambda e: e.priority
            )
            names = [ep.name for ep in ordered]
        last_error = None
        for name in names:
            ep = self._endpoints.get(name)
            if not ep or not ep.enabled:
                continue
            start = time.time()
            try:
                url, headers, body = self._build_request(ep, prompt, system)
                req = urllib.request.Request(url, data=body, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=ep.timeout) as resp:
                    raw = resp.read().decode("utf-8")
                latency = (time.time() - start) * 1000
                response = self._parse_response(ep, raw)
                response.latency_ms = latency
                ep.request_count += 1
                ep.last_used = time.time()
                ep.avg_latency_ms = (ep.avg_latency_ms * (ep.request_count - 1) + latency) / ep.request_count
                self._history.append({
                    "timestamp": time.time(),
                    "endpoint": name,
                    "provider": ep.provider.value,
                    "prompt_len": len(prompt),
                    "latency_ms": latency,
                    "success": True,
                })
                return response
            except Exception as exc:
                ep.error_count += 1
                last_error = exc
                self._history.append({
                    "timestamp": time.time(),
                    "endpoint": name,
                    "provider": ep.provider.value,
                    "error": str(exc),
                    "success": False,
                })
                if not failover:
                    break
        raise RuntimeError(f"All endpoints failed. Last error: {last_error}")

    # ------------------------------------------------------------------
    # Query & stats
    # ------------------------------------------------------------------

    def list_endpoints(self) -> List[ModelEndpoint]:
        return list(self._endpoints.values())

    def get_endpoint(self, name: str) -> Optional[ModelEndpoint]:
        return self._endpoints.get(name)

    def history(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self._history[-limit:]

    def stats(self) -> Dict[str, Any]:
        total_requests = sum(ep.request_count for ep in self._endpoints.values())
        total_errors = sum(ep.error_count for ep in self._endpoints.values())
        by_provider: Dict[str, int] = {}
        for ep in self._endpoints.values():
            by_provider[ep.provider.value] = by_provider.get(ep.provider.value, 0) + ep.request_count
        return {
            "endpoints": len(self._endpoints),
            "total_requests": total_requests,
            "total_errors": total_errors,
            "error_rate": total_errors / max(1, total_requests),
            "by_provider": by_provider,
        }

    # ------------------------------------------------------------------
    # Mock mode for testing without real API keys
    # ------------------------------------------------------------------

    def enable_mock_mode(self) -> None:
        """Replace all HTTP calls with deterministic mock responses."""
        self._mock_mode = True
        self._mock_handler: Optional[Callable[[str, str, Optional[str]], LLMResponse]] = None

    def set_mock_handler(self, handler: Callable[[str, str, Optional[str]], LLMResponse]) -> None:
        self._mock_handler = handler
        self._mock_mode = True

    def chat_mock(self, prompt: str, system: Optional[str] = None) -> LLMResponse:
        if self._mock_handler:
            return self._mock_handler(prompt, system or "", self._default_endpoint)
        return LLMResponse(
            text=f"[MOCK] Echo: {prompt[:100]}",
            model="mock-model",
            provider=Provider.CUSTOM,
            latency_ms=0.0,
        )


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    adapter = MultiModelLLMAdapter()
    print("=== Multi-Model LLM Adapter Demo ===\n")
    # Register mock endpoints (no real keys)
    adapter.register(ModelEndpoint(
        provider=Provider.OPENAI, name="gpt4", base_url="https://api.openai.com/v1",
        model_id="gpt-4", api_key="sk-fake", capabilities=[ModelCapability.CHAT], priority=0,
    ))
    adapter.register(ModelEndpoint(
        provider=Provider.OLLAMA, name="llama3", base_url="http://localhost:11434",
        model_id="llama3", capabilities=[ModelCapability.CHAT, ModelCapability.CODE], priority=1,
    ))
    adapter.register(ModelEndpoint(
        provider=Provider.ANTHROPIC, name="claude", base_url="https://api.anthropic.com/v1",
        model_id="claude-3-sonnet", api_key="fake-key", capabilities=[ModelCapability.CHAT, ModelCapability.VISION], priority=2,
    ))
    print(f"Registered {len(adapter._endpoints)} endpoints")
    # Show failover order
    for ep in sorted(adapter.list_endpoints(), key=lambda e: e.priority):
        print(f"  [{ep.priority}] {ep.name} ({ep.provider.value})")
    # Stats
    print(f"\nStats: {adapter.stats()}")


if __name__ == "__main__":
    _demo()

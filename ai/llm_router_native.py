#!/usr/bin/env python3
"""
================================================================================
MAGNATRIX-OS — LLM Router (Layer 10 Extension)
Inspired by: agiresearch/AIOS aios/llm_core/
Multi-backend LLM routing with fallback, load balancing, streaming,
and provider-specific adapters (OpenAI, Anthropic, Ollama, Local).
================================================================================
Zero-dependency router with urllib-based HTTP clients and queue management.
================================================================================
"""
from __future__ import annotations

import hashlib
import json
import queue
import threading
import time
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple


# =============================================================================
# Constants
# =============================================================================
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0


# =============================================================================
# Data Types
# =============================================================================
class ProviderType(Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    LOCAL = "local"
    CUSTOM = "custom"


class RoutingStrategy(Enum):
    ROUND_ROBIN = "round_robin"
    LEAST_LOADED = "least_loaded"
    FASTEST_RESPONSE = "fastest_response"
    FALLBACK = "fallback"
    PRIORITY = "priority"


@dataclass
class LLMProvider:
    provider_id: str
    type: ProviderType
    base_url: str
    api_key: str = ""
    model: str = ""
    timeout: float = DEFAULT_TIMEOUT
    max_tokens: int = 2048
    temperature: float = 0.7
    priority: int = 5
    weight: float = 1.0
    healthy: bool = True
    avg_latency_ms: float = 0.0
    success_rate: float = 1.0
    last_used: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMRequest:
    request_id: str
    prompt: str
    system_prompt: str = ""
    model: str = ""
    max_tokens: int = 2048
    temperature: float = 0.7
    stream: bool = False
    raw_response: bool = False
    timeout: float = DEFAULT_TIMEOUT
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    request_id: str
    text: str
    model: str = ""
    provider_id: str = ""
    tokens_used: int = 0
    tokens_prompt: int = 0
    tokens_completion: int = 0
    latency_ms: float = 0.0
    finish_reason: str = ""
    raw: Any = None


@dataclass
class StreamingChunk:
    request_id: str
    chunk: str
    done: bool = False
    provider_id: str = ""


# =============================================================================
# Base Adapter
# =============================================================================
class LLMAdapter(ABC):
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    @abstractmethod
    def chat(self, request: LLMRequest) -> LLMResponse: ...

    @abstractmethod
    def stream(self, request: LLMRequest) -> Iterator[StreamingChunk]: ...

    def _http_post(self, endpoint: str, body: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> Tuple[int, str]:
        url = f"{self.provider.base_url.rstrip('/')}{endpoint}"
        data = json.dumps(body).encode("utf-8")
        req_headers = {"Content-Type": "application/json", **(headers or {})}
        if self.provider.api_key:
            req_headers["Authorization"] = f"Bearer {self.provider.api_key}"
        req = urllib.request.Request(url, data=data, headers=req_headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.provider.timeout) as resp:
                return resp.status, resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", errors="replace")
        except Exception as exc:
            return 0, str(exc)

    def _http_get(self, endpoint: str, headers: Optional[Dict[str, str]] = None) -> Tuple[int, str]:
        url = f"{self.provider.base_url.rstrip('/')}{endpoint}"
        req_headers = {"Content-Type": "application/json", **(headers or {})}
        if self.provider.api_key:
            req_headers["Authorization"] = f"Bearer {self.provider.api_key}"
        req = urllib.request.Request(url, headers=req_headers)
        try:
            with urllib.request.urlopen(req, timeout=self.provider.timeout) as resp:
                return resp.status, resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", errors="replace")
        except Exception as exc:
            return 0, str(exc)

    def health_check(self) -> bool:
        return True  # Override in subclasses


# =============================================================================
# OpenAI Adapter
# =============================================================================
class OpenAIAdapter(LLMAdapter):
    def chat(self, request: LLMRequest) -> LLMResponse:
        t0 = time.perf_counter()
        model = request.model or self.provider.model or "gpt-4"
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.prompt},
            ],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        status, text = self._http_post("/v1/chat/completions", body)
        latency = (time.perf_counter() - t0) * 1000
        if status != 200:
            return LLMResponse(request_id=request.request_id, text="", latency_ms=latency, raw={"error": text})
        try:
            data = json.loads(text)
            choice = data.get("choices", [{}])[0]
            return LLMResponse(
                request_id=request.request_id,
                text=choice.get("message", {}).get("content", ""),
                model=model,
                provider_id=self.provider.provider_id,
                tokens_used=data.get("usage", {}).get("total_tokens", 0),
                tokens_prompt=data.get("usage", {}).get("prompt_tokens", 0),
                tokens_completion=data.get("usage", {}).get("completion_tokens", 0),
                latency_ms=latency,
                finish_reason=choice.get("finish_reason", ""),
                raw=data if request.raw_response else None,
            )
        except Exception as exc:
            return LLMResponse(request_id=request.request_id, text="", latency_ms=latency, raw={"error": str(exc)})

    def stream(self, request: LLMRequest) -> Iterator[StreamingChunk]:
        # Stub: single chunk
        resp = self.chat(request)
        yield StreamingChunk(request_id=request.request_id, chunk=resp.text, done=True, provider_id=self.provider.provider_id)

    def health_check(self) -> bool:
        status, _ = self._http_get("/v1/models")
        return status == 200


# =============================================================================
# Anthropic Adapter
# =============================================================================
class AnthropicAdapter(LLMAdapter):
    def chat(self, request: LLMRequest) -> LLMResponse:
        t0 = time.perf_counter()
        model = request.model or self.provider.model or "claude-3-opus-20240229"
        body = {
            "model": model,
            "messages": [{"role": "user", "content": request.prompt}],
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "system": request.system_prompt,
        }
        headers = {"x-api-key": self.provider.api_key, "anthropic-version": "2023-06-01"}
        status, text = self._http_post("/v1/messages", body, headers)
        latency = (time.perf_counter() - t0) * 1000
        if status != 200:
            return LLMResponse(request_id=request.request_id, text="", latency_ms=latency, raw={"error": text})
        try:
            data = json.loads(text)
            content = " ".join(c.get("text", "") for c in data.get("content", []))
            return LLMResponse(
                request_id=request.request_id,
                text=content,
                model=model,
                provider_id=self.provider.provider_id,
                tokens_prompt=data.get("usage", {}).get("input_tokens", 0),
                tokens_completion=data.get("usage", {}).get("output_tokens", 0),
                tokens_used=data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0),
                latency_ms=latency,
                finish_reason=data.get("stop_reason", ""),
                raw=data if request.raw_response else None,
            )
        except Exception as exc:
            return LLMResponse(request_id=request.request_id, text="", latency_ms=latency, raw={"error": str(exc)})

    def stream(self, request: LLMRequest) -> Iterator[StreamingChunk]:
        resp = self.chat(request)
        yield StreamingChunk(request_id=request.request_id, chunk=resp.text, done=True, provider_id=self.provider.provider_id)

    def health_check(self) -> bool:
        headers = {"x-api-key": self.provider.api_key, "anthropic-version": "2023-06-01"}
        status, _ = self._http_get("/v1/models", headers)
        return status == 200


# =============================================================================
# Ollama Adapter
# =============================================================================
class OllamaAdapter(LLMAdapter):
    def chat(self, request: LLMRequest) -> LLMResponse:
        t0 = time.perf_counter()
        model = request.model or self.provider.model or "llama3"
        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                {"role": "user", "content": request.prompt},
            ],
            "stream": False,
            "options": {"temperature": request.temperature, "num_predict": request.max_tokens},
        }
        status, text = self._http_post("/api/chat", body)
        latency = (time.perf_counter() - t0) * 1000
        if status != 200:
            return LLMResponse(request_id=request.request_id, text="", latency_ms=latency, raw={"error": text})
        try:
            data = json.loads(text)
            return LLMResponse(
                request_id=request.request_id,
                text=data.get("message", {}).get("content", ""),
                model=model,
                provider_id=self.provider.provider_id,
                latency_ms=latency,
                raw=data if request.raw_response else None,
            )
        except Exception as exc:
            return LLMResponse(request_id=request.request_id, text="", latency_ms=latency, raw={"error": str(exc)})

    def stream(self, request: LLMRequest) -> Iterator[StreamingChunk]:
        resp = self.chat(request)
        yield StreamingChunk(request_id=request.request_id, chunk=resp.text, done=True, provider_id=self.provider.provider_id)

    def health_check(self) -> bool:
        status, _ = self._http_get("/api/tags")
        return status == 200


# =============================================================================
# Local Adapter (stub for inference_backend_native.py)
# =============================================================================
class LocalAdapter(LLMAdapter):
    def __init__(self, provider: LLMProvider, inference_engine: Any = None) -> None:
        super().__init__(provider)
        self.engine = inference_engine

    def chat(self, request: LLMRequest) -> LLMResponse:
        t0 = time.perf_counter()
        if self.engine:
            model = request.model or self.provider.model
            out = ""
            for chunk in self.engine.generate(model, request.prompt, max_tokens=request.max_tokens, temperature=request.temperature):
                out += chunk
            return LLMResponse(
                request_id=request.request_id,
                text=out,
                model=model or "local",
                provider_id=self.provider.provider_id,
                latency_ms=(time.perf_counter() - t0) * 1000,
            )
        return LLMResponse(
            request_id=request.request_id,
            text="[Local inference not configured]",
            provider_id=self.provider.provider_id,
        )

    def stream(self, request: LLMRequest) -> Iterator[StreamingChunk]:
        t0 = time.perf_counter()
        if self.engine:
            model = request.model or self.provider.model
            for chunk in self.engine.generate(model, request.prompt, max_tokens=request.max_tokens, temperature=request.temperature):
                yield StreamingChunk(request_id=request.request_id, chunk=chunk, done=False, provider_id=self.provider.provider_id)
            yield StreamingChunk(request_id=request.request_id, chunk="", done=True, provider_id=self.provider.provider_id)
        else:
            yield StreamingChunk(request_id=request.request_id, chunk="[Local inference not configured]", done=True, provider_id=self.provider.provider_id)

    def health_check(self) -> bool:
        return self.engine is not None


# =============================================================================
# Adapter Factory
# =============================================================================
class AdapterFactory:
    @staticmethod
    def create(provider: LLMProvider, inference_engine: Any = None) -> LLMAdapter:
        if provider.type == ProviderType.OPENAI:
            return OpenAIAdapter(provider)
        elif provider.type == ProviderType.ANTHROPIC:
            return AnthropicAdapter(provider)
        elif provider.type == ProviderType.OLLAMA:
            return OllamaAdapter(provider)
        elif provider.type == ProviderType.LOCAL:
            return LocalAdapter(provider, inference_engine)
        return OpenAIAdapter(provider)


# =============================================================================
# LLM Router
# =============================================================================
class LLMRouter:
    """Route LLM requests to appropriate backends with failover."""

    def __init__(self, strategy: RoutingStrategy = RoutingStrategy.ROUND_ROBIN) -> None:
        self.strategy = strategy
        self._providers: Dict[str, LLMProvider] = {}
        self._adapters: Dict[str, LLMAdapter] = {}
        self._lock = threading.Lock()
        self._rr_index = 0
        self._queue: queue.Queue[Tuple[LLMRequest, Callable[[LLMResponse], None]]] = queue.Queue()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._inference_engine: Any = None
        self._callbacks: List[Callable[[LLMRequest, LLMResponse], None]] = []

    def set_inference_engine(self, engine: Any) -> None:
        self._inference_engine = engine

    def register_provider(self, provider: LLMProvider) -> None:
        with self._lock:
            self._providers[provider.provider_id] = provider
            self._adapters[provider.provider_id] = AdapterFactory.create(provider, self._inference_engine)

    def unregister_provider(self, provider_id: str) -> bool:
        with self._lock:
            return self._providers.pop(provider_id, None) is not None

    def health_check_all(self) -> Dict[str, bool]:
        with self._lock:
            return {pid: adapter.health_check() for pid, adapter in self._adapters.items()}

    def on_response(self, callback: Callable[[LLMRequest, LLMResponse], None]) -> None:
        self._callbacks.append(callback)

    def _select_provider(self, request: LLMRequest) -> Optional[LLMProvider]:
        with self._lock:
            healthy = [p for p in self._providers.values() if p.healthy]
        if not healthy:
            return None
        if self.strategy == RoutingStrategy.ROUND_ROBIN:
            idx = self._rr_index % len(healthy)
            self._rr_index += 1
            return healthy[idx]
        elif self.strategy == RoutingStrategy.LEAST_LOADED:
            return min(healthy, key=lambda p: p.last_used)
        elif self.strategy == RoutingStrategy.FASTEST_RESPONSE:
            return min(healthy, key=lambda p: p.avg_latency_ms)
        elif self.strategy == RoutingStrategy.PRIORITY:
            return min(healthy, key=lambda p: p.priority)
        return healthy[0]

    def chat(self, request: LLMRequest) -> LLMResponse:
        provider = self._select_provider(request)
        if not provider:
            return LLMResponse(request_id=request.request_id, text="[No healthy provider available]")
        adapter = self._adapters.get(provider.provider_id)
        if not adapter:
            return LLMResponse(request_id=request.request_id, text="[No adapter available]")
        # Retry logic
        for attempt in range(DEFAULT_MAX_RETRIES):
            resp = adapter.chat(request)
            provider.last_used = time.time()
            if resp.text or resp.raw:
                provider.avg_latency_ms = (provider.avg_latency_ms * 0.9) + (resp.latency_ms * 0.1)
                provider.success_rate = (provider.success_rate * 0.99) + (1.0 * 0.01)
                for cb in self._callbacks:
                    cb(request, resp)
                return resp
            provider.success_rate = (provider.success_rate * 0.99) + (0.0 * 0.01)
            if attempt < DEFAULT_MAX_RETRIES - 1:
                time.sleep(DEFAULT_RETRY_DELAY * (attempt + 1))
        return LLMResponse(
            request_id=request.request_id,
            text="[All retries failed]",
            provider_id=provider.provider_id,
        )

    def stream(self, request: LLMRequest) -> Iterator[StreamingChunk]:
        provider = self._select_provider(request)
        if not provider:
            yield StreamingChunk(request_id=request.request_id, chunk="[No healthy provider]", done=True)
            return
        adapter = self._adapters.get(provider.provider_id)
        if not adapter:
            yield StreamingChunk(request_id=request.request_id, chunk="[No adapter]", done=True)
            return
        for chunk in adapter.stream(request):
            yield chunk

    def list_providers(self) -> List[LLMProvider]:
        with self._lock:
            return list(self._providers.values())


# =============================================================================
# LLM Router Kernel Bridge
# =============================================================================
class LLMRouterKernelBridge:
    def __init__(self, router: LLMRouter, event_bus: Any = None) -> None:
        self.router = router
        self.bus = event_bus
        router.on_response(self._on_response)

    def _on_response(self, request: LLMRequest, response: LLMResponse) -> None:
        if self.bus:
            self.bus.publish("llm.response", {
                "request_id": request.request_id,
                "provider": response.provider_id,
                "latency_ms": response.latency_ms,
                "tokens": response.tokens_used,
            })


# =============================================================================
# Demo
# =============================================================================
def run_demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS LLM Router Demo")
    print("=" * 60)
    router = LLMRouter(strategy=RoutingStrategy.ROUND_ROBIN)
    router.register_provider(LLMProvider(
        provider_id="openai-1",
        type=ProviderType.OPENAI,
        base_url="https://api.openai.com",
        api_key="sk-fake",
        model="gpt-4",
    ))
    router.register_provider(LLMProvider(
        provider_id="anthropic-1",
        type=ProviderType.ANTHROPIC,
        base_url="https://api.anthropic.com",
        api_key="sk-ant-fake",
        model="claude-3-opus",
    ))
    router.register_provider(LLMProvider(
        provider_id="ollama-1",
        type=ProviderType.OLLAMA,
        base_url="http://localhost:11434",
        model="llama3",
    ))
    print(f"Registered {len(router.list_providers())} providers")
    for p in router.list_providers():
        print(f"  {p.provider_id}: {p.type.value} ({p.model})")
    req = LLMRequest(
        request_id="demo-1",
        prompt="Explain quantum computing in one sentence.",
        system_prompt="You are a helpful assistant.",
    )
    # Note: actual chat will fail without real API keys
    resp = router.chat(req)
    print(f"Response: {resp.text[:80]}...")
    print(f"Provider: {resp.provider_id}, Latency: {resp.latency_ms:.1f}ms")
    print("Demo complete.")


if __name__ == "__main__":
    run_demo()

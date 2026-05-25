#!/usr/bin/env python3
"""
ai/agentic_router_native.py
===========================
Layer 10 Extension — Multi-Backend Agentic Router

Routes LLM requests across multiple free/cheap backends:
  1. Local GGUF model (offline, fastest, zero cost)
  2. Hermes Agentic (function calling, tool use)
  3. OpenClaw / OpenRouter (free tier models)
  4. Other free APIs (Groq, Together, etc.)

Auto-fallback chain: Local → Hermes → OpenClaw → Groq → Error
Cost tracking per backend. Health-aware routing.

Usage:
  from ai.agentic_router_native import AgenticRouter
  router = AgenticRouter()
  response = router.chat("What is quantum computing?")
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class BackendHealth:
    name: str
    last_success: float = 0.0
    last_failure: float = 0.0
    success_count: int = 0
    failure_count: int = 0
    avg_latency_ms: float = 0.0
    disabled: bool = False

    @property
    def is_healthy(self) -> bool:
        if self.disabled:
            return False
        if self.failure_count > 5 and self.success_count == 0:
            return False
        return True


@dataclass
class BackendConfig:
    name: str
    weight: float = 1.0  # Routing weight
    cost_per_1k_tokens: float = 0.0  # 0 = free
    supports_tools: bool = False
    supports_streaming: bool = False
    timeout_sec: float = 30.0
    api_key_env: str = ""


class AgenticRouter:
    """Intelligent multi-backend LLM router for MAGNATRIX-OS."""

    def __init__(self, config_path: Optional[str] = None) -> None:
        self._backends: Dict[str, Any] = {}
        self._health: Dict[str, BackendHealth] = {}
        self._configs: Dict[str, BackendConfig] = {}
        self._history: List[Dict[str, Any]] = []
        self._total_requests = 0
        self._init_backends()

    def _init_backends(self) -> None:
        """Initialize all available backends lazily."""
        # 1. Local GGUF (offline, always available if model exists)
        self._configs["local_gguf"] = BackendConfig(
            name="local_gguf", weight=10.0, cost_per_1k_tokens=0.0,
            supports_tools=False, timeout_sec=60.0,
        )
        try:
            from ai.gguf_loader_native import GGUFLoader
            self._backends["local_gguf"] = GGUFLoader
            self._health["local_gguf"] = BackendHealth("local_gguf")
        except Exception:
            pass

        # 2. Hermes Agentic
        self._configs["hermes"] = BackendConfig(
            name="hermes", weight=8.0, cost_per_1k_tokens=0.0,
            supports_tools=True, timeout_sec=30.0,
            api_key_env="HERMES_API_KEY",
        )
        if os.environ.get("HERMES_API_KEY"):
            try:
                from ai.hermes_agentic_native import HermesAgentic
                self._backends["hermes"] = HermesAgentic()
                self._health["hermes"] = BackendHealth("hermes")
            except Exception as e:
                self._health["hermes"] = BackendHealth("hermes", disabled=True)

        # 3. OpenClaw / OpenRouter
        self._configs["openclaw"] = BackendConfig(
            name="openclaw", weight=7.0, cost_per_1k_tokens=0.0,
            supports_tools=False, timeout_sec=30.0,
            api_key_env="OPENCLAW_API_KEY",
        )
        if os.environ.get("OPENCLAW_API_KEY") or os.environ.get("OPENROUTER_API_KEY"):
            try:
                from ai.openclaw_native import OpenClaw
                self._backends["openclaw"] = OpenClaw()
                self._health["openclaw"] = BackendHealth("openclaw")
            except Exception as e:
                self._health["openclaw"] = BackendHealth("openclaw", disabled=True)

        # 4. Groq (free tier: 20 requests/min)
        self._configs["groq"] = BackendConfig(
            name="groq", weight=6.0, cost_per_1k_tokens=0.0,
            supports_tools=True, timeout_sec=10.0,
            api_key_env="GROQ_API_KEY",
        )
        if os.environ.get("GROQ_API_KEY"):
            self._health["groq"] = BackendHealth("groq")

        # 5. Together AI (free trial)
        self._configs["together"] = BackendConfig(
            name="together", weight=5.0, cost_per_1k_tokens=0.0,
            supports_tools=False, timeout_sec=30.0,
            api_key_env="TOGETHER_API_KEY",
        )
        if os.environ.get("TOGETHER_API_KEY"):
            self._health["together"] = BackendHealth("together")

    def _select_backend(self, require_tools: bool = False) -> Optional[str]:
        """Select best available backend based on health, cost, weight."""
        candidates = []
        for name, health in self._health.items():
            if not health.is_healthy:
                continue
            cfg = self._configs.get(name)
            if not cfg:
                continue
            if require_tools and not cfg.supports_tools:
                continue
            if name not in self._backends:
                continue
            # Score: higher weight, lower cost, lower failure rate
            failure_rate = health.failure_count / max(1, health.failure_count + health.success_count)
            score = cfg.weight * (1 - failure_rate) / (1 + cfg.cost_per_1k_tokens)
            candidates.append((name, score))
        if not candidates:
            return None
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[0][0]

    def chat(self, message: str, system: str = "",
             require_tools: bool = False, **kwargs) -> Dict[str, Any]:
        """Route chat to best available backend with auto-fallback."""
        self._total_requests += 1
        tried: List[str] = []
        backend_name = self._select_backend(require_tools)

        while backend_name:
            tried.append(backend_name)
            backend = self._backends[backend_name]
            health = self._health[backend_name]
            t0 = time.time()

            try:
                if backend_name == "local_gguf":
                    # Local model inference
                    result = self._call_local(message, system)
                elif backend_name == "hermes":
                    result = backend.chat(message, system=system)
                elif backend_name == "openclaw":
                    result = backend.chat(message, system=system)
                elif backend_name == "groq":
                    result = self._call_groq(message, system)
                elif backend_name == "together":
                    result = self._call_together(message, system)
                else:
                    result = {"error": f"Unknown backend: {backend_name}"}

                latency = (time.time() - t0) * 1000
                if "error" not in result:
                    health.success_count += 1
                    health.last_success = time.time()
                    health.avg_latency_ms = (health.avg_latency_ms * 0.9) + (latency * 0.1)
                    self._history.append({
                        "backend": backend_name, "latency_ms": latency,
                        "status": "success", "message_preview": message[:50],
                    })
                    return {**result, "_backend": backend_name, "_latency_ms": latency}
                else:
                    health.failure_count += 1
                    health.last_failure = time.time()
            except Exception as e:
                health.failure_count += 1
                health.last_failure = time.time()

            # Try next backend
            backend_name = self._select_backend(require_tools)
            if backend_name in tried:
                break

        return {"error": f"All backends failed. Tried: {tried}", "_tried": tried}

    def _call_local(self, message: str, system: str) -> Dict[str, Any]:
        """Stub: would run local GGUF model inference."""
        return {"error": "Local model not loaded. Place a .gguf file in /var/lib/magnatrix/models/"}

    def _call_groq(self, message: str, system: str) -> Dict[str, Any]:
        """Groq API call stub."""
        import urllib.request
        import json
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            return {"error": "GROQ_API_KEY not set"}
        payload = {
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": message}] if system else [{"role": "user", "content": message}],
            "temperature": 0.7,
        }
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=data, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            return {"error": str(e)}

    def _call_together(self, message: str, system: str) -> Dict[str, Any]:
        """Together AI API call stub."""
        return {"error": "Together AI integration stub"}

    def register_local_model(self, gguf_path: str) -> bool:
        """Register a local .gguf model file."""
        try:
            from ai.gguf_loader_native import GGUFLoader
            loader = GGUFLoader(gguf_path)
            loader.load_metadata()
            self._backends["local_gguf"] = loader
            self._health["local_gguf"] = BackendHealth("local_gguf")
            print(f"[ROUTER] Local model registered: {gguf_path}")
            return True
        except Exception as e:
            print(f"[ROUTER] Failed to load local model: {e}")
            return False

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "total_requests": self._total_requests,
            "backends_available": len([h for h in self._health.values() if h.is_healthy]),
            "backends_total": len(self._health),
            "health": {name: {"success": h.success_count, "failure": h.failure_count,
                              "healthy": h.is_healthy, "latency_ms": round(h.avg_latency_ms, 1)}
                       for name, h in self._health.items()},
            "cost_per_1k": {name: cfg.cost_per_1k_tokens
                           for name, cfg in self._configs.items()},
        }


def demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS  |  AGENTIC ROUTER")
    print("=" * 60)
    router = AgenticRouter()
    print("Available backends:")
    for name, cfg in router._configs.items():
        health = router._health.get(name)
        status = "✅" if health and health.is_healthy else "❌"
        print(f"  {status} {name:12s} (cost: ${cfg.cost_per_1k_tokens:.4f}/1K, tools: {cfg.supports_tools})")
    print(f"\nStats: {router.stats}")
    print("\nUsage: router.chat('Hello world')")
    print("Set API keys: HERMES_API_KEY, OPENCLAW_API_KEY, GROQ_API_KEY, TOGETHER_API_KEY")
    print("Or place .gguf in /var/lib/magnatrix/models/ for offline inference")
    print("=" * 60)


if __name__ == "__main__":
    demo()

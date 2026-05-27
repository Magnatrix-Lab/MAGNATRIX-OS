#!/usr/bin/env python3
"""
MAGNATRIX-OS — Unified LLM Backend
Real LLM integration with auto-fallback: Ollama → Groq → Together → HuggingFace.
Circuit breaker, rate limiting, token budget, health checks.
"""
from __future__ import annotations

import json
import os
import random
import threading
import time
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Any, Callable


# ── Configuration ───────────────────────────────────────────

class BackendTier(Enum):
    LOCAL = auto()
    CLOUD = auto()
    FREE = auto()


@dataclass
class BackendConfig:
    name: str
    tier: BackendTier
    api_key_env: str = ""
    base_url: str = ""
    default_model: str = ""
    max_tokens: int = 4096
    timeout: float = 30.0
    rate_limit_per_minute: int = 60


# ── Circuit Breaker ─────────────────────────────────────────

class CircuitBreaker:
    """Circuit breaker: CLOSED → OPEN → HALF_OPEN"""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state = "closed"  # closed, open, half_open
        self._failures = 0
        self._last_failure = 0.0
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        with self._lock:
            if self._state == "open":
                if time.time() - self._last_failure >= self.recovery_timeout:
                    self._state = "half_open"
                    self._failures = 0
            return self._state

    def record_success(self) -> None:
        with self._lock:
            self._failures = 0
            self._state = "closed"

    def record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            self._last_failure = time.time()
            if self._failures >= self.failure_threshold:
                self._state = "open"

    def can_execute(self) -> bool:
        return self.state in ("closed", "half_open")


# ── Rate Limiter ────────────────────────────────────────────

class TokenBucketRateLimiter:
    """Token bucket rate limiter per backend."""

    def __init__(self, rate_per_minute: int = 60):
        self.rate = rate_per_minute / 60.0  # tokens per second
        self.capacity = rate_per_minute
        self._tokens = float(rate_per_minute)
        self._last_update = time.time()
        self._lock = threading.Lock()

    def acquire(self, tokens: int = 1) -> bool:
        with self._lock:
            now = time.time()
            elapsed = now - self._last_update
            self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
            self._last_update = now
            if self._tokens >= tokens:
                self._tokens -= tokens
                return True
            return False

    def wait_time(self, tokens: int = 1) -> float:
        with self._lock:
            deficit = tokens - self._tokens
            if deficit <= 0:
                return 0.0
            return deficit / self.rate


# ── LLM Backend Base ──────────────────────────────────────

class LLMBackend(ABC):
    """Abstract base for LLM backends."""

    def __init__(self, config: BackendConfig):
        self.config = config
        self.circuit = CircuitBreaker()
        self.rate_limiter = TokenBucketRateLimiter(config.rate_limit_per_minute)
        self._stats = {"requests": 0, "successes": 0, "failures": 0, "tokens": 0}
        self._stat_lock = threading.Lock()

    @property
    def name(self) -> str:
        return self.config.name

    @abstractmethod
    def generate(self, prompt: str, **kwargs) -> str:
        ...

    @abstractmethod
    def health(self) -> bool:
        ...

    def _get_api_key(self) -> Optional[str]:
        return os.environ.get(self.config.api_key_env) or None

    def _http_post(self, url: str, headers: Dict, body: bytes, timeout: float) -> Dict:
        req = urllib.request.Request(
            url, data=body, headers=headers, method="POST"
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _http_get(self, url: str, headers: Dict, timeout: float) -> Dict:
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _record(self, success: bool, tokens: int = 0) -> None:
        with self._stat_lock:
            self._stats["requests"] += 1
            if success:
                self._stats["successes"] += 1
                self.circuit.record_success()
            else:
                self._stats["failures"] += 1
                self.circuit.record_failure()
            self._stats["tokens"] += tokens

    def get_stats(self) -> Dict[str, Any]:
        with self._stat_lock:
            return dict(self._stats)


# ── Ollama Backend (Local) ──────────────────────────────────

class OllamaBackend(LLMBackend):
    """Local inference via Ollama HTTP API."""

    def __init__(self, model: str = "llama3.2", url: str = "http://localhost:11434"):
        super().__init__(BackendConfig(
            name="ollama",
            tier=BackendTier.LOCAL,
            base_url=url,
            default_model=model,
            rate_limit_per_minute=1000,  # Local = generous
        ))

    def health(self) -> bool:
        try:
            req = urllib.request.Request(
                f"{self.config.base_url}/api/tags",
                method="GET",
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def generate(self, prompt: str, **kwargs) -> str:
        if not self.circuit.can_execute():
            raise RuntimeError(f"Ollama circuit breaker OPEN")
        if not self.rate_limiter.acquire():
            raise RuntimeError(f"Ollama rate limit exceeded")

        model = kwargs.get("model", self.config.default_model)
        body = json.dumps({
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": kwargs.get("temperature", 0.7),
                "num_predict": kwargs.get("max_tokens", self.config.max_tokens),
            }
        }).encode("utf-8")

        try:
            result = self._http_post(
                f"{self.config.base_url}/api/generate",
                {"Content-Type": "application/json"},
                body,
                self.config.timeout,
            )
            text = result.get("response", "")
            self._record(True, len(text.split()))
            return text
        except Exception as e:
            self._record(False)
            raise RuntimeError(f"Ollama generation failed: {e}")


# ── Groq Backend (Cloud Fast) ───────────────────────────────

class GroqBackend(LLMBackend):
    """Groq cloud inference — fast, affordable."""

    def __init__(self, model: str = "llama-3.3-70b-versatile"):
        super().__init__(BackendConfig(
            name="groq",
            tier=BackendTier.CLOUD,
            api_key_env="GROQ_API_KEY",
            base_url="https://api.groq.com/openai/v1",
            default_model=model,
            rate_limit_per_minute=30,
        ))

    def health(self) -> bool:
        key = self._get_api_key()
        if not key:
            return False
        try:
            req = urllib.request.Request(
                f"{self.config.base_url}/models",
                headers={"Authorization": f"Bearer {key}"},
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def generate(self, prompt: str, **kwargs) -> str:
        if not self.circuit.can_execute():
            raise RuntimeError(f"Groq circuit breaker OPEN")
        if not self.rate_limiter.acquire():
            raise RuntimeError(f"Groq rate limit exceeded")

        key = self._get_api_key()
        if not key:
            raise RuntimeError("GROQ_API_KEY not set")

        body = json.dumps({
            "model": kwargs.get("model", self.config.default_model),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
        }).encode("utf-8")

        try:
            result = self._http_post(
                f"{self.config.base_url}/chat/completions",
                {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {key}",
                },
                body,
                self.config.timeout,
            )
            text = result["choices"][0]["message"]["content"]
            self._record(True, result.get("usage", {}).get("total_tokens", 0))
            return text
        except Exception as e:
            self._record(False)
            raise RuntimeError(f"Groq generation failed: {e}")


# ── Together Backend (Cloud Open) ───────────────────────────

class TogetherBackend(LLMBackend):
    """Together AI — open source model hosting."""

    def __init__(self, model: str = "meta-llama/Llama-3.3-70B-Instruct-Turbo"):
        super().__init__(BackendConfig(
            name="together",
            tier=BackendTier.CLOUD,
            api_key_env="TOGETHER_API_KEY",
            base_url="https://api.together.xyz/v1",
            default_model=model,
            rate_limit_per_minute=20,
        ))

    def health(self) -> bool:
        key = self._get_api_key()
        if not key:
            return False
        try:
            req = urllib.request.Request(
                f"{self.config.base_url}/models",
                headers={"Authorization": f"Bearer {key}"},
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False

    def generate(self, prompt: str, **kwargs) -> str:
        if not self.circuit.can_execute():
            raise RuntimeError(f"Together circuit breaker OPEN")
        if not self.rate_limiter.acquire():
            raise RuntimeError(f"Together rate limit exceeded")

        key = self._get_api_key()
        if not key:
            raise RuntimeError("TOGETHER_API_KEY not set")

        body = json.dumps({
            "model": kwargs.get("model", self.config.default_model),
            "messages": [{"role": "user", "content": prompt}],
            "temperature": kwargs.get("temperature", 0.7),
            "max_tokens": kwargs.get("max_tokens", self.config.max_tokens),
        }).encode("utf-8")

        try:
            result = self._http_post(
                f"{self.config.base_url}/chat/completions",
                {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {key}",
                },
                body,
                self.config.timeout,
            )
            text = result["choices"][0]["message"]["content"]
            self._record(True, result.get("usage", {}).get("total_tokens", 0))
            return text
        except Exception as e:
            self._record(False)
            raise RuntimeError(f"Together generation failed: {e}")


# ── HuggingFace Backend (Free Tier) ──────────────────────────

class HuggingFaceBackend(LLMBackend):
    """HuggingFace Inference API — free tier, rate limited."""

    def __init__(self, model: str = "microsoft/Phi-3-mini-4k-instruct"):
        super().__init__(BackendConfig(
            name="huggingface",
            tier=BackendTier.FREE,
            api_key_env="HF_API_TOKEN",
            base_url="https://api-inference.huggingface.co/models",
            default_model=model,
            rate_limit_per_minute=10,
        ))

    def health(self) -> bool:
        key = self._get_api_key()
        if not key:
            return False
        try:
            req = urllib.request.Request(
                f"{self.config.base_url}/{self.config.default_model}",
                headers={"Authorization": f"Bearer {key}"},
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status in (200, 503)  # 503 = model loading
        except Exception:
            return False

    def generate(self, prompt: str, **kwargs) -> str:
        if not self.circuit.can_execute():
            raise RuntimeError(f"HuggingFace circuit breaker OPEN")
        if not self.rate_limiter.acquire():
            raise RuntimeError(f"HuggingFace rate limit exceeded")

        key = self._get_api_key()
        if not key:
            raise RuntimeError("HF_API_TOKEN not set")

        model = kwargs.get("model", self.config.default_model)
        body = json.dumps({
            "inputs": prompt,
            "parameters": {
                "temperature": kwargs.get("temperature", 0.7),
                "max_new_tokens": kwargs.get("max_tokens", self.config.max_tokens),
                "return_full_text": False,
            }
        }).encode("utf-8")

        try:
            result = self._http_post(
                f"https://api-inference.huggingface.co/models/{model}",
                {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {key}",
                },
                body,
                self.config.timeout,
            )
            # HF returns list of generated texts
            if isinstance(result, list) and len(result) > 0:
                text = result[0].get("generated_text", "")
            else:
                text = str(result)
            self._record(True, len(text.split()))
            return text
        except Exception as e:
            self._record(False)
            raise RuntimeError(f"HuggingFace generation failed: {e}")


# ── Unified LLM Orchestrator ────────────────────────────────

class UnifiedLLMNative:
    """
    Orchestrates multiple LLM backends with:
    - Auto-fallback chain (local → cloud → free)
    - Circuit breaker per backend
    - Rate limiting
    - Token budget tracking
    - Health checks
    """

    DEFAULT_BACKENDS = [
        ("ollama", OllamaBackend),
        ("groq", GroqBackend),
        ("together", TogetherBackend),
        ("huggingface", HuggingFaceBackend),
    ]

    def __init__(
        self,
        backends: Optional[List[LLMBackend]] = None,
        enable_fallback: bool = True,
        max_retries: int = 2,
    ):
        self.backends = backends or [cls() for _, cls in self.DEFAULT_BACKENDS]
        self.enable_fallback = enable_fallback
        self.max_retries = max_retries
        self._fallback_order = [b for b in self.backends if b.config.tier == BackendTier.LOCAL] +                                 [b for b in self.backends if b.config.tier == BackendTier.CLOUD] +                                 [b for b in self.backends if b.config.tier == BackendTier.FREE]

    def generate(self, prompt: str, **kwargs) -> str:
        """Generate with auto-fallback across all backends."""
        preferred = kwargs.pop("preferred_backend", None)
        errors: List[str] = []

        # Try preferred backend first
        if preferred:
            for b in self.backends:
                if b.name == preferred:
                    try:
                        return b.generate(prompt, **kwargs)
                    except Exception as e:
                        errors.append(f"{b.name}: {e}")
                        break

        # Fallback chain
        if self.enable_fallback:
            for backend in self._fallback_order:
                for attempt in range(self.max_retries + 1):
                    try:
                        return backend.generate(prompt, **kwargs)
                    except Exception as e:
                        errors.append(f"{backend.name} (attempt {attempt + 1}): {e}")
                        if attempt < self.max_retries:
                            # Exponential backoff with jitter
                            delay = (2 ** attempt) * 0.5 + random.uniform(0, 0.5)
                            time.sleep(delay)

        raise RuntimeError(
            f"All LLM backends failed. Errors: {' | '.join(errors[:5])}"
        )

    def health_check(self) -> Dict[str, bool]:
        """Health check all backends."""
        return {b.name: b.health() for b in self.backends}

    def get_stats(self) -> Dict[str, Dict]:
        """Stats per backend."""
        return {b.name: b.get_stats() for b in self.backends}

    def get_circuit_states(self) -> Dict[str, str]:
        """Circuit breaker states."""
        return {b.name: b.circuit.state for b in self.backends}

    def reset_circuits(self) -> None:
        """Reset all circuit breakers to closed."""
        for b in self.backends:
            b.circuit._state = "closed"
            b.circuit._failures = 0


# ── Demo ───────────────────────────────────────────────────

def _demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Unified LLM Backend Demo")
    print("=" * 60)

    llm = UnifiedLLMNative()

    # Health check
    print("\n[1] Health Check")
    health = llm.health_check()
    for name, ok in health.items():
        status = "✅ UP" if ok else "❌ DOWN"
        print(f"    {name}: {status}")

    # Stats
    print("\n[2] Backend Stats")
    stats = llm.get_stats()
    for name, s in stats.items():
        print(f"    {name}: {s}")

    # Circuit states
    print("\n[3] Circuit Breaker States")
    circuits = llm.get_circuit_states()
    for name, state in circuits.items():
        print(f"    {name}: {state}")

    # Try generation (will fail without API keys / Ollama, showing fallback)
    print("\n[4] Generation Test (with fallback)")
    try:
        result = llm.generate("What is 2+2? Answer in one word.")
        print(f"    Result: {result[:100]}...")
    except RuntimeError as e:
        print(f"    Expected failure (no API keys/Ollama): {e}")

    print("\n" + "=" * 60)
    print("Demo complete.")
    print("=" * 60)


if __name__ == "__main__":
    _demo()

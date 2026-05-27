#!/usr/bin/env python3
"""
OpenClaw Unified Bridge — Wraps OpenClaw API calls to UnifiedLLM fallback chain
=================================================================================
~130 lines. Pure Python stdlib + UnifiedLLMBackend import.

Used by: OpenClaw gateway to route chat completions through UnifiedLLM.
"""

from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Resolve ai/ sibling directory for UnifiedLLMBackend import
# ---------------------------------------------------------------------------
_BRIDGE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_BRIDGE_DIR.parent))
from ai.unified_llm_backend import UnifiedLLMBackend, LLMResponse


# ===========================================================================
# Model mapping: OpenRouter-style IDs → (backend, model)
# ===========================================================================

_DEFAULT_MAP: Dict[str, tuple] = {
    # OpenRouter → (preferred_backend, provider_model_id)
    "openai/gpt-4o": ("groq", "llama3-70b-8192"),
    "openai/gpt-4o-mini": ("groq", "llama3-8b-8192"),
    "anthropic/claude-3.5-sonnet": ("groq", "llama3-70b-8192"),
    "anthropic/claude-3-haiku": ("groq", "llama3-8b-8192"),
    "meta-llama/llama-3.1-70b": ("groq", "llama3-70b-8192"),
    "meta-llama/llama-3.1-8b": ("groq", "llama3-8b-8192"),
    "mistralai/mistral-7b": ("together", "mistralai/Mistral-7B-Instruct-v0.2"),
    "google/gemini-flash": ("groq", "gemma2-9b-it"),
    "google/gemini-pro": ("groq", "llama3-70b-8192"),
    # Local-first aliases
    "local/llama3.2": ("ollama", "llama3.2"),
    "local/mistral": ("ollama", "mistral"),
    "local/codellama": ("ollama", "codellama"),
}


_BACKUP_FALLBACKS: List[str] = ["groq", "together", "ollama", "huggingface"]


# ===========================================================================
# Response dataclass
# ===========================================================================

@dataclass
class BridgeChatResult:
    content: str
    backend: str
    model: str
    latency_ms: float
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None
    raw: Optional[LLMResponse] = field(default=None, repr=False)


# ===========================================================================
# OpenClawUnifiedBridge
# ===========================================================================

class OpenClawUnifiedBridge:
    """
    Wraps OpenClaw-style chat calls and routes them through UnifiedLLMBackend.
    """

    def __init__(
        self,
        llm: Optional[UnifiedLLMBackend] = None,
        model_map: Optional[Dict[str, tuple]] = None,
        default_model: str = "openai/gpt-4o-mini",
        default_temperature: float = 0.7,
        default_max_tokens: int = 512,
    ):
        self._llm: Optional[UnifiedLLMBackend] = llm
        self.model_map = model_map or dict(_DEFAULT_MAP)
        self.default_model = default_model
        self.default_temperature = default_temperature
        self.default_max_tokens = default_max_tokens
        self._stats = {"calls": 0, "tokens": 0, "errors": 0}

    @property
    def llm(self) -> UnifiedLLMBackend:
        if self._llm is None:
            self._llm = UnifiedLLMBackend()
        return self._llm

    # ------------------------------------------------------------------
    # Core chat method
    # ------------------------------------------------------------------

    def chat(
        self,
        message: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> BridgeChatResult:
        """
        Send a chat message through UnifiedLLM with OpenRouter-style model mapping.
        Falls back to UnifiedLLM auto-fallback chain if model is unrecognized.
        """
        started = time.time()
        model_id = model or self.default_model

        # Resolve mapping
        backend, provider_model = self._resolve(model_id)

        # Build prompt (simple system+user concatenation)
        parts: List[str] = []
        if system:
            parts.append(f"System: {system}")
        parts.append(f"User: {message}")
        prompt = "\n\n".join(parts)

        try:
            resp: LLMResponse = self.llm.generate(
                prompt=prompt,
                model=provider_model,
                temperature=temperature or self.default_temperature,
                max_tokens=max_tokens or self.default_max_tokens,
                preferred_backend=backend,
            )
            self._stats["calls"] += 1
            self._stats["tokens"] += resp.tokens_used or 0
            return BridgeChatResult(
                content=resp.text.strip(),
                backend=resp.backend,
                model=resp.model,
                latency_ms=(time.time() - started) * 1000,
                tokens_used=resp.tokens_used,
                finish_reason=resp.finish_reason,
                raw=resp,
            )
        except Exception as exc:
            self._stats["errors"] += 1
            # Final fallback: let UnifiedLLM pick anything
            try:
                resp = self.llm.generate(
                    prompt=prompt,
                    temperature=temperature or self.default_temperature,
                    max_tokens=max_tokens or self.default_max_tokens,
                )
                self._stats["calls"] += 1
                self._stats["tokens"] += resp.tokens_used or 0
                return BridgeChatResult(
                    content=resp.text.strip(),
                    backend=resp.backend,
                    model=resp.model,
                    latency_ms=(time.time() - started) * 1000,
                    tokens_used=resp.tokens_used,
                    finish_reason=resp.finish_reason,
                    raw=resp,
                )
            except Exception:
                raise RuntimeError(f"OpenClaw bridge failed for model={model_id}: {exc}") from exc

    # ------------------------------------------------------------------
    # Async wrapper
    # ------------------------------------------------------------------

    async def chat_async(
        self,
        message: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> BridgeChatResult:
        """Async wrapper using asyncio thread pool."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.chat(message, model, system, temperature, max_tokens),
        )

    # ------------------------------------------------------------------
    # Model discovery
    # ------------------------------------------------------------------

    def get_available_models(self) -> List[Dict[str, Any]]:
        """
        Return a merged list of available models from all configured backends.
        """
        out: List[Dict[str, Any]] = []

        # 1. Mapped models (OpenRouter-style aliases)
        for alias, (backend, provider_model) in self.model_map.items():
            out.append({
                "id": alias,
                "backend": backend,
                "provider_model": provider_model,
                "type": "mapped",
            })

        # 2. Native backend models (from UnifiedLLMBackend defaults)
        out.extend([
            {"id": "ollama/llama3.2", "backend": "ollama", "provider_model": "llama3.2", "type": "native"},
            {"id": "ollama/mistral", "backend": "ollama", "provider_model": "mistral", "type": "native"},
            {"id": "groq/llama3-8b-8192", "backend": "groq", "provider_model": "llama3-8b-8192", "type": "native"},
            {"id": "groq/llama3-70b-8192", "backend": "groq", "provider_model": "llama3-70b-8192", "type": "native"},
            {"id": "together/llama-3.2-3b", "backend": "together", "provider_model": "meta-llama/Llama-3.2-3B-Instruct-Turbo", "type": "native"},
            {"id": "hf/dialo-gpt", "backend": "huggingface", "provider_model": "microsoft/DialoGPT-medium", "type": "native"},
        ])

        return out

    # ------------------------------------------------------------------
    # Resolution helper
    # ------------------------------------------------------------------

    def _resolve(self, model_id: str) -> tuple:
        """Return (backend, provider_model). Falls back to auto-detect."""
        if model_id in self.model_map:
            return self.model_map[model_id]

        # Prefix-based inference
        prefix = model_id.split("/")[0] if "/" in model_id else model_id
        if prefix == "local":
            return ("ollama", model_id.split("/", 1)[1] if "/" in model_id else "llama3.2")
        if prefix in ("openai", "anthropic", "meta-llama", "google"):
            return ("groq", "llama3-8b-8192")
        if prefix == "mistralai":
            return ("together", "mistralai/Mistral-7B-Instruct-v0.2")

        # Unknown → let UnifiedLLM decide via fallback chain
        return (None, None)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        return {
            "bridge": dict(self._stats),
            "unified_llm": self.llm.stats(),
        }

    def reset_stats(self) -> None:
        self._stats = {"calls": 0, "tokens": 0, "errors": 0}


# ===========================================================================
# Minimal sanity check
# ===========================================================================

if __name__ == "__main__":
    bridge = OpenClawUnifiedBridge()
    print("OpenClawUnifiedBridge loaded OK")
    print(f"Mapped models: {list(bridge.model_map.keys())[:5]}...")
    print(f"Available models count: {len(bridge.get_available_models())}")
    print(f"Stats: {bridge.stats()}")

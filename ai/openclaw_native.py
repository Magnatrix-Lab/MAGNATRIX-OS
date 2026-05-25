#!/usr/bin/env python3
"""
ai/openclaw_native.py
====================
Layer 10 Extension — OpenClaw Integration

MAGNATRIX-OS interface to OpenClaw / OpenRouter / other free API aggregators.
OpenClaw provides access to multiple LLM backends through a single endpoint.

Usage:
  from ai.openclaw_native import OpenClaw
  claw = OpenClaw(api_key="...")
  response = claw.chat("Hello", model="anthropic/claude-3-haiku")
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class OpenClawConfig:
    api_key: str = ""
    base_url: str = "https://openrouter.ai/api/v1"
    default_model: str = "anthropic/claude-3-haiku-20240307"
    timeout: float = 30.0
    fallback_models: List[str] = None

    def __post_init__(self):
        if self.fallback_models is None:
            self.fallback_models = [
                "meta-llama/llama-3.1-8b-instruct",
                "google/gemma-2-9b-it",
                "mistralai/mistral-7b-instruct",
                "microsoft/phi-3-mini-128k-instruct",
            ]


class OpenClaw:
    """OpenClaw / OpenRouter API client — zero external dependencies."""

    def __init__(self, config: Optional[OpenClawConfig] = None) -> None:
        self.config = config or OpenClawConfig(
            api_key=os.environ.get("OPENCLAW_API_KEY", os.environ.get("OPENROUTER_API_KEY", ""))
        )
        self._history: List[Dict[str, Any]] = []
        self._last_error: Optional[str] = None
        self._request_count = 0

    def chat(self, message: str, model: Optional[str] = None,
             system: str = "", temperature: float = 0.7,
             max_tokens: int = 2048, enable_fallback: bool = True) -> Dict[str, Any]:
        """Send chat with automatic fallback across free models."""
        models_to_try = [model or self.config.default_model]
        if enable_fallback:
            models_to_try.extend(self.config.fallback_models)

        for m in models_to_try:
            result = self._try_chat(m, message, system, temperature, max_tokens)
            if "error" not in result:
                self._request_count += 1
                return result
            self._last_error = result.get("error")

        return {"error": f"All models failed. Last: {self._last_error}"}

    def _try_chat(self, model: str, message: str, system: str,
                  temperature: float, max_tokens: int) -> Dict[str, Any]:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": message})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        return self._http_post(f"{self.config.base_url}/chat/completions", payload)

    def _http_post(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        import urllib.request
        import urllib.error
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.config.api_key}",
            "HTTP-Referer": "https://magnatrix.io",
            "X-Title": "MAGNATRIX-OS",
        }
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            return {"error": f"HTTP {e.code}: {body[:200]}"}
        except Exception as e:
            return {"error": str(e)}

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "default_model": self.config.default_model,
            "fallbacks": len(self.config.fallback_models),
            "requests": self._request_count,
            "last_error": self._last_error,
        }


def demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS  |  OPENCLAW / OPENROUTER")
    print("=" * 60)
    claw = OpenClaw()
    print(f"Stats: {claw.stats}")
    print("Usage: claw.chat('question', model='anthropic/claude-3-haiku')")
    print("Set OPENCLAW_API_KEY or OPENROUTER_API_KEY env var")
    print("=" * 60)


if __name__ == "__main__":
    demo()

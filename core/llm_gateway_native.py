"""
llm_gateway_native.py
MAGNATRIX-OS — LLM Gateway

Inspired by OmniRoute: One endpoint, 160+ providers, smart routing. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class ProviderConfig:
    provider_id: str
    name: str
    base_url: str
    models: List[str]
    is_free: bool
    rate_limit_rpm: int
    api_key_required: bool
    is_active: bool = True


class LLMGateway:
    """Multi-provider LLM gateway with unified routing."""

    BUILT_IN_PROVIDERS = {
        "openai": {"name": "OpenAI", "base_url": "https://api.openai.com/v1", "models": ["gpt-4o", "gpt-4o-mini"], "is_free": False, "rate_limit_rpm": 60, "api_key_required": True},
        "anthropic": {"name": "Anthropic", "base_url": "https://api.anthropic.com", "models": ["claude-3-5-sonnet", "claude-3-haiku"], "is_free": False, "rate_limit_rpm": 40, "api_key_required": True},
        "google": {"name": "Google Gemini", "base_url": "https://generativelanguage.googleapis.com", "models": ["gemini-1.5-pro", "gemini-1.5-flash"], "is_free": True, "rate_limit_rpm": 60, "api_key_required": True},
        "groq": {"name": "Groq", "base_url": "https://api.groq.com", "models": ["llama-3.1-70b", "mixtral-8x7b"], "is_free": True, "rate_limit_rpm": 30, "api_key_required": True},
        "mistral": {"name": "Mistral", "base_url": "https://api.mistral.ai", "models": ["mistral-large", "mistral-medium"], "is_free": True, "rate_limit_rpm": 30, "api_key_required": True},
        "deepseek": {"name": "DeepSeek", "base_url": "https://api.deepseek.com", "models": ["deepseek-chat", "deepseek-coder"], "is_free": True, "rate_limit_rpm": 30, "api_key_required": True},
        "openrouter": {"name": "OpenRouter", "base_url": "https://openrouter.ai/api/v1", "models": ["*"], "is_free": True, "rate_limit_rpm": 20, "api_key_required": True},
        "huggingface": {"name": "Hugging Face", "base_url": "https://api-inference.huggingface.co", "models": ["*"], "is_free": True, "rate_limit_rpm": 20, "api_key_required": True},
    }

    def __init__(self, cache_dir: str = "./llm_gateway"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.providers: Dict[str, ProviderConfig] = {}
        self.request_log: List[Dict[str, Any]] = []
        self._load()
        self._init_builtin()

    def _init_builtin(self) -> None:
        for pid, info in self.BUILT_IN_PROVIDERS.items():
            if pid not in self.providers:
                self.providers[pid] = ProviderConfig(provider_id=pid, **info)

    def _load(self) -> None:
        file = self.cache_dir / "providers.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for pid, pd in data.items():
                        self.providers[pid] = ProviderConfig(**pd)
            except Exception:
                pass
        log = self.cache_dir / "log.json"
        if log.exists():
            try:
                with open(log, "r", encoding="utf-8") as f:
                    self.request_log = json.load(f)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "providers.json", "w", encoding="utf-8") as f:
            json.dump({pid: asdict(p) for pid, p in self.providers.items()}, f, indent=2)
        with open(self.cache_dir / "log.json", "w", encoding="utf-8") as f:
            json.dump(self.request_log, f, indent=2)

    def add_provider(self, provider_id: str, name: str, base_url: str, models: List[str],
                     is_free: bool, rate_limit_rpm: int, api_key_required: bool) -> ProviderConfig:
        p = ProviderConfig(
            provider_id=provider_id, name=name, base_url=base_url, models=models,
            is_free=is_free, rate_limit_rpm=rate_limit_rpm, api_key_required=api_key_required,
        )
        self.providers[provider_id] = p
        self._save()
        return p

    def route(self, model: str, prefer_free: bool = True) -> Optional[ProviderConfig]:
        """Route a request to the best provider for a model."""
        candidates = []
        for p in self.providers.values():
            if not p.is_active:
                continue
            if model in p.models or "*" in p.models:
                if prefer_free and p.is_free:
                    candidates.append(p)
                elif not prefer_free:
                    candidates.append(p)
        if not candidates and prefer_free:
            # Fallback to any provider
            for p in self.providers.values():
                if p.is_active and (model in p.models or "*" in p.models):
                    candidates.append(p)
        if not candidates:
            return None
        # Sort by rate limit (higher = better)
        candidates.sort(key=lambda x: x.rate_limit_rpm, reverse=True)
        return candidates[0]

    def get_free_providers(self) -> List[ProviderConfig]:
        return [p for p in self.providers.values() if p.is_free and p.is_active]

    def get_stats(self) -> Dict[str, Any]:
        free = sum(1 for p in self.providers.values() if p.is_free)
        active = sum(1 for p in self.providers.values() if p.is_active)
        return {"total": len(self.providers), "free": free, "active": active, "paid": len(self.providers) - free}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["LLMGateway", "ProviderConfig"]
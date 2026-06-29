"""
free_api_key_hunter_native.py
MAGNATRIX-OS — Free API Key Hunter

Hunt and track free LLM API keys, tiers, and trial credits. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta


@dataclass
class FreeKey:
    key_id: str
    provider: str
    tier: str
    key_preview: str
    monthly_limit: int
    used_this_month: int
    remaining: int
    expires_at: str
    is_active: bool = True
    last_used: str = ""

    def __post_init__(self):
        if not self.last_used:
            self.last_used = datetime.now().isoformat()


class FreeAPIKeyHunter:
    """Hunt and track free LLM API keys and trial credits."""

    FREE_TIERS = {
        "google_gemini": {"provider": "Google", "tier": "Free", "monthly_limit": 1500, "url": "https://ai.google.dev/"},
        "groq": {"provider": "Groq", "tier": "Free", "monthly_limit": 10000, "url": "https://console.groq.com/"},
        "mistral": {"provider": "Mistral", "tier": "Free", "monthly_limit": 1000, "url": "https://console.mistral.ai/"},
        "openrouter": {"provider": "OpenRouter", "tier": "Free", "monthly_limit": 2000, "url": "https://openrouter.ai/"},
        "huggingface": {"provider": "HuggingFace", "tier": "Free", "monthly_limit": 1000, "url": "https://huggingface.co/"},
        "deepseek": {"provider": "DeepSeek", "tier": "Free", "monthly_limit": 500, "url": "https://platform.deepseek.com/"},
        "cohere": {"provider": "Cohere", "tier": "Trial", "monthly_limit": 1000, "url": "https://cohere.com/"},
        "ai21": {"provider": "AI21", "tier": "Trial", "monthly_limit": 1000, "url": "https://studio.ai21.com/"},
        "nvidia_nim": {"provider": "NVIDIA NIM", "tier": "Free", "monthly_limit": 5000, "url": "https://build.nvidia.com/"},
        "octoai": {"provider": "OctoAI", "tier": "Free", "monthly_limit": 1000, "url": "https://octoai.cloud/"},
        "together": {"provider": "Together", "tier": "Free", "monthly_limit": 1000, "url": "https://api.together.xyz/"},
        "fireworks": {"provider": "Fireworks", "tier": "Trial", "monthly_limit": 500, "url": "https://fireworks.ai/"},
    }

    def __init__(self, vault_dir: str = "./free_key_vault"):
        self.vault_dir = Path(vault_dir)
        self.vault_dir.mkdir(exist_ok=True)
        self.keys: Dict[str, FreeKey] = {}
        self.opportunities: Dict[str, Dict[str, Any]] = dict(self.FREE_TIERS)
        self._load()

    def _load(self) -> None:
        file = self.vault_dir / "keys.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for kid, kd in data.items():
                        self.keys[kid] = FreeKey(**kd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.vault_dir / "keys.json", "w", encoding="utf-8") as f:
            json.dump({kid: asdict(k) for kid, k in self.keys.items()}, f, indent=2)

    def register_key(self, key_id: str, provider: str, tier: str, key_preview: str,
                     monthly_limit: int, expires_at: str) -> FreeKey:
        key = FreeKey(
            key_id=key_id, provider=provider, tier=tier, key_preview=key_preview,
            monthly_limit=monthly_limit, used_this_month=0,
            remaining=monthly_limit, expires_at=expires_at,
        )
        self.keys[key_id] = key
        self._save()
        return key

    def use_key(self, key_id: str, tokens: int = 1) -> bool:
        key = self.keys.get(key_id)
        if not key or not key.is_active or key.remaining <= 0:
            return False
        key.used_this_month += tokens
        key.remaining = max(0, key.monthly_limit - key.used_this_month)
        key.last_used = datetime.now().isoformat()
        if key.remaining <= 0:
            key.is_active = False
        self._save()
        return True

    def get_available_keys(self) -> List[FreeKey]:
        return [k for k in self.keys.values() if k.is_active and k.remaining > 0]

    def get_hunt_list(self) -> List[Dict[str, Any]]:
        """List providers to hunt for free keys."""
        return [
            {"provider": info["provider"], "tier": info["tier"], "monthly_limit": info["monthly_limit"], "url": info["url"]}
            for pid, info in self.opportunities.items()
        ]

    def get_stats(self) -> Dict[str, Any]:
        available = len(self.get_available_keys())
        total_limit = sum(k.monthly_limit for k in self.keys.values())
        total_used = sum(k.used_this_month for k in self.keys.values())
        return {
            "total_keys": len(self.keys), "available": available, "exhausted": len(self.keys) - available,
            "total_limit": total_limit, "total_used": total_used, "total_remaining": total_limit - total_used,
            "hunt_targets": len(self.opportunities),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["FreeAPIKeyHunter", "FreeKey"]
"""
provider_fallback_native.py
MAGNATRIX-OS — Provider Fallback Engine

Inspired by OmniRoute: Smart auto-fallback when a provider fails or hits rate limits. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class FallbackEvent:
    event_id: str
    original_provider: str
    fallback_provider: str
    reason: str
    model: str
    success: bool
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class ProviderFallbackEngine:
    """Smart auto-fallback when providers fail or hit rate limits."""

    def __init__(self, cache_dir: str = "./fallback_log"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.fallback_chains: Dict[str, List[str]] = {}
        self.events: List[FallbackEvent] = []
        self.provider_health: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        for fname in ["chains.json", "events.json", "health.json"]:
            f = self.cache_dir / fname
            if f.exists():
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        if fname == "chains.json":
                            self.fallback_chains = data
                        elif fname == "events.json":
                            self.events = [FallbackEvent(**e) for e in data]
                        else:
                            self.provider_health = data
                except Exception:
                    pass

    def _save(self) -> None:
        with open(self.cache_dir / "chains.json", "w", encoding="utf-8") as f:
            json.dump(self.fallback_chains, f, indent=2)
        with open(self.cache_dir / "events.json", "w", encoding="utf-8") as f:
            json.dump([asdict(e) for e in self.events], f, indent=2)
        with open(self.cache_dir / "health.json", "w", encoding="utf-8") as f:
            json.dump(self.provider_health, f, indent=2)

    def set_chain(self, model: str, providers: List[str]) -> None:
        """Set fallback chain for a model."""
        self.fallback_chains[model] = providers
        self._save()

    def fallback(self, event_id: str, model: str, original_provider: str,
                 reason: str, available_providers: List[str]) -> Optional[FallbackEvent]:
        """Find next provider in fallback chain."""
        chain = self.fallback_chains.get(model, [])
        # Mark original provider as unhealthy
        self.provider_health[original_provider] = {"status": "degraded", "last_error": reason, "time": datetime.now().isoformat()}

        # Find next available provider in chain
        fallback = None
        for p in chain:
            if p != original_provider and p in available_providers:
                fallback = p
                break

        if not fallback and available_providers:
            # Fallback to any available provider not the original
            for p in available_providers:
                if p != original_provider:
                    fallback = p
                    break

        event = FallbackEvent(
            event_id=event_id, original_provider=original_provider,
            fallback_provider=fallback or "none", reason=reason, model=model,
            success=fallback is not None,
        )
        self.events.append(event)
        self._save()
        return event

    def mark_healthy(self, provider: str) -> None:
        self.provider_health[provider] = {"status": "healthy", "last_error": "", "time": datetime.now().isoformat()}
        self._save()

    def get_chain(self, model: str) -> List[str]:
        return self.fallback_chains.get(model, [])

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.events)
        successful = sum(1 for e in self.events if e.success)
        return {"total_fallbacks": total, "successful": successful, "failed": total - successful, "chains": len(self.fallback_chains)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["ProviderFallbackEngine", "FallbackEvent"]
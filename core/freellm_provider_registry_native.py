"""Free LLM Provider Registry -- Directory of 40+ free LLM API providers."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class ProviderEntry:
    provider_id: str = ""
    name: str = ""
    base_url: str = ""
    free_tier: bool = True
    requires_card: bool = False
    requires_phone: bool = False
    signup_url: str = ""
    docs_url: str = ""
    status: str = "active"
    last_checked: str = ""

class FreellmProviderRegistry:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._providers: dict[str, ProviderEntry] = {}
        self._persist_path = self.root / "freellm_providers.json"
        self._load()
        if not self._providers:
            self._seed_defaults()

    def _seed_defaults(self) -> None:
        defaults = [
            ProviderEntry("google", "Google Gemini", "https://generativelanguage.googleapis.com", True, False, True, "https://ai.google.dev/", "https://ai.google.dev/gemini-api/docs", "active"),
            ProviderEntry("groq", "Groq", "https://api.groq.com/openai/v1", True, False, False, "https://console.groq.com/", "https://console.groq.com/docs", "active"),
            ProviderEntry("nvidia", "NVIDIA NIM", "https://integrate.api.nvidia.com/v1", True, False, False, "https://build.nvidia.com/", "https://docs.nvidia.com/nim/large-language-models/latest/index.html", "active"),
            ProviderEntry("openrouter", "OpenRouter", "https://openrouter.ai/api/v1", True, False, False, "https://openrouter.ai/", "https://openrouter.ai/docs", "active"),
            ProviderEntry("cerebras", "Cerebras", "https://api.cerebras.ai/v1", True, False, False, "https://cloud.cerebras.ai/", "https://inference-docs.cerebras.ai/", "active"),
            ProviderEntry("samba", "SambaNova", "https://fast-api.snova.ai/v1", True, False, False, "https://cloud.sambanova.ai/", "https://docs.sambanova.ai/", "active"),
            ProviderEntry("together", "Together AI", "https://api.together.xyz/v1", True, False, False, "https://api.together.xyz/", "https://docs.together.ai/", "active"),
            ProviderEntry("deepinfra", "DeepInfra", "https://api.deepinfra.com/v1/openai", True, False, False, "https://deepinfra.com/", "https://deepinfra.com/docs", "active"),
        ]
        for p in defaults:
            self._providers[p.provider_id] = p
        self._save()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._providers = {k: ProviderEntry(**v) for k, v in data.get("providers", {}).items()}

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "providers": {k: v.__dict__ for k, v in self._providers.items()}
        }, indent=2))

    def add(self, provider: ProviderEntry) -> None:
        self._providers[provider.provider_id] = provider
        self._save()

    def get(self, provider_id: str) -> ProviderEntry | None:
        return self._providers.get(provider_id)

    def list_active(self) -> list[ProviderEntry]:
        return [p for p in self._providers.values() if p.status == "active"]

    def list_free(self) -> list[ProviderEntry]:
        return [p for p in self._providers.values() if p.free_tier]

    def list_no_card(self) -> list[ProviderEntry]:
        return [p for p in self._providers.values() if not p.requires_card]

    def update_status(self, provider_id: str, status: str) -> bool:
        p = self._providers.get(provider_id)
        if p:
            p.status = status
            self._save()
            return True
        return False

    def to_dict(self) -> dict:
        return {"provider_count": len(self._providers), "active": len(self.list_active()), "free": len(self.list_free())}

    def get_stats(self) -> dict:
        by_status = {}
        by_card = {"no_card": 0, "requires_card": 0}
        for p in self._providers.values():
            by_status[p.status] = by_status.get(p.status, 0) + 1
            if p.requires_card:
                by_card["requires_card"] += 1
            else:
                by_card["no_card"] += 1
        return {"total": len(self._providers), "by_status": by_status, "by_card": by_card}

__all__ = ["FreellmProviderRegistry", "ProviderEntry"]

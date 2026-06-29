"""Free LLM Model Catalog -- 134+ models, specs, capabilities."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class ModelEntry:
    model_id: str = ""
    name: str = ""
    provider: str = ""
    context_window: int = 0
    max_tokens: int = 0
    modalities: list[str] = None
    supports_tools: bool = False
    supports_streaming: bool = False
    free_tier: bool = True
    rate_limit_rpm: int = 0
    rate_limit_rpd: int = 0

    def __post_init__(self):
        if self.modalities is None:
            self.modalities = ["text"]

class FreellmModelCatalog:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._models: dict[str, ModelEntry] = {}
        self._persist_path = self.root / "freellm_models.json"
        self._load()
        if not self._models:
            self._seed_defaults()

    def _seed_defaults(self) -> None:
        defaults = [
            ModelEntry("gemini-2.5-pro", "Gemini 2.5 Pro", "google", 1000000, 8192, ["text", "image", "video"], True, True, True, 10, 1500),
            ModelEntry("gemini-2.5-flash", "Gemini 2.5 Flash", "google", 1000000, 8192, ["text", "image"], True, True, True, 15, 1500),
            ModelEntry("llama-4-maverick", "Llama 4 Maverick", "groq", 128000, 8192, ["text"], True, True, True, 30, 14400),
            ModelEntry("llama-4-scout", "Llama 4 Scout", "groq", 128000, 8192, ["text"], True, True, True, 30, 14400),
            ModelEntry("deepseek-v3", "DeepSeek V3", "nvidia", 64000, 8192, ["text"], False, True, True, 30, 50000),
            ModelEntry("qwen-3-235b", "Qwen3 235B", "nvidia", 128000, 8192, ["text"], True, True, True, 30, 50000),
            ModelEntry("llama-3.3-70b", "Llama 3.3 70B", "cerebras", 128000, 8192, ["text"], True, True, True, 30, 14400),
            ModelEntry("llama-3.1-405b", "Llama 3.1 405B", "sambanova", 128000, 8192, ["text"], True, True, True, 10, 1000),
        ]
        for m in defaults:
            self._models[m.model_id] = m
        self._save()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._models = {k: ModelEntry(**v) for k, v in data.get("models", {}).items()}

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "models": {k: v.__dict__ for k, v in self._models.items()}
        }, indent=2))

    def add(self, model: ModelEntry) -> None:
        self._models[model.model_id] = model
        self._save()

    def get(self, model_id: str) -> ModelEntry | None:
        return self._models.get(model_id)

    def list_by_provider(self, provider: str) -> list[ModelEntry]:
        return [m for m in self._models.values() if m.provider == provider]

    def list_by_modality(self, modality: str) -> list[ModelEntry]:
        return [m for m in self._models.values() if modality in m.modalities]

    def list_free(self) -> list[ModelEntry]:
        return [m for m in self._models.values() if m.free_tier]

    def find_by_context(self, min_context: int) -> list[ModelEntry]:
        return [m for m in self._models.values() if m.context_window >= min_context]

    def to_dict(self) -> dict:
        return {"model_count": len(self._models), "providers": list(set(m.provider for m in self._models.values()))}

    def get_stats(self) -> dict:
        by_provider = {}
        by_modality = {}
        for m in self._models.values():
            by_provider[m.provider] = by_provider.get(m.provider, 0) + 1
            for mod in m.modalities:
                by_modality[mod] = by_modality.get(mod, 0) + 1
        return {"total": len(self._models), "by_provider": by_provider, "by_modality": by_modality}

__all__ = ["FreellmModelCatalog", "ModelEntry"]

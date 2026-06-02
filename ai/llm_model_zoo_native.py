"""Model Zoo — Model registry, download manager, and version management.

Modul ini menyediakan:
- ModelRegistry untuk register models dengan metadata
- ModelDownloader untuk download dan cache models
- ModelVersionManager untuk version management
- ModelValidator untuk validate model integrity
- ModelZoo untuk end-to-end model management
"""

from __future__ import annotations

import json
import time
import uuid
import hashlib
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class ModelFormat(Enum):
    PYTORCH = "pytorch"
    ONNX = "onnx"
    TENSORFLOW = "tensorflow"
    JAX = "jax"
    GGML = "ggml"
    GGUF = "gguf"
    SAFETENSORS = "safetensors"


class ModelStatus(Enum):
    AVAILABLE = auto()
    DOWNLOADING = auto()
    CACHED = auto()
    LOADING = auto()
    LOADED = auto()
    ERROR = auto()


@dataclass
class ModelInfo:
    """Model metadata."""
    model_id: str
    name: str
    version: str
    format: ModelFormat
    size_mb: float
    url: str = ""
    checksum: str = ""
    description: str = ""
    capabilities: Set[str] = field(default_factory=set)
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: ModelStatus = ModelStatus.AVAILABLE
    downloaded_at: Optional[float] = None
    loaded_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "name": self.name,
            "version": self.version,
            "format": self.format.value,
            "size_mb": self.size_mb,
            "status": self.status.name,
            "capabilities": list(self.capabilities),
        }


class ModelRegistry:
    """Register and manage models."""

    def __init__(self):
        self._models: Dict[str, ModelInfo] = {}
        self._by_name: Dict[str, List[str]] = {}  # name -> list of model_ids
        self._by_capability: Dict[str, List[str]] = {}  # capability -> list of model_ids

    def register(self, model: ModelInfo) -> None:
        self._models[model.model_id] = model
        self._by_name.setdefault(model.name, []).append(model.model_id)
        for cap in model.capabilities:
            self._by_capability.setdefault(cap, []).append(model.model_id)

    def get(self, model_id: str) -> Optional[ModelInfo]:
        return self._models.get(model_id)

    def get_by_name(self, name: str) -> List[ModelInfo]:
        return [self._models[mid] for mid in self._by_name.get(name, []) if mid in self._models]

    def find_by_capability(self, capability: str) -> List[ModelInfo]:
        return [self._models[mid] for mid in self._by_capability.get(capability, []) if mid in self._models]

    def list_all(self) -> List[ModelInfo]:
        return list(self._models.values())

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._models)
        cached = sum(1 for m in self._models.values() if m.status == ModelStatus.CACHED)
        loaded = sum(1 for m in self._models.values() if m.status == ModelStatus.LOADED)
        total_size = sum(m.size_mb for m in self._models.values())
        return {
            "total": total,
            "cached": cached,
            "loaded": loaded,
            "total_size_mb": round(total_size, 2),
            "by_format": {f.value: sum(1 for m in self._models.values() if m.format == f) for f in ModelFormat},
        }


class ModelDownloader:
    """Download and cache models."""

    def __init__(self, cache_dir: str = "./model_cache"):
        self.cache_dir = cache_dir
        self._cache: Dict[str, str] = {}  # model_id -> cache_path
        self._downloads: Dict[str, Dict[str, Any]] = {}

    def download(self, model: ModelInfo, download_fn: Optional[Callable[[ModelInfo], Tuple[bool, str]]] = None) -> Tuple[bool, str]:
        download_fn = download_fn or self._default_download
        model.status = ModelStatus.DOWNLOADING
        success, path = download_fn(model)
        if success:
            model.status = ModelStatus.CACHED
            model.downloaded_at = time.time()
            self._cache[model.model_id] = path
        else:
            model.status = ModelStatus.ERROR
        return success, path

    def _default_download(self, model: ModelInfo) -> Tuple[bool, str]:
        # Simulated download
        time.sleep(0.01)
        path = f"{self.cache_dir}/{model.model_id}.bin"
        return True, path

    def get_cache_path(self, model_id: str) -> Optional[str]:
        return self._cache.get(model_id)

    def is_cached(self, model_id: str) -> bool:
        return model_id in self._cache

    def clear_cache(self, model_id: Optional[str] = None) -> None:
        if model_id:
            self._cache.pop(model_id, None)
        else:
            self._cache.clear()


class ModelVersionManager:
    """Manage model versions."""

    def __init__(self):
        self._versions: Dict[str, List[ModelInfo]] = {}  # name -> list of versions

    def add_version(self, model: ModelInfo) -> None:
        self._versions.setdefault(model.name, []).append(model)
        # Sort by version
        self._versions[model.name].sort(key=lambda m: m.version)

    def get_latest(self, name: str) -> Optional[ModelInfo]:
        versions = self._versions.get(name, [])
        return versions[-1] if versions else None

    def get_version(self, name: str, version: str) -> Optional[ModelInfo]:
        for m in self._versions.get(name, []):
            if m.version == version:
                return m
        return None

    def list_versions(self, name: str) -> List[ModelInfo]:
        return self._versions.get(name, [])

    def compare(self, name: str, v1: str, v2: str) -> Dict[str, Any]:
        m1 = self.get_version(name, v1)
        m2 = self.get_version(name, v2)
        if not m1 or not m2:
            return {"error": "Version not found"}
        return {
            "v1": v1,
            "v2": v2,
            "size_diff_mb": round(m2.size_mb - m1.size_mb, 2),
            "capabilities_added": list(m2.capabilities - m1.capabilities),
            "capabilities_removed": list(m1.capabilities - m2.capabilities),
        }


class ModelValidator:
    """Validate model integrity."""

    def __init__(self):
        self._validators: Dict[ModelFormat, Callable[[str], bool]] = {}

    def validate(self, model: ModelInfo, path: str) -> Tuple[bool, str]:
        # Check checksum
        if model.checksum:
            actual = self._compute_checksum(path)
            if actual != model.checksum:
                return False, f"Checksum mismatch: expected {model.checksum}, got {actual}"
        # Check size
        # Simulated: always valid
        return True, "Valid"

    def _compute_checksum(self, path: str) -> str:
        # Simulated checksum
        return hashlib.sha256(path.encode()).hexdigest()[:16]

    def add_validator(self, fmt: ModelFormat, validator: Callable[[str], bool]) -> None:
        self._validators[fmt] = validator


class ModelZoo:
    """End-to-end model management."""

    def __init__(self, cache_dir: str = "./model_cache"):
        self.registry = ModelRegistry()
        self.downloader = ModelDownloader(cache_dir)
        self.version_manager = ModelVersionManager()
        self.validator = ModelValidator()
        self._loaded_models: Dict[str, Any] = {}

    def add_model(self, name: str, version: str, fmt: ModelFormat, size_mb: float,
                  url: str = "", checksum: str = "", capabilities: Optional[Set[str]] = None,
                  description: str = "") -> ModelInfo:
        model = ModelInfo(
            model_id=str(uuid.uuid4())[:12],
            name=name,
            version=version,
            format=fmt,
            size_mb=size_mb,
            url=url,
            checksum=checksum,
            capabilities=capabilities or set(),
            description=description,
        )
        self.registry.register(model)
        self.version_manager.add_version(model)
        return model

    def download(self, model_id: str) -> Tuple[bool, str]:
        model = self.registry.get(model_id)
        if not model:
            return False, "Model not found"
        return self.downloader.download(model)

    def load(self, model_id: str, loader_fn: Optional[Callable[[ModelInfo, str], Any]] = None) -> Any:
        model = self.registry.get(model_id)
        if not model:
            return None
        path = self.downloader.get_cache_path(model_id)
        if not path:
            return None
        model.status = ModelStatus.LOADING
        loader_fn = loader_fn or self._default_loader
        loaded = loader_fn(model, path)
        self._loaded_models[model_id] = loaded
        model.status = ModelStatus.LOADED
        model.loaded_at = time.time()
        return loaded

    def _default_loader(self, model: ModelInfo, path: str) -> Any:
        return {"model_id": model.model_id, "path": path, "status": "loaded"}

    def unload(self, model_id: str) -> bool:
        if model_id in self._loaded_models:
            del self._loaded_models[model_id]
            model = self.registry.get(model_id)
            if model:
                model.status = ModelStatus.CACHED
            return True
        return False

    def get_latest(self, name: str) -> Optional[ModelInfo]:
        return self.version_manager.get_latest(name)

    def find_for_task(self, capability: str) -> List[ModelInfo]:
        return self.registry.find_by_capability(capability)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "registry": self.registry.get_stats(),
            "loaded": len(self._loaded_models),
            "cached": len(self.downloader._cache),
        }

    def export_catalog(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "models": [m.to_dict() for m in self.registry.list_all()],
                "stats": self.get_stats(),
            }, f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("MODEL ZOO DEMO")
    print("=" * 70)

    # 1. Add models
    print("\n[1] Add Models")
    zoo = ModelZoo()
    zoo.add_model("llama-3-8b", "3.1", ModelFormat.GGUF, 4800,
                  url="https://models.gguf/llama-3-8b", capabilities={"chat", "reasoning"},
                  description="Meta Llama 3 8B")
    zoo.add_model("llama-3-70b", "3.1", ModelFormat.GGUF, 40000,
                  url="https://models.gguf/llama-3-70b", capabilities={"chat", "reasoning", "coding"},
                  description="Meta Llama 3 70B")
    zoo.add_model("mistral-7b", "0.3", ModelFormat.SAFETENSORS, 14000,
                  capabilities={"chat", "analysis"}, description="Mistral 7B")
    zoo.add_model("qwen-2.5-7b", "2.5", ModelFormat.GGUF, 4500,
                  capabilities={"chat", "multilingual", "coding"}, description="Qwen 2.5 7B")
    print(f"  Models registered: {len(zoo.registry.list_all())}")
    for m in zoo.registry.list_all():
        print(f"    {m.name} v{m.version}: {m.format.value}, {m.size_mb}MB, caps={m.capabilities}")

    # 2. Download
    print("\n[2] Download Models")
    for m in zoo.registry.list_all():
        success, path = zoo.download(m.model_id)
        print(f"    {m.name}: {'OK' if success else 'FAIL'} -> {path}")

    # 3. Load
    print("\n[3] Load Models")
    for m in zoo.registry.list_all()[:2]:
        loaded = zoo.load(m.model_id)
        print(f"    {m.name}: loaded={loaded is not None}")

    # 4. Find by capability
    print("\n[4] Find by Capability")
    coding_models = zoo.find_for_task("coding")
    print(f"  Coding models: {[m.name for m in coding_models]}")
    chat_models = zoo.find_for_task("chat")
    print(f"  Chat models: {len(chat_models)}")

    # 5. Version management
    print("\n[5] Version Management")
    zoo.add_model("llama-3-8b", "3.2", ModelFormat.GGUF, 4900,
                  capabilities={"chat", "reasoning", "vision"})
    latest = zoo.get_latest("llama-3-8b")
    print(f"  Latest llama-3-8b: v{latest.version}, caps={latest.capabilities}")
    versions = zoo.version_manager.list_versions("llama-3-8b")
    print(f"  All versions: {[v.version for v in versions]}")
    comparison = zoo.version_manager.compare("llama-3-8b", "3.1", "3.2")
    print(f"  Comparison: {comparison}")

    # 6. Stats
    print(f"\n[6] Stats")
    print(f"  {zoo.get_stats()}")

    # 7. Export
    print("\n[7] Export Catalog")
    zoo.export_catalog("/tmp/model_catalog.json")
    print("  Exported to /tmp/model_catalog.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()

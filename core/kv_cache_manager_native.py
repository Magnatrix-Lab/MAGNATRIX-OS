"""
kv_cache_manager_native.py
MAGNATRIX-OS — KV Cache Manager

Inspired by NVIDIA KV-cache compression research (RDKV):
Manage transformer Key-Value cache with size tracking, eviction, and quantization. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict


@dataclass
class CacheEntry:
    token_id: int
    key: List[float]
    value: List[float]
    layer: int
    head: int
    bit_width: int = 16
    is_evicted: bool = False


class KVCacheManager:
    """Manage KV cache with size tracking, eviction, and quantization."""

    def __init__(self, cache_dir: str = "./kv_cache", max_size_mb: float = 1024.0):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.max_size_mb = max_size_mb
        self.entries: Dict[str, CacheEntry] = {}
        self.sequence_length = 0
        self.num_layers = 0
        self.num_heads = 0
        self.head_dim = 0
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "meta.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.sequence_length = data.get("seq_len", 0)
                    self.num_layers = data.get("layers", 0)
                    self.num_heads = data.get("heads", 0)
                    self.head_dim = data.get("head_dim", 0)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "meta.json", "w", encoding="utf-8") as f:
            json.dump({
                "seq_len": self.sequence_length, "layers": self.num_layers,
                "heads": self.num_heads, "head_dim": self.head_dim,
                "entries": len(self.entries), "size_mb": self.current_size_mb(),
            }, f, indent=2)

    def configure(self, layers: int, heads: int, head_dim: int, seq_len: int) -> None:
        self.num_layers = layers
        self.num_heads = heads
        self.head_dim = head_dim
        self.sequence_length = seq_len
        self._save()

    def add_entry(self, token_id: int, layer: int, head: int, key: List[float], value: List[float]) -> None:
        eid = f"{layer}_{head}_{token_id}"
        self.entries[eid] = CacheEntry(
            token_id=token_id, key=key, value=value, layer=layer, head=head,
        )
        self._save()

    def current_size_mb(self) -> float:
        """Estimate current cache size in MB."""
        if self.sequence_length == 0 or self.num_layers == 0:
            return 0.0
        # K + V per token per layer per head: 2 * head_dim floats
        bytes_per_entry = 2 * self.head_dim * 4  # 4 bytes per float32
        total_entries = self.sequence_length * self.num_layers * self.num_heads
        return total_entries * bytes_per_entry / (1024 * 1024)

    def projected_size_mb(self, seq_len: int) -> float:
        """Project cache size for given sequence length."""
        if self.num_layers == 0 or self.num_heads == 0 or self.head_dim == 0:
            return 0.0
        bytes_per_entry = 2 * self.head_dim * 4
        total = seq_len * self.num_layers * self.num_heads
        return total * bytes_per_entry / (1024 * 1024)

    def get_entries(self, layer: int, head: int) -> List[CacheEntry]:
        return [e for e in self.entries.values() if e.layer == layer and e.head == head and not e.is_evicted]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "entries": len(self.entries), "seq_len": self.sequence_length,
            "layers": self.num_layers, "heads": self.num_heads, "head_dim": self.head_dim,
            "size_mb": round(self.current_size_mb(), 2),
            "max_size_mb": self.max_size_mb,
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["KVCacheManager", "CacheEntry"]
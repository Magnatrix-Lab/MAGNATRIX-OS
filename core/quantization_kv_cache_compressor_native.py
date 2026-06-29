"""KV Cache Compressor — Per-head quantization, dynamic precision."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class KVCacheBlock:
    layer_id: int = 0
    head_id: int = 0
    seq_len: int = 0
    kv_pairs: list[dict] = None
    precision: str = "fp16"  # fp16 | int8 | int4

    def __post_init__(self):
        if self.kv_pairs is None:
            self.kv_pairs = []

class QuantizationKVCacheCompressor:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._blocks: list[KVCacheBlock] = []
        self._config = {"default_precision": "fp16", "dynamic": True, "threshold_seq": 1024}
        self._persist_path = self.root / "kv_cache.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._blocks = [KVCacheBlock(**b) for b in data.get("blocks", [])]
            self._config = data.get("config", self._config)

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "blocks": [b.__dict__ for b in self._blocks],
            "config": self._config
        }, indent=2))

    def add_block(self, layer_id: int, head_id: int, kv_pairs: list[dict]) -> KVCacheBlock:
        block = KVCacheBlock(layer_id=layer_id, head_id=head_id, seq_len=len(kv_pairs), kv_pairs=kv_pairs)
        if self._config["dynamic"] and block.seq_len > self._config["threshold_seq"]:
            block.precision = "int8"
        self._blocks.append(block)
        self._save()
        return block

    def compress_block(self, block: KVCacheBlock, target_precision: str) -> KVCacheBlock:
        if target_precision == "int8":
            # Simulate int8 quantization of K/V tensors
            for pair in block.kv_pairs:
                k = pair.get("k", 0.0)
                v = pair.get("v", 0.0)
                pair["k"] = max(-128, min(127, int(k * 100))) / 100.0
                pair["v"] = max(-128, min(127, int(v * 100))) / 100.0
        elif target_precision == "int4":
            for pair in block.kv_pairs:
                k = pair.get("k", 0.0)
                v = pair.get("v", 0.0)
                pair["k"] = max(-8, min(7, int(k * 10))) / 10.0
                pair["v"] = max(-8, min(7, int(v * 10))) / 10.0
        block.precision = target_precision
        self._save()
        return block

    def compress_all(self, target_precision: str) -> None:
        for block in self._blocks:
            self.compress_block(block, target_precision)

    def evict_oldest(self, layer_id: int, head_id: int, keep: int) -> None:
        for block in self._blocks:
            if block.layer_id == layer_id and block.head_id == head_id:
                block.kv_pairs = block.kv_pairs[-keep:]
                block.seq_len = len(block.kv_pairs)
        self._save()

    def to_dict(self) -> dict:
        return {"block_count": len(self._blocks), "precision_dist": {p: sum(1 for b in self._blocks if b.precision == p) for p in set(b.precision for b in self._blocks)}}

    def get_stats(self) -> dict:
        return {"blocks": len(self._blocks), "total_seq": sum(b.seq_len for b in self._blocks), "precision_dist": {p: sum(1 for b in self._blocks if b.precision == p) for p in set(b.precision for b in self._blocks)}}

__all__ = ["QuantizationKVCacheCompressor", "KVCacheBlock"]

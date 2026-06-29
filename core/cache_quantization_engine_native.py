"""
cache_quantization_engine_native.py
MAGNATRIX-OS — Cache Quantization Engine

Inspired by NVIDIA KV-cache compression (KIVI, KVQuant, ZipCache):
Quantize KV cache entries to reduced bit-widths. Pure stdlib.
"""

import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict


@dataclass
class QuantizedEntry:
    token_id: int
    layer: int
    head: int
    bit_width: int
    quantized_key: List[int]
    quantized_value: List[int]
    scale_key: float
    zero_point_key: float
    scale_value: float
    zero_point_value: float


class CacheQuantizationEngine:
    """Quantize KV cache entries to reduced bit-widths."""

    SUPPORTED_BITS = [2, 4, 8, 16]

    def __init__(self, cache_dir: str = "./quantized_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.entries: Dict[str, QuantizedEntry] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "quantized.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for eid, ed in data.items():
                        self.entries[eid] = QuantizedEntry(**ed)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "quantized.json", "w", encoding="utf-8") as f:
            json.dump({eid: asdict(e) for eid, e in self.entries.items()}, f, indent=2)

    def _compute_scale(self, values: List[float], bit_width: int) -> Tuple[float, float]:
        if not values or bit_width not in self.SUPPORTED_BITS:
            return 1.0, 0.0
        max_val = max(values)
        min_val = min(values)
        range_val = max_val - min_val
        if range_val == 0:
            return 1.0, min_val
        num_levels = 2 ** bit_width - 1
        scale = range_val / num_levels
        zero_point = -min_val / scale
        return scale, zero_point

    def _quantize(self, values: List[float], bit_width: int) -> Tuple[List[int], float, float]:
        scale, zp = self._compute_scale(values, bit_width)
        if scale == 0:
            return [0] * len(values), scale, zp
        quantized = [max(0, min(2 ** bit_width - 1, int(round((v - (-zp * scale)) / scale)))) for v in values]
        return quantized, scale, zp

    def _dequantize(self, quantized: List[int], scale: float, zero_point: float) -> List[float]:
        return [scale * (q - zero_point) for q in quantized]

    def quantize_entry(self, token_id: int, layer: int, head: int,
                       key: List[float], value: List[float], bit_width: int) -> QuantizedEntry:
        qk, sk, zpk = self._quantize(key, bit_width)
        qv, sv, zpv = self._quantize(value, bit_width)
        entry = QuantizedEntry(
            token_id=token_id, layer=layer, head=head, bit_width=bit_width,
            quantized_key=qk, quantized_value=qv,
            scale_key=sk, zero_point_key=zpk, scale_value=sv, zero_point_value=zpv,
        )
        eid = f"{layer}_{head}_{token_id}_{bit_width}"
        self.entries[eid] = entry
        self._save()
        return entry

    def dequantize_entry(self, entry: QuantizedEntry) -> Tuple[List[float], List[float]]:
        k = self._dequantize(entry.quantized_key, entry.scale_key, entry.zero_point_key)
        v = self._dequantize(entry.quantized_value, entry.scale_value, entry.zero_point_value)
        return k, v

    def compression_ratio(self, bit_width: int) -> float:
        return 16.0 / bit_width if bit_width > 0 else 0.0

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.entries)
        avg_bits = sum(e.bit_width for e in self.entries.values()) / max(1, total)
        return {"total_entries": total, "avg_bit_width": round(avg_bits, 2), "supported_bits": self.SUPPORTED_BITS}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["CacheQuantizationEngine", "QuantizedEntry"]
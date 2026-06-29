"""
packed_decode_layout_native.py
MAGNATRIX-OS — Packed Decode Layout

Inspired by NVIDIA RDKV TriZone packed-decode layout:
Efficient mixed-bit cache packing for fused dequantization during attention. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict


@dataclass
class ZoneSegment:
    zone: str  # A, B, or C
    bit_width: int
    start_idx: int
    end_idx: int
    data: List[Any] = field(default_factory=list)


class PackedDecodeLayout:
    """TriZone packed-decode layout for mixed-bit KV cache."""

    def __init__(self, cache_dir: str = "./packed_layout"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.layouts: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "layouts.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    self.layouts = json.load(f)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "layouts.json", "w", encoding="utf-8") as f:
            json.dump(self.layouts, f, indent=2)

    def pack(self, layout_id: str, token_bits: Dict[int, int], tokens: List[int],
             head_dim: int) -> Dict[str, Any]:
        """Pack tokens into TriZone layout: A=quantized, B=FP16, C=new FP16."""
        # Zone A: quantized tokens (bit_width < 16)
        zone_a = []
        zone_b = []
        for tid in tokens:
            bw = token_bits.get(tid, 16)
            if bw < 16 and bw > 0:
                zone_a.append({"token": tid, "bit_width": bw})
            elif bw == 16:
                zone_b.append({"token": tid, "bit_width": 16})

        # Sort Zone A by bit-width for contiguous packing
        zone_a.sort(key=lambda x: x["bit_width"])

        layout = {
            "layout_id": layout_id, "head_dim": head_dim,
            "zone_a": zone_a, "zone_b": zone_b, "zone_c": [],  # C filled at decode time
            "total_tokens": len(tokens), "packed_tokens": len(zone_a) + len(zone_b),
        }
        self.layouts[layout_id] = layout
        self._save()
        return layout

    def add_decode_tokens(self, layout_id: str, new_tokens: List[int]) -> Dict[str, Any]:
        """Add newly decoded tokens to Zone C."""
        layout = self.layouts.get(layout_id)
        if not layout:
            return {}
        layout["zone_c"].extend([{"token": t, "bit_width": 16} for t in new_tokens])
        layout["total_tokens"] += len(new_tokens)
        self._save()
        return layout

    def get_layout(self, layout_id: str) -> Optional[Dict[str, Any]]:
        return self.layouts.get(layout_id)

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.layouts)
        return {"total_layouts": total}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["PackedDecodeLayout", "ZoneSegment"]
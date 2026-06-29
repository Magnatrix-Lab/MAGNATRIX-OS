"""
rate_distortion_allocator_native.py
MAGNATRIX-OS — Rate-Distortion Allocator

Inspired by NVIDIA RDKV (joint eviction + quantization via rate-distortion):
Allocate bit-widths to cache units to minimize attention distortion under budget. Pure stdlib.
"""

import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict


@dataclass
class BitAllocation:
    unit_id: str
    weight: float
    bit_width: int
    distortion: float


class RateDistortionAllocator:
    """Allocate bit-widths to cache units via rate-distortion optimization."""

    BIT_WIDTHS = [0, 2, 4, 8, 16]

    def __init__(self, cache_dir: str = "./rd_allocator"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.allocations: Dict[str, List[BitAllocation]] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "allocations.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        self.allocations[k] = [BitAllocation(**a) for a in v]
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "allocations.json", "w", encoding="utf-8") as f:
            json.dump({k: [asdict(a) for a in v] for k, v in self.allocations.items()}, f, indent=2)

    def _distortion(self, weight: float, bit_width: int, sigma: float = 1.0) -> float:
        """Estimate distortion for a cache unit at given bit-width."""
        if bit_width == 0:
            return weight * sigma * 10.0  # High distortion for eviction
        return weight * sigma * (2 ** (-bit_width))

    def allocate(self, allocation_id: str, weights: List[Tuple[str, float]], total_budget: int) -> List[BitAllocation]:
        """Allocate bit-widths via greedy rate-distortion optimization."""
        if not weights or total_budget <= 0:
            return []
        allocations = []
        remaining_budget = total_budget
        # Sort by weight descending (most important first)
        sorted_weights = sorted(weights, key=lambda x: x[1], reverse=True)
        for unit_id, weight in sorted_weights:
            if remaining_budget <= 0:
                allocations.append(BitAllocation(unit_id, weight, 0, self._distortion(weight, 0)))
                continue
            # Try bit-widths from highest to lowest
            best_bw = 16
            best_dist = float('inf')
            for bw in sorted(self.BIT_WIDTHS, reverse=True):
                if bw <= remaining_budget:
                    dist = self._distortion(weight, bw)
                    if dist < best_dist:
                        best_dist = dist
                        best_bw = bw
            allocations.append(BitAllocation(unit_id, weight, best_bw, best_dist))
            remaining_budget -= best_bw
        self.allocations[allocation_id] = allocations
        self._save()
        return allocations

    def get_allocation(self, allocation_id: str) -> List[BitAllocation]:
        return self.allocations.get(allocation_id, [])

    def get_stats(self) -> Dict[str, Any]:
        total = sum(len(v) for v in self.allocations.values())
        avg_bits = sum(a.bit_width for v in self.allocations.values() for a in v) / max(1, total)
        return {"total_allocations": total, "avg_bit_width": round(avg_bits, 2)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["RateDistortionAllocator", "BitAllocation"]
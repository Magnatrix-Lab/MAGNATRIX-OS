"""LLM Layer Profiler — Native Python (stdlib only)."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class LayerType(Enum):
    ATTENTION = auto()
    FEEDFORWARD = auto()
    EMBEDDING = auto()
    NORMALIZATION = auto()
    OUTPUT = auto()

@dataclass
class LayerProfile:
    id: str
    layer_type: LayerType
    input_shape: tuple
    output_shape: tuple
    forward_time: float = 0.0
    backward_time: float = 0.0
    memory: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

class LayerProfiler:
    def __init__(self) -> None:
        self._profiles: List[LayerProfile] = []

    def record(self, profile: LayerProfile) -> None:
        self._profiles.append(profile)

    def get_by_type(self, layer_type: LayerType) -> List[LayerProfile]:
        return [p for p in self._profiles if p.layer_type == layer_type]

    def get_bottleneck(self) -> Optional[LayerProfile]:
        if not self._profiles:
            return None
        return max(self._profiles, key=lambda p: p.forward_time + p.backward_time)

    def get_memory_heavy(self) -> Optional[LayerProfile]:
        if not self._profiles:
            return None
        return max(self._profiles, key=lambda p: p.memory)

    def get_stats(self) -> Dict[str, Any]:
        total_time = sum(p.forward_time + p.backward_time for p in self._profiles)
        total_memory = sum(p.memory for p in self._profiles)
        return {"layers": len(self._profiles), "total_time": total_time, "total_memory": total_memory, "avg_time": total_time / len(self._profiles) if self._profiles else 0.0}

def run() -> None:
    print("Layer Profiler test")
    e = LayerProfiler()
    e.record(LayerProfile("l1", LayerType.ATTENTION, (1, 512), (1, 512), forward_time=0.015, memory=1024))
    e.record(LayerProfile("l2", LayerType.FEEDFORWARD, (1, 512), (1, 2048), forward_time=0.010, memory=2048))
    e.record(LayerProfile("l3", LayerType.ATTENTION, (1, 2048), (1, 2048), forward_time=0.020, memory=2048))
    print("  Bottleneck: " + e.get_bottleneck().id)
    print("  Memory heavy: " + e.get_memory_heavy().id)
    print("  Stats: " + str(e.get_stats()))
    print("Layer Profiler test complete.")

if __name__ == "__main__":
    run()

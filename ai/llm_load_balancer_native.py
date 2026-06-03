"""LLM Load Balancer — Native Python (stdlib only)."""
from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class BackendStatus(Enum):
    HEALTHY = auto()
    DEGRADED = auto()
    UNHEALTHY = auto()

@dataclass
class Backend:
    id: str
    capacity: int
    current_load: int = 0
    status: BackendStatus = BackendStatus.HEALTHY
    metadata: Dict[str, Any] = field(default_factory=dict)

class LoadBalancer:
    def __init__(self) -> None:
        self._backends: List[Backend] = []
        self._index: int = 0

    def add_backend(self, backend: Backend) -> None:
        self._backends.append(backend)

    def remove_backend(self, backend_id: str) -> bool:
        for i, b in enumerate(self._backends):
            if b.id == backend_id:
                self._backends.pop(i)
                return True
        return False

    def round_robin(self) -> Optional[Backend]:
        healthy = [b for b in self._backends if b.status == BackendStatus.HEALTHY]
        if not healthy:
            return None
        selected = healthy[self._index % len(healthy)]
        self._index = (self._index + 1) % len(healthy)
        return selected

    def least_loaded(self) -> Optional[Backend]:
        healthy = [b for b in self._backends if b.status == BackendStatus.HEALTHY]
        if not healthy:
            return None
        return min(healthy, key=lambda b: b.current_load / b.capacity if b.capacity else float('inf'))

    def random_backend(self) -> Optional[Backend]:
        healthy = [b for b in self._backends if b.status == BackendStatus.HEALTHY]
        if not healthy:
            return None
        return random.choice(healthy)

    def get_stats(self) -> Dict[str, Any]:
        return {"backends": len(self._backends), "healthy": sum(1 for b in self._backends if b.status == BackendStatus.HEALTHY), "total_load": sum(b.current_load for b in self._backends)}

def run() -> None:
    print("Load Balancer test")
    e = LoadBalancer()
    e.add_backend(Backend("b1", 100, 30))
    e.add_backend(Backend("b2", 100, 50))
    e.add_backend(Backend("b3", 100, 10))
    print("  Round robin: " + e.round_robin().id)
    print("  Round robin: " + e.round_robin().id)
    print("  Least loaded: " + e.least_loaded().id)
    print("  Random: " + e.random_backend().id)
    print("  Stats: " + str(e.get_stats()))
    print("Load Balancer test complete.")

if __name__ == "__main__":
    run()

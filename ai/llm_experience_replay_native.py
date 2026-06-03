"""LLM Experience Replay — Native Python (stdlib only)."""
from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

@dataclass
class Experience:
    id: str
    state: Dict[str, Any]
    action: str
    reward: float
    next_state: Dict[str, Any]
    done: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

class ExperienceReplay:
    def __init__(self, capacity: int = 10000) -> None:
        self.capacity = capacity
        self._buffer: List[Experience] = []
        self._position: int = 0

    def add(self, exp: Experience) -> None:
        if len(self._buffer) < self.capacity:
            self._buffer.append(exp)
        else:
            self._buffer[self._position] = exp
        self._position = (self._position + 1) % self.capacity

    def sample(self, batch_size: int) -> List[Experience]:
        if len(self._buffer) < batch_size:
            return list(self._buffer)
        return random.sample(self._buffer, batch_size)

    def sample_recent(self, n: int) -> List[Experience]:
        return self._buffer[-n:]

    def get_stats(self) -> Dict[str, Any]:
        return {"size": len(self._buffer), "capacity": self.capacity, "fill_ratio": len(self._buffer) / self.capacity, "avg_reward": sum(e.reward for e in self._buffer) / len(self._buffer) if self._buffer else 0.0}

def run() -> None:
    print("Experience Replay test")
    e = ExperienceReplay(capacity=100)
    for i in range(10):
        e.add(Experience("e" + str(i), {"step": i}, "action_" + str(i), float(i) * 0.1, {"step": i + 1}, i == 9))
    sample = e.sample(3)
    print("  Sample size: " + str(len(sample)))
    print("  Recent: " + str([exp.id for exp in e.sample_recent(3)]))
    print("  Stats: " + str(e.get_stats()))
    print("Experience Replay test complete.")

if __name__ == "__main__":
    run()

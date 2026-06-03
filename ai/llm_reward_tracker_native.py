"""LLM Reward Tracker — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class RewardType(Enum):
    EXTRINSIC = auto()
    INTRINSIC = auto()
    HYBRID = auto()

@dataclass
class RewardEntry:
    id: str
    target_id: str
    reward_value: float
    reward_type: RewardType
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)

class RewardTracker:
    def __init__(self) -> None:
        self._entries: List[RewardEntry] = []
        self._totals: Dict[str, float] = {}

    def add(self, entry: RewardEntry) -> None:
        self._entries.append(entry)
        self._totals[entry.target_id] = self._totals.get(entry.target_id, 0.0) + entry.reward_value

    def get_total(self, target_id: str) -> float:
        return self._totals.get(target_id, 0.0)

    def get_average(self, target_id: str) -> float:
        entries = [e for e in self._entries if e.target_id == target_id]
        if not entries:
            return 0.0
        return sum(e.reward_value for e in entries) / len(entries)

    def get_top(self, n: int = 5) -> List[tuple]:
        sorted_targets = sorted(self._totals.items(), key=lambda x: x[1], reverse=True)
        return sorted_targets[:n]

    def get_stats(self) -> Dict[str, Any]:
        return {"total_entries": len(self._entries), "targets": len(self._totals), "avg_reward": sum(e.reward_value for e in self._entries) / len(self._entries) if self._entries else 0.0}

def run() -> None:
    print("Reward Tracker test")
    e = RewardTracker()
    e.add(RewardEntry("r1", "agent_1", 1.0, RewardType.EXTRINSIC, "2024-01-01T10:00:00"))
    e.add(RewardEntry("r2", "agent_1", 0.5, RewardType.INTRINSIC, "2024-01-01T10:01:00"))
    e.add(RewardEntry("r3", "agent_2", 1.5, RewardType.EXTRINSIC, "2024-01-01T10:02:00"))
    e.add(RewardEntry("r4", "agent_1", 0.8, RewardType.HYBRID, "2024-01-01T10:03:00"))
    print("  Total agent_1: " + str(e.get_total("agent_1")))
    print("  Top: " + str(e.get_top(2)))
    print("  Stats: " + str(e.get_stats()))
    print("Reward Tracker test complete.")

if __name__ == "__main__":
    run()

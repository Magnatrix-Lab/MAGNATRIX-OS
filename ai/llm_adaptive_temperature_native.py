"""LLM Adaptive Temperature — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class TaskType(Enum):
    CREATIVE = auto()
    ANALYTICAL = auto()
    TECHNICAL = auto()
    CONVERSATIONAL = auto()

@dataclass
class TemperatureProfile:
    task: TaskType
    temperature: float
    top_p: float
    top_k: int
    description: str

class AdaptiveTemperatureEngine:
    def __init__(self) -> None:
        self._profiles: Dict[str, TemperatureProfile] = {}
        self._default = TemperatureProfile(TaskType.CONVERSATIONAL, 0.7, 0.9, 50, "Default balanced profile")

    def register(self, profile: TemperatureProfile) -> None:
        self._profiles[profile.task.name] = profile

    def get(self, task: TaskType) -> TemperatureProfile:
        return self._profiles.get(task.name, self._default)

    def scale(self, task: TaskType, confidence: float) -> float:
        base = self.get(task).temperature
        if confidence < 0.3:
            return min(base * 1.3, 1.5)
        elif confidence > 0.8:
            return max(base * 0.7, 0.1)
        return base

    def get_stats(self) -> Dict[str, Any]:
        return {"profiles": len(self._profiles), "default": self._default.task.name}

def run() -> None:
    print("Adaptive Temperature test")
    e = AdaptiveTemperatureEngine()
    e.register(TemperatureProfile(TaskType.CREATIVE, 1.0, 0.95, 100, "High creativity"))
    e.register(TemperatureProfile(TaskType.ANALYTICAL, 0.2, 0.8, 20, "Precise and factual"))
    e.register(TemperatureProfile(TaskType.TECHNICAL, 0.3, 0.85, 30, "Technical accuracy"))
    print("  Creative: " + str(e.get(TaskType.CREATIVE)))
    print("  Scaled analytical (low confidence): " + str(e.scale(TaskType.ANALYTICAL, 0.2)))
    print("  Scaled analytical (high confidence): " + str(e.scale(TaskType.ANALYTICAL, 0.9)))
    print("Adaptive Temperature test complete.")

if __name__ == "__main__":
    run()

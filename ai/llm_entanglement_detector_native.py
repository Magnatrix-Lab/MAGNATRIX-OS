"""Entanglement Detector - Bell state detection for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Dict
import math
import cmath

@dataclass
class EntanglementDetector:
    threshold: float = 0.9

    def bell_state(self, state_idx: int) -> List[complex]:
        states = [
            [1/math.sqrt(2), 0, 0, 1/math.sqrt(2)],
            [1/math.sqrt(2), 0, 0, -1/math.sqrt(2)],
            [0, 1/math.sqrt(2), 1/math.sqrt(2), 0],
            [0, 1/math.sqrt(2), -1/math.sqrt(2), 0]
        ]
        return states[state_idx % 4]

    def fidelity(self, state: List[complex], target: List[complex]) -> float:
        return abs(sum(state[i].conjugate()*target[i] for i in range(len(state))))**2

    def detect(self, state: List[complex]) -> str:
        for i in range(4):
            if self.fidelity(state, self.bell_state(i)) > self.threshold:
                return f"Bell_{i}"
        return "Not entangled"

    def stats(self, state: List[complex]) -> dict:
        return {"fidelities": [round(self.fidelity(state, self.bell_state(i)), 4) for i in range(4)], "result": self.detect(state)}

def run():
    ed = EntanglementDetector()
    bell = ed.bell_state(0)
    print("Detection:", ed.detect(bell))
    print("Stats:", ed.stats(bell))

if __name__ == "__main__": run()

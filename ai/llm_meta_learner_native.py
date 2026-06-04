"""Meta Learner - Learning to learn for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
import random
import math

@dataclass
class MetaLearner:
    tasks: List[Dict] = field(default_factory=list)
    meta_params: Dict[str, float] = field(default_factory=dict)

    def __post_init__(self):
        if not self.meta_params: self.meta_params = {"lr": 0.01, "momentum": 0.9}

    def add_task(self, train_data: List[Tuple], test_data: List[Tuple]) -> None:
        self.tasks.append({"train": train_data, "test": test_data})

    def adapt(self, task_idx: int, steps: int = 5) -> Dict[str, float]:
        task = self.tasks[task_idx]
        params = self.meta_params.copy()
        for _ in range(steps):
            for x, y in task["train"]:
                pred = params.get("w", 0.0) * x + params.get("b", 0.0)
                error = pred - y
                params["w"] = params.get("w", 0.0) - self.meta_params["lr"] * error * x
                params["b"] = params.get("b", 0.0) - self.meta_params["lr"] * error
        return params

    def stats(self) -> dict:
        return {"tasks": len(self.tasks), "meta_params": self.meta_params}

def run():
    ml = MetaLearner()
    ml.add_task([(1,2),(2,4),(3,6)], [(4,8)])
    adapted = ml.adapt(0, 10)
    print("Adapted:", {k: round(v, 4) for k, v in adapted.items()})
    print("Stats:", ml.stats())

if __name__ == "__main__": run()

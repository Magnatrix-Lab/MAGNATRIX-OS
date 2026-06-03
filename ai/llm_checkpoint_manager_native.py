"""Checkpoint Manager - Model checkpointing for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum, auto
import json
import time

class CheckpointFormat(Enum):
    JSON = auto()
    DICT = auto()

@dataclass
class CheckpointManager:
    checkpoints: List[Dict[str, Any]] = field(default_factory=list)
    best_metric: Optional[float] = None
    keep_best: bool = True

    def save(self, step: int, metrics: Dict[str, float], state: Dict[str, Any]) -> None:
        ckpt = {"step": step, "timestamp": time.time(), "metrics": metrics, "state": state}
        self.checkpoints.append(ckpt)
        if self.keep_best:
            current = metrics.get("loss", float("inf"))
            if self.best_metric is None or current < self.best_metric:
                self.best_metric = current
                ckpt["is_best"] = True

    def load_best(self) -> Optional[Dict[str, Any]]:
        for ckpt in reversed(self.checkpoints):
            if ckpt.get("is_best"):
                return ckpt
        return self.checkpoints[-1] if self.checkpoints else None

    def prune_old(self, keep_last: int = 3) -> None:
        if len(self.checkpoints) > keep_last:
            best = [c for c in self.checkpoints if c.get("is_best")]
            others = [c for c in self.checkpoints if not c.get("is_best")]
            self.checkpoints = best + others[-keep_last:]

    def stats(self) -> dict:
        return {"total_ckpts": len(self.checkpoints), "best_metric": round(self.best_metric, 6) if self.best_metric else None}

def run():
    cm = CheckpointManager()
    for i in range(5):
        cm.save(i, {"loss": 1.0 - i*0.15}, {"weights": [i*0.1]})
    cm.prune_old(3)
    print("Best checkpoint:", cm.load_best()["step"])
    print("Stats:", cm.stats())

if __name__ == "__main__":
    run()

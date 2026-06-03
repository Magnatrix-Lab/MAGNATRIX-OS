"""Early Stopper - Training early stopping for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum, auto

class StopMetric(Enum):
    LOSS = auto()
    ACCURACY = auto()

@dataclass
class EarlyStopper:
    patience: int = 5
    min_delta: float = 1e-4
    stop_metric: StopMetric = StopMetric.LOSS
    best_value: Optional[float] = None
    counter: int = 0
    stopped: bool = False
    history: List[float] = field(default_factory=list)

    def check(self, value: float) -> bool:
        self.history.append(value)
        if self.best_value is None:
            self.best_value = value
            return False
        if self.stop_metric == StopMetric.LOSS:
            improved = value < self.best_value - self.min_delta
        else:
            improved = value > self.best_value + self.min_delta
        if improved:
            self.best_value = value
            self.counter = 0
        else:
            self.counter += 1
        if self.counter >= self.patience:
            self.stopped = True
        return self.stopped

    def stats(self) -> dict:
        return {"patience": self.patience, "counter": self.counter, "stopped": self.stopped, "best": round(self.best_value, 6) if self.best_value else None}

def run():
    es = EarlyStopper(3, 0.01, StopMetric.LOSS)
    losses = [1.0, 0.8, 0.75, 0.74, 0.74, 0.74, 0.74]
    for loss in losses:
        if es.check(loss):
            print(f"Stopped at loss={loss}")
            break
    print("Stats:", es.stats())

if __name__ == "__main__":
    run()

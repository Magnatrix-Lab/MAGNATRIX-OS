"""LR Scheduler - Learning rate scheduling for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum, auto
import math

class ScheduleType(Enum):
    STEP = auto()
    EXPONENTIAL = auto()
    COSINE = auto()
    WARMUP = auto()
    PLATEAU = auto()

@dataclass
class LRScheduler:
    initial_lr: float = 0.01
    schedule_type: ScheduleType = ScheduleType.STEP
    step_size: int = 10
    gamma: float = 0.1
    min_lr: float = 1e-7
    warmup_steps: int = 5
    total_steps: int = 100
    current_step: int = 0

    def step(self) -> float:
        self.current_step += 1
        if self.schedule_type == ScheduleType.STEP:
            factor = self.gamma ** (self.current_step // self.step_size)
        elif self.schedule_type == ScheduleType.EXPONENTIAL:
            factor = self.gamma ** self.current_step
        elif self.schedule_type == ScheduleType.COSINE:
            progress = self.current_step / self.total_steps
            factor = 0.5 * (1 + math.cos(math.pi * progress))
        elif self.schedule_type == ScheduleType.WARMUP:
            if self.current_step < self.warmup_steps:
                factor = self.current_step / self.warmup_steps
            else:
                factor = self.gamma ** ((self.current_step - self.warmup_steps) // self.step_size)
        else:
            factor = 1.0
        return max(self.initial_lr * factor, self.min_lr)

    def stats(self) -> dict:
        return {"schedule": self.schedule_type.name, "current_step": self.current_step, "current_lr": round(self.step(), 8)}

def run():
    for st in [ScheduleType.STEP, ScheduleType.COSINE, ScheduleType.WARMUP]:
        sched = LRScheduler(0.01, st, total_steps=20, warmup_steps=5)
        lrs = [sched.step() for _ in range(20)]
        print(f"{st.name}: {[round(lr, 6) for lr in lrs]}")

if __name__ == "__main__":
    run()

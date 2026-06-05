"""Gradient Descent Scheduler — SGD, Adam, RMSprop, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Callable, Optional
from enum import Enum, auto
import math
import random

class OptimizerType(Enum):
    SGD = auto()
    MOMENTUM = auto()
    ADAM = auto()
    RMSPROP = auto()

@dataclass
class ParameterState:
    value: float
    gradient: float = 0.0
    m: float = 0.0
    v: float = 0.0
    t: int = 0

class GradientScheduler:
    def __init__(self, optimizer: OptimizerType = OptimizerType.ADAM, lr: float = 0.01, beta1: float = 0.9, beta2: float = 0.999, eps: float = 1e-8):
        self.optimizer = optimizer
        self.lr = lr
        self.beta1 = beta1
        self.beta2 = beta2
        self.eps = eps
        self.params: Dict[str, ParameterState] = {}
        self.history: List[Dict] = []
        self.step_count = 0

    def register(self, name: str, initial_value: float):
        self.params[name] = ParameterState(initial_value)

    def set_gradients(self, gradients: Dict[str, float]):
        for name, grad in gradients.items():
            if name in self.params:
                self.params[name].gradient = grad

    def step(self):
        self.step_count += 1
        for name, p in self.params.items():
            if self.optimizer == OptimizerType.SGD:
                p.value -= self.lr * p.gradient
            elif self.optimizer == OptimizerType.MOMENTUM:
                p.m = 0.9 * p.m + p.gradient
                p.value -= self.lr * p.m
            elif self.optimizer == OptimizerType.ADAM:
                p.t += 1
                p.m = self.beta1 * p.m + (1 - self.beta1) * p.gradient
                p.v = self.beta2 * p.v + (1 - self.beta2) * (p.gradient ** 2)
                m_hat = p.m / (1 - self.beta1 ** p.t)
                v_hat = p.v / (1 - self.beta2 ** p.t)
                p.value -= self.lr * m_hat / (math.sqrt(v_hat) + self.eps)
            elif self.optimizer == OptimizerType.RMSPROP:
                p.v = 0.9 * p.v + 0.1 * (p.gradient ** 2)
                p.value -= self.lr * p.gradient / (math.sqrt(p.v) + self.eps)
        self.history.append({"step": self.step_count, "values": {k: v.value for k, v in self.params.items()}})

    def get_values(self) -> Dict[str, float]:
        return {k: v.value for k, v in self.params.items()}

    def stats(self) -> Dict:
        return {"optimizer": self.optimizer.name, "step": self.step_count, "params": len(self.params), "lr": self.lr}

def run():
    sched = GradientScheduler(OptimizerType.ADAM, lr=0.1)
    sched.register("x", 0.0)
    sched.register("y", 0.0)
    for _ in range(100):
        values = sched.get_values()
        sched.set_gradients({"x": 2 * (values["x"] - 3), "y": 2 * (values["y"] + 1)})
        sched.step()
    print(sched.get_values())
    print(sched.stats())

if __name__ == "__main__":
    run()

"""Knowledge Distillation — teacher-student training, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Callable
from enum import Enum, auto
import math
import random

class DistillLoss(Enum):
    SOFT = auto()
    HARD = auto()
    BOTH = auto()

@dataclass
class DistillationRun:
    teacher_logits: List[List[float]]
    student_logits: List[List[float]]
    labels: List[int]
    temperature: float = 2.0
    alpha: float = 0.5

class KnowledgeDistiller:
    def __init__(self, temperature: float = 2.0, alpha: float = 0.5):
        self.temperature = temperature
        self.alpha = alpha
        self.runs: List[DistillationRun] = []

    def _softmax(self, logits: List[float], temp: float) -> List[float]:
        exps = [math.exp(x / temp) for x in logits]
        s = sum(exps)
        return [e / s for e in exps]

    def _kl_div(self, p: List[float], q: List[float]) -> float:
        return sum(pi * math.log(pi / qi) if pi > 0 and qi > 0 else 0 for pi, qi in zip(p, q))

    def _cross_entropy(self, pred: List[float], label: int) -> float:
        return -math.log(max(pred[label], 1e-10))

    def distill_step(self, teacher_logits: List[List[float]], student_logits: List[List[float]], labels: List[int]) -> float:
        run = DistillationRun(teacher_logits, student_logits, labels, self.temperature, self.alpha)
        total_loss = 0.0
        for t_log, s_log, lbl in zip(teacher_logits, student_logits, labels):
            t_soft = self._softmax(t_log, self.temperature)
            s_soft = self._softmax(s_log, self.temperature)
            s_hard = self._softmax(s_log, 1.0)
            soft_loss = self._kl_div(t_soft, s_soft) * (self.temperature ** 2)
            hard_loss = self._cross_entropy(s_hard, lbl)
            loss = self.alpha * soft_loss + (1 - self.alpha) * hard_loss
            total_loss += loss
        run.soft_loss = soft_loss
        run.hard_loss = hard_loss
        self.runs.append(run)
        return total_loss / len(labels)

    def stats(self) -> Dict:
        if not self.runs:
            return {}
        return {"runs": len(self.runs), "temperature": self.temperature, "alpha": self.alpha}

def run():
    dist = KnowledgeDistiller(temperature=3.0, alpha=0.7)
    teacher = [[2.0, 1.0, 0.5], [0.5, 2.5, 1.0]]
    student = [[1.5, 1.2, 0.8], [0.8, 2.0, 1.2]]
    labels = [0, 1]
    loss = dist.distill_step(teacher, student, labels)
    print("Distillation loss:", loss)
    print(dist.stats())

if __name__ == "__main__":
    run()

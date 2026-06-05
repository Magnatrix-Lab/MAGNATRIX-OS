"""Data Quality Monitor — rules, metrics, and scoring, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from enum import Enum, auto
import math

class QualityDimension(Enum):
    COMPLETENESS = auto()
    UNIQUENESS = auto()
    VALIDITY = auto()
    CONSISTENCY = auto()
    TIMELINESS = auto()

@dataclass
class QualityRule:
    rule_id: str
    dimension: QualityDimension
    check: Callable[[Any], bool]
    field: Optional[str] = None
    weight: float = 1.0

@dataclass
class QualityScore:
    dimension: QualityDimension
    score: float
    passed: int
    failed: int

class DataQualityMonitor:
    def __init__(self):
        self.rules: List[QualityRule] = []
        self.scores: Dict[QualityDimension, QualityScore] = {}
        self.history: List[Dict] = []

    def add_rule(self, rule: QualityRule):
        self.rules.append(rule)

    def assess(self, data: List[Dict]) -> Dict[QualityDimension, QualityScore]:
        self.scores = {}
        for dim in QualityDimension:
            self.scores[dim] = QualityScore(dim, 0.0, 0, 0)
        for rule in self.rules:
            passed = 0
            failed = 0
            for row in data:
                value = row.get(rule.field) if rule.field else row
                try:
                    if rule.check(value):
                        passed += 1
                    else:
                        failed += 1
                except:
                    failed += 1
            total = passed + failed
            score = passed / total if total > 0 else 0
            if rule.dimension in self.scores:
                existing = self.scores[rule.dimension]
                self.scores[rule.dimension] = QualityScore(rule.dimension, (existing.score * existing.passed + score * passed) / (existing.passed + passed + 1e-6), existing.passed + passed, existing.failed + failed)
            else:
                self.scores[rule.dimension] = QualityScore(rule.dimension, score, passed, failed)
        self.history.append({"records": len(data), "scores": {k.name: v.score for k, v in self.scores.items()}})
        return self.scores

    def overall_score(self) -> float:
        if not self.scores:
            return 0.0
        return sum(s.score for s in self.scores.values()) / len(self.scores)

    def stats(self) -> Dict:
        return {"rules": len(self.rules), "dimensions": len(self.scores), "overall": self.overall_score(), "latest": {k.name: round(v.score, 3) for k, v in self.scores.items()}}

def run():
    monitor = DataQualityMonitor()
    monitor.add_rule(QualityRule("r1", QualityDimension.COMPLETENESS, lambda x: x is not None, "name"))
    monitor.add_rule(QualityRule("r2", QualityDimension.VALIDITY, lambda x: isinstance(x, (int, float)) and x >= 0, "age"))
    monitor.add_rule(QualityRule("r3", QualityDimension.UNIQUENESS, lambda x: True, "id"))
    data = [
        {"id": 1, "name": "Alice", "age": 30},
        {"id": 2, "name": None, "age": 25},
        {"id": 3, "name": "Bob", "age": -1},
    ]
    monitor.assess(data)
    print(monitor.stats())

if __name__ == "__main__":
    run()

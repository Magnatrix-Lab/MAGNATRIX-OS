"""Bias Detector — demographic bias, disparate impact, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math

@dataclass
class BiasReport:
    metric: str
    score: float
    threshold: float
    biased: bool

class BiasDetector:
    def __init__(self):
        self.reports: List[BiasReport] = []

    def disparate_impact(self, protected_group_positive: int, protected_group_total: int,
                         unprotected_group_positive: int, unprotected_group_total: int) -> BiasReport:
        rate_protected = protected_group_positive / protected_group_total if protected_group_total else 0
        rate_unprotected = unprotected_group_positive / unprotected_group_total if unprotected_group_total else 0
        ratio = rate_protected / rate_unprotected if rate_unprotected else 0
        biased = ratio < 0.8 or ratio > 1.25
        return BiasReport("disparate_impact", ratio, 0.8, biased)

    def demographic_parity(self, predictions_by_group: Dict[str, List[int]]) -> BiasReport:
        rates = {g: sum(p) / len(p) if p else 0 for g, p in predictions_by_group.items()}
        max_rate = max(rates.values()) if rates else 0
        min_rate = min(rates.values()) if rates else 0
        diff = max_rate - min_rate
        return BiasReport("demographic_parity", diff, 0.1, diff > 0.1)

    def equalized_odds(self, tp_by_group: Dict[str, int], fp_by_group: Dict[str, int],
                       total_pos_by_group: Dict[str, int], total_neg_by_group: Dict[str, int]) -> BiasReport:
        tpr = {g: tp_by_group.get(g, 0) / total_pos_by_group.get(g, 1) for g in tp_by_group}
        fpr = {g: fp_by_group.get(g, 0) / total_neg_by_group.get(g, 1) for g in fp_by_group}
        tpr_diff = max(tpr.values()) - min(tpr.values()) if tpr else 0
        fpr_diff = max(fpr.values()) - min(fpr.values()) if fpr else 0
        score = max(tpr_diff, fpr_diff)
        return BiasReport("equalized_odds", score, 0.1, score > 0.1)

    def analyze(self, data: Dict) -> List[BiasReport]:
        self.reports = []
        if "disparate_impact" in data:
            self.reports.append(self.disparate_impact(**data["disparate_impact"]))
        if "demographic_parity" in data:
            self.reports.append(self.demographic_parity(data["demographic_parity"]))
        return self.reports

    def stats(self) -> Dict:
        biased = sum(1 for r in self.reports if r.biased)
        return {"reports": len(self.reports), "biased": biased}

def run():
    detector = BiasDetector()
    report = detector.disparate_impact(40, 100, 50, 100)
    print("Disparate Impact:", report.score, "Biased:", report.biased)
    dp = detector.demographic_parity({"A": [1,0,1,1], "B": [0,0,1,0]})
    print("DP:", dp.score, dp.biased)
    print(detector.stats())

if __name__ == "__main__":
    run()

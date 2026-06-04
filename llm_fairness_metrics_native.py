"""Fairness Metrics — statistical parity, calibration, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math

class FairnessMetrics:
    def __init__(self):
        self.metrics: Dict[str, float] = {}

    def statistical_parity(self, predictions: List[int], protected: List[int]) -> float:
        group_1 = [p for p, prot in zip(predictions, protected) if prot == 1]
        group_0 = [p for p, prot in zip(predictions, protected) if prot == 0]
        rate_1 = sum(group_1) / len(group_1) if group_1 else 0
        rate_0 = sum(group_0) / len(group_0) if group_0 else 0
        return abs(rate_1 - rate_0)

    def calibration(self, scores: List[float], outcomes: List[int], bins: int = 10) -> float:
        bin_edges = [i / bins for i in range(bins + 1)]
        calibration_error = 0.0
        for i in range(bins):
            in_bin = [s for s in scores if bin_edges[i] <= s < bin_edges[i + 1]]
            if in_bin:
                avg_score = sum(in_bin) / len(in_bin)
                avg_outcome = sum(outcomes[j] for j, s in enumerate(scores) if bin_edges[i] <= s < bin_edges[i + 1]) / len(in_bin)
                calibration_error += abs(avg_score - avg_outcome)
        return calibration_error / bins

    def individual_fairness(self, similar_pairs: List[Tuple[int, int]], predictions: List[int]) -> float:
        if not similar_pairs:
            return 0.0
        diffs = [abs(predictions[a] - predictions[b]) for a, b in similar_pairs]
        return sum(diffs) / len(diffs)

    def compute_all(self, data: Dict) -> Dict:
        return self.metrics

    def stats(self) -> Dict:
        return {"metrics": len(self.metrics)}

def run():
    fm = FairnessMetrics()
    pred = [1, 0, 1, 1, 0, 1, 0, 0]
    prot = [1, 1, 1, 1, 0, 0, 0, 0]
    print("Statistical parity:", fm.statistical_parity(pred, prot))
    print(fm.stats())

if __name__ == "__main__":
    run()

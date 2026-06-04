"""Fairness Metrics - Multiple fairness measures for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple
import math

@dataclass
class FairnessMetrics:

    def statistical_parity(self, preds: List[int], groups: List[str]) -> float:
        from collections import defaultdict
        rates = defaultdict(list)
        for p, g in zip(preds, groups): rates[g].append(p)
        avg_rates = [sum(v)/len(v) for v in rates.values()]
        return max(avg_rates) - min(avg_rates) if avg_rates else 0

    def calibration(self, scores: List[float], labels: List[int], groups: List[str]) -> Dict[str, float]:
        from collections import defaultdict
        group_scores = defaultdict(list)
        group_labels = defaultdict(list)
        for s, l, g in zip(scores, labels, groups):
            group_scores[g].append(s); group_labels[g].append(l)
        result = {}
        for g in set(groups):
            if group_scores[g]:
                avg_score = sum(group_scores[g]) / len(group_scores[g])
                avg_label = sum(group_labels[g]) / len(group_labels[g])
                result[g] = round(abs(avg_score - avg_label), 4)
        return result

    def stats(self, preds: List[int], groups: List[str]) -> dict:
        return {"statistical_parity": round(self.statistical_parity(preds, groups), 4), "groups": len(set(groups))}

def run():
    fm = FairnessMetrics()
    preds = [1, 1, 0, 0, 1, 0, 1, 0]
    groups = ["A", "A", "A", "A", "B", "B", "B", "B"]
    print("Stats:", fm.stats(preds, groups))

if __name__ == "__main__": run()

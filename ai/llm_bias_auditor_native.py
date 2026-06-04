"""Bias Auditor - Demographic parity checker for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from collections import defaultdict
import math

@dataclass
class BiasAuditor:
    protected_attr: str = "gender"

    def demographic_parity(self, predictions: List[int], groups: List[str]) -> Dict[str, float]:
        group_preds = defaultdict(list)
        for pred, group in zip(predictions, groups):
            group_preds[group].append(pred)
        rates = {g: sum(p) / len(p) for g, p in group_preds.items()}
        return rates

    def equalized_odds(self, predictions: List[int], labels: List[int], groups: List[str]) -> Dict[str, Dict]:
        result = {}
        for group in set(groups):
            idx = [i for i, g in enumerate(groups) if g == group]
            tpr = sum(predictions[i] for i in idx if labels[i] == 1) / max(1, sum(labels[i] for i in idx))
            fpr = sum(1 for i in idx if predictions[i] == 1 and labels[i] == 0) / max(1, sum(1 for i in idx if labels[i] == 0))
            result[group] = {"tpr": round(tpr, 4), "fpr": round(fpr, 4)}
        return result

    def stats(self, predictions: List[int], groups: List[str]) -> dict:
        rates = self.demographic_parity(predictions, groups)
        return {"rates": rates, "disparity": max(rates.values()) - min(rates.values()) if rates else 0}

def run():
    ba = BiasAuditor()
    preds = [1, 1, 0, 0, 1, 0, 1, 0]
    groups = ["A", "A", "A", "A", "B", "B", "B", "B"]
    print("Demographic parity:", ba.demographic_parity(preds, groups))
    print("Stats:", ba.stats(preds, groups))

if __name__ == "__main__": run()

"""Demographic Parity Engine — audit predictions by group, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto

class DemographicParityEngine:
    def __init__(self):
        self.groups: Dict[str, List[int]] = {}

    def add_group(self, group_id: str, predictions: List[int]):
        self.groups[group_id] = predictions

    def audit(self) -> Dict:
        rates = {}
        for gid, preds in self.groups.items():
            rates[gid] = sum(preds) / len(preds) if preds else 0
        max_rate = max(rates.values()) if rates else 0
        min_rate = min(rates.values()) if rates else 0
        return {"rates": rates, "max": max_rate, "min": min_rate, "gap": max_rate - min_rate, "parity": max_rate - min_rate < 0.1}

    def recommendations(self) -> List[str]:
        audit = self.audit()
        recs = []
        if not audit["parity"]:
            recs.append("Adjust thresholds per group to achieve parity")
        return recs

    def stats(self) -> Dict:
        return {"groups": len(self.groups)}

def run():
    dp = DemographicParityEngine()
    dp.add_group("A", [1, 1, 1, 0, 0])
    dp.add_group("B", [0, 0, 1, 0, 0])
    print(dp.audit())
    print(dp.recommendations())
    print(dp.stats())

if __name__ == "__main__":
    run()

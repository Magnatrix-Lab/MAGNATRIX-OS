"""Equalized Odds Engine — TPR/FPR parity across groups, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto

class EqualizedOddsEngine:
    def __init__(self):
        self.groups: Dict[str, Dict] = {}

    def add_group(self, group_id: str, tp: int, fp: int, tn: int, fn: int):
        self.groups[group_id] = {"tp": tp, "fp": fp, "tn": tn, "fn": fn}

    def tpr(self, group_id: str) -> float:
        g = self.groups[group_id]
        total = g["tp"] + g["fn"]
        return g["tp"] / total if total else 0

    def fpr(self, group_id: str) -> float:
        g = self.groups[group_id]
        total = g["fp"] + g["tn"]
        return g["fp"] / total if total else 0

    def audit(self) -> Dict:
        tprs = {g: self.tpr(g) for g in self.groups}
        fprs = {g: self.fpr(g) for g in self.groups}
        tpr_gap = max(tprs.values()) - min(tprs.values()) if tprs else 0
        fpr_gap = max(fprs.values()) - min(fprs.values()) if fprs else 0
        return {"tpr": tprs, "fpr": fprs, "tpr_gap": tpr_gap, "fpr_gap": fpr_gap, "equalized": tpr_gap < 0.1 and fpr_gap < 0.1}

    def stats(self) -> Dict:
        return {"groups": len(self.groups)}

def run():
    eo = EqualizedOddsEngine()
    eo.add_group("A", 80, 20, 70, 30)
    eo.add_group("B", 75, 25, 75, 25)
    print(eo.audit())
    print(eo.stats())

if __name__ == "__main__":
    run()

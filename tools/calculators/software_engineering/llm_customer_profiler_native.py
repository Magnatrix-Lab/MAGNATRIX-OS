"""Customer Profiler — segmentation, RFM, lifetime scoring, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto
import time
from collections import defaultdict

@dataclass
class CustomerProfile:
    customer_id: str
    total_spent: float = 0.0
    order_count: int = 0
    last_order: float = 0.0
    first_order: float = 0.0
    category: str = ""

class CustomerProfiler:
    def __init__(self):
        self.profiles: Dict[str, CustomerProfile] = {}
        self.rfm_scores: Dict[str, Dict] = {}

    def add_transaction(self, customer_id: str, amount: float, timestamp: float = None):
        timestamp = timestamp or time.time()
        if customer_id not in self.profiles:
            self.profiles[customer_id] = CustomerProfile(customer_id, first_order=timestamp)
        p = self.profiles[customer_id]
        p.total_spent += amount
        p.order_count += 1
        p.last_order = timestamp

    def rfm_analysis(self, now: float = None) -> Dict[str, Dict]:
        now = now or time.time()
        recencies = []
        frequencies = []
        monetary = []
        for p in self.profiles.values():
            recencies.append(now - p.last_order)
            frequencies.append(p.order_count)
            monetary.append(p.total_spent)
        recencies.sort()
        frequencies.sort()
        monetary.sort()
        def quintile(val, sorted_vals):
            idx = sorted_vals.index(val) if val in sorted_vals else int(len(sorted_vals) * val / max(sorted_vals)) if sorted_vals else 0
            return min(5, max(1, int(idx / len(sorted_vals) * 5) + 1))
        for cid, p in self.profiles.items():
            r = 6 - quintile(now - p.last_order, recencies)  # lower recency = higher score
            f = quintile(p.order_count, frequencies)
            m = quintile(p.total_spent, monetary)
            self.rfm_scores[cid] = {"R": r, "F": f, "M": m, "RFM": r + f + m}
        return self.rfm_scores

    def segment(self, customer_id: str) -> str:
        score = self.rfm_scores.get(customer_id, {})
        rfm = score.get("RFM", 0)
        if rfm >= 13:
            return "CHAMPION"
        elif rfm >= 10:
            return "LOYAL"
        elif rfm >= 7:
            return "POTENTIAL"
        elif rfm >= 4:
            return "AT_RISK"
        return "LOST"

    def stats(self) -> Dict:
        return {"customers": len(self.profiles), "segments": len(set(self.segment(c) for c in self.profiles))}

def run():
    cp = CustomerProfiler()
    cp.add_transaction("C1", 500, 1000)
    cp.add_transaction("C1", 300, 2000)
    cp.add_transaction("C2", 50, 3000)
    cp.rfm_analysis(4000)
    for c in cp.profiles:
        print(c, cp.rfm_scores[c], cp.segment(c))
    print(cp.stats())

if __name__ == "__main__":
    run()

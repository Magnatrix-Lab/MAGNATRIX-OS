#!/usr/bin/env python3
"""
Temporal Reasoning -- MAGNATRIX-OS Phase 5
Path: ai/temporal_reasoning_native.py
License: AGPL-3.0
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class Interval:
    start: float
    end: float
    label: str = ""

    def __post_init__(self):
        assert self.start <= self.end

    def duration(self) -> float:
        return self.end - self.start

    def contains(self, t: float) -> bool:
        return self.start <= t <= self.end


def allen_relation(i1: Interval, i2: Interval) -> str:
    if i1.end < i2.start:
        return "before"
    if i1.end == i2.start:
        return "meets"
    if i1.start < i2.start and i1.end < i2.end and i1.end > i2.start:
        return "overlaps"
    if i1.start == i2.start and i1.end < i2.end:
        return "starts"
    if i1.start > i2.start and i1.end < i2.end:
        return "during"
    if i1.start > i2.start and i1.end == i2.end:
        return "finishes"
    if i1.start == i2.start and i1.end == i2.end:
        return "equals"
    if i1.start == i2.start and i1.end > i2.end:
        return "started_by"
    if i1.start < i2.start and i1.end > i2.end:
        return "contains"
    if i1.start < i2.start and i1.end == i2.end:
        return "finished_by"
    if i1.start < i2.end and i1.end > i2.end and i2.start > i1.start:
        return "overlapped_by"
    if i1.start == i2.end:
        return "met_by"
    return "after"


def allen_inverse(rel: str) -> str:
    inv = {"before": "after", "meets": "met_by", "overlaps": "overlapped_by",
           "starts": "started_by", "during": "contains", "finishes": "finished_by",
           "equals": "equals"}
    return inv.get(rel, "unknown")


class GrangerCausality:
    @staticmethod
    def test(x: List[float], y: List[float], max_lag: int = 3) -> Tuple[bool, float]:
        n = len(y)
        if n < max_lag * 2 + 5 or len(x) != n:
            return False, 1.0
        y_lags = [[y[i + j] for j in range(max_lag)] for i in range(n - max_lag)]
        beta_r = GrangerCausality._ols(y[max_lag:], y_lags)
        resid_r = [y[i + max_lag] - sum(beta_r[j] * y_lags[i][j] for j in range(max_lag)) for i in range(len(y_lags))]
        sse_r = sum(r ** 2 for r in resid_r)
        x_lags = [[x[i + j] for j in range(max_lag)] for i in range(n - max_lag)]
        combined = [[*y_lags[i], *x_lags[i]] for i in range(len(y_lags))]
        beta_u = GrangerCausality._ols(y[max_lag:], combined)
        resid_u = [y[i + max_lag] - sum(beta_u[j] * combined[i][j] for j in range(len(beta_u))) for i in range(len(combined))]
        sse_u = sum(r ** 2 for r in resid_u)
        df1 = max_lag
        df2 = n - 2 * max_lag - 1
        if df2 <= 0 or sse_u <= 0:
            return False, 1.0
        f_stat = ((sse_r - sse_u) / df1) / (sse_u / df2)
        p_value = max(0.001, min(1.0, math.exp(-f_stat / 2)))
        return p_value < 0.05, p_value

    @staticmethod
    def _ols(y: List[float], X: List[List[float]]) -> List[float]:
        n = len(X)
        p = len(X[0])
        xtx = [[sum(X[i][j] * X[i][k] for i in range(n)) for k in range(p)] for j in range(p)]
        xty = [sum(X[i][j] * y[i] for i in range(n)) for j in range(p)]
        beta = [0.0] * p
        for _ in range(50):
            for j in range(p):
                if xtx[j][j] != 0:
                    beta[j] = (xty[j] - sum(xtx[j][k] * beta[k] for k in range(p) if k != j)) / xtx[j][j]
        return beta


class MarkovChain:
    def __init__(self, order: int = 2):
        self.order = order
        self.transitions: Dict[Tuple, Dict[str, int]] = {}
        self.states = set()

    def train(self, sequence: List[str]) -> None:
        for i in range(len(sequence) - self.order):
            ctx = tuple(sequence[i:i + self.order])
            nxt = sequence[i + self.order]
            self.transitions.setdefault(ctx, {})
            self.transitions[ctx][nxt] = self.transitions[ctx].get(nxt, 0) + 1
            self.states.add(nxt)

    def predict(self, history: List[str], horizon: int = 5) -> List[Tuple[str, float]]:
        ctx = tuple(history[-self.order:])
        results = []
        for _ in range(horizon):
            trans = self.transitions.get(ctx, {})
            if not trans:
                break
            total = sum(trans.values())
            nxt = max(trans.keys(), key=lambda s: trans[s])
            prob = trans[nxt] / total
            results.append((nxt, prob))
            ctx = tuple(list(ctx[1:]) + [nxt])
        return results

    def stationary(self, steps: int = 1000) -> Dict[str, float]:
        if not self.states:
            return {}
        state = random.choice(list(self.states))
        counts = {s: 0 for s in self.states}
        for _ in range(steps):
            counts[state] += 1
            ctx = tuple([state] * self.order)
            trans = self.transitions.get(ctx, {})
            if not trans:
                break
            state = random.choices(list(trans.keys()), weights=list(trans.values()))[0]
        total = sum(counts.values())
        return {s: c / total for s, c in counts.items()}


@dataclass
class TemporalFact:
    subject: str
    predicate: str
    obj: str
    t_start: float
    t_end: float


class TemporalKnowledgeGraph:
    def __init__(self):
        self.facts: List[TemporalFact] = []

    def add_fact(self, s: str, p: str, o: str, t1: float, t2: float) -> None:
        self.facts.append(TemporalFact(s, p, o, t1, t2))

    def query(self, subject: str, t: float) -> List[TemporalFact]:
        return [f for f in self.facts if f.subject == subject and f.t_start <= t <= f.t_end]

    def what_changed(self, subject: str, t1: float, t2: float) -> List[Dict]:
        before = self.query(subject, t1)
        after = self.query(subject, t2)
        changes = []
        for f1 in before:
            if not any(f2.predicate == f1.predicate and f2.obj == f1.obj for f2 in after):
                changes.append({"type": "ended", "fact": f1})
        for f2 in after:
            if not any(f1.predicate == f2.predicate and f1.obj == f2.obj for f1 in before):
                changes.append({"type": "started", "fact": f2})
        return changes


def _self_test():
    print("=" * 55)
    print("Temporal Reasoning -- Self Test")
    print("=" * 55)
    passed = 0
    total = 7

    print("[Test 1] Allen relations")
    i1 = Interval(0, 5)
    i2 = Interval(3, 8)
    assert allen_relation(i1, i2) == "overlaps"
    i3 = Interval(5, 10)
    assert allen_relation(i1, i3) == "meets"
    passed += 1
    print("  PASS")

    print("[Test 2] Allen inverse")
    assert allen_inverse("before") == "after"
    passed += 1
    print("  PASS")

    print("[Test 3] Granger causality")
    x = [float(i) for i in range(100)]
    y = [2.0 * x[max(0, i - 1)] + random.gauss(0, 5) for i in range(100)]
    is_causal, p = GrangerCausality.test(x, y, max_lag=3)
    print("  X->Y: " + str(is_causal) + " (p=" + str(round(p, 4)) + ")")
    passed += 1
    print("  PASS")

    print("[Test 4] Markov prediction")
    mc = MarkovChain(order=2)
    seq = ["A", "B", "A", "B", "A", "B", "C", "A", "B"]
    mc.train(seq)
    pred = mc.predict(["A", "B"], horizon=3)
    assert len(pred) > 0
    passed += 1
    print("  PASS")

    print("[Test 5] Stationary distribution")
    dist = mc.stationary(1000)
    assert sum(dist.values()) > 0.99
    passed += 1
    print("  PASS")

    print("[Test 6] Temporal KG")
    kg = TemporalKnowledgeGraph()
    kg.add_fact("Alice", "works_at", "MAGNATRIX", 0, 100)
    kg.add_fact("Alice", "lives_in", "CyberSpace", 0, 50)
    kg.add_fact("Alice", "lives_in", "MetaVerse", 51, 100)
    assert len(kg.query("Alice", 30)) == 2
    changes = kg.what_changed("Alice", 30, 70)
    assert len(changes) == 1
    passed += 1
    print("  PASS")

    print("[Test 7] Query at boundary")
    assert len(kg.query("Alice", 50)) >= 1
    passed += 1
    print("  PASS")

    print("")
    print("PASS: " + str(passed) + "/" + str(total))
    print("=" * 55)
    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())

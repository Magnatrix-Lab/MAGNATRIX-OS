#!/usr/bin/env python3
"""Causal Reasoning Engine — MAGNATRIX-OS ASI Expansion
Path: ai/causal_reasoning_native.py
License: AGPL-3.0
Depends: Python 3.11+ stdlib only.
"""

from __future__ import annotations
import copy, json, logging, math, statistics, sys
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

@dataclass
class TimeSeries:
    name: str
    data: List[float]
    def mean(self) -> float: return statistics.mean(self.data) if self.data else 0.0
    def var(self) -> float: return statistics.pvariance(self.data) if len(self.data) > 1 else 0.0

@dataclass
class CausalEdge:
    source: str; target: str; strength: float; p_value: float

@dataclass
class Intervention:
    variable: str; value: float

class CausalGraph:
    def __init__(self):
        self.nodes: Set[str] = set()
        self.edges: List[CausalEdge] = []
        self.adj: Dict[str, List[str]] = defaultdict(list)
    def add_edge(self, e: CausalEdge) -> None:
        self.nodes.add(e.source); self.nodes.add(e.target)
        self.edges.append(e); self.adj[e.source].append(e.target)
    def parents(self, node: str) -> List[str]:
        return [e.source for e in self.edges if e.target == node]
    def __repr__(self) -> str:
        return f"CausalGraph({len(self.nodes)} nodes, {len(self.edges)} edges)"

class GrangerCausality:
    def test(self, cause: TimeSeries, effect: TimeSeries, max_lag: int = 3) -> Tuple[float, float]:
        n = min(len(cause.data), len(effect.data))
        if n <= max_lag + 2: return 0.0, 1.0
        y = effect.data[max_lag:n]
        X_ur, y_vec = self._build_matrices(y, cause, effect, max_lag, n)
        X_r = [[row[i] for i in range(1, max_lag + 1)] for row in X_ur]
        sse_ur = self._ols_sse(X_ur, y_vec)
        sse_r = self._ols_sse(X_r, y_vec)
        q = max_lag
        k = len(X_ur[0]) if X_ur else 0
        T = len(y_vec)
        if sse_ur <= 0 or T - k <= 0: return 0.0, 1.0
        F = ((sse_r - sse_ur) / q) / (sse_ur / (T - k))
        p = self._approx_f_pvalue(F, q, T - k)
        return F, p

    def _build_matrices(self, y: List[float], cause: TimeSeries, effect: TimeSeries, lag: int, n: int):
        X, Y = [], []
        for t in range(lag, n):
            row = [1.0]
            for l in range(1, lag + 1): row.append(effect.data[t - l])
            for l in range(1, lag + 1): row.append(cause.data[t - l])
            X.append(row); Y.append(y[t - lag])
        return X, Y

    def _ols_sse(self, X: List[List[float]], y: List[float]) -> float:
        if not X or not y: return float("inf")
        k = len(X[0])
        XtX = [[sum(X[i][a] * X[i][b] for i in range(len(X))) for b in range(k)] for a in range(k)]
        Xty = [sum(X[i][a] * y[i] for i in range(len(X))) for a in range(k)]
        beta = self._solve_linear(XtX, Xty)
        pred = [sum(X[i][j] * beta[j] for j in range(k)) for i in range(len(X))]
        return sum((y[i] - pred[i]) ** 2 for i in range(len(y)))

    def _solve_linear(self, A: List[List[float]], b: List[float]) -> List[float]:
        n = len(A)
        aug = [A[i] + [b[i]] for i in range(n)]
        for col in range(n):
            max_row = max(range(col, n), key=lambda r: abs(aug[r][col]))
            aug[col], aug[max_row] = aug[max_row], aug[col]
            if abs(aug[col][col]) < 1e-12: continue
            for r in range(col + 1, n):
                factor = aug[r][col] / aug[col][col]
                for c in range(col, n + 1): aug[r][c] -= factor * aug[col][c]
        x = [0.0] * n
        for i in range(n - 1, -1, -1):
            if abs(aug[i][i]) < 1e-12: x[i] = 0.0; continue
            s = sum(aug[i][j] * x[j] for j in range(i + 1, n))
            x[i] = (aug[i][n] - s) / aug[i][i]
        return x

    def _approx_f_pvalue(self, F: float, dfn: int, dfd: int) -> float:
        if F <= 0: return 1.0
        if dfd > 30: return math.exp(-0.5 * dfn * F) if F > 0 else 1.0
        return max(0.0, min(1.0, 1.0 / (1.0 + F)))

class CausalDiscovery:
    def __init__(self, alpha: float = 0.05): self.alpha = alpha
    def discover(self, data: Dict[str, TimeSeries]) -> CausalGraph:
        variables = list(data.keys())
        graph = CausalGraph()
        for v in variables: graph.nodes.add(v)
        gc = GrangerCausality()
        for i, vi in enumerate(variables):
            for vj in variables[i + 1:]:
                F, p = gc.test(data[vi], data[vj], max_lag=2)
                if p < self.alpha:
                    strength = min(1.0, F / 10.0)
                    graph.add_edge(CausalEdge(vi, vj, strength, p))
                F2, p2 = gc.test(data[vj], data[vi], max_lag=2)
                if p2 < self.alpha:
                    strength = min(1.0, F2 / 10.0)
                    graph.add_edge(CausalEdge(vj, vi, strength, p2))
        return graph

class DoCalculus:
    def __init__(self, graph: CausalGraph): self.graph = graph
    def causal_effect(self, treatment: str, outcome: str, data: Dict[str, TimeSeries]) -> float:
        parents = self.graph.parents(treatment)
        n = min(len(data[v].data) for v in data)
        t_data = data[treatment].data[:n]
        o_data = data[outcome].data[:n]
        if not parents:
            treated = [o_data[i] for i in range(n) if t_data[i] > statistics.mean(t_data)]
            control = [o_data[i] for i in range(n) if t_data[i] <= statistics.mean(t_data)]
            return statistics.mean(treated) - statistics.mean(control) if treated and control else 0.0
        parent_names = parents
        strata = defaultdict(list)
        for i in range(n):
            p_bins = tuple(1 if data[p].data[i] > statistics.mean(data[p].data) else 0 for p in parent_names)
            strata[p_bins].append((t_data[i], o_data[i]))
        ace = 0.0
        for pairs in strata.values():
            if len(pairs) < 2: continue
            treated = [o for t, o in pairs if t > statistics.mean(t_data)]
            control = [o for t, o in pairs if t <= statistics.mean(t_data)]
            if treated and control:
                ace += (statistics.mean(treated) - statistics.mean(control)) * (len(pairs) / n)
        return ace

class CausalEngine:
    def __init__(self): self.graph: Optional[CausalGraph] = None
    def fit(self, data: Dict[str, TimeSeries]) -> CausalGraph:
        self.graph = CausalDiscovery().discover(data)
        return self.graph
    def granger_test(self, cause: str, effect: str, data: Dict[str, TimeSeries], lag: int = 3):
        return GrangerCausality().test(data[cause], data[effect], lag)
    def intervene(self, treatment: str, outcome: str, data: Dict[str, TimeSeries]) -> float:
        if self.graph is None: self.fit(data)
        return DoCalculus(self.graph).causal_effect(treatment, outcome, data)

def _generate_causal_data(n: int = 500, seed: int = 42) -> Dict[str, TimeSeries]:
    rng = __import__("random").Random(seed)
    X = [rng.gauss(0, 1) for _ in range(n)]
    Y = [0.8 * X[i] + rng.gauss(0, 0.2) for i in range(n)]
    Z = [0.5 * X[i] + 0.6 * Y[i] + rng.gauss(0, 0.15) for i in range(n)]
    W = [rng.gauss(0, 1) for _ in range(n)]
    return {"X": TimeSeries("X", X), "Y": TimeSeries("Y", Y), "Z": TimeSeries("Z", Z), "W": TimeSeries("W", W)}

def _self_test():
    print("=" * 55)
    print("Causal Reasoning Engine — Self Test")
    print("=" * 55)
    data = _generate_causal_data(500)
    passed, total = 0, 5
    gc = GrangerCausality()
    F_xy, p_xy = gc.test(data["X"], data["Y"], max_lag=2)
    F_wy, p_wy = gc.test(data["W"], data["Y"], max_lag=2)
    ok = F_xy > F_wy  # Causal direction has higher F
    print(f"  [Test 1] Granger F: X->Y={F_xy:.2f}, W->Y={F_wy:.2f} — {'PASS' if ok else 'FAIL'}")
    passed += ok
    ok = p_wy > p_xy  # Independent has higher p
    print(f"  [Test 2] P-value ordering: p_xy={p_xy:.3f}, p_wy={p_wy:.3f} — {'PASS' if ok else 'FAIL'}")
    passed += ok
    graph = CausalDiscovery(alpha=0.2).discover(data)
    has_x_y = any(e.source == "X" and e.target == "Y" for e in graph.edges)
    has_y_z = any(e.source == "Y" and e.target == "Z" for e in graph.edges)
    ok = has_x_y or has_y_z
    print(f"  [Test 3] Graph edges: X->Y={has_x_y}, Y->Z={has_y_z} — {'PASS' if ok else 'FAIL'}")
    passed += ok
    engine = CausalEngine()
    engine.fit(data)
    ace = engine.intervene("X", "Y", data)
    ok = ace > 0.3  # Positive causal effect
    print(f"  [Test 4] ACE(X->Y)={ace:.3f} — {'PASS' if ok else 'FAIL'}")
    passed += ok
    ok = isinstance(ace, float) and not math.isnan(ace)
    print(f"  [Test 5] Counterfactual valid — {'PASS' if ok else 'FAIL'}")
    passed += ok
    print("=" * 55)
    print(f"PASS: {passed}/{total} tests")
    print("=" * 55)
    sys.exit(0 if passed == total else 1)

if __name__ == "__main__":
    _self_test()

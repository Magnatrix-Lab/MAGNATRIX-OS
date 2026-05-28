"""
temporal_engine_native.py — Time-Series Causal Simulation Engine
Phase 5: Temporal Engine for MAGNATRIX OS Runtime.
Pure Python stdlib only. ~700 baris.
"""

from __future__ import annotations

import math
import sys
import json
from collections import defaultdict, deque
from itertools import count
from typing import Dict, List, Tuple, Set, Optional, Callable, Any, Union, Iterator

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------
State = Dict[str, Any]
History = Dict[int, State]
InterventionMap = Dict[int, State]
Event = Tuple[int, str, Any]          # (time, variable, value)

# ---------------------------------------------------------------------------
# Causal function registry
# ---------------------------------------------------------------------------
class CausalFunction:
    """Helper namespace for reusable node functions."""

    @staticmethod
    def linear(weights: Optional[Dict[str, float]] = None,
               bias: float = 0.0) -> Callable[[Dict[str, Any]], float]:
        """Weighted sum with optional bias."""
        w = weights or {}
        def _f(parents: Dict[str, Any]) -> float:
            total = float(bias)
            for p, val in parents.items():
                total += float(w.get(p, 1.0 / max(len(parents), 1))) * float(val)
            return total
        return _f

    @staticmethod
    def threshold(weights: Optional[Dict[str, float]] = None,
                  bias: float = 0.0,
                  cutoff: float = 0.0) -> Callable[[Dict[str, Any]], float]:
        """Step function: 1.0 if sum >= cutoff else 0.0."""
        base = CausalFunction.linear(weights, bias)
        def _f(parents: Dict[str, Any]) -> float:
            return 1.0 if base(parents) >= cutoff else 0.0
        return _f

    @staticmethod
    def boolean_and() -> Callable[[Dict[str, Any]], float]:
        def _f(parents: Dict[str, Any]) -> float:
            return 1.0 if all(float(v) > 0.5 for v in parents.values()) else 0.0
        return _f

    @staticmethod
    def boolean_or() -> Callable[[Dict[str, Any]], float]:
        def _f(parents: Dict[str, Any]) -> float:
            return 1.0 if any(float(v) > 0.5 for v in parents.values()) else 0.0
        return _f


# ---------------------------------------------------------------------------
# Temporal Graph
# ---------------------------------------------------------------------------
class TemporalGraph:
    """
    Causal Time Graph with time-lagged edges.

    Edges: u --[lag]--> v  means  value of u at time t influences v at time t+lag.
    Cycles in the compact graph are allowed as long as every cycle has at least
    one positive lag, which makes the unfolded graph a DAG.
    """

    def __init__(self):
        self.nodes: Set[str] = set()
        self.edges: List[Tuple[str, str, int]] = []  # (u, v, lag)
        self._parents: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
        self._children: Dict[str, List[Tuple[str, int]]] = defaultdict(list)
        self._node_func: Dict[str, Callable[[Dict[str, Any]], Any]] = {}
        self._node_meta: Dict[str, Dict[str, Any]] = {}
        self._history: History = {}

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------
    def add_node(self, name: str,
                 func: Optional[Callable[[Dict[str, Any]], Any]] = None,
                 **meta: Any) -> TemporalGraph:
        """Register a variable node. Optional custom causal function."""
        self.nodes.add(name)
        if func is not None:
            self._node_func[name] = func
        self._node_meta[name] = meta
        return self

    def add_edge(self, u: str, v: str, lag: int) -> TemporalGraph:
        """
        Add time-lagged causal edge: u at time t -> v at time t+lag.
        Raises ValueError for invalid lags or degenerate self-loops.
        """
        if lag < 0:
            raise ValueError("Lag must be non-negative")
        if lag == 0 and u == v:
            raise ValueError("Self-loop with lag=0 is not allowed (unfolded cycle)")
        self.nodes.add(u)
        self.nodes.add(v)
        self.edges.append((u, v, lag))
        self._parents[v].append((u, lag))
        self._children[u].append((v, lag))
        return self

    # ------------------------------------------------------------------
    # Internal computation helpers
    # ------------------------------------------------------------------
    def _default_func(self, node: str, parent_vals: Dict[str, Any]) -> float:
        """Default linear combination of parent values."""
        meta = self._node_meta.get(node, {})
        weights: Dict[str, float] = meta.get("weights", {})
        bias: float = float(meta.get("bias", 0.0))
        if not weights and parent_vals:
            n = len(parent_vals)
            weights = {p: 1.0 / n for p in parent_vals}
        total = bias
        for p, val in parent_vals.items():
            w = weights.get(p, 1.0 / max(len(parent_vals), 1))
            total += w * float(val)
        return total

    def _compute_node(self, node: str, t: int, history: History) -> Any:
        """Compute natural value of `node` at time `t` from prior history."""
        # Return cached if present (should not happen during forward sim unless pre-filled)
        if t in history and node in history[t]:
            return history[t][node]

        parent_vals: Dict[str, Any] = {}
        for p, lag in self._parents[node]:
            pt = t - lag
            if pt in history and p in history[pt]:
                parent_vals[p] = history[pt][p]
            elif pt < 0:
                parent_vals[p] = 0.0
            else:
                parent_vals[p] = history.get(pt, {}).get(p, 0.0)

        if node in self._node_func:
            return self._node_func[node](parent_vals)
        return self._default_func(node, parent_vals)

    # ------------------------------------------------------------------
    # Forward simulation
    # ------------------------------------------------------------------
    def simulate(self,
                 start_state: State,
                 steps: int,
                 interventions: Optional[InterventionMap] = None) -> History:
        """
        Forward causal simulation.

        Parameters
        ----------
        start_state : dict
            Initial values at t=0.
        steps : int
            Number of steps to simulate (produces t=1..steps).
        interventions : dict, optional
            {t: {node: value}} forced overrides.

        Returns
        -------
        history : dict
            {t: {node: value}} for t=0..steps.
        """
        interventions = interventions or {}
        history: History = {0: dict(start_state)}
        for node in self.nodes:
            if node not in history[0]:
                history[0][node] = 0.0

        for t in range(1, steps + 1):
            state: State = {}
            # Hard interventions take precedence
            if t in interventions:
                state.update(interventions[t])

            for node in self.nodes:
                if node in state:
                    continue
                state[node] = self._compute_node(node, t, history)

            history[t] = state

        self._history = history
        return history

    # ------------------------------------------------------------------
    # Time-unfolding
    # ------------------------------------------------------------------
    def unfold(self, steps: int) -> Dict[int, List[Tuple[Tuple[str, int], Tuple[str, int]]]]:
        """
        Convert time-lag graph into expanded temporal network edges.

        Returns
        -------
        dict
            {t: [((u, t), (v, t+lag)), ...]} for t=0..steps.
        """
        unfolded: Dict[int, List[Tuple[Tuple[str, int], Tuple[str, int]]]] = defaultdict(list)
        for t in range(steps + 1):
            for u, v, lag in self.edges:
                if t + lag <= steps:
                    unfolded[t].append(((u, t), (v, t + lag)))
        return dict(unfolded)

    def unfold_adjacency(self, steps: int) -> Tuple[Dict[Tuple[str, int], List[Tuple[str, int]]], Set[Tuple[str, int]]]:
        """
        Adjacency list of the unfolded graph.

        Returns
        -------
        adj : dict
            {(node, t): [(child_node, child_t), ...]}
        nodes : set
            All (node, t) vertices.
        """
        adj: Dict[Tuple[str, int], List[Tuple[str, int]]] = defaultdict(list)
        nodes: Set[Tuple[str, int]] = set()
        for t in range(steps + 1):
            for n in self.nodes:
                nodes.add((n, t))
        for t in range(steps + 1):
            for u, v, lag in self.edges:
                if t + lag <= steps:
                    adj[(u, t)].append((v, t + lag))
        return adj, nodes

    def unfold_reverse_adjacency(self, steps: int) -> Dict[Tuple[str, int], List[Tuple[str, int]]]:
        """Reverse adjacency of unfolded graph (for backward induction)."""
        adj, nodes = self.unfold_adjacency(steps)
        rev: Dict[Tuple[str, int], List[Tuple[str, int]]] = {n: [] for n in nodes}
        for src, dsts in adj.items():
            for d in dsts:
                rev[d].append(src)
        return rev

    def get_temporal_paths(self, u: str, v: str, max_lag: int) -> List[List[Tuple[str, int]]]:
        """
        Find all temporal paths from u to v where total lag <= max_lag.
        Each path is a list of (node, cumulative_lag) tuples.
        """
        paths: List[List[Tuple[str, int]]] = []
        stack: List[Tuple[str, int, List[Tuple[str, int]]]] = [(u, 0, [(u, 0)])]
        while stack:
            cur, lag_sofar, path = stack.pop()
            if cur == v and lag_sofar > 0:
                paths.append(list(path))
                continue
            for child, clag in self._children[cur]:
                new_lag = lag_sofar + clag
                if new_lag <= max_lag and (child, new_lag) not in path:
                    stack.append((child, new_lag, path + [(child, new_lag)]))
        return paths

    # ------------------------------------------------------------------
    # Intervention planning (backward induction)
    # ------------------------------------------------------------------
    def plan_intervention(self,
                          target_state: State,
                          deadline: int,
                          controllable: Optional[Set[str]] = None) -> List[Event]:
        """
        Given desired future state at `deadline`, work backward to find minimal
        interventions at specific times.

        Parameters
        ----------
        target_state : dict
            {variable: desired_value} at time `deadline`.
        deadline : int
            Target time step.
        controllable : set, optional
            Subset of nodes we are allowed to intervene on. If None, all nodes.

        Returns
        -------
        list of (time, variable, value)
            Ordered intervention plan (earliest first).
        """
        controllable = controllable or self.nodes
        needed: Dict[Tuple[str, int], float] = {
            (v, deadline): float(val) for v, val in target_state.items()
        }
        interventions: List[Event] = []
        visited: Set[Tuple[str, int]] = set()
        queued: Set[Tuple[str, int]] = set()

        # Seed queue in reverse chronological order
        queue = deque(sorted(needed.keys(), key=lambda x: -x[1]))
        for item in queue:
            queued.add(item)

        while queue:
            node, t = queue.popleft()
            queued.discard((node, t))
            if (node, t) in visited:
                continue
            visited.add((node, t))
            val = needed[(node, t)]

            # If node is uncontrollable, we MUST satisfy it through parents.
            # If controllable, we have a choice: intervene directly OR recurse.
            # Heuristic: recurse to parents first (fewer direct interventions).
            # If parent recursion fails (e.g., time < 0), fall back to direct.
            parents = self._parents[node]
            directly_intervene = False

            if not parents:
                # Root variable — no parents to push to
                if node in controllable:
                    interventions.append((t, node, val))
                else:
                    raise ValueError(f"Uncontrollable root {node} cannot satisfy requirement at t={t}")
                continue

            # Attempt backward propagation to parents
            meta = self._node_meta.get(node, {})
            weights: Dict[str, float] = meta.get("weights", {})
            bias: float = float(meta.get("bias", 0.0))
            if not weights:
                n = len(parents)
                weights = {p: 1.0 / n for p, _ in parents}

            residual = val - bias
            w2_sum = sum(weights.get(p, 1.0 / len(parents)) ** 2 for p, _ in parents)

            propagated = True
            for p, lag in parents:
                pt = t - lag
                if pt < 0:
                    propagated = False
                    break
                w = weights.get(p, 1.0 / len(parents))
                p_needed = residual * w / w2_sum if abs(w2_sum) > 1e-12 else residual / len(parents)

                # If parent is not controllable, we must further recurse later
                # For now, just record the need. Conflicts are checked below.
                if (p, pt) in needed:
                    if abs(needed[(p, pt)] - p_needed) > 1e-6:
                        # Parent already has a conflicting requirement.
                        # Cannot satisfy both simultaneously through this node;
                        # fall back to direct intervention on current node.
                        propagated = False
                        break
                else:
                    needed[(p, pt)] = p_needed
                    if (p, pt) not in visited and (p, pt) not in queued:
                        queue.append((p, pt))
                        queued.add((p, pt))

            if not propagated or node not in controllable:
                if node not in controllable:
                    raise ValueError(
                        f"Cannot satisfy {node} at t={t} through parents and node is uncontrollable"
                    )
                # Sort queue again to maintain reverse chronological order
                interventions.append((t, node, val))
                # Remove parent needs that were added in this failed attempt
                if not propagated:
                    for p, lag in parents:
                        pt = t - lag
                        if pt >= 0 and (p, pt) in needed and (p, pt) not in visited:
                            # Only remove if we just added it and no one else needs it
                            # Simple: remove and re-add to queue if another child needs it
                            del needed[(p, pt)]
                            if (p, pt) in queued:
                                # Rebuild queue cleanly
                                pass
                    # Rebuild queue from remaining needed items not visited
                    queue = deque(sorted(
                        [k for k in needed if k not in visited],
                        key=lambda x: -x[1]
                    ))
                    queued = set(queue)

        # Deduplicate interventions and sort by time
        seen: Set[Tuple[int, str]] = set()
        unique: List[Event] = []
        for iv in sorted(interventions, key=lambda x: (x[0], x[1])):
            k = (iv[0], iv[1])
            if k not in seen:
                seen.add(k)
                unique.append(iv)

        return unique

    # ------------------------------------------------------------------
    # Temporal consistency checker
    # ------------------------------------------------------------------
    def check_consistency(self,
                          events: List[Event],
                          start_state: Optional[State] = None,
                          treat_as_interventions: bool = False) -> bool:
        """
        Verify that a set of events doesn't create logical paradoxes.

        Parameters
        ----------
        events : list of (time, variable, value)
        start_state : dict, optional
            Initial state at t=0.
        treat_as_interventions : bool
            If True, events are hard interventions and can override natural
            causality without being paradoxical. Paradoxes are detected only
            when events' downstream effects conflict with each other.
            If False (default), events are treated as observations that must
            agree with causal laws; any deviation is a paradox.

        Returns
        -------
        bool
            True if consistent, False if a paradox is detected.
        """
        if not events:
            return True

        # ---- Check 1: no duplicate conflicting assignments ----
        forced: Dict[Tuple[int, str], float] = {}
        for t, v, val in events:
            key = (t, v)
            if key in forced:
                if abs(forced[key] - float(val)) > 1e-9:
                    return False  # Direct contradiction
            else:
                forced[key] = float(val)

        max_t = max(t for t, _, _ in events)

        # ---- Check 2: causal violations (observations vs laws) ----
        if not treat_as_interventions:
            start_state = start_state or {}
            history: History = {0: dict(start_state)}
            for node in self.nodes:
                if node not in history[0]:
                    history[0][node] = 0.0

            # Group events by time for quick lookup
            time_events: Dict[int, Dict[str, float]] = defaultdict(dict)
            for t, v, val in events:
                time_events[t][v] = float(val)

            for t in range(1, max_t + 1):
                state: State = {}
                for node in self.nodes:
                    state[node] = self._compute_node(node, t, history)

                for v, claimed in time_events.get(t, {}).items():
                    natural = state[v]
                    # Exogenous (root) nodes are not bound by causal parent laws;
                    # their observed values are always valid.
                    if not self._parents[v]:
                        continue
                    if abs(float(natural) - claimed) > 1e-6:
                        # Event contradicts what causality would produce
                        return False

                # Advance history with events as actual state for downstream
                for v, claimed in time_events.get(t, {}).items():
                    state[v] = claimed
                history[t] = state

        # ---- Check 3: event dependency cycles (grandfather paradox) ----
        # Build reachability among events via unfolded graph.
        # If event A's effect can reach event B's node/time, and B's effect
        # can reach A's node/time, we have a causal loop among interventions.
        # In an acyclic unfolded graph this should not happen, but if users
        # supply zero-lag edges or self-referential events, it catches them.
        adj, _ = self.unfold_adjacency(max_t)
        event_map: Dict[Tuple[int, str], List[int]] = defaultdict(list)
        for idx, (t, v, _) in enumerate(events):
            event_map[(t, v)].append(idx)

        # Compute forward reachability from each event's (node, time)
        reach: Dict[int, Set[Tuple[str, int]]] = {}
        for idx, (t, v, _) in enumerate(events):
            visited_eff: Set[Tuple[str, int]] = set()
            q = deque([(v, t)])
            while q:
                cur = q.popleft()
                if cur in visited_eff:
                    continue
                visited_eff.add(cur)
                for nxt in adj.get(cur, []):
                    q.append(nxt)
            reach[idx] = visited_eff

        # Build dependency graph: i -> j if event i can causally affect event j
        n_events = len(events)
        deps: Dict[int, Set[int]] = {i: set() for i in range(n_events)}
        for i in range(n_events):
            ti, vi, _ = events[i]
            for j in range(n_events):
                if i == j:
                    continue
                tj, vj, _ = events[j]
                if (vj, tj) in reach[i]:
                    deps[i].add(j)

        # Topological sort to detect cycles
        in_deg = {i: 0 for i in range(n_events)}
        for i in range(n_events):
            for j in deps[i]:
                in_deg[j] += 1

        topo = deque([i for i in range(n_events) if in_deg[i] == 0])
        processed = 0
        while topo:
            i = topo.popleft()
            processed += 1
            for j in deps[i]:
                in_deg[j] -= 1
                if in_deg[j] == 0:
                    topo.append(j)

        if processed != n_events:
            return False  # Cycle among event dependencies -> paradox

        return True

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        """Serialize graph structure to plain dict."""
        return {
            "nodes": sorted(self.nodes),
            "edges": [
                {"from": u, "to": v, "lag": lag}
                for u, v, lag in self.edges
            ],
            "node_meta": {k: dict(v) for k, v in self._node_meta.items()},
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> TemporalGraph:
        """Deserialize from plain dict."""
        g = cls()
        for n in d.get("nodes", []):
            g.add_node(n, **d.get("node_meta", {}).get(n, {}))
        for e in d.get("edges", []):
            g.add_edge(e["from"], e["to"], e["lag"])
        return g

    def __repr__(self) -> str:
        return f"<TemporalGraph nodes={len(self.nodes)} edges={len(self.edges)}>"


# ---------------------------------------------------------------------------
# Self-test suite
# ---------------------------------------------------------------------------
def _assert_close(a: float, b: float, eps: float = 1e-6) -> None:
    if abs(a - b) > eps:
        raise AssertionError(f"Expected {b}, got {a}")


def _run_tests() -> Tuple[int, int]:
    passed = 0
    total = 0

    def _test(name: str, fn: Callable[[], None]) -> None:
        nonlocal passed, total
        total += 1
        try:
            fn()
            print(f"  PASS  {name}")
            passed += 1
        except Exception as exc:
            print(f"  FAIL  {name} — {exc}")

    # ------------------- Test 1: basic simulate -------------------
    def t1() -> None:
        g = TemporalGraph()
        g.add_edge("X", "Y", lag=1)
        g.add_edge("Y", "Z", lag=1)
        hist = g.simulate({"X": 1.0}, steps=3)
        _assert_close(hist[0]["X"], 1.0)
        _assert_close(hist[0]["Y"], 0.0)
        # t=1: Y gets X=1 from t=0 -> Y=1; Z still 0
        _assert_close(hist[1]["Y"], 1.0)
        _assert_close(hist[1]["Z"], 0.0)
        # t=2: Y gets X=1 again (X held at 1? No, X has no parents so stays 1 if start_state)
        # Wait: X has no parents, so at t=1 X is computed. No parents -> default 0.
        # So X drops to 0 after t=0 unless we add an intervention or self-loop.
        # Let's recompute: start_state only sets t=0. At t=1, X has no parents -> 0.
        # So Y at t=1 gets X(t=0)=1 -> Y=1. Z at t=2 gets Y(t=1)=1 -> Z=1.
        _assert_close(hist[2]["Z"], 1.0)

    _test("basic simulate chain", t1)

    # ------------------- Test 2: unfold structure -------------------
    def t2() -> None:
        g = TemporalGraph()
        g.add_edge("A", "B", lag=1)
        g.add_edge("B", "C", lag=2)
        uf = g.unfold(steps=4)
        # t=0: A0->B1
        assert (("A", 0), ("B", 1)) in uf[0]
        # t=1: A1->B2, B1->C3
        assert (("A", 1), ("B", 2)) in uf[1]
        assert (("B", 1), ("C", 3)) in uf[1]
        # t=2: A2->B3, B2->C4
        assert (("A", 2), ("B", 3)) in uf[2]
        assert (("B", 2), ("C", 4)) in uf[2]
        # t=3: A3->B4
        assert (("A", 3), ("B", 4)) in uf[3]
        # No B3->C5 because 3+2=5 > 4
        assert (("B", 3), ("C", 5)) not in uf.get(3, [])

    _test("unfold structure", t2)

    # ------------------- Test 3: unfold adjacency -------------------
    def t3() -> None:
        g = TemporalGraph()
        g.add_edge("A", "B", lag=1)
        g.add_edge("A", "C", lag=2)
        adj, nodes = g.unfold_adjacency(steps=3)
        assert ("A", 0) in nodes
        assert ("C", 3) in nodes
        assert ("B", 1) in adj[("A", 0)]
        assert ("C", 2) in adj[("A", 0)]
        assert ("C", 3) in adj[("A", 1)]

    _test("unfold adjacency", t3)

    # ------------------- Test 4: intervention chain -------------------
    def t4() -> None:
        g = TemporalGraph()
        g.add_edge("X", "Y", lag=1)
        g.add_edge("Y", "Z", lag=1)
        plan = g.plan_intervention({"Z": 8.0}, deadline=3)
        # Should produce interventions that make Z=8 at t=3.
        # With default weights=1, bias=0:
        # Z(t=3) = Y(t=2). So Y(t=2)=8.
        # Y(t=2) = X(t=1). So X(t=1)=8.
        # Plan: intervene X=8 at t=1, or Y=8 at t=2, or Z=8 at t=3.
        # Backward propagation should push to earliest controllable: X at t=1.
        times_nodes = {(iv[0], iv[1]) for iv in plan}
        assert (1, "X") in times_nodes or (2, "Y") in times_nodes or (3, "Z") in times_nodes
        # Verify plan achieves target by simulation
        iv_map: InterventionMap = defaultdict(dict)
        for t, v, val in plan:
            iv_map[t][v] = val
        hist = g.simulate({"X": 0.0}, steps=3, interventions=dict(iv_map))
        _assert_close(hist[3]["Z"], 8.0)

    _test("intervention chain", t4)

    # ------------------- Test 5: intervention diamond -------------------
    def t5() -> None:
        g = TemporalGraph()
        g.add_edge("A", "B", lag=1)
        g.add_edge("A", "C", lag=1)
        g.add_edge("B", "D", lag=1)
        g.add_edge("C", "D", lag=1)
        # D = B + C = A + A = 2A (default weights)
        plan = g.plan_intervention({"D": 10.0}, deadline=3)
        iv_map: InterventionMap = defaultdict(dict)
        for t, v, val in plan:
            iv_map[t][v] = val
        hist = g.simulate({"A": 0.0}, steps=3, interventions=dict(iv_map))
        _assert_close(hist[3]["D"], 10.0)

    _test("intervention diamond", t5)

    # ------------------- Test 6: temporal paths -------------------
    def t6() -> None:
        g = TemporalGraph()
        g.add_edge("S", "M", lag=1)
        g.add_edge("M", "E", lag=2)
        paths = g.get_temporal_paths("S", "E", max_lag=5)
        assert len(paths) == 1
        assert paths[0] == [("S", 0), ("M", 1), ("E", 3)]

    _test("temporal paths", t6)

    # ------------------- Test 7: consistency no paradox -------------------
    def t7() -> None:
        g = TemporalGraph()
        g.add_edge("P", "Q", lag=1)
        # Events: P=2 at t=1 causes Q=2 at t=2 naturally.
        # Event on Q at t=2 matches natural value -> consistent.
        ok = g.check_consistency(
            events=[(1, "P", 2.0), (2, "Q", 2.0)],
            start_state={"P": 0.0, "Q": 0.0},
            treat_as_interventions=False,
        )
        assert ok is True

    _test("consistency no paradox", t7)

    # ------------------- Test 8: consistency direct conflict -------------------
    def t8() -> None:
        g = TemporalGraph()
        g.add_node("P")
        ok = g.check_consistency(
            events=[(1, "P", 1.0), (1, "P", 2.0)],
            treat_as_interventions=False,
        )
        assert ok is False

    _test("consistency direct conflict", t8)

    # ------------------- Test 9: consistency causal violation -------------------
    def t9() -> None:
        g = TemporalGraph()
        g.add_edge("P", "Q", lag=1)
        # P=2 at t=1 causes Q=2 at t=2 naturally.
        # But event says Q=5 at t=2 -> contradicts causal law.
        ok = g.check_consistency(
            events=[(1, "P", 2.0), (2, "Q", 5.0)],
            start_state={"P": 0.0, "Q": 0.0},
            treat_as_interventions=False,
        )
        assert ok is False

    _test("consistency causal violation", t9)

    # ------------------- Test 10: consistency intervention mode -------------------
    def t10() -> None:
        g = TemporalGraph()
        g.add_edge("P", "Q", lag=1)
        # In intervention mode, events can override natural causality.
        # The only paradox is downstream conflicts between events.
        ok = g.check_consistency(
            events=[(1, "P", 2.0), (2, "Q", 5.0)],
            start_state={"P": 0.0, "Q": 0.0},
            treat_as_interventions=True,
        )
        # No downstream conflict because Q is directly set and there's no
        # other event that depends on Q's natural value.
        assert ok is True

    _test("consistency intervention mode", t10)

    # ------------------- Test 11: consistency grandfather-style -------------------
    def t11() -> None:
        g = TemporalGraph()
        g.add_edge("A", "B", lag=1)
        g.add_edge("B", "C", lag=1)
        # A=10 at t=1 -> B=10 at t=2 -> C=10 at t=3.
        # Event says C=0 at t=3. Natural value would be 10.
        # In observation mode this is a paradox (contradiction).
        ok = g.check_consistency(
            events=[(1, "A", 10.0), (3, "C", 0.0)],
            start_state={"A": 0.0, "B": 0.0, "C": 0.0},
            treat_as_interventions=False,
        )
        assert ok is False

    _test("consistency grandfather-style", t11)

    # ------------------- Test 12: cycle unfolded acyclic -------------------
    def t12() -> None:
        g = TemporalGraph()
        # Compact cycle: A -> B (lag=1), B -> A (lag=2)
        # Unfolded: A0->B1, B0->A2, B1->A3, A1->B2, A2->B3, B2->A4 ... no cycles.
        g.add_edge("A", "B", lag=1)
        g.add_edge("B", "A", lag=2)
        adj, nodes = g.unfold_adjacency(steps=5)
        # Check there is no back-edge in unfolded graph
        for (u, ut), dsts in adj.items():
            for (v, vt) in dsts:
                assert vt >= ut, f"Back-edge found: ({u},{ut}) -> ({v},{vt})"

    _test("cycle unfolded acyclic", t12)

    # ------------------- Test 13: simulation with custom function -------------------
    def t13() -> None:
        g = TemporalGraph()
        g.add_node("X", func=CausalFunction.threshold(cutoff=5.0))
        g.add_edge("W", "X", lag=1)
        hist = g.simulate({"W": 3.0}, steps=2)
        # X(t=1) = threshold(W=3) -> 0.0
        _assert_close(hist[1]["X"], 0.0)
        # If W stays 3 at t=1 (no parents -> drops to 0), X(t=2)=0
        _assert_close(hist[2]["X"], 0.0)

    _test("custom threshold function", t13)

    # ------------------- Test 14: serialize / deserialize -------------------
    def t14() -> None:
        g = TemporalGraph()
        g.add_node("X", bias=1.0)
        g.add_edge("X", "Y", lag=1)
        d = g.to_dict()
        g2 = TemporalGraph.from_dict(d)
        assert g2.nodes == g.nodes
        assert len(g2.edges) == len(g.edges)

    _test("serialize deserialize", t14)

    # ------------------- Test 15: reverse adjacency -------------------
    def t15() -> None:
        g = TemporalGraph()
        g.add_edge("A", "B", lag=1)
        g.add_edge("A", "C", lag=2)
        rev = g.unfold_reverse_adjacency(steps=3)
        assert ("A", 0) in rev[("B", 1)]
        assert ("A", 0) in rev[("C", 2)]
        assert ("A", 1) in rev[("C", 3)]

    _test("reverse adjacency", t15)

    print()
    return passed, total


if __name__ == "__main__":
    print("Temporal Engine Self-Test")
    print("=" * 40)
    passed, total = _run_tests()
    print("=" * 40)
    print(f"RESULT: PASS: {passed}/{total}")
    if passed != total:
        sys.exit(1)

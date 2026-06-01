"""Language Agent Tree Search (LATS) — Monte Carlo Tree Search for reasoning.

Modul ini menyediakan:
- LATSNode untuk tree node dengan value, visits, dan children
- MCTS untuk Monte Carlo Tree Search dengan UCB1 selection
- NodeExpander untuk expand nodes dengan LLM-generated thoughts
- ValueEstimator untuk estimate node value
- LATSEngine untuk end-to-end reasoning via tree search

Berdasarkan: LATS pattern dari all-agentic-architectures (FareedKhan-dev)
"""

from __future__ import annotations

import json
import time
import uuid
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
from enum import Enum, auto


class NodeStatus(Enum):
    UNVISITED = auto()
    EXPANDED = auto()
    TERMINAL = auto()


@dataclass
class LATSNode:
    """Node in the Language Agent Tree Search."""
    node_id: str
    parent_id: Optional[str]
    state: str  # current reasoning state / partial solution
    thought: str = ""  # the thought that led to this state
    value: float = 0.0
    visits: int = 0
    depth: int = 0
    children: List[str] = field(default_factory=list)
    status: NodeStatus = NodeStatus.UNVISITED
    is_terminal: bool = False
    reward: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def ucb1(self, exploration_constant: float = 1.414) -> float:
        if self.visits == 0:
            return float('inf')
        # Need parent visits for UCB1, handled by tree
        return self.value / self.visits + exploration_constant * math.sqrt(1 / self.visits)

    def avg_value(self) -> float:
        return self.value / max(self.visits, 1)


class NodeExpander:
    """Expand nodes by generating new thoughts/actions."""

    def __init__(self, num_children: int = 3):
        self.num_children = num_children

    def expand(self, node: LATSNode, expand_fn: Optional[Callable[[str], List[str]]] = None) -> List[LATSNode]:
        expand_fn = expand_fn or self._default_expander
        thoughts = expand_fn(node.state)
        children = []
        for i, thought in enumerate(thoughts[:self.num_children]):
            child = LATSNode(
                node_id=f"n-{str(uuid.uuid4())[:8]}",
                parent_id=node.node_id,
                state=f"{node.state} | {thought}"[:500],
                thought=thought,
                depth=node.depth + 1,
            )
            children.append(child)
        return children

    def _default_expander(self, state: str) -> List[str]:
        # Simulated: generate diverse reasoning steps
        templates = [
            f"Step A: Analyze {state[:30]}...",
            f"Step B: Break down {state[:30]}...",
            f"Step C: Alternative approach for {state[:30]}...",
            f"Step D: Verify assumptions about {state[:30]}...",
        ]
        return templates[:self.num_children]


class ValueEstimator:
    """Estimate the value of a node state."""

    def __init__(self):
        self._criteria: List[Tuple[str, Callable[[str], float], float]] = []

    def add_criterion(self, name: str, scorer: Callable[[str], float], weight: float = 1.0) -> None:
        self._criteria.append((name, scorer, weight))

    def estimate(self, state: str) -> Tuple[float, Dict[str, float]]:
        if not self._criteria:
            # Default: length + coherence heuristic
            return self._default_estimate(state)
        total_weight = sum(w for _, _, w in self._criteria)
        total = 0.0
        breakdown = {}
        for name, scorer, weight in self._criteria:
            s = scorer(state)
            breakdown[name] = round(s, 3)
            total += s * (weight / total_weight)
        return round(total, 3), breakdown

    def _default_estimate(self, state: str) -> Tuple[float, Dict[str, float]]:
        score = 0.5
        breakdown = {}
        # Length score
        if len(state) > 50:
            score += 0.1
        breakdown["length"] = round(min(1.0, len(state) / 200), 3)
        # Structure score
        if "|" in state:
            score += 0.1
            breakdown["structure"] = 0.8
        else:
            breakdown["structure"] = 0.3
        # Completeness
        if any(k in state.lower() for k in ["result", "answer", "conclusion", "final"]):
            score += 0.2
            breakdown["completeness"] = 0.9
        else:
            breakdown["completeness"] = 0.4
        # Coherence
        words = state.split()
        if len(words) > 5:
            breakdown["coherence"] = 0.7
        else:
            breakdown["coherence"] = 0.3
        return round(min(1.0, score), 3), breakdown


class MCTS:
    """Monte Carlo Tree Search for LATS."""

    def __init__(self, exploration_constant: float = 1.414, max_depth: int = 5):
        self.c = exploration_constant
        self.max_depth = max_depth
        self._nodes: Dict[str, LATSNode] = {}
        self._root_id: Optional[str] = None

    def set_root(self, root: LATSNode) -> None:
        self._root_id = root.node_id
        self._nodes[root.node_id] = root

    def select(self) -> LATSNode:
        """Select leaf node using UCB1."""
        if not self._root_id:
            raise RuntimeError("No root node")
        current = self._nodes[self._root_id]
        while current.children and not current.is_terminal:
            # Select child with highest UCB1
            best_child = None
            best_score = -float('inf')
            for child_id in current.children:
                child = self._nodes[child_id]
                if child.visits == 0:
                    score = float('inf')
                else:
                    score = child.avg_value() + self.c * math.sqrt(math.log(current.visits + 1) / child.visits)
                if score > best_score:
                    best_score = score
                    best_child = child
            if best_child is None:
                break
            current = best_child
        return current

    def expand(self, node: LATSNode, expander: NodeExpander) -> List[LATSNode]:
        if node.depth >= self.max_depth or node.is_terminal:
            node.status = NodeStatus.TERMINAL
            return []
        children = expander.expand(node)
        for child in children:
            self._nodes[child.node_id] = child
            node.children.append(child.node_id)
        node.status = NodeStatus.EXPANDED
        return children

    def simulate(self, node: LATSNode, estimator: ValueEstimator) -> float:
        """Simulate/estimate value from node."""
        value, _ = estimator.estimate(node.state)
        return value

    def backpropagate(self, node: LATSNode, value: float) -> None:
        """Backpropagate value up the tree."""
        current = node
        while current:
            current.visits += 1
            current.value += value
            if current.parent_id and current.parent_id in self._nodes:
                current = self._nodes[current.parent_id]
            else:
                break

    def search(self, num_iterations: int, expander: NodeExpander, estimator: ValueEstimator) -> LATSNode:
        for i in range(num_iterations):
            # Select
            leaf = self.select()
            # Expand
            if leaf.status == NodeStatus.UNVISITED and not leaf.is_terminal:
                self.expand(leaf, expander)
                # Evaluate first child or self if no children
                if leaf.children:
                    child = self._nodes[leaf.children[0]]
                    value = self.simulate(child, estimator)
                    self.backpropagate(child, value)
                else:
                    value = self.simulate(leaf, estimator)
                    self.backpropagate(leaf, value)
            else:
                # Simulate and backprop
                value = self.simulate(leaf, estimator)
                self.backpropagate(leaf, value)
        # Return best child of root
        return self.get_best_child()

    def get_best_child(self) -> Optional[LATSNode]:
        if not self._root_id:
            return None
        root = self._nodes[self._root_id]
        if not root.children:
            return root
        return max(
            (self._nodes[cid] for cid in root.children),
            key=lambda n: n.visits,
        )

    def get_best_path(self) -> List[LATSNode]:
        """Get the path from root to best leaf."""
        if not self._root_id:
            return []
        path = []
        current = self._nodes[self._root_id]
        path.append(current)
        while current.children:
            best = max(
                (self._nodes[cid] for cid in current.children),
                key=lambda n: n.avg_value(),
            )
            path.append(best)
            current = best
        return path

    def get_tree_stats(self) -> Dict[str, Any]:
        return {
            "total_nodes": len(self._nodes),
            "root_id": self._root_id,
            "max_depth": max(n.depth for n in self._nodes.values()) if self._nodes else 0,
            "total_visits": sum(n.visits for n in self._nodes.values()),
            "terminal_nodes": sum(1 for n in self._nodes.values() if n.status == NodeStatus.TERMINAL),
        }


class LATSEngine:
    """End-to-end LATS reasoning engine."""

    def __init__(self, num_iterations: int = 20, max_depth: int = 5, num_children: int = 3):
        self.num_iterations = num_iterations
        self.max_depth = max_depth
        self.num_children = num_children
        self.expander = NodeExpander(num_children)
        self.estimator = ValueEstimator()
        self._runs: List[Dict[str, Any]] = []

    def reason(self, query: str, expand_fn: Optional[Callable[[str], List[str]]] = None) -> Dict[str, Any]:
        start = time.time()
        mcts = MCTS(max_depth=self.max_depth)
        root = LATSNode(
            node_id="root",
            parent_id=None,
            state=query,
            thought="Start reasoning",
        )
        mcts.set_root(root)
        if expand_fn:
            self.expander.expand = lambda node: NodeExpander.expand(self.expander, node, expand_fn)
        best = mcts.search(self.num_iterations, self.expander, self.estimator)
        path = mcts.get_best_path()
        duration = time.time() - start
        run = {
            "run_id": str(uuid.uuid4())[:12],
            "query": query[:100],
            "best_state": best.state[:200] if best else "",
            "best_value": best.avg_value() if best else 0.0,
            "path_length": len(path),
            "nodes_explored": mcts.get_tree_stats()["total_nodes"],
            "duration": round(duration, 3),
            "path": [n.thought for n in path],
        }
        self._runs.append(run)
        return run

    def get_runs(self) -> List[Dict[str, Any]]:
        return self._runs

    def get_stats(self) -> Dict[str, Any]:
        if not self._runs:
            return {}
        return {
            "total_runs": len(self._runs),
            "avg_nodes": sum(r["nodes_explored"] for r in self._runs) / len(self._runs),
            "avg_path_length": sum(r["path_length"] for r in self._runs) / len(self._runs),
            "avg_duration": sum(r["duration"] for r in self._runs) / len(self._runs),
            "avg_value": sum(r["best_value"] for r in self._runs) / len(self._runs),
        }


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("LANGUAGE AGENT TREE SEARCH (LATS) DEMO")
    print("=" * 70)

    # 1. Simple MCTS
    print("\n[1] Monte Carlo Tree Search")
    mcts = MCTS(exploration_constant=1.414, max_depth=3)
    root = LATSNode(node_id="root", parent_id=None, state="Solve: 2 + 3 * 4", thought="Root")
    mcts.set_root(root)
    expander = NodeExpander(num_children=2)
    estimator = ValueEstimator()
    best = mcts.search(num_iterations=10, expander=expander, estimator=estimator)
    print(f"  Best node: {best.node_id}, visits={best.visits}, avg_value={best.avg_value():.3f}")
    print(f"  Tree stats: {mcts.get_tree_stats()}")
    path = mcts.get_best_path()
    print(f"  Best path ({len(path)} nodes):")
    for n in path:
        print(f"    [{n.depth}] {n.thought[:50]}... (v={n.avg_value():.3f})")

    # 2. LATS Engine - math problem
    print("\n[2] LATS Engine — Math Problem")
    engine = LATSEngine(num_iterations=15, max_depth=4, num_children=2)
    result = engine.reason("Calculate the area of a circle with radius 5")
    print(f"  Query: {result['query']}")
    print(f"  Nodes explored: {result['nodes_explored']}")
    print(f"  Path length: {result['path_length']}")
    print(f"  Best value: {result['best_value']:.3f}")
    print(f"  Path:")
    for step in result['path']:
        print(f"    -> {step[:60]}...")

    # 3. LATS Engine — reasoning problem
    print("\n[3] LATS Engine — Logic Reasoning")
    result2 = engine.reason("If all cats are mammals and some mammals are pets, are all cats pets?")
    print(f"  Nodes: {result2['nodes_explored']}, Path: {result2['path_length']}")
    print(f"  Best value: {result2['best_value']:.3f}")
    print(f"  Reasoning path:")
    for step in result2['path']:
        print(f"    -> {step[:60]}...")

    # 4. Custom expander
    print("\n[4] Custom Expander")
    def math_expander(state: str) -> List[str]:
        return [
            "Identify known variables and formulas",
            "Apply formula: A = pi * r^2",
            "Substitute r = 5 and compute",
        ]
    result3 = engine.reason("Find area of circle with r=5", expand_fn=math_expander)
    print(f"  Custom path ({result3['path_length']} steps):")
    for step in result3['path']:
        print(f"    -> {step[:60]}...")

    # 5. Multiple runs stats
    print("\n[5] Engine Stats")
    print(f"  {engine.get_stats()}")

    # 6. Complex search
    print("\n[6] Complex Search (more iterations)")
    engine2 = LATSEngine(num_iterations=30, max_depth=5, num_children=3)
    result4 = engine2.reason("Design a database schema for a social media app")
    print(f"  Nodes: {result4['nodes_explored']}, Best value: {result4['best_value']:.3f}")
    print(f"  Duration: {result4['duration']:.3f}s")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()

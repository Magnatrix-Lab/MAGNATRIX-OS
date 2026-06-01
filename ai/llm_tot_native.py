#!/usr/bin/env python3
"""
ai/llm_tot_native.py
MAGNATRIX-OS — Tree-of-Thought Reasoning Engine for the LLM Arena
AMATI pattern: multi-step branching, backtracking, heuristic evaluation

Pure Python, stdlib only. Simulates tree-structured reasoning with branching,
pruning, and best-path extraction.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ───────────────────────────────────────────────────────────────
# 0. UTILITIES
# ───────────────────────────────────────────────────────────────

def _hash(text: str) -> int:
    h = 0
    for ch in text:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    return h


# ───────────────────────────────────────────────────────────────
# 1. THOUGHT NODE
# ───────────────────────────────────────────────────────────────

@dataclass
class ThoughtNode:
    node_id: str
    thought: str
    parent: Optional[ThoughtNode] = None
    children: List[ThoughtNode] = field(default_factory=list)
    depth: int = 0
    score: float = 0.0
    confidence: float = 0.5
    is_terminal: bool = False

    def path_to_root(self) -> List[ThoughtNode]:
        path = [self]
        current = self.parent
        while current:
            path.insert(0, current)
            current = current.parent
        return path

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "thought": self.thought[:60],
            "depth": self.depth,
            "score": round(self.score, 3),
            "confidence": round(self.confidence, 3),
            "children": len(self.children),
        }


# ───────────────────────────────────────────────────────────────
# 2. THOUGHT GENERATOR
# ───────────────────────────────────────────────────────────────

class ThoughtGenerator:
    """Generate multiple thought branches from a given state."""

    def generate(self, parent: ThoughtNode, problem: str, n_branches: int = 3) -> List[ThoughtNode]:
        children = []
        for i in range(n_branches):
            thought = self._generate_thought(problem, parent.depth + 1, i)
            child = ThoughtNode(
                node_id=f"{parent.node_id}_b{i}",
                thought=thought,
                parent=parent,
                depth=parent.depth + 1,
            )
            children.append(child)
        parent.children.extend(children)
        return children

    def _generate_thought(self, problem: str, depth: int, branch: int) -> str:
        # Simulate diverse reasoning paths
        templates = [
            f"Approach {branch + 1}: Consider the problem from {['first principles', 'analogy', 'pattern matching', 'constraint analysis'][branch % 4]}",
            f"Step {depth}: Apply {['deduction', 'induction', 'abduction', 'verification'][branch % 4]}",
            f"Alternative {branch + 1}: What if we {['reframe', 'decompose', 'generalize', 'simplify'][branch % 4]} the problem?",
        ]
        return templates[depth % len(templates)]


# ───────────────────────────────────────────────────────────────
# 3. EVALUATOR
# ───────────────────────────────────────────────────────────────

class Evaluator:
    """Score each thought branch by coherence, relevance, and progress."""

    def evaluate(self, node: ThoughtNode, problem: str) -> float:
        # Simulate evaluation based on deterministic pseudo-random
        seed = _hash(node.node_id + problem)
        coherence = (seed % 1000) / 1000.0
        relevance = (seed * 7 % 1000) / 1000.0
        progress = max(0, 1.0 - node.depth * 0.1)  # Deeper = less progress unless good
        score = (coherence * 0.4 + relevance * 0.4 + progress * 0.2)
        node.score = score
        node.confidence = coherence
        return score

    def prune(self, nodes: List[ThoughtNode], threshold: float = 0.3) -> List[ThoughtNode]:
        return [n for n in nodes if n.score >= threshold]


# ───────────────────────────────────────────────────────────────
# 4. SEARCH STRATEGY
# ───────────────────────────────────────────────────────────────

class SearchStrategy:
    """Breadth-first, depth-first, or beam search."""

    def beam_search(self, root: ThoughtNode, generator: ThoughtGenerator, evaluator: Evaluator, beam_width: int = 3, max_depth: int = 5) -> List[ThoughtNode]:
        current_level = [root]
        for depth in range(max_depth):
            next_level = []
            for node in current_level:
                children = generator.generate(node, "", beam_width)
                for child in children:
                    evaluator.evaluate(child, "")
                next_level.extend(children)
            next_level.sort(key=lambda n: n.score, reverse=True)
            current_level = next_level[:beam_width]
            if not current_level:
                break
        return current_level


# ───────────────────────────────────────────────────────────────
# 5. BACKTRACKER
# ───────────────────────────────────────────────────────────────

class Backtracker:
    """Backtrack when a branch fails and try alternatives."""

    def __init__(self) -> None:
        self.visited: set = set()

    def backtrack(self, node: ThoughtNode) -> Optional[ThoughtNode]:
        self.visited.add(node.node_id)
        parent = node.parent
        while parent:
            alternatives = [c for c in parent.children if c.node_id not in self.visited]
            if alternatives:
                return max(alternatives, key=lambda c: c.score)
            parent = parent.parent
        return None


# ───────────────────────────────────────────────────────────────
# 6. SOLUTION EXTRACTOR
# ───────────────────────────────────────────────────────────────

class SolutionExtractor:
    """Find best path from root to leaf."""

    def extract(self, root: ThoughtNode, leaves: List[ThoughtNode]) -> Dict[str, Any]:
        if not leaves:
            return {"path": [], "reasoning": "No solution found", "score": 0.0}
        best_leaf = max(leaves, key=lambda n: n.score)
        path = best_leaf.path_to_root()
        reasoning = " -> ".join(n.thought for n in path)
        return {
            "path": [n.to_dict() for n in path],
            "reasoning": reasoning,
            "score": round(best_leaf.score, 3),
            "leaf": best_leaf.to_dict(),
        }


# ───────────────────────────────────────────────────────────────
# 7. TREE OF THOUGHT
# ───────────────────────────────────────────────────────────────

class TreeOfThought:
    """Main orchestrator: generate -> evaluate -> search -> backtrack -> extract."""

    def __init__(self, beam_width: int = 3, max_depth: int = 5) -> None:
        self.generator = ThoughtGenerator()
        self.evaluator = Evaluator()
        self.search = SearchStrategy()
        self.backtracker = Backtracker()
        self.extractor = SolutionExtractor()
        self.beam_width = beam_width
        self.max_depth = max_depth

    def solve(self, problem: str) -> Dict[str, Any]:
        root = ThoughtNode(
            node_id="root",
            thought=f"Problem: {problem[:60]}",
            depth=0,
        )
        self.evaluator.evaluate(root, problem)

        # Beam search
        leaves = self.search.beam_search(root, self.generator, self.evaluator, self.beam_width, self.max_depth)

        # Prune low-scoring leaves
        leaves = self.evaluator.prune(leaves, threshold=0.2)

        # Backtrack if no good leaves
        if not leaves:
            alt = self.backtracker.backtrack(root)
            if alt:
                leaves = [alt]

        solution = self.extractor.extract(root, leaves)

        return {
            "problem": problem,
            "solution": solution,
            "tree_stats": {
                "nodes": self._count_nodes(root),
                "depth": self.max_depth,
                "beam_width": self.beam_width,
            },
        }

    def _count_nodes(self, node: ThoughtNode) -> int:
        count = 1
        for child in node.children:
            count += self._count_nodes(child)
        return count


# ───────────────────────────────────────────────────────────────
# 8. DEMO
# ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX-OS Tree-of-Thought Reasoning Demo")
    print("=" * 60)

    tot = TreeOfThought(beam_width=3, max_depth=4)

    problems = [
        "A farmer has 17 sheep and all but 9 die. How many are left?",
        "Three people need to cross a bridge at night. They have one flashlight. The bridge can hold two people at a time. Crossing times: 1 min, 2 min, 5 min. What's the minimum time?",
        "Solve: If it takes 5 machines 5 minutes to make 5 widgets, how long does it take 100 machines to make 100 widgets?",
    ]

    for i, problem in enumerate(problems, 1):
        print(f"\n[{i}] Problem: {problem[:60]}...")
        result = tot.solve(problem)
        print(f"    Solution score: {result['solution']['score']:.3f}")
        print(f"    Tree nodes: {result['tree_stats']['nodes']}")
        print(f"    Reasoning path:")
        for n in result["solution"]["path"]:
            print(f"      [D{n['depth']}] {n['thought']}")
        print(f"    Final answer: {result['solution']['reasoning'][:100]}...")

    print("\n" + "=" * 60)
    print("Demo complete. Tree-of-Thought ready for LLM Arena.")
    print("=" * 60)

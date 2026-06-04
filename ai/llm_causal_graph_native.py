"""Causal Graph - DAG for causal modeling for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple
from enum import Enum, auto

class EdgeType(Enum):
    CAUSES = auto(); INHIBITS = auto(); CORRELATES = auto()

@dataclass
class CausalGraph:
    nodes: Set[str] = field(default_factory=set)
    edges: Dict[Tuple[str, str], EdgeType] = field(default_factory=dict)

    def add_node(self, node: str) -> None:
        self.nodes.add(node)

    def add_edge(self, cause: str, effect: str, etype: EdgeType = EdgeType.CAUSES) -> None:
        self.add_node(cause); self.add_node(effect)
        self.edges[(cause, effect)] = etype

    def parents(self, node: str) -> List[str]:
        return [s for (s, e), t in self.edges.items() if e == node]

    def children(self, node: str) -> List[str]:
        return [e for (s, e), t in self.edges.items() if s == node]

    def is_dag(self) -> bool:
        visited = set(); rec_stack = set()
        def dfs(n):
            visited.add(n); rec_stack.add(n)
            for c in self.children(n):
                if c not in visited and dfs(c): return True
                elif c in rec_stack: return True
            rec_stack.remove(n)
            return False
        for n in self.nodes:
            if n not in visited and dfs(n): return False
        return True

    def stats(self) -> dict:
        return {"nodes": len(self.nodes), "edges": len(self.edges), "dag": self.is_dag()}

def run():
    cg = CausalGraph()
    cg.add_edge("smoking", "lung_cancer", EdgeType.CAUSES)
    cg.add_edge("smoking", "yellow_fingers", EdgeType.CAUSES)
    cg.add_edge("lung_cancer", "cough", EdgeType.CAUSES)
    print("DAG:", cg.is_dag())
    print("Stats:", cg.stats())

if __name__ == "__main__": run()

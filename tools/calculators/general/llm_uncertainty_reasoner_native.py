"""Uncertainty Reasoner — Bayesian networks, belief propagation, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class BeliefNode:
    name: str
    parents: List[str] = field(default_factory=list)
    cpt: Dict[Tuple[bool, ...], float] = field(default_factory=dict)
    """P(True | parent_values)"""

class UncertaintyReasoner:
    def __init__(self):
        self.nodes: Dict[str, BeliefNode] = {}
        self.evidence: Dict[str, bool] = {}

    def add_node(self, node: BeliefNode):
        self.nodes[node.name] = node

    def set_evidence(self, name: str, value: bool):
        self.evidence[name] = value

    def query(self, name: str) -> float:
        if name in self.evidence:
            return 1.0 if self.evidence[name] else 0.0
        node = self.nodes.get(name)
        if not node:
            return 0.5
        if not node.parents:
            return node.cpt.get((), 0.5)
        parent_vals = tuple(self.query(p) > 0.5 for p in node.parents)
        p_true = node.cpt.get(parent_vals, 0.5)
        for p_name, p_val in self.evidence.items():
            if p_name in node.parents:
                p_node = self.nodes[p_name]
                if p_node.parents:
                    pv = tuple(self.query(pp) > 0.5 for pp in p_node.parents)
                    prob = p_node.cpt.get(pv, 0.5)
                else:
                    prob = p_node.cpt.get((), 0.5)
                if p_val:
                    p_true *= prob
                else:
                    p_true *= (1 - prob)
        return p_true

    def stats(self) -> Dict:
        return {"nodes": len(self.nodes), "evidence": len(self.evidence)}

def run():
    ur = UncertaintyReasoner()
    ur.add_node(BeliefNode("Rain", [], {(): 0.2}))
    ur.add_node(BeliefNode("Sprinkler", ["Rain"], {(False,): 0.4, (True,): 0.01}))
    ur.add_node(BeliefNode("WetGrass", ["Rain", "Sprinkler"], {(False, False): 0.0, (False, True): 0.8, (True, False): 0.9, (True, True): 0.99}))
    ur.set_evidence("WetGrass", True)
    print("P(Sprinkler|Wet):", ur.query("Sprinkler"))
    print(ur.stats())

if __name__ == "__main__":
    run()

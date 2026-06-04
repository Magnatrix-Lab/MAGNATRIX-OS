"""Monte Carlo Tree - MCTS for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum, auto
import random
import math

@dataclass
class MCTNode:
    state: any = None
    parent: Optional["MCTNode"] = None
    children: List["MCTNode"] = field(default_factory=list)
    visits: int = 0
    wins: int = 0
    untried_actions: List[int] = field(default_factory=list)

@dataclass
class MonteCarloTree:
    exploration: float = 1.414
    iterations: int = 100

    def select(self, node: MCTNode) -> MCTNode:
        while node.children and not node.untried_actions:
            node = max(node.children, key=lambda c: (c.wins/c.visits if c.visits > 0 else float('inf')) + self.exploration * math.sqrt(math.log(node.visits)/c.visits) if c.visits > 0 and node.visits > 0 else float('inf'))
        return node

    def expand(self, node: MCTNode) -> MCTNode:
        if node.untried_actions:
            action = node.untried_actions.pop()
            child = MCTNode(state=action, parent=node, untried_actions=[])
            node.children.append(child)
            return child
        return node

    def simulate(self, node: MCTNode) -> int:
        return random.choice([0, 1])

    def backpropagate(self, node: MCTNode, result: int) -> None:
        while node:
            node.visits += 1
            node.wins += result
            node = node.parent

    def search(self, root: MCTNode) -> MCTNode:
        for _ in range(self.iterations):
            leaf = self.select(root)
            child = self.expand(leaf)
            result = self.simulate(child)
            self.backpropagate(child, result)
        return max(root.children, key=lambda c: c.visits) if root.children else root

    def stats(self, root: MCTNode) -> dict:
        best = self.search(root)
        return {"root_visits": root.visits, "best_child_visits": best.visits, "win_rate": round(best.wins/best.visits, 4) if best.visits > 0 else 0}

def run():
    mct = MonteCarloTree(1.414, 50)
    root = MCTNode(state=0, untried_actions=[1, 2, 3, 4, 5])
    print("Stats:", mct.stats(root))

if __name__ == "__main__": run()

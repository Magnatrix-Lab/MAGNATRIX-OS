"""Network Topology — graph, redundancy, paths, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple

@dataclass
class Node:
    id: str
    type: str = "router"

class NetworkTopology:
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.links: List[Tuple[str, str]] = []

    def add_node(self, n: Node):
        self.nodes[n.id] = n

    def add_link(self, a: str, b: str):
        self.links.append((a, b))
        self.links.append((b, a))

    def neighbors(self, node_id: str) -> List[str]:
        return [b for a, b in self.links if a == node_id]

    def degree(self, node_id: str) -> int:
        return len(self.neighbors(node_id))

    def path(self, start: str, end: str) -> List[str]:
        visited = {start}
        queue = [(start, [start])]
        while queue:
            current, path_so_far = queue.pop(0)
            if current == end:
                return path_so_far
            for n in self.neighbors(current):
                if n not in visited:
                    visited.add(n)
                    queue.append((n, path_so_far + [n]))
        return []

    def is_connected(self) -> bool:
        if not self.nodes:
            return True
        visited = set()
        stack = [next(iter(self.nodes))]
        while stack:
            n = stack.pop()
            if n not in visited:
                visited.add(n)
                stack.extend(self.neighbors(n))
        return len(visited) == len(self.nodes)

    def redundancy(self) -> float:
        n = len(self.nodes)
        e = len(self.links) // 2
        if n < 2:
            return 0.0
        min_edges = n - 1
        return max(0, (e - min_edges) / min_edges) if min_edges > 0 else 0.0

    def stats(self) -> Dict:
        return {
            "nodes": len(self.nodes),
            "links": len(self.links) // 2,
            "connected": self.is_connected(),
            "redundancy": round(self.redundancy(), 3)
        }

def run():
    nt = NetworkTopology()
    for i in range(4):
        nt.add_node(Node(f"R{i}"))
    nt.add_link("R0", "R1")
    nt.add_link("R1", "R2")
    nt.add_link("R2", "R3")
    nt.add_link("R3", "R0")
    print(nt.stats())
    print("Path R0->R2:", nt.path("R0", "R2"))

if __name__ == "__main__":
    run()

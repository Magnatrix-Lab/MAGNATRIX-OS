"""Community Detector - Graph clustering for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional
from enum import Enum, auto
from collections import deque

class CommunityMethod(Enum):
    BFS = auto()
    GREEDY = auto()
    LABEL_PROP = auto()

@dataclass
class CommunityDetector:
    method: CommunityMethod = CommunityMethod.BFS
    edges: Dict[str, List[str]] = field(default_factory=dict)
    communities: List[Set[str]] = field(default_factory=list)

    def find_communities(self) -> List[Set[str]]:
        if self.method == CommunityMethod.BFS:
            return self._bfs_communities()
        if self.method == CommunityMethod.GREEDY:
            return self._greedy_communities()
        if self.method == CommunityMethod.LABEL_PROP:
            return self._label_propagation()
        return []

    def _bfs_communities(self) -> List[Set[str]]:
        visited = set()
        communities = []
        for node in self.edges:
            if node not in visited:
                community = set()
                queue = deque([node])
                while queue:
                    n = queue.popleft()
                    if n not in visited:
                        visited.add(n)
                        community.add(n)
                        for neighbor in self.edges.get(n, []):
                            if neighbor not in visited:
                                queue.append(neighbor)
                communities.append(community)
        return communities

    def _greedy_communities(self) -> List[Set[str]]:
        nodes = list(self.edges.keys())
        communities = [{n} for n in nodes]
        for node in nodes:
            neighbors = set(self.edges.get(node, []))
            best = None
            best_score = -1
            for i, comm in enumerate(communities):
                if node not in comm:
                    score = len(neighbors & comm)
                    if score > best_score:
                        best_score = score
                        best = i
            if best is not None and best_score > 0:
                communities[best].add(node)
                for c in communities:
                    if node in c and c is not communities[best]:
                        c.discard(node)
        return [c for c in communities if c]

    def _label_propagation(self) -> List[Set[str]]:
        labels = {node: i for i, node in enumerate(self.edges)}
        changed = True
        iterations = 0
        while changed and iterations < 100:
            changed = False
            iterations += 1
            for node in self.edges:
                neighbor_labels = {}
                for neighbor in self.edges.get(node, []):
                    lbl = labels[neighbor]
                    neighbor_labels[lbl] = neighbor_labels.get(lbl, 0) + 1
                if neighbor_labels:
                    best = max(neighbor_labels, key=neighbor_labels.get)
                    if labels[node] != best:
                        labels[node] = best
                        changed = True
        communities = {}
        for node, label in labels.items():
            communities.setdefault(label, set()).add(node)
        return list(communities.values())

    def modularity(self, communities: List[Set[str]]) -> float:
        m = sum(len(self.edges.get(n, [])) for n in self.edges) / 2
        if m == 0: return 0
        q = 0
        for comm in communities:
            for node in comm:
                for neighbor in self.edges.get(node, []):
                    if neighbor in comm:
                        ki = len(self.edges.get(node, []))
                        kj = len(self.edges.get(neighbor, []))
                        q += 1 - (ki * kj) / (2 * m)
        return q / (2 * m)

    def stats(self) -> dict:
        return {"method": self.method.name, "nodes": len(self.edges), "communities": len(self.communities)}

def run():
    cd = CommunityDetector(CommunityMethod.BFS)
    cd.edges = {"A": ["B"], "B": ["A", "C"], "C": ["B"], "D": ["E"], "E": ["D"]}
    comms = cd.find_communities()
    print("Communities:", [list(c) for c in comms])
    print("Modularity:", round(cd.modularity(comms), 4))
    print("Stats:", cd.stats())

if __name__ == "__main__":
    run()

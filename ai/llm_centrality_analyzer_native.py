"""Centrality Analyzer - Graph centrality metrics for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional
from enum import Enum, auto
from collections import deque

class CentralityType(Enum):
    DEGREE = auto()
    CLOSENESS = auto()
    BETWEENNESS = auto()

@dataclass
class CentralityAnalyzer:
    centrality_type: CentralityType = CentralityType.DEGREE
    edges: Dict[str, List[str]] = field(default_factory=dict)

    def degree_centrality(self) -> Dict[str, float]:
        n = len(self.edges)
        return {node: len(neighbors) / (n - 1) if n > 1 else 0 for node, neighbors in self.edges.items()}

    def closeness_centrality(self) -> Dict[str, float]:
        result = {}
        for node in self.edges:
            dist = self._bfs_distances(node)
            total = sum(dist.values())
            result[node] = (len(dist) - 1) / total if total > 0 else 0
        return result

    def betweenness_centrality(self) -> Dict[str, float]:
        result = {node: 0.0 for node in self.edges}
        for source in self.edges:
            for target in self.edges:
                if source != target:
                    paths = self._all_shortest_paths(source, target)
                    if paths:
                        for node in self.edges:
                            if node != source and node != target:
                                count = sum(1 for p in paths if node in p)
                                result[node] += count / len(paths)
        n = len(self.edges)
        norm = (n - 1) * (n - 2) / 2 if n > 2 else 1
        return {k: v / norm for k, v in result.items()}

    def _bfs_distances(self, start: str) -> Dict[str, int]:
        dist = {start: 0}
        queue = deque([start])
        while queue:
            node = queue.popleft()
            for neighbor in self.edges.get(node, []):
                if neighbor not in dist:
                    dist[neighbor] = dist[node] + 1
                    queue.append(neighbor)
        return dist

    def _all_shortest_paths(self, start: str, goal: str) -> List[List[str]]:
        queue = deque([(start, [start])])
        shortest = None
        paths = []
        while queue:
            node, path = queue.popleft()
            if node == goal:
                if shortest is None or len(path) == shortest:
                    shortest = len(path)
                    paths.append(path)
                continue
            if shortest and len(path) >= shortest:
                continue
            for neighbor in self.edges.get(node, []):
                if neighbor not in path:
                    queue.append((neighbor, path + [neighbor]))
        return paths

    def compute(self) -> Dict[str, float]:
        if self.centrality_type == CentralityType.DEGREE: return self.degree_centrality()
        if self.centrality_type == CentralityType.CLOSENESS: return self.closeness_centrality()
        if self.centrality_type == CentralityType.BETWEENNESS: return self.betweenness_centrality()
        return {}

    def stats(self) -> dict:
        return {"type": self.centrality_type.name, "nodes": len(self.edges)}

def run():
    ca = CentralityAnalyzer(CentralityType.DEGREE)
    ca.edges = {"A": ["B", "C"], "B": ["A", "C", "D"], "C": ["A", "B", "D"], "D": ["B", "C"]}
    print("Degree:", ca.compute())
    ca.centrality_type = CentralityType.CLOSENESS
    print("Closeness:", ca.compute())
    print("Stats:", ca.stats())

if __name__ == "__main__":
    run()

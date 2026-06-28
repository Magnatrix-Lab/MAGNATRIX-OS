#!/usr/bin/env python3
"""Social Network Analyzer for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set

class SocialNetworkAnalyzer:
    def __init__(self, repo_root=""):
        self.repo_root = repo_root
        self.nodes: Set[str] = set()
        self.edges: Dict[str, List[str]] = {}
    def add_node(self, node_id: str):
        self.nodes.add(node_id)
        if node_id not in self.edges:
            self.edges[node_id] = []
    def add_edge(self, a: str, b: str):
        self.add_node(a)
        self.add_node(b)
        self.edges[a].append(b)
        self.edges[b].append(a)
    def degree(self, node: str) -> int:
        return len(self.edges.get(node, []))
    def betweenness(self, node: str) -> float:
        # Simplified betweenness
        if node not in self.edges: return 0.0
        return self.degree(node) / len(self.nodes) if self.nodes else 0.0
    def communities(self) -> List[List[str]]:
        visited = set()
        communities = []
        for node in self.nodes:
            if node not in visited:
                community = []
                stack = [node]
                while stack:
                    n = stack.pop()
                    if n not in visited:
                        visited.add(n)
                        community.append(n)
                        stack.extend(self.edges.get(n, []))
                communities.append(community)
        return communities
    def to_dict(self): return {"nodes": len(self.nodes), "edges": sum(len(v) for v in self.edges.values())//2}

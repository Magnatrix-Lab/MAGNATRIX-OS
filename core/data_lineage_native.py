#!/usr/bin/env python3
"""Data Lineage Tracker for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set

class DataLineageTracker:
    def __init__(self, repo_root=""):
        self.repo_root = repo_root
        self.flows: Dict[str, List[str]] = {}
        self.dependencies: Dict[str, Set[str]] = {}
    def add_flow(self, source: str, target: str):
        if source not in self.flows:
            self.flows[source] = []
        self.flows[source].append(target)
        if target not in self.dependencies:
            self.dependencies[target] = set()
        self.dependencies[target].add(source)
    def trace(self, data_id: str) -> List[str]:
        visited = set()
        result = []
        stack = [data_id]
        while stack:
            current = stack.pop()
            if current not in visited:
                visited.add(current)
                result.append(current)
                stack.extend(self.flows.get(current, []))
        return result
    def impact(self, data_id: str) -> List[str]:
        return list(self.dependencies.get(data_id, set()))
    def to_dict(self): return {"flows": len(self.flows), "dependencies": len(self.dependencies)}

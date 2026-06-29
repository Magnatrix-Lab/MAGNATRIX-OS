
"""
reachability_analyzer_native.py
MAGNATRIX-OS — Reachability Analyzer

Analyze code reachability from external entry points.
Builds call graphs, control flow, and dependency chains.

Pure Python standard library.
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field, asdict
from collections import deque


@dataclass
class CallGraphNode:
    func_name: str
    filepath: str
    line: int
    callers: Set[str] = field(default_factory=set)
    callees: Set[str] = field(default_factory=set)


class ReachabilityAnalyzer:
    """Analyze which code is reachable from external entry points."""

    def __init__(self, repo_root: str = "."):
        self.repo_root = Path(repo_root)
        self.call_graph: Dict[str, CallGraphNode] = {}
        self.entry_points: Set[str] = set()
        self.reachable_set: Set[str] = set()

    def build_call_graph(self) -> Dict[str, CallGraphNode]:
        """Build a call graph across all Python files."""
        for pyfile in self.repo_root.rglob("*.py"):
            try:
                content = pyfile.read_text(encoding="utf-8")
                tree = ast.parse(content)
                current_func = None
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        current_func = node.name
                        key = f"{pyfile.stem}.{current_func}"
                        if key not in self.call_graph:
                            self.call_graph[key] = CallGraphNode(
                                func_name=current_func,
                                filepath=str(pyfile),
                                line=node.lineno,
                            )
                    elif isinstance(node, ast.Call) and current_func:
                        if isinstance(node.func, ast.Name):
                            callee = node.func.id
                            caller_key = f"{pyfile.stem}.{current_func}"
                            callee_key = f"{pyfile.stem}.{callee}"
                            if caller_key in self.call_graph:
                                self.call_graph[caller_key].callees.add(callee_key)
                            if callee_key not in self.call_graph:
                                self.call_graph[callee_key] = CallGraphNode(
                                    func_name=callee,
                                    filepath=str(pyfile),
                                    line=node.lineno,
                                )
                            self.call_graph[callee_key].callers.add(caller_key)
            except Exception:
                continue
        return self.call_graph

    def find_entry_points(self) -> Set[str]:
        """Identify external entry points."""
        entry_patterns = [
            r"if __name__\s*==\s*['\"]__main__['\"]",
            r"@app\.(route|get|post|put|delete)",
            r"def main\s*\(",
            r"handler\s*=\s*",
            r"router\.",
            r"webhook",
            r"onEvent",
        ]
        for pyfile in self.repo_root.rglob("*.py"):
            try:
                content = pyfile.read_text(encoding="utf-8")
                for i, line in enumerate(content.splitlines(), 1):
                    for pat in entry_patterns:
                        if re.search(pat, line):
                            key = f"{pyfile.stem}.main"
                            self.entry_points.add(key)
                            break
            except Exception:
                continue
        return self.entry_points

    def compute_reachability(self) -> Set[str]:
        """Compute all reachable functions from entry points."""
        if not self.call_graph:
            self.build_call_graph()
        if not self.entry_points:
            self.find_entry_points()
        visited = set()
        queue = deque(self.entry_points)
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            if current in self.call_graph:
                for callee in self.call_graph[current].callees:
                    if callee not in visited:
                        queue.append(callee)
        self.reachable_set = visited
        return visited

    def get_dead_code(self) -> Set[str]:
        """Find code not reachable from any entry point."""
        if not self.reachable_set:
            self.compute_reachability()
        all_funcs = set(self.call_graph.keys())
        return all_funcs - self.reachable_set

    def get_stats(self) -> Dict:
        total = len(self.call_graph)
        reachable = len(self.reachable_set)
        dead = total - reachable
        return {
            "total_functions": total,
            "reachable": reachable,
            "dead_code": dead,
            "reduction_pct": round((dead / total * 100), 1) if total > 0 else 0,
        }

    def to_dict(self) -> Dict:
        return self.get_stats()


__all__ = ["ReachabilityAnalyzer", "CallGraphNode"]

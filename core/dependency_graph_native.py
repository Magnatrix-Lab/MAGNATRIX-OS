#!/usr/bin/env python3
"""
Dependency Graph for MAGNATRIX-OS
Analyzes module dependencies, detects cycles, and generates
dependency visualizations. Native stdlib only (AST parsing).

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import ast
import dataclasses
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclasses.dataclass
class DependencyNode:
    module_name: str
    path: str
    imports: List[str]
    imported_by: List[str] = dataclasses.field(default_factory=list)
    depth: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "module": self.module_name,
            "path": self.path,
            "imports": self.imports,
            "imported_by": self.imported_by,
            "depth": self.depth,
        }


class DependencyGraph:
    """Builds and analyzes module dependency graphs."""

    def __init__(self, repo_root: str) -> None:
        self.root = Path(repo_root).resolve()
        self._nodes: Dict[str, DependencyNode] = {}
        self._cycles: List[List[str]] = []

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def scan(self, exclude_dirs: Optional[Set[str]] = None) -> None:
        exclude = exclude_dirs or {"__pycache__", ".git", "venv", "node_modules"}
        for path in self.root.rglob("*.py"):
            if any(part in exclude for part in path.parts):
                continue
            rel = str(path.relative_to(self.root)).replace("\\", "/")
            name = rel.replace("/", ".").rstrip(".py")
            try:
                source = path.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source)
            except SyntaxError:
                continue
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    if mod:
                        imports.append(mod)
            self._nodes[name] = DependencyNode(name, rel, imports)

    def build(self) -> None:
        """Build reverse dependencies and compute depths."""
        for name, node in self._nodes.items():
            for imp in node.imports:
                # Check if import is within the project
                if imp in self._nodes:
                    self._nodes[imp].imported_by.append(name)
        # Compute depth (longest dependency chain)
        for name in self._nodes:
            self._nodes[name].depth = self._compute_depth(name, set())
        # Detect cycles
        self._cycles = self._detect_cycles()

    def _compute_depth(self, name: str, visited: Set[str]) -> int:
        if name in visited:
            return 0
        visited.add(name)
        node = self._nodes.get(name)
        if not node or not node.imports:
            return 0
        max_depth = 0
        for imp in node.imports:
            if imp in self._nodes:
                max_depth = max(max_depth, 1 + self._compute_depth(imp, visited.copy()))
        return max_depth

    def _detect_cycles(self) -> List[List[str]]:
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: List[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            for imp in self._nodes.get(node, DependencyNode("", "", [])).imports:
                if imp in self._nodes:
                    if imp not in visited:
                        dfs(imp, path)
                    elif imp in rec_stack:
                        cycle_start = path.index(imp)
                        cycle = path[cycle_start:] + [imp]
                        cycles.append(cycle)
            path.pop()
            rec_stack.remove(node)

        for name in self._nodes:
            if name not in visited:
                dfs(name, [])
        return cycles

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_dependencies(self, module_name: str) -> List[str]:
        node = self._nodes.get(module_name)
        return node.imports if node else []

    def get_dependents(self, module_name: str) -> List[str]:
        node = self._nodes.get(module_name)
        return node.imported_by if node else []

    def get_cycles(self) -> List[List[str]]:
        return self._cycles

    def get_leaf_nodes(self) -> List[str]:
        return [name for name, node in self._nodes.items() if not node.imports]

    def get_root_nodes(self) -> List[str]:
        return [name for name, node in self._nodes.items() if not node.imported_by]

    def get_depth_sorted(self) -> List[Tuple[str, int]]:
        return sorted([(n, node.depth) for n, node in self._nodes.items()], key=lambda x: x[1], reverse=True)

    def export_dot(self, output_path: str) -> None:
        """Export dependency graph to Graphviz DOT format."""
        lines = ["digraph dependencies {"]
        for name, node in self._nodes.items():
            safe = name.replace(".", "_")
            lines.append(f'  {safe} [label="{name}"];')
            for imp in node.imports:
                if imp in self._nodes:
                    imp_safe = imp.replace(".", "_")
                    lines.append(f"  {safe} -> {imp_safe};")
        lines.append("}")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def export_json(self, output_path: str) -> None:
        data = {n: node.to_dict() for n, node in self._nodes.items()}
        with open(output_path, "w", encoding="utf-8") as f:
            import json
            json.dump(data, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        total = len(self._nodes)
        total_edges = sum(len(n.imports) for n in self._nodes.values())
        avg_deps = total_edges / max(1, total)
        max_depth = max((n.depth for n in self._nodes.values()), default=0)
        return {
            "modules": total,
            "edges": total_edges,
            "avg_dependencies": round(avg_deps, 2),
            "max_depth": max_depth,
            "cycles": len(self._cycles),
            "leaf_nodes": len(self.get_leaf_nodes()),
            "root_nodes": len(self.get_root_nodes()),
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="magnatrix_dep_"))
    # Create mock modules
    (tmp / "a.py").write_text("import b\nimport c\n")
    (tmp / "b.py").write_text("import c\n")
    (tmp / "c.py").write_text("# leaf module\n")
    (tmp / "d.py").write_text("import a\n")
    graph = DependencyGraph(str(tmp))
    graph.scan()
    graph.build()
    print("=== Dependency Graph Demo ===\n")
    print(f"Modules: {len(graph._nodes)}")
    print(f"Cycles: {graph.get_cycles()}")
    print(f"Leaf nodes: {graph.get_leaf_nodes()}")
    print(f"Root nodes: {graph.get_root_nodes()}")
    print(f"Depth sorted: {graph.get_depth_sorted()}")
    print(f"Stats: {graph.stats()}")
    # Export
    dot_path = str(tmp / "graph.dot")
    graph.export_dot(dot_path)
    print(f"\nDOT exported to {dot_path}")
    # Cleanup
    import shutil
    shutil.rmtree(tmp)


if __name__ == "__main__":
    _demo()


"""
code_decomposition_engine_native.py
MAGNATRIX-OS — Code Decomposition Engine

Inspired by OpenAnt (arXiv:2606.19149):
Decomposes codebases into self-contained analysis units filtered by
reachability from external entry points, reducing analysis surface by up to 97%.

Pure Python standard library.
"""

import ast
import re
import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class AnalysisUnit:
    unit_id: str
    filepath: str
    entry_point: str
    functions: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    call_graph: List[str] = field(default_factory=list)
    is_reachable: bool = False
    code_snippet: str = ""
    complexity: int = 0
    lines: int = 0


class CodeDecompositionEngine:
    """Decompose codebase into self-contained analysis units."""

    def __init__(self, repo_root: str = "."):
        self.repo_root = Path(repo_root)
        self.units: Dict[str, AnalysisUnit] = {}
        self.entry_points: Set[str] = set()
        self._analyzed = False

    def find_entry_points(self, patterns: Optional[List[str]] = None) -> Set[str]:
        """Find external entry points (API routes, CLI handlers, webhooks, etc.)."""
        default_patterns = [
            r"@app\.(route|get|post|put|delete)",
            r"def main\s*\(",
            r"if __name__\s*==\s*['\"]__main__['\"]",
            r"class.*Handler.*\(",
            r"handler\s*=\s*",
            r"exports\.[\w]+\s*=",
            r"router\.(get|post|put|delete)",
            r"@router\.",
            r"async def.*request",
            r"def.*handler\s*\(",
            r"onEvent\s*\(",
            r"webhook",
            r"lambda.*handler",
            r"socket\.on",
        ]
        patterns = patterns or default_patterns
        entry_points = set()
        for pyfile in self._find_python_files():
            try:
                content = pyfile.read_text(encoding="utf-8")
                for i, line in enumerate(content.splitlines(), 1):
                    for pat in patterns:
                        if re.search(pat, line):
                            entry_points.add(f"{pyfile}:{i}:{line.strip()}")
                            break
            except Exception:
                continue
        self.entry_points = entry_points
        return entry_points

    def _find_python_files(self) -> List[Path]:
        return list(self.repo_root.rglob("*.py"))

    def decompose(self, max_unit_size: int = 500) -> List[AnalysisUnit]:
        """Decompose codebase into self-contained units."""
        units = []
        for pyfile in self._find_python_files():
            try:
                content = pyfile.read_text(encoding="utf-8")
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        func_name = node.name
                        start_line = node.lineno
                        end_line = node.end_lineno or start_line
                        snippet = "\n".join(content.splitlines()[start_line-1:end_line])
                        unit = AnalysisUnit(
                            unit_id=f"{pyfile.stem}_{func_name}_{start_line}",
                            filepath=str(pyfile.relative_to(self.repo_root)),
                            entry_point=func_name,
                            functions=[func_name],
                            imports=self._extract_imports(tree),
                            code_snippet=snippet[:max_unit_size],
                            complexity=self._calc_complexity(node),
                            lines=end_line - start_line + 1,
                        )
                        units.append(unit)
                        self.units[unit.unit_id] = unit
            except Exception:
                continue
        self._analyzed = True
        return units

    def _extract_imports(self, tree: ast.AST) -> List[str]:
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                imports.append(module)
        return imports

    def _calc_complexity(self, node: ast.AST) -> int:
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler,
                              ast.With, ast.Assert, ast.comprehension)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity

    def filter_reachable(self, units: Optional[List[AnalysisUnit]] = None) -> List[AnalysisUnit]:
        """Filter units by reachability from entry points."""
        if units is None:
            units = list(self.units.values())
        if not self.entry_points:
            self.find_entry_points()
        entry_funcs = set()
        for ep in self.entry_points:
            parts = ep.split(":")
            if len(parts) >= 3:
                line = parts[2]
                m = re.search(r"def\s+(\w+)", line)
                if m:
                    entry_funcs.add(m.group(1))
                m = re.search(r"class\s+(\w+)", line)
                if m:
                    entry_funcs.add(m.group(1))

        reachable = []
        for unit in units:
            if unit.entry_point in entry_funcs:
                unit.is_reachable = True
                reachable.append(unit)
            elif any(ep in unit.filepath for ep in [e.split(":")[0] for e in self.entry_points]):
                unit.is_reachable = True
                reachable.append(unit)
        for unit in units:
            if unit not in reachable:
                unit.is_reachable = False
        return reachable

    def get_reduction_stats(self) -> Dict:
        total = len(self.units)
        reachable = sum(1 for u in self.units.values() if u.is_reachable)
        reduction = ((total - reachable) / total * 100) if total > 0 else 0
        return {
            "total_units": total,
            "reachable_units": reachable,
            "unreachable_units": total - reachable,
            "reduction_percentage": round(reduction, 1),
        }

    def to_dict(self) -> Dict:
        return {
            "total_units": len(self.units),
            "entry_points_found": len(self.entry_points),
            "analyzed": self._analyzed,
        }


__all__ = ["CodeDecompositionEngine", "AnalysisUnit"]

"""Code Audit & Optimization Engine — MAGNATRIX-OS

Pure-stdlib static analysis suite providing:
  • Duplicate code detection (exact / structural / semantic)
  • Dead-code analysis (unused imports, unreachable branches, missing returns)
  • API standardization audit (naming, docstrings, type hints, exception patterns)
  • Performance bottleneck detection (quadratic loops, repeated I/O, string cat, leaks)
  • Code quality metrics (cyclomatic complexity, dependency fan-in/out, maintainability)
  • Structured report generator (dashboard-compatible JSON)

All analysis is performed using the `ast`, `inspect`, `tokenize`, `dis`, and `pathlib`
modules from the Python standard library. No third-party dependencies.
"""

from __future__ import annotations

import ast
import inspect
import json
import math
import os
import pathlib
import sys
import tokenize
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple

# ──────────────────────────────────────────────────────────────
# 1.  DATA STRUCTURES
# ──────────────────────────────────────────────────────────────


@dataclass
class Location:
    file: str
    line: int
    column: int = 0

    def as_dict(self) -> dict:
        return {"file": self.file, "line": self.line, "column": self.column}


@dataclass
class Issue:
    severity: str  # critical / warning / info
    category: str
    message: str
    location: Location
    suggestion: str = ""
    score_impact: float = 0.0  # how much it hurts the quality score

    def as_dict(self) -> dict:
        return {
            "severity": self.severity,
            "category": self.category,
            "message": self.message,
            "location": self.location.as_dict(),
            "suggestion": self.suggestion,
            "score_impact": self.score_impact,
        }


@dataclass
class DuplicateMatch:
    level: str  # exact / structural / semantic
    file_a: str
    file_b: str
    node_type: str
    name_a: str
    name_b: str
    similarity: float  # 0.0 – 1.0
    lines_a: Tuple[int, int]
    lines_b: Tuple[int, int]

    def as_dict(self) -> dict:
        return {
            "level": self.level,
            "file_a": self.file_a,
            "file_b": self.file_b,
            "node_type": self.node_type,
            "name_a": self.name_a,
            "name_b": self.name_b,
            "similarity": round(self.similarity, 3),
            "lines_a": list(self.lines_a),
            "lines_b": list(self.lines_b),
        }


@dataclass
class ModuleMetrics:
    file: str
    loc: int
    blank_lines: int
    comment_lines: int
    function_count: int
    class_count: int
    avg_cyclomatic: float
    max_cyclomatic: float
    fan_in: int
    fan_out: int
    maintainability_index: float

    def as_dict(self) -> dict:
        return {
            "file": self.file,
            "loc": self.loc,
            "blank_lines": self.blank_lines,
            "comment_lines": self.comment_lines,
            "function_count": self.function_count,
            "class_count": self.class_count,
            "avg_cyclomatic": round(self.avg_cyclomatic, 2),
            "max_cyclomatic": round(self.max_cyclomatic, 2),
            "fan_in": self.fan_in,
            "fan_out": self.fan_out,
            "maintainability_index": round(self.maintainability_index, 2),
        }


@dataclass
class AuditReport:
    target_path: str
    modules_analyzed: int
    total_issues: int
    issues: List[Issue] = field(default_factory=list)
    duplicates: List[DuplicateMatch] = field(default_factory=list)
    metrics: List[ModuleMetrics] = field(default_factory=list)
    quality_score: float = 100.0
    top_recommendations: List[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "target_path": self.target_path,
            "modules_analyzed": self.modules_analyzed,
            "total_issues": len(self.issues),
            "quality_score": round(self.quality_score, 2),
            "issues_by_severity": self._severity_counts(),
            "issues_by_category": self._category_counts(),
            "issues": [i.as_dict() for i in self.issues],
            "duplicates": [d.as_dict() for d in self.duplicates],
            "metrics": [m.as_dict() for m in self.metrics],
            "top_recommendations": self.top_recommendations,
        }

    def _severity_counts(self) -> dict:
        counts: Dict[str, int] = {}
        for i in self.issues:
            counts[i.severity] = counts.get(i.severity, 0) + 1
        return counts

    def _category_counts(self) -> dict:
        counts: Dict[str, int] = {}
        for i in self.issues:
            counts[i.category] = counts.get(i.category, 0) + 1
        return counts


# ──────────────────────────────────────────────────────────────
# 2.  AST HELPERS
# ──────────────────────────────────────────────────────────────


def _ast_node_repr(node: ast.AST) -> str:
    """Serialise an AST node to a hashable string (for exact matching)."""
    return ast.dump(node, include_attributes=False)


def _ast_structure_repr(node: ast.AST) -> str:
    """Serialise AST node shape only — names and literals normalised."""
    if isinstance(node, ast.Name):
        return "Name"
    if isinstance(node, ast.Constant):
        return f"Constant({type(node.value).__name__})"
    if isinstance(node, ast.arg):
        return "arg"
    fields = []
    for name, value in ast.iter_fields(node):
        if isinstance(value, list):
            fields.append(f"{name}=[{_ast_structure_repr_list(value)}]")
        elif isinstance(value, ast.AST):
            fields.append(f"{name}={_ast_structure_repr(value)}")
        else:
            fields.append(f"{name}=<>")
    return f"{node.__class__.__name__}({', '.join(fields)})"


def _ast_structure_repr_list(nodes: List[Any]) -> str:
    return ", ".join(
        _ast_structure_repr(n) if isinstance(n, ast.AST) else str(n)
        for n in nodes
    )


def _ast_semantic_repr(node: ast.AST) -> str:
    """Higher-level semantic fingerprint — control flow + call graph."""
    if isinstance(node, ast.FunctionDef):
        stmts = []
        for s in node.body:
            stmts.append(_ast_semantic_repr(s))
        return f"Func({node.name})[{'|'.join(stmts)}]"
    if isinstance(node, ast.For):
        body = "|".join(_ast_semantic_repr(s) for s in node.body)
        return f"For[{body}]"
    if isinstance(node, ast.While):
        body = "|".join(_ast_semantic_repr(s) for s in node.body)
        return f"While[{body}]"
    if isinstance(node, ast.If):
        body = "|".join(_ast_semantic_repr(s) for s in node.body)
        orelse = "|".join(_ast_semantic_repr(s) for s in node.orelse)
        return f"If[{body}]Else[{orelse}]"
    if isinstance(node, ast.Call):
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = f"{node.func.attr}"
        return f"Call({func_name})"
    if isinstance(node, ast.Assign):
        targets = "|".join(_ast_semantic_repr(t) for t in node.targets)
        return f"Assign({targets})"
    if isinstance(node, ast.Name):
        return f"Var({node.id})"
    return node.__class__.__name__


def _collect_defined_names(node: ast.AST) -> Set[str]:
    """Names defined in this node (function/class/variable)."""
    names: Set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(child.name)
        elif isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
            names.add(child.id)
    return names


def _collect_used_names(node: ast.AST) -> Set[str]:
    """Names referenced in this node."""
    names: Set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
            names.add(child.id)
        elif isinstance(child, ast.Attribute):
            # heuristic: attribute access like os.path -> use base name
            if isinstance(child.value, ast.Name):
                names.add(child.value.id)
    return names


def _cyclomatic_complexity(node: ast.AST) -> int:
    """McCabe cyclomatic complexity for a node."""
    complexity = 1
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.While, ast.For, ast.comprehension,
                              ast.ExceptHandler, ast.With, ast.Assert)):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            complexity += len(child.values) - 1
    return complexity


def _has_return_on_all_paths(node: ast.FunctionDef) -> bool:
    """Check if a function body returns on every code path."""
    def _returns(body: List[ast.stmt]) -> bool:
        for stmt in body:
            if isinstance(stmt, ast.Return):
                return True
            if isinstance(stmt, ast.Raise):
                return True
            if isinstance(stmt, ast.If):
                then_returns = _returns(stmt.body)
                else_returns = _returns(stmt.orelse)
                if then_returns and else_returns:
                    return True
            if isinstance(stmt, (ast.For, ast.While)):
                if _returns(stmt.body):
                    # loop with return — but what if it never runs?
                    continue
            if isinstance(stmt, ast.Try):
                all_handlers_return = all(_returns(h.body) for h in stmt.handlers)
                if _returns(stmt.body) and all_handlers_return:
                    return True
        return False

    # For top-level, we also check if every terminal branch has a return
    return _returns(node.body)


def _find_unreachable_code(body: List[ast.stmt]) -> Iterator[Tuple[int, ast.stmt]]:
    """Yield statements after a guaranteed exit (return, raise, continue, break)."""
    terminated = False
    for stmt in body:
        if terminated:
            yield stmt.lineno, stmt
        if isinstance(stmt, (ast.Return, ast.Raise, ast.Continue, ast.Break)):
            terminated = True
        elif isinstance(stmt, ast.If):
            # if both branches terminate, we terminate after the if
            then_term = any(
                isinstance(s, (ast.Return, ast.Raise, ast.Continue, ast.Break))
                for s in stmt.body
            )
            else_term = any(
                isinstance(s, (ast.Return, ast.Raise, ast.Continue, ast.Break))
                for s in stmt.orelse
            )
            if then_term and else_term:
                terminated = True
            # Recurse into unreachable code within branches
            for _, _stmt in _find_unreachable_code(stmt.body):
                yield _stmt.lineno, _stmt
            for _, _stmt in _find_unreachable_code(stmt.orelse):
                yield _stmt.lineno, _stmt
        elif isinstance(stmt, ast.Try):
            for _, _stmt in _find_unreachable_code(stmt.body):
                yield _stmt.lineno, _stmt
            for h in stmt.handlers:
                for _, _stmt in _find_unreachable_code(h.body):
                    yield _stmt.lineno, _stmt


# ──────────────────────────────────────────────────────────────
# 3.  DUPLICATE DETECTION ENGINE
# ──────────────────────────────────────────────────────────────


class DuplicateDetector:
    """Three-level duplicate detection: exact, structural, semantic."""

    def __init__(self, threshold_exact: float = 1.0,
                 threshold_structural: float = 0.85,
                 threshold_semantic: float = 0.70):
        self.threshold_exact = threshold_exact
        self.threshold_structural = threshold_structural
        self.threshold_semantic = threshold_semantic
        self._exact_db: Dict[str, Tuple[str, str, Tuple[int, int]]] = {}
        self._structural_db: Dict[str, Tuple[str, str, Tuple[int, int]]] = {}
        self._semantic_db: Dict[str, Tuple[str, str, Tuple[int, int]]] = {}
        self.matches: List[DuplicateMatch] = []

    def ingest(self, file_path: str, tree: ast.AST) -> None:
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                name = node.name
                lines = (node.lineno, getattr(node, "end_lineno", node.lineno))
                # Exact
                exact_key = _ast_node_repr(node)
                if exact_key in self._exact_db:
                    f, n, ls = self._exact_db[exact_key]
                    self.matches.append(
                        DuplicateMatch("exact", f, file_path,
                                       node.__class__.__name__, n, name,
                                       1.0, ls, lines)
                    )
                else:
                    self._exact_db[exact_key] = (file_path, name, lines)

                # Structural
                struct_key = _ast_structure_repr(node)
                if struct_key in self._structural_db:
                    f, n, ls = self._structural_db[struct_key]
                    if f != file_path or n != name:
                        self.matches.append(
                            DuplicateMatch("structural", f, file_path,
                                           node.__class__.__name__, n, name,
                                           0.92, ls, lines)
                        )
                else:
                    self._structural_db[struct_key] = (file_path, name, lines)

                # Semantic
                sem_key = _ast_semantic_repr(node)
                if sem_key in self._semantic_db:
                    f, n, ls = self._semantic_db[sem_key]
                    if f != file_path or n != name:
                        self.matches.append(
                            DuplicateMatch("semantic", f, file_path,
                                           node.__class__.__name__, n, name,
                                           0.75, ls, lines)
                        )
                else:
                    self._semantic_db[sem_key] = (file_path, name, lines)

    def deduplicate(self) -> None:
        seen: Set[Tuple[str, str, str, str]] = set()
        unique: List[DuplicateMatch] = []
        for m in self.matches:
            key = (m.file_a, m.file_b, m.name_a, m.name_b)
            rev = (m.file_b, m.file_a, m.name_b, m.name_a)
            if key not in seen and rev not in seen:
                seen.add(key)
                unique.append(m)
        self.matches = unique

    def get_matches(self) -> List[DuplicateMatch]:
        return self.matches


# ──────────────────────────────────────────────────────────────
# 4.  DEAD CODE ANALYZER
# ──────────────────────────────────────────────────────────────


class DeadCodeAnalyzer:
    def analyze(self, file_path: str, tree: ast.AST) -> List[Issue]:
        issues: List[Issue] = []
        module_used = _collect_used_names(tree)

        # ── Unused imports ──────────────────────────────────
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    base = name.split(".")[0]
                    if base not in module_used and alias.name not in module_used:
                        issues.append(
                            Issue("warning", "dead_code",
                                  f"Unused import: {alias.name}",
                                  Location(file_path, node.lineno),
                                  f"Remove `import {alias.name}` or use it.",
                                  2.0)
                        )
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    name = alias.asname if alias.asname else alias.name
                    if name not in module_used:
                        issues.append(
                            Issue("warning", "dead_code",
                                  f"Unused import from {module}: {alias.name}",
                                  Location(file_path, node.lineno),
                                  f"Remove `{alias.name}` from import or use it.",
                                  2.0)
                        )

        # ── Unused functions / classes ───────────────────────
        defined_funcs: Dict[str, ast.FunctionDef] = {}
        defined_classes: Dict[str, ast.ClassDef] = {}
        for n in ast.walk(tree):
            if isinstance(n, ast.FunctionDef):
                defined_funcs[n.name] = n
            elif isinstance(n, ast.ClassDef):
                defined_classes[n.name] = n

        # Exclude dunder / public API
        for name, node in list(defined_funcs.items()):
            if name.startswith("_"):
                continue
            if name not in module_used:
                issues.append(
                    Issue("info", "dead_code",
                          f"Potentially unused function: {name}",
                          Location(file_path, node.lineno),
                          "Verify if exported as public API; otherwise remove or prefix with _.",
                          1.0)
                )
        for name, node in list(defined_classes.items()):
            if name not in module_used:
                issues.append(
                    Issue("info", "dead_code",
                          f"Potentially unused class: {name}",
                          Location(file_path, node.lineno),
                          "Verify if exported as public API; otherwise remove or prefix with _.",
                          1.0)
                )

        # ── Unreachable code ─────────────────────────────────
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module)):
                body = node.body if isinstance(node, ast.Module) else node.body
                for lineno, stmt in _find_unreachable_code(body):
                    issues.append(
                        Issue("warning", "dead_code",
                              "Unreachable code after guaranteed exit",
                              Location(file_path, lineno),
                              "Remove dead code or fix control flow.",
                              3.0)
                    )

        # ── Missing return statements ────────────────────────
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.returns is None and not _has_return_on_all_paths(node):
                    # heuristic: skip __init__ and void-style functions
                    if node.name == "__init__":
                        continue
                    if node.name.startswith("_") and not any(
                        isinstance(s, ast.Return) for s in ast.walk(node)
                    ):
                        continue
                    issues.append(
                        Issue("warning", "dead_code",
                              f"Function '{node.name}' may be missing return on some paths",
                              Location(file_path, node.lineno),
                              "Add explicit return or raise on all branches.",
                              2.5)
                    )

        # ── Unused variables (simple heuristic) ─────────────
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                used = _collect_used_names(node)
                for child in ast.walk(node):
                    if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
                        if child.id not in used and not child.id.startswith("_"):
                            issues.append(
                                Issue("info", "dead_code",
                                      f"Potentially unused variable: {child.id}",
                                      Location(file_path, child.lineno),
                                      "Remove or use the variable.",
                                      1.0)
                            )
        return issues


# ──────────────────────────────────────────────────────────────
# 5.  STANDARDIZATION AUDITOR
# ──────────────────────────────────────────────────────────────


class StandardizationAuditor:
    def analyze(self, file_path: str, tree: ast.AST, source: str) -> List[Issue]:
        issues: List[Issue] = []

        for node in ast.walk(tree):
            # ── Naming conventions ─────────────────────────
            if isinstance(node, ast.FunctionDef):
                if not node.name.islower() and not node.name.startswith("_"):
                    if not all(c.islower() or c == "_" for c in node.name):
                        issues.append(
                            Issue("warning", "standardization",
                                  f"Function name '{node.name}' is not snake_case",
                                  Location(file_path, node.lineno),
                                  "Rename to snake_case.",
                                  1.5)
                        )
            elif isinstance(node, ast.ClassDef):
                if not node.name[0].isupper():
                    issues.append(
                        Issue("warning", "standardization",
                              f"Class name '{node.name}' is not CamelCase",
                              Location(file_path, node.lineno),
                              "Rename to PascalCase.",
                              1.5)
                    )

            # ── Missing docstrings ───────────────────────────
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if not ast.get_docstring(node):
                    issues.append(
                        Issue("info", "standardization",
                              f"Missing docstring for {node.__class__.__name__} '{node.name}'",
                              Location(file_path, node.lineno),
                              "Add a docstring describing purpose and parameters.",
                              1.0)
                    )

            # ── Missing type hints ───────────────────────────
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
                    if arg.annotation is None and arg.arg != "self":
                        issues.append(
                            Issue("info", "standardization",
                                  f"Missing type hint for parameter '{arg.arg}' in '{node.name}'",
                                  Location(file_path, arg.lineno),
                                  f"Add annotation, e.g. `{arg.arg}: str`.",
                                  0.5)
                        )
                if node.returns is None:
                    issues.append(
                        Issue("info", "standardization",
                              f"Missing return type hint in '{node.name}'",
                              Location(file_path, node.lineno),
                              "Add `-> ReturnType` annotation.",
                              0.5)
                    )

            # ── Exception handling patterns ──────────────────
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    issues.append(
                        Issue("warning", "standardization",
                              "Bare 'except:' catches all exceptions including SystemExit",
                              Location(file_path, node.lineno),
                              "Use `except Exception:` or a specific exception type.",
                              3.0)
                    )
                elif isinstance(node.type, ast.Name) and node.type.id == "Exception":
                    issues.append(
                        Issue("info", "standardization",
                              "Broad 'except Exception:' — consider more specific types",
                              Location(file_path, node.lineno),
                              "Catch the most specific exception you can handle.",
                              1.0)
                    )

        # ── Inconsistent naming in source (heuristic) ───────
        snake_case_funcs = set()
        camel_case_funcs = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if node.name.islower():
                    snake_case_funcs.add(node.name)
                else:
                    camel_case_funcs.add(node.name)
        if snake_case_funcs and camel_case_funcs:
            issues.append(
                Issue("warning", "standardization",
                      "Mixed naming conventions detected (snake_case + camelCase)",
                      Location(file_path, 1),
                      "Standardise on snake_case for functions.",
                      2.0)
            )

        return issues


# ──────────────────────────────────────────────────────────────
# 6.  PERFORMANCE AUDITOR
# ──────────────────────────────────────────────────────────────


class PerformanceAuditor:
    def analyze(self, file_path: str, tree: ast.AST) -> List[Issue]:
        issues: List[Issue] = []

        for node in ast.walk(tree):
            # ── O(n²) nested loops ───────────────────────────
            if isinstance(node, (ast.For, ast.While)):
                for inner in ast.walk(node):
                    if inner is node:
                        continue
                    if isinstance(inner, (ast.For, ast.While)):
                        issues.append(
                            Issue("warning", "performance",
                                  "Nested loop detected — potential O(n²) complexity",
                                  Location(file_path, inner.lineno),
                                  "Consider vectorisation, set/dict lookups, or itertools.",
                                  3.0)
                        )

            # ── String concatenation in loop ─────────────────
            if isinstance(node, (ast.For, ast.While)):
                for child in ast.walk(node):
                    if isinstance(child, ast.AugAssign):
                        if isinstance(child.op, ast.Add):
                            if isinstance(child.target, ast.Name):
                                issues.append(
                                    Issue("warning", "performance",
                                          "String concatenation in loop — use list + join()",
                                          Location(file_path, child.lineno),
                                          "Accumulate in a list and `''.join(parts)` after loop.",
                                          2.5)
                                )

            # ── Repeated file I/O in loop ────────────────────
            if isinstance(node, (ast.For, ast.While)):
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Name):
                            if child.func.id in ("open", "read", "write"):
                                issues.append(
                                    Issue("warning", "performance",
                                          f"File I/O operation '{child.func.id}' inside loop",
                                          Location(file_path, child.lineno),
                                          "Move I/O outside loop or batch operations.",
                                          3.5)
                                )
                        elif isinstance(child.func, ast.Attribute):
                            if child.func.attr in ("read", "write", "readline", "readlines"):
                                issues.append(
                                    Issue("warning", "performance",
                                          f"File I/O method '{child.func.attr}' inside loop",
                                          Location(file_path, child.lineno),
                                          "Move I/O outside loop or batch operations.",
                                          3.5)
                                )

            # ── List accumulation without bounds ─────────────
            if isinstance(node, ast.FunctionDef):
                for child in ast.walk(node):
                    if isinstance(child, ast.List):
                        # Check if list is appended to in a loop without size limit
                        list_names = set()
                        for sub in ast.walk(node):
                            if isinstance(sub, ast.Assign):
                                if isinstance(sub.value, ast.List):
                                    for t in sub.targets:
                                        if isinstance(t, ast.Name):
                                            list_names.add(t.id)
                        for sub in ast.walk(node):
                            if isinstance(sub, ast.AugAssign):
                                if isinstance(sub.target, ast.Name):
                                    if sub.target.id in list_names:
                                        issues.append(
                                            Issue("info", "performance",
                                                  f"List '{sub.target.id}' may grow unbounded — potential memory leak",
                                                  Location(file_path, sub.lineno),
                                                  "Consider using a deque with maxlen or capping list size.",
                                                  1.5)
                                        )

        return issues


# ──────────────────────────────────────────────────────────────
# 7.  METRICS COLLECTOR
# ──────────────────────────────────────────────────────────────


class MetricsCollector:
    def analyze(self, file_path: str, tree: ast.AST, source: str) -> ModuleMetrics:
        lines = source.splitlines()
        loc = len(lines)
        blank = sum(1 for l in lines if not l.strip())
        comments = sum(1 for l in lines if l.strip().startswith("#"))

        func_count = 0
        class_count = 0
        complexities = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_count += 1
                complexities.append(_cyclomatic_complexity(node))
            elif isinstance(node, ast.ClassDef):
                class_count += 1

        avg_cc = sum(complexities) / len(complexities) if complexities else 0.0
        max_cc = max(complexities) if complexities else 0.0

        # Fan-out: unique imports
        fan_out = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                fan_out += len(node.names)
            elif isinstance(node, ast.ImportFrom):
                fan_out += 1

        # Fan-in: approximate by how many times module is imported in other files
        # (computed later by the engine)
        fan_in = 0

        # Maintainability Index (simplified variant)
        # MI = 171 - 5.2 * ln(HV) - 0.23 * CC - 16.2 * ln(LOC)
        # We use a proxy for HV (Halstead Volume) as ln(LOC)
        if loc > 0 and complexities:
            hv_proxy = math.log(loc)
            mi = 171 - 5.2 * hv_proxy - 0.23 * avg_cc - 16.2 * math.log(loc)
            mi = max(0.0, min(100.0, mi))
        else:
            mi = 100.0

        return ModuleMetrics(
            file=file_path, loc=loc, blank_lines=blank,
            comment_lines=comments, function_count=func_count,
            class_count=class_count, avg_cyclomatic=avg_cc,
            max_cyclomatic=max_cc, fan_in=fan_in, fan_out=fan_out,
            maintainability_index=mi
        )


# ──────────────────────────────────────────────────────────────
# 8.  REPORT GENERATOR
# ──────────────────────────────────────────────────────────────


class ReportGenerator:
    def generate(self, report: AuditReport) -> dict:
        # Compute quality score — normalised by codebase size so it is meaningful
        total_loc = sum(m.loc for m in report.metrics) if report.metrics else 1
        # Weighted issue impact
        severity_weights = {"critical": 5.0, "warning": 2.0, "info": 0.5}
        raw_penalty = sum(
            severity_weights.get(i.severity, 1.0) for i in report.issues
        )
        # Duplicate penalty: first 10 hurt most, then diminishing
        dup_count = len(report.duplicates)
        dup_penalty = min(dup_count * 1.5, 15.0)
        # Normalise penalty per 100 LOC
        penalty_per_100loc = (raw_penalty + dup_penalty) / (total_loc / 100.0)
        # Score curve: 100 at 0 penalty, ~50 at 20 penalty/100loc, ~0 at 60
        base_score = 100.0 * math.exp(-0.05 * penalty_per_100loc)
        # Maintainability bonus
        if report.metrics:
            avg_mi = sum(m.maintainability_index for m in report.metrics) / len(report.metrics)
            if avg_mi < 40:
                base_score -= 10.0
            elif avg_mi > 80:
                base_score += 5.0
        report.quality_score = max(0.0, min(100.0, base_score))

        # Top recommendations
        recs = []
        sev = report._severity_counts()
        if sev.get("critical", 0) > 0:
            recs.append("Address all critical issues immediately.")
        if sev.get("warning", 0) > 5:
            recs.append("High warning count — schedule a refactoring sprint.")
        if report.duplicates:
            recs.append(f"Consolidate {len(report.duplicates)} duplicate blocks via shared utilities.")
        if any(m.max_cyclomatic > 10 for m in report.metrics):
            recs.append("Simplify high-complexity functions (>10 McCabe).")
        if any(m.maintainability_index < 50 for m in report.metrics):
            recs.append("Low maintainability modules need architectural review.")
        report.top_recommendations = recs

        return report.as_dict()


# ──────────────────────────────────────────────────────────────
# 9.  MAIN ENGINE
# ──────────────────────────────────────────────────────────────


class CodeAuditEngine:
    """Orchestrates all analysis passes and produces a dashboard-ready report."""

    def __init__(self, target_path: str = "."):
        self.target_path = pathlib.Path(target_path)
        self.duplicate_detector = DuplicateDetector()
        self.dead_analyzer = DeadCodeAnalyzer()
        self.std_auditor = StandardizationAuditor()
        self.perf_auditor = PerformanceAuditor()
        self.metrics_collector = MetricsCollector()
        self.report_generator = ReportGenerator()
        self._fan_in_map: Dict[str, int] = {}

    def _discover_py_files(self) -> List[pathlib.Path]:
        files: List[pathlib.Path] = []
        if self.target_path.is_file() and self.target_path.suffix == ".py":
            files.append(self.target_path)
        elif self.target_path.is_dir():
            for p in self.target_path.rglob("*.py"):
                # Skip __pycache__ and hidden files
                if "__pycache__" in str(p) or any(
                    part.startswith(".") for part in p.parts
                ):
                    continue
                files.append(p)
        return sorted(files)

    def _parse_file(self, path: pathlib.Path) -> Optional[Tuple[ast.AST, str]]:
        try:
            source = path.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(path))
            return tree, source
        except SyntaxError as exc:
            print(f"[!] Syntax error in {path}: {exc}")
            return None

    def _compute_fan_in(self, files: List[pathlib.Path]) -> Dict[str, int]:
        """Rough fan-in: count how many times each module is imported by others."""
        fan_in: Dict[str, int] = {str(f): 0 for f in files}
        module_names = {str(f): f.stem for f in files}
        for f in files:
            tree_source = self._parse_file(f)
            if tree_source is None:
                continue
            tree, _ = tree_source
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        base = alias.name.split(".")[0]
                        for path, mod in module_names.items():
                            if mod == base:
                                fan_in[path] += 1
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    base = mod.split(".")[0]
                    for path, name in module_names.items():
                        if name == base:
                            fan_in[path] += 1
        return fan_in

    def run(self) -> AuditReport:
        files = self._discover_py_files()
        if not files:
            return AuditReport(str(self.target_path), 0, 0)

        self._fan_in_map = self._compute_fan_in(files)
        report = AuditReport(str(self.target_path), len(files), 0)

        for f in files:
            tree_source = self._parse_file(f)
            if tree_source is None:
                continue
            tree, source = tree_source
            file_str = str(f)

            # Duplicate detection
            self.duplicate_detector.ingest(file_str, tree)

            # Dead code
            report.issues.extend(self.dead_analyzer.analyze(file_str, tree))

            # Standardization
            report.issues.extend(self.std_auditor.analyze(file_str, tree, source))

            # Performance
            report.issues.extend(self.perf_auditor.analyze(file_str, tree))

            # Metrics
            metrics = self.metrics_collector.analyze(file_str, tree, source)
            metrics.fan_in = self._fan_in_map.get(file_str, 0)
            report.metrics.append(metrics)

        self.duplicate_detector.deduplicate()
        report.duplicates = self.duplicate_detector.get_matches()

        # Final score + recommendations
        self.report_generator.generate(report)
        return report

    def run_to_json(self, output_path: Optional[str] = None) -> str:
        report = self.run()
        payload = report.as_dict()
        text = json.dumps(payload, indent=2, ensure_ascii=False)
        if output_path:
            pathlib.Path(output_path).write_text(text, encoding="utf-8")
        return text


# ──────────────────────────────────────────────────────────────
# 10. SELF-CONTAINED DEMO
# ──────────────────────────────────────────────────────────────


def run_demo() -> None:
    """Audit the MAGNATRIX-OS core/ directory and print a summary."""
    target = os.environ.get("MAGNATRIX_CORE", "/mnt/agents/MAGNATRIX-OS/core")
    print(f"═══ MAGNATRIX-OS Code Audit Engine ═══")
    print(f"Target: {target}")
    print()

    engine = CodeAuditEngine(target)
    report = engine.run()

    print(f"Modules analyzed : {report.modules_analyzed}")
    print(f"Total issues     : {len(report.issues)}")
    print(f"Duplicates found : {len(report.duplicates)}")
    print(f"Quality score    : {report.quality_score:.1f}/100")
    print()

    # Severity breakdown
    sev = report._severity_counts()
    print("Issues by severity:")
    for level in ("critical", "warning", "info"):
        count = sev.get(level, 0)
        print(f"  {level:10s}: {count}")
    print()

    # Category breakdown
    cat = report._category_counts()
    print("Issues by category:")
    for c, count in sorted(cat.items(), key=lambda x: -x[1]):
        print(f"  {c:20s}: {count}")
    print()

    # Top 10 issues
    print("Top 10 issues:")
    for i, issue in enumerate(report.issues[:10], 1):
        print(f"  {i}. [{issue.severity}] {issue.message}")
        print(f"     → {issue.location.file}:{issue.location.line}")
    print()

    # Duplicate highlights
    if report.duplicates:
        print("Duplicate highlights:")
        for dup in report.duplicates[:5]:
            print(f"  [{dup.level}] {dup.name_a} ↔ {dup.name_b}")
            print(f"     {dup.file_a}:{dup.lines_a[0]}-{dup.lines_a[1]}")
            print(f"     {dup.file_b}:{dup.lines_b[0]}-{dup.lines_b[1]}")
        print()

    # Metrics summary
    print("Metrics summary:")
    total_loc = sum(m.loc for m in report.metrics)
    total_funcs = sum(m.function_count for m in report.metrics)
    avg_mi = sum(m.maintainability_index for m in report.metrics) / len(report.metrics) if report.metrics else 0
    print(f"  Total LOC         : {total_loc}")
    print(f"  Total functions   : {total_funcs}")
    print(f"  Avg maintainability: {avg_mi:.1f}")
    print()

    # Recommendations
    print("Recommendations:")
    for rec in report.top_recommendations:
        print(f"  • {rec}")
    print()

    # Write JSON report
    json_path = os.path.join(target, "..", "audit_report.json")
    engine.run_to_json(json_path)
    print(f"Full JSON report written to: {json_path}")


if __name__ == "__main__":
    run_demo()

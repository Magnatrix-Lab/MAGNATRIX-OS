#!/usr/bin/env python3
"""
Code Quality Checker for MAGNATRIX-OS
Static analysis, complexity detection, docstring coverage,
and style issue reporting. Native stdlib only (AST parsing).

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import ast
import dataclasses
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclasses.dataclass
class QualityIssue:
    file_path: str
    line: int
    severity: str
    message: str
    rule: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": self.file_path,
            "line": self.line,
            "severity": self.severity,
            "message": self.message,
            "rule": self.rule,
        }


@dataclasses.dataclass
class FileQuality:
    file_path: str
    line_count: int
    function_count: int
    class_count: int
    docstring_coverage: float
    max_complexity: int
    issues: List[QualityIssue]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": self.file_path,
            "lines": self.line_count,
            "functions": self.function_count,
            "classes": self.class_count,
            "docstring_coverage": round(self.docstring_coverage, 2),
            "max_complexity": self.max_complexity,
            "issues": [i.to_dict() for i in self.issues],
        }


class CodeQualityChecker:
    """Analyzes Python code quality via AST."""

    def __init__(self, repo_root: str) -> None:
        self.root = Path(repo_root).resolve()

    def check_file(self, path: Path) -> FileQuality:
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source)
        except SyntaxError:
            return FileQuality(
                file_path=str(path.relative_to(self.root)),
                line_count=0, function_count=0, class_count=0,
                docstring_coverage=0, max_complexity=0,
                issues=[QualityIssue(str(path.relative_to(self.root)), 0, "error", "Syntax error", "syntax")]
            )

        issues = []
        functions = 0
        classes = 0
        documented = 0
        max_complexity = 0

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions += 1
                if ast.get_docstring(node):
                    documented += 1
                complexity = self._compute_complexity(node)
                max_complexity = max(max_complexity, complexity)
                if complexity > 10:
                    issues.append(QualityIssue(
                        str(path.relative_to(self.root)), node.lineno, "warning",
                        f"Function complexity {complexity} > 10", "complexity"
                    ))
                if len(node.body) > 50:
                    issues.append(QualityIssue(
                        str(path.relative_to(self.root)), node.lineno, "warning",
                        f"Function too long ({len(node.body)} statements)", "function_length"
                    ))
            elif isinstance(node, ast.ClassDef):
                classes += 1
                if ast.get_docstring(node):
                    documented += 1
                if len(node.bases) > 3:
                    issues.append(QualityIssue(
                        str(path.relative_to(self.root)), node.lineno, "info",
                        f"Class has {len(node.bases)} base classes", "inheritance"
                    ))
            elif isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    issues.append(QualityIssue(
                        str(path.relative_to(self.root)), node.lineno, "warning",
                        "Bare except clause", "bare_except"
                    ))
            elif isinstance(node, (ast.Global, ast.Nonlocal)):
                issues.append(QualityIssue(
                    str(path.relative_to(self.root)), node.lineno, "info",
                    f"Use of {type(node).__name__.lower()}", "global_usage"
                ))

        docstring_coverage = (documented / max(1, functions + classes)) * 100

        return FileQuality(
            file_path=str(path.relative_to(self.root)),
            line_count=source.count("\n") + 1,
            function_count=functions,
            class_count=classes,
            docstring_coverage=docstring_coverage,
            max_complexity=max_complexity,
            issues=issues,
        )

    def _compute_complexity(self, node: ast.AST) -> int:
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.With, ast.Assert, ast.comprehension)):
                complexity += 1
            elif isinstance(child, ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity

    def scan(self, max_files: Optional[int] = None) -> List[FileQuality]:
        results = []
        count = 0
        for path in self.root.rglob("*.py"):
            if any(part in {"__pycache__", ".git", "venv"} for part in path.parts):
                continue
            results.append(self.check_file(path))
            count += 1
            if max_files and count >= max_files:
                break
        return results

    def generate_report(self, output_path: Optional[str] = None) -> Dict[str, Any]:
        results = self.scan()
        total_issues = sum(len(r.issues) for r in results)
        by_severity = {}
        by_rule = {}
        for r in results:
            for issue in r.issues:
                by_severity[issue.severity] = by_severity.get(issue.severity, 0) + 1
                by_rule[issue.rule] = by_rule.get(issue.rule, 0) + 1
        total_lines = sum(r.line_count for r in results)
        total_functions = sum(r.function_count for r in results)
        total_classes = sum(r.class_count for r in results)
        avg_coverage = sum(r.docstring_coverage for r in results) / max(1, len(results))
        max_complexity = max((r.max_complexity for r in results), default=0)

        report = {
            "files_analyzed": len(results),
            "total_lines": total_lines,
            "total_functions": total_functions,
            "total_classes": total_classes,
            "total_issues": total_issues,
            "avg_docstring_coverage": round(avg_coverage, 2),
            "max_complexity": max_complexity,
            "by_severity": by_severity,
            "by_rule": by_rule,
            "files": [r.to_dict() for r in results[:50]],
        }
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
        return report

    def stats(self) -> Dict[str, Any]:
        return {
            "repo_root": str(self.root),
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="magnatrix_quality_"))
    # Create test files
    (tmp / "good.py").write_text("""
def hello():
    \"\"\"Say hello.\"\"\"
    return "hello"

class Good:
    \"\"\"A good class.\"\"\"
    def method(self):
        return 1
""")
    (tmp / "bad.py").write_text("""
def complex():
    if 1:
        if 2:
            if 3:
                if 4:
                    if 5:
                        if 6:
                            if 7:
                                if 8:
                                    if 9:
                                        if 10:
                                            if 11:
                                                pass
    try:
        pass
    except:
        pass
""")
    checker = CodeQualityChecker(str(tmp))
    print("=== Code Quality Checker Demo ===\n")
    results = checker.scan()
    for r in results:
        print(f"{r.file_path}: {r.function_count} funcs, {r.class_count} classes, {len(r.issues)} issues, {r.docstring_coverage:.0f}% docs")
        for issue in r.issues[:3]:
            print(f"  [{issue.severity}] Line {issue.line}: {issue.message}")
    report = checker.generate_report()
    print(f"\nTotal issues: {report['total_issues']}")
    print(f"By severity: {report['by_severity']}")
    # Cleanup
    import shutil
    shutil.rmtree(tmp)


if __name__ == "__main__":
    _demo()

#!/usr/bin/env python3
"""
Module Registry for MAGNATRIX-OS
Scans, catalogs, and indexes all Python modules in the repository.
Provides searchable registry with metadata extraction (classes, functions, docstrings).
Native stdlib only — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import ast
import dataclasses
import enum
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


class ModuleType(enum.Enum):
    """Classification of module purpose."""
    CALCULATOR = "calculator"
    GOVERNANCE = "governance"
    INFRASTRUCTURE = "infrastructure"
    UTILITY = "utility"
    UNKNOWN = "unknown"


class ModuleHealth(enum.Enum):
    """Compilation health status of a module."""
    HEALTHY = "healthy"
    SYNTAX_ERROR = "syntax_error"
    IMPORT_ERROR = "import_error"
    UNCHECKED = "unchecked"


@dataclasses.dataclass(frozen=True)
class SymbolInfo:
    """Represents a class or function extracted from a module."""
    name: str
    kind: str  # "class" or "function"
    docstring: str
    line_start: int
    line_end: int
    decorators: Tuple[str, ...]
    arguments: Tuple[str, ...] = dataclasses.field(default_factory=tuple)
    returns: Optional[str] = None


@dataclasses.dataclass
class ModuleRecord:
    """Full metadata record for a single Python module."""
    relative_path: str
    absolute_path: str
    module_type: ModuleType
    health: ModuleHealth
    docstring: str
    classes: List[SymbolInfo]
    functions: List[SymbolInfo]
    imports: List[str]
    line_count: int
    last_modified: float
    file_size: int
    checksum: str  # simple hash of file content
    tags: Set[str] = dataclasses.field(default_factory=set)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relative_path": self.relative_path,
            "absolute_path": self.absolute_path,
            "module_type": self.module_type.value,
            "health": self.health.value,
            "docstring": self.docstring,
            "classes": [dataclasses.asdict(c) for c in self.classes],
            "functions": [dataclasses.asdict(f) for f in self.functions],
            "imports": self.imports,
            "line_count": self.line_count,
            "last_modified": self.last_modified,
            "file_size": self.file_size,
            "checksum": self.checksum,
            "tags": sorted(self.tags),
        }


class ModuleScanner:
    """AST-based scanner that extracts metadata from Python source files."""

    def __init__(self, repo_root: str) -> None:
        self.root = Path(repo_root).resolve()

    def _simple_hash(self, content: str) -> str:
        """Fast non-cryptographic hash for change detection."""
        h = 0
        for ch in content:
            h = (h * 31 + ord(ch)) & 0xFFFFFFFF
        return f"{h:08x}"

    def _detect_type(self, rel_path: str) -> ModuleType:
        """Classify module by its directory location."""
        lower = rel_path.lower()
        if "calculator" in lower or "tools/calculators" in lower:
            return ModuleType.CALCULATOR
        if "governance" in lower:
            return ModuleType.GOVERNANCE
        if "core" in lower or "infrastructure" in lower:
            return ModuleType.INFRASTRUCTURE
        if "utility" in lower or "util" in lower:
            return ModuleType.UTILITY
        return ModuleType.UNKNOWN

    def _parse_file(self, path: Path) -> Optional[ModuleRecord]:
        rel = str(path.relative_to(self.root))
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            return None
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return ModuleRecord(
                relative_path=rel,
                absolute_path=str(path),
                module_type=self._detect_type(rel),
                health=ModuleHealth.SYNTAX_ERROR,
                docstring="",
                classes=[],
                functions=[],
                imports=[],
                line_count=source.count("\n") + 1,
                last_modified=path.stat().st_mtime,
                file_size=len(source.encode("utf-8")),
                checksum=self._simple_hash(source),
                tags={"syntax_error"},
            )

        classes: List[SymbolInfo] = []
        functions: List[SymbolInfo] = []
        imports: List[str] = []
        docstring = ast.get_docstring(tree) or ""
        tags: Set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                end = getattr(node, "end_lineno", node.lineno)
                decorators = []
                for d in node.decorator_list:
                    try:
                        decorators.append(ast.unparse(d))
                    except Exception:
                        decorators.append("<decorator>")
                classes.append(SymbolInfo(
                    name=node.name,
                    kind="class",
                    docstring=ast.get_docstring(node) or "",
                    line_start=node.lineno,
                    line_end=end or node.lineno,
                    decorators=tuple(decorators),
                ))
                if "native" in node.name.lower():
                    tags.add("native")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                end = getattr(node, "end_lineno", node.lineno)
                decorators = []
                for d in node.decorator_list:
                    try:
                        decorators.append(ast.unparse(d))
                    except Exception:
                        decorators.append("<decorator>")
                args = [a.arg for a in node.args.args]
                returns = None
                if node.returns and hasattr(node.returns, "id"):
                    returns = node.returns.id
                functions.append(SymbolInfo(
                    name=node.name,
                    kind="function" if isinstance(node, ast.FunctionDef) else "async_function",
                    docstring=ast.get_docstring(node) or "",
                    line_start=node.lineno,
                    line_end=end or node.lineno,
                    decorators=tuple(decorators),
                    arguments=tuple(args),
                    returns=returns,
                ))
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                else:
                    mod = node.module or ""
                    for alias in node.names:
                        imports.append(f"{mod}.{alias.name}" if mod else alias.name)

        # Derive tags from path and content
        if "native" in path.name.lower():
            tags.add("native")
        if "acs_" in path.name.lower():
            tags.add("acs_governance")
        if "llm_" in path.name.lower():
            tags.add("llm_tool")

        return ModuleRecord(
            relative_path=rel,
            absolute_path=str(path),
            module_type=self._detect_type(rel),
            health=ModuleHealth.UNCHECKED,
            docstring=docstring,
            classes=classes,
            functions=functions,
            imports=imports,
            line_count=source.count("\n") + 1,
            last_modified=path.stat().st_mtime,
            file_size=len(source.encode("utf-8")),
            checksum=self._simple_hash(source),
            tags=tags,
        )

    def scan(self, exclude_dirs: Optional[Set[str]] = None) -> List[ModuleRecord]:
        """Recursively scan all Python files under repo root."""
        exclude = exclude_dirs or {"__pycache__", ".git", "venv", "node_modules", "dist", "build"}
        records: List[ModuleRecord] = []
        for path in self.root.rglob("*.py"):
            if any(part in exclude for part in path.parts):
                continue
            record = self._parse_file(path)
            if record:
                records.append(record)
        return records


class ModuleRegistry:
    """Central registry providing search, filter, and health-check capabilities."""

    def __init__(self, repo_root: str) -> None:
        self.scanner = ModuleScanner(repo_root)
        self._records: Dict[str, ModuleRecord] = {}
        self._last_scan: float = 0.0

    def refresh(self) -> None:
        """Rescan the entire repository."""
        records = self.scanner.scan()
        self._records = {r.relative_path: r for r in records}
        self._last_scan = time.time()

    @property
    def records(self) -> List[ModuleRecord]:
        return list(self._records.values())

    def search(self, keyword: str) -> List[ModuleRecord]:
        """Case-insensitive search across paths, docstrings, and symbol names."""
        kw = keyword.lower()
        results = []
        for r in self._records.values():
            if kw in r.relative_path.lower():
                results.append(r)
                continue
            if kw in r.docstring.lower():
                results.append(r)
                continue
            for c in r.classes:
                if kw in c.name.lower() or kw in c.docstring.lower():
                    results.append(r)
                    break
            else:
                for f in r.functions:
                    if kw in f.name.lower() or kw in f.docstring.lower():
                        results.append(r)
                        break
        return results

    def filter_by_type(self, module_type: ModuleType) -> List[ModuleRecord]:
        return [r for r in self._records.values() if r.module_type == module_type]

    def filter_by_tag(self, tag: str) -> List[ModuleRecord]:
        return [r for r in self._records.values() if tag in r.tags]

    def filter_by_health(self, health: ModuleHealth) -> List[ModuleRecord]:
        return [r for r in self._records.values() if r.health == health]

    def health_check(self) -> Dict[str, ModuleHealth]:
        """Compile every module to detect syntax errors."""
        import py_compile
        results: Dict[str, ModuleHealth] = {}
        for path, record in self._records.items():
            try:
                py_compile.compile(record.absolute_path, doraise=True)
                record.health = ModuleHealth.HEALTHY
                results[path] = ModuleHealth.HEALTHY
            except py_compile.PyCompileError:
                record.health = ModuleHealth.SYNTAX_ERROR
                results[path] = ModuleHealth.SYNTAX_ERROR
        return results

    def export_json(self, output_path: str) -> None:
        """Dump full registry to JSON for external consumption."""
        data = [r.to_dict() for r in self._records.values()]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def stats(self) -> Dict[str, Any]:
        """Aggregate statistics across the registry."""
        total = len(self._records)
        type_counts = {t.value: 0 for t in ModuleType}
        health_counts = {h.value: 0 for h in ModuleHealth}
        total_lines = 0
        total_classes = 0
        total_functions = 0
        for r in self._records.values():
            type_counts[r.module_type.value] += 1
            health_counts[r.health.value] += 1
            total_lines += r.line_count
            total_classes += len(r.classes)
            total_functions += len(r.functions)
        return {
            "total_modules": total,
            "type_distribution": type_counts,
            "health_distribution": health_counts,
            "total_lines_of_code": total_lines,
            "total_classes": total_classes,
            "total_functions": total_functions,
            "last_scan_timestamp": self._last_scan,
        }

    def get_module(self, relative_path: str) -> Optional[ModuleRecord]:
        return self._records.get(relative_path)

    def get_by_symbol(self, symbol_name: str) -> List[ModuleRecord]:
        """Find modules that define a specific class or function name."""
        results = []
        for r in self._records.values():
            for c in r.classes:
                if c.name == symbol_name:
                    results.append(r)
                    break
            else:
                for f in r.functions:
                    if f.name == symbol_name:
                        results.append(r)
                        break
        return results


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    repo = os.path.dirname(os.path.abspath(__file__))
    if not os.path.exists(os.path.join(repo, "governance")):
        # fallback: running standalone; use current directory
        repo = os.getcwd()
    reg = ModuleRegistry(repo)
    print(f"[ModuleRegistry] Scanning repository: {repo}")
    reg.refresh()
    stats = reg.stats()
    print(f"\n=== MAGNATRIX-OS Module Registry Demo ===")
    print(f"Total modules indexed: {stats['total_modules']}")
    print(f"Total lines of code: {stats['total_lines_of_code']}")
    print(f"Total classes: {stats['total_classes']}")
    print(f"Total functions: {stats['total_functions']}")
    print(f"\nType distribution:")
    for t, c in stats["type_distribution"].items():
        if c:
            print(f"  {t}: {c}")
    print(f"\nHealth distribution:")
    for h, c in stats["health_distribution"].items():
        if c:
            print(f"  {h}: {c}")
    # Run health check on a small sample
    print(f"\nRunning health check on first 10 modules...")
    health = reg.health_check()
    for i, (p, h) in enumerate(health.items()):
        if i >= 10:
            break
        print(f"  {p}: {h.value}")
    # Search demo
    print(f"\nSearching for 'poisoning'...")
    results = reg.search("poisoning")
    for r in results[:5]:
        print(f"  -> {r.relative_path} ({len(r.classes)} classes, {len(r.functions)} functions)")
    # Export demo
    export_path = os.path.join(repo, "module_registry.json")
    reg.export_json(export_path)
    print(f"\nRegistry exported to: {export_path}")


if __name__ == "__main__":
    _demo()

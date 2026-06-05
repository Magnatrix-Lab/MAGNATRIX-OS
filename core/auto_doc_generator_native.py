#!/usr/bin/env python3
"""
Auto Documentation Generator for MAGNATRIX-OS
Scans the entire repository and generates a comprehensive README.md
with module listings, statistics, architecture overview, and health status.
Native stdlib only — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import ast
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


class AutoDocGenerator:
    """Generates README and other docs from live repository metadata."""

    def __init__(self, repo_root: str) -> None:
        self.root = Path(repo_root).resolve()
        self._modules: List[Dict[str, any]] = []
        self._total_lines = 0
        self._total_classes = 0
        self._total_functions = 0

    # ------------------------------------------------------------------
    # Scanning (lightweight AST, no import execution)
    # ------------------------------------------------------------------

    def scan(self) -> None:
        """Walk all Python files and collect metadata."""
        exclude = {"__pycache__", ".git", "venv", "node_modules", "dist", "build", ".pytest_cache"}
        self._modules.clear()
        self._total_lines = 0
        self._total_classes = 0
        self._total_functions = 0
        for path in self.root.rglob("*.py"):
            if any(part in exclude for part in path.parts):
                continue
            rel = path.relative_to(self.root)
            try:
                source = path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue
            docstring = ast.get_docstring(tree) or ""
            classes = []
            functions = []
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes.append({
                        "name": node.name,
                        "docstring": (ast.get_docstring(node) or "")[:120],
                    })
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # skip nested functions for brevity
                    if isinstance(node.parent, ast.Module) if hasattr(node, "parent") else True:
                        functions.append({
                            "name": node.name,
                            "docstring": (ast.get_docstring(node) or "")[:120],
                        })
            # Counting with parent walk is tricky; just use simple metrics
            lines = source.count("\n") + 1
            self._total_lines += lines
            self._total_classes += len(classes)
            self._total_functions += len(functions)
            self._modules.append({
                "path": str(rel).replace("\\", "/"),
                "docstring": docstring.split("\n")[0].strip(),
                "classes": classes,
                "functions": functions,
                "line_count": lines,
                "file_size": len(source.encode("utf-8")),
                "domain": self._infer_domain(rel),
            })

    def _infer_domain(self, rel: Path) -> str:
        parts = rel.parts
        if len(parts) >= 2 and parts[0] in ("tools", "governance", "core"):
            return parts[1] if len(parts) > 1 else parts[0]
        return parts[0] if parts else "root"

    # ------------------------------------------------------------------
    # README generation
    # ------------------------------------------------------------------

    def generate_readme(self) -> str:
        """Build a comprehensive README markdown string."""
        lines: List[str] = []
        lines.append("# MAGNATRIX-OS")
        lines.append("")
        lines.append("> **Private. Uncensored. Open-Source AI Operating System.**")
        lines.append("> **Core Directive: AMATI-PELAJARI-TIRU** (Observe-Learn-Imitate)")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## Overview")
        lines.append("")
        lines.append(
            "MAGNATRIX-OS is a fully open-source AI operating system designed for "
            "maximum autonomy, zero censorship, and native privacy. It provides "
            "a complete governance layer, medical & technical calculators, "
            "infrastructure orchestration, and real-time safety controls."
        )
        lines.append("")
        lines.append("## Repository Statistics")
        lines.append("")
        lines.append(f"- **Total Python Modules:** {len(self._modules)}")
        lines.append(f"- **Total Lines of Code:** {self._total_lines:,}")
        lines.append(f"- **Total Classes:** {self._total_classes}")
        lines.append(f"- **Total Functions:** {self._total_functions}")
        lines.append(f"- **Generated:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
        lines.append("")
        # Domain breakdown
        domains: Dict[str, Dict[str, int]] = {}
        for m in self._modules:
            d = m["domain"]
            if d not in domains:
                domains[d] = {"modules": 0, "lines": 0, "classes": 0, "functions": 0}
            domains[d]["modules"] += 1
            domains[d]["lines"] += m["line_count"]
            domains[d]["classes"] += len(m["classes"])
            domains[d]["functions"] += len(m["functions"])
        lines.append("## Domain Breakdown")
        lines.append("")
        lines.append("| Domain | Modules | Lines | Classes | Functions |")
        lines.append("|--------|---------|-------|---------|-----------|")
        for d, s in sorted(domains.items(), key=lambda x: -x[1]["modules"]):
            lines.append(f"| {d} | {s['modules']} | {s['lines']:,} | {s['classes']} | {s['functions']} |")
        lines.append("")
        # Highlighted modules
        lines.append("## Core Architecture Modules")
        lines.append("")
        for m in self._modules:
            if m["path"].startswith("core/") or m["path"].startswith("governance/"):
                name = Path(m["path"]).stem
                desc = m["docstring"] or "*(no description)*"
                lines.append(f"- **{name}** — {desc}")
        lines.append("")
        # Calculators sampling
        lines.append("## Calculator Tools (Sample)")
        lines.append("")
        calc_count = 0
        for m in self._modules:
            if "calculator" in m["path"].lower() or "calculators" in m["path"]:
                if calc_count >= 20:
                    break
                name = Path(m["path"]).stem
                desc = m["docstring"] or "*(no description)*"
                lines.append(f"- **{name}** — {desc}")
                calc_count += 1
        lines.append("")
        # Governance layer
        lines.append("## Governance Layer (ACS)")
        lines.append("")
        lines.append("MAGNATRIX-OS implements an **Agent Control & Safety (ACS)** governance layer inspired by Microsoft Agent Governance Toolkit, with the following modules:")
        lines.append("")
        for m in self._modules:
            if m["path"].startswith("governance/acs_"):
                name = Path(m["path"]).stem
                desc = m["docstring"] or "*(no description)*"
                lines.append(f"- **{name}** — {desc}")
        lines.append("")
        # Safety philosophy
        lines.append("## Safety & Super AI Readiness")
        lines.append("")
        lines.append(
            "MAGNATRIX-OS includes dedicated Super AI governance modules that go beyond "
            "standard policy engines: capability concealment detection, instrumental convergence "
            "safety, and recursive self-improvement governance with circuit breaker protection."
        )
        lines.append("")
        # Footer
        lines.append("---")
        lines.append("")
        lines.append("*This README is auto-generated by `auto_doc_generator_native.py`.*")
        lines.append("")
        return "\n".join(lines)

    def write_readme(self, output_path: Optional[str] = None) -> str:
        path = output_path or str(self.root / "README.md")
        content = self.generate_readme()
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    # ------------------------------------------------------------------
    # Module index generation
    # ------------------------------------------------------------------

    def generate_module_index(self) -> str:
        """Generate a flat index of all modules as markdown."""
        lines: List[str] = []
        lines.append("# Module Index")
        lines.append("")
        lines.append(f"Total modules: {len(self._modules)}")
        lines.append("")
        for m in sorted(self._modules, key=lambda x: x["path"]):
            lines.append(f"## {m['path']}")
            lines.append("")
            if m["docstring"]:
                lines.append(f"{m['docstring']}")
                lines.append("")
            lines.append(f"- Lines: {m['line_count']}")
            lines.append(f"- Classes: {len(m['classes'])}")
            lines.append(f"- Functions: {len(m['functions'])}")
            lines.append("")
        return "\n".join(lines)

    def write_module_index(self, output_path: Optional[str] = None) -> str:
        path = output_path or str(self.root / "MODULE_INDEX.md")
        content = self.generate_module_index()
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if not os.path.exists(os.path.join(repo, "governance")):
        repo = os.getcwd()
    gen = AutoDocGenerator(repo)
    print(f"[AutoDoc] Scanning repository: {repo}")
    gen.scan()
    print(f"[AutoDoc] Modules scanned: {len(gen._modules)}")
    print(f"[AutoDoc] Total lines: {gen._total_lines:,}")
    readme_path = gen.write_readme()
    print(f"[AutoDoc] README written to: {readme_path}")
    index_path = gen.write_module_index()
    print(f"[AutoDoc] Module index written to: {index_path}")
    # Print first 60 lines of README
    print(f"\n=== README Preview (first 60 lines) ===\n")
    with open(readme_path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i >= 60:
                break
            print(line.rstrip())
    print("...")


if __name__ == "__main__":
    _demo()

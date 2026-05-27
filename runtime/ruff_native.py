#!/usr/bin/env python3
"""
MAGNATRIX-OS Ruff Native
Python code linter and formatter (simplified ruff-inspired).
Pure Python stdlib.
"""
import ast, os, re, tokenize, io
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class LintError:
    line: int
    col: int
    code: str
    message: str
    severity: str = "error"


class RuffNative:
    """
    Simplified Python linter with common rule checks.
    """

    RULES = {
        "E501": "Line too long (>79 chars)",
        "E302": "Expected 2 blank lines before function",
        "E305": "Expected 2 blank lines after function",
        "F401": "Module imported but unused",
        "F821": "Undefined name",
        "W291": "Trailing whitespace",
        "E111": "Indentation not multiple of 4",
    }

    def __init__(self, max_line_length: int = 79):
        self.max_line_length = max_line_length
        self._errors: List[LintError] = []

    def lint_file(self, path: str) -> List[LintError]:
        """Lint a single Python file."""
        self._errors = []
        try:
            with open(path, "r") as f:
                source = f.read()
                lines = source.splitlines()
        except Exception as e:
            return [LintError(0, 0, "E000", str(e))]

        # Parse AST for semantic checks
        try:
            tree = ast.parse(source)
            self._check_ast(tree)
        except SyntaxError:
            pass

        # Line-based checks
        self._check_lines(lines)
        return self._errors

    def lint_string(self, source: str) -> List[LintError]:
        """Lint source code string."""
        self._errors = []
        lines = source.splitlines()
        try:
            tree = ast.parse(source)
            self._check_ast(tree)
        except SyntaxError:
            pass
        self._check_lines(lines)
        return self._errors

    def _check_ast(self, tree: ast.AST):
        """AST-based semantic checks."""
        # Collect imports and names
        imports = set()
        used_names = set()
        defined_names = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.asname or alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    imports.add(alias.asname or alias.name)
            elif isinstance(node, ast.Name):
                if isinstance(node.ctx, ast.Load):
                    used_names.add(node.id)
                elif isinstance(node.ctx, ast.Store):
                    defined_names.add(node.id)

        # Check unused imports
        for imp in imports:
            if imp not in used_names and imp not in defined_names:
                self._errors.append(LintError(1, 0, "F401", f"'{imp}' imported but unused", "warning"))

    def _check_lines(self, lines: List[str]):
        """Line-based style checks."""
        prev_line_blank = False
        in_function = False
        function_end = 0

        for i, line in enumerate(lines, 1):
            # Line length
            if len(line) > self.max_line_length:
                self._errors.append(LintError(i, self.max_line_length, "E501", f"Line too long ({len(line)} > {self.max_line_length})", "warning"))

            # Trailing whitespace
            if line.rstrip() != line:
                self._errors.append(LintError(i, len(line.rstrip()), "W291", "Trailing whitespace", "warning"))

            # Indentation
            stripped = line.lstrip()
            if stripped and line[:len(line) - len(stripped)]:
                indent = len(line) - len(stripped)
                if indent % 4 != 0:
                    self._errors.append(LintError(i, 0, "E111", f"Indentation {indent} not multiple of 4", "warning"))

            # Blank lines around functions (simplified)
            if stripped.startswith("def "):
                if i > 2 and not prev_line_blank:
                    pass  # Simplified

            prev_line_blank = not stripped

    def format_file(self, path: str) -> str:
        """Basic formatting: trim trailing whitespace, ensure newline at end."""
        with open(path, "r") as f:
            lines = f.readlines()
        formatted = [line.rstrip() + "
" for line in lines]
        while formatted and formatted[-1].strip() == "":
            formatted.pop()
        if formatted:
            formatted.append("
")
        return "".join(formatted)

    def stats(self) -> Dict[str, Any]:
        return {
            "total_errors": len(self._errors),
            "by_severity": {
                "error": sum(1 for e in self._errors if e.severity == "error"),
                "warning": sum(1 for e in self._errors if e.severity == "warning"),
            }
        }


def _demo():
    print("=" * 60)
    print("MAGNATRIX-OS Ruff Native Demo")
    print("=" * 60)
    test_code = """
import os
import sys
x = 1
    y = 2
def long_function():
    return "This is a very long line that definitely exceeds the seventy nine character limit for sure"
def another():
    pass
"""
    ruff = RuffNative(max_line_length=79)
    errors = ruff.lint_string(test_code)
    print(f"Found {len(errors)} issues:")
    for e in errors[:5]:
        print(f"  {e.code}: {e.message} (line {e.line})")
    print(f"Stats: {ruff.stats()}")
    print("=" * 60)


if __name__ == "__main__":
    _demo()

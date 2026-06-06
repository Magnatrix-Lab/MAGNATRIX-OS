#!/usr/bin/env python3
"""
Doc Generator for MAGNATRIX-OS
Auto-documentation from docstrings (Markdown/HTML API docs).
Pure stdlib -- no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import ast
import inspect
import os
import re
from typing import Any, Dict, List, Optional


class DocGenerator:
    """Auto-generate documentation from Python source code."""

    def __init__(self) -> None:
        self._docs: Dict[str, Dict[str, Any]] = {}

    def parse_module(self, file_path: str) -> Dict[str, Any]:
        """Parse a Python module and extract documentation."""
        with open(file_path, 'r') as f:
            source = f.read()

        tree = ast.parse(source)
        module_doc = ast.get_docstring(tree) or ''

        classes = []
        functions = []

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(self._parse_class(node))
            elif isinstance(node, ast.FunctionDef) and node.name != '_demo':
                functions.append(self._parse_function(node))

        return {
            'file': os.path.basename(file_path),
            'module_doc': module_doc,
            'classes': classes,
            'functions': functions,
        }

    def _parse_class(self, node: ast.ClassDef) -> Dict[str, Any]:
        docstring = ast.get_docstring(node) or ''
        methods = []

        for item in node.body:
            if isinstance(item, ast.FunctionDef) and not item.name.startswith('_'):
                methods.append(self._parse_function(item))

        return {
            'name': node.name,
            'docstring': docstring,
            'methods': methods,
        }

    def _parse_function(self, node: ast.FunctionDef) -> Dict[str, Any]:
        docstring = ast.get_docstring(node) or ''

        args = []
        for arg in node.args.args:
            if arg.arg != 'self':
                args.append(arg.arg)

        return {
            'name': node.name,
            'docstring': docstring,
            'args': args,
            'line': node.lineno,
        }

    def generate_markdown(self, module_info: Dict[str, Any]) -> str:
        """Generate Markdown documentation."""
        lines = []
        lines.append(f"# {module_info['file']}")
        lines.append('')
        if module_info['module_doc']:
            lines.append(module_info['module_doc'])
            lines.append('')

        # Functions
        if module_info['functions']:
            lines.append('## Functions')
            lines.append('')
            for func in module_info['functions']:
                args_str = ', '.join(func['args'])
                lines.append(f"### `{func['name']}({args_str})`")
                lines.append('')
                if func['docstring']:
                    lines.append(func['docstring'])
                    lines.append('')

        # Classes
        for cls in module_info['classes']:
            lines.append(f"## Class `{cls['name']}`")
            lines.append('')
            if cls['docstring']:
                lines.append(cls['docstring'])
                lines.append('')

            for method in cls['methods']:
                args_str = ', '.join(method['args'])
                lines.append(f"### `{method['name']}({args_str})`")
                lines.append('')
                if method['docstring']:
                    lines.append(method['docstring'])
                    lines.append('')

        return '\n'.join(lines)

    def scan_directory(self, dir_path: str) -> List[Dict[str, Any]]:
        results = []
        for file in os.listdir(dir_path):
            if file.endswith('.py'):
                path = os.path.join(dir_path, file)
                try:
                    info = self.parse_module(path)
                    results.append(info)
                except Exception:
                    pass
        return results


def _demo() -> None:
    print("=== Doc Generator Demo ===\n")

    gen = DocGenerator()

    # Parse a sample module
    info = gen.parse_module('/mnt/agents/MAGNATRIX-OS/core/config_manager_native.py')
    print(f"Module: {info['file']}")
    print(f"Classes: {len(info['classes'])}")
    print(f"Functions: {len(info['functions'])}")

    for cls in info['classes']:
        print(f"  Class: {cls['name']}")
        for m in cls['methods'][:3]:
            print(f"    Method: {m['name']}")

    print(f"\nGenerated {len(gen.generate_markdown(info))} chars of Markdown")

    print("\n=== Doc Generator Demo Complete ===")


if __name__ == '__main__':
    _demo()

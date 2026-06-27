#!/usr/bin/env python3
"""
Auto Documentation + Test Generator for MAGNATRIX-OS
====================================================
Scans all 166 modules, generates README with API docs, dependency graphs,
architecture diagrams. Auto-generates test suites for untested modules.
Pure stdlib.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations
import ast, importlib, inspect, os, re, time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple


@dataclass
class ModuleDoc:
    """Documentation for a single module."""
    module_name: str
    file_path: str
    description: str = ""
    classes: List[Dict[str, Any]] = field(default_factory=list)
    functions: List[Dict[str, Any]] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    size_bytes: int = 0
    line_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TestCase:
    """Generated test case."""
    target_module: str
    target_class: str
    test_name: str
    test_code: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ModuleScanner:
    """Scans Python modules for documentation extraction."""

    def __init__(self, repo_root: str) -> None:
        self.repo_root = Path(repo_root)
        self.modules: List[ModuleDoc] = []

    def scan_all(self, pattern: str = "core/*_native.py") -> List[ModuleDoc]:
        """Scan all modules matching pattern."""
        core_dir = self.repo_root / "core"
        if not core_dir.exists():
            return []
        for fpath in sorted(core_dir.glob("*_native.py")):
            doc = self._scan_file(fpath)
            if doc:
                self.modules.append(doc)
        return self.modules

    def _scan_file(self, fpath: Path) -> Optional[ModuleDoc]:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                source = f.read()
            tree = ast.parse(source)
            size_bytes = len(source.encode("utf-8"))
            line_count = len(source.splitlines())
            module_name = fpath.stem
            doc = ModuleDoc(module_name=module_name, file_path=str(fpath), size_bytes=size_bytes, line_count=line_count)
            # Extract docstring
            if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, (ast.Str, ast.Constant)):
                doc.description = str(tree.body[0].value.s if hasattr(tree.body[0].value, "s") else tree.body[0].value.value)
            # Extract classes
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_doc = self._extract_class(node)
                    doc.classes.append(class_doc)
                elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        doc.imports.append(alias.name if alias.name else alias.asname)
            # Extract top-level functions
            for node in tree.body:
                if isinstance(node, ast.FunctionDef):
                    doc.functions.append(self._extract_function(node))
            return doc
        except Exception:
            return None

    def _extract_class(self, node: ast.ClassDef) -> Dict[str, Any]:
        methods = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                methods.append(self._extract_function(item))
        return {
            "name": node.name,
            "docstring": ast.get_docstring(node) or "",
            "methods": methods,
            "line_count": node.end_lineno - node.lineno if node.end_lineno else 0,
        }

    def _extract_function(self, node: ast.FunctionDef) -> Dict[str, Any]:
        args = [arg.arg for arg in node.args.args]
        return {
            "name": node.name,
            "args": args,
            "docstring": ast.get_docstring(node) or "",
            "line_count": node.end_lineno - node.lineno if node.end_lineno else 0,
        }

    def build_dependency_graph(self) -> Dict[str, List[str]]:
        """Build module dependency graph."""
        graph = {}
        for mod in self.modules:
            deps = []
            for imp in mod.imports:
                for other in self.modules:
                    if other.module_name in imp or imp in other.module_name:
                        deps.append(other.module_name)
            graph[mod.module_name] = list(set(deps))
        return graph

    def get_stats(self) -> Dict[str, Any]:
        total_lines = sum(m.line_count for m in self.modules)
        total_classes = sum(len(m.classes) for m in self.modules)
        total_functions = sum(len(m.functions) for m in self.modules)
        return {
            "total_modules": len(self.modules),
            "total_lines": total_lines,
            "total_classes": total_classes,
            "total_functions": total_functions,
            "avg_module_size": total_lines / len(self.modules) if self.modules else 0,
        }


class DocGenerator:
    """Generates documentation from scanned modules."""

    def __init__(self, scanner: ModuleScanner) -> None:
        self.scanner = scanner

    def generate_readme(self) -> str:
        """Generate comprehensive README."""
        stats = self.scanner.get_stats()
        lines = [
            "# MAGNATRIX-OS API Documentation",
            "",
            f"**Total Modules:** {stats['total_modules']}",
            f"**Total Lines of Code:** {stats['total_lines']:,}",
            f"**Total Classes:** {stats['total_classes']}",
            f"**Total Functions:** {stats['total_functions']}",
            f"**Average Module Size:** {stats['avg_module_size']:.0f} lines",
            "",
            "## Module Index",
            "",
        ]
        for mod in sorted(self.scanner.modules, key=lambda m: m.module_name):
            lines.append(f"### {mod.module_name}")
            lines.append(f"- **File:** `{mod.file_path}`")
            lines.append(f"- **Size:** {mod.size_bytes:,} bytes, {mod.line_count} lines")
            if mod.description:
                desc = mod.description[:200].replace('\n', ' ')
                lines.append(f"- **Description:** {desc}")
            if mod.classes:
                lines.append(f"- **Classes:** {len(mod.classes)}")
                for cls in mod.classes[:5]:
                    lines.append(f"  - `{cls['name']}` — {len(cls['methods'])} methods")
            if mod.functions:
                lines.append(f"- **Functions:** {len(mod.functions)}")
            lines.append("")
        return "\n".join(lines)

    def generate_architecture_diagram(self) -> str:
        """Generate ASCII architecture diagram."""
        graph = self.scanner.build_dependency_graph()
        lines = [
            "# MAGNATRIX-OS Architecture",
            "",
            "```",
            "+--------------------------------+",
            "|       MAGNATRIX-OS Core        |",
            "+--------------------------------+",
            "                |",
        ]
        # Group modules by layer
        layers = {
            "Infrastructure": ["auth", "config", "logging", "cache", "security"],
            "Data": ["database", "data_lake", "filesystem", "feature_store"],
            "AI": ["local", "multi_model", "model_router", "ai_model_registry", "moa"],
            "Integration": ["distributed", "federation_sync", "integration", "swarm"],
            "Application": ["dashboard", "cli", "hft_trading", "exchange"],
        }
        for layer_name, module_names in layers.items():
            lines.append(f"        +------[{layer_name}]------+")
            for mod_name in module_names:
                if any(mod_name in m.module_name for m in self.scanner.modules):
                    lines.append(f"        |  {mod_name[:30]:30s}  |")
            lines.append(f"        +------------------------+")
        lines.append("```")
        return "\n".join(lines)

    def generate_api_reference(self) -> str:
        """Generate API reference in markdown."""
        lines = ["# API Reference", ""]
        for mod in sorted(self.scanner.modules, key=lambda m: m.module_name):
            lines.append(f"## {mod.module_name}")
            lines.append("")
            for cls in mod.classes:
                lines.append(f"### class `{cls['name']}`")
                if cls['docstring']:
                    lines.append(f"{cls['docstring']}")
                lines.append("")
                for method in cls['methods'][:10]:
                    args_str = ", ".join(method['args'])
                    lines.append(f"- `{method['name']}({args_str})`")
                lines.append("")
        return "\n".join(lines)

    def write_docs(self, output_dir: str = "docs") -> Dict[str, str]:
        """Write all documentation files."""
        out = Path(output_dir)
        out.mkdir(exist_ok=True)
        files = {}
        readme = self.generate_readme()
        (out / "README.md").write_text(readme, encoding="utf-8")
        files["README"] = str(out / "README.md")
        arch = self.generate_architecture_diagram()
        (out / "ARCHITECTURE.md").write_text(arch, encoding="utf-8")
        files["ARCHITECTURE"] = str(out / "ARCHITECTURE.md")
        api = self.generate_api_reference()
        (out / "API_REFERENCE.md").write_text(api, encoding="utf-8")
        files["API_REFERENCE"] = str(out / "API_REFERENCE.md")
        return files


class TestGenerator:
    """Generates test suites automatically."""

    def __init__(self, scanner: ModuleScanner) -> None:
        self.scanner = scanner
        self.test_cases: List[TestCase] = []

    def generate_for_module(self, module_doc: ModuleDoc) -> List[TestCase]:
        """Generate test cases for a module."""
        tests = []
        for cls in module_doc.classes:
            class_name = cls['name']
            # Generate instantiation test
            test_code = self._generate_instantiation_test(module_doc.module_name, class_name)
            tests.append(TestCase(
                target_module=module_doc.module_name,
                target_class=class_name,
                test_name=f"test_{class_name}_instantiate",
                test_code=test_code,
            ))
            # Generate method tests for each method
            for method in cls['methods']:
                if method['name'] in ('__init__', '__str__'):
                    continue
                test_code = self._generate_method_test(module_doc.module_name, class_name, method)
                tests.append(TestCase(
                    target_module=module_doc.module_name,
                    target_class=class_name,
                    test_name=f"test_{class_name}_{method['name']}",
                    test_code=test_code,
                ))
        return tests

    def _generate_instantiation_test(self, module_name: str, class_name: str) -> str:
        return f'''    def test_{class_name}_instantiate(self):
        """Test that {class_name} can be instantiated."""
        try:
            from {module_name} import {class_name}
            instance = {class_name}()
            self.assertIsNotNone(instance)
        except Exception as e:
            self.fail(f"Failed to instantiate {class_name}: {{e}}")
'''

    def _generate_method_test(self, module_name: str, class_name: str, method: Dict[str, Any]) -> str:
        method_name = method['name']
        args = method['args']
        # Build simple args for calling
        call_args = []
        for arg in args:
            if arg == 'self':
                continue
            call_args.append("None")
        args_str = ", ".join(call_args) if call_args else ""
        return f'''    def test_{class_name}_{method_name}(self):
        """Test {class_name}.{method_name}."""
        try:
            from {module_name} import {class_name}
            instance = {class_name}()
            if hasattr(instance, "{method_name}"):
                result = instance.{method_name}({args_str})
                # Basic assertion: method runs without error
                self.assertTrue(True)
        except Exception as e:
            self.fail(f"{method_name} failed: {{e}}")
'''

    def generate_all(self) -> List[TestCase]:
        """Generate tests for all modules."""
        for mod in self.scanner.modules:
            tests = self.generate_for_module(mod)
            self.test_cases.extend(tests)
        return self.test_cases

    def write_test_files(self, output_dir: str = "tests/auto") -> Dict[str, str]:
        """Write generated test files."""
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        files = {}
        # Group by module
        by_module: Dict[str, List[TestCase]] = {}
        for tc in self.test_cases:
            if tc.target_module not in by_module:
                by_module[tc.target_module] = []
            by_module[tc.target_module].append(tc)
        for module_name, tests in by_module.items():
            filename = f"test_{module_name}.py"
            content = self._build_test_file(module_name, tests)
            (out / filename).write_text(content, encoding="utf-8")
            files[module_name] = str(out / filename)
        return files

    def _build_test_file(self, module_name: str, tests: List[TestCase]) -> str:
        lines = [
            f"#!/usr/bin/env python3",
            f"\"\"\"Auto-generated tests for {module_name}.\"\"\"",
            f"import unittest",
            f"",
            f"class Test{module_name.replace('_', '').title()}(unittest.TestCase):",
            f"    \"\"\"Test suite for {module_name}.\"\"\"",
            f"",
        ]
        for tc in tests:
            lines.append(tc.test_code)
        lines.append("")
        lines.append(f'if __name__ == "__main__":')
        lines.append(f'    unittest.main()')
        lines.append("")
        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_tests": len(self.test_cases),
            "modules_covered": len(set(tc.target_module for tc in self.test_cases)),
        }


class AutoDocTestEngine:
    """Top-level engine for documentation and test generation."""

    def __init__(self, repo_root: str = ".") -> None:
        self.repo_root = repo_root
        self.scanner = ModuleScanner(repo_root)
        self.doc_generator = DocGenerator(self.scanner)
        self.test_generator = TestGenerator(self.scanner)

    def run(self) -> Dict[str, Any]:
        """Run full doc + test generation pipeline."""
        results = {"scanned": 0, "docs_generated": {}, "tests_generated": {}, "errors": []}
        try:
            modules = self.scanner.scan_all()
            results["scanned"] = len(modules)
            results["scanner_stats"] = self.scanner.get_stats()
        except Exception as e:
            results["errors"].append(f"Scan failed: {e}")
            return results
        try:
            doc_files = self.doc_generator.write_docs()
            results["docs_generated"] = doc_files
        except Exception as e:
            results["errors"].append(f"Doc generation failed: {e}")
        try:
            self.test_generator.generate_all()
            test_files = self.test_generator.write_test_files()
            results["tests_generated"] = test_files
            results["test_stats"] = self.test_generator.get_stats()
        except Exception as e:
            results["errors"].append(f"Test generation failed: {e}")
        return results

    def get_status(self) -> Dict[str, Any]:
        return {
            "modules_scanned": len(self.scanner.modules),
            "scanner_stats": self.scanner.get_stats(),
            "test_stats": self.test_generator.get_stats(),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_status()

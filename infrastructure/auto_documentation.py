"""
infrastructure/auto_documentation.py
=====================================
MAGNATRIX Auto-Documentation Generator
Layer 18: Meta-Cognition

Auto-scan codebase dan generate docs / diagrams / reports.
"""

import ast, json, os, re, time, uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from collections import defaultdict

class CodeScanner:
    """Scan Python codebase untuk extract structure"""

    def __init__(self, root_path: str = "."):
        self.root = root_path
        self._modules: Dict[str, Dict] = {}

    def scan(self) -> Dict:
        """Scan all Python files"""
        for dirpath, _, filenames in os.walk(self.root):
            for fname in filenames:
                if fname.endswith(".py"):
                    fpath = os.path.join(dirpath, fname)
                    rel_path = os.path.relpath(fpath, self.root)
                    try:
                        with open(fpath, 'r', encoding='utf-8') as f:
                            source = f.read()
                        self._modules[rel_path] = self._parse_module(source, rel_path)
                    except Exception:
                        pass
        return self._modules

    def _parse_module(self, source: str, path: str) -> Dict:
        """Parse single module"""
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return {"path": path, "error": "Syntax error"}

        classes = []
        functions = []
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                classes.append({"name": node.name, "methods": methods, "line": node.lineno})
            elif isinstance(node, ast.FunctionDef):
                functions.append({"name": node.name, "args": [a.arg for a in node.args.args], "line": node.lineno})
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                if isinstance(node, ast.Import):
                    imports.extend([alias.name for alias in node.names])
                else:
                    imports.append(node.module or "")

        return {
            "path": path,
            "lines": source.count("\n"),
            "classes": classes,
            "functions": functions,
            "imports": list(set(imports)),
            "docstring": ast.get_docstring(tree)
        }

class DocGenerator:
    """Generate documentation dari scanned code"""

    def __init__(self, scanner: CodeScanner):
        self.scanner = scanner

    def generate_module_docs(self) -> str:
        """Generate markdown docs untuk semua modules"""
        modules = self.scanner._modules
        lines = ["# MAGNATRIX Codebase Documentation", ""]

        for path, info in sorted(modules.items()):
            lines.append(f"## `{path}`")
            lines.append(f"- Lines: {info.get('lines', 0)}")
            if info.get("docstring"):
                lines.append(f"- Description: {info['docstring'][:100]}")
            lines.append(f"- Classes: {len(info.get('classes', []))}")
            for cls in info.get("classes", []):
                lines.append(f"  - `{cls['name']}` ({len(cls['methods'])} methods)")
            lines.append(f"- Functions: {len(info.get('functions', []))}")
            lines.append("")

        return "\n".join(lines)

    def generate_architecture_diagram(self) -> str:
        """Generate Mermaid architecture diagram"""
        modules = self.scanner._modules

        # Extract layer info dari paths
        layers = defaultdict(list)
        for path in modules:
            parts = path.split(os.sep)
            if len(parts) > 1:
                layers[parts[0]].append(path)

        lines = ["```mermaid", "graph TD"]

        # Layer nodes
        for layer_name, files in sorted(layers.items()):
            node_id = layer_name.replace("-", "_")
            lines.append(f"    {node_id}[{layer_name}<br/>{len(files)} files]")

        # Dependencies
        for path, info in modules.items():
            for imp in info.get("imports", []):
                if "magnatrix" in imp.lower() or any(imp.startswith(l) for l in layers):
                    src = path.split(os.sep)[0].replace("-", "_")
                    # Simplified: connect layers

        lines.append("```")
        return "\n".join(lines)

    def generate_stats(self) -> Dict:
        """Generate codebase statistics"""
        modules = self.scanner._modules
        total_lines = sum(m.get("lines", 0) for m in modules.values())
        total_classes = sum(len(m.get("classes", [])) for m in modules.values())
        total_functions = sum(len(m.get("functions", [])) for m in modules.values())

        return {
            "total_files": len(modules),
            "total_lines": total_lines,
            "total_classes": total_classes,
            "total_functions": total_functions,
            "avg_file_size": total_lines / max(len(modules), 1),
            "layers": len(set(p.split(os.sep)[0] for p in modules if os.sep in p))
        }

class AutoDocumentation:
    """Main orchestrator"""

    def __init__(self, root_path: str = "."):
        self.scanner = CodeScanner(root_path)
        self.generator = DocGenerator(self.scanner)

    async def generate_all(self) -> Dict:
        """Generate complete documentation"""
        self.scanner.scan()

        return {
            "module_docs": self.generator.generate_module_docs(),
            "architecture_diagram": self.generator.generate_architecture_diagram(),
            "stats": self.generator.generate_stats(),
            "generated_at": time.time()
        }

    def get_status(self) -> Dict:
        return {"modules_scanned": len(self.scanner._modules)}


if __name__ == "__main__":
    async def demo():
        doc = AutoDocumentation("/mnt/agents/MAGNATRIX-OS")
        result = await doc.generate_all()
        print(f"Stats: {result['stats']}")
        print(f"Diagram preview:\n{result['architecture_diagram'][:200]}...")

    import asyncio
    asyncio.run(demo())

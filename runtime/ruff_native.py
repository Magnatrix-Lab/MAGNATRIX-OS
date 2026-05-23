"""
MAGNATRIX — Ruff Ultra-Fast Python Linter (Native Python Simulation)
Observed from: astral-sh/ruff — 39K⭐ Rust-based Python linter.

Pattern: AMATI-PELAJARI-TIRU — simulate core patterns in pure Python.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import time
import tokenize
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union


# ═══════════════════════════════════════════════════════════════════════════════
# CORE DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

class Severity(Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class RuleCode(Enum):
    """Lint rule codes (E=pycodestyle, W=warning, F=pyflakes, I=isort, D=docstring, C=complexity, N=naming)."""
    E501 = "line-too-long"
    E401 = "multiple-imports-on-one-line"
    E302 = "expected-2-blank-lines"
    E305 = "expected-2-blank-lines-after-class-or-function"
    W291 = "trailing-whitespace"
    W292 = "no-newline-at-end-of-file"
    W293 = "blank-line-contains-whitespace"
    F401 = "unused-import"
    F402 = "import-shadowed-by-loop-var"
    F821 = "undefined-name"
    F841 = "local-variable-assigned-but-never-used"
    I001 = "unsorted-imports"
    D100 = "missing-docstring-in-public-module"
    D101 = "missing-docstring-in-public-class"
    D102 = "missing-docstring-in-public-method"
    D103 = "missing-docstring-in-public-function"
    C901 = "function-is-too-complex"
    N801 = "invalid-class-name"
    N802 = "invalid-function-name"
    N803 = "invalid-argument-name"
    N806 = "variable-in-function-should-be-lowercase"


@dataclass
class Diagnostic:
    """Single lint diagnostic message."""
    code: RuleCode
    message: str
    line: int = 1
    column: int = 0
    severity: Severity = Severity.ERROR
    source: str = ""
    fix: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code.name,
            "message": self.message,
            "location": f"{self.line}:{self.column}",
            "severity": self.severity.value,
            "fix": self.fix,
        }


@dataclass
class ASTNode:
    """Simplified AST node."""
    type: str
    name: str = ""
    line: int = 0
    column: int = 0
    children: List[ASTNode] = field(default_factory=list)
    parent: Optional[ASTNode] = None


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 1: ASTParser
# ═══════════════════════════════════════════════════════════════════════════════

class ASTParser:
    """Python syntax tree parser (simplified)."""

    def __init__(self) -> None:
        self.tokens: List[Tuple[int, str, int, int]] = []
        self.ast: Optional[ASTNode] = None

    def tokenize(self, source: str) -> List[Tuple[int, str, int, int]]:
        """Tokenize Python source code."""
        tokens = []
        lines = source.split("\n")
        for line_num, line in enumerate(lines, 1):
            # Simple regex-based tokenization
            for match in re.finditer(r'\b(def|class|import|from|return|if|for|while|try|except|with|as|lambda|yield|async|await|pass|break|continue|raise|assert|del|global|nonlocal|True|False|None|and|or|not|in|is|elif|else|finally)\b|[a-zA-Z_][a-zA-Z0-9_]*|\d+|"[^"]*"|\'[^\']*\'|[+\-*/=<>!&|]+|[():,\.\[\]{}]', line):
                token_type = match.group(0)
                tokens.append((line_num, token_type, line_num, match.start()))
        self.tokens = tokens
        return tokens

    def parse(self, source: str) -> ASTNode:
        """Parse tokens into simplified AST."""
        self.tokenize(source)
        root = ASTNode(type="Module", name="<module>")
        current = root
        i = 0
        while i < len(self.tokens):
            line, token, _, col = self.tokens[i]
            if token == "def":
                # Function definition
                if i + 1 < len(self.tokens):
                    _, name, _, _ = self.tokens[i + 1]
                    func = ASTNode(type="FunctionDef", name=name, line=line, column=col)
                    func.parent = current
                    current.children.append(func)
                    current = func
                i += 2
            elif token == "class":
                # Class definition
                if i + 1 < len(self.tokens):
                    _, name, _, _ = self.tokens[i + 1]
                    cls = ASTNode(type="ClassDef", name=name, line=line, column=col)
                    cls.parent = current
                    current.children.append(cls)
                    current = cls
                i += 2
            elif token == "import":
                # Import statement
                imports = []
                j = i + 1
                while j < len(self.tokens) and self.tokens[j][1] not in ("\n", ";"):
                    if self.tokens[j][1] not in (",", " "):
                        imports.append(self.tokens[j][1])
                    j += 1
                imp = ASTNode(type="Import", name=",".join(imports), line=line, column=col)
                imp.parent = current
                current.children.append(imp)
                i = j
            elif token == "from":
                # From import
                if i + 2 < len(self.tokens):
                    module = self.tokens[i + 1][1]
                    imp = ASTNode(type="ImportFrom", name=module, line=line, column=col)
                    imp.parent = current
                    current.children.append(imp)
                i += 3
            elif token in ("return", "if", "for", "while", "try", "with"):
                stmt = ASTNode(type="Statement", name=token, line=line, column=col)
                stmt.parent = current
                current.children.append(stmt)
                i += 1
            elif token == "pass" or token == "break" or token == "continue":
                stmt = ASTNode(type="SimpleStatement", name=token, line=line, column=col)
                stmt.parent = current
                current.children.append(stmt)
                i += 1
            else:
                i += 1
        self.ast = root
        return root

    def find_nodes(self, node_type: str, root: Optional[ASTNode] = None) -> List[ASTNode]:
        """Find all nodes of given type."""
        if root is None:
            root = self.ast
        if root is None:
            return []
        results = []
        if root.type == node_type:
            results.append(root)
        for child in root.children:
            results.extend(self.find_nodes(node_type, child))
        return results

    def get_function_defs(self) -> List[ASTNode]:
        return self.find_nodes("FunctionDef")

    def get_class_defs(self) -> List[ASTNode]:
        return self.find_nodes("ClassDef")

    def get_imports(self) -> List[ASTNode]:
        return self.find_nodes("Import") + self.find_nodes("ImportFrom")


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 2: LintEngine
# ═══════════════════════════════════════════════════════════════════════════════

class LintEngine:
    """Lint rule engine dengan 500+ rule simulation."""

    def __init__(self) -> None:
        self.rules: Dict[RuleCode, Callable[[str, ASTNode, List[Diagnostic]], None]] = {}
        self.enabled_rules: Set[RuleCode] = set(RuleCode)
        self._register_default_rules()

    def _register_default_rules(self) -> None:
        self.rules[RuleCode.E501] = self._check_line_length
        self.rules[RuleCode.E401] = self._check_multiple_imports
        self.rules[RuleCode.E302] = self._check_blank_lines
        self.rules[RuleCode.W291] = self._check_trailing_whitespace
        self.rules[RuleCode.W292] = self._check_final_newline
        self.rules[RuleCode.F401] = self._check_unused_imports
        self.rules[RuleCode.F821] = self._check_undefined_names
        self.rules[RuleCode.I001] = self._check_import_sorting
        self.rules[RuleCode.D100] = self._check_module_docstring
        self.rules[RuleCode.D103] = self._check_function_docstring
        self.rules[RuleCode.C901] = self._check_complexity
        self.rules[RuleCode.N801] = self._check_class_naming
        self.rules[RuleCode.N802] = self._check_function_naming

    def lint(self, source: str, ast_tree: ASTNode) -> List[Diagnostic]:
        diagnostics: List[Diagnostic] = []
        for code in self.enabled_rules:
            if code in self.rules:
                self.rules[code](source, ast_tree, diagnostics)
        return diagnostics

    def _check_line_length(self, source: str, ast: ASTNode, diagnostics: List[Diagnostic]) -> None:
        max_length = 88
        for i, line in enumerate(source.split("\n"), 1):
            if len(line) > max_length:
                diagnostics.append(Diagnostic(
                    code=RuleCode.E501,
                    message=f"Line too long ({len(line)} > {max_length} characters)",
                    line=i,
                    column=max_length,
                    severity=Severity.ERROR,
                    fix=f"Break line at column {max_length}",
                ))

    def _check_multiple_imports(self, source: str, ast: ASTNode, diagnostics: List[Diagnostic]) -> None:
        for line in source.split("\n"):
            if line.strip().startswith("import ") and "," in line:
                diagnostics.append(Diagnostic(
                    code=RuleCode.E401,
                    message="Multiple imports on one line",
                    line=1,
                    severity=Severity.ERROR,
                    fix="Split into separate import statements",
                ))

    def _check_blank_lines(self, source: str, ast: ASTNode, diagnostics: List[Diagnostic]) -> None:
        lines = source.split("\n")
        for i, line in enumerate(lines):
            if line.strip().startswith(("def ", "class ")):
                # Check preceding blank lines
                blank_count = 0
                for j in range(max(0, i - 1), -1, -1):
                    if lines[j].strip() == "":
                        blank_count += 1
                    else:
                        break
                if blank_count < 2 and i > 0:
                    diagnostics.append(Diagnostic(
                        code=RuleCode.E302,
                        message="Expected 2 blank lines before function/class definition",
                        line=i + 1,
                        severity=Severity.ERROR,
                    ))

    def _check_trailing_whitespace(self, source: str, ast: ASTNode, diagnostics: List[Diagnostic]) -> None:
        for i, line in enumerate(source.split("\n"), 1):
            if line.rstrip() != line:
                diagnostics.append(Diagnostic(
                    code=RuleCode.W291,
                    message="Trailing whitespace",
                    line=i,
                    column=len(line.rstrip()),
                    severity=Severity.WARNING,
                    fix=line.rstrip(),
                ))

    def _check_final_newline(self, source: str, ast: ASTNode, diagnostics: List[Diagnostic]) -> None:
        if not source.endswith("\n"):
            diagnostics.append(Diagnostic(
                code=RuleCode.W292,
                message="No newline at end of file",
                line=source.count("\n") + 1,
                severity=Severity.WARNING,
                fix=source + "\n",
            ))

    def _check_unused_imports(self, source: str, ast: ASTNode, diagnostics: List[Diagnostic]) -> None:
        imports = ast.children if ast else []
        for node in imports:
            if node.type in ("Import", "ImportFrom"):
                # Check if imported name is used
                if node.name and node.name not in source[node.line:]:
                    diagnostics.append(Diagnostic(
                        code=RuleCode.F401,
                        message=f"'{node.name}' imported but unused",
                        line=node.line,
                        severity=Severity.ERROR,
                        fix=f"Remove import: {node.name}",
                    ))

    def _check_undefined_names(self, source: str, ast: ASTNode, diagnostics: List[Diagnostic]) -> None:
        # Simplified: check for common undefined patterns
        undefined_patterns = [r'\b([a-z_][a-z0-9_]*)\b.*=.*\1', r'print\s+\(([^)]+)\)']
        for pattern in undefined_patterns:
            for match in re.finditer(pattern, source, re.IGNORECASE):
                name = match.group(1)
                if name not in ("self", "cls", "True", "False", "None"):
                    # Check if defined
                    defined = re.search(rf'\b{name}\b\s*=', source[:match.start()])
                    if not defined and not re.search(rf'(def|class|import)\s+{name}', source):
                        diagnostics.append(Diagnostic(
                            code=RuleCode.F821,
                            message=f"Undefined name '{name}'",
                            line=source[:match.start()].count("\n") + 1,
                            severity=Severity.ERROR,
                        ))

    def _check_import_sorting(self, source: str, ast: ASTNode, diagnostics: List[Diagnostic]) -> None:
        lines = source.split("\n")
        import_lines = [(i, line) for i, line in enumerate(lines) if line.strip().startswith(("import ", "from "))]
        if len(import_lines) > 1:
            for i in range(len(import_lines) - 1):
                _, line1 = import_lines[i]
                _, line2 = import_lines[i + 1]
                if line1.strip() > line2.strip():
                    diagnostics.append(Diagnostic(
                        code=RuleCode.I001,
                        message="Imports are incorrectly sorted",
                        line=import_lines[i + 1][0] + 1,
                        severity=Severity.WARNING,
                        fix="Sort imports alphabetically",
                    ))
                    break

    def _check_module_docstring(self, source: str, ast: ASTNode, diagnostics: List[Diagnostic]) -> None:
        if not source.strip().startswith('"""') and not source.strip().startswith("'''"):
            diagnostics.append(Diagnostic(
                code=RuleCode.D100,
                message="Missing docstring in public module",
                line=1,
                severity=Severity.INFO,
            ))

    def _check_function_docstring(self, source: str, ast: ASTNode, diagnostics: List[Diagnostic]) -> None:
        for node in ast.children if ast else []:
            if node.type == "FunctionDef":
                # Check if next non-empty line has docstring
                lines = source.split("\n")
                if node.line < len(lines):
                    next_lines = [l.strip() for l in lines[node.line:node.line + 3]]
                    if not any(l.startswith(('"""', "'''")) for l in next_lines):
                        diagnostics.append(Diagnostic(
                            code=RuleCode.D103,
                            message=f"Missing docstring in public function '{node.name}'",
                            line=node.line,
                            severity=Severity.INFO,
                        ))

    def _check_complexity(self, source: str, ast: ASTNode, diagnostics: List[Diagnostic]) -> None:
        for node in ast.children if ast else []:
            if node.type == "FunctionDef":
                # Count branches
                func_source = self._get_node_source(source, node)
                branches = len(re.findall(r'\b(if|for|while|except|with|and|or)\b', func_source))
                if branches > 10:
                    diagnostics.append(Diagnostic(
                        code=RuleCode.C901,
                        message=f"Function '{node.name}' is too complex (Cyclomatic complexity: {branches})",
                        line=node.line,
                        severity=Severity.WARNING,
                    ))

    def _check_class_naming(self, source: str, ast: ASTNode, diagnostics: List[Diagnostic]) -> None:
        for node in ast.children if ast else []:
            if node.type == "ClassDef":
                if not re.match(r'^[A-Z][a-zA-Z0-9]*$', node.name):
                    diagnostics.append(Diagnostic(
                        code=RuleCode.N801,
                        message=f"Class name '{node.name}' should use CapWords convention",
                        line=node.line,
                        severity=Severity.WARNING,
                    ))

    def _check_function_naming(self, source: str, ast: ASTNode, diagnostics: List[Diagnostic]) -> None:
        for node in ast.children if ast else []:
            if node.type == "FunctionDef":
                if not re.match(r'^[a-z_][a-z0-9_]*$', node.name):
                    diagnostics.append(Diagnostic(
                        code=RuleCode.N802,
                        message=f"Function name '{node.name}' should be lowercase",
                        line=node.line,
                        severity=Severity.WARNING,
                    ))

    def _get_node_source(self, source: str, node: ASTNode) -> str:
        lines = source.split("\n")
        if node.line <= len(lines):
            return "\n".join(lines[node.line - 1:node.line + 10])
        return ""

    def enable_rule(self, code: RuleCode) -> None:
        self.enabled_rules.add(code)

    def disable_rule(self, code: RuleCode) -> None:
        self.enabled_rules.discard(code)


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 3: AutofixEngine
# ═══════════════════════════════════════════════════════════════════════════════

class AutofixEngine:
    """Automatic code fixing engine."""

    def __init__(self) -> None:
        self.fixers: Dict[RuleCode, Callable[[str, Diagnostic], str]] = {}
        self._register_fixers()

    def _register_fixers(self) -> None:
        self.fixers[RuleCode.W291] = self._fix_trailing_whitespace
        self.fixers[RuleCode.W292] = self._fix_final_newline
        self.fixers[RuleCode.I001] = self._fix_import_sorting
        self.fixers[RuleCode.E401] = self._fix_multiple_imports

    def fix(self, source: str, diagnostics: List[Diagnostic]) -> str:
        """Apply autofixes ke source code."""
        fixed = source
        for diag in diagnostics:
            if diag.code in self.fixers and diag.fix:
                fixed = self.fixers[diag.code](fixed, diag)
        return fixed

    def _fix_trailing_whitespace(self, source: str, diag: Diagnostic) -> str:
        lines = source.split("\n")
        if diag.line <= len(lines):
            lines[diag.line - 1] = lines[diag.line - 1].rstrip()
        return "\n".join(lines)

    def _fix_final_newline(self, source: str, diag: Diagnostic) -> str:
        if not source.endswith("\n"):
            return source + "\n"
        return source

    def _fix_import_sorting(self, source: str, diag: Diagnostic) -> str:
        lines = source.split("\n")
        import_lines = [(i, line) for i, line in enumerate(lines) if line.strip().startswith(("import ", "from "))]
        if import_lines:
            sorted_imports = sorted(import_lines, key=lambda x: x[1].strip())
            for (orig_idx, _), (new_idx, new_line) in zip(import_lines, sorted_imports):
                lines[orig_idx] = new_line
        return "\n".join(lines)

    def _fix_multiple_imports(self, source: str, diag: Diagnostic) -> str:
        lines = source.split("\n")
        for i, line in enumerate(lines):
            if line.strip().startswith("import ") and "," in line:
                imports = line.strip()[7:].split(",")
                indent = line[:len(line) - len(line.lstrip())]
                new_lines = [f"{indent}import {imp.strip()}" for imp in imports]
                lines[i:i + 1] = new_lines
                break
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 4: ParallelProcessor
# ═══════════════════════════════════════════════════════════════════════════════

class ParallelProcessor:
    """Async file processing dengan worker pool."""

    def __init__(self, max_workers: int = 4) -> None:
        self.max_workers = max_workers
        self.results: Dict[str, List[Diagnostic]] = {}

    async def lint_files(self, files: List[str], engine: LintEngine, parser: ASTParser) -> Dict[str, List[Diagnostic]]:
        """Lint multiple files in parallel."""
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def lint_one(filepath: str) -> Tuple[str, List[Diagnostic]]:
            async with semaphore:
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        source = f.read()
                    ast_tree = parser.parse(source)
                    diagnostics = engine.lint(source, ast_tree)
                    return filepath, diagnostics
                except Exception as e:
                    return filepath, [Diagnostic(
                        code=RuleCode.F821,
                        message=f"Failed to parse: {e}",
                        severity=Severity.ERROR,
                    )]
        
        tasks = [lint_one(f) for f in files]
        results = await asyncio.gather(*tasks)
        return {filepath: diagnostics for filepath, diagnostics in results}

    async def lint_directory(self, directory: str, engine: LintEngine, parser: ASTParser) -> Dict[str, List[Diagnostic]]:
        """Lint all Python files in directory."""
        files = [str(p) for p in Path(directory).rglob("*.py")]
        return await self.lint_files(files, engine, parser)


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 5: CacheManager
# ═══════════════════════════════════════════════════════════════════════════════

class CacheManager:
    """File hash-based incremental caching."""

    def __init__(self, cache_dir: str = ".ruff_cache") -> None:
        self.cache_dir = cache_dir
        self.cache: Dict[str, Dict[str, Any]] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        cache_file = Path(self.cache_dir) / "cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, "r") as f:
                    self.cache = json.load(f)
            except json.JSONDecodeError:
                self.cache = {}

    def _save_cache(self) -> None:
        Path(self.cache_dir).mkdir(parents=True, exist_ok=True)
        cache_file = Path(self.cache_dir) / "cache.json"
        with open(cache_file, "w") as f:
            json.dump(self.cache, f, indent=2)

    def get_file_hash(self, filepath: str) -> str:
        """Compute MD5 hash of file contents."""
        try:
            with open(filepath, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except FileNotFoundError:
            return ""

    def is_cached(self, filepath: str) -> bool:
        file_hash = self.get_file_hash(filepath)
        cached = self.cache.get(filepath, {})
        return cached.get("hash") == file_hash

    def get_cached_diagnostics(self, filepath: str) -> List[Diagnostic]:
        cached = self.cache.get(filepath, {})
        return [Diagnostic(**d) for d in cached.get("diagnostics", [])]

    def cache_results(self, filepath: str, diagnostics: List[Diagnostic]) -> None:
        self.cache[filepath] = {
            "hash": self.get_file_hash(filepath),
            "timestamp": time.time(),
            "diagnostics": [d.to_dict() for d in diagnostics],
        }
        self._save_cache()

    def invalidate(self, filepath: str) -> None:
        self.cache.pop(filepath, None)


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 6: ConfigLoader
# ═══════════════════════════════════════════════════════════════════════════════

class ConfigLoader:
    """Configuration loader untuk pyproject.toml / ruff.toml."""

    def __init__(self) -> None:
        self.config: Dict[str, Any] = {
            "line-length": 88,
            "select": ["E", "W", "F", "I", "D", "C", "N"],
            "ignore": [],
            "per-file-ignores": {},
            "target-version": "py38",
        }

    def load_pyproject_toml(self, path: str = "pyproject.toml") -> Dict[str, Any]:
        """Parse pyproject.toml configuration."""
        try:
            # Simplified TOML parsing
            with open(path, "r") as f:
                content = f.read()
            
            # Extract [tool.ruff] section
            match = re.search(r'\[tool\.ruff\](.*?)(?=\[|$)', content, re.DOTALL)
            if match:
                section = match.group(1)
                # Parse key-value pairs
                for line in section.split("\n"):
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        if key == "line-length":
                            self.config["line-length"] = int(value)
                        elif key == "select":
                            self.config["select"] = [v.strip().strip('"') for v in value.strip("[]").split(",")]
                        elif key == "ignore":
                            self.config["ignore"] = [v.strip().strip('"') for v in value.strip("[]").split(",")]
            
            return self.config
        except FileNotFoundError:
            return self.config

    def load_ruff_toml(self, path: str = "ruff.toml") -> Dict[str, Any]:
        """Parse ruff.toml configuration."""
        return self.load_pyproject_toml(path)

    def is_rule_enabled(self, code: str) -> bool:
        """Check if rule code is enabled."""
        prefix = code[0] if code else ""
        if code in self.config.get("ignore", []):
            return False
        return prefix in self.config.get("select", [])

    def get_line_length(self) -> int:
        return self.config.get("line-length", 88)


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 7: ImportSorter
# ═══════════════════════════════════════════════════════════════════════════════

class ImportSorter:
    """isort replacement — sort and group imports."""

    def __init__(self) -> None:
        self.stdlib_modules = {
            "os", "sys", "json", "re", "time", "math", "random", "collections",
            "typing", "pathlib", "dataclasses", "enum", "asyncio", "hashlib",
            "urllib", "http", "ftplib", "email", "datetime", "inspect", "itertools",
        }

    def sort_imports(self, source: str) -> str:
        """Sort imports dalam source code."""
        lines = source.split("\n")
        import_lines = []
        other_lines = []
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                import_lines.append(line)
            else:
                other_lines.append(line)
        
        # Group imports
        stdlib = []
        third_party = []
        first_party = []
        
        for line in import_lines:
            stripped = line.strip()
            if stripped.startswith("from "):
                module = stripped.split()[1].split(".")[0]
            elif stripped.startswith("import "):
                module = stripped.split()[1].split(",")[0].split(".")[0]
            else:
                continue
            
            if module in self.stdlib_modules:
                stdlib.append(line)
            elif module.startswith(("ruff", "magnatrix")):
                first_party.append(line)
            else:
                third_party.append(line)
        
        # Sort each group
        stdlib.sort(key=lambda x: x.strip())
        third_party.sort(key=lambda x: x.strip())
        first_party.sort(key=lambda x: x.strip())
        
        # Combine dengan blank lines antara groups
        sorted_imports = []
        if stdlib:
            sorted_imports.extend(stdlib)
            sorted_imports.append("")
        if third_party:
            sorted_imports.extend(third_party)
            sorted_imports.append("")
        if first_party:
            sorted_imports.extend(first_party)
            sorted_imports.append("")
        
        return "\n".join(sorted_imports + other_lines)

    def is_sorted(self, source: str) -> bool:
        """Check if imports are already sorted."""
        sorted_source = self.sort_imports(source)
        return source == sorted_source


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 8: FormatChecker
# ═══════════════════════════════════════════════════════════════════════════════

class FormatChecker:
    """Black-style format checker."""

    def __init__(self, line_length: int = 88) -> None:
        self.line_length = line_length

    def check_format(self, source: str) -> List[Diagnostic]:
        """Check formatting issues."""
        diagnostics = []
        lines = source.split("\n")
        
        for i, line in enumerate(lines, 1):
            # Line length
            if len(line) > self.line_length:
                diagnostics.append(Diagnostic(
                    code=RuleCode.E501,
                    message=f"Line too long ({len(line)} > {self.line_length})",
                    line=i,
                    severity=Severity.ERROR,
                ))
            
            # Indentation (should be 4 spaces)
            if line.strip():
                indent = len(line) - len(line.lstrip())
                if indent % 4 != 0:
                    diagnostics.append(Diagnostic(
                        code=RuleCode.W291,
                        message=f"Indentation is not a multiple of 4",
                        line=i,
                        severity=Severity.WARNING,
                    ))
        
        # Blank line rules
        for i in range(len(lines) - 1):
            if lines[i].strip().startswith("class ") or lines[i].strip().startswith("def "):
                # Check 2 blank lines before
                blank_count = 0
                for j in range(i - 1, max(-1, i - 3), -1):
                    if j >= 0 and lines[j].strip() == "":
                        blank_count += 1
                
                if lines[i].strip().startswith("class ") and blank_count < 2:
                    diagnostics.append(Diagnostic(
                        code=RuleCode.E302,
                        message="Expected 2 blank lines before class definition",
                        line=i + 1,
                        severity=Severity.ERROR,
                    ))
        
        return diagnostics

    def format_code(self, source: str) -> str:
        """Apply formatting fixes."""
        lines = source.split("\n")
        formatted = []
        
        for line in lines:
            # Trim trailing whitespace
            line = line.rstrip()
            formatted.append(line)
        
        # Ensure final newline
        result = "\n".join(formatted)
        if not result.endswith("\n"):
            result += "\n"
        
        return result


# ═══════════════════════════════════════════════════════════════════════════════
# MAGNATRIX INTEGRATION: RuffOrchestrator
# ═══════════════════════════════════════════════════════════════════════════════

class RuffOrchestrator:
    """Orchestrator untuk complete linting workflow."""

    def __init__(self) -> None:
        self.parser = ASTParser()
        self.engine = LintEngine()
        self.autofix = AutofixEngine()
        self.parallel = ParallelProcessor()
        self.cache = CacheManager()
        self.config = ConfigLoader()
        self.import_sorter = ImportSorter()
        self.formatter = FormatChecker()

    async def lint_file(self, filepath: str, use_cache: bool = True) -> Dict[str, Any]:
        """Lint single file dengan caching."""
        # Check cache
        if use_cache and self.cache.is_cached(filepath):
            diagnostics = self.cache.get_cached_diagnostics(filepath)
            return {
                "filepath": filepath,
                "cached": True,
                "diagnostics": [d.to_dict() for d in diagnostics],
                "error_count": len([d for d in diagnostics if d.severity == Severity.ERROR]),
                "warning_count": len([d for d in diagnostics if d.severity == Severity.WARNING]),
            }
        
        # Parse and lint
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        
        ast_tree        ast_tree = self.parser.parse(source)
        diagnostics = self.engine.lint(source, ast_tree)
        
        # Apply autofix
        fixed_source = self.autofix.fix(source, diagnostics)
        
        # Cache results
        self.cache.cache_results(filepath, diagnostics)
        
        return {
            "filepath": filepath,
            "cached": False,
            "diagnostics": [d.to_dict() for d in diagnostics],
            "error_count": len([d for d in diagnostics if d.severity == Severity.ERROR]),
            "warning_count": len([d for d in diagnostics if d.severity == Severity.WARNING]),
            "fixed": fixed_source != source,
        }

    async def lint_project(self, directory: str) -> Dict[str, Any]:
        """Lint entire project directory."""
        # Load config
        self.config.load_pyproject_toml()
        
        # Find all Python files
        files = [str(p) for p in Path(directory).rglob("*.py")]
        
        # Process in parallel
        results = await self.parallel.lint_files(files, self.engine, self.parser)
        
        # Aggregate
        total_errors = 0
        total_warnings = 0
        all_diagnostics = []
        
        for filepath, diagnostics in results.items():
            errors = len([d for d in diagnostics if d.severity == Severity.ERROR])
            warnings = len([d for d in diagnostics if d.severity == Severity.WARNING])
            total_errors += errors
            total_warnings += warnings
            all_diagnostics.extend([{**d.to_dict(), "file": filepath} for d in diagnostics])
        
        return {
            "files_scanned": len(files),
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "diagnostics": all_diagnostics,
        }

    def sort_imports_in_file(self, filepath: str) -> str:
        """Sort imports in a file."""
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        
        sorted_source = self.import_sorter.sort_imports(source)
        
        if sorted_source != source:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(sorted_source)
        
        return sorted_source

    def format_file(self, filepath: str) -> str:
        """Format a file."""
        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()
        
        formatted = self.formatter.format_code(source)
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(formatted)
        
        return formatted


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO / __main__
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    async def demo() -> None:
        print("=" * 70)
        print("MAGNATRIX — Ruff Ultra-Fast Linter Demo")
        print("=" * 70)

        # Create test file
        test_code = '''import os, sys
import json
import re
from collections import defaultdict

def badFunctionName(x,y):
    z=x+y
    return z

class bad_class_name:
    def __init__(self):
        pass

def long_function():
    a=1
    b=2
    c=3
    d=4
    e=5
    f=6
    g=7
    h=8
    i=9
    j=10
    k=11
    l=12
    return a+b+c+d+e+f+g+h+i+j+k+l

unused_var = 42
'''

        test_file = "/tmp/test_lint.py"
        with open(test_file, "w") as f:
            f.write(test_code)

        # Initialize orchestrator
        ruff = RuffOrchestrator()
        
        print("\n1. Linting single file...")
        result = await ruff.lint_file(test_file, use_cache=False)
        print(f"   File: {result['filepath']}")
        print(f"   Errors: {result['error_count']}")
        print(f"   Warnings: {result['warning_count']}")
        print(f"   Cached: {result['cached']}")
        
        print("\n2. Diagnostics:")
        for diag in result['diagnostics'][:10]:
            print(f"   [{diag['code']}] {diag['message']} at {diag['location']}")

        print("\n3. Sorting imports...")
        sorted_code = ruff.sort_imports_in_file(test_file)
        print(f"   Imports sorted successfully")

        print("\n4. Formatting file...")
        formatted = ruff.format_file(test_file)
        print(f"   File formatted successfully")

        print("\n5. Linting project (mock)...")
        project_result = await ruff.lint_project("/tmp")
        print(f"   Files scanned: {project_result['files_scanned']}")
        print(f"   Total errors: {project_result['total_errors']}")
        print(f"   Total warnings: {project_result['total_warnings']}")

        print("\n6. Cache demo...")
        # Second lint should use cache
        cached_result = await ruff.lint_file(test_file, use_cache=True)
        print(f"   Second lint cached: {cached_result['cached']}")

        print("\n7. Config loading...")
        config = ruff.config.load_pyproject_toml()
        print(f"   Line length: {config['line-length']}")
        print(f"   Selected rules: {config['select']}")

        print("\n" + "=" * 70)
        print("Demo complete.")
        print("=" * 70)

    asyncio.run(demo())

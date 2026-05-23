"""
AutoDev Native — Native Python Reimplementation of phodal/auto-dev
AMATI-PELAJARI-TIRU: Studied core patterns from AutoDev 3.0 Xiuper (Kotlin Multiplatform)
and distilled into idiomatic, pure-Python architecture.

Architecture:
    DevContext     → IDE context extraction (file tree, AST stubs, cursor, imports)
    IntentParser   → NL → dev action mapping (regex + heuristic classification)
    CodeGenerator  → AI-powered synthesis (prompt builder, templates, sanitizer)
    RefactorEngine → AST-based refactoring with safety checks
    TestGenerator  → Automated test stub generation
    DocGenerator   → Docstring / README / API doc generation
    ReviewEngine   → Static analysis, complexity, security, performance
    DevAgent       → Orchestrator state machine
    PromptLibrary  → Curated prompt template registry
    AutoDevKernel  → MAGNATRIX bridge (Layer 12 / 6 / 10 hooks)

Author: Android Claw (Kimi Claw)
Date: 2026-05-23
"""

from __future__ import annotations

import ast
import enum
import json
import os
import re
import textwrap
import tokenize
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple, Union

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — DevContext: IDE Context Extraction
# ═══════════════════════════════════════════════════════════════════════════════


class Language(enum.Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    GO = "go"
    RUST = "rust"
    C = "c"
    CPP = "cpp"
    JAVA = "java"
    KOTLIN = "kotlin"
    RUBY = "ruby"
    UNKNOWN = "unknown"


@dataclass
class CursorPosition:
    """Cursor location inside a source file."""

    line: int
    column: int
    offset: int = 0

    def __repr__(self) -> str:
        return f"CursorPosition(line={self.line}, col={self.column})"


@dataclass
class CodeBlock:
    """A selected or inferred code block with surrounding metadata."""

    file_path: str
    start_line: int
    end_line: int
    content: str
    language: Language
    parent_symbol: Optional[str] = None  # function/class name
    imports: List[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return (
            f"CodeBlock({self.file_path}:{self.start_line}-{self.end_line}, "
            f"lang={self.language.value}, parent={self.parent_symbol})"
        )


@dataclass
class FileTreeNode:
    """Node in a project file tree."""

    path: str
    is_dir: bool
    children: List["FileTreeNode"] = field(default_factory=list)
    language: Optional[Language] = None

    def __repr__(self) -> str:
        kind = "dir" if self.is_dir else "file"
        return f"FileTreeNode({self.path}, {kind})"


class ASTStubParser:
    """
    Simulated AST parser for multiple languages.
    For Python we use the real `ast` module; for others we produce
    lightweight structural stubs so downstream engines can reason
    about symbols, scopes, and imports without a full compiler.
    """

    EXTENSION_MAP: Dict[str, Language] = {
        ".py": Language.PYTHON,
        ".js": Language.JAVASCRIPT,
        ".ts": Language.TYPESCRIPT,
        ".go": Language.GO,
        ".rs": Language.RUST,
        ".c": Language.C,
        ".cpp": Language.CPP,
        ".h": Language.C,
        ".hpp": Language.CPP,
        ".java": Language.JAVA,
        ".kt": Language.KOTLIN,
        ".rb": Language.RUBY,
    }

    def detect_language(self, file_path: str) -> Language:
        ext = Path(file_path).suffix.lower()
        return self.EXTENSION_MAP.get(ext, Language.UNKNOWN)

    def parse(self, file_path: str, content: str) -> Dict[str, Any]:
        """Return a structural dict: {imports, classes, functions, globals}."""
        lang = self.detect_language(file_path)
        if lang == Language.PYTHON:
            return self._parse_python(content)
        return self._parse_stub(lang, content)

    def _parse_python(self, content: str) -> Dict[str, Any]:
        tree: Dict[str, Any] = {"imports": [], "classes": [], "functions": [], "globals": []}
        try:
            mod = ast.parse(content)
        except SyntaxError:
            return tree
        for node in ast.walk(mod):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                tree["imports"].append(ast.unparse(node) if hasattr(ast, "unparse") else "<import>")
            elif isinstance(node, ast.ClassDef):
                methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                tree["classes"].append({"name": node.name, "methods": methods, "line": node.lineno})
            elif isinstance(node, ast.FunctionDef):
                args = [a.arg for a in node.args.args]
                tree["functions"].append({"name": node.name, "args": args, "line": node.lineno})
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        tree["globals"].append(target.id)
        return tree

    def _parse_stub(self, lang: Language, content: str) -> Dict[str, Any]:
        """Heuristic stub parser for non-Python languages using regex."""
        tree: Dict[str, Any] = {"imports": [], "classes": [], "functions": [], "globals": []}
        lines = content.splitlines()
        # Imports / includes / uses
        import_patterns = {
            Language.JAVASCRIPT: r"import\s+.*?from\s+['\"](.+?)['\"]",
            Language.TYPESCRIPT: r"import\s+.*?from\s+['\"](.+?)['\"]",
            Language.GO: r'import\s+["\'](.+?)["\']',
            Language.RUST: r'use\s+(.+?);',
            Language.JAVA: r'import\s+(.+?);',
            Language.KOTLIN: r'import\s+(.+)',
            Language.C: r'#include\s+[\<"](.+?)[\>"]',
            Language.CPP: r'#include\s+[\<"](.+?)[\>"]',
            Language.RUBY: r'require\s+["\'](.+?)["\']',
        }
        pat = import_patterns.get(lang)
        if pat:
            for line in lines:
                m = re.search(pat, line)
                if m:
                    tree["imports"].append(m.group(1))
        # Functions
        func_patterns = {
            Language.JAVASCRIPT: r"(?:async\s+)?function\s+(\w+)\s*\((.*?)\)",
            Language.TYPESCRIPT: r"(?:async\s+)?function\s+(\w+)\s*\((.*?)\)",
            Language.GO: r"func\s+(?:\([^)]+\)\s+)?(\w+)\s*\((.*?)\)",
            Language.RUST: r"fn\s+(\w+)\s*\((.*?)\)",
            Language.JAVA: r"(?:public|private|protected)?\s*(?:static\s+)?[\w\<\>\[\]]+\s+(\w+)\s*\((.*?)\)",
            Language.KOTLIN: r"fun\s+(\w+)\s*\((.*?)\)",
            Language.C: r"[\w\*\s]+\s+(\w+)\s*\((.*?)\)\s*\{",
            Language.CPP: r"[\w\*\s:]+\s+(\w+)\s*\((.*?)\)\s*(?:const)?\s*\{",
            Language.RUBY: r"def\s+(\w+)\s*(?:\((.*?)\))?",
        }
        fp = func_patterns.get(lang)
        if fp:
            for i, line in enumerate(lines, 1):
                for m in re.finditer(fp, line):
                    tree["functions"].append(
                        {"name": m.group(1), "args": m.group(2).split(",") if m.group(2) else [], "line": i}
                    )
        # Classes
        class_patterns = {
            Language.JAVASCRIPT: r"class\s+(\w+)",
            Language.TYPESCRIPT: r"class\s+(\w+)",
            Language.JAVA: r"class\s+(\w+)",
            Language.KOTLIN: r"class\s+(\w+)",
            Language.RUST: r"struct\s+(\w+)",
            Language.CPP: r"class\s+(\w+)",
            Language.RUBY: r"class\s+(\w+)",
        }
        cp = class_patterns.get(lang)
        if cp:
            for i, line in enumerate(lines, 1):
                m = re.search(cp, line)
                if m:
                    tree["classes"].append({"name": m.group(1), "line": i})
        return tree


class ContextExtractor:
    """
    Extracts IDE-like context from a project directory.
    Simulates: file tree scanner, AST parsing, cursor position,
    selected code block, surrounding function/class context,
    import resolution.
    """

    def __init__(self, project_root: str) -> None:
        self.root = Path(project_root).resolve()
        self.ast_parser = ASTStubParser()

    def scan_file_tree(self, max_depth: int = 4) -> FileTreeNode:
        """Build a hierarchical file tree up to max_depth."""

        def walk(path: Path, depth: int) -> FileTreeNode:
            is_dir = path.is_dir()
            node = FileTreeNode(
                path=str(path.relative_to(self.root)),
                is_dir=is_dir,
                language=None if is_dir else self.ast_parser.detect_language(str(path)),
            )
            if is_dir and depth < max_depth:
                try:
                    for child in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                        if child.name.startswith(".") or child.name in {"node_modules", "__pycache__", "target", "build", ".git"}:
                            continue
                        node.children.append(walk(child, depth + 1))
                except PermissionError:
                    pass
            return node

        return walk(self.root, 0)

    def extract_file_context(self, file_path: str, cursor: Optional[CursorPosition] = None) -> Dict[str, Any]:
        """Full context for a single file: AST, cursor block, imports, surrounding symbol."""
        abs_path = self.root / file_path
        if not abs_path.exists():
            return {"error": "file not found"}
        content = abs_path.read_text(encoding="utf-8", errors="ignore")
        ast_data = self.ast_parser.parse(file_path, content)
        block = self._extract_block_at_cursor(content, cursor, file_path) if cursor else None
        surrounding = self._find_surrounding_symbol(ast_data, cursor) if cursor else None
        return {
            "file_path": file_path,
            "language": self.ast_parser.detect_language(file_path).value,
            "ast": ast_data,
            "cursor": cursor,
            "selected_block": block,
            "surrounding_symbol": surrounding,
            "line_count": len(content.splitlines()),
        }

    def _extract_block_at_cursor(self, content: str, cursor: CursorPosition, file_path: str) -> Optional[CodeBlock]:
        lines = content.splitlines()
        if cursor.line < 1 or cursor.line > len(lines):
            return None
        # Expand to surrounding blank lines or indentation boundaries
        start = cursor.line - 1
        end = cursor.line - 1
        while start > 0 and lines[start].strip():
            start -= 1
        while end < len(lines) - 1 and lines[end].strip():
            end += 1
        block_content = "\n".join(lines[start : end + 1])
        lang = self.ast_parser.detect_language(file_path)
        return CodeBlock(
            file_path=file_path,
            start_line=start + 1,
            end_line=end + 1,
            content=block_content,
            language=lang,
        )

    def _find_surrounding_symbol(self, ast_data: Dict[str, Any], cursor: CursorPosition) -> Optional[str]:
        for fn in ast_data.get("functions", []):
            if fn.get("line", 0) <= cursor.line:
                return f"function:{fn['name']}"
        for cls in ast_data.get("classes", []):
            if cls.get("line", 0) <= cursor.line:
                return f"class:{cls['name']}"
        return None

    def resolve_import(self, file_path: str, symbol: str) -> Optional[str]:
        """Simulated import resolution: guess which file exports the symbol."""
        # Naive heuristic: scan project for symbol definition
        for py_file in self.root.rglob("*.py"):
            try:
                text = py_file.read_text(encoding="utf-8", errors="ignore")
                if f"def {symbol}(" in text or f"class {symbol}:" in text or f"class {symbol}(" in text:
                    return str(py_file.relative_to(self.root))
            except Exception:
                continue
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — IntentParser: Natural Language → Dev Action
# ═══════════════════════════════════════════════════════════════════════════════


class DevAction(enum.Enum):
    CREATE_FUNCTION = "create_function"
    REFACTOR = "refactor"
    ADD_TESTS = "add_tests"
    EXPLAIN_CODE = "explain_code"
    FIX_BUG = "fix_bug"
    GENERATE_DOCS = "generate_docs"
    GENERATE_CODE = "generate_code"
    UNKNOWN = "unknown"


@dataclass
class Intent:
    """Parsed developer intent with parameters."""

    action: DevAction
    raw_query: str
    target_file: Optional[str] = None
    target_symbol: Optional[str] = None
    constraints: List[str] = field(default_factory=list)
    language: Optional[Language] = None
    confidence: float = 0.0

    def __repr__(self) -> str:
        return (
            f"Intent(action={self.action.value}, file={self.target_file}, "
            f"symbol={self.target_symbol}, confidence={self.confidence:.2f})"
        )


class IntentParser:
    """
    Heuristic + regex intent parser.
    Maps natural language queries to structured DevAction with parameters.
    """

    ACTION_PATTERNS: List[Tuple[DevAction, List[str]]] = [
        (DevAction.CREATE_FUNCTION, ["buat fungsi", "create function", "tulis fungsi", "generate function", "add function"]),
        (DevAction.REFACTOR, ["refactor", "perbaiki struktur", "restructure", "clean up", "simplify"]),
        (DevAction.ADD_TESTS, ["buat test", "add test", "generate test", "tulis unit test", "test untuk"]),
        (DevAction.EXPLAIN_CODE, ["jelaskan", "explain", "what does this do", "apa fungsi", "bagaimana cara kerja"]),
        (DevAction.FIX_BUG, ["fix", "perbaiki bug", "resolve", "repair", "debug", "correct"]),
        (DevAction.GENERATE_DOCS, ["buat dokumentasi", "generate docs", "tulis docstring", "add documentation", "document"]),
        (DevAction.GENERATE_CODE, ["generate code", "buat kode", "tulis program", "scaffold", "generate crud", "generate api"]),
    ]

    FILE_PATTERN = re.compile(r"(?:file|di|in)\s+[`\"']?([\w/\-.]+)[`\"']?", re.IGNORECASE)
    SYMBOL_PATTERN = re.compile(r"(?:fungsi|function|class|method|symbol)\s+[`\"']?(\w+)[`\"']?", re.IGNORECASE)
    LANG_PATTERN = re.compile(r"(?:dalam|in|using|dengan)\s+(python|javascript|typescript|go|rust|java|kotlin|ruby|c\+\+|c)", re.IGNORECASE)

    def parse(self, query: str) -> Intent:
        query_lower = query.lower()
        best_action = DevAction.UNKNOWN
        best_score = 0.0
        for action, keywords in self.ACTION_PATTERNS:
            for kw in keywords:
                if kw in query_lower:
                    score = len(kw) / len(query_lower)  # crude relevance
                    if score > best_score:
                        best_score = score
                        best_action = action
        # Parameter extraction
        target_file = None
        m = self.FILE_PATTERN.search(query)
        if m:
            target_file = m.group(1)
        target_symbol = None
        m = self.SYMBOL_PATTERN.search(query)
        if m:
            target_symbol = m.group(1)
        language = None
        m = self.LANG_PATTERN.search(query)
        if m:
            lang_str = m.group(1).lower()
            lang_map = {
                "python": Language.PYTHON,
                "javascript": Language.JAVASCRIPT,
                "typescript": Language.TYPESCRIPT,
                "go": Language.GO,
                "rust": Language.RUST,
                "java": Language.JAVA,
                "kotlin": Language.KOTLIN,
                "ruby": Language.RUBY,
                "c++": Language.CPP,
                "c": Language.C,
            }
            language = lang_map.get(lang_str)
        # Constraints: quoted strings or after "dengan" / "with"
        constraints: List[str] = []
        for quoted in re.findall(r'["\'](.+?)["\']', query):
            constraints.append(quoted)
        confidence = min(1.0, best_score * 5.0) if best_action != DevAction.UNKNOWN else 0.1
        return Intent(
            action=best_action,
            raw_query=query,
            target_file=target_file,
            target_symbol=target_symbol,
            constraints=constraints,
            language=language,
            confidence=confidence,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — CodeGenerator: AI-Powered Code Synthesis
# ═══════════════════════════════════════════════════════════════════════════════


class GenerationStrategy(enum.Enum):
    WHOLE_FILE = "whole_file"
    PATCH = "patch"
    INLINE = "inline"


@dataclass
class GenerationResult:
    """Output of code generation."""

    code: str
    strategy: GenerationStrategy
    language: Language
    explanation: str = ""
    warnings: List[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"GenerationResult(strategy={self.strategy.value}, lang={self.language.value}, lines={len(self.code.splitlines())})"


class PromptBuilder:
    """Assembles structured prompts from context + intent."""

    def build(self, context: Dict[str, Any], intent: Intent, template: Optional[str] = None) -> str:
        parts: List[str] = []
        parts.append("# Task")
        parts.append(intent.raw_query)
        parts.append("")
        parts.append("# Context")
        if intent.target_file:
            parts.append(f"Target file: {intent.target_file}")
        if intent.target_symbol:
            parts.append(f"Target symbol: {intent.target_symbol}")
        if intent.language:
            parts.append(f"Language: {intent.language.value}")
        if context.get("surrounding_symbol"):
            parts.append(f"Surrounding symbol: {context['surrounding_symbol']}")
        if context.get("ast"):
            ast = context["ast"]
            parts.append(f"Imports: {', '.join(ast.get('imports', [])[:10])}")
            parts.append(f"Classes: {', '.join(c['name'] for c in ast.get('classes', [])[:5])}")
            parts.append(f"Functions: {', '.join(f['name'] for f in ast.get('functions', [])[:5])}")
        parts.append("")
        parts.append("# Constraints")
        for c in intent.constraints:
            parts.append(f"- {c}")
        parts.append("")
        if template:
            parts.append("# Template")
            parts.append(template)
        return "\n".join(parts)


class TemplateEngine:
    """Code skeletons for common patterns."""

    TEMPLATES: Dict[str, str] = {
        "crud_api_python": textwrap.dedent("""
            from fastapi import FastAPI, HTTPException
            from pydantic import BaseModel

            app = FastAPI()

            class {{Model}}Create(BaseModel):
                # fields
                pass

            class {{Model}}Response(BaseModel):
                id: int
                # fields
                pass

            @app.post("/{{resource}}", response_model={{Model}}Response)
            async def create_{{resource}}(item: {{Model}}Create):
                # implementation
                pass

            @app.get("/{{resource}}/{item_id}", response_model={{Model}}Response)
            async def get_{{resource}}(item_id: int):
                # implementation
                pass

            @app.put("/{{resource}}/{item_id}", response_model={{Model}}Response)
            async def update_{{resource}}(item_id: int, item: {{Model}}Create):
                # implementation
                pass

            @app.delete("/{{resource}}/{item_id}")
            async def delete_{{resource}}(item_id: int):
                # implementation
                pass
        """).strip(),
        "class_python": textwrap.dedent("""
            class {{ClassName}}:
                def __init__(self{{args}}):
                    {{init_body}}

                {{methods}}
        """).strip(),
        "function_python": textwrap.dedent("""
            def {{name}}({{args}}) -> {{return_type}}:
                {{docstring}}
                {{body}}
        """).strip(),
        "react_component": textwrap.dedent("""
            import React from 'react';

            export const {{ComponentName}} = ({{props}}) => {
                {{hooks}}
                return (
                    {{jsx}}
                );
            };
        """).strip(),
        "go_handler": textwrap.dedent("""
            package main

            import "net/http"

            func {{Name}}Handler(w http.ResponseWriter, r *http.Request) {
                {{body}}
            }
        """).strip(),
    }

    def render(self, template_name: str, variables: Dict[str, str]) -> str:
        tpl = self.TEMPLATES.get(template_name, "")
        for key, val in variables.items():
            tpl = tpl.replace(f"{{{{{key}}}}}", val)
        return tpl

    def list_templates(self) -> List[str]:
        return list(self.TEMPLATES.keys())


class OutputSanitizer:
    """Clean generated code: strip markdown fences, validate syntax."""

    def sanitize(self, raw: str, language: Language) -> Tuple[str, List[str]]:
        warnings: List[str] = []
        # Strip markdown code fences
        cleaned = re.sub(r"^```\w*\n", "", raw)
        cleaned = re.sub(r"\n```\s*$", "", cleaned)
        cleaned = cleaned.strip()
        # Basic syntax validation for Python
        if language == Language.PYTHON:
            try:
                ast.parse(cleaned)
            except SyntaxError as e:
                warnings.append(f"Python syntax error: {e}")
        return cleaned, warnings


class CodeGenerator:
    """
    AI-powered code synthesis engine.
    Prompt builder + template engine + generation strategy + sanitizer.
    """

    def __init__(self) -> None:
        self.prompt_builder = PromptBuilder()
        self.template_engine = TemplateEngine()
        self.sanitizer = OutputSanitizer()

    def generate(
        self,
        context: Dict[str, Any],
        intent: Intent,
        strategy: GenerationStrategy = GenerationStrategy.WHOLE_FILE,
        template_name: Optional[str] = None,
    ) -> GenerationResult:
        """
        Simulate AI generation.
        In a real system this would call an LLM API; here we use templates + heuristics.
        """
        language = intent.language or Language.PYTHON
        template = None
        if template_name:
            template = self.template_engine.render(template_name, {
                "Model": intent.target_symbol or "Item",
                "resource": (intent.target_symbol or "item").lower(),
                "ClassName": intent.target_symbol or "MyClass",
                "ComponentName": intent.target_symbol or "MyComponent",
                "Name": intent.target_symbol or "My",
            })
        prompt = self.prompt_builder.build(context, intent, template)
        # Simulated "AI" output
        simulated_code = self._simulate_llm_output(prompt, language, strategy, template)
        cleaned, warnings = self.sanitizer.sanitize(simulated_code, language)
        return GenerationResult(
            code=cleaned,
            strategy=strategy,
            language=language,
            explanation=f"Generated via {strategy.value} using template {template_name}",
            warnings=warnings,
        )

    def _simulate_llm_output(
        self, prompt: str, language: Language, strategy: GenerationStrategy, template: Optional[str]
    ) -> str:
        # Return template if available, else a generic stub
        if template:
            return template
        if language == Language.PYTHON:
            return textwrap.dedent(f"""
                # Auto-generated by AutoDev
                def generated_function():
                    \"\"\"Placeholder generated function.\"\"\"
                    pass
            """).strip()
        if language == Language.JAVASCRIPT:
            return "// Auto-generated\nfunction generatedFunction() {\n  // TODO\n}"
        if language == Language.GO:
            return "package main\n\nfunc Generated() {\n    // TODO\n}"
        return f"// Auto-generated {language.value} code\n"


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — RefactorEngine: Automated Refactoring
# ═══════════════════════════════════════════════════════════════════════════════


class RefactorOperation(enum.Enum):
    RENAME_SYMBOL = "rename_symbol"
    EXTRACT_METHOD = "extract_method"
    INLINE_VARIABLE = "inline_variable"
    MOVE_CLASS = "move_class"
    LOOP_TO_COMPREHENSION = "loop_to_comprehension"
    ADD_TYPE_ANNOTATIONS = "add_type_annotations"


@dataclass
class RefactorResult:
    original: str
    refactored: str
    operation: RefactorOperation
    safety_checks: List[str] = field(default_factory=list)
    applied: bool = False

    def __repr__(self) -> str:
        return f"RefactorResult(op={self.operation.value}, applied={self.applied})"


class RefactorEngine:
    """
    AST-based refactoring with simulated safety checks.
    No real IDE SDK — uses Python ast + regex heuristics.
    """

    def refactor(
        self, code: str, operation: RefactorOperation, params: Dict[str, str]
    ) -> RefactorResult:
        safety: List[str] = []
        result = code
        applied = False
        if operation == RefactorOperation.RENAME_SYMBOL:
            old = params.get("old_name", "")
            new = params.get("new_name", "")
            if old and new:
                # Naive safety: check if new name already exists
                if re.search(rf"\b{re.escape(new)}\b", code):
                    safety.append(f"WARNING: '{new}' already exists in scope")
                result = re.sub(rf"\b{re.escape(old)}\b", new, code)
                applied = True
                safety.append(f"Renamed {old} -> {new}")
        elif operation == RefactorOperation.EXTRACT_METHOD:
            block = params.get("block", "")
            name = params.get("method_name", "extracted")
            if block:
                indent = len(block) - len(block.lstrip())
                method_def = f"{' ' * indent}def {name}():\n{textwrap.indent(block.strip(), ' ' * (indent + 4))}\n"
                result = code.replace(block, method_def + f"{' ' * indent}{name}()\n")
                applied = True
                safety.append(f"Extracted block into {name}")
        elif operation == RefactorOperation.INLINE_VARIABLE:
            var = params.get("variable", "")
            val = params.get("value", "")
            if var and val:
                result = re.sub(rf"\b{re.escape(var)}\b", val, code)
                applied = True
                safety.append(f"Inlined {var} = {val}")
        elif operation == RefactorOperation.LOOP_TO_COMPREHENSION:
            result = self._try_loop_to_comprehension(code)
            applied = result != code
            if applied:
                safety.append("Converted loop to comprehension")
            else:
                safety.append("No convertible loop found")
        elif operation == RefactorOperation.ADD_TYPE_ANNOTATIONS:
            result = self._add_type_annotations(code)
            applied = result != code
            safety.append("Added type annotations where inferable")
        return RefactorResult(
            original=code,
            refactored=result,
            operation=operation,
            safety_checks=safety,
            applied=applied,
        )

    def _try_loop_to_comprehension(self, code: str) -> str:
        # Very naive: for x in y: result.append(z) → [z for x in y]
        pattern = re.compile(
            r"^(\s*)(\w+)\s*=\s*\[\]\s*$\n"
            r"^(\s*)for\s+(\w+)\s+in\s+(.+?):\s*$\n"
            r"^(\s*)\2\.append\((.+?)\)\s*$",
            re.MULTILINE,
        )

        def repl(m: Any) -> str:
            indent = m.group(1)
            var = m.group(4)
            iterable = m.group(5)
            expr = m.group(7)
            return f"{indent}{m.group(2)} = [{expr} for {var} in {iterable}]"

        return pattern.sub(repl, code)

    def _add_type_annotations(self, code: str) -> str:
        # Naive: add -> Any to functions missing return annotation
        lines = code.splitlines()
        out: List[str] = []
        for line in lines:
            if re.match(r"^\s*def\s+\w+\([^)]*\):\s*$", line) and "->" not in line:
                line = line.rstrip(":") + " -> Any:"
            out.append(line)
        return "\n".join(out)


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — TestGenerator: Automated Test Generation
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class TestCase:
    name: str
    input_data: Optional[str] = None
    expected: Optional[str] = None
    description: str = ""

    def __repr__(self) -> str:
        return f"TestCase({self.name})"


@dataclass
class TestPlan:
    target_file: str
    target_symbol: Optional[str]
    language: Language
    cases: List[TestCase] = field(default_factory=list)
    mocks_needed: List[str] = field(default_factory=list)
    coverage_target: float = 0.8

    def __repr__(self) -> str:
        return f"TestPlan({self.target_file}, {len(self.cases)} cases)"


class TestGenerator:
    """
    Generates unit test stubs from code context.
    Supports pytest, jest, go test, cargo test.
    """

    def generate(self, context: Dict[str, Any], intent: Intent) -> TestPlan:
        language = intent.language or Language.PYTHON
        ast_data = context.get("ast", {})
        functions = ast_data.get("functions", [])
        classes = ast_data.get("classes", [])
        cases: List[TestCase] = []
        mocks: List[str] = []
        for fn in functions:
            cases.append(
                TestCase(
                    name=f"test_{fn['name']}_basic",
                    description=f"Basic test for {fn['name']}",
                )
            )
            cases.append(
                TestCase(
                    name=f"test_{fn['name']}_edge_case",
                    description=f"Edge case for {fn['name']}",
                )
            )
            if "mock" in fn["name"].lower() or "fake" in fn["name"].lower():
                mocks.append(fn["name"])
        for cls in classes:
            cases.append(
                TestCase(
                    name=f"test_{cls['name']}_init",
                    description=f"Constructor test for {cls['name']}",
                )
            )
        return TestPlan(
            target_file=intent.target_file or "unknown.py",
            target_symbol=intent.target_symbol,
            language=language,
            cases=cases,
            mocks_needed=mocks,
            coverage_target=0.8,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — DocGenerator: Automated Documentation
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class DocResult:
    """Output of documentation generation."""

    content: str
    doc_type: str  # "docstring", "readme", "api_doc"
    language: Language
    symbols_covered: List[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"DocResult(type={self.doc_type}, lang={self.language.value}, symbols={len(self.symbols_covered)})"


class DocGenerator:
    """
    Generates docstrings, README, and API documentation from code context.
    """

    def generate_docstring(self, context: Dict[str, Any], intent: Intent) -> DocResult:
        """Generate docstring for a specific symbol."""
        ast_data = context.get("ast", {})
        symbol = intent.target_symbol or "unknown"
        language = intent.language or Language.PYTHON
        functions = ast_data.get("functions", [])
        classes = ast_data.get("classes", [])
        doc_parts: List[str] = []
        for fn in functions:
            if fn["name"] == symbol:
                args_str = ", ".join(fn.get("args", []))
                doc_parts.append(f'    """{symbol}({args_str}).')
                doc_parts.append(f'    Basic function documentation.')
                doc_parts.append(f'    """')
                break
        for cls in classes:
            if cls["name"] == symbol:
                methods = ", ".join(cls.get("methods", []))
                doc_parts.append(f'    """Class {symbol}.')
                doc_parts.append(f'    Methods: {methods}')
                doc_parts.append(f'    """')
                break
        return DocResult(
            content="\n".join(doc_parts) if doc_parts else f'# TODO: docstring for {symbol}',
            doc_type="docstring",
            language=language,
            symbols_covered=[symbol],
        )

    def generate_readme(self, context: Dict[str, Any], intent: Intent) -> DocResult:
        """Generate README from project context."""
        tree = context.get("file_tree")
        language = intent.language or Language.PYTHON
        readme_parts = ["# Project README", "", "## Structure"]
        if tree:
            for child in tree.children[:10]:
                readme_parts.append(f"- {child.path}")
        readme_parts.extend(["", "## Usage", "```bash", "python main.py", "```"])
        return DocResult(
            content="\n".join(readme_parts),
            doc_type="readme",
            language=language,
            symbols_covered=[],
        )

    def generate_api_doc(self, context: Dict[str, Any], intent: Intent) -> DocResult:
        """Generate API documentation from AST."""
        ast_data = context.get("ast", {})
        language = intent.language or Language.PYTHON
        api_parts = ["# API Documentation", ""]
        for fn in ast_data.get("functions", []):
            args_str = ", ".join(fn.get("args", []))
            api_parts.append(f"## `{fn['name']}({args_str})`")
            api_parts.append(f"- Line: {fn.get('line', '?')}")
            api_parts.append("")
        for cls in ast_data.get("classes", []):
            api_parts.append(f"## class `{cls['name']}`")
            methods = cls.get("methods", [])
            if methods:
                api_parts.append(f"- Methods: {', '.join(methods)}")
            api_parts.append("")
        return DocResult(
            content="\n".join(api_parts),
            doc_type="api_doc",
            language=language,
            symbols_covered=[f["name"] for f in ast_data.get("functions", [])] + [c["name"] for c in ast_data.get("classes", [])],
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — ReviewEngine: Code Review & Static Analysis
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ReviewFinding:
    """Single review finding."""

    severity: str  # "info", "warning", "error", "critical"
    category: str  # "complexity", "security", "performance", "style"
    message: str
    line: Optional[int] = None
    suggestion: str = ""

    def __repr__(self) -> str:
        return f"ReviewFinding({self.severity}, {self.category}, line={self.line})"


@dataclass
class ReviewReport:
    """Complete review report."""

    target_file: str
    findings: List[ReviewFinding] = field(default_factory=list)
    score: float = 0.0  # 0-100
    summary: str = ""

    def __repr__(self) -> str:
        return f"ReviewReport({self.target_file}, score={self.score}, findings={len(self.findings)})"


class ReviewEngine:
    """
    Simulated static analysis: complexity, security, performance, style.
    """

    def review(self, context: Dict[str, Any], intent: Intent) -> ReviewReport:
        findings: List[ReviewFinding] = []
        ast_data = context.get("ast", {})
        file_path = intent.target_file or "unknown.py"
        # Complexity: flag functions with >5 args
        for fn in ast_data.get("functions", []):
            args = fn.get("args", [])
            if len(args) > 5:
                findings.append(
                    ReviewFinding(
                        severity="warning",
                        category="complexity",
                        message=f"Function `{fn['name']}` has {len(args)} arguments — consider grouping into a config object",
                        line=fn.get("line"),
                        suggestion="Use a dataclass or dict for configuration parameters",
                    )
                )
        # Security: flag eval/exec patterns
        content = context.get("content", "")
        if "eval(" in content:
            findings.append(
                ReviewFinding(
                    severity="critical",
                    category="security",
                    message="`eval()` detected — arbitrary code execution risk",
                    suggestion="Use ast.literal_eval() or json.loads() instead",
                )
            )
        # Performance: flag nested loops (naive)
        lines = content.splitlines()
        for i, line in enumerate(lines, 1):
            if re.match(r"^\s*for\s+.*:\s*$", line):
                # Check next line for another for
                if i < len(lines) and re.match(r"^\s*for\s+.*:\s*$", lines[i]):
                    findings.append(
                        ReviewFinding(
                            severity="warning",
                            category="performance",
                            message=f"Nested loop at line {i} — O(n²) complexity",
                            line=i,
                            suggestion="Consider vectorization or algorithmic optimization",
                        )
                    )
        # Style: line length
        for i, line in enumerate(lines, 1):
            if len(line) > 120:
                findings.append(
                    ReviewFinding(
                        severity="info",
                        category="style",
                        message=f"Line {i} exceeds 120 characters ({len(line)} chars)",
                        line=i,
                        suggestion="Break into multiple lines",
                    )
                )
        score = max(0, 100 - len(findings) * 5)
        return ReviewReport(
            target_file=file_path,
            findings=findings,
            score=score,
            summary=f"Review complete: {len(findings)} findings, score {score}/100",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — DevAgent: Orchestrator State Machine
# ═══════════════════════════════════════════════════════════════════════════════


class AgentState(enum.Enum):
    IDLE = "idle"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    REFACTORING = "refactoring"
    TESTING = "testing"
    REVIEWING = "reviewing"
    DOCUMENTING = "documenting"
    ERROR = "error"


@dataclass
class AgentTask:
    """A single task in the agent queue."""

    id: str
    intent: Intent
    status: str = "pending"
    result: Optional[Any] = None
    error: Optional[str] = None

    def __repr__(self) -> str:
        return f"AgentTask({self.id}, {self.intent.action.value}, status={self.status})"


class DevAgent:
    """
    Orchestrator state machine for AutoDev.
    Receives intent, dispatches to appropriate engine, returns result.
    """

    def __init__(self) -> None:
        self.state = AgentState.IDLE
        self.tasks: List[AgentTask] = []
        self.context_extractor: Optional[ContextExtractor] = None
        self.intent_parser = IntentParser()
        self.code_generator = CodeGenerator()
        self.refactor_engine = RefactorEngine()
        self.test_generator = TestGenerator()
        self.doc_generator = DocGenerator()
        self.review_engine = ReviewEngine()

    def set_project(self, project_root: str) -> None:
        self.context_extractor = ContextExtractor(project_root)

    def submit(self, query: str, file_path: Optional[str] = None) -> AgentTask:
        """Submit a natural language query for processing."""
        intent = self.intent_parser.parse(query)
        if file_path:
            intent.target_file = file_path
        task = AgentTask(id=f"task_{len(self.tasks)}", intent=intent)
        self.tasks.append(task)
        self._execute(task)
        return task

    def _execute(self, task: AgentTask) -> None:
        try:
            self.state = AgentState.ANALYZING
            context: Dict[str, Any] = {}
            if self.context_extractor and task.intent.target_file:
                context = self.context_extractor.extract_file_context(task.intent.target_file)
            action = task.intent.action
            if action == DevAction.GENERATE_CODE:
                self.state = AgentState.GENERATING
                task.result = self.code_generator.generate(context, task.intent)
            elif action == DevAction.REFACTOR:
                self.state = AgentState.REFACTORING
                # Simulated refactor: just return a stub result
                task.result = RefactorResult(
                    original="# original",
                    refactored="# refactored",
                    operation=RefactorOperation.RENAME_SYMBOL,
                    safety_checks=["Simulated refactor"],
                    applied=True,
                )
            elif action == DevAction.ADD_TESTS:
                self.state = AgentState.TESTING
                task.result = self.test_generator.generate(context, task.intent)
            elif action == DevAction.GENERATE_DOCS:
                self.state = AgentState.DOCUMENTING
                task.result = self.doc_generator.generate_docstring(context, task.intent)
            elif action == DevAction.EXPLAIN_CODE:
                self.state = AgentState.ANALYZING
                task.result = self.doc_generator.generate_api_doc(context, task.intent)
            elif action == DevAction.CREATE_FUNCTION:
                self.state = AgentState.GENERATING
                task.result = self.code_generator.generate(context, task.intent, template_name="function_python")
            else:
                task.result = {"message": "Action not yet implemented", "action": action.value}
            task.status = "completed"
            self.state = AgentState.IDLE
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            self.state = AgentState.ERROR

    def get_status(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "queue_size": len(self.tasks),
            "completed": sum(1 for t in self.tasks if t.status == "completed"),
            "failed": sum(1 for t in self.tasks if t.status == "failed"),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 9 — PromptLibrary: Curated Template Registry
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class PromptTemplate:
    """A reusable prompt template with metadata."""

    name: str
    description: str
    template: str
    variables: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def render(self, variables: Dict[str, str]) -> str:
        result = self.template
        for key, val in variables.items():
            result = result.replace(f"{{{{{key}}}}}", val)
        return result

    def __repr__(self) -> str:
        return f"PromptTemplate({self.name}, tags={self.tags})"


class PromptLibrary:
    """
    Registry of curated prompt templates.
    Extensible: add new templates for domains, languages, frameworks.
    """

    def __init__(self) -> None:
        self._templates: Dict[str, PromptTemplate] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        defaults = [
            PromptTemplate(
                name="crud_api",
                description="Generate CRUD API endpoints",
                template="Generate CRUD API for {{model}} with fields: {{fields}}",
                variables=["model", "fields"],
                tags=["api", "backend"],
            ),
            PromptTemplate(
                name="react_component",
                description="Generate React component",
                template="Create React component {{name}} with props: {{props}}",
                variables=["name", "props"],
                tags=["frontend", "react"],
            ),
            PromptTemplate(
                name="python_class",
                description="Generate Python class with methods",
                template="Create Python class {{name}} with methods: {{methods}}",
                variables=["name", "methods"],
                tags=["python", "class"],
            ),
            PromptTemplate(
                name="unit_test",
                description="Generate unit tests",
                template="Write unit tests for {{function}} covering: {{cases}}",
                variables=["function", "cases"],
                tags=["testing", "quality"],
            ),
            PromptTemplate(
                name="code_review",
                description="Review code for issues",
                template="Review this code for {{focus}}: {{code}}",
                variables=["focus", "code"],
                tags=["review", "quality"],
            ),
        ]
        for pt in defaults:
            self._templates[pt.name] = pt

    def get(self, name: str) -> Optional[PromptTemplate]:
        return self._templates.get(name)

    def list_all(self) -> List[PromptTemplate]:
        return list(self._templates.values())

    def search_by_tag(self, tag: str) -> List[PromptTemplate]:
        return [t for t in self._templates.values() if tag in t.tags]

    def register(self, template: PromptTemplate) -> None:
        self._templates[template.name] = template


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 10 — AutoDevKernel: MAGNATRIX Bridge
# ═══════════════════════════════════════════════════════════════════════════════


class AutoDevKernel:
    """
    MAGNATRIX integration bridge.
    Hooks: Layer 12 (IDE), Layer 6 (Skills/Code gen), Layer 10 (AI Agents).
    """

    def __init__(self) -> None:
        self.agent = DevAgent()
        self.prompt_library = PromptLibrary()

    def ide_hook(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Layer 12: IDE event handler (file open, cursor move, selection)."""
        event_type = event.get("type", "unknown")
        if event_type == "file_open":
            file_path = event.get("file_path", "")
            if self.agent.context_extractor:
                context = self.agent.context_extractor.extract_file_context(file_path)
                return {"layer": 12, "action": "context_loaded", "context": context}
        elif event_type == "cursor_move":
            file_path = event.get("file_path", "")
            cursor = CursorPosition(line=event.get("line", 1), column=event.get("column", 0))
            if self.agent.context_extractor:
                context = self.agent.context_extractor.extract_file_context(file_path, cursor)
                return {"layer": 12, "action": "cursor_context", "context": context}
        return {"layer": 12, "action": "noop"}

    def skills_hook(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """Layer 6: Skills / code generation hook."""
        query = intent_data.get("query", "")
        template_name = intent_data.get("template")
        task = self.agent.submit(query)
        if template_name and isinstance(task.result, GenerationResult):
            # Re-generate with specific template
            context = {}
            if self.agent.context_extractor and task.intent.target_file:
                context = self.agent.context_extractor.extract_file_context(task.intent.target_file)
            task.result = self.agent.code_generator.generate(
                context, task.intent, template_name=template_name
            )
        return {"layer": 6, "task_id": task.id, "result": task.result}

    def ai_hook(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Layer 10: AI Agent orchestration hook."""
        action = message.get("action", "status")
        if action == "status":
            return {"layer": 10, "status": self.agent.get_status()}
        elif action == "submit":
            query = message.get("query", "")
            task = self.agent.submit(query)
            return {"layer": 10, "task_id": task.id, "status": task.status}
        elif action == "result":
            task_id = message.get("task_id", "")
            for task in self.agent.tasks:
                if task.id == task_id:
                    return {"layer": 10, "task": task}
            return {"layer": 10, "error": "task not found"}
        return {"layer": 10, "error": "unknown action"}


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO BLOCK — Simulasi "Generate CRUD API dari Schema"
# ═══════════════════════════════════════════════════════════════════════════════


def demo() -> None:
    """Demonstrate AutoDev Native with a CRUD API generation scenario."""
    print("=" * 60)
    print("AutoDev Native — Demo: Generate CRUD API dari Schema")
    print("=" * 60)

    # 1. Setup project context
    kernel = AutoDevKernel()
    # Simulated project root (current directory)
    kernel.agent.set_project(".")

    # 2. Parse intent
    query = "generate CRUD API untuk User dengan field name, email, age dalam python"
    intent = kernel.agent.intent_parser.parse(query)
    print(f"\n[Intent] {intent}")

    # 3. Generate code
    context = {}
    if kernel.agent.context_extractor:
        context = kernel.agent.context_extractor.extract_file_context("demo.py")
    result = kernel.agent.code_generator.generate(
        context, intent, template_name="crud_api_python"
    )
    print(f"\n[Generated] {result}")
    print(f"\n--- Code ({len(result.code.splitlines())} lines) ---")
    print(result.code[:500] + "..." if len(result.code) > 500 else result.code)

    # 4. Generate tests
    test_plan = kernel.agent.test_generator.generate(context, intent)
    print(f"\n[TestPlan] {test_plan}")
    for case in test_plan.cases[:3]:
        print(f"  - {case.name}: {case.description}")

    # 5. Review
    review = kernel.agent.review_engine.review(
        {"ast": context.get("ast", {}), "content": result.code}, intent
    )
    print(f"\n[Review] Score: {review.score}/100, Findings: {len(review.findings)}")
    for f in review.findings[:2]:
        print(f"  - [{f.severity}] {f.message}")

    # 6. MAGNATRIX bridge hooks
    ide_event = {"type": "file_open", "file_path": "demo.py"}
    print(f"\n[MAGNATRIX Layer 12] {kernel.ide_hook(ide_event)['action']}")

    skills_event = {"query": query, "template": "crud_api_python"}
    skills_result = kernel.skills_hook(skills_event)
    print(f"[MAGNATRIX Layer 6] Task {skills_result['task_id']} -> {type(skills_result['result']).__name__}")

    ai_event = {"action": "status"}
    print(f"[MAGNATRIX Layer 10] {kernel.ai_hook(ai_event)['status']}")

    print("\n" + "=" * 60)
    print("Demo selesai. AutoDev Native siap integrasi MAGNATRIX.")
    print("=" * 60)


if __name__ == "__main__":
    demo()

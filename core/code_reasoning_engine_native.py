#!/usr/bin/env python3
"""
Code Reasoning Engine — MAGNATRIX-OS Python Code Analysis & Reasoning
=======================================================================
Parse Python code (AST), reason about it: find bugs, suggest fixes,
explain logic, trace data flow. Pure stdlib ast + inspect.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations

import ast
import builtins
import inspect
import textwrap
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union


@dataclass
class CodeIssue:
    """A detected issue in code."""
    severity: str  # critical, warning, info
    category: str  # bug, style, performance, security
    message: str
    line: int
    col: int
    suggestion: str = ""
    confidence: float = 1.0  # 0.0 - 1.0


@dataclass
class CodeExplanation:
    """Explanation of what code does."""
    summary: str
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    side_effects: List[str] = field(default_factory=list)
    control_flow: List[str] = field(default_factory=list)
    complexity: str = ""


@dataclass
class DataFlow:
    """Data flow analysis result."""
    variable: str
    sources: List[int] = field(default_factory=list)  # line numbers
    sinks: List[int] = field(default_factory=list)
    transformations: List[str] = field(default_factory=list)


class ASTAnalyzer(ast.NodeVisitor):
    """Analyze Python AST for issues and patterns."""

    BUG_PATTERNS = {
        "bare_except": (ast.ExceptHandler, "Bare except clause catches SystemExit and KeyboardInterrupt", "warning", "bug"),
        "mutable_default": (ast.FunctionDef, "Mutable default argument can cause unexpected sharing", "warning", "bug"),
        "compare_identity": (ast.Compare, "Using 'is' for equality comparison may be incorrect", "info", "bug"),
    }

    SECURITY_PATTERNS = {
        "eval_call": ("Avoid eval() — arbitrary code execution risk", "critical"),
        "exec_call": ("Avoid exec() — arbitrary code execution risk", "critical"),
        "pickle_load": ("pickle.loads() can execute arbitrary code", "warning"),
        "yaml_load": ("yaml.load() without Loader can be unsafe", "warning"),
        "subprocess_shell": ("subprocess with shell=True is dangerous", "warning"),
    }

    def __init__(self, source: str = ""):
        self.source = source
        self.issues: List[CodeIssue] = []
        self.variables: Dict[str, List[Tuple[int, str]]] = {}  # name -> [(line, type)]
        self.functions: Dict[str, Dict[str, Any]] = {}
        self.classes: Dict[str, Dict[str, Any]] = {}
        self.data_flows: List[DataFlow] = []
        self._current_function: Optional[str] = None
        self._loop_depth = 0

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        old_func = self._current_function
        self._current_function = node.name
        func_info = {
            "args": [arg.arg for arg in node.args.args],
            "defaults": len(node.args.defaults),
            "line": node.lineno,
            "has_docstring": isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, (ast.Str, ast.Constant)) if node.body else False,
            "returns": isinstance(node.returns, ast.AST) if node.returns else False,
        }
        self.functions[node.name] = func_info

        # Check for mutable default arguments
        for default in node.args.defaults:
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                self.issues.append(CodeIssue(
                    severity="warning", category="bug",
                    message="Mutable default argument (list/dict/set) can cause unexpected sharing across calls",
                    line=node.lineno, col=node.col_offset,
                    suggestion=f"Use None as default and initialize inside function: def {node.name}(..., arg=None):",
                    confidence=0.9
                ))

        self.generic_visit(node)
        self._current_function = old_func

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.classes[node.name] = {
            "bases": [self._get_name(base) for base in node.bases],
            "methods": [item.name for item in node.body if isinstance(item, ast.FunctionDef)],
            "line": node.lineno,
        }
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.type is None:
            self.issues.append(CodeIssue(
                severity="warning", category="bug",
                message="Bare 'except:' catches SystemExit and KeyboardInterrupt — use 'except Exception:' instead",
                line=node.lineno, col=node.col_offset,
                suggestion="Replace 'except:' with 'except Exception:' or more specific exception types",
                confidence=0.95
            ))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        func_name = self._get_call_name(node.func)
        if func_name:
            for pattern, (msg, sev) in self.SECURITY_PATTERNS.items():
                if pattern in func_name.lower() or func_name.endswith(pattern.split("_")[-1]):
                    self.issues.append(CodeIssue(
                        severity=sev, category="security",
                        message=msg, line=node.lineno, col=node.col_offset,
                        suggestion=f"Consider safer alternatives for {func_name}",
                        confidence=0.85
                    ))
        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        for op in node.ops:
            if isinstance(op, ast.Is):
                # Check if comparing literals or strings
                if isinstance(node.left, (ast.Constant, ast.Str, ast.Num)):
                    self.issues.append(CodeIssue(
                        severity="info", category="bug",
                        message="Using 'is' for literal comparison — use '==' instead",
                        line=node.lineno, col=node.col_offset,
                        suggestion="Replace 'is' with '==' for value comparison",
                        confidence=0.8
                    ))
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self._loop_depth += 1
        self.generic_visit(node)
        self._loop_depth -= 1

    def visit_While(self, node: ast.While) -> None:
        self._loop_depth += 1
        # Check for potential infinite loops
        if not node.orelse and self._is_always_true(node.test):
            self.issues.append(CodeIssue(
                severity="warning", category="bug",
                message="Potential infinite loop — condition always appears true",
                line=node.lineno, col=node.col_offset,
                suggestion="Add a break condition or verify the loop logic",
                confidence=0.6
            ))
        self.generic_visit(node)
        self._loop_depth -= 1

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id
                if var_name not in self.variables:
                    self.variables[var_name] = []
                self.variables[var_name].append((node.lineno, "assignment"))
        self.generic_visit(node)

    def _get_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return ""

    def _get_call_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return ""

    def _is_always_true(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Constant):
            return bool(node.value)
        if isinstance(node, ast.Num):
            return bool(node.n)
        return False


class BugFinder:
    """Find bugs and suggest fixes in Python code."""

    def __init__(self):
        self._analyzer = ASTAnalyzer()

    def analyze(self, code: str) -> List[CodeIssue]:
        """Analyze code and return list of issues."""
        try:
            tree = ast.parse(textwrap.dedent(code))
        except SyntaxError as e:
            return [CodeIssue(
                severity="critical", category="bug",
                message=f"Syntax error: {e}", line=e.lineno or 1, col=e.offset or 0,
                suggestion="Fix syntax error before further analysis"
            )]

        self._analyzer = ASTAnalyzer(code)
        self._analyzer.visit(tree)
        return self._analyzer.issues

    def find_bugs(self, code: str) -> List[CodeIssue]:
        """Find only bug-level issues."""
        return [i for i in self.analyze(code) if i.category == "bug"]

    def find_security_issues(self, code: str) -> List[CodeIssue]:
        """Find security issues."""
        return [i for i in self.analyze(code) if i.category == "security"]


class CodeExplainer:
    """Explain what code does in natural language."""

    def explain(self, code: str) -> CodeExplanation:
        """Generate a high-level explanation of code."""
        try:
            tree = ast.parse(textwrap.dedent(code))
        except SyntaxError:
            return CodeExplanation(summary="Could not parse code — syntax error")

        explanation = CodeExplanation(summary="")
        lines = []

        # Count complexity metrics
        complexity = 0
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.For, ast.While, ast.ListComp, ast.DictComp, ast.SetComp)):
                complexity += 1
            if isinstance(node, ast.FunctionDef):
                explanation.inputs.extend([arg.arg for arg in node.args.args])
                if isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, (ast.Str, ast.Constant)):
                    doc = node.body[0].value.value if isinstance(node.body[0].value, ast.Constant) else node.body[0].value.s
                    lines.append(f"Function '{node.name}': {doc}")
                else:
                    lines.append(f"Function '{node.name}' with {len(node.args.args)} parameters")

        explanation.complexity = f"Cyclomatic complexity: ~{complexity}"

        # Identify side effects
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func_name = self._get_call_name(node.func)
                if func_name in ("print", "open", "write", "save", "delete", "remove"):
                    explanation.side_effects.append(f"Calls {func_name}() at line {node.lineno}")

        # Identify control flow
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                explanation.control_flow.append(f"Conditional at line {node.lineno}")
            elif isinstance(node, ast.For):
                explanation.control_flow.append(f"Loop at line {node.lineno}")
            elif isinstance(node, ast.While):
                explanation.control_flow.append(f"While loop at line {node.lineno}")
            elif isinstance(node, ast.Try):
                explanation.control_flow.append(f"Exception handling at line {node.lineno}")

        if not lines:
            lines.append("Module-level code (no function definitions)")
        explanation.summary = "; ".join(lines) if lines else "Simple code block"

        return explanation

    def _get_call_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_call_name(node.value)}.{node.attr}"
        return ""


class DataFlowTracer:
    """Trace data flow through variables in code."""

    def trace(self, code: str, variable_name: Optional[str] = None) -> List[DataFlow]:
        """Trace data flow for all or a specific variable."""
        try:
            tree = ast.parse(textwrap.dedent(code))
        except SyntaxError:
            return []

        analyzer = ASTAnalyzer(code)
        analyzer.visit(tree)

        flows = []
        for var_name, occurrences in analyzer.variables.items():
            if variable_name and var_name != variable_name:
                continue
            flow = DataFlow(variable=var_name)
            for line, op_type in occurrences:
                if op_type == "assignment":
                    flow.sources.append(line)
                else:
                    flow.sinks.append(line)
            flows.append(flow)

        return flows


class CodeReasoningEngine:
    """
    Top-level code reasoning engine for MAGNATRIX-OS.
    
    Provides: bug finding, security scanning, code explanation,
    data flow tracing, and fix suggestions.
    """

    CAPABILITIES = ["code_analysis", "bug_detection", "security_scan", "code_explanation", "data_flow"]

    def __init__(self, repo_root: str = "."):
        self.repo_root = repo_root
        self._bug_finder = BugFinder()
        self._explainer = CodeExplainer()
        self._tracer = DataFlowTracer()
        self._lock = threading.Lock()
        self._stats = {"files_analyzed": 0, "issues_found": 0, "explanations": 0}

    def analyze(self, code: str) -> Dict[str, Any]:
        """Full analysis: issues, explanation, data flow."""
        issues = self._bug_finder.analyze(code)
        explanation = self._explainer.explain(code)
        flows = self._tracer.trace(code)

        with self._lock:
            self._stats["files_analyzed"] += 1
            self._stats["issues_found"] += len(issues)

        return {
            "issues": [
                {"severity": i.severity, "category": i.category, "message": i.message,
                 "line": i.line, "col": i.col, "suggestion": i.suggestion, "confidence": i.confidence}
                for i in issues
            ],
            "explanation": {
                "summary": explanation.summary,
                "inputs": explanation.inputs,
                "outputs": explanation.outputs,
                "side_effects": explanation.side_effects,
                "control_flow": explanation.control_flow,
                "complexity": explanation.complexity,
            },
            "data_flow": [
                {"variable": f.variable, "sources": f.sources, "sinks": f.sinks}
                for f in flows
            ],
            "summary": {
                "critical": len([i for i in issues if i.severity == "critical"]),
                "warnings": len([i for i in issues if i.severity == "warning"]),
                "info": len([i for i in issues if i.severity == "info"]),
            }
        }

    def find_bugs(self, code: str) -> List[Dict[str, Any]]:
        """Find bugs only."""
        issues = self._bug_finder.find_bugs(code)
        return [{"message": i.message, "line": i.line, "suggestion": i.suggestion} for i in issues]

    def find_security_issues(self, code: str) -> List[Dict[str, Any]]:
        """Find security issues only."""
        issues = self._bug_finder.find_security_issues(code)
        return [{"message": i.message, "line": i.line, "severity": i.severity} for i in issues]

    def explain(self, code: str) -> Dict[str, Any]:
        """Explain what code does."""
        exp = self._explainer.explain(code)
        with self._lock:
            self._stats["explanations"] += 1
        return {
            "summary": exp.summary,
            "inputs": exp.inputs,
            "outputs": exp.outputs,
            "side_effects": exp.side_effects,
            "control_flow": exp.control_flow,
            "complexity": exp.complexity,
        }

    def trace_data_flow(self, code: str, variable: Optional[str] = None) -> List[Dict[str, Any]]:
        """Trace data flow for variables."""
        flows = self._tracer.trace(code, variable)
        return [{"variable": f.variable, "sources": f.sources, "sinks": f.sinks} for f in flows]

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._stats)

    def handle_message(self, message: Dict[str, Any]) -> Any:
        action = message.get("action", "")
        if action == "analyze":
            return self.analyze(message["code"])
        elif action == "find_bugs":
            return self.find_bugs(message["code"])
        elif action == "security":
            return self.find_security_issues(message["code"])
        elif action == "explain":
            return self.explain(message["code"])
        elif action == "trace":
            return self.trace_data_flow(message["code"], message.get("variable"))
        elif action == "stats":
            return self.get_stats()
        return None

    def on_event(self, event) -> None:
        pass

#!/usr/bin/env python3
"""
security/safe_eval_native.py
==========================
Security Utility — Safe Expression Evaluator & Input Validators

Replaces dangerous eval()/exec() with restricted expression evaluation.
Provides path sanitization, input validation, and safe code execution.
"""

from __future__ import annotations

import ast
import math
import operator
import os
import re
from typing import Any, Dict, List, Optional, Set, Callable


# =============================================================================
# 1. SAFE EXPRESSION EVALUATOR (replaces eval)
# =============================================================================

class SafeExpressionError(Exception):
    pass


class SafeEvaluator:
    """Evaluate mathematical/logical expressions without arbitrary code execution.
    Supports: numbers, basic math, comparisons, logical ops.
    NO: function calls, attribute access, imports, comprehensions, lambdas.
    """

    _SAFE_OPS: Dict[type, Callable] = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        ast.And: lambda a, b: a and b,
        ast.Or: lambda a, b: a or b,
        ast.Not: operator.not_,
        ast.In: lambda a, b: a in b,
        ast.Is: operator.is_,
    }

    _SAFE_NAMES: Dict[str, Any] = {
        "True": True,
        "False": False,
        "None": None,
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "len": len,
        "int": int,
        "float": float,
        "str": str,
        "bool": bool,
        "math": math,
    }

    def __init__(self, extra_names: Optional[Dict[str, Any]] = None) -> None:
        self.names = dict(self._SAFE_NAMES)
        if extra_names:
            self.names.update(extra_names)

    def eval(self, expression: str) -> Any:
        """Safely evaluate an expression string."""
        if not isinstance(expression, str):
            raise SafeExpressionError("Expression must be a string")
        if len(expression) > 10000:
            raise SafeExpressionError("Expression too long (>10000 chars)")
        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as e:
            raise SafeExpressionError(f"Invalid syntax: {e}") from e
        return self._eval_node(tree.body)

    def _eval_node(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Num):  # Python < 3.8
            return node.n
        elif isinstance(node, ast.Str):  # Python < 3.8
            return node.s
        elif isinstance(node, ast.Name):
            if node.id not in self.names:
                raise SafeExpressionError(f"Unknown name: {node.id}")
            return self.names[node.id]
        elif isinstance(node, ast.NameConstant):  # Python < 3.8
            return node.value
        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in self._SAFE_OPS:
                raise SafeExpressionError(f"Unsupported binary operator: {op_type.__name__}")
            return self._SAFE_OPS[op_type](self._eval_node(node.left), self._eval_node(node.right))
        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in self._SAFE_OPS:
                raise SafeExpressionError(f"Unsupported unary operator: {op_type.__name__}")
            return self._SAFE_OPS[op_type](self._eval_node(node.operand))
        elif isinstance(node, ast.Compare):
            left = self._eval_node(node.left)
            result = True
            for op, comparator in zip(node.ops, node.comparators):
                op_type = type(op)
                if op_type not in self._SAFE_OPS:
                    raise SafeExpressionError(f"Unsupported comparison: {op_type.__name__}")
                right = self._eval_node(comparator)
                result = self._SAFE_OPS[op_type](left, right)
                if not result:
                    break
                left = right
            return result
        elif isinstance(node, ast.BoolOp):
            values = [self._eval_node(v) for v in node.values]
            op_type = type(node.op)
            if op_type == ast.And:
                return all(values)
            elif op_type == ast.Or:
                return any(values)
            raise SafeExpressionError(f"Unsupported bool op: {op_type.__name__}")
        elif isinstance(node, ast.IfExp):
            return self._eval_node(node.body) if self._eval_node(node.test) else self._eval_node(node.orelse)
        elif isinstance(node, ast.Tuple):
            return tuple(self._eval_node(elt) for elt in node.elts)
        elif isinstance(node, ast.List):
            return [self._eval_node(elt) for elt in node.elts]
        elif isinstance(node, ast.Dict):
            return {self._eval_node(k): self._eval_node(v) for k, v in zip(node.keys, node.values)}
        elif isinstance(node, ast.Subscript):
            value = self._eval_node(node.value)
            slice_val = self._eval_node(node.slice)
            return value[slice_val]
        elif isinstance(node, ast.Call):
            raise SafeExpressionError("Function calls are not allowed")
        elif isinstance(node, ast.Attribute):
            raise SafeExpressionError("Attribute access is not allowed")
        elif isinstance(node, ast.Lambda):
            raise SafeExpressionError("Lambdas are not allowed")
        elif isinstance(node, ast.ListComp) or isinstance(node, ast.DictComp) or isinstance(node, ast.SetComp) or isinstance(node, ast.GeneratorExp):
            raise SafeExpressionError("Comprehensions are not allowed")
        else:
            raise SafeExpressionError(f"Unsupported expression type: {type(node).__name__}")


# =============================================================================
# 2. PATH SANITIZER (replaces raw open())
# =============================================================================

class PathSanitizer:
    """Sanitize file paths to prevent directory traversal attacks."""

    @staticmethod
    def sanitize(user_path: str, allowed_roots: List[str], max_length: int = 4096) -> str:
        """Sanitize a user-provided path.
        
        Args:
            user_path: The path provided by user/external input
            allowed_roots: List of allowed base directories (absolute paths)
            max_length: Maximum allowed path length
            
        Returns:
            Absolute sanitized path
            
        Raises:
            ValueError: If path is invalid or outside allowed roots
        """
        if not isinstance(user_path, str):
            raise ValueError("Path must be a string")
        if len(user_path) > max_length:
            raise ValueError(f"Path too long (> {max_length} chars)")
        
        # Reject null bytes
        if "\x00" in user_path:
            raise ValueError("Path contains null bytes")
        
        # Reject path traversal attempts
        if ".." in user_path.split(os.sep):
            raise ValueError("Path traversal not allowed")
        
        # Normalize to absolute
        abs_path = os.path.abspath(os.path.normpath(user_path))
        
        # Check against allowed roots
        for root in allowed_roots:
            root_abs = os.path.abspath(os.path.normpath(root))
            # Ensure the path is under the allowed root
            if abs_path == root_abs or abs_path.startswith(root_abs + os.sep):
                return abs_path
        
        raise ValueError(f"Path '{user_path}' is outside allowed directories")

    @staticmethod
    def safe_open(user_path: str, allowed_roots: List[str], mode: str = "r", **kwargs) -> Any:
        """Open a file after path sanitization."""
        safe_path = PathSanitizer.sanitize(user_path, allowed_roots)
        return open(safe_path, mode, **kwargs)


# =============================================================================
# 3. INPUT VALIDATOR
# =============================================================================

class InputValidator:
    """Validate external input at function boundaries."""

    @staticmethod
    def string(value: Any, max_length: int = 10000, min_length: int = 0,
               pattern: Optional[str] = None, name: str = "input") -> str:
        if not isinstance(value, str):
            raise TypeError(f"{name} must be a string, got {type(value).__name__}")
        if len(value) < min_length:
            raise ValueError(f"{name} too short (< {min_length} chars)")
        if len(value) > max_length:
            raise ValueError(f"{name} too long (> {max_length} chars)")
        if pattern and not re.match(pattern, value):
            raise ValueError(f"{name} does not match required pattern")
        return value

    @staticmethod
    def integer(value: Any, min_val: Optional[int] = None, max_val: Optional[int] = None,
                name: str = "input") -> int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise TypeError(f"{name} must be an integer, got {type(value).__name__}")
        if min_val is not None and value < min_val:
            raise ValueError(f"{name} below minimum {min_val}")
        if max_val is not None and value > max_val:
            raise ValueError(f"{name} above maximum {max_val}")
        return value

    @staticmethod
    def bytes(value: Any, max_length: int = 10 * 1024 * 1024, name: str = "input") -> bytes:
        if not isinstance(value, bytes):
            raise TypeError(f"{name} must be bytes, got {type(value).__name__}")
        if len(value) > max_length:
            raise ValueError(f"{name} too large (> {max_length} bytes)")
        return value

    @staticmethod
    def dict(value: Any, required_keys: Optional[List[str]] = None,
             max_depth: int = 5, current_depth: int = 0, name: str = "input") -> Dict:
        if not isinstance(value, dict):
            raise TypeError(f"{name} must be a dict, got {type(value).__name__}")
        if current_depth > max_depth:
            raise ValueError(f"{name} nesting too deep (> {max_depth})")
        if required_keys:
            for key in required_keys:
                if key not in value:
                    raise ValueError(f"{name} missing required key: {key}")
        return value


# =============================================================================
# 4. SAFE SUBPROCESS WRAPPER
# =============================================================================

class SafeSubprocess:
    """Secure subprocess execution without shell=True."""

    @staticmethod
    def run(cmd: List[str], **kwargs) -> Any:
        """Run a command with shell=False enforced.
        
        Args:
            cmd: List of command arguments (never a string!)
            **kwargs: Additional subprocess.run kwargs
            
        Raises:
            ValueError: If cmd is not a list, or if shell=True is passed
        """
        if not isinstance(cmd, list):
            raise ValueError("cmd must be a list of strings, never a shell string")
        if kwargs.get("shell"):
            raise ValueError("shell=True is forbidden — use list args instead")
        import subprocess
        return subprocess.run(cmd, shell=False, **kwargs)

    @staticmethod
    def check_output(cmd: List[str], **kwargs) -> bytes:
        """Run command and return stdout."""
        if not isinstance(cmd, list):
            raise ValueError("cmd must be a list of strings")
        if kwargs.get("shell"):
            raise ValueError("shell=True is forbidden")
        import subprocess
        return subprocess.check_output(cmd, shell=False, **kwargs)


# =============================================================================
# 5. SAFE FILE OPERATIONS
# =============================================================================

class SafeFileOps:
    """File operations with automatic path sanitization."""

    _DEFAULT_ROOTS: List[str] = ["/var/lib/magnatrix", "/tmp/magnatrix", "/mnt/agents/MAGNATRIX-OS"]

    @classmethod
    def set_allowed_roots(cls, roots: List[str]) -> None:
        cls._DEFAULT_ROOTS = [os.path.abspath(r) for r in roots]

    @classmethod
    def open(cls, path: str, mode: str = "r", **kwargs) -> Any:
        return PathSanitizer.safe_open(path, cls._DEFAULT_ROOTS, mode, **kwargs)

    @classmethod
    def read(cls, path: str) -> bytes:
        with cls.open(path, "rb") as f:
            return f.read()

    @classmethod
    def write(cls, path: str, data: bytes) -> None:
        with cls.open(path, "wb") as f:
            f.write(data)

    @classmethod
    def exists(cls, path: str) -> bool:
        try:
            safe_path = PathSanitizer.sanitize(path, cls._DEFAULT_ROOTS)
            return os.path.exists(safe_path)
        except ValueError:
            return False


# =============================================================================
# 6. DEMO
# =============================================================================

def demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS  |  SAFE EVAL & INPUT VALIDATION")
    print("=" * 60)

    # Safe eval
    se = SafeEvaluator()
    expressions = [
        "2 + 3 * 4",
        "math.sqrt(16)",  # Will fail — no attribute access
        "True and False",
        "10 > 5",
        "[1, 2, 3]",
        "__import__('os').system('ls')",  # Will fail
    ]
    for expr in expressions:
        try:
            result = se.eval(expr)
            print(f"  [OK] {expr!r} = {result!r}")
        except SafeExpressionError as e:
            print(f"  [BLOCKED] {expr!r} -> {e}")

    # Path sanitizer
    ps = PathSanitizer()
    print("\n  Path sanitization:")
    test_paths = [
        ("/var/lib/magnatrix/data.txt", True),
        ("../../../etc/passwd", False),
        ("/tmp/magnatrix/cache.bin", True),
        ("/etc/shadow", False),
    ]
    for path, should_pass in test_paths:
        try:
            result = ps.sanitize(path, ["/var/lib/magnatrix", "/tmp/magnatrix"])
            status = "OK" if should_pass else "FAIL (should have blocked)"
            print(f"  [{status}] {path} -> {result}")
        except ValueError as e:
            status = "OK" if not should_pass else "FAIL (should have allowed)"
            print(f"  [{status}] {path} -> BLOCKED: {e}")

    # Input validator
    print("\n  Input validation:")
    try:
        InputValidator.string("hello", max_length=100)
        print("  [OK] string validation passed")
    except Exception as e:
        print(f"  [FAIL] {e}")

    try:
        InputValidator.integer(42, min_val=0, max_val=100)
        print("  [OK] integer validation passed")
    except Exception as e:
        print(f"  [FAIL] {e}")

    print("=" * 60)


if __name__ == "__main__":
    demo()

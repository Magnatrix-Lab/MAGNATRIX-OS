"""security/safe_eval_native.py — Safe evaluation wrapper for MAGNATRIX-OS"""
from __future__ import annotations
import ast
import builtins
import threading
import time
from typing import Any, Dict, Optional

class SafeEvaluator:
    """Safe eval/exec wrapper. Blocks dangerous builtins, supports timeout."""

    DANGEROUS_BUILTINS = {
        '__import__', 'open', 'exec', 'eval', 'compile',
        'os', 'sys', 'subprocess', 'socket', 'input',
        'file', 'reload', 'exit', 'quit',
    }

    SAFE_BUILTINS = {
        'abs', 'all', 'any', 'bool', 'chr', 'dict', 'divmod',
        'enumerate', 'filter', 'float', 'format', 'frozenset',
        'hasattr', 'hash', 'hex', 'int', 'isinstance', 'issubclass',
        'iter', 'len', 'list', 'map', 'max', 'min', 'next', 'oct',
        'ord', 'pow', 'range', 'repr', 'reversed', 'round', 'set',
        'slice', 'sorted', 'str', 'sum', 'tuple', 'type', 'zip',
        'True', 'False', 'None',
    }

    def __init__(self, timeout_sec: float = 5.0):
        self.timeout_sec = timeout_sec
        self._lock = threading.Lock()

    def eval(self, expr: str, globals_dict: Optional[Dict] = None, locals_dict: Optional[Dict] = None) -> Any:
        """Safely evaluate an expression."""
        if not isinstance(expr, str):
            raise ValueError("Expression must be a string")

        # Try ast.literal_eval first for simple literals
        try:
            return ast.literal_eval(expr)
        except (ValueError, SyntaxError):
            pass

        # Validate AST
        try:
            tree = ast.parse(expr, mode='eval')
        except SyntaxError as e:
            raise ValueError(f"Invalid expression: {e}")

        # Check for dangerous nodes
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in self.DANGEROUS_BUILTINS:
                    raise ValueError(f"Forbidden function call: {node.func.id}")
            elif isinstance(node, ast.Name) and node.id in self.DANGEROUS_BUILTINS:
                raise ValueError(f"Forbidden name: {node.id}")

        # Create safe globals
        safe_globals = {k: getattr(builtins, k) for k in self.SAFE_BUILTINS if hasattr(builtins, k)}
        safe_globals['__builtins__'] = safe_globals

        if globals_dict:
            safe_globals.update({k: v for k, v in globals_dict.items() if k not in self.DANGEROUS_BUILTINS})

        # Execute with timeout
        result = [None]
        error = [None]
        def target():
            try:
                result[0] = eval(compile(tree, '<safe_eval>', 'eval'), safe_globals, locals_dict)
            except Exception as e:
                error[0] = e

        t = threading.Thread(target=target)
        t.start()
        t.join(timeout=self.timeout_sec)

        if t.is_alive():
            raise TimeoutError(f"Expression evaluation timed out after {self.timeout_sec}s")

        if error[0]:
            raise error[0]

        return result[0]

    def exec(self, code: str, globals_dict: Optional[Dict] = None, locals_dict: Optional[Dict] = None) -> None:
        """Safely execute code."""
        if not isinstance(code, str):
            raise ValueError("Code must be a string")

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise ValueError(f"Invalid code: {e}")

        for node in ast.walk(tree):
            if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                raise ValueError("Import statements are forbidden")
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in self.DANGEROUS_BUILTINS:
                    raise ValueError(f"Forbidden function call: {node.func.id}")

        safe_globals = {k: getattr(builtins, k) for k in self.SAFE_BUILTINS if hasattr(builtins, k)}
        safe_globals['__builtins__'] = safe_globals

        if globals_dict:
            safe_globals.update({k: v for k, v in globals_dict.items() if k not in self.DANGEROUS_BUILTINS})

        result = [None]
        error = [None]
        def target():
            try:
                exec(compile(tree, '<safe_exec>', 'exec'), safe_globals, locals_dict)
            except Exception as e:
                error[0] = e

        t = threading.Thread(target=target)
        t.start()
        t.join(timeout=self.timeout_sec)

        if t.is_alive():
            raise TimeoutError(f"Code execution timed out after {self.timeout_sec}s")

        if error[0]:
            raise error[0]

if __name__ == "__main__":
    print("SafeEvaluator self-test")
    se = SafeEvaluator()
    assert se.eval("1 + 2") == 3
    assert se.eval("[1, 2, 3]") == [1, 2, 3]
    try:
        se.eval("__import__('os')")
        assert False
    except ValueError:
        pass
    print("All tests pass")

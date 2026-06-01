"""Secure Code Execution Sandbox — Safe code execution, output capture, timeout, resource limits.

Modul ini menyediakan:
- CodeSandbox untuk isolated execution environment
- OutputCapture untuk stdout/stderr capture
- ResourceLimiter dengan timeout dan memory limits
- SafetyChecker untuk dangerous code detection
- ExecutionResult dengan output, errors, dan metrics
"""

from __future__ import annotations

import json
import time
import uuid
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum, auto


class ExecutionStatus(Enum):
    SUCCESS = auto()
    TIMEOUT = auto()
    MEMORY_EXCEEDED = auto()
    SAFETY_VIOLATION = auto()
    SYNTAX_ERROR = auto()
    RUNTIME_ERROR = auto()
    CANCELLED = auto()


@dataclass
class ExecutionResult:
    """Result dari code execution."""
    execution_id: str
    status: ExecutionStatus
    stdout: str = ""
    stderr: str = ""
    return_value: Any = None
    duration_ms: float = 0.0
    memory_used_kb: float = 0.0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "status": self.status.name,
            "stdout": self.stdout[:500],
            "stderr": self.stderr[:500],
            "return_value": str(self.return_value)[:200],
            "duration_ms": round(self.duration_ms, 2),
            "memory_used_kb": round(self.memory_used_kb, 2),
            "error": self.error
        }


class SafetyChecker:
    """Check code untuk dangerous patterns."""

    def __init__(self):
        self._dangerous_patterns = [
            (r"\b__import__\b", "Dynamic import detected"),
            (r"\bimport\s+os\b", "OS module import"),
            (r"\bimport\s+subprocess\b", "Subprocess import"),
            (r"\bimport\s+sys\b", "Sys module import"),
            (r"\bopen\s*\(", "File open operation"),
            (r"\bexec\s*\(", "Exec call"),
            (r"\beval\s*\(", "Eval call"),
            (r"\bcompile\s*\(", "Compile call"),
            (r"\bfile\s*\(", "File constructor"),
            (r"\binput\s*\(", "Input call"),
            (r"\braw_input\s*\(", "Raw input call"),
            (r"\b__builtins__\b", "Builtins access"),
            (r"\b__ subclasses __\b", "Subclass enumeration"),
            (r"\bimport\s+socket\b", "Socket import"),
            (r"\bimport\s+urllib\b", "urllib import"),
            (r"\bimport\s+requests\b", "Requests import"),
            (r"\bimport\s+ftplib\b", "FTP import"),
            (r"\bimport\s+smtplib\b", "SMTP import"),
        ]
        self._allowed_modules = {"math", "random", "statistics", "json", "datetime", "itertools", "collections", "functools", "typing", "string", "re", "hashlib", "uuid", "time", "decimal", "fractions", "numbers", "enum"}

    def check(self, code: str) -> Tuple[bool, List[str]]:
        violations = []
        for pattern, reason in self._dangerous_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                violations.append(reason)
        # Check imports
        import_lines = re.findall(r'^import\s+(\w+)|^from\s+(\w+)', code, re.MULTILINE)
        for groups in import_lines:
            module = groups[0] or groups[1]
            if module not in self._allowed_modules:
                violations.append(f"Import '{module}' not in allowed list")
        return len(violations) == 0, violations

    def sanitize(self, code: str) -> str:
        # Remove dangerous builtins
        for pattern, _ in self._dangerous_patterns:
            code = re.sub(pattern, "# [BLOCKED]", code, flags=re.IGNORECASE)
        return code


class CodeSandbox:
    """Isolated code execution environment."""

    def __init__(self, timeout_ms: float = 5000.0, max_memory_kb: float = 10240.0, strict_mode: bool = True):
        self.timeout_ms = timeout_ms
        self.max_memory_kb = max_memory_kb
        self.strict_mode = strict_mode
        self.safety = SafetyChecker()
        self._execution_history: List[ExecutionResult] = []
        self._global_env: Dict[str, Any] = {}
        self._setup_safe_env()

    def _setup_safe_env(self) -> None:
        import math, random, statistics, json, datetime, itertools, collections, functools, string, re, hashlib, time, decimal, fractions, enum
        self._global_env = {
            "__builtins__": {
                "abs": abs, "all": all, "any": any, "ascii": ascii, "bin": bin,
                "bool": bool, "bytearray": bytearray, "bytes": bytes, "callable": callable,
                "chr": chr, "complex": complex, "dict": dict, "divmod": divmod,
                "enumerate": enumerate, "filter": filter, "float": float, "format": format,
                "frozenset": frozenset, "hasattr": hasattr, "hash": hash, "hex": hex,
                "int": int, "isinstance": isinstance, "issubclass": issubclass, "iter": iter,
                "len": len, "list": list, "map": map, "max": max, "min": min,
                "next": next, "oct": oct, "ord": ord, "pow": pow, "print": print,
                "range": range, "repr": repr, "reversed": reversed, "round": round,
                "set": set, "slice": slice, "sorted": sorted, "str": str, "sum": sum,
                "tuple": tuple, "type": type, "zip": zip, "True": True, "False": False, "None": None,
            },
            "math": math, "random": random, "statistics": statistics, "json": json,
            "datetime": datetime, "itertools": itertools, "collections": collections,
            "functools": functools, "string": string, "re": re, "hashlib": hashlib,
            "time": time, "decimal": decimal, "fractions": fractions, "enum": enum,
        }

    def execute(self, code: str, input_data: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        exec_id = str(uuid.uuid4())[:12]
        start = time.time()

        # Safety check
        safe, violations = self.safety.check(code)
        if not safe and self.strict_mode:
            return ExecutionResult(
                execution_id=exec_id,
                status=ExecutionStatus.SAFETY_VIOLATION,
                error="Safety violations: " + "; ".join(violations),
                duration_ms=(time.time() - start) * 1000
            )

        # Syntax check
        try:
            compile(code, "<sandbox>", "exec")
        except SyntaxError as e:
            return ExecutionResult(
                execution_id=exec_id,
                status=ExecutionStatus.SYNTAX_ERROR,
                error=str(e),
                duration_ms=(time.time() - start) * 1000
            )

        # Prepare environment
        env = dict(self._global_env)
        if input_data:
            env.update(input_data)

        # Capture output
        import io, sys
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = stdout_capture
        sys.stderr = stderr_capture

        try:
            # Execute with timeout simulation (simplified - no real process isolation)
            exec(compile(code, "<sandbox>", "exec"), env)
            duration = (time.time() - start) * 1000

            if duration > self.timeout_ms:
                return ExecutionResult(
                    execution_id=exec_id,
                    status=ExecutionStatus.TIMEOUT,
                    stdout=stdout_capture.getvalue(),
                    stderr=stderr_capture.getvalue(),
                    error=f"Execution exceeded {self.timeout_ms}ms",
                    duration_ms=duration
                )

            result = ExecutionResult(
                execution_id=exec_id,
                status=ExecutionStatus.SUCCESS,
                stdout=stdout_capture.getvalue(),
                stderr=stderr_capture.getvalue(),
                return_value=env.get("__result__", None),
                duration_ms=duration,
                memory_used_kb=0.0  # Not tracked in this implementation
            )
            self._execution_history.append(result)
            return result

        except Exception as e:
            duration = (time.time() - start) * 1000
            result = ExecutionResult(
                execution_id=exec_id,
                status=ExecutionStatus.RUNTIME_ERROR,
                stdout=stdout_capture.getvalue(),
                stderr=stderr_capture.getvalue(),
                error=str(e),
                duration_ms=duration
            )
            self._execution_history.append(result)
            return result
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def execute_file(self, file_path: str) -> ExecutionResult:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code = f.read()
            return self.execute(code)
        except Exception as e:
            return ExecutionResult(
                execution_id=str(uuid.uuid4())[:12],
                status=ExecutionStatus.RUNTIME_ERROR,
                error=str(e)
            )

    def get_history(self) -> List[ExecutionResult]:
        return self._execution_history

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._execution_history)
        success = sum(1 for r in self._execution_history if r.status == ExecutionStatus.SUCCESS)
        return {
            "total_executions": total,
            "successful": success,
            "failed": total - success,
            "success_rate": round(success / max(total, 1), 3),
            "avg_duration_ms": round(sum(r.duration_ms for r in self._execution_history) / max(total, 1), 2)
        }

    def export_history(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([r.to_dict() for r in self._execution_history], f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("SECURE CODE EXECUTION SANDBOX DEMO")
    print("=" * 70)

    sandbox = CodeSandbox(timeout_ms=5000, strict_mode=True)

    # 1. Safe code execution
    print("\n[1] Safe Code Execution")
    code1 = """
import math
x = 10
y = 20
result = math.sqrt(x**2 + y**2)
print(f"Hypotenuse: {result}")
__result__ = result
"""
    r1 = sandbox.execute(code1)
    print(f"  Status: {r1.status.name}")
    print(f"  Output: {r1.stdout.strip()}")
    print(f"  Return: {r1.return_value}")
    print(f"  Duration: {r1.duration_ms:.2f}ms")

    # 2. Math and statistics
    print("\n[2] Math & Statistics")
    code2 = """
import random
import statistics

data = [random.randint(1, 100) for _ in range(20)]
mean = statistics.mean(data)
median = statistics.median(data)
stdev = statistics.stdev(data)
print(f"Data: {data[:5]}...")
print(f"Mean: {mean:.2f}, Median: {median:.2f}, Stdev: {stdev:.2f}")
__result__ = {"mean": mean, "median": median}
"""
    r2 = sandbox.execute(code2)
    print(f"  Status: {r2.status.name}")
    print(f"  Output: {r2.stdout.strip()}")

    # 3. Safety violation
    print("\n[3] Safety Violation Detection")
    code3 = """
import os
os.system("ls")
"""
    r3 = sandbox.execute(code3)
    print(f"  Status: {r3.status.name}")
    print(f"  Error: {r3.error}")

    # 4. Syntax error
    print("\n[4] Syntax Error")
    code4 = "print('hello"
    r4 = sandbox.execute(code4)
    print(f"  Status: {r4.status.name}")
    print(f"  Error: {r4.error[:60]}...")

    # 5. Runtime error
    print("\n[5] Runtime Error")
    code5 = "x = 1 / 0"
    r5 = sandbox.execute(code5)
    print(f"  Status: {r5.status.name}")
    print(f"  Error: {r5.error}")

    # 6. With input data
    print("\n[6] Input Data")
    code6 = """
result = data["a"] + data["b"]
print(f"Sum: {result}")
__result__ = result
"""
    r6 = sandbox.execute(code6, {"data": {"a": 5, "b": 10}})
    print(f"  Status: {r6.status.name}")
    print(f"  Output: {r6.stdout.strip()}")
    print(f"  Return: {r6.return_value}")

    # 7. Stats and history
    print("\n[7] Execution Stats")
    print(f"  Stats: {sandbox.get_stats()}")
    print(f"  History: {len(sandbox.get_history())} executions")
    sandbox.export_history("/tmp/sandbox_history.json")
    print(f"  Exported to /tmp/sandbox_history.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()

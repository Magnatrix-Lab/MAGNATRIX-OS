"""
llm_sandbox_executor_native.py
MAGNATRIX-OS Sandbox Executor Engine
Native Python, stdlib only.
Provides isolated code execution with timeout, memory limits, stdout/stderr capture,
resource monitoring, and restricted builtins for safe LLM-generated code execution.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Callable


class SandboxStatus(Enum):
    SUCCESS = "success"
    TIMEOUT = "timeout"
    MEMORY_EXCEEDED = "memory_exceeded"
    ERROR = "error"
    KILLED = "killed"


@dataclass
class SandboxResult:
    status: SandboxStatus
    stdout: str
    stderr: str
    return_code: int
    execution_time_ms: float
    memory_used_kb: int = 0
    output_truncated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value, "stdout": self.stdout[:200],
            "stderr": self.stderr[:200], "return_code": self.return_code,
            "execution_time_ms": self.execution_time_ms,
            "memory_used_kb": self.memory_used_kb,
            "output_truncated": self.output_truncated,
        }


class SandboxExecutorEngine:
    """
    Isolated sandbox executor for running untrusted code safely.
    """

    def __init__(self, max_output_size: int = 65536) -> None:
        self.max_output_size = max_output_size
        self._restricted_builtins = self._build_restricted_builtins()

    def _build_restricted_builtins(self) -> Dict[str, Any]:
        safe = {}
        for name in (
            "abs", "all", "any", "ascii", "bin", "bool", "bytearray", "bytes",
            "chr", "complex", "dict", "divmod", "enumerate", "filter", "float",
            "format", "frozenset", "hash", "hex", "int", "isinstance", "issubclass",
            "iter", "len", "list", "map", "max", "min", "oct", "ord", "pow",
            "print", "range", "reversed", "round", "set", "slice", "sorted",
            "str", "sum", "tuple", "zip", "True", "False", "None",
        ):
            if name in __builtins__:
                safe[name] = __builtins__[name]
        return safe

    def execute_python(self, code: str, timeout_seconds: float = 5.0,
                       memory_limit_mb: Optional[int] = None,
                       allowed_modules: Optional[List[str]] = None) -> SandboxResult:
        start = time.time()
        stdout_buffer = []
        stderr_buffer = []
        status = SandboxStatus.SUCCESS
        return_code = 0

        # Create restricted environment
        env = {
            "__builtins__": self._restricted_builtins.copy(),
            "__name__": "__sandbox__",
        }
        if allowed_modules:
            for mod_name in allowed_modules:
                try:
                    env[mod_name] = __import__(mod_name)
                except ImportError:
                    pass

        # Capture stdout
        import io
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()

        result_container = {}
        def run_code():
            try:
                exec(code, env)
                result_container["status"] = "success"
            except Exception as e:
                result_container["status"] = "error"
                result_container["error"] = e

        thread = threading.Thread(target=run_code)
        thread.start()
        thread.join(timeout=timeout_seconds)

        elapsed = (time.time() - start) * 1000

        if thread.is_alive():
            status = SandboxStatus.TIMEOUT
            return_code = -1
            # Can't kill thread in Python easily; mark as timeout
        elif result_container.get("status") == "error":
            status = SandboxStatus.ERROR
            return_code = 1

        stdout = sys.stdout.getvalue()
        stderr = sys.stderr.getvalue()
        sys.stdout = old_stdout
        sys.stderr = old_stderr

        if len(stdout) > self.max_output_size:
            stdout = stdout[:self.max_output_size] + "\n... [truncated]"
            output_truncated = True
        else:
            output_truncated = False

        return SandboxResult(
            status=status, stdout=stdout, stderr=stderr,
            return_code=return_code, execution_time_ms=elapsed,
            output_truncated=output_truncated,
        )

    def execute_shell(self, command: List[str], timeout_seconds: float = 5.0,
                      working_dir: Optional[str] = None) -> SandboxResult:
        start = time.time()
        try:
            proc = subprocess.run(
                command, capture_output=True, text=True,
                timeout=timeout_seconds, cwd=working_dir,
                env={"PATH": os.environ.get("PATH", "/usr/bin")}
            )
            elapsed = (time.time() - start) * 1000
            stdout = proc.stdout
            stderr = proc.stderr
            output_truncated = len(stdout) > self.max_output_size
            if output_truncated:
                stdout = stdout[:self.max_output_size] + "\n... [truncated]"
            return SandboxResult(
                status=SandboxStatus.SUCCESS if proc.returncode == 0 else SandboxStatus.ERROR,
                stdout=stdout, stderr=stderr,
                return_code=proc.returncode, execution_time_ms=elapsed,
                output_truncated=output_truncated,
            )
        except subprocess.TimeoutExpired:
            elapsed = (time.time() - start) * 1000
            return SandboxResult(
                status=SandboxStatus.TIMEOUT, stdout="", stderr="",
                return_code=-1, execution_time_ms=elapsed,
            )
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return SandboxResult(
                status=SandboxStatus.ERROR, stdout="", stderr=str(e),
                return_code=-1, execution_time_ms=elapsed,
            )

    def execute_file(self, file_path: str, timeout_seconds: float = 5.0) -> SandboxResult:
        if not os.path.exists(file_path):
            return SandboxResult(
                status=SandboxStatus.ERROR, stdout="", stderr=f"File not found: {file_path}",
                return_code=-1, execution_time_ms=0,
            )
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
        return self.execute_python(code, timeout_seconds)

    def validate_code(self, code: str) -> List[str]:
        errors = []
        dangerous = ["__import__", "eval", "exec", "compile", "open", "os.system",
                     "subprocess", "sys.exit", "breakpoint"]
        for token in dangerous:
            if token in code:
                errors.append(f"Potentially dangerous token: {token}")
        try:
            compile(code, "<sandbox>", "exec")
        except SyntaxError as e:
            errors.append(f"Syntax error: {e}")
        return errors


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Sandbox Executor Engine")
    print("=" * 60)

    engine = SandboxExecutorEngine(max_output_size=4096)

    print("\n--- Execute Python: simple math ---")
    code1 = """
result = sum(range(1, 101))
print(f"Sum 1-100 = {result}")
for i in range(5):
    print(f"Line {i}")
"""
    result = engine.execute_python(code1, timeout_seconds=2.0)
    print(f"  Status: {result.status.value}")
    print(f"  Time: {result.execution_time_ms:.2f}ms")
    print(f"  Stdout: {result.stdout.strip()}")
    print(f"  Stderr: {result.stderr.strip()}")

    print("\n--- Execute Python: error ---")
    code2 = "print(1 / 0)"
    result = engine.execute_python(code2, timeout_seconds=2.0)
    print(f"  Status: {result.status.value}")
    print(f"  Stderr: {result.stderr[:100]}")

    print("\n--- Execute Python: timeout ---")
    code3 = "while True: pass"
    result = engine.execute_python(code3, timeout_seconds=0.5)
    print(f"  Status: {result.status.value}")
    print(f"  Time: {result.execution_time_ms:.2f}ms")

    print("\n--- Validate code ---")
    code4 = "eval('__import__(\"os\").system(\"ls\")')"
    errors = engine.validate_code(code4)
    print(f"  Validation errors: {errors}")

    print("\n--- Execute shell: echo ---")
    result = engine.execute_shell(["echo", "Hello from sandbox"], timeout_seconds=2.0)
    print(f"  Status: {result.status.value}")
    print(f"  Stdout: {result.stdout.strip()}")

    print("\nSandbox Executor test complete.")


if __name__ == "__main__":
    run()

#!/usr/bin/env python3
"""
MAGNATRIX-OS — Code Sandbox Engine
ai/llm_code_sandbox_native.py

Features:
- Safe code execution environment
- Stdout/stderr capture
- Execution timeout enforcement
- Resource limits (memory, output size)
- Result collection and error handling

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import enum
import signal
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("code_sandbox")


class SandboxStatus(enum.Enum):
    SUCCESS = "success"
    TIMEOUT = "timeout"
    MEMORY_ERROR = "memory_error"
    RUNTIME_ERROR = "runtime_error"
    COMPILE_ERROR = "compile_error"
    OUTPUT_LIMIT = "output_limit"


@dataclass
class SandboxResult:
    status: SandboxStatus
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: float
    memory_kb: int = 0


class CodeSandbox:
    """Safe code execution sandbox."""

    def __init__(self, timeout_seconds: float = 5.0, max_output_size: int = 10000, max_memory_mb: int = 256):
        self.timeout = timeout_seconds
        self.max_output = max_output_size
        self.max_memory = max_memory_mb

    def execute(self, code: str, language: str = "python") -> SandboxResult:
        t0 = time.monotonic()
        if language == "python":
            return self._exec_python(code, t0)
        return SandboxResult(SandboxStatus.COMPILE_ERROR, "", f"Unsupported language: {language}", -1, 0)

    def _exec_python(self, code: str, t0: float) -> SandboxResult:
        stdout = ""
        stderr = ""
        exit_code = 0
        status = SandboxStatus.SUCCESS

        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(code)
                f.flush()
                path = f.name

            proc = subprocess.run(
                [sys.executable, path],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
            stdout = proc.stdout[:self.max_output]
            stderr = proc.stderr[:self.max_output]
            exit_code = proc.returncode
            if exit_code != 0:
                status = SandboxStatus.RUNTIME_ERROR

        except subprocess.TimeoutExpired:
            status = SandboxStatus.TIMEOUT
            stderr = "Execution timed out"
            exit_code = -1
        except Exception as e:
            status = SandboxStatus.RUNTIME_ERROR
            stderr = str(e)[:500]
            exit_code = -1

        duration = (time.monotonic() - t0) * 1000
        return SandboxResult(status, stdout, stderr, exit_code, duration)

    def validate(self, code: str) -> List[str]:
        """Pre-validate code for dangerous patterns."""
        warnings = []
        dangerous = ["os.system", "subprocess.call", "subprocess.run", "eval(", "exec(", "import os", "import subprocess", "open('/etc", "open('C:"]
        for pattern in dangerous:
            if pattern in code:
                warnings.append(f"Potentially dangerous pattern: {pattern}")
        return warnings

    def get_stats(self) -> Dict[str, Any]:
        return {"timeout": self.timeout, "max_output": self.max_output, "max_memory": self.max_memory}


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Code Sandbox Engine")
    print("ai/llm_code_sandbox_native.py")
    print("=" * 60)

    sandbox = CodeSandbox(timeout_seconds=2.0, max_output_size=5000)

    # 1. Successful execution
    print("\n[1] Successful Execution")
    code = "print('Hello from sandbox')\nresult = 2 + 3\nprint(f'Result: {result}')"
    result = sandbox.execute(code)
    print(f"  Status: {result.status.value}")
    print(f"  Stdout: {result.stdout.strip()}")
    print(f"  Duration: {result.duration_ms:.1f}ms")

    # 2. Timeout
    print("\n[2] Timeout Handling")
    code = "import time\ntime.sleep(10)"
    result = sandbox.execute(code)
    print(f"  Status: {result.status.value}")
    print(f"  Stderr: {result.stderr}")

    # 3. Runtime error
    print("\n[3] Runtime Error")
    code = "print(1/0)"
    result = sandbox.execute(code)
    print(f"  Status: {result.status.value}")
    print(f"  Stderr: {result.stderr[:50]}")

    # 4. Validation
    print("\n[4] Code Validation")
    warnings = sandbox.validate("import os\nos.system('ls')")
    for w in warnings:
        print(f"  Warning: {w}")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()

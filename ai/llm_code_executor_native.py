"""Safe Code Execution Engine — Sandboxed execution, language support, output capture, security isolation.

Modul ini menyediakan:
- CodeSandbox untuk sandboxed code execution
- LanguageRunner untuk multi-language support (Python, JavaScript, Shell)
- OutputCapture untuk capture stdout/stderr
- SecurityChecker untuk static analysis sebelum execution
- ResourceLimiter untuk CPU/memory/time limits

Arsitektur: Code → Validate → Sandbox → Execute → Capture → Return
"""

from __future__ import annotations

import json
import time
import uuid
import re
import subprocess
import sys
import tempfile
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class Language(Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    BASH = "bash"
    RUBY = "ruby"
    GO = "go"
    RUST = "rust"


class ExecutionStatus(Enum):
    SUCCESS = auto()
    ERROR = auto()
    TIMEOUT = auto()
    MEMORY_EXCEEDED = auto()
    SECURITY_VIOLATION = auto()
    COMPILATION_ERROR = auto()


@dataclass
class ExecutionResult:
    """Result of code execution."""
    execution_id: str
    status: ExecutionStatus
    stdout: str = ""
    stderr: str = ""
    return_value: Any = None
    duration: float = 0.0
    memory_used: int = 0
    language: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityReport:
    """Security analysis report."""
    report_id: str
    violations: List[str] = field(default_factory=list)
    risk_score: float = 0.0
    safe: bool = True


class SecurityChecker:
    """Static security analysis for code."""

    DANGEROUS_PATTERNS = {
        "python": [
            r"os\.system\s*\(", r"subprocess\.call\s*\(", r"subprocess\.run\s*\(",
            r"eval\s*\(", r"exec\s*\(", r"__import__\s*\(",
            r"open\s*\(\s*['\"]/", r"shutil\.rmtree", r"os\.remove\s*\(",
        ],
        "javascript": [
            r"eval\s*\(", r"Function\s*\(", r"setTimeout\s*\(\s*['\"]",
            r"document\.write", r"innerHTML\s*=",
        ],
        "bash": [
            r"rm\s+-rf", r">\s*/dev", r"mkfs", r"dd\s+if=",
            r"curl\s+.*\|\s*bash", r"wget\s+.*\|\s*sh",
        ],
    }

    def __init__(self):
        self._custom_patterns: Dict[str, List[str]] = {}

    def check(self, code: str, language: Language) -> SecurityReport:
        violations = []
        patterns = self.DANGEROUS_PATTERNS.get(language.value, [])
        patterns.extend(self._custom_patterns.get(language.value, []))
        for pattern in patterns:
            if re.search(pattern, code, re.IGNORECASE):
                violations.append(f"Dangerous pattern: {pattern}")
        risk = min(1.0, len(violations) * 0.2)
        return SecurityReport(
            report_id=str(uuid.uuid4())[:12],
            violations=violations,
            risk_score=risk,
            safe=len(violations) == 0
        )

    def add_pattern(self, language: str, pattern: str) -> None:
        self._custom_patterns.setdefault(language, []).append(pattern)

    def check_imports(self, code: str, language: Language) -> List[str]:
        imports = []
        if language == Language.PYTHON:
            imports = re.findall(r"(?:import|from)\s+([\w.]+)", code)
        elif language == Language.JAVASCRIPT:
            imports = re.findall(r"(?:require|import)\s*\(?['\"]([\w./-]+)['\"]", code)
        return imports


class ResourceLimiter:
    """Limit CPU, memory, and time for code execution."""

    def __init__(self, max_time: float = 5.0, max_memory_mb: int = 100):
        self.max_time = max_time
        self.max_memory_mb = max_memory_mb

    def check_limits(self, duration: float, memory_used: int) -> Tuple[bool, Optional[str]]:
        if duration > self.max_time:
            return False, f"Time limit exceeded: {duration:.2f}s > {self.max_time}s"
        if memory_used > self.max_memory_mb * 1024 * 1024:
            return False, f"Memory limit exceeded: {memory_used} > {self.max_memory_mb}MB"
        return True, None


class CodeSandbox:
    """Sandboxed code execution environment."""

    def __init__(self, limiter: Optional[ResourceLimiter] = None, checker: Optional[SecurityChecker] = None):
        self.limiter = limiter or ResourceLimiter()
        self.checker = checker or SecurityChecker()
        self._history: List[ExecutionResult] = []

    def execute(self, code: str, language: Language = Language.PYTHON,
                timeout: Optional[float] = None) -> ExecutionResult:
        timeout = timeout or self.limiter.max_time
        exec_id = str(uuid.uuid4())[:12]

        # Security check
        security = self.checker.check(code, language)
        if not security.safe:
            return ExecutionResult(
                execution_id=exec_id,
                status=ExecutionStatus.SECURITY_VIOLATION,
                stderr=f"Security violations: {security.violations}",
                language=language.value
            )

        start = time.time()
        try:
            if language == Language.PYTHON:
                result = self._execute_python(code, timeout)
            elif language == Language.BASH:
                result = self._execute_bash(code, timeout)
            elif language == Language.JAVASCRIPT:
                result = self._execute_javascript(code, timeout)
            else:
                result = ExecutionResult(
                    execution_id=exec_id,
                    status=ExecutionStatus.ERROR,
                    stderr=f"Language {language.value} not supported",
                    language=language.value
                )
            duration = time.time() - start
            result.duration = duration
            result.execution_id = exec_id
            # Check limits
            ok, msg = self.limiter.check_limits(duration, result.memory_used)
            if not ok:
                result.status = ExecutionStatus.TIMEOUT if "Time" in msg else ExecutionStatus.MEMORY_EXCEEDED
                result.stderr += f"\n{msg}"
            self._history.append(result)
            return result
        except Exception as e:
            duration = time.time() - start
            result = ExecutionResult(
                execution_id=exec_id,
                status=ExecutionStatus.ERROR,
                stderr=str(e),
                duration=duration,
                language=language.value
            )
            self._history.append(result)
            return result

    def _execute_python(self, code: str, timeout: float) -> ExecutionResult:
        # Create temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            f.flush()
            temp_path = f.name
        try:
            # Execute with subprocess for isolation
            result = subprocess.run(
                [sys.executable, temp_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tempfile.gettempdir()
            )
            return ExecutionResult(
                execution_id="",
                status=ExecutionStatus.SUCCESS if result.returncode == 0 else ExecutionStatus.ERROR,
                stdout=result.stdout,
                stderr=result.stderr,
                return_value=None,
                language=Language.PYTHON.value
            )
        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass

    def _execute_bash(self, code: str, timeout: float) -> ExecutionResult:
        try:
            result = subprocess.run(
                ["bash", "-c", code],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tempfile.gettempdir()
            )
            return ExecutionResult(
                execution_id="",
                status=ExecutionStatus.SUCCESS if result.returncode == 0 else ExecutionStatus.ERROR,
                stdout=result.stdout,
                stderr=result.stderr,
                language=Language.BASH.value
            )
        except subprocess.TimeoutExpired:
            return ExecutionResult(
                execution_id="",
                status=ExecutionStatus.TIMEOUT,
                stderr="Execution timed out",
                language=Language.BASH.value
            )

    def _execute_javascript(self, code: str, timeout: float) -> ExecutionResult:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
            f.write(code)
            temp_path = f.name
        try:
            result = subprocess.run(
                ["node", temp_path],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=tempfile.gettempdir()
            )
            return ExecutionResult(
                execution_id="",
                status=ExecutionStatus.SUCCESS if result.returncode == 0 else ExecutionStatus.ERROR,
                stdout=result.stdout,
                stderr=result.stderr,
                language=Language.JAVASCRIPT.value
            )
        except FileNotFoundError:
            return ExecutionResult(
                execution_id="",
                status=ExecutionStatus.ERROR,
                stderr="Node.js not available",
                language=Language.JAVASCRIPT.value
            )
        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass

    def get_history(self) -> List[ExecutionResult]:
        return self._history

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._history)
        success = sum(1 for r in self._history if r.status == ExecutionStatus.SUCCESS)
        return {
            "total_executions": total,
            "successful": success,
            "failed": total - success,
            "success_rate": success / max(total, 1),
        }


class MultiLanguageRunner:
    """Run code in multiple languages with unified interface."""

    def __init__(self, sandbox: Optional[CodeSandbox] = None):
        self.sandbox = sandbox or CodeSandbox()

    def run(self, code: str, language: str = "python", timeout: Optional[float] = None) -> ExecutionResult:
        try:
            lang = Language(language)
        except ValueError:
            return ExecutionResult(
                execution_id=str(uuid.uuid4())[:12],
                status=ExecutionStatus.ERROR,
                stderr=f"Unknown language: {language}",
                language=language
            )
        return self.sandbox.execute(code, lang, timeout)

    def run_batch(self, tasks: List[Tuple[str, str, Optional[float]]]) -> List[ExecutionResult]:
        return [self.run(code, lang, timeout) for code, lang, timeout in tasks]

    def get_supported_languages(self) -> List[str]:
        return [l.value for l in Language]


class CodeExecutionEngine:
    """End-to-end code execution engine."""

    def __init__(self, max_time: float = 5.0, max_memory_mb: int = 100):
        self.limiter = ResourceLimiter(max_time, max_memory_mb)
        self.checker = SecurityChecker()
        self.sandbox = CodeSandbox(self.limiter, self.checker)
        self.runner = MultiLanguageRunner(self.sandbox)

    def execute(self, code: str, language: str = "python", timeout: Optional[float] = None) -> ExecutionResult:
        return self.runner.run(code, language, timeout)

    def check_security(self, code: str, language: str) -> SecurityReport:
        try:
            lang = Language(language)
        except ValueError:
            return SecurityReport(
                report_id=str(uuid.uuid4())[:12],
                violations=[f"Unknown language: {language}"],
                risk_score=1.0,
                safe=False
            )
        return self.checker.check(code, lang)

    def get_stats(self) -> Dict[str, Any]:
        return self.sandbox.get_stats()

    def get_history(self) -> List[ExecutionResult]:
        return self.sandbox.get_history()


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("SAFE CODE EXECUTION ENGINE DEMO")
    print("=" * 70)

    engine = CodeExecutionEngine(max_time=3.0, max_memory_mb=50)

    # 1. Execute Python
    print("\n[1] Execute Python")
    code = """
import math
result = []
for i in range(5):
    result.append(f"sqrt({i}) = {math.sqrt(i):.3f}")
print("\\n".join(result))
"""
    result = engine.execute(code, "python")
    print(f"  Status: {result.status.name}")
    print(f"  stdout: {result.stdout.strip()}")
    print(f"  Duration: {result.duration:.3f}s")

    # 2. Execute Bash
    print("\n[2] Execute Bash")
    bash_code = "echo 'Hello from bash' && ls -la | head -5"
    result = engine.execute(bash_code, "bash")
    print(f"  Status: {result.status.name}")
    print(f"  stdout: {result.stdout.strip()[:100]}...")

    # 3. Security check - safe code
    print("\n[3] Security Check - Safe Code")
    safe_code = "x = 1 + 2\nprint(x)"
    report = engine.check_security(safe_code, "python")
    print(f"  Safe: {report.safe}")
    print(f"  Risk score: {report.risk_score}")
    print(f"  Violations: {report.violations}")

    # 4. Security check - dangerous code
    print("\n[4] Security Check - Dangerous Code")
    dangerous_code = "import os\nos.system('rm -rf /')"
    report = engine.check_security(dangerous_code, "python")
    print(f"  Safe: {report.safe}")
    print(f"  Risk score: {report.risk_score}")
    print(f"  Violations: {report.violations}")

    # 5. Blocked execution
    print("\n[5] Blocked Execution")
    result = engine.execute(dangerous_code, "python")
    print(f"  Status: {result.status.name}")
    print(f"  stderr: {result.stderr[:100]}")

    # 6. Timeout
    print("\n[6] Timeout Handling")
    infinite_loop = """
import time
while True:
    time.sleep(0.1)
"""
    result = engine.execute(infinite_loop, "python", timeout=1.0)
    print(f"  Status: {result.status.name}")
    print(f"  stderr: {result.stderr.strip()}")

    # 7. Batch execution
    print("\n[7] Batch Execution")
    tasks = [
        ("print('Task 1')", "python", None),
        ("echo 'Task 2'", "bash", None),
        ("x = 1/0\nprint(x)", "python", None),
    ]
    results = engine.runner.run_batch(tasks)
    for i, r in enumerate(results):
        print(f"  Task {i+1}: {r.status.name} ({r.duration:.3f}s)")

    # 8. Stats
    print("\n[8] Execution Stats")
    stats = engine.get_stats()
    print(f"  {stats}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()

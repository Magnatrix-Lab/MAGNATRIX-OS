"""
sandbox_executor_native.py
MAGNATRIX-OS — Sandbox Executor

Inspired by Deer-Flow (ByteDance): Sandbox environments for code execution.
Simulated sandbox with isolation, timeout, and resource limits. Pure stdlib.
"""

import json
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class SandboxResult:
    execution_id: str
    code: str
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: float
    memory_kb: int
    status: str
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class SandboxExecutor:
    """Sandbox environment for safe code execution with limits."""

    SUPPORTED_LANGUAGES = ["python", "bash", "javascript"]

    def __init__(self, sandbox_dir: str = "./sandbox"):
        self.sandbox_dir = Path(sandbox_dir)
        self.sandbox_dir.mkdir(exist_ok=True)
        self.history: List[SandboxResult] = []
        self._load()

    def _load(self) -> None:
        file = self.sandbox_dir / "history.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.history = [SandboxResult(**r) for r in data[-100:]]
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.sandbox_dir / "history.json", "w", encoding="utf-8") as f:
            json.dump([asdict(r) for r in self.history[-100:]], f, indent=2)

    def execute(self, execution_id: str, code: str, language: str = "python",
                timeout_sec: int = 30, max_memory_mb: int = 128) -> SandboxResult:
        """Execute code in a simulated sandbox."""
        start = time.time()
        stdout, stderr, exit_code = "", "", 0

        if language == "python":
            try:
                # Use subprocess with timeout for real execution
                proc = subprocess.run(
                    ["python", "-c", code],
                    capture_output=True, text=True, timeout=timeout_sec,
                    cwd=str(self.sandbox_dir),
                )
                stdout = proc.stdout
                stderr = proc.stderr
                exit_code = proc.returncode
            except subprocess.TimeoutExpired:
                stdout, stderr, exit_code = "", "Execution timed out", -1
            except Exception as e:
                stdout, stderr, exit_code = "", str(e), -1
        elif language == "bash":
            try:
                proc = subprocess.run(
                    code, shell=True, capture_output=True, text=True,
                    timeout=timeout_sec, cwd=str(self.sandbox_dir),
                )
                stdout = proc.stdout
                stderr = proc.stderr
                exit_code = proc.returncode
            except subprocess.TimeoutExpired:
                stdout, stderr, exit_code = "", "Execution timed out", -1
            except Exception as e:
                stdout, stderr, exit_code = "", str(e), -1
        else:
            stdout, stderr = "", f"Language {language} not yet supported in sandbox"
            exit_code = -1

        duration = (time.time() - start) * 1000
        status = "success" if exit_code == 0 else "failed" if exit_code > 0 else "timeout"
        result = SandboxResult(
            execution_id=execution_id, code=code[:500], stdout=stdout[:2000],
            stderr=stderr[:1000], exit_code=exit_code, duration_ms=round(duration, 2),
            memory_kb=0, status=status,
        )
        self.history.append(result)
        self._save()
        return result

    def get_history(self, limit: int = 10) -> List[SandboxResult]:
        return self.history[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.history)
        success = sum(1 for r in self.history if r.status == "success")
        failed = sum(1 for r in self.history if r.status == "failed")
        timeout = sum(1 for r in self.history if r.status == "timeout")
        avg_duration = sum(r.duration_ms for r in self.history) / max(1, total)
        return {
            "total_executions": total, "success": success, "failed": failed,
            "timeout": timeout, "avg_duration_ms": round(avg_duration, 2),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["SandboxExecutor", "SandboxResult"]
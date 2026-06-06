#!/usr/bin/env python3
"""
Process Manager for MAGNATRIX-OS
Subprocess execution, process monitoring, signal handling,
output capture, and resource limit enforcement. Native stdlib only.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import enum
import os
import signal
import subprocess
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple


class ProcessStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    KILLED = "killed"


@dataclasses.dataclass
class ProcessResult:
    command: str
    status: ProcessStatus
    returncode: int
    stdout: str
    stderr: str
    pid: int
    start_time: float
    end_time: float
    duration_ms: float
    killed_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command": self.command,
            "status": self.status.value,
            "returncode": self.returncode,
            "stdout": self.stdout[:500] if len(self.stdout) > 500 else self.stdout,
            "stderr": self.stderr[:500] if len(self.stderr) > 500 else self.stderr,
            "pid": self.pid,
            "duration_ms": self.duration_ms,
        }


class ProcessManager:
    """Subprocess execution manager with monitoring and limits."""

    def __init__(self, default_timeout: float = 30.0, max_output_size: int = 10 * 1024 * 1024) -> None:
        self.default_timeout = default_timeout
        self.max_output_size = max_output_size
        self._processes: Dict[int, subprocess.Popen] = {}
        self._results: List[ProcessResult] = []
        self._lock = threading.Lock()
        self._hooks: List[Callable[[ProcessResult], None]] = []

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def run(
        self,
        command: List[str],
        timeout: Optional[float] = None,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
        capture_output: bool = True,
        shell: bool = False,
    ) -> ProcessResult:
        start = time.time()
        timeout = timeout or self.default_timeout
        try:
            proc = subprocess.Popen(
                command,
                stdout=subprocess.PIPE if capture_output else None,
                stderr=subprocess.PIPE if capture_output else None,
                text=True,
                env=env,
                cwd=cwd,
                shell=shell,
                preexec_fn=os.setsid if hasattr(os, "setsid") else None,
            )
            with self._lock:
                self._processes[proc.pid] = proc
            try:
                stdout, stderr = proc.communicate(timeout=timeout)
                if stdout and len(stdout.encode()) > self.max_output_size:
                    stdout = stdout[:self.max_output_size]
                if stderr and len(stderr.encode()) > self.max_output_size:
                    stderr = stderr[:self.max_output_size]
                end = time.time()
                result = ProcessResult(
                    command=" ".join(command),
                    status=ProcessStatus.COMPLETED if proc.returncode == 0 else ProcessStatus.FAILED,
                    returncode=proc.returncode or 0,
                    stdout=stdout or "",
                    stderr=stderr or "",
                    pid=proc.pid,
                    start_time=start,
                    end_time=end,
                    duration_ms=round((end - start) * 1000, 2),
                )
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                end = time.time()
                result = ProcessResult(
                    command=" ".join(command),
                    status=ProcessStatus.TIMEOUT,
                    returncode=-1,
                    stdout=proc.stdout.read() if proc.stdout else "",
                    stderr=proc.stderr.read() if proc.stderr else "",
                    pid=proc.pid,
                    start_time=start,
                    end_time=end,
                    duration_ms=round((end - start) * 1000, 2),
                    killed_by="timeout",
                )
        except Exception as e:
            end = time.time()
            result = ProcessResult(
                command=" ".join(command),
                status=ProcessStatus.FAILED,
                returncode=-1,
                stdout="",
                stderr=str(e),
                pid=-1,
                start_time=start,
                end_time=end,
                duration_ms=round((end - start) * 1000, 2),
            )
        finally:
            with self._lock:
                self._processes.pop(proc.pid, None)
            self._results.append(result)
            for hook in self._hooks:
                try:
                    hook(result)
                except Exception:
                    pass
        return result

    # ------------------------------------------------------------------
    # Process control
    # ------------------------------------------------------------------

    def kill(self, pid: int, force: bool = False) -> bool:
        with self._lock:
            proc = self._processes.get(pid)
        if not proc:
            return False
        try:
            if force:
                proc.kill()
            else:
                proc.terminate()
            proc.wait(timeout=5)
            return True
        except Exception:
            return False

    def kill_all(self, force: bool = False) -> int:
        with self._lock:
            pids = list(self._processes.keys())
        killed = 0
        for pid in pids:
            if self.kill(pid, force):
                killed += 1
        return killed

    def signal_send(self, pid: int, sig: int) -> bool:
        with self._lock:
            proc = self._processes.get(pid)
        if not proc:
            try:
                os.kill(pid, sig)
                return True
            except Exception:
                return False
        try:
            proc.send_signal(sig)
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Monitoring
    # ------------------------------------------------------------------

    def list_running(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [{"pid": pid, "poll": p.poll()} for pid, p in self._processes.items()]

    def is_running(self, pid: int) -> bool:
        with self._lock:
            proc = self._processes.get(pid)
        return proc is not None and proc.poll() is None

    def get_result(self, index: int = -1) -> Optional[ProcessResult]:
        if self._results and -len(self._results) <= index < len(self._results):
            return self._results[index]
        return None

    def add_hook(self, hook: Callable[[ProcessResult], None]) -> None:
        self._hooks.append(hook)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        by_status = {}
        for r in self._results:
            by_status[r.status.value] = by_status.get(r.status.value, 0) + 1
        return {
            "total_executed": len(self._results),
            "currently_running": len(self._processes),
            "by_status": by_status,
            "avg_duration_ms": round(sum(r.duration_ms for r in self._results) / max(1, len(self._results)), 2),
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    pm = ProcessManager(default_timeout=5.0)
    print("=== Process Manager Demo ===\n")
    # Successful command
    result = pm.run(["echo", "Hello from MAGNATRIX-OS"])
    print(f"echo: {result.status.value} (pid={result.pid}, {result.duration_ms}ms)")
    print(f"  stdout: {result.stdout.strip()}")
    # Failed command
    result = pm.run(["false"])
    print(f"\nfalse: {result.status.value} (code={result.returncode})")
    # Timeout command
    result = pm.run(["sleep", "10"], timeout=1.0)
    print(f"sleep 10 (timeout 1s): {result.status.value} ({result.duration_ms}ms)")
    # Stats
    print(f"\nStats: {pm.stats()}")


if __name__ == "__main__":
    _demo()

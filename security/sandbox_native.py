#!/usr/bin/env python3
"""
================================================================================
MAGNATRIX-OS — Sandbox Engine (Layer 9 Extension)
Sandboxed Code Execution with Resource Limits, FS Jail, Network Jail
================================================================================
Zero-dependency sandbox using subprocess + resource limits + tempdirs.
================================================================================
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import resource
import signal
import subprocess
import tempfile
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


# =============================================================================
# Constants
# =============================================================================
DEFAULT_MAX_MEMORY_MB = 256
DEFAULT_MAX_CPU_SEC = 5.0
DEFAULT_MAX_PROCESSES = 4
DEFAULT_MAX_FILE_SIZE_MB = 10
SANDBOX_TEMP_PREFIX = "magnatrix_sandbox_"


# =============================================================================
# Data Types
# =============================================================================
@dataclass
class SandboxResult:
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: float
    memory_peak_mb: float
    sandbox_id: str
    violations: List[str] = field(default_factory=list)


@dataclass
class SandboxPolicy:
    max_memory_mb: int = DEFAULT_MAX_MEMORY_MB
    max_cpu_sec: float = DEFAULT_MAX_CPU_SEC
    max_processes: int = DEFAULT_MAX_PROCESSES
    max_file_size_mb: int = DEFAULT_MAX_FILE_SIZE_MB
    allow_network: bool = False
    allow_filesystem_write: bool = False
    allowed_paths: List[str] = field(default_factory=list)
    blocked_syscalls: List[int] = field(default_factory=list)
    env_vars: Dict[str, str] = field(default_factory=dict)


# =============================================================================
# Resource Limiter
# =============================================================================
class ResourceLimiter:
    """Apply POSIX resource limits before exec."""

    @staticmethod
    def apply(policy: SandboxPolicy) -> None:
        # Memory (address space)
        max_bytes = policy.max_memory_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (max_bytes, max_bytes))
        # CPU time
        resource.setrlimit(resource.RLIMIT_CPU, (int(policy.max_cpu_sec), int(policy.max_cpu_sec) + 1))
        # Number of processes
        resource.setrlimit(resource.RLIMIT_NPROC, (policy.max_processes, policy.max_processes))
        # File size
        max_fsize = policy.max_file_size_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_FSIZE, (max_fsize, max_fsize))
        # Core dump = 0
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


# =============================================================================
# File System Jail
# =============================================================================
class FileSystemJail:
    """Create chroot-like temp environment for sandboxed code."""

    def __init__(self, base_dir: Optional[str] = None) -> None:
        self.base_dir = Path(base_dir or tempfile.mkdtemp(prefix=SANDBOX_TEMP_PREFIX))
        self._created_dirs: List[Path] = []

    def setup(self, policy: SandboxPolicy) -> Path:
        for sub in ("bin", "lib", "tmp", "home", "work"):
            d = self.base_dir / sub
            d.mkdir(parents=True, exist_ok=True)
            self._created_dirs.append(d)
        # Copy minimal Python if running python scripts
        return self.base_dir / "work"

    def write_script(self, filename: str, content: str) -> Path:
        path = self.base_dir / "work" / filename
        path.write_text(content, encoding="utf-8")
        return path

    def read_output(self, filename: str) -> str:
        path = self.base_dir / "work" / filename
        if path.exists():
            return path.read_text(encoding="utf-8")
        return ""

    def cleanup(self) -> None:
        import shutil
        shutil.rmtree(self.base_dir, ignore_errors=True)


# =============================================================================
# Network Jail
# =============================================================================
class NetworkJail:
    """Block network via firewall rules or LD_PRELOAD shim (stub)."""

    @staticmethod
    def is_available() -> bool:
        return platform.system() == "Linux"

    @staticmethod
    def apply() -> None:
        """Stub: real implementation would use iptables/nftables or network namespace."""
        pass

    @staticmethod
    def lift() -> None:
        pass


# =============================================================================
# Seccomp Filter (Stub)
# =============================================================================
class SeccompFilterStub:
    """Placeholder for seccomp-bpf system call filtering."""

    def __init__(self, blocked: List[int] = None) -> None:
        self.blocked = blocked or []

    def install(self) -> bool:
        """Returns False — real seccomp requires native extension."""
        return False

    def to_preload_env(self) -> Dict[str, str]:
        return {}


# =============================================================================
# Namespace Isolation (Stub)
# =============================================================================
class NamespaceIsolationStub:
    """Placeholder for PID/UTS/IPC/MOUNT namespace isolation."""

    @staticmethod
    def is_available() -> bool:
        return os.getuid() == 0 and platform.system() == "Linux"

    @staticmethod
    def unshare_flags() -> int:
        """Return clone flags for namespace isolation."""
        return 0


# =============================================================================
# Process Spawner
# =============================================================================
class ProcessSpawner:
    """Spawn sandboxed subprocess with pre_exec limiter."""

    def __init__(self, policy: SandboxPolicy) -> None:
        self.policy = policy

    def spawn(self, cmd: List[str], cwd: str = ".", env: Optional[Dict[str, str]] = None) -> subprocess.Popen:
        def preexec() -> None:
            ResourceLimiter.apply(self.policy)
            if not self.policy.allow_network:
                NetworkJail.apply()
        merged_env = {**os.environ, **self.policy.env_vars}
        if env:
            merged_env.update(env)
        return subprocess.Popen(
            cmd,
            cwd=cwd,
            env=merged_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=preexec,
        )


# =============================================================================
# Syscall Interceptor (Stub)
# =============================================================================
class SyscallInterceptorStub:
    """Placeholder for ptrace-based syscall interception."""

    @staticmethod
    def is_available() -> bool:
        return platform.system() == "Linux"

    def trace(self, pid: int, allowed: List[int]) -> None:
        pass


# =============================================================================
# Sandbox Kernel Bridge
# =============================================================================
class SandboxKernelBridge:
    def __init__(self, event_bus: Any = None) -> None:
        self.bus = event_bus

    def emit(self, sandbox_id: str, result: SandboxResult) -> None:
        if self.bus:
            self.bus.publish("sandbox.completed", {
                "sandbox_id": sandbox_id,
                "success": result.success,
                "duration_ms": result.duration_ms,
                "violations": result.violations,
            })


# =============================================================================
# Main Sandbox Engine
# =============================================================================
class SandboxEngine:
    """Orchestrates sandboxed execution of arbitrary code."""

    def __init__(self, policy: Optional[SandboxPolicy] = None) -> None:
        self.policy = policy or SandboxPolicy()
        self.bridge = SandboxKernelBridge()
        self._running = False
        self._lock = threading.Lock()
        self._active: Dict[str, subprocess.Popen] = {}

    def _generate_id(self) -> str:
        return hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]

    def run_python(self, code: str, timeout: Optional[float] = None) -> SandboxResult:
        sid = self._generate_id()
        jail = FileSystemJail()
        work = jail.setup(self.policy)
        script_path = jail.write_script("__sandbox__.py", code)
        spawner = ProcessSpawner(self.policy)
        t0 = time.perf_counter()
        try:
            proc = spawner.spawn(
                ["python3", str(script_path)],
                cwd=str(work),
                env={"PYTHONDONTWRITEBYTECODE": "1", "PYTHONNOUSERSITE": "1"},
            )
            with self._lock:
                self._active[sid] = proc
            to = timeout or self.policy.max_cpu_sec + 2.0
            try:
                stdout, stderr = proc.communicate(timeout=to)
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()
                violations = ["TIMEOUT"]
            else:
                violations = []
            duration_ms = (time.perf_counter() - t0) * 1000
            mem_mb = 0.0  # Would read from /proc/{pid}/status on Linux
            result = SandboxResult(
                success=proc.returncode == 0 and not violations,
                stdout=stdout.decode("utf-8", errors="replace")[:4096],
                stderr=stderr.decode("utf-8", errors="replace")[:4096],
                exit_code=proc.returncode,
                duration_ms=duration_ms,
                memory_peak_mb=mem_mb,
                sandbox_id=sid,
                violations=violations,
            )
        except Exception as exc:
            result = SandboxResult(
                success=False,
                stdout="",
                stderr=str(exc),
                exit_code=-1,
                duration_ms=(time.perf_counter() - t0) * 1000,
                memory_peak_mb=0.0,
                sandbox_id=sid,
                violations=["SPAWN_ERROR"],
            )
        finally:
            with self._lock:
                self._active.pop(sid, None)
            jail.cleanup()
        self.bridge.emit(sid, result)
        return result

    def run_shell(self, command: str, timeout: Optional[float] = None) -> SandboxResult:
        sid = self._generate_id()
        jail = FileSystemJail()
        work = jail.setup(self.policy)
        script_path = jail.write_script("__cmd__.sh", command)
        spawner = ProcessSpawner(self.policy)
        t0 = time.perf_counter()
        try:
            proc = spawner.spawn(
                ["/bin/sh", str(script_path)],
                cwd=str(work),
            )
            with self._lock:
                self._active[sid] = proc
            to = timeout or self.policy.max_cpu_sec + 2.0
            try:
                stdout, stderr = proc.communicate(timeout=to)
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()
                violations = ["TIMEOUT"]
            else:
                violations = []
            duration_ms = (time.perf_counter() - t0) * 1000
            result = SandboxResult(
                success=proc.returncode == 0 and not violations,
                stdout=stdout.decode("utf-8", errors="replace")[:4096],
                stderr=stderr.decode("utf-8", errors="replace")[:4096],
                exit_code=proc.returncode,
                duration_ms=duration_ms,
                memory_peak_mb=0.0,
                sandbox_id=sid,
                violations=violations,
            )
        except Exception as exc:
            result = SandboxResult(
                success=False,
                stdout="",
                stderr=str(exc),
                exit_code=-1,
                duration_ms=(time.perf_counter() - t0) * 1000,
                memory_peak_mb=0.0,
                sandbox_id=sid,
                violations=["SPAWN_ERROR"],
            )
        finally:
            with self._lock:
                self._active.pop(sid, None)
            jail.cleanup()
        self.bridge.emit(sid, result)
        return result

    def kill(self, sandbox_id: str) -> bool:
        with self._lock:
            proc = self._active.get(sandbox_id)
        if proc:
            proc.kill()
            return True
        return False

    def list_active(self) -> List[str]:
        with self._lock:
            return list(self._active.keys())

    def shutdown(self) -> None:
        self._running = False
        with self._lock:
            for proc in list(self._active.values()):
                try:
                    proc.kill()
                except Exception:
                    pass
            self._active.clear()

    def __enter__(self) -> SandboxEngine:
        self._running = True
        return self

    def __exit__(self, *args: Any) -> None:
        self.shutdown()


# =============================================================================
# Demo
# =============================================================================
def run_demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Sandbox Engine Demo")
    print("=" * 60)
    engine = SandboxEngine(SandboxPolicy(max_memory_mb=128, max_cpu_sec=3.0, allow_network=False))
    # Safe Python
    r1 = engine.run_python("print('Hello from sandbox')\nx = sum(range(100))\nprint('sum:', x)")
    print(f"Python sandbox: success={r1.success}, stdout={r1.stdout.strip()}, duration={r1.duration_ms:.1f}ms")
    # CPU limit test
    r2 = engine.run_python("while True: pass", timeout=1.0)
    print(f"CPU timeout test: success={r2.success}, violations={r2.violations}")
    engine.shutdown()
    print("Demo complete.")


if __name__ == "__main__":
    run_demo()

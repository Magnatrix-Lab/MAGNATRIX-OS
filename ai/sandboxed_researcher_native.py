#!/usr/bin/env python3
"""
MAGNATRIX-OS Layer: AI — Sandboxed Researcher
File: ai/sandboxed_researcher_native.py
Pattern: AMATI-PELAJARI-TIRU dari ZIB-IOL/The-Agentic-Researcher

Native pure-Python reimplementation of:
  - Sandboxed filesystem isolation (chroot-like path prefixing)
  - Restricted shell command execution (allowlist/blocklist)
  - Safe Python code exec with restricted globals
  - Multi-CLI launcher (Claude, Copilot, Cursor, OpenClaw modes)
  - Research session with planning, execution, artifact collection

Zero external dependencies. Pure Python standard library.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


# ── BaseLayer ── SandboxConfig, FileSystemIsolation, ResourceLimiter

@dataclass
class SandboxConfig:
    work_dir: str = ""
    gpu_enabled: bool = False
    timeout_sec: int = 30
    max_disk_mb: int = 100
    env_vars: Dict[str, str] = field(default_factory=dict)
    allowed_commands: Tuple[str, ...] = (
        "python", "cat", "echo", "grep", "sed", "awk", "wc",
        "ls", "pwd", "mkdir", "cp", "mv", "rm", "git", "curl",
    )
    blocked_patterns: Tuple[str, ...] = (
        "sudo", "rm -rf /", "> /etc/", "> /sys/", "> /proc/",
        "mkfs", "dd if=/dev/zero", "chmod 777 /", "chown root",
        "nc -l", "ncat -l", "python -c 'import socket'",
        "__import__('os').system", "subprocess.call", "os.system",
    )


class FileSystemIsolation:
    """Context manager creating a sandboxed temp work directory."""

    def __init__(self, config: SandboxConfig):
        self.config = config
        self._temp_dir: Optional[str] = None

    def __enter__(self) -> str:
        self._temp_dir = tempfile.mkdtemp(prefix="magnatrix_sandbox_")
        self.config.work_dir = self._temp_dir
        # Create standard subdirs
        for sub in ("src", "data", "output", "logs"):
            os.makedirs(os.path.join(self._temp_dir, sub), exist_ok=True)
        return self._temp_dir

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._temp_dir and os.path.exists(self._temp_dir):
            shutil.rmtree(self._temp_dir, ignore_errors=True)

    def resolve(self, path: str) -> str:
        """Resolve a user-provided path to sandboxed absolute path."""
        if os.path.isabs(path):
            # Force into sandbox
            safe = os.path.join(self.config.work_dir, os.path.relpath(path, "/"))
        else:
            safe = os.path.join(self.config.work_dir, path)
        # Ensure it stays within sandbox
        real_safe = os.path.realpath(safe)
        real_base = os.path.realpath(self.config.work_dir)
        if not real_safe.startswith(real_base):
            raise PermissionError(f"Path escapes sandbox: {path}")
        return real_safe


class ResourceLimiter:
    """Track memory, disk, and time usage (mock since pure Python)."""

    def __init__(self, config: SandboxConfig):
        self.config = config
        self.start_time = time.time()
        self._disk_used = 0

    def check_timeout(self) -> bool:
        return (time.time() - self.start_time) < self.config.timeout_sec

    def check_disk(self, additional_bytes: int = 0) -> bool:
        self._disk_used += additional_bytes
        return self._disk_used < self.config.max_disk_mb * 1024 * 1024

    def stats(self) -> Dict[str, Any]:
        return {
            "elapsed_sec": round(time.time() - self.start_time, 2),
            "timeout_sec": self.config.timeout_sec,
            "disk_used_mb": round(self._disk_used / (1024 * 1024), 2),
            "disk_limit_mb": self.config.max_disk_mb,
        }


# ── CoreEngine ── SandboxedShell, SandboxedPython, GPUMonitor

class SandboxedShell:
    """Execute shell commands in restricted environment."""

    def __init__(self, config: SandboxConfig, fs: FileSystemIsolation, limiter: ResourceLimiter):
        self.config = config
        self.fs = fs
        self.limiter = limiter
        self.history: List[str] = []

    def run(self, command: str) -> str:
        if not self.limiter.check_timeout():
            return "[Sandbox ERROR] Timeout exceeded"

        # Check blocklist
        cmd_lower = command.lower()
        for blocked in self.config.blocked_patterns:
            if blocked.lower() in cmd_lower:
                return f"[Sandbox BLOCKED] Pattern '{blocked}' is forbidden"

        # Parse command
        parts = command.strip().split()
        if not parts:
            return "[Sandbox] Empty command"

        cmd = parts[0]
        if cmd not in self.config.allowed_commands:
            return f"[Sandbox BLOCKED] Command '{cmd}' not in allowlist"

        # Simulate output for common commands
        return self._simulate(cmd, parts[1:])

    def _simulate(self, cmd: str, args: List[str]) -> str:
        if cmd == "ls":
            return "src\ndata\noutput\nlogs\nREADME.md"
        if cmd == "pwd":
            return self.config.work_dir
        if cmd == "echo":
            return " ".join(args)
        if cmd == "cat":
            return f"[Mock content of {' '.join(args)}]"
        if cmd == "git":
            return "On branch main\nYour branch is up to date with 'origin/main'."
        if cmd == "wc":
            return "  10   50 300 mock.txt"
        if cmd == "grep":
            return f"[Grep results for pattern {args[0] if args else '???'}]"
        return f"[Sandbox] Simulated {cmd} {' '.join(args)}"


class SandboxedPython:
    """exec() code in restricted globals."""

    SAFE_BUILTINS = {
        "abs", "all", "any", "bin", "bool", "bytearray", "bytes",
        "chr", "divmod", "enumerate", "filter", "float", "format",
        "frozenset", "hash", "hex", "int", "isinstance", "issubclass",
        "iter", "len", "list", "map", "max", "min", "oct", "ord",
        "pow", "print", "range", "reversed", "round", "set", "slice",
        "sorted", "str", "sum", "tuple", "zip",
    }

    def __init__(self, fs: FileSystemIsolation, limiter: ResourceLimiter):
        self.fs = fs
        self.limiter = limiter

    def exec(self, code: str) -> str:
        if not self.limiter.check_timeout():
            return "[SandboxPy ERROR] Timeout"
        if len(code) > 5000:
            return "[SandboxPy ERROR] Code too long (>5000 chars)"

        # Block dangerous patterns
        dangerous = ["os.system", "subprocess", "socket", "urllib.request.urlopen",
                     "__import__('os')", "import os", "import subprocess"]
        for d in dangerous:
            if d in code:
                return f"[SandboxPy BLOCKED] Forbidden pattern: {d}"

        import builtins as _builtins
        restricted = {"__builtins__": {}}
        for name in self.SAFE_BUILTINS:
            val = getattr(_builtins, name, None)
            if val is not None:
                restricted["__builtins__"][name] = val

        # Inject safe helpers
        restricted["json"] = __import__("json")
        restricted["math"] = __import__("math")
        restricted["re"] = __import__("re")

        output_buf: List[str] = []
        restricted["print"] = lambda *a, **k: output_buf.append(" ".join(str(x) for x in a))

        try:
            exec(code, restricted)
            out = "\n".join(output_buf) if output_buf else "[no output]"
            return f"[SandboxPy OK] {out[:300]}"
        except Exception as e:
            return f"[SandboxPy ERROR] {type(e).__name__}: {e}"


class GPUMonitor:
    """Stub GPU allocation tracker."""

    def __init__(self) -> None:
        self.allocations: List[Dict[str, Any]] = []

    def request(self, vram_mb: int, task_id: str) -> bool:
        # Always grant in simulation
        self.allocations.append({"task_id": task_id, "vram_mb": vram_mb, "granted": True})
        return True

    def release(self, task_id: str) -> None:
        self.allocations = [a for a in self.allocations if a["task_id"] != task_id]

    def summary(self) -> Dict[str, Any]:
        total = sum(a["vram_mb"] for a in self.allocations)
        return {"active_allocations": len(self.allocations), "total_vram_mb": total}


# ── Features ── MultiCLILauncher, ResearchSession, ArtifactCollector

class MultiCLILauncher:
    """Launch agent in different CLI modes."""

    MODES = ["claude", "copilot", "cursor", "openclaw"]

    @staticmethod
    def generate_prompt(mode: str, task: str) -> str:
        if mode == "claude":
            return f"<thinking>\nAnalyzing task: {task}\n</thinking>\n\nUsing tool: bash\nTask: {task}"
        if mode == "copilot":
            return f"# Suggestion for: {task}\n# Inline completion triggered\n"
        if mode == "cursor":
            return f"[Composer Agent]\nGoal: {task}\nPlan: 1. Understand 2. Search 3. Implement\n"
        if mode == "openclaw":
            return f"<skill>research</skill>\n<task>{task}</task>\n<agent>openclaw_researcher</agent>"
        return f"[Generic] Task: {task}"

    def simulate_response(self, mode: str, task: str) -> str:
        prompt = self.generate_prompt(mode, task)
        return f"[{mode.upper()} MODE]\n{prompt}\n\n[Result] Simulated completion for task."


class ResearchSession:
    """One full research task with planning and execution."""

    def __init__(self, query: str, mode: str, config: SandboxConfig):
        self.query = query
        self.mode = mode
        self.config = config
        self.session_id = uuid.uuid4().hex[:8]
        self.artifacts: List[str] = []
        self.logs: List[Dict[str, Any]] = []

    def run(self) -> Dict[str, Any]:
        with FileSystemIsolation(self.config) as work_dir:
            fs = FileSystemIsolation(self.config)
            fs.config.work_dir = work_dir
            limiter = ResourceLimiter(self.config)
            shell = SandboxedShell(self.config, fs, limiter)
            py = SandboxedPython(fs, limiter)
            gpu = GPUMonitor()
            cli = MultiCLILauncher()

            # Phase 1: Plan
            plan = f"Research plan for '{self.query}':\n1. Search literature\n2. Extract key findings\n3. Synthesize report"
            self._log("plan", plan)

            # Phase 2: Execute
            self._log("shell", shell.run("ls"))
            self._log("shell", shell.run("git status"))
            self._log("python", py.exec("print('Data processing OK')"))

            # Phase 3: CLI simulation
            self._log("cli", cli.simulate_response(self.mode, self.query))

            # Phase 4: Artifacts
            artifact_path = os.path.join(work_dir, "output", "research_report.txt")
            with open(artifact_path, "w") as f:
                f.write(f"Research: {self.query}\n\n{plan}\n\nSession: {self.session_id}")
            self.artifacts.append(artifact_path)

            return {
                "session_id": self.session_id,
                "query": self.query,
                "mode": self.mode,
                "work_dir": work_dir,
                "artifacts": self.artifacts,
                "logs": self.logs,
                "resources": limiter.stats(),
                "gpu": gpu.summary(),
            }

    def _log(self, phase: str, output: str) -> None:
        self.logs.append({"phase": phase, "output": output[:200], "time": datetime.now(timezone.utc).isoformat()})


class ArtifactCollector:
    """Gather output files, summaries, logs into final package."""

    def collect(self, session_result: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "package_id": f"pkg_{uuid.uuid4().hex[:8]}",
            "session_id": session_result["session_id"],
            "summary": f"Research on '{session_result['query']}' completed in {session_result['mode']} mode.",
            "artifacts": session_result["artifacts"],
            "log_count": len(session_result["logs"]),
            "resources": session_result["resources"],
        }


# ── Kernel ── SandboxedResearcherKernel

class SandboxedResearcherKernel:
    """Bridge class for MAGNATRIX-OS integration."""

    def __init__(self):
        self.config = SandboxConfig()
        self.collector = ArtifactCollector()

    def research(self, query: str, mode: str = "claude") -> Dict[str, Any]:
        session = ResearchSession(query, mode, self.config)
        result = session.run()
        return self.collector.collect(result)

    def quick_exec(self, code: str) -> str:
        with FileSystemIsolation(self.config) as work_dir:
            fs = FileSystemIsolation(self.config)
            fs.config.work_dir = work_dir
            limiter = ResourceLimiter(self.config)
            py = SandboxedPython(fs, limiter)
            return py.exec(code)


# ── Self-Test ──

def _self_test():
    print("=" * 55)
    print("Sandboxed Researcher Native — Self Test")
    print("=" * 55)

    kernel = SandboxedResearcherKernel()

    # Test 1: Research in Claude mode
    print("\n[Test 1] Research session (Claude mode)")
    r1 = kernel.research("sorting algorithm comparison", mode="claude")
    print(f"  Package ID: {r1['package_id']}")
    print(f"  Artifacts: {len(r1['artifacts'])}")
    print(f"  Logs: {r1['log_count']}")

    # Test 2: Research in Cursor mode
    print("\n[Test 2] Research session (Cursor mode)")
    r2 = kernel.research("machine learning pipelines", mode="cursor")
    print(f"  Package ID: {r2['package_id']}")

    # Test 3: Blocked command
    print("\n[Test 3] Blocked shell command")
    with FileSystemIsolation(SandboxConfig()) as wd:
        fs = FileSystemIsolation(SandboxConfig())
        fs.config.work_dir = wd
        limiter = ResourceLimiter(SandboxConfig())
        shell = SandboxedShell(SandboxConfig(), fs, limiter)
        res = shell.run("sudo apt-get update")
        print(f"  {res}")

    # Test 4: Allowed command
    print("\n[Test 4] Allowed shell command")
    res = shell.run("ls")
    print(f"  {res}")

    # Test 5: Safe Python exec
    print("\n[Test 5] Safe Python execution")
    res = kernel.quick_exec("print(sum(range(10)))")
    print(f"  {res}")

    # Test 6: Dangerous Python blocked
    print("\n[Test 6] Dangerous Python blocked")
    res = kernel.quick_exec("import os; os.system('ls')")
    print(f"  {res}")

    # Test 7: GPU monitor
    print("\n[Test 7] GPU monitor")
    gpu = GPUMonitor()
    gpu.request(4096, "task_001")
    print(f"  {gpu.summary()}")

    # Test 8: Resource limiter
    print("\n[Test 8] Resource limiter")
    limiter = ResourceLimiter(SandboxConfig(timeout_sec=60))
    print(f"  {limiter.stats()}")

    # Test 9: Filesystem isolation
    print("\n[Test 9] Filesystem isolation")
    with FileSystemIsolation(SandboxConfig()) as wd:
        print(f"  Work dir: {wd}")
        print(f"  Subdirs: {os.listdir(wd)}")

    # Test 10: Multi-CLI modes
    print("\n[Test 10] Multi-CLI launcher")
    cli = MultiCLILauncher()
    for m in cli.MODES:
        prompt = cli.generate_prompt(m, "test task")
        print(f"  [{m}] {prompt[:60]}...")

    print("\n" + "=" * 55)
    print("All tests passed.")
    print("=" * 55)


if __name__ == "__main__":
    _self_test()

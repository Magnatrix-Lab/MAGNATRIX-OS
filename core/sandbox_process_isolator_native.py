"""Sandbox Process Isolator — PID namespace simulation, fork/wrap."""
from dataclasses import dataclass
from pathlib import Path
import json, os, time, subprocess

@dataclass
class IsolatedProcess:
    pid: int = 0
    command: str = ""
    status: str = "pending"  # pending | running | finished | killed
    exit_code: int | None = None
    start_time: float = 0.0
    end_time: float = 0.0

class SandboxProcessIsolator:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._processes: dict[int, IsolatedProcess] = {}
        self._next_pid = 1000
        self._persist_path = self.root / "sandbox_processes.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._processes = {int(k): IsolatedProcess(**v) for k, v in data.get("processes", {}).items()}
            self._next_pid = data.get("next_pid", 1000)

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "processes": {k: v.__dict__ for k, v in self._processes.items()},
            "next_pid": self._next_pid
        }, indent=2))

    def spawn(self, command: str, env: dict | None = None) -> IsolatedProcess:
        pid = self._next_pid
        self._next_pid += 1
        proc = IsolatedProcess(pid=pid, command=command, status="running", start_time=time.time())
        self._processes[pid] = proc
        self._save()
        return proc

    def terminate(self, pid: int) -> bool:
        proc = self._processes.get(pid)
        if proc and proc.status == "running":
            proc.status = "killed"
            proc.end_time = time.time()
            proc.exit_code = -9
            self._save()
            return True
        return False

    def wait(self, pid: int) -> IsolatedProcess | None:
        proc = self._processes.get(pid)
        if proc and proc.status == "running":
            proc.status = "finished"
            proc.end_time = time.time()
            proc.exit_code = 0
            self._save()
        return proc

    def list_active(self) -> list[IsolatedProcess]:
        return [p for p in self._processes.values() if p.status == "running"]

    def to_dict(self) -> dict:
        return {"process_count": len(self._processes), "active": len(self.list_active())}

    def get_stats(self) -> dict:
        return {"total": len(self._processes), "active": len(self.list_active()), "killed": sum(1 for p in self._processes.values() if p.status == "killed")}

__all__ = ["SandboxProcessIsolator", "IsolatedProcess"]

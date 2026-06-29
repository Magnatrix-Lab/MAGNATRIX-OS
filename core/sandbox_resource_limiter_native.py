"""Sandbox Resource Limiter — CPU, memory, fd limits."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class ResourceLimits:
    cpu_time_ms: int = 0
    memory_mb: int = 0
    file_size_mb: int = 0
    open_fds: int = 0
    stack_size_mb: int = 0

class SandboxResourceLimiter:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._limits: dict[str, ResourceLimits] = {}
        self._violations: list[dict] = []
        self._persist_path = self.root / "sandbox_limits.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._limits = {k: ResourceLimits(**v) for k, v in data.get("limits", {}).items()}
            self._violations = data.get("violations", [])

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "limits": {k: v.__dict__ for k, v in self._limits.items()},
            "violations": self._violations
        }, indent=2))

    def set_limits(self, sandbox_id: str, cpu_ms: int = 1000, memory_mb: int = 64, file_size_mb: int = 10, open_fds: int = 32, stack_mb: int = 8) -> ResourceLimits:
        limits = ResourceLimits(cpu_time_ms=cpu_ms, memory_mb=memory_mb, file_size_mb=file_size_mb, open_fds=open_fds, stack_size_mb=stack_mb)
        self._limits[sandbox_id] = limits
        self._save()
        return limits

    def check(self, sandbox_id: str, cpu_used_ms: int, mem_used_mb: int, fd_used: int, file_size_mb: int) -> list[str]:
        limits = self._limits.get(sandbox_id)
        if not limits:
            return []
        violations = []
        if limits.cpu_time_ms > 0 and cpu_used_ms > limits.cpu_time_ms:
            violations.append("cpu")
        if limits.memory_mb > 0 and mem_used_mb > limits.memory_mb:
            violations.append("memory")
        if limits.open_fds > 0 and fd_used > limits.open_fds:
            violations.append("fds")
        if limits.file_size_mb > 0 and file_size_mb > limits.file_size_mb:
            violations.append("file_size")
        if violations:
            self._violations.append({"sandbox": sandbox_id, "violations": violations, "cpu": cpu_used_ms, "mem": mem_used_mb})
            self._save()
        return violations

    def get_limits(self, sandbox_id: str) -> ResourceLimits | None:
        return self._limits.get(sandbox_id)

    def to_dict(self) -> dict:
        return {"sandbox_count": len(self._limits), "violation_count": len(self._violations)}

    def get_stats(self) -> dict:
        return {"sandboxes": len(self._limits), "violations": len(self._violations)}

__all__ = ["SandboxResourceLimiter", "ResourceLimits"]

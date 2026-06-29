"""Sandbox Seccomp Simulator — Syscall filter simulation."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class SyscallRule:
    syscall: str = ""
    action: str = "allow"  # allow | block | log
    args_filter: list[dict] = None

    def __post_init__(self):
        if self.args_filter is None:
            self.args_filter = []

class SandboxSeccompSimulator:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._rules: list[SyscallRule] = []
        self._default_action: str = "block"
        self._audit_log: list[dict] = []
        self._persist_path = self.root / "sandbox_seccomp.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._rules = [SyscallRule(**r) for r in data.get("rules", [])]
            self._default_action = data.get("default_action", "block")
            self._audit_log = data.get("audit_log", [])

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "rules": [r.__dict__ for r in self._rules],
            "default_action": self._default_action,
            "audit_log": self._audit_log
        }, indent=2))

    def allow(self, syscall: str) -> None:
        self._rules.append(SyscallRule(syscall=syscall, action="allow"))
        self._save()

    def block(self, syscall: str) -> None:
        self._rules.append(SyscallRule(syscall=syscall, action="block"))
        self._save()

    def log(self, syscall: str) -> None:
        self._rules.append(SyscallRule(syscall=syscall, action="log"))
        self._save()

    def evaluate(self, syscall: str, args: list = None) -> str:
        for rule in self._rules:
            if rule.syscall == syscall:
                self._audit_log.append({"syscall": syscall, "action": rule.action, "args": args})
                self._save()
                return rule.action
        self._audit_log.append({"syscall": syscall, "action": self._default_action, "args": args})
        self._save()
        return self._default_action

    def set_default(self, action: str) -> None:
        self._default_action = action
        self._save()

    def to_dict(self) -> dict:
        return {"rule_count": len(self._rules), "default": self._default_action, "audit_entries": len(self._audit_log)}

    def get_stats(self) -> dict:
        actions = {}
        for r in self._rules:
            actions[r.action] = actions.get(r.action, 0) + 1
        return {"rules": len(self._rules), "actions": actions, "audit_entries": len(self._audit_log)}

__all__ = ["SandboxSeccompSimulator", "SyscallRule"]

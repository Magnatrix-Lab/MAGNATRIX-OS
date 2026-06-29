"""Sandbox File System Guard — Path allowlist, read/write restriction."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class FSGuardRule:
    path: str = ""
    access: str = "read"  # read | write | readwrite | none
    recursive: bool = True

class SandboxFileSystemGuard:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._rules: list[FSGuardRule] = []
        self._temp_dirs: list[str] = []
        self._log: list[dict] = []
        self._persist_path = self.root / "sandbox_fsguard.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._rules = [FSGuardRule(**r) for r in data.get("rules", [])]
            self._temp_dirs = data.get("temp_dirs", [])
            self._log = data.get("log", [])

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "rules": [r.__dict__ for r in self._rules],
            "temp_dirs": self._temp_dirs,
            "log": self._log
        }, indent=2))

    def allow(self, path: str, access: str = "readwrite", recursive: bool = True) -> None:
        self._rules.append(FSGuardRule(path=path, access=access, recursive=recursive))
        self._save()

    def set_temp_dir(self, temp_dir: str) -> None:
        self._temp_dirs.append(temp_dir)
        self._rules.append(FSGuardRule(path=temp_dir, access="readwrite", recursive=True))
        self._save()

    def check_access(self, path: str, operation: str) -> bool:
        # Check rules
        for rule in self._rules:
            if Path(rule.path) in Path(path).parents or Path(rule.path) == Path(path):
                if operation in rule.access or rule.access == "readwrite":
                    self._log.append({"path": path, "op": operation, "allowed": True})
                    self._save()
                    return True
                if rule.access == "none":
                    self._log.append({"path": path, "op": operation, "allowed": False})
                    self._save()
                    return False
        # Default deny if no matching rule
        self._log.append({"path": path, "op": operation, "allowed": False})
        self._save()
        return False

    def normalize_path(self, path: str) -> str | None:
        try:
            resolved = str(Path(path).resolve())
            # Check path traversal
            for temp in self._temp_dirs:
                if resolved.startswith(temp):
                    return resolved
            for rule in self._rules:
                if resolved.startswith(rule.path):
                    return resolved
            return None
        except Exception:
            return None

    def to_dict(self) -> dict:
        return {"rule_count": len(self._rules), "temp_dirs": len(self._temp_dirs), "log_entries": len(self._log)}

    def get_stats(self) -> dict:
        return {"rules": len(self._rules), "denied": sum(1 for e in self._log if not e.get("allowed", True)), "allowed": sum(1 for e in self._log if e.get("allowed", False))}

__all__ = ["SandboxFileSystemGuard", "FSGuardRule"]

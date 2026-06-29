"""Sandbox Chroot Manager — Directory isolation simulation."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class ChrootJail:
    jail_id: str = ""
    root_path: str = ""
    bind_mounts: list[dict] = None
    read_only: bool = True

    def __post_init__(self):
        if self.bind_mounts is None:
            self.bind_mounts = []

class SandboxChrootManager:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._jails: dict[str, ChrootJail] = {}
        self._persist_path = self.root / "sandbox_chroot.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._jails = {k: ChrootJail(**v) for k, v in data.get("jails", {}).items()}

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "jails": {k: v.__dict__ for k, v in self._jails.items()}
        }, indent=2))

    def create_jail(self, jail_id: str, root_path: str, read_only: bool = True) -> ChrootJail:
        jail = ChrootJail(jail_id=jail_id, root_path=root_path, read_only=read_only)
        self._jails[jail_id] = jail
        self._save()
        return jail

    def bind_mount(self, jail_id: str, source: str, target: str, ro: bool = True) -> None:
        jail = self._jails.get(jail_id)
        if jail:
            jail.bind_mounts.append({"source": source, "target": target, "ro": ro})
            self._save()

    def resolve_path(self, jail_id: str, path: str) -> str | None:
        jail = self._jails.get(jail_id)
        if not jail:
            return None
        # Simulate chroot resolution
        resolved = Path(jail.root_path) / path.lstrip("/")
        # Check against bind mounts
        for bm in jail.bind_mounts:
            if path.startswith(bm["target"]):
                return bm["source"] + path[len(bm["target"]):]
        return str(resolved)

    def destroy_jail(self, jail_id: str) -> bool:
        if jail_id in self._jails:
            del self._jails[jail_id]
            self._save()
            return True
        return False

    def to_dict(self) -> dict:
        return {"jail_count": len(self._jails)}

    def get_stats(self) -> dict:
        return {"jails": len(self._jails), "read_only": sum(1 for j in self._jails.values() if j.read_only)}

__all__ = ["SandboxChrootManager", "ChrootJail"]

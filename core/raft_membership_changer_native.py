"""Raft Membership Changer — Joint consensus, add/remove nodes."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class MembershipConfig:
    old_servers: list[str] = None
    new_servers: list[str] = None
    joint_consensus: bool = False
    phase: str = "stable"  # stable | joint | finalized

    def __post_init__(self):
        if self.old_servers is None:
            self.old_servers = []
        if self.new_servers is None:
            self.new_servers = []

class RaftMembershipChanger:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self.config = MembershipConfig()
        self._history: list[dict] = []
        self._persist_path = self.root / "raft_membership.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self.config = MembershipConfig(**data.get("config", {}))
            self._history = data.get("history", [])

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "config": self.config.__dict__,
            "history": self._history
        }, indent=2))

    def propose_add(self, node_id: str, current_servers: list[str]) -> None:
        self.config.old_servers = list(current_servers)
        self.config.new_servers = list(current_servers) + [node_id]
        self.config.joint_consensus = True
        self.config.phase = "joint"
        self._history.append({"action": "add", "node": node_id})
        self._save()

    def propose_remove(self, node_id: str, current_servers: list[str]) -> None:
        self.config.old_servers = list(current_servers)
        self.config.new_servers = [s for s in current_servers if s != node_id]
        self.config.joint_consensus = True
        self.config.phase = "joint"
        self._history.append({"action": "remove", "node": node_id})
        self._save()

    def finalize(self) -> None:
        if self.config.joint_consensus:
            self.config.old_servers = list(self.config.new_servers)
            self.config.joint_consensus = False
            self.config.phase = "finalized"
            self._save()

    def quorum(self) -> int:
        if self.config.joint_consensus:
            return max(len(self.config.old_servers), len(self.config.new_servers)) // 2 + 1
        return len(self.config.new_servers) // 2 + 1 if self.config.new_servers else 1

    def to_dict(self) -> dict:
        return self.config.__dict__

    def get_stats(self) -> dict:
        return {"phase": self.config.phase, "old_count": len(self.config.old_servers), "new_count": len(self.config.new_servers), "quorum": self.quorum()}

__all__ = ["RaftMembershipChanger", "MembershipConfig"]

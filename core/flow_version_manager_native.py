"""
flow_version_manager_native.py
MAGNATRIX-OS — Flow Version Manager

Inspired by langflow-ai/langflow flow versioning:
Version control for flows with diff, rollback, and tagging. Pure stdlib.
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class FlowVersion:
    version_id: str
    flow_id: str
    version_number: int
    snapshot: Dict[str, Any]
    tag: str = ""
    commit_message: str = ""
    created_at: str = ""
    author: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class FlowVersionManager:
    """Version control for flows with diff, rollback, and tagging."""

    def __init__(self, versions_dir: str = "./flow_versions"):
        self.versions_dir = Path(versions_dir)
        self.versions_dir.mkdir(exist_ok=True)
        self.versions: Dict[str, List[FlowVersion]] = {}
        self._load()

    def _load(self) -> None:
        file = self.versions_dir / "versions.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for flow_id, vlist in data.items():
                        self.versions[flow_id] = [FlowVersion(**v) for v in vlist]
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.versions_dir / "versions.json", "w", encoding="utf-8") as f:
            json.dump(
                {fid: [asdict(v) for v in vlist] for fid, vlist in self.versions.items()}, f, indent=2,
            )

    def _hash_snapshot(self, snapshot: Dict[str, Any]) -> str:
        return hashlib.md5(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()[:8]

    def save_version(self, flow_id: str, snapshot: Dict[str, Any], tag: str = "",
                     commit_message: str = "", author: str = "") -> FlowVersion:
        versions = self.versions.setdefault(flow_id, [])
        version_num = len(versions) + 1
        version_id = f"{flow_id}_v{version_num}"
        version = FlowVersion(
            version_id=version_id, flow_id=flow_id, version_number=version_num,
            snapshot=snapshot, tag=tag, commit_message=commit_message, author=author,
        )
        versions.append(version)
        self._save()
        return version

    def get_version(self, flow_id: str, version_number: int) -> Optional[FlowVersion]:
        versions = self.versions.get(flow_id, [])
        for v in versions:
            if v.version_number == version_number:
                return v
        return None

    def get_latest(self, flow_id: str) -> Optional[FlowVersion]:
        versions = self.versions.get(flow_id, [])
        return versions[-1] if versions else None

    def rollback(self, flow_id: str, version_number: int) -> Optional[Dict[str, Any]]:
        version = self.get_version(flow_id, version_number)
        if version:
            return version.snapshot
        return None

    def diff(self, flow_id: str, v1: int, v2: int) -> Dict[str, Any]:
        version1 = self.get_version(flow_id, v1)
        version2 = self.get_version(flow_id, v2)
        if not version1 or not version2:
            return {"error": "Version not found"}
        snap1 = json.dumps(version1.snapshot, sort_keys=True)
        snap2 = json.dumps(version2.snapshot, sort_keys=True)
        return {
            "from": v1, "to": v2, "changed": snap1 != snap2,
            "hash_v1": self._hash_snapshot(version1.snapshot),
            "hash_v2": self._hash_snapshot(version2.snapshot),
        }

    def list_versions(self, flow_id: str) -> List[FlowVersion]:
        return self.versions.get(flow_id, [])

    def tag_version(self, flow_id: str, version_number: int, tag: str) -> bool:
        version = self.get_version(flow_id, version_number)
        if version:
            version.tag = tag
            self._save()
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        total = sum(len(v) for v in self.versions.values())
        return {"total_versions": total, "flows_tracked": len(self.versions)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["FlowVersionManager", "FlowVersion"]
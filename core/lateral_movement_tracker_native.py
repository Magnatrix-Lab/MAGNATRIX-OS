"""
lateral_movement_tracker_native.py
MAGNATRIX-OS — Lateral Movement Tracker

Inspired by AbyssSec red team operations:
Track and simulate lateral movement paths across a network. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class LateralHop:
    hop_id: str
    from_host: str
    to_host: str
    technique: str
    credentials: str
    success: bool
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


@dataclass
class LateralPath:
    path_id: str
    entry_point: str
    hops: List[LateralHop] = field(default_factory=list)
    target: str = ""
    status: str = "in_progress"


class LateralMovementTracker:
    """Track and simulate lateral movement paths across a network."""

    TECHNIQUES = ["psexec", "wmi", "winrm", "ssh", "rdp", "smb", "pass_the_hash", "kerberoast"]

    def __init__(self, tracker_dir: str = "./lateral_movement"):
        self.tracker_dir = Path(tracker_dir)
        self.tracker_dir.mkdir(exist_ok=True)
        self.paths: Dict[str, LateralPath] = {}
        self._load()

    def _load(self) -> None:
        file = self.tracker_dir / "paths.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for pid, pd in data.items():
                        pd["hops"] = [LateralHop(**h) for h in pd.get("hops", [])]
                        self.paths[pid] = LateralPath(**pd)
            except Exception:
                pass

    def _save(self) -> None:
        out = {}
        for pid, p in self.paths.items():
            d = asdict(p)
            d["hops"] = [asdict(h) for h in p.hops]
            out[pid] = d
        with open(self.tracker_dir / "paths.json", "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)

    def create_path(self, path_id: str, entry_point: str, target: str) -> LateralPath:
        path = LateralPath(path_id=path_id, entry_point=entry_point, target=target)
        self.paths[path_id] = path
        self._save()
        return path

    def add_hop(self, path_id: str, hop_id: str, from_host: str, to_host: str,
                technique: str, credentials: str, success: bool = True) -> bool:
        path = self.paths.get(path_id)
        if not path:
            return False
        hop = LateralHop(
            hop_id=hop_id, from_host=from_host, to_host=to_host,
            technique=technique, credentials=credentials, success=success,
        )
        path.hops.append(hop)
        self._save()
        return True

    def complete_path(self, path_id: str) -> bool:
        path = self.paths.get(path_id)
        if not path:
            return False
        path.status = "completed"
        self._save()
        return True

    def get_path(self, path_id: str) -> Optional[LateralPath]:
        return self.paths.get(path_id)

    def get_paths(self) -> List[LateralPath]:
        return list(self.paths.values())

    def get_hops_from(self, host: str) -> List[LateralHop]:
        return [h for p in self.paths.values() for h in p.hops if h.from_host == host]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.paths)
        total_hops = sum(len(p.hops) for p in self.paths.values())
        successful = sum(1 for p in self.paths.values() for h in p.hops if h.success)
        return {"paths": total, "hops": total_hops, "successful_hops": successful}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["LateralMovementTracker", "LateralPath", "LateralHop"]
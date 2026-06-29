"""
worktree_isolation_manager_native.py
MAGNATRIX-OS — Worktree Isolation Manager

Inspired by gajae-code: Git worktree isolation for concurrent tasks. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class Worktree:
    worktree_id: str
    branch_name: str
    path: str
    task_id: str
    is_active: bool
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class WorktreeIsolationManager:
    """Manage Git worktree isolation for concurrent tasks."""

    def __init__(self, cache_dir: str = "./worktrees"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.worktrees: Dict[str, Worktree] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "worktrees.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for wid, wd in data.items():
                        self.worktrees[wid] = Worktree(**wd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "worktrees.json", "w", encoding="utf-8") as f:
            json.dump({wid: asdict(w) for wid, w in self.worktrees.items()}, f, indent=2)

    def create_worktree(self, worktree_id: str, branch_name: str, path: str, task_id: str) -> Worktree:
        wt = Worktree(
            worktree_id=worktree_id, branch_name=branch_name, path=path,
            task_id=task_id, is_active=True,
        )
        self.worktrees[worktree_id] = wt
        self._save()
        return wt

    def deactivate(self, worktree_id: str) -> bool:
        wt = self.worktrees.get(worktree_id)
        if wt:
            wt.is_active = False
            self._save()
            return True
        return False

    def get_for_task(self, task_id: str) -> List[Worktree]:
        return [w for w in self.worktrees.values() if w.task_id == task_id]

    def get_active(self) -> List[Worktree]:
        return [w for w in self.worktrees.values() if w.is_active]

    def get_stats(self) -> Dict[str, Any]:
        active = sum(1 for w in self.worktrees.values() if w.is_active)
        return {"total_worktrees": len(self.worktrees), "active": active}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["WorktreeIsolationManager", "Worktree"]
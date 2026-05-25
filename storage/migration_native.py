#!/usr/bin/env python3
"""
storage/migration_native.py
===========================
Storage Schema Migration System

Manages versioned storage schemas with forward/backward migration scripts.
Prevents data loss on version upgrades.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional


@dataclass
class Migration:
    from_version: int
    to_version: int
    name: str
    up: Callable[[], None]
    down: Optional[Callable[[], None]] = None


class MigrationManager:
    """Track and execute storage migrations."""

    def __init__(self, state_file: str = "/var/lib/magnatrix/schema_version.json") -> None:
        self.state_file = state_file
        self._migrations: Dict[int, Migration] = {}
        os.makedirs(os.path.dirname(state_file), exist_ok=True)

    def register(self, migration: Migration) -> None:
        self._migrations[migration.from_version] = migration

    @property
    def current_version(self) -> int:
        if os.path.exists(self.state_file):
            with open(self.state_file, "r") as f:
                return json.load(f).get("version", 0)
        return 0

    def _save_version(self, version: int) -> None:
        with open(self.state_file, "w") as f:
            json.dump({"version": version, "last_migration": self._migrations.get(version - 1, Migration(0, 0, "", lambda: None)).name}, f)

    def migrate(self, target_version: int) -> List[str]:
        """Migrate forward to target_version. Returns list of applied migrations."""
        current = self.current_version
        applied: List[str] = []
        while current < target_version:
            m = self._migrations.get(current)
            if not m:
                raise ValueError(f"No migration path from v{current} to v{current + 1}")
            m.up()
            current = m.to_version
            self._save_version(current)
            applied.append(m.name)
        return applied

    def rollback(self, target_version: int) -> List[str]:
        """Rollback to target_version."""
        current = self.current_version
        rolled: List[str] = []
        while current > target_version:
            m = self._migrations.get(current - 1)
            if not m or not m.down:
                raise ValueError(f"No rollback path from v{current} to v{current - 1}")
            m.down()
            current = m.from_version
            self._save_version(current)
            rolled.append(m.name)
        return rolled

"""LLM Migration Runner — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum, auto

class MigrationStatus(Enum):
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    ROLLED_BACK = auto()

@dataclass
class Migration:
    id: str
    version: str
    description: str
    up: Callable[[], None]
    down: Optional[Callable[[], None]] = None
    status: MigrationStatus = MigrationStatus.PENDING
    error: Optional[str] = None

class MigrationRunner:
    def __init__(self) -> None:
        self._migrations: List[Migration] = []
        self._completed: List[str] = []

    def add(self, migration: Migration) -> None:
        self._migrations.append(migration)

    def run_all(self) -> Dict[str, Any]:
        results = {}
        for migration in self._migrations:
            if migration.id in self._completed:
                continue
            migration.status = MigrationStatus.RUNNING
            try:
                migration.up()
                migration.status = MigrationStatus.COMPLETED
                self._completed.append(migration.id)
                results[migration.id] = "success"
            except Exception as ex:
                migration.status = MigrationStatus.FAILED
                migration.error = str(ex)
                results[migration.id] = "failed: " + str(ex)
                break
        return results

    def rollback(self, migration_id: str) -> bool:
        for migration in self._migrations:
            if migration.id == migration_id and migration.down:
                try:
                    migration.down()
                    migration.status = MigrationStatus.ROLLED_BACK
                    if migration_id in self._completed:
                        self._completed.remove(migration_id)
                    return True
                except Exception:
                    return False
        return False

    def get_stats(self) -> Dict[str, Any]:
        return {"total": len(self._migrations), "completed": len(self._completed), "failed": sum(1 for m in self._migrations if m.status == MigrationStatus.FAILED)}

def run() -> None:
    print("Migration Runner test")
    e = MigrationRunner()
    e.add(Migration("m1", "1.0", "Create schema", lambda: print("  Schema created")))
    e.add(Migration("m2", "1.1", "Add index", lambda: print("  Index added")))
    e.add(Migration("m3", "1.2", "Add column", lambda: print("  Column added"), lambda: print("  Column removed")))
    results = e.run_all()
    print("  Results: " + str(results))
    e.rollback("m3")
    print("  Stats: " + str(e.get_stats()))
    print("Migration Runner test complete.")

if __name__ == "__main__":
    run()

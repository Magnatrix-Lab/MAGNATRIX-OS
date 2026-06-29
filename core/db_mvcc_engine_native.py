"""DB MVCC Engine -- Multi-version concurrency control, snapshot isolation."""
from dataclasses import dataclass
from pathlib import Path
import json, time

@dataclass
class VersionedRecord:
    key: str = ""
    value: str = ""
    version: int = 0
    tx_id: str = ""
    created_at: float = 0.0
    deleted: bool = False

class DBMVCCengine:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._versions: dict[str, list[VersionedRecord]] = {}
        self._next_version: int = 1
        self._persist_path = self.root / "db_mvcc.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._versions = {k: [VersionedRecord(**r) for r in v] for k, v in data.get("versions", {}).items()}
            self._next_version = data.get("next_version", 1)

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "versions": {k: [r.__dict__ for r in v] for k, v in self._versions.items()},
            "next_version": self._next_version
        }, indent=2))

    def write(self, key: str, value: str, tx_id: str) -> VersionedRecord:
        record = VersionedRecord(
            key=key, value=value, version=self._next_version,
            tx_id=tx_id, created_at=time.time()
        )
        self._next_version += 1
        if key not in self._versions:
            self._versions[key] = []
        self._versions[key].append(record)
        self._save()
        return record

    def read(self, key: str, as_of_version: int = None) -> VersionedRecord | None:
        versions = self._versions.get(key, [])
        if not versions:
            return None
        if as_of_version is None:
            # Return latest non-deleted
            for v in reversed(versions):
                if not v.deleted:
                    return v
            return None
        # Return latest version <= as_of_version
        for v in reversed(versions):
            if v.version <= as_of_version and not v.deleted:
                return v
        return None

    def delete(self, key: str, tx_id: str) -> bool:
        versions = self._versions.get(key)
        if not versions:
            return False
        latest = versions[-1]
        tombstone = VersionedRecord(
            key=key, value=latest.value, version=self._next_version,
            tx_id=tx_id, created_at=time.time(), deleted=True
        )
        self._next_version += 1
        versions.append(tombstone)
        self._save()
        return True

    def get_versions(self, key: str) -> list[VersionedRecord]:
        return self._versions.get(key, [])

    def vacuum(self, key: str, keep_versions: int = 5) -> int:
        versions = self._versions.get(key)
        if not versions or len(versions) <= keep_versions:
            return 0
        removed = len(versions) - keep_versions
        self._versions[key] = versions[-keep_versions:]
        self._save()
        return removed

    def to_dict(self) -> dict:
        total_versions = sum(len(v) for v in self._versions.values())
        return {"key_count": len(self._versions), "total_versions": total_versions}

    def get_stats(self) -> dict:
        total_versions = sum(len(v) for v in self._versions.values())
        deleted = sum(sum(1 for r in v if r.deleted) for v in self._versions.values())
        return {"keys": len(self._versions), "versions": total_versions, "deleted": deleted}

__all__ = ["DBMVCCengine", "VersionedRecord"]

"""DB LSM Tree -- Log-structured merge tree, memtable, SSTable, compaction."""
from dataclasses import dataclass
from pathlib import Path
import json, time

@dataclass
class SSTable:
    table_id: str = ""
    min_key: str = ""
    max_key: str = ""
    entries: list[dict] = None
    level: int = 0
    size_bytes: int = 0

    def __post_init__(self):
        if self.entries is None:
            self.entries = []

class DBLSMTree:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._memtable: dict[str, str] = {}
        self._sstables: list[SSTable] = []
        self._wal: list[dict] = []
        self._memtable_size_limit = 100
        self._persist_path = self.root / "db_lsm.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._memtable = data.get("memtable", {})
            self._sstables = [SSTable(**t) for t in data.get("sstables", [])]
            self._wal = data.get("wal", [])

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "memtable": self._memtable,
            "sstables": [t.__dict__ for t in self._sstables],
            "wal": self._wal
        }, indent=2))

    def put(self, key: str, value: str) -> None:
        self._wal.append({"op": "put", "key": key, "ts": time.time()})
        self._memtable[key] = value
        if len(self._memtable) >= self._memtable_size_limit:
            self._flush()
        self._save()

    def get(self, key: str) -> str | None:
        if key in self._memtable:
            return self._memtable[key]
        for table in sorted(self._sstables, key=lambda t: t.level):
            if table.min_key <= key <= table.max_key:
                for entry in table.entries:
                    if entry["key"] == key:
                        return entry["value"]
        return None

    def delete(self, key: str) -> None:
        self._wal.append({"op": "delete", "key": key, "ts": time.time()})
        self._memtable[key] = "__TOMBSTONE__"
        self._save()

    def _flush(self) -> None:
        if not self._memtable:
            return
        sorted_items = sorted(self._memtable.items())
        entries = [{"key": k, "value": v} for k, v in sorted_items]
        table = SSTable(
            table_id=f"sst_{len(self._sstables)}",
            min_key=sorted_items[0][0],
            max_key=sorted_items[-1][0],
            entries=entries,
            level=0,
            size_bytes=len(json.dumps(entries))
        )
        self._sstables.append(table)
        self._memtable = {}
        self._compact()

    def _compact(self) -> None:
        # Simple compaction: merge Level 0 tables if > 2
        level0 = [t for t in self._sstables if t.level == 0]
        if len(level0) > 2:
            all_entries = []
            for t in level0:
                all_entries.extend(t.entries)
            all_entries.sort(key=lambda e: e["key"])
            # Remove duplicates (keep latest)
            seen = {}
            for e in all_entries:
                seen[e["key"]] = e
            merged = list(seen.values())
            new_table = SSTable(
                table_id=f"sst_{len(self._sstables)}_compact",
                min_key=merged[0]["key"],
                max_key=merged[-1]["key"],
                entries=merged,
                level=1,
                size_bytes=len(json.dumps(merged))
            )
            self._sstables = [t for t in self._sstables if t.level != 0]
            self._sstables.append(new_table)

    def scan(self, start_key: str = "", end_key: str = "") -> list[dict]:
        results = {}
        for k, v in self._memtable.items():
            if v != "__TOMBSTONE__" and (not start_key or k >= start_key) and (not end_key or k <= end_key):
                results[k] = v
        for table in self._sstables:
            for entry in table.entries:
                if entry["value"] != "__TOMBSTONE__" and (not start_key or entry["key"] >= start_key) and (not end_key or entry["key"] <= end_key):
                    results[entry["key"]] = entry["value"]
        return [{"key": k, "value": v} for k, v in sorted(results.items())]

    def to_dict(self) -> dict:
        return {"memtable_size": len(self._memtable), "sstable_count": len(self._sstables)}

    def get_stats(self) -> dict:
        by_level = {}
        for t in self._sstables:
            by_level[t.level] = by_level.get(t.level, 0) + 1
        total_entries = len(self._memtable) + sum(len(t.entries) for t in self._sstables)
        return {"memtable": len(self._memtable), "sstables": len(self._sstables), "by_level": by_level, "total_entries": total_entries}

__all__ = ["DBLSMTree", "SSTable"]

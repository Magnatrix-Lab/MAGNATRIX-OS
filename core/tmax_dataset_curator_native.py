"""TMax Dataset Curator -- TMax-15K style dataset management, filtering, dedup."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class DatasetEntry:
    entry_id: str = ""
    prompt: str = ""
    response: str = ""
    task_id: str = ""
    quality_score: float = 0.0
    source: str = ""
    verified: bool = False
    tags: list[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []

class TmaxDatasetCurator:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._entries: list[DatasetEntry] = []
        self._persist_path = self.root / "tmax_dataset.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._entries = [DatasetEntry(**e) for e in data.get("entries", [])]

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "entries": [e.__dict__ for e in self._entries]
        }, indent=2))

    def add(self, entry_id: str, prompt: str, response: str, task_id: str = "", source: str = "", quality: float = 0.0) -> DatasetEntry:
        entry = DatasetEntry(
            entry_id=entry_id, prompt=prompt, response=response,
            task_id=task_id, source=source, quality_score=quality
        )
        self._entries.append(entry)
        self._save()
        return entry

    def filter_by_quality(self, min_score: float = 0.7) -> list[DatasetEntry]:
        return [e for e in self._entries if e.quality_score >= min_score]

    def filter_by_task(self, task_id: str) -> list[DatasetEntry]:
        return [e for e in self._entries if e.task_id == task_id]

    def deduplicate(self) -> int:
        seen = set()
        unique = []
        for e in self._entries:
            key = e.prompt[:100] + e.response[:100]
            if key not in seen:
                seen.add(key)
                unique.append(e)
        removed = len(self._entries) - len(unique)
        self._entries = unique
        self._save()
        return removed

    def verify(self, entry_id: str) -> bool:
        for e in self._entries:
            if e.entry_id == entry_id:
                e.verified = True
                self._save()
                return True
        return False

    def score(self, entry_id: str, score: float) -> bool:
        for e in self._entries:
            if e.entry_id == entry_id:
                e.quality_score = score
                self._save()
                return True
        return False

    def export(self, path: str) -> int:
        data = [e.__dict__ for e in self._entries]
        Path(path).write_text(json.dumps(data, indent=2))
        return len(data)

    def split(self, train_ratio: float = 0.8) -> tuple[list[DatasetEntry], list[DatasetEntry]]:
        import random
        shuffled = self._entries[:]
        random.shuffle(shuffled)
        split_idx = int(len(shuffled) * train_ratio)
        return shuffled[:split_idx], shuffled[split_idx:]

    def to_dict(self) -> dict:
        return {"entry_count": len(self._entries)}

    def get_stats(self) -> dict:
        by_source = {}
        by_task = {}
        verified = 0
        for e in self._entries:
            by_source[e.source] = by_source.get(e.source, 0) + 1
            by_task[e.task_id] = by_task.get(e.task_id, 0) + 1
            if e.verified:
                verified += 1
        avg_quality = sum(e.quality_score for e in self._entries) / len(self._entries) if self._entries else 0
        return {"entries": len(self._entries), "by_source": by_source, "by_task": by_task, "verified": verified, "avg_quality": round(avg_quality, 2)}

__all__ = ["TmaxDatasetCurator", "DatasetEntry"]

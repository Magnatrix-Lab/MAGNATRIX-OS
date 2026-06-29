"""Vector Batch Inserter — Bulk insert, buffering, flush thresholds."""
from dataclasses import dataclass
from pathlib import Path
import json, time

@dataclass
class BatchInsert:
    batch_id: str = ""
    vectors: list[dict] = None
    status: str = "buffering"  # buffering | flushing | committed
    inserted_at: float = 0.0

    def __post_init__(self):
        if self.vectors is None:
            self.vectors = []

class VectorBatchInserter:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._buffer: list[dict] = []
        self._batches: list[BatchInsert] = []
        self._flush_threshold = 1000
        self._id_map: dict[str, int] = {}
        self._next_id = 1
        self._persist_path = self.root / "vector_batch.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._buffer = data.get("buffer", [])
            self._batches = [BatchInsert(**b) for b in data.get("batches", [])]
            self._id_map = data.get("id_map", {})
            self._next_id = data.get("next_id", 1)

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "buffer": self._buffer,
            "batches": [b.__dict__ for b in self._batches],
            "id_map": self._id_map,
            "next_id": self._next_id
        }, indent=2))

    def add(self, vector: list[float], external_id: str = "", metadata: dict = None) -> int:
        internal_id = self._next_id
        self._next_id += 1
        self._id_map[external_id or str(internal_id)] = internal_id
        entry = {"id": internal_id, "vector": vector, "metadata": metadata or {}, "added_at": time.time()}
        self._buffer.append(entry)
        if len(self._buffer) >= self._flush_threshold:
            self.flush()
        self._save()
        return internal_id

    def flush(self) -> BatchInsert:
        if not self._buffer:
            return BatchInsert(batch_id="empty")
        batch = BatchInsert(batch_id=f"batch_{len(self._batches)}", vectors=list(self._buffer), status="committed", inserted_at=time.time())
        self._batches.append(batch)
        self._buffer = []
        self._save()
        return batch

    def get_id(self, external_id: str) -> int | None:
        return self._id_map.get(external_id)

    def to_dict(self) -> dict:
        return {"buffer_size": len(self._buffer), "batch_count": len(self._batches), "total_inserted": sum(len(b.vectors) for b in self._batches)}

    def get_stats(self) -> dict:
        return {"buffered": len(self._buffer), "batches": len(self._batches), "total_vectors": sum(len(b.vectors) for b in self._batches), "id_map": len(self._id_map)}

__all__ = ["VectorBatchInserter", "BatchInsert"]

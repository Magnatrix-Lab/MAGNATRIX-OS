"""Vector Metadata Filter — Metadata indexing, boolean filter queries."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class MetadataFilter:
    field: str = ""
    op: str = "eq"  # eq | ne | gt | lt | gte | lte | in | contains
    value = None

class VectorMetadataFilter:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._index: dict[str, dict[str, list[int]]] = {}
        self._queries: list[dict] = []
        self._persist_path = self.root / "vector_metadata.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._index = data.get("index", {})
            self._queries = data.get("queries", [])

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "index": self._index,
            "queries": self._queries
        }, indent=2))

    def index_vector(self, vector_id: int, metadata: dict) -> None:
        for field, value in metadata.items():
            if field not in self._index:
                self._index[field] = {}
            str_val = str(value)
            if str_val not in self._index[field]:
                self._index[field][str_val] = []
            if vector_id not in self._index[field][str_val]:
                self._index[field][str_val].append(vector_id)
        self._save()

    def query(self, filters: list[MetadataFilter]) -> list[int]:
        results = None
        for f in filters:
            if f.field in self._index and f.op == "eq":
                candidates = set(self._index[f.field].get(str(f.value), []))
            else:
                candidates = set()
            if results is None:
                results = candidates
            else:
                results = results.intersection(candidates)
        self._queries.append({"filters": len(filters), "results": len(results) if results else 0})
        self._save()
        return list(results) if results else []

    def filtered_search(self, filters: list[MetadataFilter], vector_results: list[int]) -> list[int]:
        filtered_ids = self.query(filters)
        if not filtered_ids:
            return vector_results
        return [vid for vid in vector_results if vid in filtered_ids]

    def to_dict(self) -> dict:
        return {"field_count": len(self._index), "query_count": len(self._queries)}

    def get_stats(self) -> dict:
        total_entries = sum(len(v) for field in self._index.values() for v in field.values())
        return {"fields": len(self._index), "total_indexed": total_entries, "queries": len(self._queries)}

__all__ = ["VectorMetadataFilter", "MetadataFilter"]

"""Vector Storage Engine — Dense vector storage, page allocation, segments."""
from dataclasses import dataclass
from pathlib import Path
import json, struct

@dataclass
class VectorPage:
    page_id: int = 0
    capacity: int = 100
    vectors: list[dict] = None
    full: bool = False

    def __post_init__(self):
        if self.vectors is None:
            self.vectors = []

class VectorStorageEngine:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._pages: list[VectorPage] = []
        self._next_page_id = 0
        self._page_size = 100
        self._persist_path = self.root / "vector_storage.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._pages = [VectorPage(**p) for p in data.get("pages", [])]
            self._next_page_id = data.get("next_page_id", 0)

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "pages": [p.__dict__ for p in self._pages],
            "next_page_id": self._next_page_id
        }, indent=2))

    def _allocate_page(self) -> VectorPage:
        page = VectorPage(page_id=self._next_page_id, capacity=self._page_size)
        self._next_page_id += 1
        self._pages.append(page)
        self._save()
        return page

    def insert(self, vector_id: int, vector: list[float], metadata: dict = None) -> dict:
        for page in self._pages:
            if not page.full and len(page.vectors) < page.capacity:
                entry = {"id": vector_id, "vector": vector, "metadata": metadata or {}}
                page.vectors.append(entry)
                if len(page.vectors) >= page.capacity:
                    page.full = True
                self._save()
                return entry
        # Allocate new page
        page = self._allocate_page()
        entry = {"id": vector_id, "vector": vector, "metadata": metadata or {}}
        page.vectors.append(entry)
        self._save()
        return entry

    def get(self, vector_id: int) -> dict | None:
        for page in self._pages:
            for v in page.vectors:
                if v["id"] == vector_id:
                    return v
        return None

    def delete(self, vector_id: int) -> bool:
        for page in self._pages:
            for i, v in enumerate(page.vectors):
                if v["id"] == vector_id:
                    page.vectors.pop(i)
                    page.full = False
                    self._save()
                    return True
        return False

    def to_dict(self) -> dict:
        return {"page_count": len(self._pages), "total_vectors": sum(len(p.vectors) for p in self._pages)}

    def get_stats(self) -> dict:
        return {"pages": len(self._pages), "vectors": sum(len(p.vectors) for p in self._pages), "full_pages": sum(1 for p in self._pages if p.full)}

__all__ = ["VectorStorageEngine", "VectorPage"]

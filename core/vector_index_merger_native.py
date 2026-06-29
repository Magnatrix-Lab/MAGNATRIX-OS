"""Vector Index Merger — Multi-segment merge, compaction, dedup."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class IndexSegment:
    segment_id: str = ""
    vector_count: int = 0
    deleted: int = 0
    size_bytes: int = 0

class VectorIndexMerger:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._segments: list[IndexSegment] = []
        self._merged_count = 0
        self._persist_path = self.root / "vector_merger.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._segments = [IndexSegment(**s) for s in data.get("segments", [])]
            self._merged_count = data.get("merged_count", 0)

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "segments": [s.__dict__ for s in self._segments],
            "merged_count": self._merged_count
        }, indent=2))

    def add_segment(self, segment_id: str, vectors: list[dict]) -> IndexSegment:
        seg = IndexSegment(segment_id=segment_id, vector_count=len(vectors), size_bytes=len(json.dumps(vectors)))
        self._segments.append(seg)
        self._save()
        return seg

    def merge_segments(self, segment_ids: list[str]) -> IndexSegment:
        total_vectors = 0
        total_size = 0
        merged_ids = []
        for seg in self._segments:
            if seg.segment_id in segment_ids:
                total_vectors += seg.vector_count
                total_size += seg.size_bytes
                merged_ids.append(seg.segment_id)
        # Remove old segments
        self._segments = [s for s in self._segments if s.segment_id not in merged_ids]
        new_seg = IndexSegment(
            segment_id=f"merged_{self._merged_count}",
            vector_count=total_vectors,
            size_bytes=total_size
        )
        self._merged_count += 1
        self._segments.append(new_seg)
        self._save()
        return new_seg

    def deduplicate(self, segment_id: str, vectors: list[dict]) -> tuple[int, list[dict]]:
        seen = set()
        unique = []
        for v in vectors:
            vid = v.get("id")
            if vid not in seen:
                seen.add(vid)
                unique.append(v)
        removed = len(vectors) - len(unique)
        for seg in self._segments:
            if seg.segment_id == segment_id:
                seg.deleted += removed
                seg.vector_count = len(unique)
        self._save()
        return removed, unique

    def to_dict(self) -> dict:
        return {"segment_count": len(self._segments), "merged_count": self._merged_count}

    def get_stats(self) -> dict:
        return {"segments": len(self._segments), "total_vectors": sum(s.vector_count for s in self._segments), "deleted": sum(s.deleted for s in self._segments)}

__all__ = ["VectorIndexMerger", "IndexSegment"]

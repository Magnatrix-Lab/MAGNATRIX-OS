"""CV Image Segmentation -- Region growing, threshold-based segmentation."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class Segment:
    segment_id: str = ""
    class_name: str = ""
    pixels: list[tuple[int, int]] = None
    color: str = ""
    area: int = 0

    def __post_init__(self):
        if self.pixels is None:
            self.pixels = []

class CVImageSegmentation:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._segments: list[Segment] = []
        self._persist_path = self.root / "cv_segmentation.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._segments = [Segment(**s) for s in data.get("segments", [])]

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "segments": [s.__dict__ for s in self._segments]
        }, indent=2))

    def threshold_segment(self, image_id: str, data: list[list[int]], threshold: int = 128) -> list[Segment]:
        h = len(data)
        w = len(data[0]) if h > 0 else 0
        visited = [[False] * w for _ in range(h)]
        segments = []
        seg_id = 0

        for y in range(h):
            for x in range(w):
                if visited[y][x]:
                    continue
                region = []
                stack = [(x, y)]
                visited[y][x] = True
                while stack:
                    cx, cy = stack.pop()
                    region.append((cx, cy))
                    for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < w and 0 <= ny < h and not visited[ny][nx]:
                            if abs(data[ny][nx] - data[y][x]) < threshold:
                                visited[ny][nx] = True
                                stack.append((nx, ny))

                if len(region) > 10:
                    seg = Segment(
                        segment_id=f"{image_id}_seg_{seg_id}",
                        class_name="region",
                        pixels=region,
                        area=len(region)
                    )
                    segments.append(seg)
                    self._segments.append(seg)
                    seg_id += 1

        self._save()
        return segments

    def merge_small_segments(self, min_area: int = 50) -> int:
        merged = 0
        self._segments = [s for s in self._segments if s.area >= min_area]
        self._save()
        return merged

    def get_by_area(self, min_area: int = 0) -> list[Segment]:
        return [s for s in self._segments if s.area >= min_area]

    def to_dict(self) -> dict:
        return {"segment_count": len(self._segments)}

    def get_stats(self) -> dict:
        total_area = sum(s.area for s in self._segments)
        avg_area = total_area / len(self._segments) if self._segments else 0
        return {"segments": len(self._segments), "total_area": total_area, "avg_area": round(avg_area, 1)}

__all__ = ["CVImageSegmentation", "Segment"]

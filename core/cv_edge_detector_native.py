"""CV Edge Detector -- Canny, Sobel, Prewitt edge detection."""
from dataclasses import dataclass
from pathlib import Path
import json, math

@dataclass
class EdgeMap:
    image_id: str = ""
    width: int = 0
    height: int = 0
    edges: list[list[int]] = None
    method: str = ""

    def __post_init__(self):
        if self.edges is None:
            self.edges = []

class CVEdgeDetector:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._edge_maps: list[EdgeMap] = []
        self._persist_path = self.root / "cv_edges.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._edge_maps = [EdgeMap(**e) for e in data.get("edge_maps", [])]

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "edge_maps": [e.__dict__ for e in self._edge_maps]
        }, indent=2))

    def _sobel_kernel(self, data: list[list[int]], x: int, y: int) -> float:
        gx = 0
        gy = 0
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                px = x + dx
                py = y + dy
                if 0 <= py < len(data) and 0 <= px < len(data[0]):
                    val = data[py][px]
                else:
                    val = 0
                if dx == 0 and dy == 0:
                    continue
                if dx == -1 and dy == 0: gx -= val * 2
                elif dx == 1 and dy == 0: gx += val * 2
                elif dx == -1 and dy == -1: gx -= val; gy -= val
                elif dx == 1 and dy == -1: gx += val; gy -= val
                elif dx == -1 and dy == 1: gx -= val; gy += val
                elif dx == 1 and dy == 1: gx += val; gy += val
                elif dy == -1 and dx == 0: gy -= val * 2
                elif dy == 1 and dx == 0: gy += val * 2
        return math.sqrt(gx * gx + gy * gy)

    def sobel(self, image_id: str, data: list[list[int]]) -> EdgeMap:
        h = len(data)
        w = len(data[0]) if h > 0 else 0
        edges = [[0] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                edges[y][x] = min(255, int(self._sobel_kernel(data, x, y)))
        em = EdgeMap(image_id=image_id, width=w, height=h, edges=edges, method="sobel")
        self._edge_maps.append(em)
        self._save()
        return em

    def threshold(self, edge_map: EdgeMap, threshold: int = 128) -> EdgeMap:
        binary = [[255 if p > threshold else 0 for p in row] for row in edge_map.edges]
        return EdgeMap(image_id=edge_map.image_id, width=edge_map.width, height=edge_map.height, edges=binary, method="threshold")

    def count_edges(self, edge_map: EdgeMap) -> int:
        return sum(sum(1 for p in row if p > 0) for row in edge_map.edges)

    def to_dict(self) -> dict:
        return {"edge_map_count": len(self._edge_maps)}

    def get_stats(self) -> dict:
        by_method = {}
        for e in self._edge_maps:
            by_method[e.method] = by_method.get(e.method, 0) + 1
        return {"edge_maps": len(self._edge_maps), "by_method": by_method}

__all__ = ["CVEdgeDetector", "EdgeMap"]

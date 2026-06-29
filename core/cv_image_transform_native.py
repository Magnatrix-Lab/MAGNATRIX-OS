"""CV Image Transform -- Resize, rotate, flip, crop, color space conversion."""
from dataclasses import dataclass
from pathlib import Path
import json, math

@dataclass
class TransformedImage:
    image_id: str = ""
    transform_type: str = ""
    params: dict = None
    result_data: list[list[int]] = None
    source_id: str = ""

    def __post_init__(self):
        if self.params is None:
            self.params = {}
        if self.result_data is None:
            self.result_data = []

class CVImageTransform:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._transforms: list[TransformedImage] = []
        self._persist_path = self.root / "cv_transforms.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._transforms = [TransformedImage(**t) for t in data.get("transforms", [])]

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "transforms": [t.__dict__ for t in self._transforms]
        }, indent=2))

    def resize(self, image_id: str, data: list[list[int]], new_width: int, new_height: int) -> TransformedImage:
        h = len(data)
        w = len(data[0]) if h > 0 else 0
        result = [[0] * new_width for _ in range(new_height)]
        for y in range(new_height):
            for x in range(new_width):
                src_x = int(x * w / new_width)
                src_y = int(y * h / new_height)
                src_x = min(src_x, w - 1)
                src_y = min(src_y, h - 1)
                result[y][x] = data[src_y][src_x]
        t = TransformedImage(image_id=image_id, transform_type="resize", params={"w": new_width, "h": new_height}, result_data=result, source_id=image_id)
        self._transforms.append(t)
        self._save()
        return t

    def rotate(self, image_id: str, data: list[list[int]], angle: float) -> TransformedImage:
        h = len(data)
        w = len(data[0]) if h > 0 else 0
        rad = math.radians(angle)
        cos_a = math.cos(rad)
        sin_a = math.sin(rad)
        cx = w / 2
        cy = h / 2
        result = [[0] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                nx = int(cos_a * (x - cx) - sin_a * (y - cy) + cx)
                ny = int(sin_a * (x - cx) + cos_a * (y - cy) + cy)
                if 0 <= nx < w and 0 <= ny < h:
                    result[y][x] = data[ny][nx]
        t = TransformedImage(image_id=image_id, transform_type="rotate", params={"angle": angle}, result_data=result, source_id=image_id)
        self._transforms.append(t)
        self._save()
        return t

    def flip_horizontal(self, image_id: str, data: list[list[int]]) -> TransformedImage:
        result = [row[::-1] for row in data]
        t = TransformedImage(image_id=image_id, transform_type="flip_h", params={}, result_data=result, source_id=image_id)
        self._transforms.append(t)
        self._save()
        return t

    def crop(self, image_id: str, data: list[list[int]], x: int, y: int, w: int, h: int) -> TransformedImage:
        result = []
        for py in range(y, min(y + h, len(data))):
            row = []
            for px in range(x, min(x + w, len(data[0]))):
                row.append(data[py][px])
            result.append(row)
        t = TransformedImage(image_id=image_id, transform_type="crop", params={"x": x, "y": y, "w": w, "h": h}, result_data=result, source_id=image_id)
        self._transforms.append(t)
        self._save()
        return t

    def to_dict(self) -> dict:
        return {"transform_count": len(self._transforms)}

    def get_stats(self) -> dict:
        by_type = {}
        for t in self._transforms:
            by_type[t.transform_type] = by_type.get(t.transform_type, 0) + 1
        return {"transforms": len(self._transforms), "by_type": by_type}

__all__ = ["CVImageTransform", "TransformedImage"]

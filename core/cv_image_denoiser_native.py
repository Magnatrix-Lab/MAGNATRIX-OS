"""CV Image Denoiser -- Gaussian, median, bilateral filtering."""
from dataclasses import dataclass
from pathlib import Path
import json, statistics

@dataclass
class DenoisedImage:
    image_id: str = ""
    method: str = ""
    kernel_size: int = 0
    data: list[list[int]] = None

    def __post_init__(self):
        if self.data is None:
            self.data = []

class CVImageDenoiser:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._images: list[DenoisedImage] = []
        self._persist_path = self.root / "cv_denoise.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._images = [DenoisedImage(**i) for i in data.get("images", [])]

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "images": [i.__dict__ for i in self._images]
        }, indent=2))

    def gaussian(self, image_id: str, data: list[list[int]], kernel_size: int = 3) -> DenoisedImage:
        h = len(data)
        w = len(data[0]) if h > 0 else 0
        result = [[0] * w for _ in range(h)]
        sigma = kernel_size / 2.0
        # Generate Gaussian kernel
        kernel = []
        for ky in range(-kernel_size//2, kernel_size//2 + 1):
            row = []
            for kx in range(-kernel_size//2, kernel_size//2 + 1):
                import math
                val = math.exp(-(kx*kx + ky*ky) / (2 * sigma * sigma))
                row.append(val)
            kernel.append(row)
        total = sum(sum(r) for r in kernel)
        kernel = [[v / total for v in row] for row in kernel]

        for y in range(h):
            for x in range(w):
                acc = 0.0
                for ky in range(len(kernel)):
                    for kx in range(len(kernel[0])):
                        px = x + kx - len(kernel)//2
                        py = y + ky - len(kernel)//2
                        if 0 <= px < w and 0 <= py < h:
                            acc += data[py][px] * kernel[ky][kx]
                result[y][x] = int(acc)

        img = DenoisedImage(image_id=image_id, method="gaussian", kernel_size=kernel_size, data=result)
        self._images.append(img)
        self._save()
        return img

    def median(self, image_id: str, data: list[list[int]], kernel_size: int = 3) -> DenoisedImage:
        h = len(data)
        w = len(data[0]) if h > 0 else 0
        result = [[0] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                neighbors = []
                for dy in range(-kernel_size//2, kernel_size//2 + 1):
                    for dx in range(-kernel_size//2, kernel_size//2 + 1):
                        px = x + dx
                        py = y + dy
                        if 0 <= px < w and 0 <= py < h:
                            neighbors.append(data[py][px])
                result[y][x] = int(statistics.median(neighbors)) if neighbors else 0

        img = DenoisedImage(image_id=image_id, method="median", kernel_size=kernel_size, data=result)
        self._images.append(img)
        self._save()
        return img

    def to_dict(self) -> dict:
        return {"image_count": len(self._images)}

    def get_stats(self) -> dict:
        by_method = {}
        for i in self._images:
            by_method[i.method] = by_method.get(i.method, 0) + 1
        return {"images": len(self._images), "by_method": by_method}

__all__ = ["CVImageDenoiser", "DenoisedImage"]

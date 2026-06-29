"""CV Feature Extractor -- SIFT-like keypoint detection, descriptor generation."""
from dataclasses import dataclass
from pathlib import Path
import json, math

@dataclass
class Keypoint:
    kp_id: str = ""
    x: float = 0.0
    y: float = 0.0
    scale: float = 1.0
    orientation: float = 0.0
    descriptor: list[float] = None

    def __post_init__(self):
        if self.descriptor is None:
            self.descriptor = []

class CVFeatureExtractor:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._keypoints: list[Keypoint] = []
        self._persist_path = self.root / "cv_features.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._keypoints = [Keypoint(**k) for k in data.get("keypoints", [])]

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "keypoints": [k.__dict__ for k in self._keypoints]
        }, indent=2))

    def detect_corners(self, image_id: str, data: list[list[int]], threshold: int = 100) -> list[Keypoint]:
        h = len(data)
        w = len(data[0]) if h > 0 else 0
        keypoints = []
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                # Harris corner response (simplified)
                ix = data[y][x+1] - data[y][x-1]
                iy = data[y+1][x] - data[y-1][x]
                ixx = ix * ix
                iyy = iy * iy
                ixy = ix * iy
                det = ixx * iyy - ixy * ixy
                trace = ixx + iyy
                response = det - 0.04 * trace * trace
                if response > threshold:
                    # Generate 128-dim descriptor (simplified)
                    desc = []
                    for dy in range(-2, 3):
                        for dx in range(-2, 3):
                            px = x + dx
                            py = y + dy
                            if 0 <= px < w and 0 <= py < h:
                                desc.append(data[py][px] / 255.0)
                            else:
                                desc.append(0.0)
                    kp = Keypoint(
                        kp_id=f"{image_id}_kp_{len(keypoints)}",
                        x=x, y=y, scale=1.0, orientation=math.atan2(iy, ix),
                        descriptor=desc[:128]
                    )
                    keypoints.append(kp)
                    self._keypoints.append(kp)
        self._save()
        return keypoints

    def match(self, kp1: Keypoint, kp2: Keypoint) -> float:
        if not kp1.descriptor or not kp2.descriptor:
            return 0.0
        # Euclidean distance between descriptors
        dist = math.sqrt(sum((a - b) ** 2 for a, b in zip(kp1.descriptor, kp2.descriptor)))
        return 1.0 / (1.0 + dist)

    def to_dict(self) -> dict:
        return {"keypoint_count": len(self._keypoints)}

    def get_stats(self) -> dict:
        by_scale = {}
        for k in self._keypoints:
            s = round(k.scale, 1)
            by_scale[s] = by_scale.get(s, 0) + 1
        return {"keypoints": len(self._keypoints), "by_scale": by_scale}

__all__ = ["CVFeatureExtractor", "Keypoint"]

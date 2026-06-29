"""CV Face Detector -- Haar-like feature-based face detection."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class Face:
    face_id: str = ""
    image_id: str = ""
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0
    confidence: float = 0.0
    features: list[float] = None

    def __post_init__(self):
        if self.features is None:
            self.features = []

class CVFaceDetector:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._faces: list[Face] = []
        self._persist_path = self.root / "cv_faces.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._faces = [Face(**f) for f in data.get("faces", [])]

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "faces": [f.__dict__ for f in self._faces]
        }, indent=2))

    def detect(self, image_id: str, data: list[list[int]], min_face_size: int = 20) -> list[Face]:
        import random
        h = len(data)
        w = len(data[0]) if h > 0 else 0
        faces = []
        # Simulated detection: scan for high-contrast rectangular regions
        for y in range(0, h - min_face_size, min_face_size // 2):
            for x in range(0, w - min_face_size, min_face_size // 2):
                # Check for face-like pattern (simplified: average intensity in region)
                region = [data[py][px] for py in range(y, y + min_face_size) for px in range(x, x + min_face_size)]
                avg = sum(region) / len(region) if region else 0
                std = (sum((v - avg) ** 2 for v in region) / len(region)) ** 0.5 if region else 0
                # Face-like: moderate average with moderate variance
                if 60 < avg < 180 and 30 < std < 80:
                    conf = round(random.uniform(0.7, 0.99), 3)
                    face = Face(
                        face_id=f"{image_id}_face_{len(faces)}",
                        image_id=image_id, x=x, y=y,
                        width=min_face_size, height=min_face_size,
                        confidence=conf,
                        features=[avg / 255.0, std / 255.0, random.random()]
                    )
                    faces.append(face)
                    self._faces.append(face)
        self._save()
        return faces

    def get_faces(self, image_id: str) -> list[Face]:
        return [f for f in self._faces if f.image_id == image_id]

    def to_dict(self) -> dict:
        return {"face_count": len(self._faces)}

    def get_stats(self) -> dict:
        by_image = {}
        for f in self._faces:
            by_image[f.image_id] = by_image.get(f.image_id, 0) + 1
        avg_conf = sum(f.confidence for f in self._faces) / len(self._faces) if self._faces else 0
        return {"faces": len(self._faces), "by_image": by_image, "avg_confidence": round(avg_conf, 3)}

__all__ = ["CVFaceDetector", "Face"]

"""CV Object Detector -- Pure Python bounding box detection pipeline."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class Detection:
    detection_id: str = ""
    class_name: str = ""
    confidence: float = 0.0
    x: int = 0
    y: int = 0
    width: int = 0
    height: int = 0

@dataclass
class DetectionResult:
    image_id: str = ""
    detections: list[Detection] = None

    def __post_init__(self):
        if self.detections is None:
            self.detections = []

class CVObjectDetector:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._classes: list[str] = ["person", "car", "bicycle", "dog", "cat", "chair", "table"]
        self._anchors: list[tuple[int, int]] = [(10, 10), (20, 20), (40, 40), (80, 80)]
        self._results: list[DetectionResult] = []
        self._persist_path = self.root / "cv_detector.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._results = [DetectionResult(**r) for r in data.get("results", [])]

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "results": [{
                "image_id": r.image_id,
                "detections": [d.__dict__ for d in r.detections]
            } for r in self._results]
        }, indent=2))

    def detect(self, image_id: str, image_width: int, image_height: int, num_objects: int = 3) -> DetectionResult:
        import random
        result = DetectionResult(image_id=image_id)
        for i in range(num_objects):
            cls = random.choice(self._classes)
            w, h = random.choice(self._anchors)
            x = random.randint(0, max(0, image_width - w))
            y = random.randint(0, max(0, image_height - h))
            conf = round(random.uniform(0.6, 0.99), 3)
            result.detections.append(Detection(
                detection_id=f"{image_id}_det_{i}", class_name=cls,
                confidence=conf, x=x, y=y, width=w, height=h
            ))
        self._results.append(result)
        self._save()
        return result

    def nms(self, detections: list[Detection], iou_threshold: float = 0.5) -> list[Detection]:
        # Non-maximum suppression (simplified)
        if not detections:
            return []
        sorted_dets = sorted(detections, key=lambda d: d.confidence, reverse=True)
        keep = [sorted_dets[0]]
        for det in sorted_dets[1:]:
            overlap = self._iou(keep[-1], det)
            if overlap < iou_threshold:
                keep.append(det)
        return keep

    def _iou(self, a: Detection, b: Detection) -> float:
        x1 = max(a.x, b.x)
        y1 = max(a.y, b.y)
        x2 = min(a.x + a.width, b.x + b.width)
        y2 = min(a.y + a.height, b.y + b.height)
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        union = a.width * a.height + b.width * b.height - inter
        return inter / union if union > 0 else 0.0

    def to_dict(self) -> dict:
        return {"result_count": len(self._results)}

    def get_stats(self) -> dict:
        total = sum(len(r.detections) for r in self._results)
        by_class = {}
        for r in self._results:
            for d in r.detections:
                by_class[d.class_name] = by_class.get(d.class_name, 0) + 1
        return {"results": len(self._results), "total_detections": total, "by_class": by_class}

__all__ = ["CVObjectDetector", "Detection", "DetectionResult"]

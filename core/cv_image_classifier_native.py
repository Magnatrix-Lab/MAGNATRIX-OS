"""CV Image Classifier -- Pure Python image classification pipeline."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class ClassificationResult:
    image_id: str = ""
    predicted_class: str = ""
    confidence: float = 0.0
    all_scores: dict = None

    def __post_init__(self):
        if self.all_scores is None:
            self.all_scores = {}

class CVImageClassifier:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._classes: list[str] = ["cat", "dog", "bird", "car", "tree", "person", "building", "water"]
        self._weights: dict[str, list[float]] = {}
        self._results: list[ClassificationResult] = []
        self._persist_path = self.root / "cv_classifier.json"
        self._load()
        if not self._weights:
            self._init_weights()

    def _init_weights(self) -> None:
        import random
        for c in self._classes:
            self._weights[c] = [random.uniform(-1, 1) for _ in range(64)]

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._classes = data.get("classes", self._classes)
            self._weights = data.get("weights", {})
            self._results = [ClassificationResult(**r) for r in data.get("results", [])]

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "classes": self._classes,
            "weights": self._weights,
            "results": [r.__dict__ for r in self._results]
        }, indent=2))

    def _extract_features(self, image_data: list[int]) -> list[float]:
        # Simulated feature extraction: 64-dim histogram-like features
        features = [0.0] * 64
        for i, val in enumerate(image_data[:64]):
            features[i] = val / 255.0
        return features

    def _softmax(self, logits: list[float]) -> list[float]:
        import math
        exp = [math.exp(l) for l in logits]
        total = sum(exp)
        return [e / total for e in exp]

    def classify(self, image_id: str, image_data: list[int]) -> ClassificationResult:
        features = self._extract_features(image_data)
        logits = []
        for c in self._classes:
            w = self._weights.get(c, [0.0] * 64)
            score = sum(f * wi for f, wi in zip(features, w))
            logits.append(score)
        probs = self._softmax(logits)
        all_scores = {c: round(p, 4) for c, p in zip(self._classes, probs)}
        best_idx = max(range(len(probs)), key=lambda i: probs[i])
        result = ClassificationResult(
            image_id=image_id, predicted_class=self._classes[best_idx],
            confidence=round(probs[best_idx], 4), all_scores=all_scores
        )
        self._results.append(result)
        self._save()
        return result

    def add_class(self, class_name: str) -> None:
        if class_name not in self._classes:
            self._classes.append(class_name)
            import random
            self._weights[class_name] = [random.uniform(-1, 1) for _ in range(64)]
            self._save()

    def train(self, class_name: str, image_data: list[int], label: int) -> None:
        # Simulated online learning: adjust weights
        if class_name not in self._weights:
            return
        features = self._extract_features(image_data)
        lr = 0.01
        for i in range(len(self._weights[class_name])):
            self._weights[class_name][i] += lr * label * features[i]
        self._save()

    def to_dict(self) -> dict:
        return {"class_count": len(self._classes), "result_count": len(self._results)}

    def get_stats(self) -> dict:
        by_class = {}
        for r in self._results:
            by_class[r.predicted_class] = by_class.get(r.predicted_class, 0) + 1
        avg_conf = sum(r.confidence for r in self._results) / len(self._results) if self._results else 0
        return {"results": len(self._results), "by_class": by_class, "avg_confidence": round(avg_conf, 3)}

__all__ = ["CVImageClassifier", "ClassificationResult"]

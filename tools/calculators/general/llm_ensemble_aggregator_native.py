"""Ensemble Aggregator — voting, stacking, bagging, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any
from enum import Enum, auto
import math
import statistics

class EnsembleType(Enum):
    VOTING = auto()
    AVERAGING = auto()
    WEIGHTED = auto()
    STACKING = auto()

@dataclass
class ModelPrediction:
    model_id: str
    prediction: Any
    confidence: float = 1.0

class EnsembleAggregator:
    def __init__(self, ensemble_type: EnsembleType = EnsembleType.VOTING):
        self.ensemble_type = ensemble_type
        self.weights: Dict[str, float] = {}
        self.meta_learner: Optional[Callable] = None
        self.history: List[Dict] = []

    def set_weight(self, model_id: str, weight: float):
        self.weights[model_id] = weight

    def set_meta_learner(self, learner: Callable):
        self.meta_learner = learner

    def aggregate(self, predictions: List[ModelPrediction]) -> Any:
        if self.ensemble_type == EnsembleType.VOTING:
            return self._voting(predictions)
        elif self.ensemble_type == EnsembleType.AVERAGING:
            return self._averaging(predictions)
        elif self.ensemble_type == EnsembleType.WEIGHTED:
            return self._weighted(predictions)
        elif self.ensemble_type == EnsembleType.STACKING:
            return self._stacking(predictions)
        return None

    def _voting(self, predictions: List[ModelPrediction]) -> Any:
        votes = {}
        for p in predictions:
            key = str(p.prediction)
            votes[key] = votes.get(key, 0) + 1
        return max(votes, key=votes.get)

    def _averaging(self, predictions: List[ModelPrediction]) -> float:
        vals = [p.prediction for p in predictions if isinstance(p.prediction, (int, float))]
        return sum(vals) / len(vals) if vals else 0.0

    def _weighted(self, predictions: List[ModelPrediction]) -> float:
        total = 0.0
        weight_sum = 0.0
        for p in predictions:
            w = self.weights.get(p.model_id, 1.0)
            total += p.prediction * w
            weight_sum += w
        return total / weight_sum if weight_sum > 0 else 0.0

    def _stacking(self, predictions: List[ModelPrediction]) -> Any:
        if self.meta_learner:
            features = [p.prediction for p in predictions]
            return self.meta_learner(features)
        return self._averaging(predictions)

    def stats(self) -> Dict:
        return {"type": self.ensemble_type.name, "weights": len(self.weights), "has_meta": self.meta_learner is not None}

def run():
    agg = EnsembleAggregator(EnsembleType.WEIGHTED)
    agg.set_weight("m1", 0.5)
    agg.set_weight("m2", 0.3)
    agg.set_weight("m3", 0.2)
    preds = [
        ModelPrediction("m1", 10.0),
        ModelPrediction("m2", 12.0),
        ModelPrediction("m3", 11.0),
    ]
    print(agg.aggregate(preds))
    print(agg.stats())

if __name__ == "__main__":
    run()

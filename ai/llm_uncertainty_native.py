"""Uncertainty Quantification — Confidence calibration, entropy-based uncertainty, ensemble disagreement, Monte Carlo dropout.

Modul ini menyediakan:
- ConfidenceCalibrator untuk calibration curve dan ECE (Expected Calibration Error)
- EntropyEstimator untuk uncertainty via entropy
- EnsembleDisagreement untuk multi-model disagreement
- MonteCarloEstimator untuk dropout-based uncertainty
- UncertaintyAggregator untuk kombinasi multiple uncertainty sources

Arsitektur: Prediction → Uncertainty Sources → Aggregate → Calibrate → Report
"""

from __future__ import annotations

import json
import time
import uuid
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class UncertaintyType(Enum):
    ALEATORIC = auto()
    EPISTEMIC = auto()
    TOTAL = auto()


class CalibrationMethod(Enum):
    TEMPERATURE = auto()
    PLATT = auto()
    ISOTONIC = auto()


@dataclass
class Prediction:
    """Single prediction with confidence."""
    prediction_id: str
    output: str
    confidence: float = 0.0
    probabilities: Dict[str, float] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class UncertaintyEstimate:
    """Uncertainty estimate for a prediction."""
    estimate_id: str
    prediction_id: str
    uncertainty_type: UncertaintyType
    value: float
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CalibrationResult:
    """Calibration metrics."""
    ece: float = 0.0  # Expected Calibration Error
    mce: float = 0.0  # Maximum Calibration Error
    brier: float = 0.0  # Brier score
    bin_accuracies: List[float] = field(default_factory=list)
    bin_confidences: List[float] = field(default_factory=list)
    bin_counts: List[int] = field(default_factory=list)


class ConfidenceCalibrator:
    """Calibrate confidence scores using temperature scaling."""

    def __init__(self, num_bins: int = 10):
        self.num_bins = num_bins
        self._predictions: List[Tuple[float, bool]] = []  # (confidence, correct)
        self.temperature: float = 1.0

    def add(self, confidence: float, correct: bool) -> None:
        self._predictions.append((confidence, correct))

    def calibrate(self, method: CalibrationMethod = CalibrationMethod.TEMPERATURE) -> CalibrationResult:
        if not self._predictions:
            return CalibrationResult()

        if method == CalibrationMethod.TEMPERATURE:
            self.temperature = self._find_temperature()

        result = CalibrationResult()
        result.bin_accuracies = []
        result.bin_confidences = []
        result.bin_counts = []

        for i in range(self.num_bins):
            low = i / self.num_bins
            high = (i + 1) / self.num_bins
            bin_preds = [(c, correct) for c, correct in self._predictions if low <= c < high]
            if not bin_preds:
                result.bin_accuracies.append(0.0)
                result.bin_confidences.append((low + high) / 2)
                result.bin_counts.append(0)
                continue
            acc = sum(1 for _, correct in bin_preds if correct) / len(bin_preds)
            avg_conf = sum(c for c, _ in bin_preds) / len(bin_preds)
            result.bin_accuracies.append(acc)
            result.bin_confidences.append(avg_conf)
            result.bin_counts.append(len(bin_preds))

        result.ece = sum(
            (count / len(self._predictions)) * abs(acc - conf)
            for acc, conf, count in zip(result.bin_accuracies, result.bin_confidences, result.bin_counts)
            if count > 0
        )
        result.mce = max(
            abs(acc - conf)
            for acc, conf, count in zip(result.bin_accuracies, result.bin_confidences, result.bin_counts)
            if count > 0
        ) if any(c > 0 for c in result.bin_counts) else 0.0

        # Brier score
        result.brier = sum((c - (1.0 if correct else 0.0)) ** 2 for c, correct in self._predictions) / len(self._predictions)
        return result

    def _find_temperature(self) -> float:
        # Simplified temperature search
        best_temp = 1.0
        best_ece = float('inf')
        for temp in [0.5, 0.8, 1.0, 1.2, 1.5, 2.0]:
            ece = self._compute_ece_with_temp(temp)
            if ece < best_ece:
                best_ece = ece
                best_temp = temp
        return best_temp

    def _compute_ece_with_temp(self, temp: float) -> float:
        scaled = [min(1.0, c / temp) for c, _ in self._predictions]
        total = 0
        for i in range(self.num_bins):
            low = i / self.num_bins
            high = (i + 1) / self.num_bins
            bin_items = [(s, correct) for s, (_, correct) in zip(scaled, self._predictions) if low <= s < high]
            if bin_items:
                acc = sum(1 for _, correct in bin_items if correct) / len(bin_items)
                conf = sum(s for s, _ in bin_items) / len(bin_items)
                total += (len(bin_items) / len(self._predictions)) * abs(acc - conf)
        return total

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_predictions": len(self._predictions),
            "temperature": self.temperature,
            "accuracy": sum(1 for _, correct in self._predictions if correct) / max(len(self._predictions), 1),
        }


class EntropyEstimator:
    """Estimate uncertainty via Shannon entropy."""

    @staticmethod
    def entropy(probabilities: List[float]) -> float:
        return -sum(p * math.log2(p) for p in probabilities if p > 0)

    @staticmethod
    def normalized_entropy(probabilities: List[float]) -> float:
        max_entropy = math.log2(len(probabilities)) if probabilities else 1.0
        return EntropyEstimator.entropy(probabilities) / max(max_entropy, 1e-9)

    def estimate(self, prediction: Prediction) -> UncertaintyEstimate:
        probs = list(prediction.probabilities.values()) if prediction.probabilities else [prediction.confidence, 1 - prediction.confidence]
        if not probs:
            probs = [0.5, 0.5]
        ent = self.entropy(probs)
        norm_ent = self.normalized_entropy(probs)
        return UncertaintyEstimate(
            estimate_id=str(uuid.uuid4())[:12],
            prediction_id=prediction.prediction_id,
            uncertainty_type=UncertaintyType.TOTAL,
            value=round(norm_ent, 4),
            source="entropy",
            metadata={"raw_entropy": round(ent, 4)}
        )

    def estimate_token_sequence(self, token_probs: List[Dict[str, float]]) -> List[float]:
        """Entropy per token position."""
        return [self.normalized_entropy(list(probs.values())) for probs in token_probs]


class EnsembleDisagreement:
    """Measure uncertainty via ensemble disagreement."""

    def __init__(self, num_models: int = 3):
        self.num_models = num_models
        self._predictions: Dict[str, List[Prediction]] = {}  # query_id -> predictions from each model

    def add_prediction(self, query_id: str, model_id: str, prediction: Prediction) -> None:
        if query_id not in self._predictions:
            self._predictions[query_id] = []
        self._predictions[query_id].append(prediction)

    def disagreement(self, query_id: str) -> UncertaintyEstimate:
        preds = self._predictions.get(query_id, [])
        if len(preds) < 2:
            return UncertaintyEstimate(
                estimate_id=str(uuid.uuid4())[:12],
                prediction_id=query_id,
                uncertainty_type=UncertaintyType.EPISTEMIC,
                value=0.0,
                source="ensemble"
            )
        # Vote entropy as disagreement measure
        outputs = [p.output for p in preds]
        unique = list(set(outputs))
        counts = [outputs.count(u) for u in unique]
        probs = [c / len(outputs) for c in counts]
        ent = -sum(p * math.log2(p) for p in probs if p > 0)
        max_ent = math.log2(len(unique)) if unique else 1.0
        return UncertaintyEstimate(
            estimate_id=str(uuid.uuid4())[:12],
            prediction_id=query_id,
            uncertainty_type=UncertaintyType.EPISTEMIC,
            value=round(ent / max(max_ent, 1e-9), 4),
            source="ensemble",
            metadata={"models": len(preds), "unique_outputs": len(unique)}
        )

    def variance(self, query_id: str) -> float:
        """Variance of confidence scores."""
        preds = self._predictions.get(query_id, [])
        if len(preds) < 2:
            return 0.0
        confs = [p.confidence for p in preds]
        mean = sum(confs) / len(confs)
        return sum((c - mean) ** 2 for c in confs) / len(confs)


class MonteCarloEstimator:
    """Monte Carlo dropout for uncertainty estimation."""

    def __init__(self, num_samples: int = 10):
        self.num_samples = num_samples

    def estimate(self, predictor: Callable[[], Prediction]) -> UncertaintyEstimate:
        predictions = [predictor() for _ in range(self.num_samples)]
        outputs = [p.output for p in predictions]
        confs = [p.confidence for p in predictions]

        # Mean prediction
        mean_conf = sum(confs) / len(confs)
        variance = sum((c - mean_conf) ** 2 for c in confs) / len(confs)

        # Unique output ratio
        unique = len(set(outputs)) / len(outputs)

        return UncertaintyEstimate(
            estimate_id=str(uuid.uuid4())[:12],
            prediction_id=predictions[0].prediction_id if predictions else "",
            uncertainty_type=UncertaintyType.EPISTEMIC,
            value=round(variance + unique * 0.1, 4),
            source="monte_carlo",
            metadata={"variance": round(variance, 4), "unique_ratio": round(unique, 4)}
        )


class UncertaintyAggregator:
    """Aggregate multiple uncertainty sources."""

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or {"entropy": 0.3, "ensemble": 0.4, "monte_carlo": 0.3}
        self._estimates: List[UncertaintyEstimate] = []

    def add(self, estimate: UncertaintyEstimate) -> None:
        self._estimates.append(estimate)

    def aggregate(self, method: str = "weighted") -> UncertaintyEstimate:
        if not self._estimates:
            return UncertaintyEstimate(
                estimate_id=str(uuid.uuid4())[:12],
                prediction_id="",
                uncertainty_type=UncertaintyType.TOTAL,
                value=0.0
            )
        if method == "weighted":
            total = 0.0
            weight_sum = 0.0
            for est in self._estimates:
                w = self.weights.get(est.source, 0.1)
                total += est.value * w
                weight_sum += w
            value = total / max(weight_sum, 1e-9)
        elif method == "max":
            value = max(est.value for est in self._estimates)
        else:
            value = sum(est.value for est in self._estimates) / len(self._estimates)
        return UncertaintyEstimate(
            estimate_id=str(uuid.uuid4())[:12],
            prediction_id=self._estimates[0].prediction_id,
            uncertainty_type=UncertaintyType.TOTAL,
            value=round(value, 4),
            source="aggregated",
            metadata={"sources": [est.source for est in self._estimates]}
        )

    def get_estimates(self) -> List[UncertaintyEstimate]:
        return self._estimates

    def get_high_uncertainty(self, threshold: float = 0.7) -> List[UncertaintyEstimate]:
        return [e for e in self._estimates if e.value > threshold]


class UncertaintyEngine:
    """End-to-end uncertainty quantification engine."""

    def __init__(self, num_bins: int = 10, num_samples: int = 10):
        self.calibrator = ConfidenceCalibrator(num_bins)
        self.entropy = EntropyEstimator()
        self.ensemble = EnsembleDisagreement()
        self.monte_carlo = MonteCarloEstimator(num_samples)
        self.aggregator = UncertaintyAggregator()

    def quantify(self, prediction: Prediction, method: str = "all") -> Dict[str, UncertaintyEstimate]:
        results = {}
        if method in ("all", "entropy"):
            results["entropy"] = self.entropy.estimate(prediction)
        if method in ("all", "monte_carlo"):
            results["monte_carlo"] = self.monte_carlo.estimate(lambda: prediction)
        return results

    def calibrate(self, confidences: List[Tuple[float, bool]], method: CalibrationMethod = CalibrationMethod.TEMPERATURE) -> CalibrationResult:
        for conf, correct in confidences:
            self.calibrator.add(conf, correct)
        return self.calibrator.calibrate(method)

    def get_summary(self) -> Dict[str, Any]:
        return {
            "calibrator": self.calibrator.get_stats(),
            "total_estimates": len(self.aggregator.get_estimates()),
        }

    def export_calibration(self, path: str) -> None:
        result = self.calibrator.calibrate()
        data = {
            "ece": result.ece,
            "mce": result.mce,
            "brier": result.brier,
            "bins": [
                {"accuracy": a, "confidence": c, "count": n}
                for a, c, n in zip(result.bin_accuracies, result.bin_confidences, result.bin_counts)
            ]
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("UNCERTAINTY QUANTIFICATION DEMO")
    print("=" * 70)

    engine = UncertaintyEngine(num_bins=5, num_samples=5)

    # 1. Entropy estimation
    print("\n[1] Entropy Estimation")
    pred = Prediction(
        prediction_id="p1",
        output="Paris",
        confidence=0.9,
        probabilities={"Paris": 0.9, "London": 0.05, "Berlin": 0.05}
    )
    ent = engine.entropy.estimate(pred)
    print(f"  Prediction: {pred.output} (conf={pred.confidence})")
    print(f"  Entropy uncertainty: {ent.value} (type: {ent.uncertainty_type.name})")
    print(f"  Raw entropy: {ent.metadata.get('raw_entropy')}")

    # 2. Low confidence prediction
    print("\n[2] High Uncertainty Prediction")
    pred2 = Prediction(
        prediction_id="p2",
        output="Maybe Paris",
        confidence=0.4,
        probabilities={"Paris": 0.4, "London": 0.35, "Berlin": 0.25}
    )
    ent2 = engine.entropy.estimate(pred2)
    print(f"  Prediction: {pred2.output} (conf={pred2.confidence})")
    print(f"  Entropy uncertainty: {ent2.value}")
    print(f"  Higher uncertainty: {ent2.value > ent.value}")

    # 3. Ensemble disagreement
    print("\n[3] Ensemble Disagreement")
    engine.ensemble.add_prediction("q1", "model-a", Prediction("p-a", "Paris", 0.9))
    engine.ensemble.add_prediction("q1", "model-b", Prediction("p-b", "London", 0.7))
    engine.ensemble.add_prediction("q1", "model-c", Prediction("p-c", "Paris", 0.8))
    disag = engine.ensemble.disagreement("q1")
    print(f"  Disagreement: {disag.value}")
    print(f"  Variance: {engine.ensemble.variance('q1'):.4f}")
    print(f"  Unique outputs: {disag.metadata.get('unique_outputs')}")

    # 4. Monte Carlo estimation
    print("\n[4] Monte Carlo Estimation")
    mc = engine.monte_carlo.estimate(lambda: Prediction("mc", "Output", confidence=0.5 + (uuid.uuid4().int % 50) / 100))
    print(f"  MC uncertainty: {mc.value}")
    print(f"  Source: {mc.source}")
    print(f"  Metadata: {mc.metadata}")

    # 5. Calibration
    print("\n[5] Confidence Calibration")
    # Well-calibrated data
    for _ in range(100):
        conf = 0.5 + (uuid.uuid4().int % 50) / 100
        correct = uuid.uuid4().int % 100 < conf * 100
        engine.calibrator.add(conf, correct)
    result = engine.calibrator.calibrate(CalibrationMethod.TEMPERATURE)
    print(f"  ECE: {result.ece:.4f}")
    print(f"  MCE: {result.mce:.4f}")
    print(f"  Brier: {result.brier:.4f}")
    print(f"  Temperature: {engine.calibrator.temperature}")
    print(f"  Bin counts: {result.bin_counts}")

    # 6. Aggregation
    print("\n[6] Uncertainty Aggregation")
    agg = UncertaintyAggregator(weights={"entropy": 0.4, "ensemble": 0.3, "monte_carlo": 0.3})
    agg.add(ent)
    agg.add(disag)
    agg.add(mc)
    total = agg.aggregate("weighted")
    print(f"  Aggregated uncertainty: {total.value}")
    print(f"  Sources: {total.metadata.get('sources')}")
    max_unc = agg.aggregate("max")
    print(f"  Max uncertainty: {max_unc.value}")

    # 7. Token sequence entropy
    print("\n[7] Token Sequence Entropy")
    token_probs = [
        {"The": 0.9, "A": 0.1},
        {"cat": 0.7, "dog": 0.2, "bird": 0.1},
        {"sat": 0.8, "ran": 0.15, "jumped": 0.05},
    ]
    seq_ent = engine.entropy.estimate_token_sequence(token_probs)
    print(f"  Per-token entropy: {seq_ent}")
    print(f"  Average: {sum(seq_ent)/len(seq_ent):.4f}")

    # 8. Stats
    print("\n[8] Engine Stats")
    stats = engine.get_summary()
    print(f"  {stats}")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()

"""
MAGNATRIX-OS Layer 8 — HFT Trading Signal Engine (Native Python)
=====================================================================
Pure Python implementation of a quantitative signal processing pipeline.
No external dependencies beyond the Python standard library.

Based on Grinold & Kahn's "Active Portfolio Management" alpha combination
methodology, with extensions for HFT signal processing, Kelly sizing,
and risk management.

Classes (14+):
    1. Signal                    — dataclass for individual signal metadata
    2. SignalCollector           — collect, validate, clean, demean, normalize
    3. ICCalculator              — Information Coefficient & correlation matrix
    4. AlphaCombinationEngine    — 11-step Grinold & Kahn combination engine
    5. InformationRatioEngine    — IR = IC × sqrt(N_effective)
    6. CorrelationAnalyzer       — detect shared variance, penalize correlation
    7. SignalCategoryRegistry    — 5-category signal taxonomy & routing
    8. PredictionMarketStub      — Polymarket-style signal integration
    9. PositionSizer             — Empirical Kelly Criterion + MC adjustment
   10. RiskManager               — drawdown limits, leverage, stop-loss
   11. BacktestEngineStub        — walk-forward backtest & Sharpe calc
   12. HFTKernelBridge           — bridge to event_bus & service_registry
   13. QuantSignalEngine         — main orchestrator
   14+ Supporting helpers       — StatisticsEngine, SignalValidator, etc.

Author: Magnatrix-OS Layer 8
"""

from __future__ import annotations

import math
import random
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


# =============================================================================
# PART 1 — Core Signal Infrastructure (Lines ~1-500)
# =============================================================================


class SignalCategory(Enum):
    """Five canonical signal categories for quantitative trading."""
    MOMENTUM = auto()
    MEAN_REVERSION = auto()
    VOLATILITY = auto()
    FACTOR = auto()
    MICROSTRUCTURE = auto()

    @classmethod
    def from_string(cls, s: str) -> "SignalCategory":
        mapping = {
            "momentum": cls.MOMENTUM,
            "mean_reversion": cls.MEAN_REVERSION,
            "volatility": cls.VOLATILITY,
            "factor": cls.FACTOR,
            "microstructure": cls.MICROSTRUCTURE,
        }
        return mapping.get(s.lower(), cls.MOMENTUM)


@dataclass
class Signal:
    """
    Core dataclass representing a quantitative trading signal.

    Attributes:
        name: Unique identifier for the signal.
        category: Taxonomic category (momentum/mean_reversion/etc).
        ic: Information Coefficient — correlation between signal and forward returns.
        returns_series: Historical returns vector (list of floats).
        weight: Current portfolio weight assigned to this signal.
        confidence: Confidence score [0.0, 1.0] in signal quality.
        metadata: Optional extra data (timestamp, source, etc).
    """
    name: str
    category: SignalCategory
    ic: float
    returns_series: List[float] = field(default_factory=list)
    weight: float = 0.0
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.category, SignalCategory):
            self.category = SignalCategory.from_string(str(self.category))
        # Clamp confidence
        self.confidence = max(0.0, min(1.0, self.confidence))
        # Ensure IC is realistic
        self.ic = max(-1.0, min(1.0, self.ic))

    @property
    def volatility(self) -> float:
        """Sample standard deviation of returns series."""
        if len(self.returns_series) < 2:
            return 0.0
        mean = sum(self.returns_series) / len(self.returns_series)
        variance = sum((r - mean) ** 2 for r in self.returns_series) / (len(self.returns_series) - 1)
        return math.sqrt(variance)

    @property
    def sharpe_stub(self) -> float:
        """Sharpe-like ratio: mean return / volatility."""
        vol = self.volatility
        if vol < 1e-12 or len(self.returns_series) == 0:
            return 0.0
        mean = sum(self.returns_series) / len(self.returns_series)
        return mean / vol

    def zscore_latest(self) -> float:
        """Z-score of the most recent observation."""
        if len(self.returns_series) < 2:
            return 0.0
        mean = sum(self.returns_series) / len(self.returns_series)
        vol = self.volatility
        if vol < 1e-12:
            return 0.0
        return (self.returns_series[-1] - mean) / vol


class SignalValidator:
    """Validates individual signals for structural integrity."""

    @staticmethod
    def validate(signal: Signal) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        if not signal.name or not isinstance(signal.name, str):
            errors.append("Signal must have a valid string name.")
        if len(signal.returns_series) < 3:
            errors.append(f"Signal {signal.name}: returns_series too short (<3).")
        if math.isnan(signal.ic) or math.isinf(signal.ic):
            errors.append(f"Signal {signal.name}: IC is NaN or Inf.")
        if any(math.isnan(r) or math.isinf(r) for r in signal.returns_series):
            errors.append(f"Signal {signal.name}: returns_series contains NaN/Inf.")
        return len(errors) == 0, errors


class StatisticsEngine:
    """Pure Python statistical utilities (no numpy/sklearn)."""

    @staticmethod
    def mean(data: List[float]) -> float:
        if not data:
            return 0.0
        return sum(data) / len(data)

    @staticmethod
    def variance(data: List[float], sample: bool = True) -> float:
        if len(data) < 2:
            return 0.0
        m = StatisticsEngine.mean(data)
        ss = sum((x - m) ** 2 for x in data)
        denom = len(data) - 1 if sample else len(data)
        return ss / denom

    @staticmethod
    def std(data: List[float], sample: bool = True) -> float:
        return math.sqrt(StatisticsEngine.variance(data, sample))

    @staticmethod
    def correlation(a: List[float], b: List[float]) -> float:
        """Pearson correlation coefficient between two equal-length series."""
        n = len(a)
        if n == 0 or n != len(b):
            return 0.0
        ma, mb = StatisticsEngine.mean(a), StatisticsEngine.mean(b)
        sa = StatisticsEngine.std(a, sample=False)
        sb = StatisticsEngine.std(b, sample=False)
        if sa < 1e-12 or sb < 1e-12:
            return 0.0
        cov = sum((a[i] - ma) * (b[i] - mb) for i in range(n)) / n
        return cov / (sa * sb)

    @staticmethod
    def covariance_matrix(vectors: List[List[float]]) -> List[List[float]]:
        """Compute covariance matrix for a list of equal-length vectors."""
        n = len(vectors)
        if n == 0:
            return []
        mat = [[0.0] * n for _ in range(n)]
        means = [StatisticsEngine.mean(v) for v in vectors]
        for i in range(n):
            for j in range(n):
                if len(vectors[i]) != len(vectors[j]):
                    mat[i][j] = 0.0
                    continue
                length = len(vectors[i])
                cov = sum((vectors[i][k] - means[i]) * (vectors[j][k] - means[j]) for k in range(length)) / length
                mat[i][j] = cov
        return mat

    @staticmethod
    def correlation_matrix(vectors: List[List[float]]) -> List[List[float]]:
        """Compute correlation matrix for a list of equal-length vectors."""
        cov = StatisticsEngine.covariance_matrix(vectors)
        n = len(cov)
        if n == 0:
            return []
        stds = [math.sqrt(cov[i][i]) for i in range(n)]
        corr = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(n):
                if stds[i] < 1e-12 or stds[j] < 1e-12:
                    corr[i][j] = 0.0
                else:
                    corr[i][j] = cov[i][j] / (stds[i] * stds[j])
        return corr

    @staticmethod
    def demean(data: List[float]) -> List[float]:
        m = StatisticsEngine.mean(data)
        return [x - m for x in data]

    @staticmethod
    def serial_demean(series_list: List[List[float]]) -> List[List[float]]:
        """Demean each series individually (serial demeaning)."""
        return [StatisticsEngine.demean(s) for s in series_list]

    @staticmethod
    def cross_sectional_demean(matrix: List[List[float]]) -> List[List[float]]:
        """Cross-sectional demeaning: at each time step, demean across signals."""
        if not matrix or not matrix[0]:
            return matrix
        n_signals = len(matrix)
        n_periods = len(matrix[0])
        result = [[0.0] * n_periods for _ in range(n_signals)]
        for t in range(n_periods):
            col = [matrix[i][t] for i in range(n_signals)]
            m = StatisticsEngine.mean(col)
            for i in range(n_signals):
                result[i][t] = matrix[i][t] - m
        return result

    @staticmethod
    def zscore_normalize(data: List[float]) -> List[float]:
        m = StatisticsEngine.mean(data)
        s = StatisticsEngine.std(data, sample=False)
        if s < 1e-12:
            return [0.0] * len(data)
        return [(x - m) / s for x in data]

    @staticmethod
    def drop_last(data: List[float], n: int = 1) -> List[float]:
        return data[:-n] if len(data) > n else []

    @staticmethod
    def regression_residuals(y: List[float], x: List[float]) -> List[float]:
        """Simple OLS residual: y = beta * x + alpha. Returns residuals."""
        if len(y) != len(x) or len(y) < 2:
            return [0.0] * len(y)
        mx, my = StatisticsEngine.mean(x), StatisticsEngine.mean(y)
        ss_xx = sum((xi - mx) ** 2 for xi in x)
        if ss_xx < 1e-12:
            return [yi - my for yi in y]
        ss_xy = sum((x[i] - mx) * (y[i] - my) for i in range(len(x)))
        beta = ss_xy / ss_xx
        alpha = my - beta * mx
        return [y[i] - (alpha + beta * x[i]) for i in range(len(y))]


class SignalCollector:
    """
    Collects N signals, validates them, cleans missing data,
    applies serial demeaning and normalization.
    """

    def __init__(self, min_observations: int = 10):
        self.signals: List[Signal] = []
        self.min_observations = min_observations
        self.validator = SignalValidator()
        self.stats = StatisticsEngine()

    def add_signal(self, signal: Signal) -> bool:
        valid, errors = self.validator.validate(signal)
        if not valid:
            # Log errors to signal metadata for traceability
            signal.metadata["validation_errors"] = errors
            return False
        self.signals.append(signal)
        return True

    def add_signals(self, signals: List[Signal]) -> Tuple[int, int]:
        accepted = 0
        rejected = 0
        for sig in signals:
            if self.add_signal(sig):
                accepted += 1
            else:
                rejected += 1
        return accepted, rejected

    def clean_missing_data(self) -> None:
        """
        Align all signals to the same length by trimming to the shortest series.
        Also removes any NaN-like values (represented as None or extreme values).
        """
        if not self.signals:
            return
        min_len = min(len(s.returns_series) for s in self.signals)
        for sig in self.signals:
            # Trim to common length
            sig.returns_series = sig.returns_series[:min_len]
            # Replace any suspicious extreme values with 0.0 (stub cleaning)
            sig.returns_series = [
                0.0 if (math.isnan(r) or math.isinf(r) or abs(r) > 1e6) else r
                for r in sig.returns_series
            ]

    def serial_demean(self) -> List[List[float]]:
        """Apply serial demeaning to all signal return series."""
        series = [s.returns_series[:] for s in self.signals]
        return self.stats.serial_demean(series)

    def normalize_signals(self) -> List[List[float]]:
        """Z-score normalize each signal's returns series."""
        series = [s.returns_series[:] for s in self.signals]
        demeaned = self.stats.serial_demean(series)
        normalized = []
        for s in demeaned:
            z = self.stats.zscore_normalize(s)
            normalized.append(z)
        return normalized

    def get_signal_matrix(self) -> List[List[float]]:
        """Return returns matrix: rows = signals, cols = time periods."""
        return [s.returns_series[:] for s in self.signals]

    def summary(self) -> Dict[str, Any]:
        return {
            "count": len(self.signals),
            "min_observations": self.min_observations,
            "categories": list(set(s.category.name for s in self.signals)),
            "avg_ic": self.stats.mean([s.ic for s in self.signals]),
            "avg_volatility": self.stats.mean([s.volatility for s in self.signals]),
        }


class ICCalculator:
    """
    Calculates Information Coefficient per signal, correlation matrix
    across signals, and detects shared variance.
    """

    def __init__(self):
        self.stats = StatisticsEngine()
        self.ics: Dict[str, float] = {}
        self.correlation_matrix: List[List[float]] = []
        self.shared_variance_detected: bool = False

    def calculate_ic(self, signal: Signal, forward_returns: List[float]) -> float:
        """
        Calculate Information Coefficient: correlation between signal
        returns and forward returns.
        """
        if len(signal.returns_series) != len(forward_returns) or len(signal.returns_series) < 3:
            return 0.0
        ic = self.stats.correlation(signal.returns_series, forward_returns)
        self.ics[signal.name] = ic
        return ic

    def calculate_all_ics(self, signals: List[Signal], forward_returns: List[float]) -> Dict[str, float]:
        for sig in signals:
            self.calculate_ic(sig, forward_returns)
        return self.ics

    def calculate_correlation_matrix(self, signals: List[Signal]) -> List[List[float]]:
        vectors = [s.returns_series for s in signals]
        self.correlation_matrix = self.stats.correlation_matrix(vectors)
        return self.correlation_matrix

    def detect_shared_variance(self, threshold: float = 0.7) -> List[Tuple[int, int, float]]:
        """Return pairs of signal indices with correlation above threshold."""
        pairs = []
        n = len(self.correlation_matrix)
        for i in range(n):
            for j in range(i + 1, n):
                if abs(self.correlation_matrix[i][j]) > threshold:
                    pairs.append((i, j, self.correlation_matrix[i][j]))
        self.shared_variance_detected = len(pairs) > 0
        return pairs

    def summary(self) -> Dict[str, Any]:
        return {
            "ics": self.ics,
            "shared_variance_detected": self.shared_variance_detected,
            "high_correlation_pairs": len(self.detect_shared_variance(0.7)),
        }


class AlphaCombinationEngine:
    """
    Implements the 11-step Grinold & Kahn alpha combination engine.

    Steps:
        1. Collect historical returns R(i,s)
        2. Serial demeaning
        3. Sample variance per signal
        4. Normalize (z-score)
        5. Drop most recent observation
        6. Cross-sectional demeaning
        7. Drop one more period
        8. Expected forward return
        9. Regress E_normalized on Lambda → residuals = independent contribution
        10. Weight = residual / sigma (high edge + low noise = more weight)
        11. Normalize abs(weights) = 1
    """

    def __init__(self, lookback_d: int = 20):
        self.lookback_d = lookback_d
        self.stats = StatisticsEngine()
        self.weights: List[float] = []
        self.residuals: List[float] = []
        self.lambda_matrix: List[List[float]] = []

    def run(self, returns_matrix: List[List[float]]) -> List[float]:
        """
        returns_matrix: rows = signals, cols = time periods.
        Returns: list of weights (one per signal), |weights| sum to 1.
        """
        if not returns_matrix or not returns_matrix[0]:
            return []
        n_signals = len(returns_matrix)
        n_periods = len(returns_matrix[0])
        if n_periods < self.lookback_d + 4:
            # Not enough data — fall back to equal weights
            return [1.0 / n_signals] * n_signals

        # Step 1: R(i,s) is already in returns_matrix
        # Step 2: Serial demeaning
        X = self.stats.serial_demean(returns_matrix)

        # Step 3: Sample variance per signal
        sigmas = [self.stats.std(row, sample=True) for row in X]

        # Step 4: Normalize (z-score) per signal
        Y = []
        for i in range(n_signals):
            if sigmas[i] < 1e-12:
                Y.append([0.0] * n_periods)
            else:
                Y.append([x / sigmas[i] for x in X[i]])

        # Step 5: Drop most recent observation
        Y = [self.stats.drop_last(row, 1) for row in Y]
        current_periods = n_periods - 1

        # Step 6: Cross-sectional demeaning
        Lambda = self.stats.cross_sectional_demean(Y)

        # Step 7: Drop one more period
        Lambda = [self.stats.drop_last(row, 1) for row in Lambda]
        current_periods -= 1

        # Step 8: Expected forward return from recent lookback
        # Use the dropped periods as "recent" for expectation
        recent_periods = min(self.lookback_d, current_periods)
        recent = [returns_matrix[i][-recent_periods:] for i in range(n_signals)]
        E = []
        for i in range(n_signals):
            mu = self.stats.mean(recent[i])
            if sigmas[i] < 1e-12:
                E.append(0.0)
            else:
                E.append(mu / sigmas[i])

        # Step 9: Regress E on Lambda → residuals = independent contribution
        # For each signal, we use the average Lambda value as predictor
        lambda_avg = [self.stats.mean(Lambda[i]) for i in range(n_signals)]
        self.residuals = self.stats.regression_residuals(E, lambda_avg)

        # Step 10: Weight = residual / sigma
        w = []
        for i in range(n_signals):
            if sigmas[i] < 1e-12:
                w.append(0.0)
            else:
                w.append(self.residuals[i] / sigmas[i])

        # Step 11: Normalize abs(weights) = 1
        abs_sum = sum(abs(x) for x in w)
        if abs_sum < 1e-12:
            self.weights = [1.0 / n_signals] * n_signals
        else:
            self.weights = [x / abs_sum for x in w]
        return self.weights

    def summary(self) -> Dict[str, Any]:
        return {
            "lookback_d": self.lookback_d,
            "weights": self.weights,
            "residuals": self.residuals,
            "weight_count": len(self.weights),
        }


class InformationRatioEngine:
    """
    Information Ratio = IC × sqrt(N_effective),
    where N_effective accounts for correlation between signals.
    """

    def __init__(self):
        self.stats = StatisticsEngine()
        self.ir: float = 0.0
        self.n_effective: float = 0.0

    def calculate(self, ics: List[float], correlation_matrix: List[List[float]]) -> float:
        n = len(ics)
        if n == 0:
            self.ir = 0.0
            self.n_effective = 0.0
            return 0.0

        avg_ic = self.stats.mean(ics)

        # Calculate N_effective using correlation penalty
        # N_eff = n / (1 + (n-1) * avg_correlation)
        if n > 1 and len(correlation_matrix) == n:
            off_diag = []
            for i in range(n):
                for j in range(i + 1, n):
                    off_diag.append(correlation_matrix[i][j])
            avg_corr = self.stats.mean(off_diag) if off_diag else 0.0
            self.n_effective = n / (1.0 + (n - 1.0) * abs(avg_corr))
        else:
            self.n_effective = float(n)

        self.ir = avg_ic * math.sqrt(max(0.0, self.n_effective))
        return self.ir

    def summary(self) -> Dict[str, Any]:
        return {
            "information_ratio": self.ir,
            "n_effective": self.n_effective,
            "n_raw": int(self.n_effective) if self.n_effective == int(self.n_effective) else None,
        }


class CorrelationAnalyzer:
    """
    Detects shared variance, calculates effective independent signal count,
    and penalizes highly correlated signals.
    """

    def __init__(self, high_corr_threshold: float = 0.7):
        self.threshold = high_corr_threshold
        self.stats = StatisticsEngine()
        self.correlation_matrix: List[List[float]] = []
        self.shared_pairs: List[Tuple[int, int, float]] = []
        self.effective_count: float = 0.0
        self.penalty_weights: List[float] = []

    def analyze(self, signals: List[Signal]) -> Dict[str, Any]:
        vectors = [s.returns_series for s in signals]
        self.correlation_matrix = self.stats.correlation_matrix(vectors)
        n = len(signals)

        # Detect shared variance
        self.shared_pairs = []
        for i in range(n):
            for j in range(i + 1, n):
                corr = self.correlation_matrix[i][j]
                if abs(corr) > self.threshold:
                    self.shared_pairs.append((i, j, corr))

        # Effective independent count: n / (1 + avg_pairwise_corr * (n-1))
        if n > 1:
            off_diag = []
            for i in range(n):
                for j in range(i + 1, n):
                    off_diag.append(self.correlation_matrix[i][j])
            avg_corr = self.stats.mean(off_diag) if off_diag else 0.0
            self.effective_count = n / (1.0 + abs(avg_corr) * (n - 1.0))
        else:
            self.effective_count = float(n)

        # Penalty weights: penalize signals that are highly correlated with many others
        correlation_counts = [0] * n
        for i, j, _ in self.shared_pairs:
            correlation_counts[i] += 1
            correlation_counts[j] += 1
        max_count = max(correlation_counts) if correlation_counts else 0
        if max_count > 0:
            self.penalty_weights = [
                1.0 / (1.0 + count) for count in correlation_counts
            ]
        else:
            self.penalty_weights = [1.0] * n

        return self.summary()

    def summary(self) -> Dict[str, Any]:
        return {
            "high_corr_threshold": self.threshold,
            "shared_variance_pairs": len(self.shared_pairs),
            "effective_independent_count": self.effective_count,
            "penalty_weights": self.penalty_weights,
            "shared_pairs_detail": self.shared_pairs,
        }


# =============================================================================
# PART 2 — Advanced Modules, Registry, Risk, Backtest, Bridge, Orchestrator
# =============================================================================


class SignalCategoryRegistry:
    """
    Five-category signal taxonomy: Momentum, Mean Reversion, Volatility,
    Factor, Microstructure. Register, validate, and route signals.
    """

    def __init__(self):
        self._registry: Dict[SignalCategory, List[Signal]] = {
            cat: [] for cat in SignalCategory
        }
        self._validators: Dict[SignalCategory, Callable[[Signal], bool]] = {}

    def register_signal(self, signal: Signal) -> bool:
        if not isinstance(signal.category, SignalCategory):
            return False
        self._registry[signal.category].append(signal)
        return True

    def register_validator(self, category: SignalCategory, fn: Callable[[Signal], bool]) -> None:
        self._validators[category] = fn

    def validate_category(self, category: SignalCategory) -> Tuple[bool, List[str]]:
        signals = self._registry.get(category, [])
        errors: List[str] = []
        validator = self._validators.get(category)
        for sig in signals:
            if validator and not validator(sig):
                errors.append(f"Signal {sig.name} failed category validation for {category.name}")
        return len(errors) == 0, errors

    def get_by_category(self, category: SignalCategory) -> List[Signal]:
        return self._registry.get(category, [])

    def route(self, signal: Signal) -> str:
        """Return routing hint based on category."""
        routing_map = {
            SignalCategory.MOMENTUM: "execution_layer_twap",
            SignalCategory.MEAN_REVERSION: "execution_layer_iceberg",
            SignalCategory.VOLATILITY: "risk_layer_vol_target",
            SignalCategory.FACTOR: "research_layer_factor",
            SignalCategory.MICROSTRUCTURE: "execution_layer_hft_direct",
        }
        return routing_map.get(signal.category, "default")

    def category_summary(self) -> Dict[str, Any]:
        return {
            cat.name: {
                "count": len(sigs),
                "avg_ic": StatisticsEngine.mean([s.ic for s in sigs]) if sigs else 0.0,
                "avg_vol": StatisticsEngine.mean([s.volatility for s in sigs]) if sigs else 0.0,
            }
            for cat, sigs in self._registry.items()
        }


class PredictionMarketStub:
    """
    Polymarket-style signal integration stub.
    Simulates cross-venue pricing, calibration, Bayesian updates,
    VPIN microstructure, and momentum near resolution.
    """

    def __init__(self):
        self.prices: Dict[str, float] = {}          # signal_name -> market-implied price
        self.calibration_scores: Dict[str, float] = {}  # signal_name -> calibration score
        self.beliefs: Dict[str, float] = {}         # Bayesian posterior belief
        self.vpin_estimates: Dict[str, float] = {}  # Volume-synchronized PIN

    def integrate_signal(self, signal: Signal, market_price: float = 0.5) -> float:
        """
        Integrate a signal into the prediction market framework.
        Returns updated belief probability.
        """
        name = signal.name
        prior = self.beliefs.get(name, 0.5)
        # Likelihood from signal IC (higher IC = stronger evidence)
        likelihood = 0.5 + 0.5 * signal.ic * signal.confidence
        # Bayesian update stub: P(H|E) ∝ P(E|H) * P(H)
        posterior = (likelihood * prior) / ((likelihood * prior) + ((1 - likelihood) * (1 - prior)))
        if math.isnan(posterior) or math.isinf(posterior):
            posterior = prior
        self.beliefs[name] = max(0.0, min(1.0, posterior))
        self.prices[name] = market_price
        return self.beliefs[name]

    def calibrate(self, signal: Signal, actual_outcome: float) -> float:
        """Update calibration score based on actual outcome (0 or 1)."""
        name = signal.name
        pred = self.beliefs.get(name, 0.5)
        # Brier score component: (pred - outcome)^2
        brier = (pred - actual_outcome) ** 2
        old_cal = self.calibration_scores.get(name, 1.0)
        # Exponential decay update
        new_cal = 0.9 * old_cal + 0.1 * (1.0 - brier)
        self.calibration_scores[name] = max(0.0, min(1.0, new_cal))
        return self.calibration_scores[name]

    def estimate_vpin(self, signal: Signal, volume_buckets: List[float]) -> float:
        """Volume-synchronized Probability of Informed Trading stub."""
        if len(volume_buckets) < 2:
            return 0.0
        # VPIN ≈ |buy_volume - sell_volume| / total_volume (simplified)
        total = sum(volume_buckets)
        if total < 1e-12:
            return 0.0
        # Assume alternating buy/sell buckets for stub
        buy_sum = sum(volume_buckets[i] for i in range(0, len(volume_buckets), 2))
        sell_sum = total - buy_sum
        vpin = abs(buy_sum - sell_sum) / total
        self.vpin_estimates[signal.name] = vpin
        return vpin

    def momentum_near_resolution(self, signal: Signal, time_to_resolution: float) -> float:
        """
        Return a momentum score that increases as resolution approaches.
        time_to_resolution: hours until event resolves.
        """
        if time_to_resolution <= 0:
            return 1.0
        # Decay function: momentum builds as t -> 0
        momentum = math.exp(-time_to_resolution / 24.0)  # 24h half-life
        return momentum * signal.confidence

    def summary(self) -> Dict[str, Any]:
        return {
            "beliefs": self.beliefs,
            "calibration_scores": self.calibration_scores,
            "vpin_estimates": self.vpin_estimates,
            "market_prices": self.prices,
        }


class PositionSizer:
    """
    Empirical Kelly Criterion with Monte Carlo uncertainty adjustment.

    Formula: f* = (p * b - q) / b * (1 - CV_edge)
    where:
        p = win probability
        b = win/loss payoff ratio
        q = 1 - p
        CV_edge = coefficient of variation of edge estimates
    """

    def __init__(self, n_monte_carlo: int = 1000):
        self.n_mc = n_monte_carlo
        self.stats = StatisticsEngine()
        self.f_kelly: float = 0.0
        self.f_adjusted: float = 0.0

    def empirical_kelly(
        self,
        returns: List[float],
        win_payoff: float = 1.0,
        loss_payoff: float = 1.0,
    ) -> Tuple[float, float]:
        """
        Calculate Kelly fraction from empirical return distribution.
        Returns (raw_kelly, adjusted_kelly).
        """
        if not returns:
            return 0.0, 0.0
        wins = [r for r in returns if r > 0]
        losses = [r for r in returns if r <= 0]
        n = len(returns)
        p = len(wins) / n if n > 0 else 0.5
        q = 1.0 - p

        # Payoff ratio b = avg_win / avg_loss
        avg_win = self.stats.mean(wins) if wins else 0.0
        avg_loss = abs(self.stats.mean(losses)) if losses else 1.0
        b = avg_win / avg_loss if avg_loss > 1e-12 else 1.0

        if b < 1e-12:
            self.f_kelly = 0.0
            self.f_adjusted = 0.0
            return 0.0, 0.0

        # Kelly fraction: f* = (p*b - q) / b
        f_raw = (p * b - q) / b
        f_raw = max(0.0, min(1.0, f_raw))
        self.f_kelly = f_raw

        # Monte Carlo uncertainty adjustment
        mc_estimates = []
        for _ in range(self.n_mc):
            sample = [random.choice(returns) for _ in range(len(returns))]
            sample_wins = [r for r in sample if r > 0]
            sample_losses = [r for r in sample if r <= 0]
            sn = len(sample)
            sp = len(sample_wins) / sn if sn > 0 else 0.5
            sq = 1.0 - sp
            s_avg_win = self.stats.mean(sample_wins) if sample_wins else 0.0
            s_avg_loss = abs(self.stats.mean(sample_losses)) if sample_losses else 1.0
            sb = s_avg_win / s_avg_loss if s_avg_loss > 1e-12 else 1.0
            if sb > 1e-12:
                sf = (sp * sb - sq) / sb
                mc_estimates.append(max(0.0, min(1.0, sf)))

        if mc_estimates:
            mean_mc = self.stats.mean(mc_estimates)
            std_mc = self.stats.std(mc_estimates, sample=True)
            cv_edge = std_mc / mean_mc if mean_mc > 1e-12 else 0.0
            self.f_adjusted = f_raw * (1.0 - min(cv_edge, 0.99))
        else:
            self.f_adjusted = f_raw

        return self.f_kelly, self.f_adjusted

    def size_position(self, capital: float, signal: Signal) -> float:
        """Return dollar position size for a signal."""
        f_kelly, f_adj = self.empirical_kelly(signal.returns_series)
        # Scale by confidence and IC
        scale = signal.confidence * abs(signal.ic)
        return capital * f_adj * scale

    def summary(self) -> Dict[str, Any]:
        return {
            "f_kelly_raw": self.f_kelly,
            "f_kelly_adjusted": self.f_adjusted,
            "n_monte_carlo": self.n_mc,
        }


class RiskManager:
    """
    Manages max drawdown limits, position size caps, correlation-based
    leverage adjustment, and stop-loss engine.
    """

    def __init__(
        self,
        max_drawdown: float = 0.15,
        max_position_pct: float = 0.20,
        max_leverage: float = 3.0,
        stop_loss_pct: float = 0.05,
    ):
        self.max_drawdown = max_drawdown
        self.max_position_pct = max_position_pct
        self.max_leverage = max_leverage
        self.stop_loss_pct = stop_loss_pct
        self.peak_pnl = 0.0
        self.current_drawdown = 0.0
        self.stopped_signals: set = set()

    def check_drawdown(self, cumulative_pnl: float) -> bool:
        """Return True if within drawdown limits, False if breached."""
        self.peak_pnl = max(self.peak_pnl, cumulative_pnl)
        dd = (self.peak_pnl - cumulative_pnl) / max(abs(self.peak_pnl), 1e-12)
        self.current_drawdown = dd
        return dd <= self.max_drawdown

    def cap_position(self, raw_size: float, capital: float) -> float:
        """Cap position size to max_position_pct of capital."""
        max_size = capital * self.max_position_pct
        if raw_size > max_size:
            return max_size
        if raw_size < -max_size:
            return -max_size
        return raw_size

    def adjust_leverage(self, correlation_matrix: List[List[float]]) -> float:
        """Reduce leverage when correlations are high."""
        n = len(correlation_matrix)
        if n <= 1:
            return self.max_leverage
        off_diag = []
        for i in range(n):
            for j in range(i + 1, n):
                off_diag.append(abs(correlation_matrix[i][j]))
        avg_corr = StatisticsEngine.mean(off_diag) if off_diag else 0.0
        # Leverage scales inversely with avg correlation
        leverage = self.max_leverage / (1.0 + avg_corr * 2.0)
        return min(leverage, self.max_leverage)

    def check_stop_loss(self, signal: Signal, entry_price: float, current_price: float) -> bool:
        """Return True if stop-loss triggered."""
        if entry_price == 0:
            return False
        loss_pct = (entry_price - current_price) / entry_price
        if loss_pct >= self.stop_loss_pct:
            self.stopped_signals.add(signal.name)
            return True
        return False

    def get_allowed_signals(self, signals: List[Signal]) -> List[Signal]:
        """Filter out stopped signals."""
        return [s for s in signals if s.name not in self.stopped_signals]

    def summary(self) -> Dict[str, Any]:
        return {
            "max_drawdown_limit": self.max_drawdown,
            "current_drawdown": self.current_drawdown,
            "max_position_pct": self.max_position_pct,
            "max_leverage": self.max_leverage,
            "stopped_signals": list(self.stopped_signals),
        }


class BacktestEngineStub:
    """
    Walk-forward backtest engine with rolling window, out-of-sample
    validation, and Sharpe ratio calculation.
    """

    def __init__(self, train_window: int = 60, test_window: int = 20):
        self.train_window = train_window
        self.test_window = test_window
        self.stats = StatisticsEngine()
        self.oos_returns: List[float] = []
        self.sharpe_ratio: float = 0.0
        self.max_drawdown: float = 0.0

    def walk_forward(
        self,
        returns_matrix: List[List[float]],
        combination_engine: AlphaCombinationEngine,
    ) -> List[float]:
        """
        Run walk-forward backtest: train on train_window, test on test_window,
        roll forward. Returns out-of-sample portfolio returns.
        """
        n_signals = len(returns_matrix)
        n_periods = len(returns_matrix[0]) if returns_matrix else 0
        oos = []
        peak = 0.0
        cum_pnl = 0.0

        for start in range(0, n_periods - self.train_window - self.test_window + 1, self.test_window):
            train_end = start + self.train_window
            test_end = train_end + self.test_window

            # Slice training data
            train_slice = [r[start:train_end] for r in returns_matrix]
            # Calculate weights on training data
            weights = combination_engine.run(train_slice)

            # Apply to test data
            test_slice = [r[train_end:test_end] for r in returns_matrix]
            for t in range(len(test_slice[0])):
                day_ret = sum(weights[i] * test_slice[i][t] for i in range(n_signals))
                oos.append(day_ret)
                cum_pnl += day_ret
                peak = max(peak, cum_pnl)
                dd = (peak - cum_pnl) / max(abs(peak), 1e-12)
                self.max_drawdown = max(self.max_drawdown, dd)

        self.oos_returns = oos
        self._calculate_sharpe()
        return oos

    def _calculate_sharpe(self, risk_free_rate: float = 0.0) -> float:
        if not self.oos_returns:
            self.sharpe_ratio = 0.0
            return 0.0
        mean_ret = self.stats.mean(self.oos_returns)
        std_ret = self.stats.std(self.oos_returns, sample=True)
        if std_ret < 1e-12:
            self.sharpe_ratio = 0.0
        else:
            self.sharpe_ratio = (mean_ret - risk_free_rate) / std_ret * math.sqrt(252)
        return self.sharpe_ratio

    def summary(self) -> Dict[str, Any]:
        return {
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "oos_return_count": len(self.oos_returns),
            "total_oos_return": sum(self.oos_returns) if self.oos_returns else 0.0,
        }


class HFTKernelBridge:
    """
    Bridge to the HFT kernel event_bus and service_registry.
    Provides stubs for publishing signals and registering services.
    """

    def __init__(self):
        self.event_bus: List[Dict[str, Any]] = []
        self.service_registry: Dict[str, Any] = {}
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)

    def publish(self, event_type: str, payload: Dict[str, Any]) -> None:
        event = {
            "type": event_type,
            "timestamp": time.time(),
            "payload": payload,
        }
        self.event_bus.append(event)
        for fn in self.subscribers.get(event_type, []):
            fn(event)

    def subscribe(self, event_type: str, callback: Callable[[Dict[str, Any]], None]) -> None:
        self.subscribers[event_type].append(callback)

    def register_service(self, name: str, instance: Any) -> None:
        self.service_registry[name] = instance

    def get_service(self, name: str) -> Optional[Any]:
        return self.service_registry.get(name)

    def emit_signal_update(self, signal: Signal, weight: float) -> None:
        self.publish("signal_update", {
            "signal_name": signal.name,
            "category": signal.category.name,
            "weight": weight,
            "ic": signal.ic,
            "confidence": signal.confidence,
        })

    def emit_portfolio_rebalance(self, weights: Dict[str, float]) -> None:
        self.publish("portfolio_rebalance", {"weights": weights})

    def get_event_log(self) -> List[Dict[str, Any]]:
        return self.event_bus[:]


class QuantSignalEngine:
    """
    Main orchestrator — composes all modules, runs the signal pipeline,
    generates alpha, and outputs optimal weights.
    """

    def __init__(self, lookback_d: int = 20, capital: float = 1_000_000.0):
        self.capital = capital
        self.collector = SignalCollector(min_observations=lookback_d)
        self.ic_calc = ICCalculator()
        self.combiner = AlphaCombinationEngine(lookback_d=lookback_d)
        self.ir_engine = InformationRatioEngine()
        self.corr_analyzer = CorrelationAnalyzer(high_corr_threshold=0.7)
        self.registry = SignalCategoryRegistry()
        self.prediction_market = PredictionMarketStub()
        self.position_sizer = PositionSizer(n_monte_carlo=1000)
        self.risk_manager = RiskManager(
            max_drawdown=0.15,
            max_position_pct=0.20,
            max_leverage=3.0,
            stop_loss_pct=0.05,
        )
        self.backtest = BacktestEngineStub(train_window=60, test_window=20)
        self.bridge = HFTKernelBridge()

        # Register services
        self.bridge.register_service("signal_collector", self.collector)
        self.bridge.register_service("ic_calculator", self.ic_calc)
        self.bridge.register_service("alpha_combiner", self.combiner)
        self.bridge.register_service("risk_manager", self.risk_manager)

    def add_signals(self, signals: List[Signal]) -> None:
        accepted, rejected = self.collector.add_signals(signals)
        for sig in signals:
            self.registry.register_signal(sig)
            self.prediction_market.integrate_signal(sig)
        self.bridge.publish("signals_added", {"accepted": accepted, "rejected": rejected})

    def run_pipeline(self) -> Dict[str, Any]:
        """
        Run the full signal pipeline and return portfolio composition.
        """
        # Step 1: Clean and prepare
        self.collector.clean_missing_data()
        signals = self.collector.signals
        if not signals:
            return {"error": "No valid signals"}

        # Step 2: Build returns matrix
        returns_matrix = self.collector.get_signal_matrix()

        # Step 3: Correlation analysis
        corr_summary = self.corr_analyzer.analyze(signals)
        corr_matrix = self.corr_analyzer.correlation_matrix

        # Step 4: IC calculation (use forward returns = last column as proxy)
        forward_returns = [r[-1] for r in returns_matrix]
        ics = self.ic_calc.calculate_all_ics(signals, forward_returns)
        self.ic_calc.calculate_correlation_matrix(signals)

        # Step 5: Alpha combination
        weights = self.combiner.run(returns_matrix)

        # Step 6: Apply correlation penalty
        penalty = self.corr_analyzer.penalty_weights
        adjusted_weights = [weights[i] * penalty[i] for i in range(len(weights))]
        abs_sum = sum(abs(w) for w in adjusted_weights)
        if abs_sum > 1e-12:
            adjusted_weights = [w / abs_sum for w in adjusted_weights]
        else:
            adjusted_weights = [1.0 / len(signals)] * len(signals)

        # Step 7: Information Ratio
        ic_values = [ics.get(s.name, 0.0) for s in signals]
        ir = self.ir_engine.calculate(ic_values, corr_matrix)

        # Step 8: Position sizing
        positions: Dict[str, float] = {}
        for i, sig in enumerate(signals):
            raw_size = self.position_sizer.size_position(self.capital, sig)
            capped = self.risk_manager.cap_position(raw_size, self.capital)
            positions[sig.name] = capped * adjusted_weights[i]

        # Step 9: Risk check
        allowed_signals = self.risk_manager.get_allowed_signals(signals)
        allowed_names = {s.name for s in allowed_signals}
        positions = {k: v for k, v in positions.items() if k in allowed_names}

        # Step 10: Backtest stub
        oos_returns = self.backtest.walk_forward(returns_matrix, self.combiner)

        # Step 11: Emit events
        for i, sig in enumerate(signals):
            self.bridge.emit_signal_update(sig, adjusted_weights[i])
        self.bridge.emit_portfolio_rebalance(positions)

        return {
            "weights": {s.name: adjusted_weights[i] for i, s in enumerate(signals)},
            "positions": positions,
            "information_ratio": ir,
            "n_effective": self.ir_engine.n_effective,
            "sharpe_ratio": self.backtest.sharpe_ratio,
            "max_drawdown": self.backtest.max_drawdown,
            "correlation_summary": corr_summary,
            "ic_summary": self.ic_calc.summary(),
            "risk_summary": self.risk_manager.summary(),
            "category_summary": self.registry.category_summary(),
            "prediction_market": self.prediction_market.summary(),
            "position_sizer": self.position_sizer.summary(),
        }

    def summary(self) -> Dict[str, Any]:
        return {
            "capital": self.capital,
            "signal_count": len(self.collector.signals),
            "pipeline_ready": len(self.collector.signals) >= 2,
        }


# =============================================================================
# DEMO
# =============================================================================

def generate_synthetic_returns(n_periods: int = 120, ic_target: float = 0.05, seed: int = 42) -> List[float]:
    """Generate synthetic returns with slight directional bias."""
    random.seed(seed)
    returns = []
    bias = ic_target * 0.02  # Small directional bias
    for _ in range(n_periods):
        r = random.gauss(bias, 0.02)
        returns.append(r)
    return returns


def demo() -> None:
    """
    Demo: create 10 signals (IC 0.03-0.12) → run combination engine
    → show optimal weights → calculate IR → run Kelly sizing
    → show risk-adjusted portfolio.
    """
    print("=" * 70)
    print("MAGNATRIX-OS Layer 8 — HFT Quant Signal Engine Demo")
    print("=" * 70)

    engine = QuantSignalEngine(lookback_d=20, capital=1_000_000.0)

    categories = [
        SignalCategory.MOMENTUM,
        SignalCategory.MEAN_REVERSION,
        SignalCategory.VOLATILITY,
        SignalCategory.FACTOR,
        SignalCategory.MICROSTRUCTURE,
    ]

    signals = []
    for i in range(10):
        ic = 0.03 + (i * 0.01)  # 0.03 to 0.12
        cat = categories[i % len(categories)]
        name = f"signal_{cat.name.lower()}_{i+1}"
        returns = generate_synthetic_returns(n_periods=120, ic_target=ic, seed=100 + i)
        sig = Signal(
            name=name,
            category=cat,
            ic=ic,
            returns_series=returns,
            weight=0.0,
            confidence=0.7 + (i * 0.03),
            metadata={"source": "synthetic", "version": "demo_v1"},
        )
        signals.append(sig)

    print(f"\n[1] Created {len(signals)} synthetic signals:")
    for s in signals:
        print(f"    • {s.name:35s} | IC={s.ic:.3f} | {s.category.name:15s} | conf={s.confidence:.2f}")

    engine.add_signals(signals)
    print(f"\n[2] SignalCollector summary: {engine.collector.summary()}")

    result = engine.run_pipeline()

    print(f"\n[3] OPTIMAL WEIGHTS (Grinold & Kahn 11-step combination):")
    for name, w in sorted(result["weights"].items(), key=lambda x: -abs(x[1])):
        bar = "█" * int(abs(w) * 40)
        print(f"    • {name:35s} | weight={w:+.4f} | {bar}")

    print(f"\n[4] INFORMATION RATIO:")
    print(f"    • IR = {result['information_ratio']:.4f}")
    print(f"    • N_effective = {result['n_effective']:.2f}")

    print(f"\n[5] KELLY POSITION SIZING:")
    for name, pos in sorted(result["positions"].items(), key=lambda x: -abs(x[1])):
        print(f"    • {name:35s} | ${pos:,.2f}")

    print(f"\n[6] RISK-ADJUSTED PORTFOLIO:")
    print(f"    • Sharpe Ratio (OOS) = {result['sharpe_ratio']:.4f}")
    print(f"    • Max Drawdown       = {result['max_drawdown']:.4f}")

    print(f"\n[7] CORRELATION ANALYSIS:")
    corr = result["correlation_summary"]
    print(f"    • Shared variance pairs = {corr['shared_variance_pairs']}")
    print(f"    • Effective independent signals = {corr['effective_independent_count']:.2f}")

    print(f"\n[8] CATEGORY BREAKDOWN:")
    for cat_name, data in result["category_summary"].items():
        print(f"    • {cat_name:15s} | count={data['count']:2d} | avg_IC={data['avg_ic']:.4f} | avg_vol={data['avg_vol']:.4f}")

    print(f"\n[9] PREDICTION MARKET INTEGRATION:")
    pm = result["prediction_market"]
    for name in list(pm["beliefs"].keys())[:3]:
        print(f"    • {name:35s} | belief={pm['beliefs'][name]:.4f} | cal={pm['calibration_scores'].get(name, 0):.4f}")

    print(f"\n[10] EVENT BRIDGE LOG:")
    for ev in engine.bridge.get_event_log():
        print(f"    • [{ev['type']:20s}] @ {ev['timestamp']:.3f}")

    print("\n" + "=" * 70)
    print("Demo complete. Magnatrix-OS Layer 8 Signal Engine operational.")
    print("=" * 70)


if __name__ == "__main__":
    demo()


"""Quant Risk Metrics - Fixed-income risk metrics and portfolio analytics."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class RiskSnapshot:
    snapshot_id: str
    timestamp: float
    var_95: float = 0.0
    var_99: float = 0.0
    expected_shortfall: float = 0.0
    volatility: float = 0.0
    tracking_error: float = 0.0
    information_ratio: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp,
            "var_95": round(self.var_95, 4),
            "var_99": round(self.var_99, 4),
            "expected_shortfall": round(self.expected_shortfall, 4),
            "volatility": round(self.volatility, 4),
            "tracking_error": round(self.tracking_error, 4),
            "information_ratio": round(self.information_ratio, 4),
        }


@dataclass
class CorrelationMatrix:
    matrix_id: str
    assets: List[str] = field(default_factory=list)
    correlations: List[List[float]] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "matrix_id": self.matrix_id,
            "assets": self.assets,
            "correlations": [[round(c, 4) for c in row] for row in self.correlations],
        }


class QuantRiskMetrics:
    """Fixed-income risk metrics: VaR, ES, volatility, tracking error."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "quant_risk"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots: List[RiskSnapshot] = []
        self.correlations: Dict[str, CorrelationMatrix] = {}
        self._load_state()

    def _load_state(self) -> None:
        state_file = self.data_dir / "state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                for s in data.get("snapshots", []):
                    self.snapshots.append(RiskSnapshot(**s))
                for c in data.get("correlations", []):
                    self.correlations[c["matrix_id"]] = CorrelationMatrix(**c)
            except Exception:
                pass

    def _save_state(self) -> None:
        state_file = self.data_dir / "state.json"
        state = {
            "snapshots": [s.to_dict() for s in self.snapshots[-100:]],
            "correlations": [c.to_dict() for c in self.correlations.values()],
        }
        state_file.write_text(json.dumps(state, indent=2))

    def compute_var(self, returns: List[float], confidence: float = 0.95) -> float:
        """Compute historical VaR from return series."""
        if not returns:
            return 0.0
        sorted_returns = sorted(returns)
        idx = int((1.0 - confidence) * len(sorted_returns))
        idx = max(0, min(idx, len(sorted_returns) - 1))
        return round(sorted_returns[idx], 4)

    def compute_expected_shortfall(self, returns: List[float], confidence: float = 0.95) -> float:
        """Compute Expected Shortfall (CVaR)."""
        var = self.compute_var(returns, confidence)
        tail = [r for r in returns if r <= var]
        if not tail:
            return var
        return round(sum(tail) / len(tail), 4)

    def compute_volatility(self, returns: List[float], annualize: bool = True) -> float:
        """Compute annualized volatility from return series."""
        if len(returns) < 2:
            return 0.0
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / len(returns)
        vol = math.sqrt(variance)
        if annualize:
            vol *= math.sqrt(52)  # Weekly data
        return round(vol, 4)

    def compute_tracking_error(self, portfolio_returns: List[float], benchmark_returns: List[float]) -> float:
        """Compute tracking error (annualized standard deviation of excess returns)."""
        if len(portfolio_returns) != len(benchmark_returns) or len(portfolio_returns) < 2:
            return 0.0
        excess = [p - b for p, b in zip(portfolio_returns, benchmark_returns)]
        mean_excess = sum(excess) / len(excess)
        variance = sum((e - mean_excess) ** 2 for e in excess) / len(excess)
        return round(math.sqrt(variance) * math.sqrt(52), 4)

    def compute_information_ratio(self, portfolio_returns: List[float], benchmark_returns: List[float]) -> float:
        """Compute information ratio."""
        if len(portfolio_returns) != len(benchmark_returns) or len(portfolio_returns) < 2:
            return 0.0
        excess = [p - b for p, b in zip(portfolio_returns, benchmark_returns)]
        mean_excess = sum(excess) / len(excess)
        te = self.compute_tracking_error(portfolio_returns, benchmark_returns)
        if te == 0:
            return 0.0
        return round(mean_excess / te, 4)

    def analyze(self, portfolio_returns: List[float], benchmark_returns: Optional[List[float]] = None, timestamp: float = 0.0) -> RiskSnapshot:
        """Run full risk analysis."""
        var95 = self.compute_var(portfolio_returns, 0.95)
        var99 = self.compute_var(portfolio_returns, 0.99)
        es = self.compute_expected_shortfall(portfolio_returns, 0.95)
        vol = self.compute_volatility(portfolio_returns)
        te = self.compute_tracking_error(portfolio_returns, benchmark_returns or portfolio_returns)
        ir = self.compute_information_ratio(portfolio_returns, benchmark_returns or portfolio_returns)

        snap = RiskSnapshot(
            snapshot_id=f"risk_{int(timestamp)}_{len(self.snapshots)}",
            timestamp=timestamp,
            var_95=var95,
            var_99=var99,
            expected_shortfall=es,
            volatility=vol,
            tracking_error=te,
            information_ratio=ir,
        )
        self.snapshots.append(snap)
        self._save_state()
        return snap

    def compute_correlation(self, asset_returns: Dict[str, List[float]]) -> CorrelationMatrix:
        """Compute correlation matrix from asset return series."""
        assets = list(asset_returns.keys())
        n = len(assets)
        corrs = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]

        for i in range(n):
            for j in range(i + 1, n):
                r1 = asset_returns[assets[i]]
                r2 = asset_returns[assets[j]]
                if len(r1) != len(r2) or len(r1) < 2:
                    continue
                m1 = sum(r1) / len(r1)
                m2 = sum(r2) / len(r2)
                cov = sum((r1[k] - m1) * (r2[k] - m2) for k in range(len(r1))) / len(r1)
                std1 = math.sqrt(sum((r - m1) ** 2 for r in r1) / len(r1))
                std2 = math.sqrt(sum((r - m2) ** 2 for r in r2) / len(r2))
                if std1 > 0 and std2 > 0:
                    corrs[i][j] = corrs[j][i] = round(cov / (std1 * std2), 4)

        mat = CorrelationMatrix(
            matrix_id=f"corr_{'_'.join(assets)}_{len(self.correlations)}",
            assets=assets,
            correlations=corrs,
        )
        self.correlations[mat.matrix_id] = mat
        self._save_state()
        return mat

    def get_stats(self) -> Dict:
        avg_var = sum(s.var_95 for s in self.snapshots) / max(1, len(self.snapshots))
        return {
            "snapshots_total": len(self.snapshots),
            "correlation_matrices": len(self.correlations),
            "avg_var_95": round(avg_var, 4),
        }

    def to_dict(self) -> Dict:
        return {
            "snapshots": [s.to_dict() for s in self.snapshots[-20:]],
            "correlations": [c.to_dict() for c in self.correlations.values()],
            "stats": self.get_stats(),
        }


__all__ = ["QuantRiskMetrics", "RiskSnapshot", "CorrelationMatrix"]

"""Quant Bond Trading Strategy - Directional trading based on yield forecasts."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class TradeSignal:
    signal_id: str
    maturity_months: int
    direction: str  # long, short, hold
    confidence: float
    expected_return_bps: float
    timestamp: float

    def to_dict(self) -> Dict:
        return {
            "signal_id": self.signal_id,
            "maturity_months": self.maturity_months,
            "direction": self.direction,
            "confidence": round(self.confidence, 3),
            "expected_return_bps": round(self.expected_return_bps, 2),
            "timestamp": self.timestamp,
        }


@dataclass
class BacktestResult:
    result_id: str
    strategy_name: str
    total_return: float
    sharpe_ratio: float
    max_drawdown: float
    win_rate: float
    trades_total: int
    directional_accuracy: float
    period_start: str = ""
    period_end: str = ""

    def to_dict(self) -> Dict:
        return {
            "result_id": self.result_id,
            "strategy_name": self.strategy_name,
            "total_return": round(self.total_return, 4),
            "sharpe_ratio": round(self.sharpe_ratio, 4),
            "max_drawdown": round(self.max_drawdown, 4),
            "win_rate": round(self.win_rate, 4),
            "trades_total": self.trades_total,
            "directional_accuracy": round(self.directional_accuracy, 4),
            "period_start": self.period_start,
            "period_end": self.period_end,
        }


class QuantBondTradingStrategy:
    """Fixed-income trading strategy based on yield curve forecast direction."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "quant_strategy"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.signals: List[TradeSignal] = []
        self.backtests: Dict[str, BacktestResult] = {}
        self._load_state()

    def _load_state(self) -> None:
        state_file = self.data_dir / "state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                for s in data.get("signals", []):
                    self.signals.append(TradeSignal(**s))
                for b in data.get("backtests", []):
                    self.backtests[b["result_id"]] = BacktestResult(**b)
            except Exception:
                pass

    def _save_state(self) -> None:
        state_file = self.data_dir / "state.json"
        state = {
            "signals": [s.to_dict() for s in self.signals],
            "backtests": [b.to_dict() for b in self.backtests.values()],
        }
        state_file.write_text(json.dumps(state, indent=2))

    def generate_signals(self, current_rates: List[Dict], forecasted_rates: List[Dict], timestamp: float) -> List[TradeSignal]:
        """Generate trading signals based on forecasted vs current rates."""
        signals = []
        for cur in current_rates:
            mat = cur["maturity_months"]
            forecast = next((f for f in forecasted_rates if f.get("maturity_months") == mat), None)
            if forecast is None:
                continue
            rate_diff = forecast["rate_pct"] - cur["rate_pct"]
            if rate_diff < -0.05:  # Rates falling → long bonds (price rises)
                direction = "long"
                confidence = min(1.0, abs(rate_diff) * 5)
                exp_ret = abs(rate_diff) * 100  # in bps
            elif rate_diff > 0.05:  # Rates rising → short bonds (price falls)
                direction = "short"
                confidence = min(1.0, abs(rate_diff) * 5)
                exp_ret = abs(rate_diff) * 100
            else:
                direction = "hold"
                confidence = 0.3
                exp_ret = 0.0

            sig = TradeSignal(
                signal_id=f"sig_{mat}_{int(timestamp)}",
                maturity_months=mat,
                direction=direction,
                confidence=round(confidence, 3),
                expected_return_bps=round(exp_ret, 2),
                timestamp=timestamp,
            )
            signals.append(sig)
            self.signals.append(sig)
        self._save_state()
        return signals

    def backtest(self, historical_signals: List[TradeSignal], actual_returns: List[float], strategy_name: str = "dns_directional") -> BacktestResult:
        """Backtest trading strategy performance."""
        if not historical_signals or not actual_returns:
            return BacktestResult(result_id="empty", strategy_name=strategy_name, total_return=0.0, sharpe_ratio=0.0, max_drawdown=0.0, win_rate=0.0, trades_total=0, directional_accuracy=0.0)

        # Match signals to returns
        matched_returns = []
        wins = 0
        for i, sig in enumerate(historical_signals):
            if i < len(actual_returns):
                ret = actual_returns[i]
                if (sig.direction == "long" and ret > 0) or (sig.direction == "short" and ret < 0):
                    matched_returns.append(abs(ret) * sig.confidence)
                    wins += 1
                elif sig.direction == "hold":
                    matched_returns.append(0.0)
                else:
                    matched_returns.append(-abs(ret) * sig.confidence)

        total_return = sum(matched_returns)
        avg_return = total_return / max(1, len(matched_returns))
        variance = sum((r - avg_return) ** 2 for r in matched_returns) / max(1, len(matched_returns))
        std_dev = math.sqrt(variance) if variance > 0 else 0.001
        sharpe = avg_return / std_dev if std_dev > 0 else 0.0

        # Max drawdown
        cumulative = 0.0
        peak = 0.0
        max_dd = 0.0
        for r in matched_returns:
            cumulative += r
            if cumulative > peak:
                peak = cumulative
            dd = peak - cumulative
            if dd > max_dd:
                max_dd = dd

        win_rate = wins / max(1, len([s for s in historical_signals if s.direction != "hold"]))

        result = BacktestResult(
            result_id=f"bt_{strategy_name}_{len(self.backtests)}",
            strategy_name=strategy_name,
            total_return=round(total_return, 4),
            sharpe_ratio=round(sharpe, 4),
            max_drawdown=round(max_dd, 4),
            win_rate=round(win_rate, 4),
            trades_total=len(matched_returns),
            directional_accuracy=round(win_rate, 4),
        )
        self.backtests[result.result_id] = result
        self._save_state()
        return result

    def get_active_signals(self, max_age_sec: float = 86400) -> List[TradeSignal]:
        now = 0.0
        return [s for s in self.signals if now - s.timestamp < max_age_sec]

    def get_stats(self) -> Dict:
        total_backtests = len(self.backtests)
        avg_sharpe = sum(b.sharpe_ratio for b in self.backtests.values()) / max(1, total_backtests)
        return {
            "signals_total": len(self.signals),
            "backtests_total": total_backtests,
            "avg_sharpe_ratio": round(avg_sharpe, 4),
            "strategies": list(set(b.strategy_name for b in self.backtests.values())),
        }

    def to_dict(self) -> Dict:
        return {
            "signals": [s.to_dict() for s in self.signals[-100:]],
            "backtests": [b.to_dict() for b in self.backtests.values()],
            "stats": self.get_stats(),
        }


__all__ = ["QuantBondTradingStrategy", "TradeSignal", "BacktestResult"]

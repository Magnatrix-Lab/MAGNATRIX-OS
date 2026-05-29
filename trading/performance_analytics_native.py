#!/usr/bin/env python3
"""performance_analytics_native.py — MAGNATRIX-OS Trading Layer
Performance Analytics Engine.

Features:
  - Sharpe ratio, Sortino ratio, Calmar ratio, Omega ratio
  - Win rate, expectancy, profit factor, avg win/loss ratio
  - Max drawdown, underwater plot (drawdown depth + duration)
  - Equity curve + rolling metrics (30-day window)
  - Annualized return, volatility, alpha/beta proxy
  - Trade distribution analysis

Usage:
    pa = NativePerformanceAnalytics()
    pa.add_trade(pnl=100, duration_sec=3600, strategy="trend")
    pa.add_trade(pnl=-50, duration_sec=1800, strategy="mean_reversion")
    report = pa.generate_report()
    print(report["sharpe_ratio"])
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ══════════════════════════════════════════════════════════════════════════════
# Data Model
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class TradeRecord:
    pnl: float
    duration_sec: float
    strategy: str
    symbol: str = ""
    timestamp: float = 0.0
    side: str = ""
    entry_price: float = 0.0
    exit_price: float = 0.0


@dataclass
class EquityPoint:
    timestamp: float
    equity: float
    drawdown: float


# ══════════════════════════════════════════════════════════════════════════════
# Core Metrics
# ══════════════════════════════════════════════════════════════════════════════

class MetricsCalculator:
    """Calculate standard trading performance metrics."""

    @staticmethod
    def sharpe(returns: List[float], risk_free_rate: float = 0.0) -> float:
        if len(returns) < 2:
            return 0.0
        avg = sum(returns) / len(returns)
        variance = sum((r - avg) ** 2 for r in returns) / (len(returns) - 1)
        std = math.sqrt(variance) if variance > 0 else 0.0
        if std == 0:
            return 0.0
        return (avg - risk_free_rate) / std * math.sqrt(252)  # Annualized

    @staticmethod
    def sortino(returns: List[float], risk_free_rate: float = 0.0) -> float:
        if len(returns) < 2:
            return 0.0
        avg = sum(returns) / len(returns)
        downside = [r for r in returns if r < risk_free_rate]
        if not downside:
            return float("inf")
        downside_std = math.sqrt(sum((r - risk_free_rate) ** 2 for r in downside) / len(downside))
        if downside_std == 0:
            return float("inf")
        return (avg - risk_free_rate) / downside_std * math.sqrt(252)

    @staticmethod
    def calmar(returns: List[float], max_drawdown: float) -> float:
        if max_drawdown == 0 or len(returns) < 2:
            return 0.0
        avg_return = sum(returns) / len(returns)
        return avg_return * 252 / abs(max_drawdown)

    @staticmethod
    def omega(returns: List[float], threshold: float = 0.0) -> float:
        gains = sum(r - threshold for r in returns if r > threshold)
        losses = sum(threshold - r for r in returns if r < threshold)
        if losses == 0:
            return float("inf")
        return gains / losses

    @staticmethod
    def win_rate(returns: List[float]) -> float:
        if not returns:
            return 0.0
        wins = sum(1 for r in returns if r > 0)
        return wins / len(returns)

    @staticmethod
    def expectancy(returns: List[float]) -> float:
        if not returns:
            return 0.0
        avg_win = sum(r for r in returns if r > 0) / max(1, sum(1 for r in returns if r > 0))
        avg_loss = abs(sum(r for r in returns if r < 0) / max(1, sum(1 for r in returns if r < 0)))
        win_rate = MetricsCalculator.win_rate(returns)
        return (win_rate * avg_win) - ((1 - win_rate) * avg_loss)

    @staticmethod
    def profit_factor(returns: List[float]) -> float:
        gross_profit = sum(r for r in returns if r > 0)
        gross_loss = abs(sum(r for r in returns if r < 0))
        if gross_loss == 0:
            return float("inf")
        return gross_profit / gross_loss

    @staticmethod
    def avg_win_loss_ratio(returns: List[float]) -> float:
        wins = [r for r in returns if r > 0]
        losses = [abs(r) for r in returns if r < 0]
        if not losses:
            return float("inf")
        return (sum(wins) / len(wins)) / (sum(losses) / len(losses)) if wins else 0.0

    @staticmethod
    def max_drawdown(equity_curve: List[float]) -> Tuple[float, int]:
        peak = equity_curve[0]
        max_dd = 0.0
        max_dd_duration = 0
        dd_start = 0
        for i, eq in enumerate(equity_curve):
            if eq > peak:
                peak = eq
                dd_start = i
            dd = (peak - eq) / peak
            if dd > max_dd:
                max_dd = dd
                max_dd_duration = i - dd_start
        return max_dd, max_dd_duration

    @staticmethod
    def underwater_curve(equity_curve: List[float]) -> List[float]:
        peak = equity_curve[0]
        underwater = []
        for eq in equity_curve:
            if eq > peak:
                peak = eq
            underwater.append((peak - eq) / peak)
        return underwater

    @staticmethod
    def annualized_return(returns: List[float]) -> float:
        if not returns:
            return 0.0
        return sum(returns) / len(returns) * 252

    @staticmethod
    def volatility(returns: List[float]) -> float:
        if len(returns) < 2:
            return 0.0
        avg = sum(returns) / len(returns)
        variance = sum((r - avg) ** 2 for r in returns) / (len(returns) - 1)
        return math.sqrt(variance) * math.sqrt(252)

    @staticmethod
    def rolling_window(returns: List[float], window: int = 30) -> List[Dict[str, float]]:
        results = []
        for i in range(window, len(returns) + 1):
            chunk = returns[i - window:i]
            results.append({
                "start": i - window,
                "end": i - 1,
                "sharpe": MetricsCalculator.sharpe(chunk),
                "win_rate": MetricsCalculator.win_rate(chunk),
                "expectancy": MetricsCalculator.expectancy(chunk),
                "volatility": MetricsCalculator.volatility(chunk),
            })
        return results


# ══════════════════════════════════════════════════════════════════════════════
# Performance Analytics Engine
# ══════════════════════════════════════════════════════════════════════════════

class NativePerformanceAnalytics:
    """Track trades and generate comprehensive performance reports."""

    def __init__(self, initial_equity: float = 10000.0) -> None:
        self.initial_equity = initial_equity
        self.current_equity = initial_equity
        self.trades: List[TradeRecord] = []
        self.equity_curve: List[EquityPoint] = [EquityPoint(time.time(), initial_equity, 0.0)]
        self._strategies: Dict[str, List[TradeRecord]] = {}

    def add_trade(self, pnl: float, duration_sec: float = 0.0, strategy: str = "default",
                  symbol: str = "", side: str = "", entry_price: float = 0.0,
                  exit_price: float = 0.0) -> None:
        trade = TradeRecord(
            pnl=pnl, duration_sec=duration_sec, strategy=strategy,
            symbol=symbol, side=side, entry_price=entry_price,
            exit_price=exit_price, timestamp=time.time(),
        )
        self.trades.append(trade)
        self.current_equity += pnl
        dd_info = self._calculate_drawdown()
        self.equity_curve.append(EquityPoint(time.time(), self.current_equity, dd_info[0]))
        self._strategies.setdefault(strategy, []).append(trade)

    def _calculate_drawdown(self) -> Tuple[float, int]:
        eq = [e.equity for e in self.equity_curve]
        return MetricsCalculator.max_drawdown(eq)

    def generate_report(self) -> Dict[str, Any]:
        returns = [t.pnl / self.initial_equity for t in self.trades] if self.trades else []
        eq = [e.equity for e in self.equity_curve]
        max_dd, dd_duration = MetricsCalculator.max_drawdown(eq)
        underwater = MetricsCalculator.underwater_curve(eq)

        report = {
            "summary": {
                "total_trades": len(self.trades),
                "gross_profit": sum(t.pnl for t in self.trades if t.pnl > 0),
                "gross_loss": sum(t.pnl for t in self.trades if t.pnl < 0),
                "net_pnl": sum(t.pnl for t in self.trades),
                "initial_equity": self.initial_equity,
                "final_equity": self.current_equity,
                "total_return_pct": (self.current_equity - self.initial_equity) / self.initial_equity * 100,
            },
            "metrics": {
                "sharpe_ratio": round(MetricsCalculator.sharpe(returns), 4),
                "sortino_ratio": round(MetricsCalculator.sortino(returns), 4),
                "calmar_ratio": round(MetricsCalculator.calmar(returns, max_dd), 4),
                "omega_ratio": round(MetricsCalculator.omega(returns), 4),
                "win_rate": round(MetricsCalculator.win_rate(returns), 4),
                "expectancy": round(MetricsCalculator.expectancy(returns), 4),
                "profit_factor": round(MetricsCalculator.profit_factor(returns), 4),
                "avg_win_loss_ratio": round(MetricsCalculator.avg_win_loss_ratio(returns), 4),
                "max_drawdown_pct": round(max_dd * 100, 4),
                "max_drawdown_duration": dd_duration,
                "annualized_return": round(MetricsCalculator.annualized_return(returns), 4),
                "volatility": round(MetricsCalculator.volatility(returns), 4),
            },
            "distribution": {
                "winning_trades": sum(1 for t in self.trades if t.pnl > 0),
                "losing_trades": sum(1 for t in self.trades if t.pnl < 0),
                "breakeven_trades": sum(1 for t in self.trades if t.pnl == 0),
                "avg_trade_pnl": round(sum(t.pnl for t in self.trades) / len(self.trades), 2) if self.trades else 0,
                "avg_win": round(sum(t.pnl for t in self.trades if t.pnl > 0) / max(1, sum(1 for t in self.trades if t.pnl > 0)), 2),
                "avg_loss": round(sum(t.pnl for t in self.trades if t.pnl < 0) / max(1, sum(1 for t in self.trades if t.pnl < 0)), 2),
                "largest_win": max((t.pnl for t in self.trades), default=0),
                "largest_loss": min((t.pnl for t in self.trades), default=0),
            },
            "strategy_breakdown": {
                name: {
                    "trades": len(trades),
                    "net_pnl": sum(t.pnl for t in trades),
                    "win_rate": round(MetricsCalculator.win_rate([t.pnl / self.initial_equity for t in trades]), 4),
                }
                for name, trades in self._strategies.items()
            },
            "underwater_curve": [round(u * 100, 2) for u in underwater[-50:]],
            "rolling_30d": MetricsCalculator.rolling_window(returns, 30)[-10:],
        }
        return report

    def equity_chart_data(self) -> List[Tuple[float, float]]:
        """Return [(timestamp, equity), ...] for charting."""
        return [(e.timestamp, e.equity) for e in self.equity_curve]


# ══════════════════════════════════════════════════════════════════════════════
# Self-test
# ══════════════════════════════════════════════════════════════════════════════

def _self_test() -> int:
    print("=" * 60)
    print("Native Performance Analytics — Self Test")
    print("=" * 60)
    passed = 0
    total = 7

    # Test 1: Sharpe ratio
    print("[Test 1] Sharpe ratio")
    returns = [0.001, -0.002, 0.003, 0.001, -0.001, 0.002, 0.001, -0.001, 0.003, 0.001]
    sharpe = MetricsCalculator.sharpe(returns)
    ok = sharpe > 0
    print(f"  Sharpe={sharpe:.4f}: {ok} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    # Test 2: Max drawdown
    print("[Test 2] Max drawdown")
    equity = [100, 105, 103, 108, 106, 104, 110, 108, 100, 95]
    dd, dur = MetricsCalculator.max_drawdown(equity)
    ok2 = dd > 0 and dur >= 0
    print(f"  DD={dd:.4f}, dur={dur}: {ok2} — {'PASS' if ok2 else 'FAIL'}")
    passed += ok2

    # Test 3: Win rate
    print("[Test 3] Win rate")
    wr = MetricsCalculator.win_rate(returns)
    ok3 = 0 <= wr <= 1
    print(f"  Win rate={wr:.4f}: {ok3} — {'PASS' if ok3 else 'FAIL'}")
    passed += ok3

    # Test 4: Expectancy
    print("[Test 4] Expectancy")
    exp = MetricsCalculator.expectancy(returns)
    ok4 = isinstance(exp, float)
    print(f"  Expectancy={exp:.6f}: {ok4} — {'PASS' if ok4 else 'FAIL'}")
    passed += ok4

    # Test 5: Full report
    print("[Test 5] Full report generation")
    pa = NativePerformanceAnalytics(initial_equity=10000.0)
    pa.add_trade(100, 3600, "trend")
    pa.add_trade(-50, 1800, "trend")
    pa.add_trade(80, 2400, "mean_reversion")
    pa.add_trade(-30, 1200, "mean_reversion")
    report = pa.generate_report()
    ok5 = "metrics" in report and "sharpe_ratio" in report["metrics"]
    print(f"  Report has metrics: {ok5} — {'PASS' if ok5 else 'FAIL'}")
    passed += ok5

    # Test 6: Strategy breakdown
    print("[Test 6] Strategy breakdown")
    breakdown = report.get("strategy_breakdown", {})
    ok6 = "trend" in breakdown and "mean_reversion" in breakdown
    print(f"  Strategy breakdown valid: {ok6} — {'PASS' if ok6 else 'FAIL'}")
    passed += ok6

    # Test 7: Underwater curve
    print("[Test 7] Underwater curve")
    uw = MetricsCalculator.underwater_curve([e.equity for e in pa.equity_curve])
    ok7 = len(uw) > 0 and all(0 <= u <= 1 for u in uw)
    print(f"  Underwater curve valid: {ok7} — {'PASS' if ok7 else 'FAIL'}")
    passed += ok7

    print(f"\nPASS: {passed}/{total}")
    print("=" * 60)
    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())

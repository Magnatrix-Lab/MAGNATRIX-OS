#!/usr/bin/env python3
"""
MAGNATRIX-OS — Layer 8: WorldQuant Alpha101 Engine
Native Python, zero external dependencies.
Based on yli188/WorldQuant_alpha101_code (748 stars) — 101 Formulaic Alphas.
"""
from __future__ import annotations
import math, random, time, json, threading
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Callable
from enum import Enum


class AlphaCategory(Enum):
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    VOLATILITY = "volatility"
    VOLUME = "volume"
    SENTIMENT = "sentiment"
    MICROSTRUCTURE = "microstructure"
    COMPOSITE = "composite"


@dataclass
class Alpha:
    name: str
    formula_id: str
    category: AlphaCategory
    description: str
    formula_lambda: str
    parameters: Dict = field(default_factory=dict)
    lookback_window: int = 20
    ic: float = 0.0
    ic_std: float = 0.0
    sharpe: float = 0.0
    max_drawdown: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "formula_id": self.formula_id,
            "category": self.category.value,
            "description": self.description,
            "parameters": self.parameters,
            "lookback_window": self.lookback_window,
            "ic": self.ic,
            "sharpe": self.sharpe,
            "max_drawdown": self.max_drawdown,
        }


class TSFunctionEngine:
    """Time-series functions: ts_rank, ts_delta, ts_corr, etc."""

    @staticmethod
    def ts_mean(series: List[float], window: int) -> List[float]:
        result = []
        for i in range(len(series)):
            start = max(0, i - window + 1)
            subset = series[start:i+1]
            result.append(sum(subset) / len(subset))
        return result

    @staticmethod
    def ts_std(series: List[float], window: int) -> List[float]:
        result = []
        for i in range(len(series)):
            start = max(0, i - window + 1)
            subset = series[start:i+1]
            mean = sum(subset) / len(subset)
            variance = sum((x - mean) ** 2 for x in subset) / len(subset)
            result.append(math.sqrt(variance))
        return result

    @staticmethod
    def ts_rank(series: List[float], window: int) -> List[float]:
        result = []
        for i in range(len(series)):
            start = max(0, i - window + 1)
            subset = series[start:i+1]
            if not subset:
                result.append(0.0)
                continue
            current = series[i]
            rank = sum(1 for x in subset if x < current) + 0.5 * sum(1 for x in subset if x == current)
            result.append(rank / len(subset))
        return result

    @staticmethod
    def ts_delta(series: List[float], period: int) -> List[float]:
        result = []
        for i in range(len(series)):
            if i < period:
                result.append(0.0)
            else:
                result.append(series[i] - series[i - period])
        return result

    @staticmethod
    def ts_corr(a: List[float], b: List[float], window: int) -> List[float]:
        result = []
        for i in range(len(a)):
            start = max(0, i - window + 1)
            sa, sb = a[start:i+1], b[start:i+1]
            if len(sa) < 2:
                result.append(0.0)
                continue
            ma, mb = sum(sa)/len(sa), sum(sb)/len(sb)
            num = sum((x - ma) * (y - mb) for x, y in zip(sa, sb))
            den_a = math.sqrt(sum((x - ma) ** 2 for x in sa))
            den_b = math.sqrt(sum((y - mb) ** 2 for y in sb))
            result.append(num / (den_a * den_b) if den_a * den_b > 0 else 0.0)
        return result

    @staticmethod
    def ts_zscore(series: List[float], window: int) -> List[float]:
        means = TSFunctionEngine.ts_mean(series, window)
        stds = TSFunctionEngine.ts_std(series, window)
        return [(s - m) / (std + 1e-10) for s, m, std in zip(series, means, stds)]

    @staticmethod
    def ts_decay_linear(series: List[float], window: int) -> List[float]:
        result = []
        for i in range(len(series)):
            start = max(0, i - window + 1)
            subset = series[start:i+1]
            weights = list(range(1, len(subset) + 1))
            total = sum(w * v for w, v in zip(weights, subset))
            result.append(total / sum(weights))
        return result


class CrossSectionalEngine:
    """Cross-sectional functions: rank, sign, abs, log, scale."""

    @staticmethod
    def rank(values: List[float]) -> List[float]:
        sorted_vals = sorted(set(values))
        rank_map = {v: i for i, v in enumerate(sorted_vals)}
        return [(rank_map[v] + 1) / len(sorted_vals) for v in values]

    @staticmethod
    def scale(values: List[float], scale_to: float = 1.0) -> List[float]:
        total = sum(abs(v) for v in values)
        if total == 0:
            return values[:]
        return [v * scale_to / total for v in values]

    @staticmethod
    def sign(values: List[float]) -> List[float]:
        return [1.0 if v > 0 else -1.0 if v < 0 else 0.0 for v in values]

    @staticmethod
    def abs_log(values: List[float]) -> List[float]:
        return [math.log(abs(v) + 1) for v in values]


class AlphaRegistry:
    """Register 101 alphas, categorize, metadata lookup."""

    def __init__(self):
        self._alphas: Dict[str, Alpha] = {}
        self._category_map: Dict[AlphaCategory, List[str]] = {c: [] for c in AlphaCategory}
        self._lock = threading.Lock()

    def register(self, alpha: Alpha):
        with self._lock:
            self._alphas[alpha.formula_id] = alpha
            self._category_map[alpha.category].append(alpha.formula_id)

    def get(self, formula_id: str) -> Optional[Alpha]:
        with self._lock:
            return self._alphas.get(formula_id)

    def by_category(self, category: AlphaCategory) -> List[Alpha]:
        with self._lock:
            return [self._alphas[k] for k in self._category_map.get(category, [])]

    def list_all(self) -> List[Alpha]:
        with self._lock:
            return list(self._alphas.values())


class AlphaEvaluator:
    """Evaluate alpha with IC, IR, turnover, sharpe, max drawdown."""

    @staticmethod
    def calculate_ic(alpha_values: List[float], forward_returns: List[float]) -> float:
        if len(alpha_values) != len(forward_returns) or len(alpha_values) < 2:
            return 0.0
        mean_a = sum(alpha_values) / len(alpha_values)
        mean_f = sum(forward_returns) / len(forward_returns)
        num = sum((a - mean_a) * (f - mean_f) for a, f in zip(alpha_values, forward_returns))
        den_a = math.sqrt(sum((a - mean_a) ** 2 for a in alpha_values))
        den_f = math.sqrt(sum((f - mean_f) ** 2 for f in forward_returns))
        return num / (den_a * den_f) if den_a * den_f > 0 else 0.0

    @staticmethod
    def calculate_ir(alpha_values: List[float], forward_returns: List[float]) -> float:
        ics = []
        window = min(20, len(alpha_values) // 2)
        for i in range(window, len(alpha_values)):
            ic = AlphaEvaluator.calculate_ic(alpha_values[i-window:i], forward_returns[i-window:i])
            ics.append(ic)
        if not ics:
            return 0.0
        mean_ic = sum(ics) / len(ics)
        std_ic = math.sqrt(sum((x - mean_ic) ** 2 for x in ics) / len(ics)) + 1e-10
        return mean_ic / std_ic

    @staticmethod
    def calculate_sharpe(pnl_series: List[float]) -> float:
        if not pnl_series:
            return 0.0
        mean = sum(pnl_series) / len(pnl_series)
        std = math.sqrt(sum((x - mean) ** 2 for x in pnl_series) / len(pnl_series)) + 1e-10
        return mean / std * math.sqrt(252)  # Annualized

    @staticmethod
    def calculate_max_drawdown(pnl_series: List[float]) -> float:
        peak = 0.0
        max_dd = 0.0
        cumulative = 0.0
        for pnl in pnl_series:
            cumulative += pnl
            if cumulative > peak:
                peak = cumulative
            dd = peak - cumulative
            if dd > max_dd:
                max_dd = dd
        return max_dd


class AlphaCombiner:
    """Combine multiple alphas: equal weight, IC-weighted, risk-weighted."""

    @staticmethod
    def equal_weight(alpha_signals: Dict[str, List[float]]) -> List[float]:
        keys = list(alpha_signals.keys())
        n = len(alpha_signals[keys[0]])
        return [sum(alpha_signals[k][i] for k in keys) / len(keys) for i in range(n)]

    @staticmethod
    def ic_weighted(alpha_signals: Dict[str, List[float]], ics: Dict[str, float]) -> List[float]:
        keys = list(alpha_signals.keys())
        n = len(alpha_signals[keys[0]])
        weights = {k: max(0, ics.get(k, 0)) for k in keys}
        total_weight = sum(weights.values()) + 1e-10
        return [sum(alpha_signals[k][i] * weights[k] for k in keys) / total_weight for i in range(n)]


class AlphaBacktestStub:
    """Walk-forward backtest per alpha."""

    def run(self, alpha_values: List[float], prices: List[float], position_size: float = 0.1) -> Dict:
        pnl = []
        positions = []
        for i in range(1, len(alpha_values)):
            # Signal → position
            signal = alpha_values[i - 1]
            position = signal * position_size
            positions.append(position)
            # Return
            ret = (prices[i] - prices[i-1]) / prices[i-1] if prices[i-1] != 0 else 0
            pnl.append(position * ret)

        return {
            "pnl": pnl,
            "total_pnl": sum(pnl),
            "sharpe": AlphaEvaluator.calculate_sharpe(pnl),
            "max_drawdown": AlphaEvaluator.calculate_max_drawdown(pnl),
            "num_trades": len(pnl),
        }


class Alpha101Engine:
    """Main orchestrator — run all 101 alphas, evaluate, rank, combine."""

    def __init__(self):
        self.registry = AlphaRegistry()
        self.ts = TSFunctionEngine()
        self.cs = CrossSectionalEngine()
        self.evaluator = AlphaEvaluator()
        self.combiner = AlphaCombiner()
        self.backtest = AlphaBacktestStub()
        self._init_alphas()

    def _init_alphas(self):
        # Alpha001: (rank(ts_argmax(power(returns, 2), 5)) - 0.5)
        self.registry.register(Alpha(
            name="Alpha001", formula_id="alpha001",
            category=AlphaCategory.MOMENTUM,
            description="Rank of ts_argmax of squared returns",
            formula_lambda="rank(ts_argmax(power(returns,2),5))-0.5",
            parameters={"window": 5},
        ))
        # Alpha002: (-1 * correlation(rank(delta(log(volume), 2)), rank((close - open) / open), 6))
        self.registry.register(Alpha(
            name="Alpha002", formula_id="alpha002",
            category=AlphaCategory.VOLUME,
            description="Correlation of volume delta rank and return rank",
            formula_lambda="-corr(rank(delta(log(volume),2)),rank((close-open)/open),6)",
            parameters={"window": 6},
        ))
        # Alpha003: (-1 * correlation(rank(open), rank(volume), 10))
        self.registry.register(Alpha(
            name="Alpha003", formula_id="alpha003",
            category=AlphaCategory.VOLUME,
            description="Correlation of open rank and volume rank",
            formula_lambda="-corr(rank(open),rank(volume),10)",
            parameters={"window": 10},
        ))
        # Alpha004: (-1 * ts_rank(rank(low), 9))
        self.registry.register(Alpha(
            name="Alpha004", formula_id="alpha004",
            category=AlphaCategory.MEAN_REVERSION,
            description="Time-series rank of low rank",
            formula_lambda="-ts_rank(rank(low),9)",
            parameters={"window": 9},
        ))
        # Alpha005: (rank(open - (sum(vwap, 10) / 10)) * (-1 * abs(rank(close - vwap))))
        self.registry.register(Alpha(
            name="Alpha005", formula_id="alpha005",
            category=AlphaCategory.VOLATILITY,
            description="Open deviation from VWAP mean times close-vwap deviation",
            formula_lambda="rank(open-ts_mean(vwap,10))*(-abs(rank(close-vwap)))",
            parameters={"window": 10},
        ))
        # Alpha006: (-1 * correlation(open, volume, 10))
        self.registry.register(Alpha(
            name="Alpha006", formula_id="alpha006",
            category=AlphaCategory.VOLUME,
            description="Correlation of open and volume",
            formula_lambda="-corr(open,volume,10)",
            parameters={"window": 10},
        ))
        # Alpha007: (adv20 < volume) ? (-1 * ts_rank(abs(delta(close, 7)), 60)) * sign(delta(close, 7)) : -1
        self.registry.register(Alpha(
            name="Alpha007", formula_id="alpha007",
            category=AlphaCategory.MEAN_REVERSION,
            description="Mean reversion based on close delta",
            formula_lambda="if(adv20<volume,-ts_rank(abs(delta(close,7)),60)*sign(delta(close,7)),-1)",
            parameters={"window": 60},
        ))
        # Alpha008: (-1 * rank(sum(sign(delta(volume, 1)), 2) / sum(delta(volume, 1), 2)))
        self.registry.register(Alpha(
            name="Alpha008", formula_id="alpha008",
            category=AlphaCategory.VOLUME,
            description="Volume acceleration signal",
            formula_lambda="-rank(sum(sign(delta(volume,1)),2)/sum(delta(volume,1),2))",
            parameters={"window": 2},
        ))
        # Alpha009: (0 < ts_min(delta(close, 1), 5)) ? delta(close, 1) : (ts_max(delta(close, 1), 5) < 0) ? delta(close, 1) : (-1 * delta(close, 1))
        self.registry.register(Alpha(
            name="Alpha009", formula_id="alpha009",
            category=AlphaCategory.MOMENTUM,
            description="Close momentum with min/max filter",
            formula_lambda="if(ts_min(delta(close,1),5)>0,delta(close,1),if(ts_max(delta(close,1),5)<0,delta(close,1),-delta(close,1)))",
            parameters={"window": 5},
        ))
        # Alpha010: rank(ts_max(((delta(close, 1) * (1 - delta(close, 1))) ** 2), 5))
        self.registry.register(Alpha(
            name="Alpha010", formula_id="alpha010",
            category=AlphaCategory.VOLATILITY,
            description="Max of squared adjusted close delta",
            formula_lambda="rank(ts_max((delta(close,1)*(1-delta(close,1)))**2,5))",
            parameters={"window": 5},
        ))
        # ... (stub for remaining 91 alphas)
        for i in range(11, 102):
            self.registry.register(Alpha(
                name=f"Alpha{i:03d}", formula_id=f"alpha{i:03d}",
                category=random.choice(list(AlphaCategory)),
                description=f"WorldQuant Formulaic Alpha {i:03d} (stub)",
                formula_lambda=f"alpha_{i:03d}_formula",
                parameters={"window": random.choice([5, 10, 20, 60])},
            ))

    def run_alpha(self, formula_id: str, data: Dict) -> List[float]:
        alpha = self.registry.get(formula_id)
        if not alpha:
            return []

        # Execute formula based on formula_id
        close = data.get("close", [])
        volume = data.get("volume", [])
        open_p = data.get("open", [])
        low = data.get("low", [])
        high = data.get("high", [])
        vwap = data.get("vwap", [])
        returns = data.get("returns", [])

        if formula_id == "alpha001":
            # rank(ts_argmax(power(returns, 2), 5)) - 0.5
            sq_returns = [r * r for r in returns]
            argmax = []
            for i in range(len(sq_returns)):
                start = max(0, i - 5 + 1)
                subset = sq_returns[start:i+1]
                argmax.append(subset.index(max(subset)) + start if subset else i)
            return self.cs.scale(self.cs.rank(argmax), 1.0)

        elif formula_id == "alpha002":
            # -corr(rank(delta(log(volume),2)), rank((close-open)/open), 6)
            log_vol = [math.log(v + 1) for v in volume]
            delta_log = self.ts.ts_delta(log_vol, 2)
            rank_delta = self.cs.rank(delta_log)
            rank_ret = self.cs.rank([(c - o) / (o + 1e-10) for c, o in zip(close, open_p)])
            corr = self.ts.ts_corr(rank_delta, rank_ret, 6)
            return [-c for c in corr]

        elif formula_id == "alpha003":
            # -corr(rank(open), rank(volume), 10)
            rank_open = self.cs.rank(open_p)
            rank_vol = self.cs.rank(volume)
            corr = self.ts.ts_corr(rank_open, rank_vol, 10)
            return [-c for c in corr]

        elif formula_id == "alpha004":
            # -ts_rank(rank(low), 9)
            rank_low = self.cs.rank(low)
            return self.ts.ts_rank(rank_low, 9)

        elif formula_id == "alpha005":
            # rank(open-ts_mean(vwap,10))*(-abs(rank(close-vwap)))
            mean_vwap = self.ts.ts_mean(vwap, 10)
            dev = [o - m for o, m in zip(open_p, mean_vwap)]
            rank_dev = self.cs.rank(dev)
            close_dev = [c - v for c, v in zip(close, vwap)]
            rank_close = self.cs.rank(close_dev)
            return [r * (-abs(rc)) for r, rc in zip(rank_dev, rank_close)]

        elif formula_id == "alpha006":
            # -corr(open, volume, 10)
            corr = self.ts.ts_corr(open_p, volume, 10)
            return [-c for c in corr]

        elif formula_id == "alpha009":
            # momentum signal
            delta_close = self.ts.ts_delta(close, 1)
            min_delta = []
            max_delta = []
            for i in range(len(delta_close)):
                start = max(0, i - 5 + 1)
                subset = delta_close[start:i+1]
                min_delta.append(min(subset) if subset else 0)
                max_delta.append(max(subset) if subset else 0)
            result = []
            for i, d in enumerate(delta_close):
                if min_delta[i] > 0:
                    result.append(d)
                elif max_delta[i] < 0:
                    result.append(d)
                else:
                    result.append(-d)
            return result

        elif formula_id == "alpha010":
            # rank(ts_max((delta(close,1)*(1-delta(close,1)))**2, 5))
            delta = self.ts.ts_delta(close, 1)
            adj = [d * (1 - d) for d in delta]
            sq = [a * a for a in adj]
            max_sq = []
            for i in range(len(sq)):
                start = max(0, i - 5 + 1)
                max_sq.append(max(sq[start:i+1]) if sq[start:i+1] else 0)
            return self.cs.rank(max_sq)

        else:
            # Generic stub: random walk signal
            return [random.gauss(0, 0.01) for _ in range(len(close))]

    def evaluate_all(self, data: Dict, forward_returns: List[float]) -> Dict:
        results = {}
        for alpha in self.registry.list_all():
            signals = self.run_alpha(alpha.formula_id, data)
            if signals and len(signals) == len(forward_returns):
                ic = self.evaluator.calculate_ic(signals, forward_returns)
                ir = self.evaluator.calculate_ir(signals, forward_returns)
                alpha.ic = ic
                results[alpha.formula_id] = {
                    "name": alpha.name,
                    "ic": ic,
                    "ir": ir,
                }
        return results

    def combine_top_alphas(self, data: Dict, forward_returns: List[float], top_n: int = 10) -> List[float]:
        evals = self.evaluate_all(data, forward_returns)
        sorted_alphas = sorted(evals.items(), key=lambda x: abs(x[1]["ic"]), reverse=True)
        top = sorted_alphas[:top_n]

        signals = {}
        ics = {}
        for formula_id, info in top:
            signals[formula_id] = self.run_alpha(formula_id, data)
            ics[formula_id] = info["ic"]

        if not signals:
            return []
        return self.combiner.ic_weighted(signals, ics)

    def get_stats(self) -> Dict:
        return {
            "total_alphas": len(self.registry.list_all()),
            "by_category": {c.value: len(self.registry.by_category(c)) for c in AlphaCategory},
        }


def run_demo():
    print("=" * 60)
    print("MAGNATRIX-OS WorldQuant Alpha101 Engine Demo")
    print("=" * 60)

    engine = Alpha101Engine()
    stats = engine.get_stats()
    print(f"\nRegistered alphas: {stats['total_alphas']}")
    for cat, count in stats['by_category'].items():
        print(f"  {cat}: {count}")

    # Generate synthetic data
    n = 200
    prices = [100.0]
    for _ in range(n - 1):
        prices.append(prices[-1] * (1 + random.gauss(0, 0.01)))

    close = prices[:]
    open_p = [p * (1 + random.gauss(0, 0.005)) for p in prices]
    high = [max(c, o) * (1 + abs(random.gauss(0, 0.005))) for c, o in zip(close, open_p)]
    low = [min(c, o) * (1 - abs(random.gauss(0, 0.005))) for c, o in zip(close, open_p)]
    volume = [random.randint(1000000, 10000000) for _ in range(n)]
    vwap = [(h + l + c) / 3 for h, l, c in zip(high, low, close)]
    returns = [(close[i] - close[i-1]) / close[i-1] if i > 0 else 0 for i in range(n)]

    data = {
        "close": close, "open": open_p, "high": high, "low": low,
        "volume": volume, "vwap": vwap, "returns": returns,
    }
    forward_returns = returns[1:] + [0]

    # Run top alphas
    print("\n--- Running Top 10 Alphas ---")
    combined = engine.combine_top_alphas(data, forward_returns, top_n=10)
    print(f"Combined signal length: {len(combined)}")
    if combined:
        print(f"Combined signal mean: {sum(combined)/len(combined):.6f}")
        print(f"Combined signal std: {math.sqrt(sum((x - sum(combined)/len(combined))**2 for x in combined)/len(combined)):.6f}")

    # Evaluate all
    print("\n--- IC Evaluation ---")
    evals = engine.evaluate_all(data, forward_returns)
    top_5 = sorted(evals.items(), key=lambda x: abs(x[1]["ic"]), reverse=True)[:5]
    for fid, info in top_5:
        print(f"  {info['name']}: IC={info['ic']:.4f}, IR={info['ir']:.4f}")

    # Backtest
    print("\n--- Backtest ---")
    if combined:
        bt = engine.backtest.run(combined, close, position_size=0.1)
        print(f"  Total PnL: {bt['total_pnl']:.4f}")
        print(f"  Sharpe: {bt['sharpe']:.4f}")
        print(f"  Max Drawdown: {bt['max_drawdown']:.4f}")
        print(f"  Num Trades: {bt['num_trades']}")

    print("\n" + "=" * 60)
    print("Demo complete.")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()

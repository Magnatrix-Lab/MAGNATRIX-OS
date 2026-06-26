#!/usr/bin/env python3
"""
HFT Trading Engine for MAGNATRIX-OS
====================================
High-frequency trading engine with paper trading, strategy framework,
risk management, and performance reporting. Pure Python stdlib only.
Target: 65-90% win rate framework.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations
import json, math, random, threading, time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional, Callable


class Side(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class Signal(Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


@dataclass
class Tick:
    """Market tick data."""
    timestamp: float
    price: float
    volume: float
    bid: float
    ask: float
    symbol: str = "BTCUSD"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Tick":
        return cls(**d)


@dataclass
class Candle:
    """OHLCV candle."""
    open: float
    high: float
    low: float
    close: float
    volume: float
    timestamp: float
    timeframe: str = "1m"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_ticks(cls, ticks: List[Tick], timeframe: str = "1m") -> "Candle":
        if not ticks:
            return cls(0.0, 0.0, 0.0, 0.0, 0.0, time.time(), timeframe)
        prices = [t.price for t in ticks]
        volumes = [t.volume for t in ticks]
        return cls(
            open=prices[0],
            high=max(prices),
            low=min(prices),
            close=prices[-1],
            volume=sum(volumes),
            timestamp=ticks[0].timestamp,
            timeframe=timeframe,
        )

    def merge(self, other: "Candle") -> "Candle":
        return Candle(
            open=self.open,
            high=max(self.high, other.high),
            low=min(self.low, other.low),
            close=other.close,
            volume=self.volume + other.volume,
            timestamp=self.timestamp,
            timeframe=self.timeframe,
        )


@dataclass
class Order:
    """Trading order."""
    symbol: str
    side: Side
    order_type: OrderType
    qty: float
    price: Optional[float] = None
    timestamp: float = field(default_factory=time.time)
    status: OrderStatus = OrderStatus.PENDING
    order_id: str = field(default_factory=lambda: f"ord_{int(time.time()*1000000)}")
    fill_price: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["side"] = self.side.value
        d["order_type"] = self.order_type.value
        d["status"] = self.status.value
        return d


@dataclass
class Position:
    """Open position."""
    symbol: str
    side: Side
    entry_price: float
    qty: float
    open_time: float = field(default_factory=time.time)
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    exit_price: Optional[float] = None
    close_time: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

    def update(self, current_price: float) -> None:
        if self.side == Side.BUY:
            self.unrealized_pnl = (current_price - self.entry_price) * self.qty
        else:
            self.unrealized_pnl = (self.entry_price - current_price) * self.qty

    def close(self, exit_price: float) -> float:
        self.exit_price = exit_price
        self.close_time = time.time()
        if self.side == Side.BUY:
            self.realized_pnl = (exit_price - self.entry_price) * self.qty
        else:
            self.realized_pnl = (self.entry_price - exit_price) * self.qty
        self.unrealized_pnl = 0.0
        return self.realized_pnl

    def pnl(self) -> float:
        return self.realized_pnl if self.realized_pnl != 0.0 else self.unrealized_pnl

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["side"] = self.side.value
        return d


class CandleBuilder:
    """Aggregates ticks into candles."""

    TIMEFRAME_SECONDS = {
        "1s": 1, "5s": 5, "15s": 15,
        "1m": 60, "5m": 300, "15m": 900, "1h": 3600,
    }

    def __init__(self, timeframe: str = "1m") -> None:
        self.timeframe = timeframe
        self.interval = self.TIMEFRAME_SECONDS.get(timeframe, 60)
        self.current_ticks: List[Tick] = []
        self.candles: List[Candle] = []
        self._current_bucket: Optional[int] = None

    def add_tick(self, tick: Tick) -> Optional[Candle]:
        bucket = int(tick.timestamp) // self.interval
        if self._current_bucket is not None and bucket != self._current_bucket:
            if self.current_ticks:
                candle = Candle.from_ticks(self.current_ticks, self.timeframe)
                self.candles.append(candle)
                self.current_ticks = []
                self._current_bucket = bucket
                return candle
        if self._current_bucket is None:
            self._current_bucket = bucket
        self.current_ticks.append(tick)
        return None

    def get_candles(self, n: Optional[int] = None) -> List[Candle]:
        if n is None:
            return self.candles.copy()
        return self.candles[-n:]

    def reset(self) -> None:
        self.current_ticks = []
        self.candles = []
        self._current_bucket = None


class Portfolio:
    """Manages positions, cash, and PnL."""

    def __init__(self, initial_cash: float = 10000.0) -> None:
        self.cash = initial_cash
        self.initial_cash = initial_cash
        self.positions: Dict[str, Position] = {}
        self.closed_positions: List[Position] = []
        self.max_value = initial_cash
        self.peak = initial_cash

    def open_position(self, position: Position) -> bool:
        required = position.entry_price * position.qty
        if self.cash < required:
            return False
        self.cash -= required
        self.positions[position.symbol] = position
        return True

    def close_position(self, symbol: str, exit_price: float) -> Optional[float]:
        pos = self.positions.pop(symbol, None)
        if pos is None:
            return None
        pnl = pos.close(exit_price)
        self.cash += exit_price * pos.qty
        self.closed_positions.append(pos)
        return pnl

    def update_prices(self, prices: Dict[str, float]) -> None:
        for sym, pos in self.positions.items():
            if sym in prices:
                pos.update(prices[sym])

    def get_equity(self) -> float:
        return self.cash + sum(p.unrealized_pnl for p in self.positions.values())

    def get_total_pnl(self) -> float:
        return self.get_equity() - self.initial_cash

    def get_drawdown(self) -> float:
        equity = self.get_equity()
        self.peak = max(self.peak, equity)
        if self.peak > 0:
            return (self.peak - equity) / self.peak
        return 0.0

    def get_max_drawdown(self) -> float:
        if not self.closed_positions:
            return 0.0
        max_dd = 0.0
        peak = self.initial_cash
        for pos in self.closed_positions:
            if pos.side == Side.BUY:
                val = self.cash + pos.realized_pnl
            else:
                val = self.cash + pos.realized_pnl
            peak = max(peak, val)
            dd = (peak - val) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
        return max_dd

    def get_summary(self) -> Dict[str, Any]:
        return {
            "cash": round(self.cash, 2),
            "equity": round(self.get_equity(), 2),
            "total_pnl": round(self.get_total_pnl(), 2),
            "drawdown_pct": round(self.get_drawdown() * 100, 2),
            "open_positions": len(self.positions),
            "closed_positions": len(self.closed_positions),
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cash": self.cash,
            "initial_cash": self.initial_cash,
            "positions": {k: v.to_dict() for k, v in self.positions.items()},
            "closed_positions": [p.to_dict() for p in self.closed_positions],
        }


class Strategy:
    """Abstract strategy base class."""

    def __init__(self, name: str = "BaseStrategy") -> None:
        self.name = name
        self.candles: List[Candle] = []
        self.last_signal: Signal = Signal.HOLD
        self.confidence: float = 0.0

    def on_tick(self, tick: Tick) -> None:
        pass

    def on_candle(self, candle: Candle) -> None:
        self.candles.append(candle)
        if len(self.candles) > 1000:
            self.candles = self.candles[-500:]

    def signal(self) -> tuple[Signal, float]:
        return self.last_signal, self.confidence

    def reset(self) -> None:
        self.candles = []
        self.last_signal = Signal.HOLD
        self.confidence = 0.0


class MAStrategy(Strategy):
    """Moving Average Crossover Strategy."""

    def __init__(self, fast: int = 10, slow: int = 30) -> None:
        super().__init__(f"MA_{fast}_{slow}")
        self.fast = fast
        self.slow = slow

    def _ma(self, prices: List[float], period: int) -> Optional[float]:
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period

    def on_candle(self, candle: Candle) -> None:
        super().on_candle(candle)
        closes = [c.close for c in self.candles]
        if len(closes) < self.slow + 1:
            return
        fast_ma = self._ma(closes, self.fast)
        slow_ma = self._ma(closes, self.slow)
        if fast_ma is None or slow_ma is None:
            return
        prev_fast = self._ma(closes[:-1], self.fast)
        prev_slow = self._ma(closes[:-1], self.slow)
        if prev_fast is None or prev_slow is None:
            return
        if prev_fast <= prev_slow and fast_ma > slow_ma:
            self.last_signal = Signal.BUY
            self.confidence = min(0.5 + abs(fast_ma - slow_ma) / slow_ma, 0.95)
        elif prev_fast >= prev_slow and fast_ma < slow_ma:
            self.last_signal = Signal.SELL
            self.confidence = min(0.5 + abs(fast_ma - slow_ma) / slow_ma, 0.95)
        else:
            self.last_signal = Signal.HOLD
            self.confidence = 0.0


class RSIStrategy(Strategy):
    """RSI Mean-Reversion Strategy."""

    def __init__(self, period: int = 14, overbought: float = 70.0, oversold: float = 30.0) -> None:
        super().__init__(f"RSI_{period}")
        self.period = period
        self.overbought = overbought
        self.oversold = oversold

    def _rsi(self, prices: List[float]) -> Optional[float]:
        if len(prices) < self.period + 1:
            return None
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas[-self.period:]]
        losses = [-d if d < 0 else 0 for d in deltas[-self.period:]]
        avg_gain = sum(gains) / self.period
        avg_loss = sum(losses) / self.period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def on_candle(self, candle: Candle) -> None:
        super().on_candle(candle)
        closes = [c.close for c in self.candles]
        rsi = self._rsi(closes)
        if rsi is None:
            return
        if rsi < self.oversold:
            self.last_signal = Signal.BUY
            self.confidence = min((self.oversold - rsi) / self.oversold + 0.3, 0.9)
        elif rsi > self.overbought:
            self.last_signal = Signal.SELL
            self.confidence = min((rsi - self.overbought) / (100 - self.overbought) + 0.3, 0.9)
        else:
            self.last_signal = Signal.HOLD
            self.confidence = 0.0


class BreakoutStrategy(Strategy):
    """Breakout Strategy."""

    def __init__(self, lookback: int = 20) -> None:
        super().__init__(f"Breakout_{lookback}")
        self.lookback = lookback

    def on_candle(self, candle: Candle) -> None:
        super().on_candle(candle)
        if len(self.candles) < self.lookback + 1:
            return
        window = self.candles[-self.lookback:-1]
        high = max(c.high for c in window)
        low = min(c.low for c in window)
        if candle.close > high:
            self.last_signal = Signal.BUY
            self.confidence = min(0.5 + (candle.close - high) / high, 0.9)
        elif candle.close < low:
            self.last_signal = Signal.SELL
            self.confidence = min(0.5 + (low - candle.close) / low, 0.9)
        else:
            self.last_signal = Signal.HOLD
            self.confidence = 0.0


class RiskManager:
    """Position sizing and risk controls."""

    def __init__(
        self,
        max_position_pct: float = 0.2,
        max_drawdown_pct: float = 0.15,
        max_positions: int = 5,
        stop_loss_pct: float = 0.02,
        take_profit_pct: float = 0.04,
        min_confidence: float = 0.3,
    ) -> None:
        self.max_position_pct = max_position_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.max_positions = max_positions
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.min_confidence = min_confidence

    def can_trade(self, portfolio: Portfolio, signal: Signal, confidence: float) -> bool:
        if signal == Signal.HOLD or confidence < self.min_confidence:
            return False
        if len(portfolio.positions) >= self.max_positions:
            return False
        if portfolio.get_drawdown() > self.max_drawdown_pct:
            return False
        return True

    def calculate_size(self, portfolio: Portfolio, price: float, confidence: float) -> float:
        equity = portfolio.get_equity()
        max_alloc = equity * self.max_position_pct
        size = max_alloc * confidence / price
        return max(size, 0.0)

    def check_stop_loss(self, position: Position, current_price: float) -> bool:
        if position.stop_loss is None:
            if position.side == Side.BUY:
                position.stop_loss = position.entry_price * (1 - self.stop_loss_pct)
            else:
                position.stop_loss = position.entry_price * (1 + self.stop_loss_pct)
        if position.side == Side.BUY and current_price <= position.stop_loss:
            return True
        if position.side == Side.SELL and current_price >= position.stop_loss:
            return True
        return False

    def check_take_profit(self, position: Position, current_price: float) -> bool:
        if position.take_profit is None:
            if position.side == Side.BUY:
                position.take_profit = position.entry_price * (1 + self.take_profit_pct)
            else:
                position.take_profit = position.entry_price * (1 - self.take_profit_pct)
        if position.side == Side.BUY and current_price >= position.take_profit:
            return True
        if position.side == Side.SELL and current_price <= position.take_profit:
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_position_pct": self.max_position_pct,
            "max_drawdown_pct": self.max_drawdown_pct,
            "max_positions": self.max_positions,
            "stop_loss_pct": self.stop_loss_pct,
            "take_profit_pct": self.take_profit_pct,
            "min_confidence": self.min_confidence,
        }


class ExecutionEngine:
    """Paper trading execution engine."""

    def __init__(self, slippage_pct: float = 0.001, latency_ms: float = 50.0) -> None:
        self.slippage_pct = slippage_pct
        self.latency_ms = latency_ms
        self.fills: List[Order] = []
        self._order_counter = 0

    def submit(self, order: Order, current_price: float) -> Order:
        time.sleep(self.latency_ms / 1000.0)
        if order.order_type == OrderType.MARKET:
            fill_price = current_price * (1 + random.uniform(-self.slippage_pct, self.slippage_pct))
        elif order.order_type == OrderType.LIMIT and order.price is not None:
            if order.side == Side.BUY and current_price <= order.price:
                fill_price = order.price
            elif order.side == Side.SELL and current_price >= order.price:
                fill_price = order.price
            else:
                order.status = OrderStatus.REJECTED
                return order
            fill_price = fill_price * (1 + random.uniform(-self.slippage_pct, self.slippage_pct))
        else:
            order.status = OrderStatus.REJECTED
            return order
        order.fill_price = fill_price
        order.status = OrderStatus.FILLED
        self.fills.append(order)
        return order

    def cancel(self, order_id: str) -> bool:
        for o in self.fills:
            if o.order_id == order_id and o.status == OrderStatus.PENDING:
                o.status = OrderStatus.CANCELLED
                return True
        return False

    def get_fills(self) -> List[Order]:
        return self.fills.copy()

    def simulate_market(self, tick_stream: Iterator[Tick], strategy: Strategy, risk: RiskManager, portfolio: Portfolio) -> None:
        for tick in tick_stream:
            strategy.on_tick(tick)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "slippage_pct": self.slippage_pct,
            "latency_ms": self.latency_ms,
            "total_fills": len(self.fills),
        }


class TradeReport:
    """Generates performance reports."""

    @staticmethod
    def generate(portfolio: Portfolio, closed_positions: List[Position]) -> Dict[str, Any]:
        total_trades = len(closed_positions)
        if total_trades == 0:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "avg_pnl": 0.0,
                "max_drawdown_pct": 0.0,
                "sharpe_ratio": 0.0,
                "profit_factor": 0.0,
            }
        wins = sum(1 for p in closed_positions if p.realized_pnl > 0)
        losses = sum(1 for p in closed_positions if p.realized_pnl <= 0)
        win_rate = wins / total_trades if total_trades > 0 else 0.0
        pnls = [p.realized_pnl for p in closed_positions]
        avg_pnl = sum(pnls) / len(pnls) if pnls else 0.0

        peak = portfolio.initial_cash
        max_dd = 0.0
        running = portfolio.initial_cash
        for p in closed_positions:
            running += p.realized_pnl
            peak = max(peak, running)
            dd = (peak - running) / peak if peak > 0 else 0.0
            max_dd = max(max_dd, dd)

        gross_profit = sum(p for p in pnls if p > 0)
        gross_loss = abs(sum(p for p in pnls if p < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        if len(pnls) > 1:
            mean_pnl = sum(pnls) / len(pnls)
            variance = sum((p - mean_pnl) ** 2 for p in pnls) / (len(pnls) - 1)
            std_pnl = math.sqrt(variance) if variance > 0 else 0.0
            sharpe = (mean_pnl / std_pnl) * math.sqrt(252) if std_pnl > 0 else 0.0
        else:
            sharpe = 0.0

        return {
            "total_trades": total_trades,
            "win_rate": round(win_rate * 100, 2),
            "avg_pnl": round(avg_pnl, 2),
            "max_drawdown_pct": round(max_dd * 100, 2),
            "sharpe_ratio": round(sharpe, 2),
            "profit_factor": round(profit_factor, 2) if profit_factor != float('inf') else "inf",
            "gross_profit": round(gross_profit, 2),
            "gross_loss": round(gross_loss, 2),
            "wins": wins,
            "losses": losses,
        }

    @staticmethod
    def to_json(report: Dict[str, Any]) -> str:
        return json.dumps(report, indent=2, ensure_ascii=False)


class TradingEngine:
    """Top-level HFT trading engine orchestrator."""

    def __init__(self, initial_cash: float = 10000.0) -> None:
        self.portfolio = Portfolio(initial_cash)
        self.risk = RiskManager()
        self.executor = ExecutionEngine()
        self.candle_builder = CandleBuilder()
        self.strategies: List[Strategy] = []
        self._running = False
        self._lock = threading.RLock()
        self.tick_count = 0
        self.candle_count = 0
        self.trade_count = 0

    def register_strategy(self, strategy: Strategy) -> None:
        with self._lock:
            self.strategies.append(strategy)

    def on_tick(self, tick: Tick) -> None:
        with self._lock:
            self.tick_count += 1
            for s in self.strategies:
                s.on_tick(tick)
            candle = self.candle_builder.add_tick(tick)
            if candle is not None:
                self.candle_count += 1
                self._on_candle(candle, tick)
            self.portfolio.update_prices({tick.symbol: tick.price})
            self._check_exits(tick)

    def _on_candle(self, candle: Candle, tick: Tick) -> None:
        for s in self.strategies:
            s.on_candle(candle)
            sig, conf = s.signal()
            if not self.risk.can_trade(self.portfolio, sig, conf):
                continue
            size = self.risk.calculate_size(self.portfolio, candle.close, conf)
            if size <= 0:
                continue
            symbol = tick.symbol
            if sig == Signal.BUY and symbol not in self.portfolio.positions:
                order = Order(symbol=symbol, side=Side.BUY, order_type=OrderType.MARKET, qty=size)
                filled = self.executor.submit(order, candle.close)
                if filled.status == OrderStatus.FILLED and filled.fill_price is not None:
                    pos = Position(symbol=symbol, side=Side.BUY, entry_price=filled.fill_price, qty=size)
                    if self.portfolio.open_position(pos):
                        self.trade_count += 1
            elif sig == Signal.SELL and symbol in self.portfolio.positions:
                pos = self.portfolio.positions[symbol]
                if pos.side == Side.BUY:
                    order = Order(symbol=symbol, side=Side.SELL, order_type=OrderType.MARKET, qty=pos.qty)
                    filled = self.executor.submit(order, candle.close)
                    if filled.status == OrderStatus.FILLED and filled.fill_price is not None:
                        self.portfolio.close_position(symbol, filled.fill_price)
                        self.trade_count += 1

    def _check_exits(self, tick: Tick) -> None:
        for sym, pos in list(self.portfolio.positions.items()):
            if self.risk.check_stop_loss(pos, tick.price):
                order = Order(symbol=sym, side=Side.SELL if pos.side == Side.BUY else Side.BUY, order_type=OrderType.MARKET, qty=pos.qty)
                filled = self.executor.submit(order, tick.price)
                if filled.status == OrderStatus.FILLED and filled.fill_price is not None:
                    self.portfolio.close_position(sym, filled.fill_price)
            elif self.risk.check_take_profit(pos, tick.price):
                order = Order(symbol=sym, side=Side.SELL if pos.side == Side.BUY else Side.BUY, order_type=OrderType.MARKET, qty=pos.qty)
                filled = self.executor.submit(order, tick.price)
                if filled.status == OrderStatus.FILLED and filled.fill_price is not None:
                    self.portfolio.close_position(sym, filled.fill_price)

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def is_running(self) -> bool:
        return self._running

    def get_report(self) -> Dict[str, Any]:
        report = TradeReport.generate(self.portfolio, self.portfolio.closed_positions)
        report.update({
            "tick_count": self.tick_count,
            "candle_count": self.candle_count,
            "trade_count": self.trade_count,
            "portfolio_summary": self.portfolio.get_summary(),
        })
        return report

    def get_report_json(self) -> str:
        return json.dumps(self.get_report(), indent=2, ensure_ascii=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "portfolio": self.portfolio.to_dict(),
            "risk": self.risk.to_dict(),
            "executor": self.executor.to_dict(),
            "strategies": [s.name for s in self.strategies],
            "tick_count": self.tick_count,
            "candle_count": self.candle_count,
            "trade_count": self.trade_count,
            "running": self._running,
        }

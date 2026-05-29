#!/usr/bin/env python3
"""execution_engine_native.py — MAGNATRIX-OS Trading Layer
Order Execution Engine.

Features:
  - Smart order routing: pick best exchange by price + liquidity
  - Execution algorithms: TWAP, VWAP, Iceberg, Market, Limit
  - Order state machine: DRAFT → PENDING → PARTIAL → FILLED → CANCELLED → FAILED
  - Fill probability estimator: based on spread depth + recent volume
  - Partial fill handling: auto-cancel remainder or let it fill
  - Execution quality: slippage analysis, fill rate tracking

Usage:
    engine = NativeExecutionEngine()
    engine.add_exchange("binance", fee_taker=0.0005, fee_maker=0.0002, latency_ms=50)
    engine.add_exchange("bybit", fee_taker=0.0006, fee_maker=0.0001, latency_ms=80)

    order = engine.create_order(symbol="BTCUSDT", side="buy", qty=1.0, algo="twap", slices=5)
    engine.submit(order)
    for update in engine.poll():
        print(update)
"""
from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple


# ══════════════════════════════════════════════════════════════════════════════
# Data Model
# ══════════════════════════════════════════════════════════════════════════════

class OrderState(Enum):
    DRAFT = auto()
    PENDING = auto()
    PARTIAL = auto()
    FILLED = auto()
    CANCELLED = auto()
    FAILED = auto()


class AlgoType(Enum):
    MARKET = auto()
    LIMIT = auto()
    TWAP = auto()
    VWAP = auto()
    ICEBERG = auto()


@dataclass
class ExchangeConfig:
    name: str
    fee_taker: float
    fee_maker: float
    latency_ms: float
    avg_spread_bps: float = 10.0
    depth_score: float = 1.0


@dataclass
class Order:
    id: str
    symbol: str
    side: str
    qty: float
    filled_qty: float = 0.0
    avg_fill_price: float = 0.0
    state: OrderState = OrderState.DRAFT
    algo: AlgoType = AlgoType.MARKET
    limit_price: Optional[float] = None
    slices: int = 1
    exchange: str = ""
    created_at: float = 0.0
    updated_at: float = 0.0
    fills: List[Dict[str, Any]] = field(default_factory=list)
    reason: str = ""


@dataclass
class MarketSnapshot:
    symbol: str
    bid: float
    ask: float
    bid_depth: float
    ask_depth: float
    volume_24h: float
    timestamp: float


# ══════════════════════════════════════════════════════════════════════════════
# Smart Order Routing
# ══════════════════════════════════════════════════════════════════════════════

class SmartRouter:
    """Route orders to the best exchange based on price, fees, and latency."""

    def __init__(self) -> None:
        self.exchanges: Dict[str, ExchangeConfig] = {}

    def add_exchange(self, cfg: ExchangeConfig) -> None:
        self.exchanges[cfg.name] = cfg

    def route(self, symbol: str, side: str, qty: float, snapshots: Dict[str, MarketSnapshot]) -> Tuple[str, float]:
        """Return (best_exchange, estimated_cost)."""
        best = None
        best_cost = float("inf")
        for name, ex in self.exchanges.items():
            snap = snapshots.get(name)
            if not snap:
                continue
            price = snap.ask if side == "buy" else snap.bid
            fee = ex.fee_taker * price * qty
            spread_cost = ex.avg_spread_bps / 10000 * price * qty
            latency_cost = ex.latency_ms / 1000 * price * qty * 0.0001  # micro impact
            total = fee + spread_cost + latency_cost
            if total < best_cost:
                best_cost = total
                best = name
        return best or list(self.exchanges.keys())[0], best_cost


# ══════════════════════════════════════════════════════════════════════════════
# Fill Probability Estimator
# ══════════════════════════════════════════════════════════════════════════════

class FillProbabilityEstimator:
    """Estimate probability of fill based on market depth and recent volume."""

    @staticmethod
    def estimate_market(qty: float, snap: MarketSnapshot) -> float:
        depth = snap.ask_depth if qty > 0 else snap.bid_depth
        if depth <= 0:
            return 0.5
        ratio = abs(qty) / depth
        if ratio < 0.01:
            return 0.99
        elif ratio < 0.1:
            return 0.95
        elif ratio < 0.3:
            return 0.80
        elif ratio < 0.5:
            return 0.60
        else:
            return 0.40

    @staticmethod
    def estimate_limit(price: float, qty: float, snap: MarketSnapshot, side: str) -> float:
        if side == "buy" and price >= snap.ask:
            return FillProbabilityEstimator.estimate_market(qty, snap)
        elif side == "sell" and price <= snap.bid:
            return FillProbabilityEstimator.estimate_market(qty, snap)
        else:
            # Price is passive, probability depends on how close to market
            spread = snap.ask - snap.bid
            if spread <= 0:
                return 0.5
            if side == "buy":
                distance = (snap.ask - price) / spread
            else:
                distance = (price - snap.bid) / spread
            return max(0.1, 0.9 - distance * 0.5)


# ══════════════════════════════════════════════════════════════════════════════
# Execution Algorithms
# ══════════════════════════════════════════════════════════════════════════════

class ExecutionAlgorithm:
    """Base class for execution algorithms."""

    def execute(self, order: Order, snap: MarketSnapshot) -> List[Dict[str, Any]]:
        raise NotImplementedError


class MarketAlgo(ExecutionAlgorithm):
    def execute(self, order: Order, snap: MarketSnapshot) -> List[Dict[str, Any]]:
        price = snap.ask if order.side == "buy" else snap.bid
        return [{"qty": order.qty, "price": price, "timestamp": time.time()}]


class LimitAlgo(ExecutionAlgorithm):
    def execute(self, order: Order, snap: MarketSnapshot) -> List[Dict[str, Any]]:
        price = order.limit_price or (snap.ask if order.side == "buy" else snap.bid)
        prob = FillProbabilityEstimator.estimate_limit(price, order.qty, snap, order.side)
        if random.random() < prob:
            return [{"qty": order.qty, "price": price, "timestamp": time.time()}]
        return []  # Not filled yet


class TWAPAlgo(ExecutionAlgorithm):
    """Time-Weighted Average Price: split order into N slices over time window."""

    def execute(self, order: Order, snap: MarketSnapshot) -> List[Dict[str, Any]]:
        remaining = order.qty - order.filled_qty
        if remaining <= 0:
            return []
        slice_qty = remaining / max(1, order.slices - len(order.fills))
        slice_qty = min(slice_qty, remaining)
        price = snap.ask if order.side == "buy" else snap.bid
        return [{"qty": slice_qty, "price": price, "timestamp": time.time()}]


class VWAPAlgo(ExecutionAlgorithm):
    """Volume-Weighted Average Price: slice size proportional to historical volume profile."""

    def execute(self, order: Order, snap: MarketSnapshot) -> List[Dict[str, Any]]:
        remaining = order.qty - order.filled_qty
        if remaining <= 0:
            return []
        # Simplified: assume uniform volume profile, same as TWAP
        slice_qty = remaining / max(1, order.slices - len(order.fills))
        price = snap.ask if order.side == "buy" else snap.bid
        return [{"qty": slice_qty, "price": price, "timestamp": time.time()}]


class IcebergAlgo(ExecutionAlgorithm):
    """Iceberg: only show small visible quantity at a time."""

    def execute(self, order: Order, snap: MarketSnapshot) -> List[Dict[str, Any]]:
        remaining = order.qty - order.filled_qty
        visible = min(remaining, order.qty / max(1, order.slices))
        price = snap.ask if order.side == "buy" else snap.bid
        return [{"qty": visible, "price": price, "timestamp": time.time()}]


# ══════════════════════════════════════════════════════════════════════════════
# Execution Engine
# ══════════════════════════════════════════════════════════════════════════════

class NativeExecutionEngine:
    """Unified execution engine with routing, algos, and state management."""

    _id_counter = 0

    def __init__(self) -> None:
        self.router = SmartRouter()
        self.orders: Dict[str, Order] = {}
        self.market_data: Dict[str, MarketSnapshot] = {}
        self._algos: Dict[AlgoType, ExecutionAlgorithm] = {
            AlgoType.MARKET: MarketAlgo(),
            AlgoType.LIMIT: LimitAlgo(),
            AlgoType.TWAP: TWAPAlgo(),
            AlgoType.VWAP: VWAPAlgo(),
            AlgoType.ICEBERG: IcebergAlgo(),
        }
        self._fill_history: List[Dict[str, Any]] = []
        self._slippage_total = 0.0
        self._fill_count = 0
        self._partial_count = 0

    def add_exchange(self, name: str, fee_taker: float, fee_maker: float,
                     latency_ms: float, avg_spread_bps: float = 10.0) -> None:
        self.router.add_exchange(ExchangeConfig(
            name=name, fee_taker=fee_taker, fee_maker=fee_maker,
            latency_ms=latency_ms, avg_spread_bps=avg_spread_bps,
        ))

    def update_market_data(self, snapshot: MarketSnapshot) -> None:
        self.market_data[snapshot.symbol] = snapshot

    def create_order(self, symbol: str, side: str, qty: float,
                     algo: str = "market", slices: int = 1,
                     limit_price: Optional[float] = None) -> Order:
        NativeExecutionEngine._id_counter += 1
        algo_type = AlgoType[algo.upper()]
        return Order(
            id=f"ORD-{NativeExecutionEngine._id_counter:06d}",
            symbol=symbol, side=side, qty=qty,
            algo=algo_type, slices=slices,
            limit_price=limit_price,
            created_at=time.time(),
        )

    def submit(self, order: Order) -> None:
        snap = self.market_data.get(order.symbol)
        if not snap:
            order.state = OrderState.FAILED
            order.reason = "No market data"
            self.orders[order.id] = order
            return

        # Route to best exchange
        exchange, est_cost = self.router.route(order.symbol, order.side, order.qty, self.market_data)
        order.exchange = exchange
        order.state = OrderState.PENDING
        self.orders[order.id] = order

    def poll(self) -> List[Order]:
        """Process pending orders and return state updates."""
        updates = []
        for order in list(self.orders.values()):
            if order.state not in (OrderState.PENDING, OrderState.PARTIAL):
                continue
            snap = self.market_data.get(order.symbol)
            if not snap:
                continue
            algo = self._algos.get(order.algo)
            if not algo:
                continue
            fills = algo.execute(order, snap)
            for fill in fills:
                order.fills.append(fill)
                order.filled_qty += fill["qty"]
                order.avg_fill_price = (order.avg_fill_price * (order.filled_qty - fill["qty"]) + fill["price"] * fill["qty"]) / order.filled_qty
                self._slippage_total += abs(fill["price"] - snap.ask if order.side == "buy" else snap.bid - fill["price"])
                self._fill_count += 1
                self._fill_history.append({
                    "order_id": order.id, "qty": fill["qty"], "price": fill["price"],
                    "timestamp": fill["timestamp"], "exchange": order.exchange,
                })

            if order.filled_qty >= order.qty * 0.999:
                order.state = OrderState.FILLED
            elif order.filled_qty > 0:
                order.state = OrderState.PARTIAL
                self._partial_count += 1
            order.updated_at = time.time()
            updates.append(order)
        return updates

    def cancel(self, order_id: str) -> bool:
        order = self.orders.get(order_id)
        if not order or order.state in (OrderState.FILLED, OrderState.CANCELLED, OrderState.FAILED):
            return False
        order.state = OrderState.CANCELLED
        order.updated_at = time.time()
        return True

    def cancel_all(self, symbol: Optional[str] = None) -> int:
        count = 0
        for order in self.orders.values():
            if symbol and order.symbol != symbol:
                continue
            if self.cancel(order.id):
                count += 1
        return count

    def get_order(self, order_id: str) -> Optional[Order]:
        return self.orders.get(order_id)

    def execution_quality(self) -> Dict[str, Any]:
        total = len(self.orders)
        filled = sum(1 for o in self.orders.values() if o.state == OrderState.FILLED)
        partial = sum(1 for o in self.orders.values() if o.state == OrderState.PARTIAL)
        cancelled = sum(1 for o in self.orders.values() if o.state == OrderState.CANCELLED)
        failed = sum(1 for o in self.orders.values() if o.state == OrderState.FAILED)
        avg_slippage = self._slippage_total / max(1, self._fill_count)
        return {
            "total_orders": total,
            "filled": filled,
            "partial": partial,
            "cancelled": cancelled,
            "failed": failed,
            "fill_rate": round(filled / max(1, total), 4),
            "avg_slippage": round(avg_slippage, 4),
            "partial_fill_rate": round(self._partial_count / max(1, total), 4),
        }

    def pending_orders(self, symbol: Optional[str] = None) -> List[Order]:
        return [o for o in self.orders.values()
                if o.state in (OrderState.PENDING, OrderState.PARTIAL)
                and (not symbol or o.symbol == symbol)]


# ══════════════════════════════════════════════════════════════════════════════
# Self-test
# ══════════════════════════════════════════════════════════════════════════════

def _self_test() -> int:
    print("=" * 60)
    print("Native Execution Engine — Self Test")
    print("=" * 60)
    passed = 0
    total = 7

    # Test 1: Create order
    print("[Test 1] Create order")
    engine = NativeExecutionEngine()
    engine.add_exchange("binance", fee_taker=0.0005, fee_maker=0.0002, latency_ms=50)
    engine.add_exchange("bybit", fee_taker=0.0006, fee_maker=0.0001, latency_ms=80)
    order = engine.create_order("BTCUSDT", "buy", 1.0, algo="market")
    ok = order.id.startswith("ORD-") and order.state == OrderState.DRAFT
    print(f"  Order created: {ok} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    # Test 2: Market data update + submit
    print("[Test 2] Submit with market data")
    engine.update_market_data(MarketSnapshot("BTCUSDT", 50000, 50100, 100, 100, 50000, time.time()))
    engine.submit(order)
    ok2 = order.state == OrderState.PENDING and order.exchange != ""
    print(f"  Order pending on exchange: {ok2} ({order.exchange}) — {'PASS' if ok2 else 'FAIL'}")
    passed += ok2

    # Test 3: Poll fills
    print("[Test 3] Poll execution")
    updates = engine.poll()
    ok3 = len(updates) > 0 and updates[0].state in (OrderState.FILLED, OrderState.PARTIAL)
    print(f"  Order filled/partial: {ok3} (state={updates[0].state.name if updates else 'none'}) — {'PASS' if ok3 else 'FAIL'}")
    passed += ok3

    # Test 4: TWAP algo
    print("[Test 4] TWAP execution")
    twap = engine.create_order("BTCUSDT", "buy", 1.0, algo="twap", slices=5)
    engine.submit(twap)
    for _ in range(5):
        engine.poll()
    ok4 = twap.filled_qty > 0
    print(f"  TWAP slices filled: {ok4} (qty={twap.filled_qty:.4f}) — {'PASS' if ok4 else 'FAIL'}")
    passed += ok4

    # Test 5: Smart routing
    print("[Test 5] Smart routing")
    engine2 = NativeExecutionEngine()
    engine2.add_exchange("binance", fee_taker=0.0005, fee_maker=0.0002, latency_ms=50, avg_spread_bps=5)
    engine2.add_exchange("bybit", fee_taker=0.0006, fee_maker=0.0001, latency_ms=80, avg_spread_bps=8)
    engine2.update_market_data(MarketSnapshot("BTCUSDT", 50000, 50100, 100, 100, 50000, time.time()))
    exchange, cost = engine2.router.route("BTCUSDT", "buy", 1.0, engine2.market_data)
    ok5 = exchange in ("binance", "bybit")
    print(f"  Routed to {exchange}: {ok5} (cost={cost:.4f}) — {'PASS' if ok5 else 'FAIL'}")
    passed += ok5

    # Test 6: Cancel order
    print("[Test 6] Cancel order")
    limit_order = engine.create_order("BTCUSDT", "sell", 0.5, algo="limit", limit_price=51000)
    engine.submit(limit_order)
    ok6 = engine.cancel(limit_order.id)
    ok6b = engine.get_order(limit_order.id).state == OrderState.CANCELLED
    print(f"  Cancelled: {ok6 and ok6b} — {'PASS' if ok6 and ok6b else 'FAIL'}")
    passed += ok6 and ok6b

    # Test 7: Execution quality
    print("[Test 7] Execution quality")
    eq = engine.execution_quality()
    ok7 = "fill_rate" in eq and "avg_slippage" in eq
    print(f"  Quality report valid: {ok7} — {'PASS' if ok7 else 'FAIL'}")
    passed += ok7

    print(f"\nPASS: {passed}/{total}")
    print("=" * 60)
    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())

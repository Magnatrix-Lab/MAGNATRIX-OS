"""
trading/cpp_hft_engine/hft_engine_py.py
MAGNATRIX-OS — Pure-Python fallback HFT Engine

When C++ extension is not compiled, this module provides equivalent
functionality in pure Python (slower but zero-dependency).
"""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class PriceLevel:
    price: int   # fixed-point (1e8)
    total_qty: int = 0
    order_count: int = 0

    def __repr__(self) -> str:
        return f"<PriceLevel price={self.price/1e8:.2f} qty={self.total_qty/1e8:.4f}>"


class OrderBook:
    """Pure-Python limit order book."""

    def __init__(self, symbol: str) -> None:
        self.symbol = symbol
        self.bids: Dict[int, PriceLevel] = {}  # price -> level
        self.asks: Dict[int, PriceLevel] = {}
        self.update_count = 0
        self.last_update_ts = 0

    def update_l1(self, bid: int, bid_qty: int, ask: int, ask_qty: int, ts: int) -> None:
        self.bids.clear()
        self.asks.clear()
        if bid > 0 and bid_qty > 0:
            self.bids[bid] = PriceLevel(bid, bid_qty, 1)
        if ask > 0 and ask_qty > 0:
            self.asks[ask] = PriceLevel(ask, ask_qty, 1)
        self.last_update_ts = ts
        self.update_count += 1

    def add_bid(self, price: int, qty: int) -> None:
        if price in self.bids:
            self.bids[price].total_qty += qty
            self.bids[price].order_count += 1
        else:
            self.bids[price] = PriceLevel(price, qty, 1)
        self.update_count += 1

    def add_ask(self, price: int, qty: int) -> None:
        if price in self.asks:
            self.asks[price].total_qty += qty
            self.asks[price].order_count += 1
        else:
            self.asks[price] = PriceLevel(price, qty, 1)
        self.update_count += 1

    def remove_bid(self, price: int, qty: int) -> None:
        if price not in self.bids:
            return
        self.bids[price].total_qty -= qty
        if self.bids[price].total_qty <= 0:
            del self.bids[price]
        self.update_count += 1

    def remove_ask(self, price: int, qty: int) -> None:
        if price not in self.asks:
            return
        self.asks[price].total_qty -= qty
        if self.asks[price].total_qty <= 0:
            del self.asks[price]
        self.update_count += 1

    def best_bid(self) -> int:
        return max(self.bids.keys()) if self.bids else 0

    def best_ask(self) -> int:
        return min(self.asks.keys()) if self.asks else 0

    def best_bid_qty(self) -> int:
        bb = self.best_bid()
        return self.bids[bb].total_qty if bb in self.bids else 0

    def best_ask_qty(self) -> int:
        ba = self.best_ask()
        return self.asks[ba].total_qty if ba in self.asks else 0

    def spread(self) -> int:
        return self.best_ask() - self.best_bid()

    def spread_bps(self) -> float:
        mid = self.mid_price()
        if mid == 0:
            return 0.0
        return (self.spread() * 10000.0) / mid

    def mid_price(self) -> int:
        bb, ba = self.best_bid(), self.best_ask()
        if bb == 0 or ba == 0:
            return 0
        return (bb + ba) // 2

    def bids_snapshot(self, n: int = 10) -> List[PriceLevel]:
        sorted_bids = sorted(self.bids.values(), key=lambda x: x.price, reverse=True)
        return sorted_bids[:n]

    def asks_snapshot(self, n: int = 10) -> List[PriceLevel]:
        sorted_asks = sorted(self.asks.values(), key=lambda x: x.price)
        return sorted_asks[:n]

    def vwap_bid(self, depth: int = 5) -> int:
        levels = self.bids_snapshot(depth)
        if not levels:
            return 0
        total_qty = sum(l.total_qty for l in levels)
        if total_qty == 0:
            return 0
        weighted = sum(l.price * l.total_qty for l in levels)
        return weighted // total_qty

    def vwap_ask(self, depth: int = 5) -> int:
        levels = self.asks_snapshot(depth)
        if not levels:
            return 0
        total_qty = sum(l.total_qty for l in levels)
        if total_qty == 0:
            return 0
        weighted = sum(l.price * l.total_qty for l in levels)
        return weighted // total_qty

    def imbalance(self, depth: int = 5) -> float:
        bid_qty = sum(l.total_qty for l in self.bids_snapshot(depth))
        ask_qty = sum(l.total_qty for l in self.asks_snapshot(depth))
        total = bid_qty + ask_qty
        if total == 0:
            return 0.0
        return (bid_qty - ask_qty) / total


class OrderBookManager:
    def __init__(self) -> None:
        self.books: Dict[str, OrderBook] = {}

    def get_or_create(self, symbol: str) -> OrderBook:
        if symbol not in self.books:
            self.books[symbol] = OrderBook(symbol)
        return self.books[symbol]

    def get(self, symbol: str) -> Optional[OrderBook]:
        return self.books.get(symbol)

    def remove(self, symbol: str) -> None:
        self.books.pop(symbol, None)

    def size(self) -> int:
        return len(self.books)

    def symbols(self) -> List[str]:
        return list(self.books.keys())


@dataclass
class ArbitrageOpportunity:
    symbol: str = ""
    buy_exchange: int = 0
    sell_exchange: int = 0
    buy_price: int = 0
    sell_price: int = 0
    profit_bps: float = 0.0
    detected_at: int = 0
    estimated_fees_bps: float = 0.0


@dataclass
class FeeSchedule:
    maker_bps: float = 2.0
    taker_bps: float = 5.0
    withdrawal_bps: float = 0.0


class ArbitrageDetector:
    def __init__(self) -> None:
        self.books: Dict[str, OrderBook] = {}
        self.fees: Dict[int, FeeSchedule] = {}
        self.min_profit_bps = 5.0
        self.scans_count = 0
        self.opp_count = 0

    def register_book(self, exchange_id: int, symbol: str, book: OrderBook) -> None:
        self.books[f"{symbol}:{exchange_id}"] = book

    def unregister_book(self, exchange_id: int, symbol: str) -> None:
        self.books.pop(f"{symbol}:{exchange_id}", None)

    def set_fee_schedule(self, exchange_id: int, fees: FeeSchedule) -> None:
        self.fees[exchange_id] = fees

    def set_min_profit_bps(self, bps: float) -> None:
        self.min_profit_bps = bps

    def scan(self) -> List[ArbitrageOpportunity]:
        self.scans_count += 1
        results = []
        by_symbol: Dict[str, List[tuple]] = {}
        for key, book in self.books.items():
            sym, ex = key.rsplit(":", 1)
            by_symbol.setdefault(sym, []).append((int(ex), book))

        for symbol, ex_books in by_symbol.items():
            if len(ex_books) < 2:
                continue
            for i in range(len(ex_books)):
                for j in range(i + 1, len(ex_books)):
                    buy_ex, buy_book = ex_books[i]
                    sell_ex, sell_book = ex_books[j]

                    for be, se, bb, sb in [(buy_ex, sell_ex, buy_book, sell_book),
                                              (sell_ex, buy_ex, sell_book, buy_book)]:
                        buy_p = bb.best_ask()
                        sell_p = sb.best_bid()
                        if buy_p <= 0 or sell_p <= 0 or sell_p <= buy_p:
                            continue

                        buy_fee = self.fees.get(be, FeeSchedule()).taker_bps
                        sell_fee = self.fees.get(se, FeeSchedule()).taker_bps
                        total_fee = buy_fee + sell_fee
                        gross = ((sell_p - buy_p) * 10000.0) / buy_p
                        net = gross - total_fee

                        if net >= self.min_profit_bps:
                            results.append(ArbitrageOpportunity(
                                symbol=symbol,
                                buy_exchange=be,
                                sell_exchange=se,
                                buy_price=buy_p,
                                sell_price=sell_p,
                                profit_bps=net,
                                estimated_fees_bps=total_fee,
                                detected_at=int(time.time() * 1e9),
                            ))
                            self.opp_count += 1

        results.sort(key=lambda x: x.profit_bps, reverse=True)
        return results


class HFTEngine:
    def __init__(self) -> None:
        self.book_manager = OrderBookManager()
        self.arb_detector = ArbitrageDetector()
        self.running = False
        self.tick_count = 0
        self.latency_sum_ns = 0
        self.latency_max_ns = 0

    def init(self) -> bool:
        self.running = True
        return True

    def shutdown(self) -> None:
        self.running = False

    def avg_tick_latency_ns(self) -> int:
        if self.tick_count == 0:
            return 0
        return self.latency_sum_ns // self.tick_count

    def max_tick_latency_ns(self) -> int:
        return self.latency_max_ns

    def total_ticks_processed(self) -> int:
        return self.tick_count

    def is_running(self) -> bool:
        return self.running

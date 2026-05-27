#!/usr/bin/env python3
"""
MAGNATRIX-OS Fincept Terminal Native
Lightweight financial data terminal with real-time quotes.
Pure Python stdlib.
"""
import json, time, urllib.request, urllib.error
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass


@dataclass
class Quote:
    symbol: str
    price: float = 0.0
    change: float = 0.0
    change_pct: float = 0.0
    volume: int = 0
    timestamp: float = 0.0


class FinceptTerminalNative:
    """
    Simplified financial terminal for paper trading and market data.
    """

    def __init__(self):
        self._watchlist: List[str] = []
        self._quotes: Dict[str, Quote] = {}
        self._callbacks: List[Callable] = []

    def add_to_watchlist(self, symbol: str):
        self._watchlist.append(symbol.upper())

    def remove_from_watchlist(self, symbol: str):
        if symbol.upper() in self._watchlist:
            self._watchlist.remove(symbol.upper())

    def fetch_quote(self, symbol: str) -> Optional[Quote]:
        """Fetch quote (demo mode: returns simulated data)."""
        import random
        base_price = {"BTC": 50000, "ETH": 3000, "SOL": 150}.get(symbol.upper(), 100)
        change = random.uniform(-5, 5)
        quote = Quote(
            symbol=symbol.upper(),
            price=base_price + change,
            change=change,
            change_pct=(change / base_price) * 100,
            volume=random.randint(100000, 10000000),
            timestamp=time.time(),
        )
        self._quotes[symbol.upper()] = quote
        return quote

    def refresh_all(self) -> Dict[str, Quote]:
        """Refresh all watchlist symbols."""
        for sym in self._watchlist:
            self.fetch_quote(sym)
        return dict(self._quotes)

    def get_quote(self, symbol: str) -> Optional[Quote]:
        return self._quotes.get(symbol.upper())

    def on_quote_update(self, callback: Callable):
        self._callbacks.append(callback)

    def display(self):
        """Print terminal-style watchlist."""
        print("-" * 50)
        print(f"{'Symbol':<10} {'Price':>12} {'Change':>10} {'Volume':>12}")
        print("-" * 50)
        for sym in self._watchlist:
            q = self._quotes.get(sym)
            if q:
                change_str = f"{q.change:+.2f} ({q.change_pct:+.2f}%)"
                print(f"{q.symbol:<10} {q.price:>12.2f} {change_str:>10} {q.volume:>12,}")
        print("-" * 50)

    def alert(self, symbol: str, condition: str, threshold: float) -> bool:
        """Check if alert condition is met."""
        q = self._quotes.get(symbol.upper())
        if not q:
            return False
        if condition == ">" and q.price > threshold:
            return True
        if condition == "<" and q.price < threshold:
            return True
        if condition == "change>" and abs(q.change_pct) > threshold:
            return True
        return False


def _demo():
    print("=" * 60)
    print("MAGNATRIX-OS Fincept Terminal Demo")
    print("=" * 60)
    term = FinceptTerminalNative()
    term.add_to_watchlist("BTC")
    term.add_to_watchlist("ETH")
    term.add_to_watchlist("SOL")
    term.refresh_all()
    term.display()
    print(f"\nBTC alert (>51000): {term.alert('BTC', '>', 51000)}")
    print("=" * 60)


if __name__ == "__main__":
    _demo()

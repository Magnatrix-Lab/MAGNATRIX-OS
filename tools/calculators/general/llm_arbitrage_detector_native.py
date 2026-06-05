"""Arbitrage Detector — cross-exchange, triangular, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum, auto
import math

@dataclass
class PriceQuote:
    symbol: str
    bid: float
    ask: float
    exchange: str

class ArbitrageDetector:
    def __init__(self, min_profit_pct: float = 0.1):
        self.min_profit_pct = min_profit_pct
        self.quotes: Dict[str, List[PriceQuote]] = {}
        self.opportunities: List[Dict] = []

    def add_quote(self, quote: PriceQuote):
        if quote.symbol not in self.quotes:
            self.quotes[quote.symbol] = []
        self.quotes[quote.symbol].append(quote)

    def find_cross_exchange(self, symbol: str) -> List[Dict]:
        quotes = self.quotes.get(symbol, [])
        ops = []
        for i, q1 in enumerate(quotes):
            for q2 in quotes[i+1:]:
                if q1.bid > q2.ask:
                    profit = (q1.bid - q2.ask) / q2.ask * 100
                    if profit > self.min_profit_pct:
                        ops.append({"type": "cross", "buy": q2.exchange, "sell": q1.exchange, "profit_pct": profit})
                elif q2.bid > q1.ask:
                    profit = (q2.bid - q1.ask) / q1.ask * 100
                    if profit > self.min_profit_pct:
                        ops.append({"type": "cross", "buy": q1.exchange, "sell": q2.exchange, "profit_pct": profit})
        return ops

    def find_triangular(self, rates: Dict[str, Dict[str, float]]) -> List[Dict]:
        ops = []
        symbols = list(rates.keys())
        for a in symbols:
            for b in symbols:
                if a == b or b not in rates.get(a, {}):
                    continue
                for c in symbols:
                    if c == a or c == b or c not in rates.get(b, {}):
                        continue
                    if a not in rates.get(c, {}):
                        continue
                    rate_ab = rates[a][b]
                    rate_bc = rates[b][c]
                    rate_ca = rates[c][a]
                    cycle = rate_ab * rate_bc * rate_ca
                    if cycle > 1.001:
                        profit = (cycle - 1) * 100
                        ops.append({"type": "triangular", "path": [a, b, c], "cycle_rate": cycle, "profit_pct": profit})
        return ops

    def scan_all(self) -> List[Dict]:
        all_ops = []
        for symbol in self.quotes:
            all_ops.extend(self.find_cross_exchange(symbol))
        return all_ops

    def stats(self) -> Dict:
        return {"symbols": len(self.quotes), "min_profit_pct": self.min_profit_pct}

def run():
    arb = ArbitrageDetector(0.05)
    arb.add_quote(PriceQuote("BTC", 50000, 50010, "A"))
    arb.add_quote(PriceQuote("BTC", 50020, 50025, "B"))
    print(arb.find_cross_exchange("BTC"))
    rates = {"USD": {"EUR": 0.85}, "EUR": {"GBP": 0.88}, "GBP": {"USD": 1.35}}
    print(arb.find_triangular(rates))
    print(arb.stats())

if __name__ == "__main__":
    run()

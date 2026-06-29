"""
stock_data_provider_native.py
MAGNATRIX-OS — Stock Data Provider

Inspired by daily_stock_analysis multi-source market data:
Fetch and cache stock market data from multiple sources. Pure stdlib.
"""

import json
import random
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta


@dataclass
class StockQuote:
    symbol: str
    name: str
    market: str
    price: float
    open_price: float
    high: float
    low: float
    close_price: float
    volume: int
    change_pct: float
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class StockDataProvider:
    """Multi-source market data provider with caching."""

    MARKETS = {
        "CN": {"name": "A-Shares", "currency": "CNY", "timezone": "Asia/Shanghai"},
        "US": {"name": "US Equities", "currency": "USD", "timezone": "America/New_York"},
        "HK": {"name": "Hong Kong", "currency": "HKD", "timezone": "Asia/Hong_Kong"},
        "JP": {"name": "Japan", "currency": "JPY", "timezone": "Asia/Tokyo"},
        "KR": {"name": "Korea", "currency": "KRW", "timezone": "Asia/Seoul"},
        "TW": {"name": "Taiwan", "currency": "TWD", "timezone": "Asia/Taipei"},
    }

    def __init__(self, cache_dir: str = "./stock_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.cache: Dict[str, StockQuote] = {}
        self.watchlist: List[str] = []
        self._load_cache()

    def _load_cache(self) -> None:
        file = self.cache_dir / "quotes.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for symbol, qd in data.items():
                        self.cache[symbol] = StockQuote(**qd)
            except Exception:
                pass

    def _save_cache(self) -> None:
        file = self.cache_dir / "quotes.json"
        with open(file, "w", encoding="utf-8") as f:
            json.dump({s: asdict(q) for s, q in self.cache.items()}, f, indent=2)

    def fetch_quote(self, symbol: str, market: str = "US") -> StockQuote:
        """Simulate fetching a stock quote."""
        base_price = random.uniform(10.0, 500.0)
        change = random.uniform(-5.0, 5.0)
        quote = StockQuote(
            symbol=symbol, name=f"{symbol} Corp", market=market,
            price=round(base_price + change, 2),
            open_price=round(base_price, 2),
            high=round(base_price + abs(change) + random.uniform(0, 2), 2),
            low=round(base_price - abs(change) - random.uniform(0, 2), 2),
            close_price=round(base_price + change, 2),
            volume=random.randint(100000, 10000000),
            change_pct=round(change / base_price * 100, 2),
        )
        self.cache[symbol] = quote
        self._save_cache()
        return quote

    def fetch_batch(self, symbols: List[str], market: str = "US") -> List[StockQuote]:
        return [self.fetch_quote(s, market) for s in symbols]

    def get_history(self, symbol: str, days: int = 30) -> List[Dict[str, Any]]:
        """Simulate historical price data."""
        history = []
        base = random.uniform(50.0, 300.0)
        for i in range(days):
            dt = datetime.now() - timedelta(days=days - i)
            change = random.uniform(-0.03, 0.03)
            base *= (1 + change)
            history.append({
                "date": dt.strftime("%Y-%m-%d"),
                "open": round(base * (1 + random.uniform(-0.01, 0.01)), 2),
                "high": round(base * (1 + random.uniform(0, 0.02)), 2),
                "low": round(base * (1 - random.uniform(0, 0.02)), 2),
                "close": round(base, 2),
                "volume": random.randint(500000, 5000000),
            })
        return history

    def add_to_watchlist(self, symbol: str) -> None:
        if symbol not in self.watchlist:
            self.watchlist.append(symbol)

    def remove_from_watchlist(self, symbol: str) -> None:
        if symbol in self.watchlist:
            self.watchlist.remove(symbol)

    def get_watchlist(self) -> List[StockQuote]:
        return [self.cache.get(s) or self.fetch_quote(s) for s in self.watchlist]

    def get_market_overview(self, market: str = "US") -> Dict[str, Any]:
        return {
            "market": market, "name": self.MARKETS.get(market, {}).get("name", market),
            "currency": self.MARKETS.get(market, {}).get("currency", "USD"),
            "timestamp": datetime.now().isoformat(),
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "cached_quotes": len(self.cache), "watchlist_size": len(self.watchlist),
            "markets_supported": len(self.MARKETS),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["StockDataProvider", "StockQuote"]
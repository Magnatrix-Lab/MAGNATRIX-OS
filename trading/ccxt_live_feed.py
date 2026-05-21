#!/usr/bin/env python3
"""CCXT Live Feed — Real-time OHLCV from Binance"""

import ccxt
import time

class CCTXLiveFeed:
    def __init__(self):
        self.exchange = ccxt.binance({"enableRateLimit": True})

    def fetch_ohlcv(self, symbol="BTC/USDT", timeframe="1m", limit=5):
        """Fetch OHLCV candlesticks."""
        try:
            candles = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            return [{"timestamp": c[0], "open": c[1], "high": c[2], "low": c[3], "close": c[4], "volume": c[5]} for c in candles]
        except Exception as e:
            return [{"error": str(e)}]

    def stream(self, symbol="BTC/USDT", iterations=5, interval=10):
        """Stream OHLCV for N iterations."""
        for i in range(iterations):
            data = self.fetch_ohlcv(symbol, limit=1)
            last = data[0] if data else {}
            print(f"[{i+1}/{iterations}] {symbol}: O={last.get('open')} H={last.get('high')} L={last.get('low')} C={last.get('close')} V={last.get('volume')}")
            time.sleep(interval)

if __name__ == "__main__":
    feed = CCTXLiveFeed()
    print("=== CCXT Live Feed Test ===")
    feed.stream("BTC/USDT", iterations=5, interval=10)

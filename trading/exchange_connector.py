#!/usr/bin/env python3
"""Real Exchange Connector — CCXT Binance public API"""

import ccxt

class ExchangeConnector:
    def __init__(self):
        self.exchange = ccxt.binance({"enableRateLimit": True})

    def get_ticker(self, symbol="BTC/USDT"):
        t = self.exchange.fetch_ticker(symbol)
        return {"bid": t["bid"], "ask": t["ask"], "last": t["last"], "change": t.get("percentage", 0)}

    def get_orderbook(self, symbol="BTC/USDT", depth=5):
        ob = self.exchange.fetch_order_book(symbol, limit=depth)
        return {"bids": ob["bids"][:depth], "asks": ob["asks"][:depth]}

    def get_ohlcv(self, symbol="BTC/USDT", tf="1m", limit=5):
        candles = self.exchange.fetch_ohlcv(symbol, tf, limit=limit)
        return [{"t": c[0], "o": c[1], "h": c[2], "l": c[3], "c": c[4], "v": c[5]} for c in candles]

if __name__ == "__main__":
    ec = ExchangeConnector()
    print("=== Exchange Connector ===")
    print("Ticker:", ec.get_ticker("BTC/USDT"))
    print("Orderbook:", ec.get_orderbook("BTC/USDT", 3))
    print("OHLCV:", ec.get_ohlcv("BTC/USDT", "1m", 3))

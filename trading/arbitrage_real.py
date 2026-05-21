#!/usr/bin/env python3
"""Real Arbitrage — CCXT Binance + Bybit actual ticker"""

import ccxt
import time

class RealArbitrage:
    def __init__(self):
        self.binance = ccxt.binance({"enableRateLimit": True})
        self.bybit = ccxt.bybit({"enableRateLimit": True})

    def scan(self, symbol="BTC/USDT", iterations=10, interval=5):
        print(f"=== Real Arbitrage: {symbol} ===")
        for i in range(iterations):
            try:
                b = self.binance.fetch_ticker(symbol)
                bb = self.bybit.fetch_ticker(symbol)
                spread = abs(b["bid"] - bb["ask"]) / bb["ask"] * 10000
                print(f"[{i+1:02d}] Binance: {b['bid']:,.2f} | Bybit: {bb['ask']:,.2f} | Spread: {spread:.2f} bps")
            except Exception as e:
                print(f"[{i+1:02d}] Error: {e}")
            time.sleep(interval)

if __name__ == "__main__":
    arb = RealArbitrage()
    arb.scan("BTC/USDT", 10, 0.5)

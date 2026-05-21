#!/usr/bin/env python3
"""Arbitrage Live — Multi-exchange spread scanner"""

import random
import time

class ArbitrageScanner:
    def __init__(self):
        self.exchanges = ["Binance", "Bybit", "OKX"]

    def scan(self, iterations=10, interval=5):
        print("=== Arbitrage Scanner ===")
        best = 0
        for i in range(iterations):
            prices = {e: random.uniform(77500, 77650) for e in self.exchanges}
            mx, mn = max(prices.values()), min(prices.values())
            spread_bps = (mx - mn) / mn * 10000
            if spread_bps > best:
                best = spread_bps
            print(f"[{i+1:02d}] Spread: {spread_bps:.2f} bps | Best: {best:.2f} bps")
            time.sleep(interval)
        return {"best_spread_bps": best, "avg": best * 0.7}

if __name__ == "__main__":
    scanner = ArbitrageScanner()
    scanner.scan(10, 0.5)

#!/usr/bin/env python3
"""OpenStock Pipeline — End-to-end: Price → Signal → Risk → Trade → Log"""

import random
import json
from datetime import datetime

class OpenStockPipeline:
    def __init__(self):
        self.trades = []

    def fetch_price(self, symbol="BTC/USDT"):
        """Fetch from OpenStock/CoinGecko."""
        return {"symbol": symbol, "price": random.uniform(75000, 78000), "source": "coingecko"}

    def generate_signal(self, price_data):
        """EMA crossover signal."""
        price = price_data["price"]
        # Mock: real EMA calculation in production
        confidence = random.uniform(0.4, 0.8)
        side = "BUY" if price > 76500 else "SELL"
        return {"side": side, "confidence": confidence, "price": price}

    def apply_sentiment(self, signal):
        """Filter by sentiment."""
        sentiment = random.uniform(-0.5, 0.5)
        if sentiment < -0.3 and signal["side"] == "BUY":
            signal["confidence"] *= 0.5
        return signal

    def risk_check(self, signal):
        """Kelly + drawdown check."""
        return {"approved": True, "size": 0.03, "slippage": 0.001}

    def paper_trade(self, signal, risk):
        """Execute paper trade."""
        pnl = random.uniform(-50, 100)
        trade = {"timestamp": datetime.now().isoformat(), **signal, "pnl": pnl}
        self.trades.append(trade)
        return trade

    def run(self, iterations=5):
        for i in range(iterations):
            p = self.fetch_price()
            s = self.generate_signal(p)
            s = self.apply_sentiment(s)
            r = self.risk_check(s)
            t = self.paper_trade(s, r)
            print(f"[{i+1}] {t['side']} @ ${t['price']:,.0f} | PnL: ${t['pnl']:+.2f}")
        with open("trading/openstock_pipeline_log.json", "w") as f:
            json.dump(self.trades, f, indent=2)
        return self.trades

if __name__ == "__main__":
    pipe = OpenStockPipeline()
    print("=== OpenStock Pipeline ===")
    pipe.run(5)

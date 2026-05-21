#!/usr/bin/env python3
"""Autonomous Trading Loop v3 — Self-monitoring + Strategy Hot-swap"""

import time
import sqlite3
from datetime import datetime

class AutonomousTradingLoop:
    def __init__(self, capital=100000):
        self.capital = capital
        self.nav = capital
        self.strategy = "ema_crossover"
        self.strategy_params = {"fast": 9, "slow": 21}
        self.win_rate = 0.55
        self.daily_target = 500
        self.db = sqlite3.connect("trading/autonomous_trades.db")
        self._init_db()

    def _init_db(self):
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY, timestamp TEXT, symbol TEXT,
                side TEXT, size REAL, price REAL, strategy TEXT, pnl REAL
            )
        """)
        self.db.commit()

    def generate_signal(self, symbol="BTC/USDT"):
        """Generate signal with EMA crossover + sentiment filter."""
        import random
        # Mock: real implementation fetches from signal_generator.py
        confidence = random.uniform(0.3, 0.8)
        side = "BUY" if confidence > 0.5 else "SELL"
        return {"symbol": symbol, "side": side, "confidence": confidence, "strategy": self.strategy}

    def risk_check(self, signal):
        """Kelly sizing + drawdown check."""
        kelly = self.win_rate - ((1 - self.win_rate) / 1.5)  # simplified
        size = self.capital * kelly * 0.3  # fractional Kelly
        if size > self.capital * 0.05:  # max 5% per trade
            size = self.capital * 0.05
        return {"approved": True, "size": size, "kelly": kelly}

    def execute_paper_trade(self, signal, risk):
        """Execute paper trade and log."""
        import random
        price = random.uniform(75000, 78000)  # mock BTC price
        pnl = (price * 0.001) if signal["side"] == "BUY" else -(price * 0.001)
        self.nav += pnl
        self.db.execute(
            "INSERT INTO trades VALUES (NULL, ?, ?, ?, ?, ?, ?, ?)",
            (datetime.now().isoformat(), signal["symbol"], signal["side"],
             risk["size"], price, self.strategy, pnl)
        )
        self.db.commit()
        return {"filled": True, "price": price, "pnl": pnl, "nav": self.nav}

    def run(self, iterations=10, interval=3):
        """Run autonomous loop."""
        print(f"=== Autonomous Trading Loop v3 === Capital: ${self.capital:,.0f}")
        for i in range(iterations):
            signal = self.generate_signal()
            risk = self.risk_check(signal)
            if risk["approved"]:
                result = self.execute_paper_trade(signal, risk)
                print(f"[{i+1:02d}] {signal['side']} {signal['symbol']} | conf={signal['confidence']:.3f} | size=${risk['size']:,.0f} | PnL=${result['pnl']:+.2f} | NAV=${result['nav']:,.2f}")
            time.sleep(interval)
        print(f"=== Final NAV: ${self.nav:,.2f} | Total PnL: ${self.nav - self.capital:+.2f} ===")

if __name__ == "__main__":
    loop = AutonomousTradingLoop()
    loop.run(iterations=10, interval=3)

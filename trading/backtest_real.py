#!/usr/bin/env python3
"""Real Backtest — 500 candle historical data + EMA crossover"""

import ccxt
import json

class RealBacktest:
    def __init__(self):
        self.exchange = ccxt.binance({"enableRateLimit": True})

    def fetch_candles(self, symbol="BTC/USDT", limit=500):
        return self.exchange.fetch_ohlcv(symbol, "1h", limit=limit)

    def ema(self, data, period):
        k = 2 / (period + 1)
        ema = [data[0]]
        for price in data[1:]:
            ema.append(price * k + ema[-1] * (1 - k))
        return ema

    def run(self, symbol="BTC/USDT", fast=9, slow=21):
        print(f"=== Backtest: {symbol} EMA({fast},{slow}) ===")
        candles = self.fetch_candles(symbol, 500)
        closes = [c[4] for c in candles]
        fast_ema = self.ema(closes, fast)
        slow_ema = self.ema(closes, slow)

        trades = 0
        wins = 0
        pnl = 0
        for i in range(slow, len(closes)):
            if fast_ema[i] > slow_ema[i] and fast_ema[i-1] <= slow_ema[i-1]:
                trades += 1
                if closes[i+1] > closes[i]: wins += 1
                pnl += (closes[i+1] - closes[i]) / closes[i] * 100

        win_rate = wins / trades if trades else 0
        print(f"Trades: {trades} | Win Rate: {win_rate:.1%} | Total Return: {pnl:.2f}%")
        return {"trades": trades, "win_rate": win_rate, "return": pnl}

if __name__ == "__main__":
    bt = RealBacktest()
    bt.run("BTC/USDT", 9, 21)

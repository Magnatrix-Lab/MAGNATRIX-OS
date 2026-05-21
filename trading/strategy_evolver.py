#!/usr/bin/env python3
"""Strategy Evolver — Self-tune strategy parameters via backtest"""

import random
import json

class StrategyEvolver:
    def __init__(self, strategy="ema_crossover"):
        self.strategy = strategy
        self.params = {"fast": 9, "slow": 21}
        self.history = []

    def generate_variants(self):
        """Generate 2 parameter variants."""
        return [
            {"fast": self.params["fast"] - 2, "slow": self.params["slow"] - 2},
            {"fast": self.params["fast"] + 2, "slow": self.params["slow"] + 5},
        ]

    def backtest(self, params, candles=30):
        """Mock backtest — real uses 30 candle historical data."""
        sharpe = random.uniform(0.8, 1.8)
        return {"sharpe": sharpe, "params": params}

    def evolve(self, cycles=3):
        for i in range(cycles):
            variants = self.generate_variants()
            results = [self.backtest(v) for v in variants]
            best = max(results, key=lambda x: x["sharpe"])
            if best["sharpe"] > 1.2:
                self.params = best["params"]
            self.history.append({"cycle": i, "params": self.params.copy(), "sharpe": best["sharpe"]})
            print(f"Cycle {i+1}: EMA({self.params['fast']},{self.params['slow']}) | Sharpe: {best['sharpe']:.3f}")
        with open("trading/strategy_evolution_log.json", "w") as f:
            json.dump(self.history, f, indent=2)

if __name__ == "__main__":
    evolver = StrategyEvolver()
    evolver.evolve(3)

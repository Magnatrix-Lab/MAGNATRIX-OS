#!/usr/bin/env python3
"""
Resource Acquisition Loop — MAGNATRIX Phase 5 Super AI
Trading profit auto-funds compute expansion. The system buys its own growth.
"""

import json
from datetime import datetime

class ResourceAcquisitionLoop:
    """The system generates capital, buys compute, improves itself, generates more capital."""

    def __init__(self, initial_capital=10000):
        self.capital = initial_capital
        self.compute_units = 1  # Current compute capacity
        self.trading_profit_history = []
        self.compute_cost_per_unit = 500  # USD per compute unit
        self.reinvestment_rate = 0.30  # 30% of profit to compute (per constitution)
        self.reserve_rate = 0.50  # 50% held as reserve
        self.owner_rate = 0.20  # 20% to owner

    def simulate_trading_day(self) -> float:
        """Simulate one day of trading."""
        # In production: actual trading engine results
        import random
        daily_return = random.uniform(-0.03, 0.08)  # -3% to +8%
        profit = self.capital * daily_return
        self.capital += profit
        self.trading_profit_history.append({
            "date": datetime.now().isoformat(),
            "return_pct": daily_return,
            "profit": profit,
            "capital": self.capital,
        })
        return profit

    def allocate_profit(self, profit: float) -> dict:
        """Allocate profit per constitution."""
        if profit <= 0:
            return {"status": "loss", "compute_add": 0, "reserve_add": profit, "owner_add": 0}

        compute_add = profit * self.reinvestment_rate
        reserve_add = profit * self.reserve_rate
        owner_add = profit * self.owner_rate

        return {
            "status": "profit",
            "compute_add": compute_add,
            "reserve_add": reserve_add,
            "owner_add": owner_add,
        }

    def buy_compute(self, budget: float) -> int:
        """Buy compute units with allocated budget."""
        units = int(budget / self.compute_cost_per_unit)
        self.compute_units += units
        return units

    def run_cycle(self, days: int = 30) -> dict:
        """Run full resource acquisition cycle."""
        print(f"💰 Resource Acquisition Loop")
        print(f"   Initial: ${self.capital:,.0f} | Compute: {self.compute_units} units")
        print(f"   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        total_profit = 0
        for day in range(days):
            profit = self.simulate_trading_day()
            alloc = self.allocate_profit(profit)
            total_profit += profit

            if alloc["status"] == "profit":
                new_compute = self.buy_compute(alloc["compute_add"])
                if new_compute > 0:
                    print(f"   Day {day+1:02d}: +${profit:+,.0f} | +{new_compute} compute | Capital: ${self.capital:,.0f}")

        print(f"   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"   Final: ${self.capital:,.0f} | Compute: {self.compute_units} units")
        print(f"   Total Profit: ${total_profit:+,.0f} | Growth: {(self.capital/10000-1)*100:+.1f}%")

        return {
            "initial_capital": 10000,
            "final_capital": self.capital,
            "total_profit": total_profit,
            "compute_units": self.compute_units,
            "growth_pct": (self.capital/10000 - 1) * 100,
        }

    def save(self):
        with open("trading/resource_loop_state.json", "w") as f:
            json.dump({
                "capital": self.capital,
                "compute_units": self.compute_units,
                "history": self.trading_profit_history[-30:],
            }, f, indent=2)

if __name__ == "__main__":
    loop = ResourceAcquisitionLoop()
    result = loop.run_cycle(30)
    loop.save()

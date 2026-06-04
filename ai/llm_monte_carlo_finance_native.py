"""Monte Carlo Finance - Monte Carlo simulation for financial modeling for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import math
import random

@dataclass
class MonteCarloFinance:
    simulations: int = 10000
    
    def simulate_stock_price(self, S0: float, mu: float, sigma: float, T: float, dt: float) -> List[float]:
        steps = int(T / dt)
        prices = [S0]
        for _ in range(steps):
            dW = random.gauss(0, math.sqrt(dt))
            dS = prices[-1] * (mu * dt + sigma * dW)
            prices.append(prices[-1] + dS)
        return prices
    
    def price_option(self, S0: float, K: float, T: float, r: float, sigma: float, option_type: str = "call") -> float:
        payoffs = []
        for _ in range(self.simulations):
            path = self.simulate_stock_price(S0, r, sigma, T, T/252)
            ST = path[-1]
            if option_type == "call":
                payoff = max(0, ST - K)
            else:
                payoff = max(0, K - ST)
            payoffs.append(payoff)
        return math.exp(-r * T) * sum(payoffs) / len(payoffs)
    
    def stats(self, S0: float, K: float, T: float, r: float, sigma: float) -> dict:
        call_price = self.price_option(S0, K, T, r, sigma, "call")
        put_price = self.price_option(S0, K, T, r, sigma, "put")
        return {
            "call_price": round(call_price, 4),
            "put_price": round(put_price, 4),
            "simulations": self.simulations
        }

def run():
    mcf = MonteCarloFinance(1000)
    S0, K, T, r, sigma = 100.0, 100.0, 1.0, 0.05, 0.2
    print("Call price:", round(mcf.price_option(S0, K, T, r, sigma, "call"), 4))
    print("Put price:", round(mcf.price_option(S0, K, T, r, sigma, "put"), 4))
    print("Stats:", mcf.stats(S0, K, T, r, sigma))

if __name__ == "__main__": run()

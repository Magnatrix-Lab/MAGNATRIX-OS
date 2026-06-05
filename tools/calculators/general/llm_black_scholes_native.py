"""Black-Scholes Option Pricing — European call/put, greeks, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math

@dataclass
class OptionParams:
    S: float  # Spot price
    K: float  # Strike price
    T: float  # Time to maturity (years)
    r: float  # Risk-free rate
    sigma: float  # Volatility
    q: float = 0.0  # Dividend yield

@dataclass
class Greeks:
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float

class BlackScholesModel:
    def __init__(self):
        self._cache: Dict[str, float] = {}

    def _d1(self, p: OptionParams) -> float:
        return (math.log(p.S / p.K) + (p.r - p.q + 0.5 * p.sigma**2) * p.T) / (p.sigma * math.sqrt(p.T))

    def _d2(self, p: OptionParams) -> float:
        return self._d1(p) - p.sigma * math.sqrt(p.T)

    def _nd(self, x: float) -> float:
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))

    def _npd(self, x: float) -> float:
        return math.exp(-x**2 / 2) / math.sqrt(2 * math.pi)

    def call_price(self, p: OptionParams) -> float:
        d1 = self._d1(p)
        d2 = self._d2(p)
        return p.S * math.exp(-p.q * p.T) * self._nd(d1) - p.K * math.exp(-p.r * p.T) * self._nd(d2)

    def put_price(self, p: OptionParams) -> float:
        d1 = self._d1(p)
        d2 = self._d2(p)
        return p.K * math.exp(-p.r * p.T) * self._nd(-d2) - p.S * math.exp(-p.q * p.T) * self._nd(-d1)

    def greeks(self, p: OptionParams, is_call: bool = True) -> Greeks:
        d1 = self._d1(p)
        d2 = self._d2(p)
        nd1 = self._nd(d1)
        nd2 = self._nd(d2)
        npd1 = self._npd(d1)
        delta = math.exp(-p.q * p.T) * (nd1 if is_call else nd1 - 1)
        gamma = math.exp(-p.q * p.T) * npd1 / (p.S * p.sigma * math.sqrt(p.T))
        theta = -p.S * npd1 * p.sigma / (2 * math.sqrt(p.T)) - p.r * p.K * math.exp(-p.r * p.T) * (nd2 if is_call else -nd2) + p.q * p.S * math.exp(-p.q * p.T) * (nd1 if is_call else -nd1)
        theta = theta / 365
        vega = p.S * math.exp(-p.q * p.T) * npd1 * math.sqrt(p.T) / 100
        rho = p.K * p.T * math.exp(-p.r * p.T) * (nd2 if is_call else -nd2) / 100
        return Greeks(delta, gamma, theta, vega, rho)

    def stats(self) -> Dict:
        return {"model": "Black-Scholes", "supports": ["call", "put", "greeks"]}

def run():
    bs = BlackScholesModel()
    p = OptionParams(100, 105, 1, 0.05, 0.2, 0.0)
    print("Call:", bs.call_price(p))
    print("Put:", bs.put_price(p))
    print("Greeks:", bs.greeks(p, True))
    print(bs.stats())

if __name__ == "__main__":
    run()

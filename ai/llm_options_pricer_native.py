"""Options Pricer - Black-Scholes option pricing for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import math

class OptionType(Enum):
    CALL = auto(); PUT = auto()

@dataclass
class OptionsPricer:
    
    def _normal_cdf(self, x: float) -> float:
        # Approximation of normal CDF
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))
    
    def black_scholes(self, S: float, K: float, T: float, r: float, sigma: float, option_type: OptionType) -> float:
        if T <= 0 or sigma <= 0: return max(0, S - K) if option_type == OptionType.CALL else max(0, K - S)
        d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
        d2 = d1 - sigma * math.sqrt(T)
        if option_type == OptionType.CALL:
            return S * self._normal_cdf(d1) - K * math.exp(-r * T) * self._normal_cdf(d2)
        else:
            return K * math.exp(-r * T) * self._normal_cdf(-d2) - S * self._normal_cdf(-d1)
    
    def stats(self, S: float, K: float, T: float, r: float, sigma: float) -> dict:
        call = self.black_scholes(S, K, T, r, sigma, OptionType.CALL)
        put = self.black_scholes(S, K, T, r, sigma, OptionType.PUT)
        return {"call": round(call, 4), "put": round(put, 4), "spot": S, "strike": K}

def run():
    op = OptionsPricer()
    S, K, T, r, sigma = 100.0, 100.0, 1.0, 0.05, 0.2
    print("Call:", round(op.black_scholes(S, K, T, r, sigma, OptionType.CALL), 4))
    print("Put:", round(op.black_scholes(S, K, T, r, sigma, OptionType.PUT), 4))
    print("Stats:", op.stats(S, K, T, r, sigma))

if __name__ == "__main__": run()

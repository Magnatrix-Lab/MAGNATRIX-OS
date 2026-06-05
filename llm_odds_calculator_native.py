"""Native stdlib module: Odds Calculator
Converts between decimal, fractional, and American odds; calculates implied probability.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class OddsFormat(Enum):
    DECIMAL = "decimal"
    FRACTIONAL = "fractional"
    AMERICAN = "american"

@dataclass
class OddsCalculator:
    odds_format: OddsFormat
    odds_value: float

    def to_decimal(self) -> float:
        if self.odds_format == OddsFormat.DECIMAL:
            return self.odds_value
        elif self.odds_format == OddsFormat.FRACTIONAL:
            return self.odds_value + 1
        else:
            if self.odds_value > 0:
                return (self.odds_value / 100) + 1
            else:
                return (100 / abs(self.odds_value)) + 1

    def to_fractional(self) -> str:
        dec = self.to_decimal()
        if dec == 1:
            return "0/1"
        from math import gcd
        num = int(round((dec - 1) * 100))
        den = 100
        d = gcd(num, den)
        return f"{num//d}/{den//d}"

    def to_american(self) -> int:
        dec = self.to_decimal()
        if dec >= 2:
            return int((dec - 1) * 100)
        else:
            return int(-100 / (dec - 1))

    def implied_probability_pct(self) -> float:
        dec = self.to_decimal()
        if dec == 0:
            return 0.0
        return (1 / dec) * 100

    def payout(self, stake: float) -> float:
        return stake * self.to_decimal()

    def profit(self, stake: float) -> float:
        return self.payout(stake) - stake

    def stats(self, stake: float = 100) -> Dict:
        return {
            "decimal": round(self.to_decimal(), 2),
            "fractional": self.to_fractional(),
            "american": self.to_american(),
            "implied_probability_pct": round(self.implied_probability_pct(), 1),
            "payout": round(self.payout(stake), 2),
            "profit": round(self.profit(stake), 2),
        }

def run():
    oc = OddsCalculator(odds_format=OddsFormat.DECIMAL, odds_value=2.5)
    print(oc.stats(stake=100))

if __name__ == "__main__":
    run()

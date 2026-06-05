"""Native stdlib module: Exchange Rate Calculator
Converts currencies, calculates cross rates, and purchasing power parity.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class ExchangeRateCalculator:
    base_currency: str
    target_currency: str
    rate: float
    amount: float
    ppp_rate: float = 0.0

    def convert(self) -> float:
        return self.amount * self.rate

    def inverse_rate(self) -> float:
        if self.rate == 0:
            return 0.0
        return 1 / self.rate

    def cross_rate(self, third_currency_rate: float) -> float:
        if third_currency_rate == 0:
            return 0.0
        return self.rate / third_currency_rate

    def ppp_overvaluation_pct(self) -> float:
        if self.ppp_rate == 0 or self.rate == 0:
            return 0.0
        return ((self.rate - self.ppp_rate) / self.ppp_rate) * 100

    def real_exchange_rate(self, domestic_price_index: float, foreign_price_index: float) -> float:
        if foreign_price_index == 0:
            return 0.0
        return self.rate * (domestic_price_index / foreign_price_index)

    def spread_pct(self, bid_rate: float, ask_rate: float) -> float:
        if ask_rate == 0:
            return 0.0
        return ((ask_rate - bid_rate) / ask_rate) * 100

    def stats(self) -> Dict:
        return {
            "base_currency": self.base_currency,
            "target_currency": self.target_currency,
            "rate": self.rate,
            "amount": self.amount,
            "converted": round(self.convert(), 2),
            "inverse_rate": round(self.inverse_rate(), 6),
            "ppp_overvaluation_pct": round(self.ppp_overvaluation_pct(), 2) if self.ppp_rate else None,
        }

def run():
    erc = ExchangeRateCalculator(base_currency="USD", target_currency="EUR", rate=0.85, amount=1000, ppp_rate=0.80)
    print(erc.stats())

if __name__ == "__main__":
    run()

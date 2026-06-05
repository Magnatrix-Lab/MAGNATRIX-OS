"""Native stdlib module: Purchasing Power Parity Calculator
Compares cost of living and real incomes across countries using PPP.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class PurchasingPowerParityCalculator:
    country_a: str
    country_b: str
    nominal_income_a: float
    nominal_income_b: float
    price_level_a: float
    price_level_b: float
    exchange_rate_a_to_b: float

    def ppp_income_a_in_b(self) -> float:
        if self.price_level_a == 0:
            return 0.0
        return self.nominal_income_a * (self.price_level_b / self.price_level_a)

    def ppp_income_b_in_a(self) -> float:
        if self.price_level_b == 0:
            return 0.0
        return self.nominal_income_b * (self.price_level_a / self.price_level_b)

    def real_income_a(self) -> float:
        if self.price_level_a == 0:
            return 0.0
        return self.nominal_income_a / self.price_level_a

    def real_income_b(self) -> float:
        if self.price_level_b == 0:
            return 0.0
        return self.nominal_income_b / self.price_level_b

    def income_comparison_pct(self) -> float:
        if self.real_income_b() == 0:
            return 0.0
        return ((self.real_income_a() - self.real_income_b()) / self.real_income_b()) * 100

    def ppp_exchange_rate(self) -> float:
        if self.price_level_b == 0:
            return 0.0
        return self.price_level_a / self.price_level_b

    def exchange_rate_misalignment_pct(self) -> float:
        if self.ppp_exchange_rate() == 0:
            return 0.0
        return ((self.exchange_rate_a_to_b - self.ppp_exchange_rate()) / self.ppp_exchange_rate()) * 100

    def stats(self) -> Dict:
        return {
            "country_a": self.country_a,
            "country_b": self.country_b,
            "real_income_a": round(self.real_income_a(), 2),
            "real_income_b": round(self.real_income_b(), 2),
            "income_comparison_pct": round(self.income_comparison_pct(), 2),
            "ppp_exchange_rate": round(self.ppp_exchange_rate(), 4),
            "misalignment_pct": round(self.exchange_rate_misalignment_pct(), 2),
        }

def run():
    ppp = PurchasingPowerParityCalculator(country_a="USA", country_b="Germany", nominal_income_a=60000, nominal_income_b=50000, price_level_a=100, price_level_b=95, exchange_rate_a_to_b=0.85)
    print(ppp.stats())

if __name__ == "__main__":
    run()

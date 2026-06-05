"""Native stdlib module: GDP Calculator
Calculates GDP, growth rates, and per capita metrics.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class GDPCalculator:
    consumption: float
    investment: float
    government_spending: float
    exports: float
    imports: float
    population: int
    previous_year_gdp: float = 0

    def gdp(self) -> float:
        return self.consumption + self.investment + self.government_spending + (self.exports - self.imports)

    def gdp_per_capita(self) -> float:
        if self.population == 0:
            return 0.0
        return self.gdp() / self.population

    def growth_rate_pct(self) -> float:
        if self.previous_year_gdp == 0:
            return 0.0
        return ((self.gdp() - self.previous_year_gdp) / self.previous_year_gdp) * 100

    def trade_balance(self) -> float:
        return self.exports - self.imports

    def trade_balance_pct(self) -> float:
        if self.gdp() == 0:
            return 0.0
        return (self.trade_balance() / self.gdp()) * 100

    def government_spending_pct(self) -> float:
        if self.gdp() == 0:
            return 0.0
        return (self.government_spending / self.gdp()) * 100

    def investment_pct(self) -> float:
        if self.gdp() == 0:
            return 0.0
        return (self.investment / self.gdp()) * 100

    def stats(self) -> Dict:
        return {
            "gdp": round(self.gdp(), 2),
            "gdp_per_capita": round(self.gdp_per_capita(), 2),
            "growth_rate_pct": round(self.growth_rate_pct(), 2),
            "trade_balance": round(self.trade_balance(), 2),
            "trade_balance_pct": round(self.trade_balance_pct(), 2),
            "gov_spending_pct": round(self.government_spending_pct(), 2),
            "investment_pct": round(self.investment_pct(), 2),
        }

def run():
    gdp = GDPCalculator(consumption=12000, investment=3000, government_spending=4000, exports=2500, imports=3000, population=330000000, previous_year_gdp=18000)
    print(gdp.stats())

if __name__ == "__main__":
    run()

"""Native stdlib module: Locale Cost Estimator
Estimates translation costs by locale, word count, and complexity.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class LocaleRate:
    locale_code: str
    language_name: str
    rate_per_word: float
    complexity_multiplier: float = 1.0

@dataclass
class LocaleCostEstimator:
    project_name: str
    word_count: int
    locales: List[LocaleRate] = field(default_factory=list)

    def cost_per_locale(self) -> Dict[str, float]:
        costs = {}
        for locale in self.locales:
            costs[locale.locale_code] = self.word_count * locale.rate_per_word * locale.complexity_multiplier
        return costs

    def total_cost(self) -> float:
        return sum(self.cost_per_locale().values())

    def most_expensive_locale(self) -> str:
        if not self.locales:
            return ""
        costs = self.cost_per_locale()
        return max(costs, key=costs.get)

    def stats(self) -> Dict:
        return {
            "project": self.project_name,
            "word_count": self.word_count,
            "locales_count": len(self.locales),
            "cost_per_locale": {k: round(v, 2) for k, v in self.cost_per_locale().items()},
            "total_cost": round(self.total_cost(), 2),
            "most_expensive": self.most_expensive_locale(),
        }

def run():
    lce = LocaleCostEstimator(
        project_name="Mobile App Strings",
        word_count=12000,
        locales=[
            LocaleRate("de", "German", 0.18, 1.1),
            LocaleRate("fr", "French", 0.16, 1.0),
            LocaleRate("ja", "Japanese", 0.22, 1.3),
            LocaleRate("es", "Spanish", 0.14, 1.0),
            LocaleRate("zh", "Chinese", 0.15, 1.2),
        ]
    )
    print(lce.stats())

if __name__ == "__main__":
    run()

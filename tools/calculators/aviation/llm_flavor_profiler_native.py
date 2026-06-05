"""Native stdlib module: Flavor Profiler
Maps flavor profiles of ingredients using intensity scores across taste dimensions.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class FlavorDimension:
    name: str
    score: float

@dataclass
class FlavorProfiler:
    ingredient_name: str
    dimensions: List[FlavorDimension] = field(default_factory=list)

    def total_intensity(self) -> float:
        return sum(d.score for d in self.dimensions)

    def dominant_flavor(self) -> str:
        if not self.dimensions:
            return "none"
        return max(self.dimensions, key=lambda d: d.score).name

    def balance_score(self) -> float:
        if len(self.dimensions) < 2:
            return 0.0
        avg = self.total_intensity() / len(self.dimensions)
        variance = sum((d.score - avg) ** 2 for d in self.dimensions) / len(self.dimensions)
        return max(0, 10 - variance ** 0.5)

    def stats(self) -> Dict:
        return {
            "total_intensity": round(self.total_intensity(), 1),
            "dominant": self.dominant_flavor(),
            "balance_score": round(self.balance_score(), 2),
            "dimensions": len(self.dimensions),
        }

def run():
    fp = FlavorProfiler(
        ingredient_name="Star Anise",
        dimensions=[
            FlavorDimension("sweet", 2.5),
            FlavorDimension("bitter", 1.0),
            FlavorDimension("warm", 9.0),
            FlavorDimension("floral", 6.0),
            FlavorDimension("anise", 10.0),
        ]
    )
    print(fp.stats())

if __name__ == "__main__":
    run()

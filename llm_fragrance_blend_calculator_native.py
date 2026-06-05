"""Native stdlib module: Fragrance Blend Calculator
Balances top, middle, and base notes with evaporation rates.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional

@dataclass
class FragranceNote:
    name: str
    type: str  # top, middle, base
    drops: int
    evaporation_hours: float

@dataclass
class FragranceBlendCalculator:
    notes: List[FragranceNote]

    def total_drops(self) -> int:
        return sum(n.drops for n in self.notes)

    def note_ratios(self) -> Dict[str, float]:
        total = self.total_drops()
        if total == 0:
            return {}
        return {n.name: (n.drops / total) * 100 for n in self.notes}

    def type_distribution(self) -> Dict[str, float]:
        total = self.total_drops()
        if total == 0:
            return {}
        dist = {}
        for n in self.notes:
            dist[n.type] = dist.get(n.type, 0) + n.drops
        return {k: (v / total) * 100 for k, v in dist.items()}

    def weighted_evaporation_hours(self) -> float:
        total = self.total_drops()
        if total == 0:
            return 0
        return sum(n.drops * n.evaporation_hours for n in self.notes) / total

    def blend_balance_score(self) -> float:
        ideal = {"top": 30, "middle": 50, "base": 20}
        dist = self.type_distribution()
        score = 0
        for t, ideal_pct in ideal.items():
            actual = dist.get(t, 0)
            score += max(0, 100 - abs(actual - ideal_pct) * 5)
        return score / 3

    def longevity_estimate(self) -> str:
        hours = self.weighted_evaporation_hours()
        if hours < 2:
            return "short (< 2h)"
        elif hours < 6:
            return "moderate (2-6h)"
        elif hours < 12:
            return "long (6-12h)"
        return "very_long (> 12h)"

    def stats(self) -> Dict:
        return {
            "total_drops": self.total_drops(),
            "note_ratios": {k: round(v, 1) for k, v in self.note_ratios().items()},
            "type_distribution": {k: round(v, 1) for k, v in self.type_distribution().items()},
            "weighted_evaporation_hours": round(self.weighted_evaporation_hours(), 1),
            "blend_balance_score": round(self.blend_balance_score(), 1),
            "longevity_estimate": self.longevity_estimate(),
        }

def run():
    notes = [
        FragranceNote("bergamot", "top", 10, 2),
        FragranceNote("lavender", "middle", 15, 4),
        FragranceNote("sandalwood", "base", 5, 24),
    ]
    fbc = FragranceBlendCalculator(notes=notes)
    print(fbc.stats())

if __name__ == "__main__":
    run()

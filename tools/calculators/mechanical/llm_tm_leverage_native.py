"""Native stdlib module: TM Leverage Calculator
Calculates translation memory leverage percentages and cost savings.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class MatchType(Enum):
    EXACT = "exact"
    FUZZY_95 = "fuzzy_95"
    FUZZY_85 = "fuzzy_85"
    FUZZY_75 = "fuzzy_75"
    NEW = "new"

@dataclass
class SegmentMatch:
    match_type: MatchType
    word_count: int
    discount_pct: float

@dataclass
class TMLeverageCalculator:
    project_name: str
    total_words: int
    segments: List[SegmentMatch] = field(default_factory=list)
    base_rate_per_word: float = 0.15

    def words_by_match(self) -> Dict[str, int]:
        counts = {}
        for seg in self.segments:
            counts[seg.match_type.value] = counts.get(seg.match_type.value, 0) + seg.word_count
        return counts

    def weighted_cost(self) -> float:
        total = 0.0
        for seg in self.segments:
            rate = self.base_rate_per_word * (1 - seg.discount_pct / 100)
            total += seg.word_count * rate
        return total

    def full_cost_no_tm(self) -> float:
        return self.total_words * self.base_rate_per_word

    def savings(self) -> float:
        return self.full_cost_no_tm() - self.weighted_cost()

    def savings_pct(self) -> float:
        if self.full_cost_no_tm() == 0:
            return 0.0
        return (self.savings() / self.full_cost_no_tm()) * 100

    def stats(self) -> Dict:
        return {
            "project": self.project_name,
            "total_words": self.total_words,
            "words_by_match": self.words_by_match(),
            "weighted_cost": round(self.weighted_cost(), 2),
            "full_cost": round(self.full_cost_no_tm(), 2),
            "savings": round(self.savings(), 2),
            "savings_pct": round(self.savings_pct(), 1),
        }

def run():
    tm = TMLeverageCalculator(
        project_name="User Manual v2",
        total_words=50000,
        segments=[
            SegmentMatch(MatchType.EXACT, 15000, 100),
            SegmentMatch(MatchType.FUZZY_95, 8000, 75),
            SegmentMatch(MatchType.FUZZY_85, 5000, 50),
            SegmentMatch(MatchType.FUZZY_75, 3000, 25),
            SegmentMatch(MatchType.NEW, 19000, 0),
        ]
    )
    print(tm.stats())

if __name__ == "__main__":
    run()

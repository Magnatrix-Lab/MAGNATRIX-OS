"""Brand Analyzer — consistency, sentiment, positioning, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class BrandAnalyzer:
    brand_values: List[str] = field(default_factory=list)
    touchpoints: List[Dict] = field(default_factory=list)

    def value_coverage(self) -> float:
        if not self.touchpoints:
            return 0.0
        mentions = sum(1 for t in self.touchpoints if any(v in t.get("text", "") for v in self.brand_values))
        return mentions / len(self.touchpoints)

    def sentiment_score(self) -> float:
        if not self.touchpoints:
            return 0.0
        return sum(t.get("sentiment", 0) for t in self.touchpoints) / len(self.touchpoints)

    def consistency(self) -> float:
        if len(self.touchpoints) < 2:
            return 1.0
        return 1.0 - (sum(1 for t in self.touchpoints if t.get("on_brand", False)) / len(self.touchpoints))

    def stats(self) -> Dict:
        return {"coverage": round(self.value_coverage(), 3), "sentiment": round(self.sentiment_score(), 3), "consistency": round(self.consistency(), 3)}

def run():
    ba = BrandAnalyzer(brand_values=["innovation", "trust"], touchpoints=[{"text": "innovation", "sentiment": 0.8, "on_brand": True}])
    print(ba.stats())

if __name__ == "__main__":
    run()

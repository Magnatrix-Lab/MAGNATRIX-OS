"""Source Ranker — authority, recency, bias, citation count, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime

@dataclass
class Source:
    name: str
    domain: str
    published: str
    citations: int = 0
    bias_score: float = 0.0
    authority: float = 0.5

class SourceRanker:
    def __init__(self):
        self.sources: List[Source] = []

    def add_source(self, s: Source):
        self.sources.append(s)

    def recency_score(self, s: Source) -> float:
        try:
            pub = datetime.strptime(s.published, "%Y-%m-%d")
            days_old = (datetime.now() - pub).days
            return max(0, 1 - days_old / 365)
        except:
            return 0.5

    def rank(self) -> List[Tuple[str, float]]:
        scored = []
        for s in self.sources:
            score = s.authority * 0.4 + self.recency_score(s) * 0.2 + min(1, s.citations / 100) * 0.2 + (1 - s.bias_score) * 0.2
            scored.append((s.name, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored

    def bias_filter(self, max_bias: float = 0.3) -> List[Source]:
        return [s for s in self.sources if s.bias_score <= max_bias]

    def stats(self) -> Dict:
        return {"sources": len(self.sources), "avg_authority": sum(s.authority for s in self.sources) / len(self.sources) if self.sources else 0}

def run():
    sr = SourceRanker()
    sr.add_source(Source("Reuters", "reuters.com", "2024-06-01", 500, 0.1, 0.9))
    sr.add_source(Source("BlogX", "blogx.com", "2023-01-01", 5, 0.6, 0.3))
    print(sr.rank())
    print(sr.stats())

if __name__ == "__main__":
    run()

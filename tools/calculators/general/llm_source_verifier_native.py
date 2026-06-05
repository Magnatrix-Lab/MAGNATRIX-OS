"""Native stdlib module: Source Verifier
Tracks source credibility, verification status, and citation counts.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class SourceType(Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    EXPERT = "expert"
    OFFICIAL = "official"
    ANONYMOUS = "anonymous"

@dataclass
class Source:
    name: str
    source_type: SourceType
    verified: bool
    credibility_score: float
    used_in_stories: int = 0

@dataclass
class SourceVerifier:
    organization: str
    sources: List[Source] = field(default_factory=list)

    def verified_count(self) -> int:
        return sum(1 for s in self.sources if s.verified)

    def avg_credibility(self) -> float:
        if not self.sources:
            return 0.0
        return sum(s.credibility_score for s in self.sources) / len(self.sources)

    def by_type(self) -> Dict[str, int]:
        counts = {}
        for s in self.sources:
            counts[s.source_type.value] = counts.get(s.source_type.value, 0) + 1
        return counts

    def high_credibility(self) -> List[Source]:
        return [s for s in self.sources if s.credibility_score >= 4.0]

    def stats(self) -> Dict:
        return {
            "organization": self.organization,
            "total_sources": len(self.sources),
            "verified": self.verified_count(),
            "avg_credibility": round(self.avg_credibility(), 2),
            "by_type": self.by_type(),
            "high_credibility_count": len(self.high_credibility()),
        }

def run():
    sv = SourceVerifier(
        organization="News Desk",
        sources=[
            Source("Mayor Smith", SourceType.OFFICIAL, True, 4.5, 12),
            Source("Dr. Jones", SourceType.EXPERT, True, 4.8, 8),
            Source("Anonymous Tip", SourceType.ANONYMOUS, False, 2.0, 3),
            Source("Police Report", SourceType.PRIMARY, True, 4.2, 15),
            Source("Blog Post", SourceType.SECONDARY, False, 1.5, 1),
        ]
    )
    print(sv.stats())

if __name__ == "__main__":
    run()

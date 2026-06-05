"""Native stdlib module: Hashtag Analyzer
Analyzes hashtag performance, reach, and trending potential.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class HashtagData:
    tag: str
    posts_count: int
    reach: int
    engagement: int
    growth_rate_pct: float

@dataclass
class HashtagAnalyzer:
    niche: str
    hashtags: List[HashtagData] = field(default_factory=list)

    def avg_engagement_rate(self) -> float:
        if not self.hashtags:
            return 0.0
        total_reach = sum(h.reach for h in self.hashtags)
        if total_reach == 0:
            return 0.0
        return (sum(h.engagement for h in self.hashtags) / total_reach) * 100

    def trending_tags(self, min_growth_pct: float = 10) -> List[str]:
        return [h.tag for h in self.hashtags if h.growth_rate_pct >= min_growth_pct]

    def oversaturated_tags(self, threshold_posts: int = 1000000) -> List[str]:
        return [h.tag for h in self.hashtags if h.posts_count > threshold_posts]

    def recommended_tags(self, max_posts: int = 500000, min_growth_pct: float = 5) -> List[str]:
        return [h.tag for h in self.hashtags if h.posts_count <= max_posts and h.growth_rate_pct >= min_growth_pct]

    def stats(self) -> Dict:
        return {
            "niche": self.niche,
            "hashtags": len(self.hashtags),
            "avg_engagement_rate_pct": round(self.avg_engagement_rate(), 2),
            "trending": self.trending_tags(),
            "oversaturated": self.oversaturated_tags(),
            "recommended": self.recommended_tags(),
        }

def run():
    ha = HashtagAnalyzer(
        niche="Fitness",
        hashtags=[
            HashtagData("fitness", 50000000, 1000000, 50000, 2),
            HashtagData("homeworkout", 5000000, 200000, 25000, 15),
            HashtagData("yoga", 30000000, 800000, 40000, 5),
            HashtagData("hiit", 2000000, 150000, 20000, 20),
        ]
    )
    print(ha.stats())

if __name__ == "__main__":
    run()

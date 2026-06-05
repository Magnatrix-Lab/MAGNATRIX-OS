"""Native stdlib module: Engagement Rate Calculator
Calculates social media engagement rates, reach, and viral coefficients.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class PostMetrics:
    post_id: str
    impressions: int
    likes: int
    comments: int
    shares: int
    saves: int
    clicks: int

@dataclass
class EngagementRateCalculator:
    account_name: str
    posts: List[PostMetrics] = field(default_factory=list)

    def engagement_rate_pct(self, post: PostMetrics) -> float:
        if post.impressions == 0:
            return 0.0
        engagements = post.likes + post.comments + post.shares + post.saves + post.clicks
        return (engagements / post.impressions) * 100

    def avg_engagement_rate_pct(self) -> float:
        if not self.posts:
            return 0.0
        return sum(self.engagement_rate_pct(p) for p in self.posts) / len(self.posts)

    def total_reach(self) -> int:
        return sum(p.impressions for p in self.posts)

    def total_engagements(self) -> int:
        return sum(p.likes + p.comments + p.shares + p.saves + p.clicks for p in self.posts)

    def viral_coefficient(self) -> float:
        if self.total_reach() == 0:
            return 0.0
        return sum(p.shares for p in self.posts) / self.total_reach()

    def amplification_rate(self) -> float:
        if self.total_reach() == 0:
            return 0.0
        return (sum(p.shares + p.comments for p in self.posts) / self.total_reach()) * 100

    def best_post(self) -> str:
        if not self.posts:
            return ""
        return max(self.posts, key=lambda p: self.engagement_rate_pct(p)).post_id

    def stats(self) -> Dict:
        return {
            "account": self.account_name,
            "posts": len(self.posts),
            "avg_engagement_rate_pct": round(self.avg_engagement_rate_pct(), 2),
            "total_reach": self.total_reach(),
            "total_engagements": self.total_engagements(),
            "viral_coefficient": round(self.viral_coefficient(), 4),
            "amplification_rate_pct": round(self.amplification_rate(), 2),
            "best_post": self.best_post(),
        }

def run():
    erc = EngagementRateCalculator(
        account_name="BrandX",
        posts=[
            PostMetrics("p1", 10000, 500, 50, 30, 20, 100),
            PostMetrics("p2", 15000, 800, 120, 80, 40, 200),
            PostMetrics("p3", 8000, 300, 20, 10, 15, 50),
        ]
    )
    print(erc.stats())

if __name__ == "__main__":
    run()

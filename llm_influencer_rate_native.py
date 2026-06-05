"""Native stdlib module: Influencer Rate Calculator
Calculates influencer pricing by reach, engagement, and niche.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class Platform(Enum):
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    TWITTER = "twitter"

class Tier(Enum):
    NANO = 1
    MICRO = 2
    MID = 3
    MACRO = 4
    MEGA = 5

@dataclass
class InfluencerRateCalculator:
    followers: int
    avg_engagement_rate_pct: float
    platform: Platform
    niche_factor: float = 1.0

    def tier(self) -> Tier:
        if self.followers < 1000:
            return Tier.NANO
        elif self.followers < 10000:
            return Tier.MICRO
        elif self.followers < 100000:
            return Tier.MID
        elif self.followers < 1000000:
            return Tier.MACRO
        return Tier.MEGA

    def base_rate_per_1000_followers(self) -> float:
        rates = {Platform.INSTAGRAM: 10, Platform.TIKTOK: 8, Platform.YOUTUBE: 20, Platform.TWITTER: 6}
        return rates.get(self.platform, 10)

    def engagement_multiplier(self) -> float:
        if self.avg_engagement_rate_pct >= 5:
            return 2.0
        elif self.avg_engagement_rate_pct >= 3:
            return 1.5
        elif self.avg_engagement_rate_pct >= 1:
            return 1.0
        return 0.7

    def estimated_post_rate_usd(self) -> float:
        return (self.followers / 1000) * self.base_rate_per_1000_followers() * self.engagement_multiplier() * self.niche_factor

    def story_rate_usd(self) -> float:
        return self.estimated_post_rate_usd() * 0.3

    def video_rate_usd(self) -> float:
        return self.estimated_post_rate_usd() * 1.5

    def stats(self) -> Dict:
        return {
            "followers": self.followers,
            "tier": self.tier().name,
            "platform": self.platform.value,
            "engagement_rate_pct": self.avg_engagement_rate_pct,
            "post_rate_usd": round(self.estimated_post_rate_usd(), 2),
            "story_rate_usd": round(self.story_rate_usd(), 2),
            "video_rate_usd": round(self.video_rate_usd(), 2),
        }

def run():
    irc = InfluencerRateCalculator(followers=50000, avg_engagement_rate_pct=3.5, platform=Platform.INSTAGRAM, niche_factor=1.2)
    print(irc.stats())

if __name__ == "__main__":
    run()

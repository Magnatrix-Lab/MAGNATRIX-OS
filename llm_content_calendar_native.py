"""Native stdlib module: Content Calendar Planner
Plans content schedules by frequency and engagement patterns.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class ContentSlot:
    day: str
    time: str
    content_type: str
    platform: str
    expected_engagement: float

@dataclass
class ContentCalendarPlanner:
    brand_name: str
    slots: List[ContentSlot] = field(default_factory=list)
    target_posts_per_week: int = 7

    def posts_per_platform(self) -> Dict[str, int]:
        counts = {}
        for s in self.slots:
            counts[s.platform] = counts.get(s.platform, 0) + 1
        return counts

    def posts_per_day(self) -> Dict[str, int]:
        counts = {}
        for s in self.slots:
            counts[s.day] = counts.get(s.day, 0) + 1
        return counts

    def avg_expected_engagement(self) -> float:
        if not self.slots:
            return 0.0
        return sum(s.expected_engagement for s in self.slots) / len(self.slots)

    def content_type_distribution(self) -> Dict[str, int]:
        counts = {}
        for s in self.slots:
            counts[s.content_type] = counts.get(s.content_type, 0) + 1
        return counts

    def weekly_frequency(self) -> int:
        return len(self.slots)

    def frequency_gap(self) -> int:
        return self.target_posts_per_week - self.weekly_frequency()

    def stats(self) -> Dict:
        return {
            "brand": self.brand_name,
            "weekly_posts": self.weekly_frequency(),
            "target_posts": self.target_posts_per_week,
            "frequency_gap": self.frequency_gap(),
            "avg_expected_engagement": round(self.avg_expected_engagement(), 2),
            "per_platform": self.posts_per_platform(),
            "per_day": self.posts_per_day(),
            "content_types": self.content_type_distribution(),
        }

def run():
    ccp = ContentCalendarPlanner(
        brand_name="TechBrand",
        target_posts_per_week=10,
        slots=[
            ContentSlot("Mon", "09:00", "educational", "LinkedIn", 150),
            ContentSlot("Mon", "15:00", "promotional", "Instagram", 200),
            ContentSlot("Tue", "10:00", "blog", "Twitter", 100),
            ContentSlot("Wed", "12:00", "video", "TikTok", 500),
            ContentSlot("Thu", "09:00", "educational", "LinkedIn", 180),
            ContentSlot("Fri", "14:00", "promotional", "Instagram", 250),
        ]
    )
    print(ccp.stats())

if __name__ == "__main__":
    run()

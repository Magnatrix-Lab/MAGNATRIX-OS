"""Native stdlib module: Shot List Manager
Manages film shots, duration, and coverage estimates for production.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class ShotType(Enum):
    WIDE = "wide"
    MEDIUM = "medium"
    CLOSE_UP = "close_up"
    EXTREME_CLOSE_UP = "extreme_close_up"
    ESTABLISHING = "establishing"
    CUTAWAY = "cutaway"
    POV = "pov"
    AERIAL = "aerial"

@dataclass
class Shot:
    shot_number: int
    shot_type: ShotType
    description: str
    estimated_duration_sec: float
    setup_time_min: float = 0

@dataclass
class ShotListManager:
    scene_name: str
    shots: List[Shot] = field(default_factory=list)

    def total_estimated_duration_sec(self) -> float:
        return sum(s.estimated_duration_sec for s in self.shots)

    def total_setup_time_min(self) -> float:
        return sum(s.setup_time_min for s in self.shots)

    def shot_count_by_type(self) -> Dict[str, int]:
        counts = {}
        for s in self.shots:
            counts[s.shot_type.value] = counts.get(s.shot_type.value, 0) + 1
        return counts

    def avg_shot_duration_sec(self) -> float:
        if not self.shots:
            return 0.0
        return self.total_estimated_duration_sec() / len(self.shots)

    def estimated_total_time_min(self) -> float:
        return (self.total_estimated_duration_sec() / 60) + self.total_setup_time_min()

    def stats(self) -> Dict:
        return {
            "scene": self.scene_name,
            "shot_count": len(self.shots),
            "total_duration_sec": round(self.total_estimated_duration_sec(), 1),
            "total_setup_min": round(self.total_setup_time_min(), 1),
            "avg_shot_duration_sec": round(self.avg_shot_duration_sec(), 1),
            "estimated_total_time_min": round(self.estimated_total_time_min(), 1),
            "by_type": self.shot_count_by_type(),
        }

def run():
    slm = ShotListManager(
        scene_name="Opening Scene",
        shots=[
            Shot(1, ShotType.ESTABLISHING, "City skyline at dawn", 8, 15),
            Shot(2, ShotType.WIDE, "Main character walks through park", 12, 10),
            Shot(3, ShotType.MEDIUM, "Character stops at bench", 6, 5),
            Shot(4, ShotType.CLOSE_UP, "Character's expression changes", 4, 3),
            Shot(5, ShotType.CUTAWAY, "Bird flies overhead", 3, 2),
        ]
    )
    print(slm.stats())

if __name__ == "__main__":
    run()

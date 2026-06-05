"""Native stdlib module: CBT Thought Record
Analyzes cognitive distortions and generates balanced thoughts.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class DistortionType(Enum):
    ALL_OR_NOTHING = "all_or_nothing"
    CATASTROPHIZING = "catastrophizing"
    MIND_READING = "mind_reading"
    OVERGENERALIZATION = "overgeneralization"
    PERSONALIZATION = "personalization"
    DISQUALIFYING = "disqualifying_the_positive"

@dataclass
class ThoughtRecord:
    situation: str
    automatic_thought: str
    emotion: str
    emotion_intensity: float
    distortions: List[DistortionType] = field(default_factory=list)
    balanced_thought: str = ""

@dataclass
class CBTThoughtRecord:
    client_name: str
    records: List[ThoughtRecord] = field(default_factory=list)

    def avg_intensity(self) -> float:
        if not self.records:
            return 0.0
        return sum(r.emotion_intensity for r in self.records) / len(self.records)

    def distortion_counts(self) -> Dict[str, int]:
        counts = {}
        for r in self.records:
            for d in r.distortions:
                counts[d.value] = counts.get(d.value, 0) + 1
        return counts

    def most_common_distortion(self) -> str:
        counts = self.distortion_counts()
        if not counts:
            return ""
        return max(counts, key=counts.get)

    def records_with_balanced(self) -> int:
        return sum(1 for r in self.records if r.balanced_thought)

    def stats(self) -> Dict:
        return {
            "client": self.client_name,
            "records": len(self.records),
            "avg_intensity": round(self.avg_intensity(), 1),
            "distortion_counts": self.distortion_counts(),
            "most_common": self.most_common_distortion(),
            "records_with_balanced": self.records_with_balanced(),
        }

def run():
    cbt = CBTThoughtRecord(
        client_name="Alex",
        records=[
            ThoughtRecord("Presentation", "I will fail", "anxiety", 8, [DistortionType.CATASTROPHIZING], "I have prepared and can handle feedback"),
            ThoughtRecord("Meeting", "They think I am incompetent", "shame", 7, [DistortionType.MIND_READING], "I cannot know their thoughts"),
            ThoughtRecord("Deadline", "I always miss deadlines", "stress", 6, [DistortionType.OVERGENERALIZATION], "I have met many deadlines"),
        ]
    )
    print(cbt.stats())

if __name__ == "__main__":
    run()

"""Native stdlib module: Plot Structure Analyzer
Analyzes story structure by acts, beats, and arcs for narrative planning.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class ActType(Enum):
    ACT_1 = "act_1"
    ACT_2A = "act_2a"
    ACT_2B = "act_2b"
    ACT_3 = "act_3"

@dataclass
class Beat:
    name: str
    act: ActType
    word_count: int
    description: str = ""

@dataclass
class PlotStructure:
    title: str
    total_words: int
    beats: List[Beat] = field(default_factory=list)

    def words_by_act(self) -> Dict[str, int]:
        counts = {}
        for beat in self.beats:
            counts[beat.act.value] = counts.get(beat.act.value, 0) + beat.word_count
        return counts

    def act_percentages(self) -> Dict[str, float]:
        by_act = self.words_by_act()
        return {act: round((count / max(1, self.total_words)) * 100, 1) for act, count in by_act.items()}

    def beat_count(self) -> int:
        return len(self.beats)

    def target_word_counts(self) -> Dict[str, int]:
        return {
            ActType.ACT_1.value: int(self.total_words * 0.25),
            ActType.ACT_2A.value: int(self.total_words * 0.25),
            ActType.ACT_2B.value: int(self.total_words * 0.25),
            ActType.ACT_3.value: int(self.total_words * 0.25),
        }

    def stats(self) -> Dict:
        return {
            "title": self.title,
            "total_words": self.total_words,
            "beats": self.beat_count(),
            "words_by_act": self.words_by_act(),
            "act_percentages": self.act_percentages(),
            "target_distribution": self.target_word_counts(),
        }

def run():
    ps = PlotStructure(
        title="The Hero's Journey",
        total_words=80000,
        beats=[
            Beat("Ordinary World", ActType.ACT_1, 15000),
            Beat("Call to Adventure", ActType.ACT_1, 5000),
            Beat("Crossing Threshold", ActType.ACT_2A, 10000),
            Beat("Tests and Enemies", ActType.ACT_2A, 12000),
            Beat("Midpoint", ActType.ACT_2B, 8000),
            Beat("Darkest Hour", ActType.ACT_2B, 15000),
            Beat("Climax", ActType.ACT_3, 10000),
            Beat("Resolution", ActType.ACT_3, 5000),
        ]
    )
    print(ps.stats())

if __name__ == "__main__":
    run()

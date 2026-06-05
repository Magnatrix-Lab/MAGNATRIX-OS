"""Quiz Generator — MCQ, fill-in, difficulty, bloom taxonomy, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import random

@dataclass
class Question:
    text: str
    answer: str
    options: List[str] = field(default_factory=list)
    difficulty: int = 1
    bloom_level: str = "remember"

class QuizGenerator:
    def __init__(self):
        self.questions: List[Question] = []

    def add(self, q: Question):
        self.questions.append(q)

    def generate_mcq(self, topic: str, count: int = 5) -> List[Question]:
        relevant = [q for q in self.questions if topic.lower() in q.text.lower()]
        return random.sample(relevant, min(count, len(relevant)))

    def by_difficulty(self, level: int) -> List[Question]:
        return [q for q in self.questions if q.difficulty == level]

    def by_bloom(self, level: str) -> List[Question]:
        return [q for q in self.questions if q.bloom_level == level.lower()]

    def difficulty_distribution(self) -> Dict[int, int]:
        dist = {}
        for q in self.questions:
            dist[q.difficulty] = dist.get(q.difficulty, 0) + 1
        return dist

    def stats(self) -> Dict:
        return {"total": len(self.questions), "difficulty_dist": self.difficulty_distribution()}

def run():
    qg = QuizGenerator()
    qg.add(Question("What is 2+2?", "4", ["3", "4", "5"], 1, "remember"))
    qg.add(Question("Explain photosynthesis", "process", difficulty=3, bloom_level="understand"))
    print(qg.stats())
    print("By bloom:", [q.text for q in qg.by_bloom("remember")])

if __name__ == "__main__":
    run()

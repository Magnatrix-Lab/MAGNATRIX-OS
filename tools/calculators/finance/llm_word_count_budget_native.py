"""Native stdlib module: Word Count Budget
Tracks word count budgets by section for articles and reports.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class Section:
    name: str
    budget_words: int
    actual_words: int = 0

@dataclass
class WordCountBudget:
    article_title: str
    total_budget: int
    sections: List[Section] = field(default_factory=list)

    def total_actual(self) -> int:
        return sum(s.actual_words for s in self.sections)

    def remaining_budget(self) -> int:
        return self.total_budget - self.total_actual()

    def over_budget(self) -> bool:
        return self.total_actual() > self.total_budget

    def by_section(self) -> Dict[str, Dict]:
        return {
            s.name: {
                "budget": s.budget_words,
                "actual": s.actual_words,
                "variance": s.actual_words - s.budget_words,
            }
            for s in self.sections
        }

    def stats(self) -> Dict:
        return {
            "article": self.article_title,
            "total_budget": self.total_budget,
            "total_actual": self.total_actual(),
            "remaining": self.remaining_budget(),
            "over_budget": self.over_budget(),
            "by_section": self.by_section(),
        }

def run():
    wb = WordCountBudget(
        article_title="Climate Change Report",
        total_budget=3000,
        sections=[
            Section("Introduction", 400, 380),
            Section("Background", 600, 720),
            Section("Analysis", 1200, 1150),
            Section("Conclusion", 500, 480),
            Section("Recommendations", 300, 290),
        ]
    )
    print(wb.stats())

if __name__ == "__main__":
    run()

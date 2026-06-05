"""Native stdlib module: Deadline Tracker
Tracks editorial deadlines, word counts, and publication schedules.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from datetime import datetime

@dataclass
class Assignment:
    title: str
    due_date: str
    word_count: int
    status: str = "draft"
    assigned_to: str = ""

@dataclass
class DeadlineTracker:
    publication_name: str
    assignments: List[Assignment] = field(default_factory=list)

    def overdue(self) -> List[Assignment]:
        today = datetime.now().strftime("%Y-%m-%d")
        return [a for a in self.assignments if a.due_date < today and a.status != "published"]

    def upcoming(self, days: int = 7) -> List[Assignment]:
        today = datetime.now()
        return [a for a in self.assignments if (datetime.strptime(a.due_date, "%Y-%m-%d") - today).days <= days and a.status != "published"]

    def total_words(self) -> int:
        return sum(a.word_count for a in self.assignments)

    def words_by_status(self) -> Dict[str, int]:
        counts = {}
        for a in self.assignments:
            counts[a.status] = counts.get(a.status, 0) + a.word_count
        return counts

    def stats(self) -> Dict:
        return {
            "publication": self.publication_name,
            "total_assignments": len(self.assignments),
            "total_words": self.total_words(),
            "overdue_count": len(self.overdue()),
            "upcoming_7d": len(self.upcoming()),
            "words_by_status": self.words_by_status(),
        }

def run():
    dt = DeadlineTracker(
        publication_name="Daily Tribune",
        assignments=[
            Assignment("City Council Report", "2024-06-10", 800, "editing", "Alice"),
            Assignment("Tech Review", "2024-06-12", 1200, "draft", "Bob"),
            Assignment("Sports Roundup", "2024-06-08", 600, "published", "Carol"),
            Assignment("Opinion Piece", "2024-06-15", 900, "draft", "Dave"),
        ]
    )
    print(dt.stats())

if __name__ == "__main__":
    run()

"""Curriculum Planner — prerequisites, credit hours, schedule, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple

@dataclass
class Course:
    code: str
    name: str
    credits: int
    prerequisites: List[str] = field(default_factory=list)

class CurriculumPlanner:
    def __init__(self):
        self.courses: Dict[str, Course] = {}
        self.completed: Set[str] = set()

    def add_course(self, c: Course):
        self.courses[c.code] = c

    def can_take(self, code: str) -> bool:
        c = self.courses.get(code)
        if not c:
            return False
        return all(p in self.completed for p in c.prerequisites)

    def available(self) -> List[str]:
        return [code for code in self.courses if code not in self.completed and self.can_take(code)]

    def topological_order(self) -> List[str]:
        visited = set()
        result = []
        def visit(code):
            if code in visited:
                return
            visited.add(code)
            for p in self.courses.get(code, Course("","",0)).prerequisites:
                visit(p)
            result.append(code)
        for code in self.courses:
            visit(code)
        return result

    def total_credits(self, codes: List[str]) -> int:
        return sum(self.courses[c].credits for c in codes if c in self.courses)

    def stats(self) -> Dict:
        return {"courses": len(self.courses), "completed": len(self.completed), "available": len(self.available())}

def run():
    cp = CurriculumPlanner()
    cp.add_course(Course("CS101", "Intro", 3))
    cp.add_course(Course("CS201", "Data Structures", 3, ["CS101"]))
    cp.add_course(Course("CS301", "Algorithms", 3, ["CS201"]))
    cp.completed.add("CS101")
    print("Available:", cp.available())
    print("Topo:", cp.topological_order())
    print(cp.stats())

if __name__ == "__main__":
    run()

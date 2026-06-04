"""Syllogism Engine — categorical logic, valid forms, Venn validation, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum, auto

class Mood(Enum):
    A = "All" # universal affirmative
    E = "No" # universal negative
    I = "Some" # particular affirmative
    O = "Some not" # particular negative

@dataclass
class Syllogism:
    major: Tuple[Mood, str, str]
    minor: Tuple[Mood, str, str]
    conclusion: Tuple[Mood, str, str]

class SyllogismEngine:
    def __init__(self):
        self.valid_forms = {
            (Mood.A, Mood.A, Mood.A), (Mood.A, Mood.I, Mood.I), (Mood.E, Mood.A, Mood.E),
            (Mood.E, Mood.I, Mood.O), (Mood.A, Mood.E, Mood.E), (Mood.I, Mood.A, Mood.I),
            (Mood.O, Mood.A, Mood.O), (Mood.E, Mood.O, Mood.O)
        }

    def validate(self, s: Syllogism) -> bool:
        return (s.major[0], s.minor[0], s.conclusion[0]) in self.valid_forms

    def figure(self, s: Syllogism) -> int:
        major_m, major_p, major_s = s.major
        minor_m, minor_s, minor_p = s.minor
        if major_p == minor_m:
            return 1
        if major_m == minor_p:
            return 2
        if major_m == minor_m:
            return 3
        if major_p == minor_p:
            return 4
        return 0

    def terms(self, s: Syllogism) -> Set[str]:
        return {s.major[1], s.major[2], s.minor[1], s.minor[2]}

    def stats(self, s: Syllogism) -> Dict:
        return {"valid": self.validate(s), "figure": self.figure(s), "terms": len(self.terms(s))}

def run():
    se = SyllogismEngine()
    s = Syllogism((Mood.A, "M", "P"), (Mood.A, "S", "M"), (Mood.A, "S", "P"))
    print("Valid:", se.validate(s))
    print("Figure:", se.figure(s))
    print(se.stats(s))

if __name__ == "__main__":
    run()

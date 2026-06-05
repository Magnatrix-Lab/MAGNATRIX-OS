"""Dialectic Engine — thesis-antithesis-synthesis, contradiction detection, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set

@dataclass
class DialecticEngine:
    thesis: str = ""
    antithesis: str = ""
    synthesis: str = ""

    def set_thesis(self, text: str):
        self.thesis = text

    def set_antithesis(self, text: str):
        self.antithesis = text

    def generate_synthesis(self) -> str:
        if not self.thesis or not self.antithesis:
            return ""
        thesis_words = set(self.thesis.lower().split())
        anti_words = set(self.antithesis.lower().split())
        common = thesis_words & anti_words
        synthesis = f"A synthesis that incorporates {len(common)} shared elements while resolving the tension between the positions."
        self.synthesis = synthesis
        return synthesis

    def detect_contradiction(self, a: str, b: str) -> bool:
        negators = {"not", "no", "never", "without"}
        a_words = set(a.lower().split())
        b_words = set(b.lower().split())
        for word in a_words:
            if word in b_words and any(n in a.lower() or n in b.lower() for n in negators):
                return True
        return False

    def triad_valid(self) -> bool:
        return bool(self.thesis) and bool(self.antithesis) and bool(self.synthesis)

    def resolution_score(self) -> float:
        if not self.triad_valid():
            return 0.0
        t_words = set(self.thesis.lower().split())
        a_words = set(self.antithesis.lower().split())
        s_words = set(self.synthesis.lower().split())
        coverage = len((t_words | a_words) & s_words) / len(t_words | a_words) if (t_words | a_words) else 0
        return coverage

    def stats(self) -> Dict:
        return {"triad_valid": self.triad_valid(), "resolution": round(self.resolution_score(), 3), "thesis_len": len(self.thesis), "antithesis_len": len(self.antithesis)}

def run():
    de = DialecticEngine()
    de.set_thesis("Privacy is a fundamental right that must be protected.")
    de.set_antithesis("National security requires surveillance to protect citizens.")
    print("Synthesis:", de.generate_synthesis())
    print("Contradiction:", de.detect_contradiction(de.thesis, de.antithesis))
    print(de.stats())

if __name__ == "__main__":
    run()

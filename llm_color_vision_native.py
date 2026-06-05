"""Color Vision Tester — Ishihara, CVD type, severity, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class ColorVisionTester:
    correct_answers: int = 0
    total_plates: int = 17
    deutan_errors: int = 0
    protan_errors: int = 0
    tritan_errors: int = 0

    def score(self) -> float:
        return self.correct_answers / self.total_plates if self.total_plates > 0 else 0.0

    def classification(self) -> str:
        if self.score() >= 0.94: return "normal"
        if self.deutan_errors > self.protan_errors and self.deutan_errors > self.tritan_errors:
            return "deuteranomaly" if self.score() > 0.5 else "deuteranopia"
        if self.protan_errors > self.deutan_errors and self.protan_errors > self.tritan_errors:
            return "protanomaly" if self.score() > 0.5 else "protanopia"
        if self.tritan_errors > 0:
            return "tritanomaly" if self.score() > 0.5 else "tritanopia"
        return "unclassified"

    def severity(self) -> str:
        score = self.score()
        if score >= 0.8: return "mild"
        elif score >= 0.6: return "moderate"
        return "severe"

    def occupational_suitability(self, occupation: str) -> str:
        cvd = self.classification()
        restricted = {"pilot", "electrician", "police", "firefighter"}
        if cvd != "normal" and occupation.lower() in restricted:
            return "may require restriction"
        return "generally suitable"

    def stats(self) -> Dict:
        return {
            "score": round(self.score(), 2),
            "classification": self.classification(),
            "severity": self.severity()
        }

def run():
    cvt = ColorVisionTester(correct_answers=10, deutan_errors=5, protan_errors=1, tritan_errors=0)
    print(cvt.stats())
    print("Suitability pilot:", cvt.occupational_suitability("pilot"))

if __name__ == "__main__":
    run()

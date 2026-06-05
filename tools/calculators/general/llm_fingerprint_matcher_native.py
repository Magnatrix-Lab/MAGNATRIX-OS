"""Fingerprint Matcher — minutiae, ridge count, pattern classification, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class Minutia:
    x: float
    y: float
    type: str
    angle: float

@dataclass
class FingerprintMatcher:
    minutiae: List[Minutia] = field(default_factory=list)

    def add_minutia(self, m: Minutia):
        self.minutiae.append(m)

    def ridge_count(self, m1: Minutia, m2: Minutia) -> int:
        dist = math.sqrt((m1.x - m2.x)**2 + (m1.y - m2.y)**2)
        return int(dist / 0.5)

    def pattern_class(self) -> str:
        if not self.minutiae:
            return "unknown"
        types = [m.type for m in self.minutiae]
        if "loop" in types and "delta" in types:
            return "loop"
        elif "whorl" in types:
            return "whorl"
        elif "arch" in types:
            return "arch"
        return "tented_arch"

    def similarity(self, other: 'FingerprintMatcher') -> float:
        if not self.minutiae or not other.minutiae:
            return 0.0
        matches = 0
        for m1 in self.minutiae:
            for m2 in other.minutiae:
                if m1.type == m2.type and abs(m1.angle - m2.angle) < 15:
                    dist = math.sqrt((m1.x - m2.x)**2 + (m1.y - m2.y)**2)
                    if dist < 10:
                        matches += 1
        return min(1.0, matches / max(len(self.minutiae), len(other.minutiae)))

    def stats(self) -> Dict:
        return {"minutiae": len(self.minutiae), "pattern": self.pattern_class()}

def run():
    fm = FingerprintMatcher()
    fm.add_minutia(Minutia(10, 20, "loop", 45))
    fm.add_minutia(Minutia(30, 40, "delta", 90))
    print(fm.stats())

if __name__ == "__main__":
    run()

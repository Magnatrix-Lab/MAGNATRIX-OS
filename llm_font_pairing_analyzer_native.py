"""Native stdlib module: Font Pairing Analyzer
Analyzes font pairings for contrast, x-height matching, and compatibility.
"""
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class FontPairingAnalyzer:
    font_a_x_height_pct: float
    font_b_x_height_pct: float
    font_a_contrast: float  # stroke contrast ratio
    font_b_contrast: float
    font_a_weight: str = "regular"  # light, regular, bold, black
    font_b_weight: str = "regular"

    _WEIGHTS = {"light": 300, "regular": 400, "bold": 700, "black": 900}

    def x_height_match_score(self) -> float:
        diff = abs(self.font_a_x_height_pct - self.font_b_x_height_pct)
        return max(0, 100 - diff * 20)

    def contrast_difference(self) -> float:
        return abs(self.font_a_contrast - self.font_b_contrast)

    def contrast_compatibility(self) -> str:
        diff = self.contrast_difference()
        if diff < 0.5:
            return "high"
        elif diff < 1.5:
            return "moderate"
        return "low"

    def weight_hierarchy(self) -> str:
        a = self._WEIGHTS.get(self.font_a_weight, 400)
        b = self._WEIGHTS.get(self.font_b_weight, 400)
        if a > b:
            return "a_dominant"
        elif b > a:
            return "b_dominant"
        return "equal"

    def pairing_score(self) -> float:
        x_score = self.x_height_match_score()
        contrast_diff = self.contrast_difference()
        contrast_penalty = min(30, contrast_diff * 10)
        weight_bonus = 0 if self.weight_hierarchy() == "equal" else 10
        return max(0, x_score - contrast_penalty + weight_bonus)

    def recommendation(self) -> str:
        score = self.pairing_score()
        if score >= 80:
            return "excellent_pair"
        elif score >= 60:
            return "good_pair"
        elif score >= 40:
            return "fair_pair"
        return "poor_pair"

    def stats(self) -> Dict:
        return {
            "x_height_match_score": round(self.x_height_match_score(), 1),
            "contrast_difference": round(self.contrast_difference(), 2),
            "contrast_compatibility": self.contrast_compatibility(),
            "weight_hierarchy": self.weight_hierarchy(),
            "pairing_score": round(self.pairing_score(), 1),
            "recommendation": self.recommendation(),
        }

def run():
    fpa = FontPairingAnalyzer(
        font_a_x_height_pct=52, font_b_x_height_pct=50,
        font_a_contrast=0.8, font_b_contrast=0.3,
        font_a_weight="bold", font_b_weight="regular",
    )
    print(fpa.stats())

if __name__ == "__main__":
    run()

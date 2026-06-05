"""Color Temperature Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class ColorTemperature:
    color_temp_k: float
    cri: float = 80.0

    def is_warm_white(self) -> bool:
        return self.color_temp_k < 3300

    def is_neutral_white(self) -> bool:
        return 3300 <= self.color_temp_k < 5300

    def is_cool_white(self) -> bool:
        return self.color_temp_k >= 5300

    def color_description(self) -> str:
        if self.is_warm_white():
            return "warm_white"
        elif self.is_neutral_white():
            return "neutral_white"
        else:
            return "cool_white"

    def wavelength_peak_nm(self) -> float:
        if self.color_temp_k <= 0:
            return 0.0
        return round(2.898e6 / self.color_temp_k, 1)

    def is_good_for_task(self, task_type: str = "office") -> bool:
        recommendations = {"office": (4000, 5000), "retail": (3000, 4000), "hospital": (4000, 5000), "residential": (2700, 3000), "industrial": (5000, 6500)}
        min_temp, max_temp = recommendations.get(task_type, (3000, 5000))
        return min_temp <= self.color_temp_k <= max_temp

    def color_quality_scale(self) -> float:
        if self.cri >= 90:
            return 100.0
        return round(self.cri, 1)

    def stats(self) -> Dict[str, float]:
        return {"color_temp_k": self.color_temp_k, "cri": self.cri, "wavelength_peak_nm": self.wavelength_peak_nm()}

    def run(self):
        print("=" * 60)
        print("COLOR TEMPERATURE CALCULATOR")
        print("=" * 60)
        ct = ColorTemperature(color_temp_k=4000, cri=85)
        print(f"CCT: {ct.color_temp_k} K")
        print(f"Description: {ct.color_description()}")
        print(f"Peak wavelength: {ct.wavelength_peak_nm():.1f} nm")
        print(f"Good for office: {ct.is_good_for_task('office')}")
        print(f"CQS: {ct.color_quality_scale():.1f}")
        print(f"Stats: {ct.stats()}")

if __name__ == "__main__":
    ColorTemperature(0).run()

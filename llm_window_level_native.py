"""Native stdlib module: Window Level Calculator
Calculates window width, level, and contrast settings for medical imaging.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class TissueType(Enum):
    BRAIN = "brain"
    LUNG = "lung"
    BONE = "bone"
    SOFT_TISSUE = "soft_tissue"
    LIVER = "liver"
    MEDIASTINUM = "mediastinum"
    ABDOMEN = "abdomen"

@dataclass
class WindowLevelCalculator:
    tissue_type: TissueType
    custom_window_width: float = 0.0
    custom_window_level: float = 0.0

    def standard_window_width(self) -> int:
        windows = {
            TissueType.BRAIN: 80,
            TissueType.LUNG: 1500,
            TissueType.BONE: 1800,
            TissueType.SOFT_TISSUE: 400,
            TissueType.LIVER: 150,
            TissueType.MEDIASTINUM: 350,
            TissueType.ABDOMEN: 400,
        }
        return windows.get(self.tissue_type, 400)

    def standard_window_level(self) -> int:
        levels = {
            TissueType.BRAIN: 40,
            TissueType.LUNG: -600,
            TissueType.BONE: 400,
            TissueType.SOFT_TISSUE: 50,
            TissueType.LIVER: 30,
            TissueType.MEDIASTINUM: 50,
            TissueType.ABDOMEN: 50,
        }
        return levels.get(self.tissue_type, 50)

    def window_width(self) -> int:
        return int(self.custom_window_width) if self.custom_window_width else self.standard_window_width()

    def window_level(self) -> int:
        return int(self.custom_window_level) if self.custom_window_level else self.standard_window_level()

    def min_display_value(self) -> int:
        return self.window_level() - (self.window_width() // 2)

    def max_display_value(self) -> int:
        return self.window_level() + (self.window_width() // 2)

    def contrast_resolution(self) -> float:
        if self.window_width() == 0:
            return 0.0
        return 256 / self.window_width()

    def stats(self) -> Dict:
        return {
            "tissue": self.tissue_type.value,
            "window_width": self.window_width(),
            "window_level": self.window_level(),
            "min_display": self.min_display_value(),
            "max_display": self.max_display_value(),
            "contrast_resolution": round(self.contrast_resolution(), 3),
        }

def run():
    wlc = WindowLevelCalculator(tissue_type=TissueType.LUNG)
    print(wlc.stats())

if __name__ == "__main__":
    run()

"""Native stdlib module: Dynamic Range Calculator
Calculates dynamic range, LUFS, and peak levels for audio mastering.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class DynamicRangeCalculator:
    peak_db: float
    rms_db: float
    lufs_integrated: float
    true_peak_db: float = 0.0

    def dynamic_range_db(self) -> float:
        return self.peak_db - self.rms_db

    def crest_factor(self) -> float:
        if self.rms_db == 0:
            return 0.0
        return 10 ** ((self.peak_db - self.rms_db) / 20)

    def headroom_db(self) -> float:
        return 0 - self.true_peak_db

    def loudness_range_lu(self, lufs_short_term_min: float, lufs_short_term_max: float) -> float:
        return lufs_short_term_max - lufs_short_term_min

    def perceived_loudness(self) -> str:
        l = self.lufs_integrated
        if l > -9:
            return "very_loud"
        elif l > -14:
            return "loud"
        elif l > -20:
            return "moderate"
        elif l > -30:
            return "quiet"
        return "very_quiet"

    def stats(self) -> Dict:
        return {
            "peak_db": self.peak_db,
            "rms_db": self.rms_db,
            "lufs_integrated": self.lufs_integrated,
            "true_peak_db": self.true_peak_db,
            "dynamic_range_db": round(self.dynamic_range_db(), 1),
            "crest_factor": round(self.crest_factor(), 2),
            "headroom_db": round(self.headroom_db(), 1),
            "perceived_loudness": self.perceived_loudness(),
        }

def run():
    drc = DynamicRangeCalculator(peak_db=-1.5, rms_db=-14.0, lufs_integrated=-16.5, true_peak_db=-0.8)
    print(drc.stats())

if __name__ == "__main__":
    run()

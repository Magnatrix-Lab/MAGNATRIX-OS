"""Filtration Designer -- media, rate, backwash, head loss, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import math

@dataclass
class FiltrationDesigner:
    media_depth_m: float = 0.6
    media_size_mm: float = 0.5
    porosity: float = 0.4
    filtration_rate_m_hr: float = 5.0
    filter_area_m2: float = 50.0

    def head_loss_carmen_kozeny(self) -> float:
        g = 9.81
        mu = 0.001
        rho = 1000
        d = self.media_size_mm / 1000
        v = self.filtration_rate_m_hr / 3600
        k = 5 * (1 - self.porosity) ** 2 / self.porosity ** 3
        return k * mu * self.media_depth_m * v / (rho * g * d ** 2)

    def flow_rate(self) -> float:
        return self.filtration_rate_m_hr * self.filter_area_m2

    def backwash_rate(self) -> float:
        return self.filtration_rate_m_hr * 2.5

    def run_time(self, solids_loading_kg_m3: float, max_headloss_m: float = 3.0) -> float:
        hl = self.head_loss_carmen_kozeny()
        if hl >= max_headloss_m:
            return 0.0
        return (max_headloss_m - hl) / (solids_loading_kg_m3 * 0.001)

    def filter_count_needed(self, total_flow_m3_hr: float) -> int:
        return math.ceil(total_flow_m3_hr / self.flow_rate())

    def stats(self) -> Dict:
        return {"head_loss_m": round(self.head_loss_carmen_kozeny(), 3), "flow_m3_hr": round(self.flow_rate(), 1), "filters_needed_1000": self.filter_count_needed(1000)}

def run():
    fd = FiltrationDesigner()
    print(fd.stats())

if __name__ == "__main__":
    run()

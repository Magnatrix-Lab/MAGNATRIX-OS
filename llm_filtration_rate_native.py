"""Filtration Rate Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class FiltrationRate:
    filter_area_sqm: float
    flow_rate_m3_h: float
    filter_media_depth_m: float = 0.6
    media_size_mm: float = 0.5
    backwash_rate_m3_h_per_sqm: float = 30.0

    def filtration_rate_m_h(self) -> float:
        if self.filter_area_sqm <= 0:
            return 0.0
        return round(self.flow_rate_m3_h / self.filter_area_sqm, 2)

    def filtration_rate_m3_per_day_per_sqm(self) -> float:
        return round(self.filtration_rate_m_h() * 24, 2)

    def hydraulic_loading_rate_m3_per_m2_day(self) -> float:
        return self.filtration_rate_m3_per_day_per_sqm()

    def head_loss_m(self) -> float:
        rate = self.filtration_rate_m_h()
        k = 1000
        return round(rate * self.media_size_mm / k * self.filter_media_depth_m * 50, 3)

    def backwash_duration_min(self, expansion_percent: float = 30.0) -> float:
        return round(expansion_percent / 5.0, 1)

    def backwash_water_volume_m3(self) -> float:
        duration_h = self.backwash_duration_min() / 60.0
        return round(self.backwash_rate_m3_h_per_sqm * self.filter_area_sqm * duration_h, 2)

    def water_recovery_percent(self) -> float:
        daily = self.flow_rate_m3_h * 24
        backwash = self.backwash_water_volume_m3()
        if daily + backwash <= 0:
            return 0.0
        return round(daily / (daily + backwash) * 100, 2)

    def stats(self) -> Dict[str, float]:
        return {
            "filtration_rate_m_h": self.filtration_rate_m_h(),
            "head_loss_m": self.head_loss_m(),
            "water_recovery_percent": self.water_recovery_percent(),
        }

    def run(self):
        print("=" * 60)
        print("FILTRATION RATE CALCULATOR")
        print("=" * 60)
        filt = FiltrationRate(
            filter_area_sqm=50, flow_rate_m3_h=200,
            filter_media_depth_m=0.8, media_size_mm=0.8
        )
        print(f"Filter area: {filt.filter_area_sqm} sqm")
        print(f"Flow rate: {filt.flow_rate_m3_h} m3/h")
        print(f"Filtration rate: {filt.filtration_rate_m_h():.2f} m/h")
        print(f"Daily rate: {filt.filtration_rate_m3_per_day_per_sqm():.2f} m3/day/sqm")
        print(f"Head loss: {filt.head_loss_m():.3f} m")
        print(f"Backwash volume: {filt.backwash_water_volume_m3():.2f} m3")
        print(f"Water recovery: {filt.water_recovery_percent():.2f}%")
        print(f"Stats: {filt.stats()}")

if __name__ == "__main__":
    FiltrationRate(0, 0).run()

"""Marine Weather — sea state, swell, wind wave, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
from math import sqrt, pow, radians, degrees, sin, cos, atan2, pi, fabs, exp, log
from datetime import datetime, timedelta

class SeaStateCode(Enum):
    CALM = 0
    SMOOTH = 1
    SLIGHT = 2
    MODERATE = 3
    ROUGH = 4
    VERY_ROUGH = 5
    HIGH = 6
    VERY_HIGH = 7
    PHENOMENAL = 8

@dataclass
class WaveComponent:
    height_m: float
    period_s: float
    direction_deg: float  # from which wave comes
    type: str = "swell"  # swell or wind

    @property
    def wavelength(self) -> float:
        """Deep water wavelength using dispersion relation."""
        g = 9.81
        return g * self.period_s ** 2 / (2 * pi)

    @property
    def speed_ms(self) -> float:
        """Wave speed in m/s."""
        return self.wavelength / self.period_s if self.period_s > 0 else 0.0

    @property
    def steepness(self) -> float:
        return self.height_m / self.wavelength if self.wavelength > 0 else 0.0

@dataclass
class MarineWeather:
    wind_speed_ms: float = 0.0
    wind_direction_deg: float = 0.0
    air_pressure_hpa: float = 1013.0
    air_temp_c: float = 20.0
    sea_temp_c: float = 20.0
    waves: List[WaveComponent] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def significant_wave_height(self) -> float:
        """Hs = sqrt(sum of squares of wave heights)."""
        if not self.waves:
            return 0.0
        return sqrt(sum(w.height_m ** 2 for w in self.waves))

    def mean_wave_period(self) -> float:
        if not self.waves:
            return 0.0
        return sum(w.period_s for w in self.waves) / len(self.waves)

    def sea_state_code(self) -> SeaStateCode:
        hs = self.significant_wave_height()
        if hs < 0.1:
            return SeaStateCode.CALM
        elif hs < 0.5:
            return SeaStateCode.SMOOTH
        elif hs < 1.25:
            return SeaStateCode.SLIGHT
        elif hs < 2.5:
            return SeaStateCode.MODERATE
        elif hs < 4.0:
            return SeaStateCode.ROUGH
        elif hs < 6.0:
            return SeaStateCode.VERY_ROUGH
        elif hs < 9.0:
            return SeaStateCode.HIGH
        elif hs < 14.0:
            return SeaStateCode.VERY_HIGH
        return SeaStateCode.PHENOMENAL

    def wind_stress(self) -> float:
        """Wind stress in N/m^2 using simplified drag."""
        rho = 1.225
        cd = 0.0012
        return rho * cd * self.wind_speed_ms ** 2

    def wind_wave_estimate(self, fetch_km: float) -> WaveComponent:
        """Estimate wind wave from fetch and wind speed."""
        g = 9.81
        F = fetch_km * 1000
        # Simplified empirical
        H = 0.0016 * self.wind_speed_ms * sqrt(F / g) if F > 0 and self.wind_speed_ms > 0 else 0.0
        T = 0.2857 * self.wind_speed_ms
        return WaveComponent(height_m=H, period_s=T, direction_deg=self.wind_direction_deg, type="wind")

    def swell_wave_estimate(self, storm_distance_km: float, storm_wind_ms: float) -> WaveComponent:
        """Estimate swell from distant storm."""
        H = 0.0015 * storm_wind_ms * sqrt(storm_distance_km)
        T = 0.3 * storm_wind_ms + 2.0
        return WaveComponent(height_m=H, period_s=T, direction_deg=self.wind_direction_deg, type="swell")

    def stats(self) -> Dict[str, float]:
        return {
            "wind_speed_ms": self.wind_speed_ms,
            "air_pressure_hpa": self.air_pressure_hpa,
            "significant_wave_height_m": self.significant_wave_height(),
            "mean_wave_period_s": self.mean_wave_period(),
            "sea_state_code": self.sea_state_code().value,
            "wind_stress_nm2": self.wind_stress(),
            "wave_component_count": len(self.waves)
        }

def run():
    weather = MarineWeather(wind_speed_ms=12, wind_direction_deg=135, air_pressure_hpa=1008, air_temp_c=28, sea_temp_c=26)
    weather.waves.append(WaveComponent(height_m=1.5, period_s=8, direction_deg=135, type="wind"))
    weather.waves.append(WaveComponent(height_m=0.8, period_s=12, direction_deg=120, type="swell"))
    print(f"Significant wave height: {weather.significant_wave_height():.2f} m")
    print(f"Sea state: {weather.sea_state_code().name}")
    print(f"Wind stress: {weather.wind_stress():.3f} N/m²")
    wind_wave = weather.wind_wave_estimate(fetch_km=50)
    print(f"Estimated wind wave: H={wind_wave.height_m:.2f}m, T={wind_wave.period_s:.1f}s")
    print(weather.stats())

if __name__ == "__main__":
    run()

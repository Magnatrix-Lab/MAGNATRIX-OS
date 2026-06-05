"""Native stdlib module: UV Index Calculator
Estimates UV index by latitude, date, and ozone layer thickness.
"""
from dataclasses import dataclass
from typing import Dict
from enum import Enum

class SkinType(Enum):
    TYPE_1 = 1
    TYPE_2 = 2
    TYPE_3 = 3
    TYPE_4 = 4
    TYPE_5 = 5
    TYPE_6 = 6

@dataclass
class UVIndexCalculator:
    latitude: float
    day_of_year: int
    ozone_du: float = 300
    altitude_m: float = 0
    cloud_cover_pct: float = 0

    def solar_elevation_angle(self) -> float:
        declination = 23.45 * math.sin(math.radians((360 / 365) * (self.day_of_year - 81)))
        hour_angle = 0
        lat_rad = math.radians(self.latitude)
        dec_rad = math.radians(declination)
        sea = math.asin(math.sin(lat_rad) * math.sin(dec_rad) + math.cos(lat_rad) * math.cos(dec_rad) * math.cos(math.radians(hour_angle)))
        return math.degrees(sea)

    def base_uv_index(self) -> float:
        import math
        sea = self.solar_elevation_angle()
        if sea <= 0:
            return 0.0
        return max(0, (sea * 0.4) * (1 - (self.ozone_du - 250) / 1000))

    def altitude_adjustment(self) -> float:
        return 1 + (self.altitude_m / 1000) * 0.12

    def cloud_adjustment(self) -> float:
        return 1 - (self.cloud_cover_pct / 100) * 0.7

    def uv_index(self) -> float:
        return self.base_uv_index() * self.altitude_adjustment() * self.cloud_adjustment()

    def burn_time_min(self, skin_type: SkinType = SkinType.TYPE_3) -> int:
        burn_times = {SkinType.TYPE_1: 15, SkinType.TYPE_2: 25, SkinType.TYPE_3: 40, SkinType.TYPE_4: 60, SkinType.TYPE_5: 90, SkinType.TYPE_6: 120}
        base = burn_times.get(skin_type, 40)
        uv = self.uv_index()
        if uv == 0:
            return 999
        return int(base / uv)

    def risk_level(self) -> str:
        uv = self.uv_index()
        if uv < 3:
            return "low"
        elif uv < 6:
            return "moderate"
        elif uv < 8:
            return "high"
        elif uv < 11:
            return "very_high"
        return "extreme"

    def stats(self) -> Dict:
        return {
            "latitude": self.latitude,
            "day_of_year": self.day_of_year,
            "uv_index": round(self.uv_index(), 1),
            "risk_level": self.risk_level(),
            "burn_time_min": self.burn_time_min(),
        }

def run():
    import math
    uv = UVIndexCalculator(latitude=35, day_of_year=180, ozone_du=300, altitude_m=500, cloud_cover_pct=20)
    print(uv.stats())

if __name__ == "__main__":
    run()

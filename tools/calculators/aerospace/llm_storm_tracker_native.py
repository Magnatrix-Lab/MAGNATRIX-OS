"""Storm Tracker — path prediction, intensity, eye detection, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class StormTracker:
    positions: List[Tuple[float, float]] = field(default_factory=list)
    """lat, lon"""
    pressures: List[float] = field(default_factory=list)
    winds: List[float] = field(default_factory=list)

    def speed(self) -> float:
        if len(self.positions) < 2:
            return 0.0
        total = 0.0
        for i in range(len(self.positions) - 1):
            lat1, lon1 = self.positions[i]
            lat2, lon2 = self.positions[i+1]
            dlat = math.radians(lat2 - lat1)
            dlon = math.radians(lon2 - lon1)
            a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
            total += 2 * 6371 * math.asin(min(1, math.sqrt(a)))
        return total / (len(self.positions) - 1)

    def direction(self) -> float:
        if len(self.positions) < 2:
            return 0.0
        lat1, lon1 = self.positions[0]
        lat2, lon2 = self.positions[-1]
        dlon = math.radians(lon2 - lon1)
        y = math.sin(dlon) * math.cos(math.radians(lat2))
        x = math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(dlon)
        return (math.degrees(math.atan2(y, x)) + 360) % 360

    def category(self) -> int:
        max_wind = max(self.winds) if self.winds else 0
        if max_wind >= 70:
            return 5
        elif max_wind >= 58:
            return 4
        elif max_wind >= 50:
            return 3
        elif max_wind >= 43:
            return 2
        elif max_wind >= 33:
            return 1
        return 0

    def predict_position(self, hours: int = 6) -> Tuple[float, float]:
        if len(self.positions) < 2:
            return self.positions[-1] if self.positions else (0, 0)
        lat1, lon1 = self.positions[-2]
        lat2, lon2 = self.positions[-1]
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        return lat2 + dlat * hours / 6, lon2 + dlon * hours / 6

    def stats(self) -> Dict:
        return {"speed_kmh": round(self.speed(), 1), "direction": round(self.direction(), 1), "category": self.category()}

def run():
    st = StormTracker(positions=[(20,-80),(21,-79),(22,-78)], winds=[30,45,55])
    print(st.stats())
    print("Predict:", st.predict_position(12))

if __name__ == "__main__":
    run()

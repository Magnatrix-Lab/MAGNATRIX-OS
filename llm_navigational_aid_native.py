"""Navigational Aid — VOR, DME, NDB, bearing, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class NavAid:
    name: str
    lat: float
    lon: float
    freq: float
    nav_type: str

class NavigationalAid:
    def __init__(self):
        self.aids: List[NavAid] = []

    def add_aid(self, aid: NavAid):
        self.aids.append(aid)

    def bearing_to(self, aid: NavAid, lat: float, lon: float) -> float:
        dlon = math.radians(aid.lon - lon)
        y = math.sin(dlon) * math.cos(math.radians(aid.lat))
        x = math.cos(math.radians(lat)) * math.sin(math.radians(aid.lat)) - math.sin(math.radians(lat)) * math.cos(math.radians(aid.lat)) * math.cos(dlon)
        return (math.degrees(math.atan2(y, x)) + 360) % 360

    def distance_to(self, aid: NavAid, lat: float, lon: float) -> float:
        R = 6371.0
        dlat = math.radians(aid.lat - lat)
        dlon = math.radians(aid.lon - lon)
        ha = math.sin(dlat/2)**2 + math.cos(math.radians(lat)) * math.cos(math.radians(aid.lat)) * math.sin(dlon/2)**2
        return 2 * R * math.asin(min(1, math.sqrt(ha)))

    def nearest(self, lat: float, lon: float) -> Optional[NavAid]:
        if not self.aids:
            return None
        return min(self.aids, key=lambda a: self.distance_to(a, lat, lon))

    def stats(self, lat: float, lon: float) -> Dict:
        nearest = self.nearest(lat, lon)
        return {"aids": len(self.aids), "nearest": nearest.name if nearest else None, "distance": round(self.distance_to(nearest, lat, lon), 1) if nearest else None}

def run():
    na = NavigationalAid()
    na.add_aid(NavAid("JFK VOR", 40.64, -73.78, 115.9, "VOR"))
    na.add_aid(NavAid("BOS VOR", 42.37, -71.02, 112.3, "VOR"))
    print(na.stats(40.7, -73.9))

if __name__ == "__main__":
    run()

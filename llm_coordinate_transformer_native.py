"""Coordinate Transformer — UTM, Mercator, local tangent, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class CoordinateTransformer:
    a: float = 6378137.0
    e2: float = 0.00669437999013

    def latlon_to_utm(self, lat: float, lon: float) -> Tuple[float, float, int, str]:
        zone = int((lon + 180) / 6) + 1
        band = chr(ord('C') + int((lat + 80) / 8)) if -80 <= lat < 72 else 'X'
        lon0 = math.radians((zone - 1) * 6 - 180 + 3)
        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)
        N = self.a / math.sqrt(1 - self.e2 * math.sin(lat_rad)**2)
        T = math.tan(lat_rad)**2
        C = self.e2 * math.cos(lat_rad)**2 / (1 - self.e2)
        A = math.cos(lat_rad) * (lon_rad - lon0)
        M = self.a * ((1 - self.e2/4 - 3*self.e2**2/64 - 5*self.e2**3/256) * lat_rad - (3*self.e2/8 + 3*self.e2**2/32 + 45*self.e2**3/1024) * math.sin(2*lat_rad) + (15*self.e2**2/256 + 45*self.e2**3/1024) * math.sin(4*lat_rad) - (35*self.e2**3/3072) * math.sin(6*lat_rad))
        x = 500000 + 0.9996 * N * (A + (1-T+C) * A**3/6 + (5-18*T+T**2+72*C-58*self.e2/(1-self.e2)) * A**5/120)
        y = 0.9996 * (M + N * math.tan(lat_rad) * (A**2/2 + (5-T+9*C+4*C**2) * A**4/24 + (61-58*T+T**2+600*C-330*self.e2/(1-self.e2)) * A**6/720))
        if lat < 0: y += 10000000
        return round(x, 2), round(y, 2), zone, band

    def latlon_to_mercator(self, lat: float, lon: float) -> Tuple[float, float]:
        x = self.a * math.radians(lon)
        y = self.a * math.log(math.tan(math.pi/4 + math.radians(lat)/2))
        return round(x, 2), round(y, 2)

    def stats(self) -> Dict:
        return {"ellipsoid": "WGS84", "a": self.a}

def run():
    ct = CoordinateTransformer()
    print("UTM:", ct.latlon_to_utm(40.7128, -74.0060))
    print("Mercator:", ct.latlon_to_mercator(40.7128, -74.0060))
    print(ct.stats())

if __name__ == "__main__":
    run()

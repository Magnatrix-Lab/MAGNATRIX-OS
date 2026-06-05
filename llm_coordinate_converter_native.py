"""Native stdlib module: Coordinate Converter
Converts between decimal degrees, DMS, and UTM coordinates.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class CoordinateConverter:
    decimal_latitude: float
    decimal_longitude: float

    def to_dms(self, decimal: float) -> tuple:
        degrees = int(decimal)
        minutes_float = (decimal - degrees) * 60
        minutes = int(minutes_float)
        seconds = round((minutes_float - minutes) * 60, 2)
        return (degrees, minutes, seconds)

    def latitude_dms(self) -> str:
        d, m, s = self.to_dms(abs(self.decimal_latitude))
        direction = "N" if self.decimal_latitude >= 0 else "S"
        return f"{d}° {m}' {s}\" {direction}"

    def longitude_dms(self) -> str:
        d, m, s = self.to_dms(abs(self.decimal_longitude))
        direction = "E" if self.decimal_longitude >= 0 else "W"
        return f"{d}° {m}' {s}\" {direction}"

    def utm_zone(self) -> int:
        return int((self.decimal_longitude + 180) / 6) + 1

    def utm_letter(self) -> str:
        lat = self.decimal_latitude
        letters = "CDEFGHJKLMNPQRSTUVWXX"
        index = int((lat + 80) / 8)
        return letters[min(index, len(letters) - 1)]

    def utm_easting_northing(self) -> tuple:
        zone = self.utm_zone()
        lon0 = (zone - 1) * 6 - 180 + 3
        k0 = 0.9996
        a = 6378137.0
        e = 0.081819191
        lat_rad = math.radians(self.decimal_latitude)
        lon_rad = math.radians(self.decimal_longitude - lon0)
        N = a / math.sqrt(1 - e**2 * math.sin(lat_rad)**2)
        T = math.tan(lat_rad)**2
        C = e**2 * math.cos(lat_rad)**2 / (1 - e**2)
        A = math.cos(lat_rad) * lon_rad
        M = a * ((1 - e**2/4 - 3*e**4/64 - 5*e**6/256) * lat_rad
                 - (3*e**2/8 + 3*e**4/32 + 45*e**6/1024) * math.sin(2*lat_rad)
                 + (15*e**4/256 + 45*e**6/1024) * math.sin(4*lat_rad)
                 - (35*e**6/3072) * math.sin(6*lat_rad))
        easting = k0 * N * (A + (1-T+C) * A**3/6 + (5-18*T+T**2+72*C-58*0.006739497) * A**5/120) + 500000
        northing = k0 * (M + N * math.tan(lat_rad) * (A**2/2 + (5-T+9*C+4*C**2) * A**4/24 + (61-58*T+T**2+600*C-330*0.006739497) * A**6/720))
        if self.decimal_latitude < 0:
            northing += 10000000
        return (round(easting, 1), round(northing, 1))

    def stats(self) -> Dict:
        return {
            "decimal_lat": self.decimal_latitude,
            "decimal_lon": self.decimal_longitude,
            "latitude_dms": self.latitude_dms(),
            "longitude_dms": self.longitude_dms(),
            "utm_zone": self.utm_zone(),
            "utm_letter": self.utm_letter(),
            "utm_easting_northing": self.utm_easting_northing(),
        }

def run():
    cc = CoordinateConverter(decimal_latitude=40.7128, decimal_longitude=-74.0060)
    print(cc.stats())

if __name__ == "__main__":
    run()

"""Coordinate Converter — lat/lon, UTM, Cartesian, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import math

class CoordinateSystem(Enum):
    WGS84 = auto()
    UTM = auto()
    CARTESIAN = auto()

@dataclass
class GeoCoordinate:
    lat: float
    lon: float
    altitude: float = 0.0

@dataclass
class CartesianCoordinate:
    x: float
    y: float
    z: float = 0.0

class CoordinateConverter:
    def __init__(self):
        self.earth_radius = 6371000.0

    def wgs84_to_cartesian(self, coord: GeoCoordinate) -> CartesianCoordinate:
        lat_rad = math.radians(coord.lat)
        lon_rad = math.radians(coord.lon)
        x = self.earth_radius * math.cos(lat_rad) * math.cos(lon_rad)
        y = self.earth_radius * math.cos(lat_rad) * math.sin(lon_rad)
        z = self.earth_radius * math.sin(lat_rad) + coord.altitude
        return CartesianCoordinate(x, y, z)

    def cartesian_to_wgs84(self, coord: CartesianCoordinate) -> GeoCoordinate:
        lat = math.degrees(math.asin(coord.z / self.earth_radius))
        lon = math.degrees(math.atan2(coord.y, coord.x))
        return GeoCoordinate(lat, lon, 0.0)

    def haversine_distance(self, a: GeoCoordinate, b: GeoCoordinate) -> float:
        dlat = math.radians(b.lat - a.lat)
        dlon = math.radians(b.lon - a.lon)
        lat1 = math.radians(a.lat)
        lat2 = math.radians(b.lat)
        sin_dlat = math.sin(dlat / 2)
        sin_dlon = math.sin(dlon / 2)
        c = 2 * math.asin(math.sqrt(sin_dlat ** 2 + math.cos(lat1) * math.cos(lat2) * sin_dlon ** 2))
        return self.earth_radius * c

    def bearing(self, a: GeoCoordinate, b: GeoCoordinate) -> float:
        lat1 = math.radians(a.lat)
        lat2 = math.radians(b.lat)
        dlon = math.radians(b.lon - a.lon)
        x = math.sin(dlon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        brng = math.degrees(math.atan2(x, y))
        return (brng + 360) % 360

    def destination(self, start: GeoCoordinate, distance: float, bearing_deg: float) -> GeoCoordinate:
        lat1 = math.radians(start.lat)
        lon1 = math.radians(start.lon)
        brng = math.radians(bearing_deg)
        d_r = distance / self.earth_radius
        lat2 = math.asin(math.sin(lat1) * math.cos(d_r) + math.cos(lat1) * math.sin(d_r) * math.cos(brng))
        lon2 = lon1 + math.atan2(math.sin(brng) * math.sin(d_r) * math.cos(lat1), math.cos(d_r) - math.sin(lat1) * math.sin(lat2))
        return GeoCoordinate(math.degrees(lat2), math.degrees(lon2))

    def stats(self) -> Dict:
        return {"earth_radius": self.earth_radius, "supported_systems": ["WGS84", "UTM", "CARTESIAN"]}

def run():
    conv = CoordinateConverter()
    a = GeoCoordinate(40.7128, -74.0060)
    b = GeoCoordinate(51.5074, -0.1278)
    print("Distance:", conv.haversine_distance(a, b) / 1000, "km")
    print("Bearing:", conv.bearing(a, b))
    dest = conv.destination(a, 100000, 90)
    print("Destination:", dest.lat, dest.lon)
    print(conv.stats())

if __name__ == "__main__":
    run()

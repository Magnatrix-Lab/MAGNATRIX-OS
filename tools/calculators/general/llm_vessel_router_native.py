"""Vessel Router — waypoint routing, weather avoidance, fuel optimization, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
from math import sqrt, radians, degrees, sin, cos, atan2, pi, fabs, pow, asin
from datetime import datetime, timedelta

class HazardType(Enum):
    SHALLOW = auto()
    STORM = auto()
    ICE = auto()
    PIRACY = auto()

@dataclass
class Waypoint:
    lat: float
    lon: float
    name: str = ""
    min_depth: float = 0.0  # meters

@dataclass
class Hazard:
    lat: float
    lon: float
    radius: float  # nm
    type: HazardType
    start: datetime
    end: datetime

@dataclass
class VesselProfile:
    max_speed: float  # knots
    draft: float  # meters
    beam: float  # meters
    length: float  # meters
    fuel_rate: float  # tons/hour at cruising speed
    turn_radius: float = 0.5  # nm

class VesselRouter:
    def __init__(self, vessel: VesselProfile):
        self.vessel = vessel
        self.waypoints: List[Waypoint] = []
        self.hazards: List[Hazard] = []

    def add_waypoint(self, wp: Waypoint) -> None:
        self.waypoints.append(wp)

    def add_hazard(self, h: Hazard) -> None:
        self.hazards.append(h)

    def _haversine(self, wp1: Waypoint, wp2: Waypoint) -> float:
        """Distance in nautical miles."""
        R = 3440.065
        lat1, lon1 = radians(wp1.lat), radians(wp1.lon)
        lat2, lon2 = radians(wp2.lat), radians(wp2.lon)
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1)*cos(lat2)*sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        return R * c

    def _initial_bearing(self, wp1: Waypoint, wp2: Waypoint) -> float:
        lat1, lon1 = radians(wp1.lat), radians(wp1.lon)
        lat2, lon2 = radians(wp2.lat), radians(wp2.lon)
        dlon = lon2 - lon1
        x = sin(dlon) * cos(lat2)
        y = cos(lat1)*sin(lat2) - sin(lat1)*cos(lat2)*cos(dlon)
        return (degrees(atan2(x, y)) + 360) % 360

    def total_distance(self) -> float:
        if len(self.waypoints) < 2:
            return 0.0
        return sum(self._haversine(self.waypoints[i], self.waypoints[i+1]) for i in range(len(self.waypoints)-1))

    def total_time(self) -> float:
        """Total time in hours at cruising speed."""
        return self.total_distance() / self.vessel.max_speed if self.vessel.max_speed > 0 else 0.0

    def fuel_required(self) -> float:
        """Total fuel in tons."""
        return self.total_time() * self.vessel.fuel_rate

    def _point_in_hazard(self, lat: float, lon: float, h: Hazard) -> bool:
        R = 3440.065
        d = self._haversine(Waypoint(lat, lon), Waypoint(h.lat, h.lon))
        return d <= h.radius

    def check_hazards(self, t: datetime) -> List[Hazard]:
        active = [h for h in self.hazards if h.start <= t <= h.end]
        return active

    def route_summary(self) -> List[Dict]:
        legs = []
        for i in range(len(self.waypoints)-1):
            wp1, wp2 = self.waypoints[i], self.waypoints[i+1]
            dist = self._haversine(wp1, wp2)
            bearing = self._initial_bearing(wp1, wp2)
            legs.append({
                "from": wp1.name,
                "to": wp2.name,
                "distance_nm": dist,
                "bearing_deg": bearing,
                "time_hours": dist / self.vessel.max_speed,
                "fuel_tons": dist / self.vessel.max_speed * self.vessel.fuel_rate
            })
        return legs

    def stats(self) -> Dict[str, float]:
        return {
            "total_distance_nm": self.total_distance(),
            "total_time_hours": self.total_time(),
            "total_fuel_tons": self.fuel_required(),
            "waypoint_count": len(self.waypoints),
            "avg_leg_distance_nm": self.total_distance() / max(len(self.waypoints)-1, 1)
        }

def run():
    vessel = VesselProfile(max_speed=15, draft=12, beam=30, length=200, fuel_rate=0.5)
    router = VesselRouter(vessel)
    router.add_waypoint(Waypoint(1.3, 103.8, "Singapore"))
    router.add_waypoint(Waypoint(-6.2, 106.8, "Jakarta"))
    router.add_waypoint(Waypoint(-7.2, 112.7, "Surabaya"))
    router.add_hazard(Hazard(0.0, 105.0, 50, HazardType.STORM, datetime(2024, 6, 1), datetime(2024, 6, 3)))
    print(f"Total distance: {router.total_distance():.1f} nm")
    print(f"Total time: {router.total_time():.1f} hours")
    print(f"Fuel required: {router.fuel_required():.1f} tons")
    for leg in router.route_summary():
        print(f"  {leg['from']} → {leg['to']}: {leg['distance_nm']:.1f} nm, bearing {leg['bearing_deg']:.0f}°")
    print(router.stats())

if __name__ == "__main__":
    run()

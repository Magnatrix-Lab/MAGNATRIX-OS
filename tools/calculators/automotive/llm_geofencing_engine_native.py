"""Geofencing Engine — circular/polygon fences, entry/exit events, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Callable
from enum import Enum, auto
import math
import time

class FenceType(Enum):
    CIRCLE = auto()
    POLYGON = auto()

class GeofenceEvent(Enum):
    ENTER = auto()
    EXIT = auto()
    DWELL = auto()

@dataclass
class Geofence:
    fence_id: str
    fence_type: FenceType
    center: Optional[Tuple[float, float]] = None
    radius: float = 0.0
    vertices: List[Tuple[float, float]] = field(default_factory=list)

    def contains(self, lat: float, lon: float) -> bool:
        if self.fence_type == FenceType.CIRCLE and self.center:
            d = math.sqrt((lat - self.center[0]) ** 2 + (lon - self.center[1]) ** 2)
            return d <= self.radius
        elif self.fence_type == FenceType.POLYGON:
            return self._point_in_polygon(lat, lon, self.vertices)
        return False

    def _point_in_polygon(self, x: float, y: float, vertices: List[Tuple[float, float]]) -> bool:
        inside = False
        j = len(vertices) - 1
        for i in range(len(vertices)):
            xi, yi = vertices[i]
            xj, yj = vertices[j]
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        return inside

class GeofencingEngine:
    def __init__(self):
        self.fences: Dict[str, Geofence] = {}
        self.states: Dict[str, Dict[str, bool]] = {}
        self.handlers: Dict[GeofenceEvent, List[Callable]] = {}
        self.history: List[Dict] = []

    def add_fence(self, fence: Geofence):
        self.fences[fence.fence_id] = fence

    def on(self, event: GeofenceEvent, handler: Callable):
        if event not in self.handlers:
            self.handlers[event] = []
        self.handlers[event].append(handler)

    def check(self, entity_id: str, lat: float, lon: float):
        if entity_id not in self.states:
            self.states[entity_id] = {}
        for fid, fence in self.fences.items():
            inside = fence.contains(lat, lon)
            was_inside = self.states[entity_id].get(fid, False)
            if inside and not was_inside:
                self._trigger(GeofenceEvent.ENTER, entity_id, fid, lat, lon)
            elif not inside and was_inside:
                self._trigger(GeofenceEvent.EXIT, entity_id, fid, lat, lon)
            self.states[entity_id][fid] = inside

    def _trigger(self, event: GeofenceEvent, entity_id: str, fence_id: str, lat: float, lon: float):
        self.history.append({"event": event.name, "entity": entity_id, "fence": fence_id, "lat": lat, "lon": lon, "time": time.time()})
        for handler in self.handlers.get(event, []):
            try:
                handler(entity_id, fence_id, lat, lon)
            except:
                pass

    def stats(self) -> Dict:
        return {"fences": len(self.fences), "entities": len(self.states), "events": len(self.history)}

def run():
    engine = GeofencingEngine()
    engine.add_fence(Geofence("home", FenceType.CIRCLE, center=(40.7, -74.0), radius=1.0))
    engine.add_fence(Geofence("office", FenceType.POLYGON, vertices=[(40.8, -74.1), (40.8, -73.9), (40.6, -73.9), (40.6, -74.1)]))
    events = []
    def on_enter(e, f, lat, lon):
        events.append(f"enter {f}")
    engine.on(GeofenceEvent.ENTER, on_enter)
    engine.check("user1", 40.71, -74.01)
    engine.check("user1", 40.72, -74.02)
    engine.check("user1", 40.75, -74.05)
    print(events)
    print(engine.stats())

if __name__ == "__main__":
    run()

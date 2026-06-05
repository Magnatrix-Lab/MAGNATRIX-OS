"""Traffic Flow Simulator — intersection, throughput, signal timing, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto

class TrafficLightState(Enum):
    RED = auto()
    GREEN = auto()
    YELLOW = auto()

class TrafficFlowSimulator:
    def __init__(self):
        self.intersections: Dict[str, Dict] = {}
        self.roads: Dict[str, Dict] = {}

    def add_intersection(self, inter_id: str, green_duration: float = 30, yellow_duration: float = 5):
        self.intersections[inter_id] = {
            "state": TrafficLightState.GREEN,
            "green": green_duration,
            "yellow": yellow_duration,
            "timer": 0,
            "queues": {"N": 0, "S": 0, "E": 0, "W": 0},
        }

    def add_road(self, road_id: str, from_inter: str, to_inter: str, capacity: int = 100):
        self.roads[road_id] = {"from": from_inter, "to": to_inter, "capacity": capacity, "vehicles": 0}

    def add_vehicle(self, road_id: str, inter_id: str, direction: str):
        if inter_id in self.intersections:
            self.intersections[inter_id]["queues"][direction] += 1

    def step(self, dt: float):
        for inter in self.intersections.values():
            inter["timer"] += dt
            if inter["state"] == TrafficLightState.GREEN and inter["timer"] >= inter["green"]:
                inter["state"] = TrafficLightState.YELLOW
                inter["timer"] = 0
            elif inter["state"] == TrafficLightState.YELLOW and inter["timer"] >= inter["yellow"]:
                inter["state"] = TrafficLightState.RED
                inter["timer"] = 0
            elif inter["state"] == TrafficLightState.RED and inter["timer"] >= 30:
                inter["state"] = TrafficLightState.GREEN
                inter["timer"] = 0
            # Process queues
            if inter["state"] == TrafficLightState.GREEN:
                for d in inter["queues"]:
                    processed = min(inter["queues"][d], int(2 * dt))
                    inter["queues"][d] = max(0, inter["queues"][d] - processed)

    def get_throughput(self, inter_id: str) -> int:
        inter = self.intersections.get(inter_id, {})
        return sum(inter.get("queues", {}).values())

    def stats(self) -> Dict:
        total_queue = sum(sum(i["queues"].values()) for i in self.intersections.values())
        return {"intersections": len(self.intersections), "roads": len(self.roads), "total_queued": total_queue}

def run():
    tf = TrafficFlowSimulator()
    tf.add_intersection("I1", 30, 5)
    tf.add_road("R1", "I1", "I2", 50)
    tf.add_vehicle("R1", "I1", "N")
    tf.add_vehicle("R1", "I1", "N")
    tf.add_vehicle("R1", "I1", "E")
    for _ in range(10):
        tf.step(1.0)
    print(tf.stats())

if __name__ == "__main__":
    run()

"""Native stdlib module: Trajectory Planner
Plans point-to-point trajectories with velocity and acceleration profiles.
"""
from dataclasses import dataclass
from typing import Dict, List

@dataclass
class TrajectoryPlanner:
    start_pos: float
    end_pos: float
    max_velocity: float
    max_acceleration: float

    def distance(self) -> float:
        return abs(self.end_pos - self.start_pos)

    def direction(self) -> float:
        if self.end_pos > self.start_pos:
            return 1.0
        return -1.0

    def acceleration_time(self) -> float:
        if self.max_acceleration == 0:
            return 0.0
        return self.max_velocity / self.max_acceleration

    def acceleration_distance(self) -> float:
        t = self.acceleration_time()
        return 0.5 * self.max_acceleration * t ** 2

    def total_time(self) -> float:
        d = self.distance()
        acc_dist = self.acceleration_distance()
        if d >= 2 * acc_dist:
            cruise_dist = d - 2 * acc_dist
            cruise_time = cruise_dist / self.max_velocity
            return 2 * self.acceleration_time() + cruise_time
        else:
            t = (d / self.max_acceleration) ** 0.5
            return 2 * t

    def max_reachable_velocity(self) -> float:
        d = self.distance()
        acc_dist = self.acceleration_distance()
        if d >= 2 * acc_dist:
            return self.max_velocity
        return (d * self.max_acceleration) ** 0.5

    def stats(self) -> Dict:
        return {
            "distance": round(self.distance(), 4),
            "total_time": round(self.total_time(), 4),
            "acceleration_time": round(self.acceleration_time(), 4),
            "max_reachable_velocity": round(self.max_reachable_velocity(), 4),
        }

def run():
    tp = TrajectoryPlanner(start_pos=0, end_pos=10, max_velocity=2, max_acceleration=1)
    print(tp.stats())

if __name__ == "__main__":
    run()

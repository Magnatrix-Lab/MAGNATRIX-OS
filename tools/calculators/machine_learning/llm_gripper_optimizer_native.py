"""Gripper Optimizer — force, friction, stability, finger design, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class GripperOptimizer:
    finger_count: int = 2
    finger_width: float = 0.02
    contact_friction: float = 0.5
    max_force: float = 100.0

    def required_force(self, object_weight: float, safety_factor: float = 1.5) -> float:
        return object_weight * 9.81 * safety_factor / (self.finger_count * self.contact_friction)

    def contact_pressure(self, object_weight: float, contact_area: float) -> float:
        force = self.required_force(object_weight)
        return force / contact_area if contact_area > 0 else 0.0

    def stable_grasp(self, object_weight: float, object_radius: float) -> bool:
        force = self.required_force(object_weight)
        if force > self.max_force:
            return False
        min_span = object_radius * 0.5
        return self.finger_width <= min_span

    def finger_span(self, object_radius: float) -> float:
        if self.finger_count == 2:
            return 2 * object_radius * 1.2
        elif self.finger_count == 3:
            return 2 * object_radius * math.cos(math.pi / 6) * 1.2
        return 2 * object_radius

    def stats(self, object_weight: float = 1.0, object_radius: float = 0.05) -> Dict:
        return {
            "required_force": round(self.required_force(object_weight), 2),
            "stable": self.stable_grasp(object_weight, object_radius),
            "span": round(self.finger_span(object_radius), 3)
        }

def run():
    go = GripperOptimizer(finger_count=3, contact_friction=0.6, max_force=50)
    print(go.stats(2.0, 0.08))

if __name__ == "__main__":
    run()

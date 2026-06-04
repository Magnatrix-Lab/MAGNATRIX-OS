"""Actuator Driver - Motor/servo control for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List
from enum import Enum, auto

class ActuatorType(Enum):
    MOTOR = auto(); SERVO = auto(); LED = auto(); RELAY = auto()

@dataclass
class ActuatorDriver:
    actuators: Dict[str, Dict] = field(default_factory=dict)

    def register(self, id: str, atype: ActuatorType, min_val: float = 0, max_val: float = 100) -> None:
        self.actuators[id] = {"type": atype, "min": min_val, "max": max_val, "current": 0.0}

    def set_value(self, id: str, value: float) -> None:
        if id in self.actuators:
            a = self.actuators[id]
            a["current"] = max(a["min"], min(a["max"], value))

    def get_value(self, id: str) -> float:
        return self.actuators.get(id, {}).get("current", 0.0)

    def stats(self) -> dict:
        return {"actuators": len(self.actuators), "types": list(set(a["type"].name for a in self.actuators.values()))}

def run():
    ad = ActuatorDriver()
    ad.register("motor1", ActuatorType.MOTOR, 0, 255)
    ad.set_value("motor1", 128)
    print("Motor1:", ad.get_value("motor1"))
    print("Stats:", ad.stats())

if __name__ == "__main__": run()

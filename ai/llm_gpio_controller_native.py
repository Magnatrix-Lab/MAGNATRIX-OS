"""GPIO Controller - GPIO abstraction for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List
from enum import Enum, auto

class PinMode(Enum):
    INPUT = auto(); OUTPUT = auto(); PWM = auto()

class PinState(Enum):
    LOW = auto(); HIGH = auto()

@dataclass
class GPIOController:
    pins: Dict[int, Dict] = field(default_factory=dict)

    def set_mode(self, pin: int, mode: PinMode) -> None:
        self.pins[pin] = {"mode": mode, "state": PinState.LOW}

    def digital_write(self, pin: int, state: PinState) -> None:
        if pin in self.pins and self.pins[pin]["mode"] == PinMode.OUTPUT:
            self.pins[pin]["state"] = state

    def digital_read(self, pin: int) -> PinState:
        return self.pins.get(pin, {}).get("state", PinState.LOW)

    def stats(self) -> dict:
        return {"pins": len(self.pins), "outputs": sum(1 for p in self.pins.values() if p["mode"] == PinMode.OUTPUT)}

def run():
    gpio = GPIOController()
    gpio.set_mode(1, PinMode.OUTPUT)
    gpio.digital_write(1, PinState.HIGH)
    print("Pin 1:", gpio.digital_read(1).name)
    print("Stats:", gpio.stats())

if __name__ == "__main__": run()

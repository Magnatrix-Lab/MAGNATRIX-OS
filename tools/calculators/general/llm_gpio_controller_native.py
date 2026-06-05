"""GPIO Controller — hardware pin abstraction, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from enum import Enum, auto
import time

class PinMode(Enum):
    INPUT = auto()
    OUTPUT = auto()
    PWM = auto()

class PinState(Enum):
    LOW = 0
    HIGH = 1

@dataclass
class Pin:
    pin_number: int
    mode: PinMode = PinMode.INPUT
    state: PinState = PinState.LOW
    pwm_duty: float = 0.0
    pwm_freq: float = 1000.0

class GPIOController:
    def __init__(self):
        self.pins: Dict[int, Pin] = {}
        self.interrupts: Dict[int, List[Callable]] = {}
        self.history: List[Dict] = []

    def setup_pin(self, pin_number: int, mode: PinMode):
        self.pins[pin_number] = Pin(pin_number, mode)

    def digital_write(self, pin_number: int, state: PinState):
        pin = self.pins.get(pin_number)
        if pin and pin.mode == PinMode.OUTPUT:
            pin.state = state
            self.history.append({"pin": pin_number, "state": state.name, "time": time.time()})

    def digital_read(self, pin_number: int) -> PinState:
        pin = self.pins.get(pin_number)
        return pin.state if pin else PinState.LOW

    def pwm_write(self, pin_number: int, duty: float, freq: float = 1000.0):
        pin = self.pins.get(pin_number)
        if pin and pin.mode == PinMode.PWM:
            pin.pwm_duty = max(0, min(100, duty))
            pin.pwm_freq = freq

    def pwm_read(self, pin_number: int) -> Tuple[float, float]:
        pin = self.pins.get(pin_number)
        return (pin.pwm_duty, pin.pwm_freq) if pin else (0.0, 0.0)

    def register_interrupt(self, pin_number: int, callback: Callable):
        if pin_number not in self.interrupts:
            self.interrupts[pin_number] = []
        self.interrupts[pin_number].append(callback)

    def trigger_interrupt(self, pin_number: int):
        for cb in self.interrupts.get(pin_number, []):
            try:
                cb(pin_number)
            except:
                pass

    def stats(self) -> Dict:
        return {"pins": len(self.pins), "interrupts": sum(len(v) for v in self.interrupts.values()), "history": len(self.history)}

def run():
    gpio = GPIOController()
    gpio.setup_pin(1, PinMode.OUTPUT)
    gpio.setup_pin(2, PinMode.INPUT)
    gpio.setup_pin(3, PinMode.PWM)
    gpio.digital_write(1, PinState.HIGH)
    gpio.pwm_write(3, 75.0)
    print(gpio.digital_read(1).name, gpio.pwm_read(3))
    print(gpio.stats())

if __name__ == "__main__":
    run()

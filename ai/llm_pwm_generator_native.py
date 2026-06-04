"""PWM Generator - Pulse width modulation for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List

@dataclass
class PWMGenerator:
    frequency: float = 1000.0
    duty_cycle: float = 0.5
    resolution: int = 8

    def set_duty(self, duty: float) -> None:
        self.duty_cycle = max(0.0, min(1.0, duty))

    def generate(self, cycles: int = 10) -> List[int]:
        period = 1.0 / self.frequency
        on_time = period * self.duty_cycle
        samples = []
        for i in range(cycles):
            t = (i % int(self.frequency)) / self.frequency
            samples.append(1 if t < self.duty_cycle else 0)
        return samples

    def effective_voltage(self, vcc: float = 5.0) -> float:
        return vcc * self.duty_cycle

    def stats(self) -> dict:
        return {"freq": self.frequency, "duty": self.duty_cycle, "effective_v": self.effective_voltage()}

def run():
    pwm = PWMGenerator(1000, 0.75)
    print("Waveform:", pwm.generate(10))
    print("Effective 5V:", pwm.effective_voltage(5.0))
    print("Stats:", pwm.stats())

if __name__ == "__main__": run()

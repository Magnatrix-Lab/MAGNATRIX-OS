"""Signal Strength — RSSI, dBm, path loss, Fresnel, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class SignalStrength:
    tx_power: float = 20.0
    frequency: float = 2400.0
    distance: float = 1000.0
    antenna_gain: float = 2.0

    def free_space_path_loss(self) -> float:
        if self.distance <= 0 or self.frequency <= 0:
            return 0.0
        return 20 * math.log10(self.distance) + 20 * math.log10(self.frequency) + 32.45

    def rssi(self) -> float:
        return self.tx_power + self.antenna_gain * 2 - self.free_space_path_loss()

    def fresnel_zone_radius(self, n: int = 1) -> float:
        if self.distance <= 0 or self.frequency <= 0:
            return 0.0
        c = 3e8
        return 17.32 * math.sqrt((n * self.distance * 1000) / (4 * self.frequency)) if self.frequency > 0 else 0

    def link_budget(self, rx_sensitivity: float = -90.0) -> float:
        return self.rssi() - rx_sensitivity

    def max_range(self, rx_sensitivity: float = -90.0) -> float:
        if self.frequency <= 0:
            return 0.0
        loss_allowed = self.tx_power + self.antenna_gain * 2 - rx_sensitivity - 32.45
        return 10 ** (loss_allowed / 20) / self.frequency * 1e6 if loss_allowed > 0 else 0

    def stats(self) -> Dict:
        return {"rssi": round(self.rssi(), 1), "path_loss": round(self.free_space_path_loss(), 1), "link_budget": round(self.link_budget(), 1)}

def run():
    ss = SignalStrength(tx_power=23, frequency=5800, distance=2, antenna_gain=5)
    print(ss.stats())
    print("Fresnel:", ss.fresnel_zone_radius())
    print("Max range:", ss.max_range())

if __name__ == "__main__":
    run()

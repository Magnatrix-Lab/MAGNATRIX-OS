"""Signal Strength Calculator — dBm, path loss, link budget, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math

@dataclass
class SignalStrengthCalculator:
    tx_power: float = 20.0
    """dBm"""
    frequency: float = 2.4
    """GHz"""
    antenna_gain: float = 2.0
    """dBi"""
    cable_loss: float = 1.0
    """dB"""

    def fspl(self, distance_km: float) -> float:
        """Free space path loss."""
        return 20 * math.log10(distance_km) + 20 * math.log10(self.frequency * 1000) + 32.45

    def rx_power(self, distance_km: float) -> float:
        return self.tx_power + self.antenna_gain - self.cable_loss - self.fspl(distance_km)

    def rssi_to_quality(self, rssi: float) -> str:
        if rssi >= -50: return "excellent"
        elif rssi >= -60: return "good"
        elif rssi >= -70: return "fair"
        elif rssi >= -80: return "poor"
        return "very_poor"

    def link_budget(self, distance_km: float, rx_sensitivity: float = -90.0) -> float:
        return self.rx_power(distance_km) - rx_sensitivity

    def max_range(self, rx_sensitivity: float = -90.0) -> float:
        for d in range(1, 10000):
            if self.link_budget(d / 1000, rx_sensitivity) < 0:
                return (d - 1) / 1000
        return 10.0

    def stats(self, distance_km: float = 1.0) -> Dict:
        return {
            "rx_power": round(self.rx_power(distance_km), 1),
            "quality": self.rssi_to_quality(self.rx_power(distance_km)),
            "link_budget": round(self.link_budget(distance_km), 1)
        }

def run():
    ssc = SignalStrengthCalculator()
    print(ssc.stats(0.5))
    print("Max range:", ssc.max_range(), "km")

if __name__ == "__main__":
    run()

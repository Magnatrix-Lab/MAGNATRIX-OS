"""Cell Voltage Calculator — native stdlib module for MAGNATRIX-OS."""
from __future__ import annotations
import math
from dataclasses import dataclass
from typing import Dict, Optional

@dataclass
class CellVoltage:
    chemistry: str
    state_of_charge_percent: float
    temperature_c: float = 25.0
    load_current_a: float = 0.0
    internal_resistance_mohm: float = 20.0

    def nominal_voltage(self) -> float:
        voltages = {"li_ion": 3.7, "lifepo4": 3.2, "lead_acid": 2.0, "nimh": 1.2, "nicd": 1.2, "lto": 2.4}
        return voltages.get(self.chemistry, 3.7)

    def open_circuit_voltage(self) -> float:
        nom = self.nominal_voltage()
        soc = self.state_of_charge_percent / 100.0
        curves = {
            "li_ion": 3.0 + 0.7 * soc,
            "lifepo4": 3.0 + 0.3 * soc,
            "lead_acid": 1.75 + 0.5 * soc,
            "nimh": 1.0 + 0.4 * soc,
            "nicd": 1.0 + 0.4 * soc,
            "lto": 2.0 + 0.5 * soc,
        }
        return round(curves.get(self.chemistry, nom), 3)

    def loaded_voltage(self) -> float:
        ocv = self.open_circuit_voltage()
        drop = self.load_current_a * self.internal_resistance_mohm / 1000.0
        return round(ocv - drop, 3)

    def voltage_sag(self) -> float:
        return round(self.open_circuit_voltage() - self.loaded_voltage(), 3)

    def efficiency_percent(self) -> float:
        ocv = self.open_circuit_voltage()
        if ocv <= 0:
            return 0.0
        return round(self.loaded_voltage() / ocv * 100, 2)

    def temperature_compensation(self) -> float:
        return round((self.temperature_c - 25) * -0.003 * self.nominal_voltage(), 3)

    def stats(self) -> Dict[str, float]:
        return {
            "open_circuit_voltage": self.open_circuit_voltage(),
            "loaded_voltage": self.loaded_voltage(),
            "voltage_sag": self.voltage_sag(),
        }

    def run(self):
        print("=" * 60)
        print("CELL VOLTAGE CALCULATOR")
        print("=" * 60)
        cell = CellVoltage(
            chemistry="li_ion", state_of_charge_percent=80,
            temperature_c=30, load_current_a=5.0, internal_resistance_mohm=15
        )
        print(f"Chemistry: {cell.chemistry}")
        print(f"SOC: {cell.state_of_charge_percent}%")
        print(f"Nominal: {cell.nominal_voltage():.2f} V")
        print(f"OCV: {cell.open_circuit_voltage():.3f} V")
        print(f"Loaded voltage: {cell.loaded_voltage():.3f} V")
        print(f"Voltage sag: {cell.voltage_sag():.3f} V")
        print(f"Efficiency: {cell.efficiency_percent():.2f}%")
        print(f"Temp compensation: {cell.temperature_compensation():.3f} V")
        print(f"Stats: {cell.stats()}")

if __name__ == "__main__":
    CellVoltage("li_ion", 0).run()

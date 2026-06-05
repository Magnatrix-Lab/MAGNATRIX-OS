"""Native stdlib module: Battery Sizer
Calculates battery bank size for off-grid or backup systems.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class BatterySizer:
    daily_load_kwh: float
    days_autonomy: int
    depth_of_discharge_pct: float
    system_voltage_v: float
    inverter_efficiency_pct: float = 95.0

    def total_energy_needed_kwh(self) -> float:
        return self.daily_load_kwh * self.days_autonomy / (self.inverter_efficiency_pct / 100)

    def usable_battery_capacity_kwh(self) -> float:
        return self.total_energy_needed_kwh() / (self.depth_of_discharge_pct / 100)

    def battery_capacity_ah(self) -> float:
        if self.system_voltage_v == 0:
            return 0.0
        return (self.usable_battery_capacity_kwh() * 1000) / self.system_voltage_v

    def stats(self) -> Dict[str, float]:
        return {
            "daily_load_kwh": self.daily_load_kwh,
            "total_energy_needed_kwh": round(self.total_energy_needed_kwh(), 2),
            "usable_battery_capacity_kwh": round(self.usable_battery_capacity_kwh(), 2),
            "battery_capacity_ah": round(self.battery_capacity_ah(), 1),
            "system_voltage_v": self.system_voltage_v,
        }

def run():
    bs = BatterySizer(daily_load_kwh=15, days_autonomy=2, depth_of_discharge_pct=80, system_voltage_v=48)
    print(bs.stats())

if __name__ == "__main__":
    run()

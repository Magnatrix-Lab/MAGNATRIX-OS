"""Native stdlib module: Port Operations Calculator
Calculates berth occupancy, vessel turnaround time, and throughput for ports.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class VesselCall:
    vessel_name: str
    cargo_ton: float
    arrival_time: str
    departure_time: str
    berth_time_hours: float

@dataclass
class PortOperationsCalculator:
    port_name: str
    num_berths: int
    annual_operating_days: int = 330
    vessel_calls: List[VesselCall] = field(default_factory=list)

    def total_cargo_ton(self) -> float:
        return sum(v.cargo_ton for v in self.vessel_calls)

    def total_berth_hours(self) -> float:
        return sum(v.berth_time_hours for v in self.vessel_calls)

    def berth_occupancy_pct(self) -> float:
        total_available_hours = self.num_berths * 24 * self.annual_operating_days
        if total_available_hours == 0:
            return 0.0
        return (self.total_berth_hours() / total_available_hours) * 100

    def avg_turnaround_hours(self) -> float:
        if not self.vessel_calls:
            return 0.0
        return self.total_berth_hours() / len(self.vessel_calls)

    def annual_throughput_mt(self) -> float:
        return self.total_cargo_ton() / 1000000

    def avg_cargo_per_vessel_ton(self) -> float:
        if not self.vessel_calls:
            return 0.0
        return self.total_cargo_ton() / len(self.vessel_calls)

    def stats(self) -> Dict:
        return {
            "port": self.port_name,
            "berths": self.num_berths,
            "vessel_calls": len(self.vessel_calls),
            "total_cargo_ton": round(self.total_cargo_ton(), 1),
            "berth_occupancy_pct": round(self.berth_occupancy_pct(), 1),
            "avg_turnaround_hr": round(self.avg_turnaround_hours(), 1),
            "annual_throughput_mt": round(self.annual_throughput_mt(), 2),
        }

def run():
    poc = PortOperationsCalculator(
        port_name="Port Alpha",
        num_berths=4,
        vessel_calls=[
            VesselCall("Vessel A", 50000, "2024-06-01", "2024-06-03", 36),
            VesselCall("Vessel B", 35000, "2024-06-02", "2024-06-04", 30),
            VesselCall("Vessel C", 80000, "2024-06-03", "2024-06-06", 48),
            VesselCall("Vessel D", 25000, "2024-06-05", "2024-06-06", 24),
        ]
    )
    print(poc.stats())

if __name__ == "__main__":
    run()

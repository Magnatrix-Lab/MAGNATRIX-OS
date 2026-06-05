"""Native stdlib module: Line Balancer
Balances production line tasks across stations to minimize cycle time.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class Task:
    name: str
    duration_sec: float
    predecessors: List[str] = field(default_factory=list)

@dataclass
class LineBalancer:
    line_name: str
    cycle_time_sec: float
    tasks: List[Task] = field(default_factory=list)

    def total_work_content(self) -> float:
        return sum(t.duration_sec for t in self.tasks)

    def min_stations(self) -> int:
        if self.cycle_time_sec <= 0:
            return 0
        return max(1, int(self.total_work_content() / self.cycle_time_sec) + (1 if self.total_work_content() % self.cycle_time_sec > 0 else 0))

    def balance_efficiency(self, num_stations: int) -> float:
        if num_stations == 0:
            return 0.0
        return (self.total_work_content() / (num_stations * self.cycle_time_sec)) * 100

    def idle_time(self, num_stations: int) -> float:
        return (num_stations * self.cycle_time_sec) - self.total_work_content()

    def stats(self, num_stations: int = 0) -> Dict:
        if num_stations == 0:
            num_stations = self.min_stations()
        return {
            "line": self.line_name,
            "total_work_content_sec": round(self.total_work_content(), 1),
            "min_stations": self.min_stations(),
            "balance_efficiency_pct": round(self.balance_efficiency(num_stations), 1),
            "idle_time_sec": round(self.idle_time(num_stations), 1),
        }

def run():
    lb = LineBalancer(
        line_name="Assembly Line A",
        cycle_time_sec=60,
        tasks=[
            Task("install_engine", 45),
            Task("attach_wheels", 30),
            Task("wiring", 40),
            Task("quality_check", 25),
            Task("packaging", 20),
        ]
    )
    print(lb.stats())

if __name__ == "__main__":
    run()

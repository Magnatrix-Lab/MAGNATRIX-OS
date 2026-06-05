"""Native stdlib module: Attendance Tracker
Tracks employee attendance, leave balances, and overtime hours.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class DayRecord:
    date: str
    hours_worked: float
    leave_type: str = ""
    overtime_hours: float = 0.0

@dataclass
class AttendanceTracker:
    employee_name: str
    annual_leave_days: float = 20.0
    sick_leave_days: float = 10.0
    records: List[DayRecord] = field(default_factory=list)

    def total_hours_worked(self) -> float:
        return sum(r.hours_worked for r in self.records if not r.leave_type)

    def total_overtime(self) -> float:
        return sum(r.overtime_hours for r in self.records)

    def leave_used(self, leave_type: str) -> int:
        return sum(1 for r in self.records if r.leave_type == leave_type)

    def leave_balance(self, leave_type: str) -> float:
        if leave_type == "annual":
            return self.annual_leave_days - self.leave_used("annual")
        elif leave_type == "sick":
            return self.sick_leave_days - self.leave_used("sick")
        return 0.0

    def stats(self) -> Dict:
        return {
            "employee": self.employee_name,
            "total_hours": round(self.total_hours_worked(), 1),
            "total_overtime": round(self.total_overtime(), 1),
            "annual_balance": self.leave_balance("annual"),
            "sick_balance": self.leave_balance("sick"),
        }

def run():
    at = AttendanceTracker(
        employee_name="Bob Chen",
        records=[
            DayRecord("2024-06-01", 8, overtime_hours=2),
            DayRecord("2024-06-02", 8),
            DayRecord("2024-06-03", 0, leave_type="annual"),
            DayRecord("2024-06-04", 8, overtime_hours=1.5),
            DayRecord("2024-06-05", 6, leave_type="sick"),
        ]
    )
    print(at.stats())

if __name__ == "__main__":
    run()

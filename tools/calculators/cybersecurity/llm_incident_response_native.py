"""Native stdlib module: Incident Response Calculator
Calculates incident severity, response times, and MTTD/MTTR metrics.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class ImpactLevel(Enum):
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

@dataclass
class Incident:
    incident_id: str
    detected_time_min: float
    resolved_time_min: float
    impact: ImpactLevel
    affected_systems: int

@dataclass
class IncidentResponseCalculator:
    team_name: str
    incidents: List[Incident] = field(default_factory=list)

    def mttd_min(self) -> float:
        if not self.incidents:
            return 0.0
        return sum(i.detected_time_min for i in self.incidents) / len(self.incidents)

    def mttr_min(self) -> float:
        if not self.incidents:
            return 0.0
        return sum(i.resolved_time_min for i in self.incidents) / len(self.incidents)

    def total_affected_systems(self) -> int:
        return sum(i.affected_systems for i in self.incidents)

    def avg_severity_score(self) -> float:
        if not self.incidents:
            return 0.0
        return sum(i.impact.value for i in self.incidents) / len(self.incidents)

    def incidents_by_impact(self) -> Dict[str, int]:
        counts = {}
        for i in self.incidents:
            counts[i.impact.name] = counts.get(i.impact.name, 0) + 1
        return counts

    def sl_compliance_pct(self, sl_threshold_min: float) -> float:
        if not self.incidents:
            return 100.0
        met = sum(1 for i in self.incidents if i.resolved_time_min <= sl_threshold_min)
        return (met / len(self.incidents)) * 100

    def stats(self, sl_threshold_min: float = 60) -> Dict:
        return {
            "team": self.team_name,
            "incidents": len(self.incidents),
            "mttd_min": round(self.mttd_min(), 1),
            "mttr_min": round(self.mttr_min(), 1),
            "total_affected_systems": self.total_affected_systems(),
            "avg_severity": round(self.avg_severity_score(), 2),
            "by_impact": self.incidents_by_impact(),
            "sl_compliance_pct": round(self.sl_compliance_pct(sl_threshold_min), 1),
        }

def run():
    irc = IncidentResponseCalculator(
        team_name="SOC Alpha",
        incidents=[
            Incident("INC-001", 5, 45, ImpactLevel.HIGH, 3),
            Incident("INC-002", 10, 120, ImpactLevel.CRITICAL, 12),
            Incident("INC-003", 2, 15, ImpactLevel.LOW, 1),
            Incident("INC-004", 8, 55, ImpactLevel.MEDIUM, 2),
            Incident("INC-005", 15, 90, ImpactLevel.HIGH, 5),
        ]
    )
    print(irc.stats())

if __name__ == "__main__":
    run()

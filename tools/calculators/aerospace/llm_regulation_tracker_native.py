"""Native stdlib module: Regulation Tracker
Tracks regulatory requirements by jurisdiction, sector, and effective dates.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class Jurisdiction(Enum):
    US = "us"
    EU = "eu"
    UK = "uk"
    CA = "ca"
    AU = "au"
    JP = "jp"

class Sector(Enum):
    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    TECH = "tech"
    ENERGY = "energy"
    MANUFACTURING = "manufacturing"

@dataclass
class Regulation:
    code: str
    name: str
    jurisdiction: Jurisdiction
    sector: Sector
    effective_date: str
    compliance_deadline: str
    status: str = "active"

@dataclass
class RegulationTracker:
    tracker_name: str
    regulations: List[Regulation] = field(default_factory=list)

    def by_jurisdiction(self, jurisdiction: Jurisdiction) -> List[Regulation]:
        return [r for r in self.regulations if r.jurisdiction == jurisdiction]

    def by_sector(self, sector: Sector) -> List[Regulation]:
        return [r for r in self.regulations if r.sector == sector]

    def upcoming_deadlines(self, days: int = 90) -> List[Regulation]:
        from datetime import datetime, timedelta
        today = datetime.now()
        upcoming = []
        for r in self.regulations:
            try:
                deadline = datetime.strptime(r.compliance_deadline, "%Y-%m-%d")
                if (deadline - today).days <= days and r.status == "active":
                    upcoming.append(r)
            except ValueError:
                continue
        return upcoming

    def stats(self) -> Dict:
        return {
            "tracker": self.tracker_name,
            "total_regulations": len(self.regulations),
            "upcoming_90d": len(self.upcoming_deadlines()),
            "by_jurisdiction": {j.value: len(self.by_jurisdiction(j)) for j in Jurisdiction},
        }

def run():
    rt = RegulationTracker(
        tracker_name="Global Compliance 2024",
        regulations=[
            Regulation("GDPR-2016", "General Data Protection", Jurisdiction.EU, Sector.TECH, "2018-05-25", "2024-12-31"),
            Regulation("SOX-2002", "Sarbanes-Oxley", Jurisdiction.US, Sector.FINANCE, "2002-07-30", "2024-12-31"),
            Regulation("HIPAA-1996", "Health Insurance Portability", Jurisdiction.US, Sector.HEALTHCARE, "1996-08-21", "2025-01-01"),
            Regulation("CCPA-2018", "California Privacy Act", Jurisdiction.US, Sector.TECH, "2020-01-01", "2024-06-30"),
        ]
    )
    print(rt.stats())

if __name__ == "__main__":
    run()

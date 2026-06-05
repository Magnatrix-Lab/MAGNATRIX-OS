"""Native stdlib module: Compliance Auditor
Checks compliance items against a checklist and calculates a compliance score.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class ComplianceArea(Enum):
    DATA_PRIVACY = "data_privacy"
    SECURITY = "security"
    FINANCIAL = "financial"
    ENVIRONMENTAL = "environmental"
    LABOR = "labor"

@dataclass
class ComplianceItem:
    area: ComplianceArea
    description: str
    compliant: bool
    severity: str = "medium"

@dataclass
class ComplianceAuditor:
    audit_name: str
    audit_date: str
    items: List[ComplianceItem] = field(default_factory=list)

    def score(self) -> float:
        if not self.items:
            return 100.0
        passed = sum(1 for i in self.items if i.compliant)
        return (passed / len(self.items)) * 100

    def failures_by_area(self) -> Dict[str, int]:
        fails = {}
        for i in self.items:
            if not i.compliant:
                fails[i.area.value] = fails.get(i.area.value, 0) + 1
        return fails

    def critical_failures(self) -> List[ComplianceItem]:
        return [i for i in self.items if not i.compliant and i.severity == "critical"]

    def stats(self) -> Dict:
        return {
            "audit": self.audit_name,
            "score_pct": round(self.score(), 1),
            "total_items": len(self.items),
            "failures_by_area": self.failures_by_area(),
            "critical_failures": len(self.critical_failures()),
        }

def run():
    ca = ComplianceAuditor(
        audit_name="Q2 Internal Audit",
        audit_date="2024-06-15",
        items=[
            ComplianceItem(ComplianceArea.DATA_PRIVACY, "GDPR consent forms", True, "critical"),
            ComplianceItem(ComplianceArea.SECURITY, "MFA enabled", False, "critical"),
            ComplianceItem(ComplianceArea.FINANCIAL, "Expense receipts", True, "medium"),
            ComplianceItem(ComplianceArea.LABOR, "Overtime records", False, "medium"),
            ComplianceItem(ComplianceArea.ENVIRONMENTAL, "Waste disposal log", True, "low"),
        ]
    )
    print(ca.stats())

if __name__ == "__main__":
    run()

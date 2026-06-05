"""Native stdlib module: Cyber Risk Matrix
Calculates risk scores and priority levels from vulnerability assessments.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class Severity(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class Likelihood(Enum):
    RARE = 1
    UNLIKELY = 2
    POSSIBLE = 3
    LIKELY = 4
    ALMOST_CERTAIN = 5

@dataclass
class Vulnerability:
    name: str
    severity: Severity
    likelihood: Likelihood
    asset_value: float = 1.0

@dataclass
class CyberRiskMatrix:
    assessment_name: str
    vulnerabilities: List[Vulnerability] = field(default_factory=list)

    def risk_score(self, vuln: Vulnerability) -> float:
        return vuln.severity.value * vuln.likelihood.value * vuln.asset_value

    def total_risk_score(self) -> float:
        return sum(self.risk_score(v) for v in self.vulnerabilities)

    def risk_level(self, score: float) -> str:
        if score <= 4:
            return "low"
        elif score <= 9:
            return "medium"
        elif score <= 16:
            return "high"
        return "critical"

    def sorted_by_risk(self) -> List[Vulnerability]:
        return sorted(self.vulnerabilities, key=lambda v: self.risk_score(v), reverse=True)

    def by_risk_level(self) -> Dict[str, int]:
        counts = {}
        for v in self.vulnerabilities:
            level = self.risk_level(self.risk_score(v))
            counts[level] = counts.get(level, 0) + 1
        return counts

    def stats(self) -> Dict:
        return {
            "assessment": self.assessment_name,
            "vulnerabilities": len(self.vulnerabilities),
            "total_risk_score": round(self.total_risk_score(), 1),
            "by_risk_level": self.by_risk_level(),
            "top_risk": self.sorted_by_risk()[0].name if self.sorted_by_risk() else None,
        }

def run():
    crm = CyberRiskMatrix(
        assessment_name="Q2 Security Audit",
        vulnerabilities=[
            Vulnerability("SQL injection", Severity.CRITICAL, Likelihood.LIKELY, 5.0),
            Vulnerability("Outdated TLS", Severity.HIGH, Likelihood.POSSIBLE, 4.0),
            Vulnerability("Missing 2FA", Severity.MEDIUM, Likelihood.LIKELY, 3.0),
            Vulnerability("Weak password policy", Severity.MEDIUM, Likelihood.ALMOST_CERTAIN, 2.0),
            Vulnerability("Unpatched server", Severity.HIGH, Likelihood.LIKELY, 4.0),
        ]
    )
    print(crm.stats())

if __name__ == "__main__":
    run()

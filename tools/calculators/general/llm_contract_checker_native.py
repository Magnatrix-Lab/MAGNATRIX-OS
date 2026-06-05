"""Native stdlib module: Contract Checker
Validates contract clauses against standard templates and flags missing terms.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Set
from enum import Enum

class ClauseType(Enum):
    PAYMENT = "payment"
    TERMINATION = "termination"
    LIABILITY = "liability"
    CONFIDENTIALITY = "confidentiality"
    IP = "intellectual_property"
    FORCE_MAJEURE = "force_majeure"
    GOVERNING_LAW = "governing_law"

@dataclass
class ContractClause:
    clause_type: ClauseType
    present: bool
    risk_level: str = "low"

@dataclass
class ContractChecker:
    contract_name: str
    parties: List[str] = field(default_factory=list)
    clauses: List[ContractClause] = field(default_factory=list)
    required_clauses: List[ClauseType] = field(default_factory=lambda: list(ClauseType))

    def missing_clauses(self) -> List[ClauseType]:
        present = {c.clause_type for c in self.clauses if c.present}
        return [r for r in self.required_clauses if r not in present]

    def high_risk_count(self) -> int:
        return sum(1 for c in self.clauses if c.risk_level == "high")

    def coverage_pct(self) -> float:
        if not self.required_clauses:
            return 100.0
        present = sum(1 for c in self.clauses if c.present and c.clause_type in self.required_clauses)
        return (present / len(self.required_clauses)) * 100

    def stats(self) -> Dict:
        return {
            "contract": self.contract_name,
            "parties": self.parties,
            "coverage_pct": round(self.coverage_pct(), 1),
            "missing": [c.value for c in self.missing_clauses()],
            "high_risk_count": self.high_risk_count(),
        }

def run():
    cc = ContractChecker(
        contract_name="Service Agreement",
        parties=["Vendor A", "Client B"],
        clauses=[
            ContractClause(ClauseType.PAYMENT, True, "low"),
            ContractClause(ClauseType.TERMINATION, True, "medium"),
            ContractClause(ClauseType.LIABILITY, True, "high"),
            ContractClause(ClauseType.CONFIDENTIALITY, False, "high"),
            ContractClause(ClauseType.IP, True, "medium"),
            ContractClause(ClauseType.FORCE_MAJEURE, False, "low"),
            ContractClause(ClauseType.GOVERNING_LAW, True, "low"),
        ]
    )
    print(cc.stats())

if __name__ == "__main__":
    run()

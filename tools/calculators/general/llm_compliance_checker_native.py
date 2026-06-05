"""Compliance Checker — regulations, gaps, audit trail, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple

@dataclass
class Requirement:
    id: str
    regulation: str
    description: str
    mandatory: bool = True

class ComplianceChecker:
    def __init__(self):
        self.requirements: List[Requirement] = []
        self.evidence: Dict[str, List[str]] = {}

    def add_requirement(self, r: Requirement):
        self.requirements.append(r)

    def add_evidence(self, req_id: str, evidence: str):
        self.evidence.setdefault(req_id, []).append(evidence)

    def compliant(self, req_id: str) -> bool:
        return req_id in self.evidence and len(self.evidence[req_id]) > 0

    def gaps(self) -> List[str]:
        return [r.id for r in self.requirements if r.mandatory and not self.compliant(r.id)]

    def coverage(self) -> float:
        if not self.requirements:
            return 0.0
        met = sum(1 for r in self.requirements if self.compliant(r.id))
        return met / len(self.requirements)

    def audit_trail(self) -> Dict[str, List[str]]:
        return self.evidence

    def stats(self) -> Dict:
        return {"requirements": len(self.requirements), "coverage": round(self.coverage(), 3), "gaps": len(self.gaps())}

def run():
    cc = ComplianceChecker()
    cc.add_requirement(Requirement("R1", "GDPR", "Data protection", True))
    cc.add_requirement(Requirement("R2", "SOX", "Financial controls", True))
    cc.add_evidence("R1", "Privacy policy v2")
    print(cc.stats())
    print("Gaps:", cc.gaps())

if __name__ == "__main__":
    run()

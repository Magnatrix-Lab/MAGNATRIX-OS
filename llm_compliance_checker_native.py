"""Compliance Checker — rule validation, gap analysis, scoring, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto

class ComplianceRule:
    def __init__(self, rule_id: str, description: str, required: bool = True):
        self.rule_id = rule_id
        self.description = description
        self.required = required

class ComplianceChecker:
    def __init__(self):
        self.rules: List[ComplianceRule] = []
        self.checks: Dict[str, bool] = {}
        self.findings: List[Dict] = []

    def add_rule(self, rule: ComplianceRule):
        self.rules.append(rule)

    def check(self, evidence: Dict[str, bool]):
        self.checks = evidence
        self.findings = []
        for rule in self.rules:
            passed = evidence.get(rule.rule_id, False)
            if rule.required and not passed:
                self.findings.append({"rule": rule.rule_id, "status": "FAIL", "severity": "HIGH"})
            elif not passed:
                self.findings.append({"rule": rule.rule_id, "status": "FAIL", "severity": "MEDIUM"})

    def score(self) -> float:
        if not self.rules:
            return 100.0
        passed = sum(1 for r in self.rules if self.checks.get(r.rule_id, False))
        return (passed / len(self.rules)) * 100

    def gaps(self) -> List[str]:
        return [f["rule"] for f in self.findings if f["severity"] == "HIGH"]

    def stats(self) -> Dict:
        return {"rules": len(self.rules), "findings": len(self.findings), "score": self.score()}

def run():
    cc = ComplianceChecker()
    cc.add_rule(ComplianceRule("R1", "Data encryption required", True))
    cc.add_rule(ComplianceRule("R2", "Audit logging", True))
    cc.add_rule(ComplianceRule("R3", "Backup policy", False))
    cc.check({"R1": True, "R2": False, "R3": True})
    print(cc.findings)
    print(cc.score())
    print(cc.stats())

if __name__ == "__main__":
    run()

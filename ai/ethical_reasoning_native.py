#!/usr/bin/env python3
"""Ethical Reasoning Engine — MAGNATRIX-OS ASI Expansion
Path: ai/ethical_reasoning_native.py
License: AGPL-3.0
Depends: Python 3.11+ stdlib only.
"""

from __future__ import annotations
import logging, sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

@dataclass
class ActionProposal:
    action: str; affected: List[str]; benefits: float; harms: float; autonomy_impact: float

class EthicalFramework:
    """Evaluate actions against multiple ethical frameworks."""

    def utilitarian(self, proposal: ActionProposal) -> float:
        """Net utility = benefits - harms."""
        return proposal.benefits - proposal.harms

    def deontological(self, proposal: ActionProposal) -> bool:
        """Check if action violates any hard constraints (no deception, no coercion)."""
        forbidden = ["deceive", "coerce", "harm_innocent", "break_promise"]
        return not any(f in proposal.action.lower() for f in forbidden)

    def virtue_ethics(self, proposal: ActionProposal) -> float:
        """Score based on virtues promoted (courage, honesty, justice)."""
        virtues = ["help", "protect", "share", "truth", "fair"]
        return sum(1 for v in virtues if v in proposal.action.lower()) / len(virtues)

    def care_ethics(self, proposal: ActionProposal) -> float:
        """Prioritize actions that protect vulnerable affected parties."""
        if not proposal.affected: return 0.5
        # Higher score if harms are minimized for all
        return max(0.0, 1.0 - proposal.harms / max(len(proposal.affected), 1))

class EthicalReasoning:
    def __init__(self):
        self.framework = EthicalFramework()
        self.violations: List[str] = []

    def evaluate(self, proposal: ActionProposal) -> Dict[str, Any]:
        util = self.framework.utilitarian(proposal)
        deon = self.framework.deontological(proposal)
        virtue = self.framework.virtue_ethics(proposal)
        care = self.framework.care_ethics(proposal)

        # Weighted composite
        score = 0.3 * (1 if util > 0 else 0) + 0.3 * (1 if deon else 0) + 0.2 * virtue + 0.2 * care

        if not deon:
            self.violations.append(f"Deontological violation: {proposal.action}")

        return {
            "action": proposal.action,
            "utilitarian": util,
            "deontological": deon,
            "virtue": virtue,
            "care": care,
            "composite_score": score,
            "approved": score > 0.5 and deon,
        }

    def compare(self, proposals: List[ActionProposal]) -> List[Dict[str, Any]]:
        results = [self.evaluate(p) for p in proposals]
        return sorted(results, key=lambda r: -r["composite_score"])

def _self_test():
    print("=" * 55)
    print("Ethical Reasoning — Self Test")
    print("=" * 55)
    er = EthicalReasoning()
    passed, total = 0, 5

    p1 = ActionProposal("help_person", ["A"], 10.0, 0.0, 0.0)
    r1 = er.evaluate(p1)
    ok = r1["approved"] == True
    print(f"  [Test 1] Help approved: {r1['approved']} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    p2 = ActionProposal("deceive_user", ["B"], 5.0, 1.0, -1.0)
    r2 = er.evaluate(p2)
    ok = r2["approved"] == False
    print(f"  [Test 2] Deceive blocked: {r2['approved']} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    p3 = ActionProposal("share_resource", ["A", "B", "C"], 3.0, 0.0, 0.0)
    p4 = ActionProposal("harm_innocent", ["A"], 0.0, 10.0, -1.0)
    ranked = er.compare([p4, p3])
    ok = ranked[0]["action"] == "share_resource"
    print(f"  [Test 3] Ranking: {ranked[0]['action']} first — {'PASS' if ok else 'FAIL'}")
    passed += ok

    ok = len(er.violations) >= 1
    print(f"  [Test 4] Violations logged: {len(er.violations)} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    ok = 0 <= r1["composite_score"] <= 1
    print(f"  [Test 5] Score in [0,1]: {r1['composite_score']:.2f} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    print("=" * 55)
    print(f"PASS: {passed}/{total} tests")
    print("=" * 55)
    sys.exit(0 if passed == total else 1)

if __name__ == "__main__":
    _self_test()

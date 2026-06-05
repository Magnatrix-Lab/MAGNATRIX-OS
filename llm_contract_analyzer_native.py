"""Contract Analyzer — clauses, risk, obligations, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
import re

@dataclass
class ContractAnalyzer:
    text: str = ""
    clauses: List[Dict] = field(default_factory=list)

    def extract_clauses(self) -> List[Dict]:
        patterns = {
            "termination": r'terminat[^.]*',
            "payment": r'payment|fee|compensation[^.]*',
            "liability": r'liabilit|indemnif|warrant[^.]*',
            "confidentiality": r'confidential|non-disclosure|NDA[^.]*',
            "governing_law": r'govern[^.]*law|jurisdiction[^.]*'
        }
        found = []
        for ctype, pattern in patterns.items():
            for m in re.finditer(pattern, self.text, re.IGNORECASE):
                found.append({"type": ctype, "text": m.group()[:100], "pos": m.start()})
        return found

    def risk_score(self) -> float:
        risks = 0
        if "unlimited liability" in self.text.lower():
            risks += 3
        if "no termination" in self.text.lower():
            risks += 2
        if "as is" in self.text.lower():
            risks += 1
        return risks

    def obligations(self) -> List[str]:
        return re.findall(r'(?:shall|must|will|agrees to) ([^.]+)', self.text, re.IGNORECASE)

    def missing_clauses(self, expected: List[str]) -> List[str]:
        text_lower = self.text.lower()
        return [e for e in expected if e.lower() not in text_lower]

    def stats(self) -> Dict:
        return {"clauses": len(self.extract_clauses()), "risk": self.risk_score(), "obligations": len(self.obligations())}

def run():
    ca = ContractAnalyzer("The Party shall pay fees within 30 days. This agreement is governed by New York law. The Provider warrants the service.")
    print(ca.stats())
    print("Missing:", ca.missing_clauses(["confidentiality", "termination", "liability"]))

if __name__ == "__main__":
    run()

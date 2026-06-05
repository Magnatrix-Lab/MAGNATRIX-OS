"""Fact Checker — claim extraction, source matching, credibility, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
import re

@dataclass
class FactChecker:
    claims: List[str] = field(default_factory=list)
    sources: Dict[str, str] = field(default_factory=dict)
    """claim -> source verdict"""

    def extract_claims(self, text: str) -> List[str]:
        sentences = re.split(r'[.!?]', text)
        claims = []
        for s in sentences:
            s = s.strip()
            if any(w in s.lower() for w in ["is", "are", "was", "were", "has", "have"]):
                if len(s) > 10:
                    claims.append(s)
        return claims

    def match_source(self, claim: str) -> Optional[str]:
        for known, verdict in self.sources.items():
            if any(word in claim.lower() for word in known.lower().split()):
                return verdict
        return None

    def credibility_score(self, sources: List[str]) -> float:
        if not sources:
            return 0.0
        high_cred = ["peer_reviewed", "government", "official"]
        return sum(1 for s in sources if s in high_cred) / len(sources)

    def check(self, text: str) -> List[Dict]:
        claims = self.extract_claims(text)
        results = []
        for c in claims:
            verdict = self.match_source(c)
            results.append({"claim": c, "verdict": verdict or "unverified"})
        return results

    def stats(self, text: str) -> Dict:
        results = self.check(text)
        return {"claims": len(results), "verified": sum(1 for r in results if r["verdict"] != "unverified")}

def run():
    fc = FactChecker()
    fc.sources["earth is round"] = "verified"
    fc.sources["water boils"] = "verified"
    text = "The earth is round. Water boils at 100 degrees. Aliens exist."
    print(fc.check(text))
    print(fc.stats(text))

if __name__ == "__main__":
    run()

"""DNA Profiler — STR, CODIS, allele matching, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class DNAProfiler:
    profile: Dict[str, List[int]] = field(default_factory=dict)
    """locus -> alleles"""

    def add_locus(self, locus: str, alleles: List[int]):
        self.profile[locus] = alleles

    def match(self, other: 'DNAProfiler') -> float:
        if not self.profile or not other.profile:
            return 0.0
        matches = 0
        total = 0
        for locus, alleles in self.profile.items():
            other_alleles = other.profile.get(locus, [])
            total += len(alleles)
            matches += sum(1 for a in alleles if a in other_alleles)
        return matches / total if total > 0 else 0.0

    def random_match_prob(self, locus_freqs: Dict[str, Dict[int, float]]) -> float:
        prob = 1.0
        for locus, alleles in self.profile.items():
            freqs = locus_freqs.get(locus, {})
            locus_prob = 0.0
            for a in alleles:
                f = freqs.get(a, 0.01)
                locus_prob += f
            if locus_prob > 0:
                prob *= locus_prob
        return prob

    def stats(self) -> Dict:
        return {"loci": len(self.profile), "alleles": sum(len(v) for v in self.profile.values())}

def run():
    dp = DNAProfiler()
    dp.add_locus("D3S1358", [15, 17])
    dp.add_locus("vWA", [16, 18])
    dp2 = DNAProfiler()
    dp2.add_locus("D3S1358", [15, 17])
    dp2.add_locus("vWA", [16, 19])
    print("Match:", dp.match(dp2))
    print(dp.stats())

if __name__ == "__main__":
    run()

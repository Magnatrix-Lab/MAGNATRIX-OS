"""Native stdlib module: DNA Match Calculator
Calculates DNA match probabilities, LR, and exclusion probabilities.
"""
from dataclasses import dataclass, field
from typing import List, Dict
import math

@dataclass
class LocusData:
    locus_name: str
    suspect_alleles: List[float]
    evidence_alleles: List[float]
    population_freq: float

@dataclass
class DNAMatchCalculator:
    case_id: str
    loci: List[LocusData] = field(default_factory=list)

    def match_probability(self) -> float:
        if not self.loci:
            return 0.0
        prob = 1.0
        for locus in self.loci:
            matching = sum(1 for a in locus.suspect_alleles if a in locus.evidence_alleles)
            if matching > 0:
                prob *= locus.population_freq ** matching
            else:
                return 0.0
        return prob

    def match_probability_formatted(self) -> str:
        prob = self.match_probability()
        if prob == 0:
            return "0"
        return f"1 in {1/prob:.0e}"

    def lr(self, relatedness: float = 0.5) -> float:
        prob = self.match_probability()
        if prob == 0:
            return float('inf')
        return relatedness / prob

    def exclusion_probability(self) -> float:
        prob = self.match_probability()
        return 1 - prob

    def matching_loci(self) -> int:
        matches = 0
        for locus in self.loci:
            if any(a in locus.evidence_alleles for a in locus.suspect_alleles):
                matches += 1
        return matches

    def total_loci(self) -> int:
        return len(self.loci)

    def stats(self) -> Dict:
        return {
            "case_id": self.case_id,
            "total_loci": self.total_loci(),
            "matching_loci": self.matching_loci(),
            "match_probability": self.match_probability_formatted(),
            "exclusion_probability": round(self.exclusion_probability(), 10),
            "lr": round(self.lr(), 2) if self.lr() != float('inf') else "inf",
        }

def run():
    dna = DNAMatchCalculator(
        case_id="CASE-2024-002",
        loci=[
            LocusData("D3S1358", [15, 17], [15, 17], 0.05),
            LocusData("vWA", [16, 18], [16, 18], 0.08),
            LocusData("FGA", [22, 24], [22, 24], 0.03),
            LocusData("D8S1179", [12, 13], [12, 13], 0.10),
            LocusData("D21S11", [30, 31], [30, 31], 0.04),
        ]
    )
    print(dna.stats())

if __name__ == "__main__":
    run()

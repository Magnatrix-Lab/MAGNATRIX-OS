"""Taxonomy Classifier — kingdom, phylum, hierarchy, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class TaxonomyClassifier:
    hierarchy: Dict[str, List[str]] = field(default_factory=dict)
    """rank -> [taxa]"""

    def add_entry(self, rank: str, taxon: str):
        self.hierarchy.setdefault(rank, []).append(taxon)

    def lineage(self, species: str, data: Dict[str, str]) -> List[str]:
        ranks = ["kingdom", "phylum", "class", "order", "family", "genus", "species"]
        return [data.get(r, "") for r in ranks if data.get(r)]

    def rank_count(self) -> Dict[str, int]:
        return {rank: len(taxa) for rank, taxa in self.hierarchy.items()}

    def find_by_rank(self, rank: str) -> List[str]:
        return self.hierarchy.get(rank, [])

    def is_valid(self, lineage: List[str]) -> bool:
        return len(lineage) >= 3 and all(lineage)

    def stats(self) -> Dict:
        return {"ranks": len(self.hierarchy), "total_taxa": sum(len(t) for t in self.hierarchy.values())}

def run():
    tc = TaxonomyClassifier()
    tc.add_entry("kingdom", "Animalia")
    tc.add_entry("phylum", "Chordata")
    tc.add_entry("class", "Mammalia")
    print(tc.stats())
    print("Lineage:", tc.lineage("Canis lupus", {"kingdom": "Animalia", "phylum": "Chordata", "class": "Mammalia", "species": "Canis lupus"}))

if __name__ == "__main__":
    run()

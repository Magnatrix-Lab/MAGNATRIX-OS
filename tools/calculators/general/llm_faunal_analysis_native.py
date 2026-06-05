"""Native stdlib module: Faunal Analysis Calculator
Analyzes faunal remains by NISP, MNI, and species diversity.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class ElementType(Enum):
    CRANIUM = "cranium"
    MANDIBLE = "mandible"
    VERTEBRA = "vertebra"
    RIB = "rib"
    LONG_BONE = "long_bone"
    TOOTH = "tooth"

@dataclass
class FaunalElement:
    species: str
    element_type: ElementType
    count: int
    side: str = "unknown"

@dataclass
class FaunalAnalysisCalculator:
    site_name: str
    elements: List[FaunalElement] = field(default_factory=list)

    def nisp(self) -> int:
        return sum(e.count for e in self.elements)

    def mni(self) -> int:
        by_species_side = {}
        for e in self.elements:
            key = f"{e.species}:{e.side}"
            by_species_side[key] = by_species_side.get(key, 0) + e.count
        return sum(by_species_side.values())

    def species_list(self) -> List[str]:
        return sorted(set(e.species for e in self.elements))

    def species_count(self) -> int:
        return len(self.species_list())

    def by_species(self) -> Dict[str, int]:
        counts = {}
        for e in self.elements:
            counts[e.species] = counts.get(e.species, 0) + e.count
        return counts

    def by_element_type(self) -> Dict[str, int]:
        counts = {}
        for e in self.elements:
            counts[e.element_type.value] = counts.get(e.element_type.value, 0) + e.count
        return counts

    def stats(self) -> Dict:
        return {
            "site": self.site_name,
            "nisp": self.nisp(),
            "mni": self.mni(),
            "species_count": self.species_count(),
            "species": self.species_list(),
            "by_species": self.by_species(),
            "by_element": self.by_element_type(),
        }

def run():
    fac = FaunalAnalysisCalculator(
        site_name="Rock Shelter",
        elements=[
            FaunalElement("deer", ElementType.MANDIBLE, 3, "left"),
            FaunalElement("deer", ElementType.MANDIBLE, 2, "right"),
            FaunalElement("rabbit", ElementType.LONG_BONE, 8, "unknown"),
            FaunalElement("rabbit", ElementType.VERTEBRA, 12, "unknown"),
            FaunalElement("turkey", ElementType.LONG_BONE, 4, "left"),
            FaunalElement("turkey", ElementType.LONG_BONE, 3, "right"),
        ]
    )
    print(fac.stats())

if __name__ == "__main__":
    run()

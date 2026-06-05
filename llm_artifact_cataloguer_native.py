"""Native stdlib module: Artifact Cataloguer
Catalogs artifacts by type, dimensions, condition, and provenance.
"""
from dataclasses import dataclass, field
from typing import List, Dict
from enum import Enum

class Condition(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    FRAGMENTARY = "fragmentary"

class ArtifactType(Enum):
    POTTERY = "pottery"
    LITHIC = "lithic"
    METAL = "metal"
    BONE = "bone"
    TEXTILE = "textile"
    GLASS = "glass"

@dataclass
class Artifact:
    artifact_id: str
    artifact_type: ArtifactType
    condition: Condition
    length_mm: float
    width_mm: float
    weight_g: float
    site: str
    context: str

@dataclass
class ArtifactCataloguer:
    collection_name: str
    artifacts: List[Artifact] = field(default_factory=list)

    def total_count(self) -> int:
        return len(self.artifacts)

    def by_type(self) -> Dict[str, int]:
        counts = {}
        for a in self.artifacts:
            counts[a.artifact_type.value] = counts.get(a.artifact_type.value, 0) + 1
        return counts

    def by_condition(self) -> Dict[str, int]:
        counts = {}
        for a in self.artifacts:
            counts[a.condition.value] = counts.get(a.condition.value, 0) + 1
        return counts

    def total_weight_g(self) -> float:
        return sum(a.weight_g for a in self.artifacts)

    def avg_dimensions(self) -> Dict[str, float]:
        if not self.artifacts:
            return {}
        return {
            "avg_length_mm": round(sum(a.length_mm for a in self.artifacts) / len(self.artifacts), 1),
            "avg_width_mm": round(sum(a.width_mm for a in self.artifacts) / len(self.artifacts), 1),
            "avg_weight_g": round(sum(a.weight_g for a in self.artifacts) / len(self.artifacts), 1),
        }

    def stats(self) -> Dict:
        return {
            "collection": self.collection_name,
            "total_artifacts": self.total_count(),
            "by_type": self.by_type(),
            "by_condition": self.by_condition(),
            "total_weight_g": round(self.total_weight_g(), 1),
            "avg_dimensions": self.avg_dimensions(),
        }

def run():
    ac = ArtifactCataloguer(
        collection_name="Site B Excavation",
        artifacts=[
            Artifact("A-001", ArtifactType.POTTERY, Condition.GOOD, 120, 80, 250, "Site B", "Midden"),
            Artifact("A-002", ArtifactType.LITHIC, Condition.FAIR, 45, 25, 35, "Site B", "Hearth"),
            Artifact("A-003", ArtifactType.BONE, Condition.POOR, 60, 20, 15, "Site B", "Midden"),
            Artifact("A-004", ArtifactType.METAL, Condition.EXCELLENT, 30, 15, 40, "Site B", "Burial"),
            Artifact("A-005", ArtifactType.POTTERY, Condition.FRAGMENTARY, 50, 30, 80, "Site B", "Midden"),
        ]
    )
    print(ac.stats())

if __name__ == "__main__":
    run()

"""Artifact Classifier — typology, material detection, period assignment, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Set
from enum import Enum, auto
from math import sqrt, pow, radians, degrees, sin, cos, atan2, pi, fabs, exp, log
from datetime import datetime, timedelta

class MaterialType(Enum):
    CERAMIC = auto()
    STONE = auto()
    METAL = auto()
    BONE = auto()
    WOOD = auto()
    GLASS = auto()
    TEXTILE = auto()
    ORGANIC = auto()

class Period(Enum):
    PREHISTORIC = auto()
    ANCIENT = auto()
    CLASSICAL = auto()
    MEDIEVAL = auto()
    POST_MEDIEVAL = auto()
    MODERN = auto()

@dataclass
class ArtifactFeature:
    name: str
    value: float  # normalized 0-1
    weight: float = 1.0

@dataclass
class Artifact:
    id: str
    features: List[ArtifactFeature] = field(default_factory=list)
    material: Optional[MaterialType] = None
    period: Optional[Period] = None
    dimensions: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # l, w, h cm
    weight_g: float = 0.0
    provenance: str = ""

    @property
    def volume(self) -> float:
        return self.dimensions[0] * self.dimensions[1] * self.dimensions[2]

    @property
    def density(self) -> float:
        return self.weight_g / self.volume if self.volume > 0 else 0.0

    def similarity(self, other: 'Artifact') -> float:
        """Cosine similarity of feature vectors."""
        if not self.features or not other.features:
            return 0.0
        feat_map = {f.name: f.value * f.weight for f in self.features}
        other_map = {f.name: f.value * f.weight for f in other.features}
        all_keys = set(feat_map.keys()) | set(other_map.keys())
        dot = sum(feat_map.get(k, 0) * other_map.get(k, 0) for k in all_keys)
        norm1 = sqrt(sum(v**2 for v in feat_map.values()))
        norm2 = sqrt(sum(v**2 for v in other_map.values()))
        return dot / (norm1 * norm2) if norm1 > 0 and norm2 > 0 else 0.0

class ArtifactClassifier:
    def __init__(self):
        self.artifacts: List[Artifact] = []
        self.type_database: Dict[str, Dict] = {}

    def add_artifact(self, artifact: Artifact) -> None:
        self.artifacts.append(artifact)

    def add_type(self, name: str, material: MaterialType, period: Period, features: List[ArtifactFeature]) -> None:
        self.type_database[name] = {"material": material, "period": period, "features": features}

    def classify(self, artifact: Artifact) -> List[Tuple[str, float]]:
        """Return top matches with similarity scores."""
        scores = []
        for type_name, data in self.type_database.items():
            temp = Artifact("temp", features=data["features"])
            sim = artifact.similarity(temp)
            scores.append((type_name, sim))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores

    def assign_material(self, artifact: Artifact) -> MaterialType:
        """Assign material based on density and features."""
        if artifact.density < 0.5:
            return MaterialType.ORGANIC
        elif artifact.density < 1.5:
            return MaterialType.CERAMIC
        elif artifact.density < 3.0:
            return MaterialType.STONE
        elif artifact.density < 7.0:
            return MaterialType.GLASS
        elif artifact.density < 12.0:
            return MaterialType.BONE
        return MaterialType.METAL

    def group_by_similarity(self, threshold: float = 0.7) -> List[List[Artifact]]:
        groups: List[List[Artifact]] = []
        for a in self.artifacts:
            found = False
            for g in groups:
                if a.similarity(g[0]) >= threshold:
                    g.append(a)
                    found = True
                    break
            if not found:
                groups.append([a])
        return groups

    def stats(self) -> Dict[str, float]:
        by_material = {}
        by_period = {}
        for a in self.artifacts:
            mat = a.material.name if a.material else "UNKNOWN"
            per = a.period.name if a.period else "UNKNOWN"
            by_material[mat] = by_material.get(mat, 0) + 1
            by_period[per] = by_period.get(per, 0) + 1
        return {
            "artifact_count": len(self.artifacts),
            "type_database_count": len(self.type_database),
            "material_categories": len(by_material),
            "period_categories": len(by_period)
        }

def run():
    clf = ArtifactClassifier()
    clf.add_type("amphora", MaterialType.CERAMIC, Period.ANCIENT, [
        ArtifactFeature("curvature", 0.8), ArtifactFeature("thickness", 0.3), ArtifactFeature("glaze", 0.2)
    ])
    clf.add_type("sword", MaterialType.METAL, Period.MEDIEVAL, [
        ArtifactFeature("elongation", 0.9), ArtifactFeature("hardness", 0.8), ArtifactFeature("edge_sharpness", 0.7)
    ])
    art = Artifact("A1", features=[
        ArtifactFeature("curvature", 0.75), ArtifactFeature("thickness", 0.35), ArtifactFeature("glaze", 0.15)
    ], dimensions=(30, 20, 15), weight_g=800, provenance="Mediterranean")
    print(f"Classify result: {clf.classify(art)}")
    print(f"Assigned material: {clf.assign_material(art).name}")
    print(clf.stats())

if __name__ == "__main__":
    run()

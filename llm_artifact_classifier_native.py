"""Artifact Classifier — typology, material, function, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple

@dataclass
class Artifact:
    id: str
    dimensions: Tuple[float, float, float]
    material: str
    features: List[str] = field(default_factory=list)

class ArtifactClassifier:
    def __init__(self):
        self.artifacts: List[Artifact] = []
        self.typologies: Dict[str, List[str]] = {}

    def add_artifact(self, a: Artifact):
        self.artifacts.append(a)

    def classify_by_material(self, material: str) -> List[Artifact]:
        return [a for a in self.artifacts if a.material == material]

    def classify_by_feature(self, feature: str) -> List[Artifact]:
        return [a for a in self.artifacts if feature in a.features]

    def function_hypothesis(self, a: Artifact) -> str:
        if "edge" in a.features and "handle" in a.features:
            return "tool"
        if "opening" in a.features and "base" in a.features:
            return "container"
        if "decoration" in a.features:
            return "ornament"
        return "unknown"

    def similarity(self, a1: Artifact, a2: Artifact) -> float:
        shared = len(set(a1.features) & set(a2.features))
        total = len(set(a1.features) | set(a2.features))
        return shared / total if total > 0 else 0.0

    def stats(self) -> Dict:
        materials = set(a.material for a in self.artifacts)
        return {"artifacts": len(self.artifacts), "materials": len(materials)}

def run():
    ac = ArtifactClassifier()
    ac.add_artifact(Artifact("A1", (10, 5, 2), "stone", ["edge", "handle", "polished"]))
    ac.add_artifact(Artifact("A2", (8, 8, 10), "clay", ["opening", "base", "decoration"]))
    ac.add_artifact(Artifact("A3", (10, 5, 2), "stone", ["edge", "handle"]))
    print(ac.stats())
    print("Similarity A1-A3:", ac.similarity(ac.artifacts[0], ac.artifacts[2]))
    print("Function A1:", ac.function_hypothesis(ac.artifacts[0]))

if __name__ == "__main__":
    run()

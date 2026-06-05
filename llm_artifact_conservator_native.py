"""Artifact Conservator — condition, storage, monitoring, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class ArtifactConservator:
    artifacts: List[Dict] = field(default_factory=list)
    """Each: {id, material, condition, age, humidity_exposure}"""

    def condition_score(self, artifact: Dict) -> float:
        base = 10.0
        age_factor = min(5, artifact.get("age", 0) / 10)
        condition_map = {"excellent": 0, "good": 1, "fair": 2, "poor": 3, "critical": 5}
        cond = condition_map.get(artifact.get("condition", "fair"), 2)
        humidity = artifact.get("humidity_exposure", 0) * 0.5
        return max(0, base - age_factor - cond - humidity)

    def priority_queue(self) -> List[str]:
        scored = [(a["id"], self.condition_score(a)) for a in self.artifacts]
        scored.sort(key=lambda x: x[1])
        return [s[0] for s in scored]

    def storage_recommendation(self, artifact: Dict) -> Dict:
        material = artifact.get("material", "")
        if material in ["paper", "textile"]:
            return {"temp_c": 18, "rh_pct": 50, "light_lux": 50}
        elif material in ["metal"]:
            return {"temp_c": 20, "rh_pct": 40, "light_lux": 200}
        elif material in ["wood"]:
            return {"temp_c": 20, "rh_pct": 55, "light_lux": 150}
        return {"temp_c": 20, "rh_pct": 50, "light_lux": 150}

    def degradation_rate(self, artifact: Dict) -> float:
        score = self.condition_score(artifact)
        return max(0, (10 - score) / 10)

    def stats(self) -> Dict:
        return {"artifacts": len(self.artifacts), "avg_condition": sum(self.condition_score(a) for a in self.artifacts) / len(self.artifacts) if self.artifacts else 0}

def run():
    ac = ArtifactConservator()
    ac.artifacts = [{"id": "A1", "material": "paper", "condition": "fair", "age": 50, "humidity_exposure": 2}]
    ac.artifacts.append({"id": "A2", "material": "metal", "condition": "good", "age": 100, "humidity_exposure": 1})
    print(ac.stats())
    print("Priority:", ac.priority_queue())
    print("Storage A1:", ac.storage_recommendation(ac.artifacts[0]))

if __name__ == "__main__":
    run()

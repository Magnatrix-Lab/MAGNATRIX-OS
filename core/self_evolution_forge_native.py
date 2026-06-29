"""
self_evolution_forge_native.py
MAGNATRIX-OS — Self-Evolution Forge

Inspired by telagod/code-abyss self-evolution forge:
Distill repeated workflows into reusable skills and personas with safety scanning. Pure stdlib.
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class CultivatedArtifact:
    artifact_id: str
    artifact_type: str  # skill or persona
    source_workflows: List[str]
    distilled_content: str
    safety_score: float
    publish_tier: str  # local, project, community
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class SelfEvolutionForge:
    """Distill repeated workflows into reusable skills and personas."""

    def __init__(self, forge_dir: str = "./forge"):
        self.forge_dir = Path(forge_dir)
        self.forge_dir.mkdir(exist_ok=True)
        self.artifacts: Dict[str, CultivatedArtifact] = {}
        self._load()

    def _load(self) -> None:
        file = self.forge_dir / "artifacts.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for aid, ad in data.items():
                        self.artifacts[aid] = CultivatedArtifact(**ad)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.forge_dir / "artifacts.json", "w", encoding="utf-8") as f:
            json.dump({k: asdict(v) for k, v in self.artifacts.items()}, f, indent=2)

    def _hash_workflows(self, workflows: List[str]) -> str:
        combined = "|".join(sorted(workflows))
        return hashlib.md5(combined.encode()).hexdigest()[:8]

    def _safety_scan(self, content: str) -> float:
        """Scan content for safety issues. Returns score 0-1."""
        # Simple heuristic: check for dangerous patterns
        dangerous = ["rm -rf", "drop database", "delete from", "exec(", "eval("]
        score = 1.0
        for pattern in dangerous:
            if pattern.lower() in content.lower():
                score -= 0.2
        return max(0.0, score)

    def distill_skill(self, source_workflows: List[str], skill_name: str) -> Optional[CultivatedArtifact]:
        """Distill repeated workflows into a skill."""
        artifact_id = f"skill_{self._hash_workflows(source_workflows)}"
        # Extract common patterns
        common = self._extract_common_patterns(source_workflows)
        content = f"## {skill_name}\n\n### Common Patterns\n{common}\n\n### Usage\nApply this pattern when encountering similar workflows."
        safety = self._safety_scan(content)
        tier = "local" if safety < 0.8 else "project"
        artifact = CultivatedArtifact(
            artifact_id=artifact_id, artifact_type="skill",
            source_workflows=source_workflows, distilled_content=content,
            safety_score=round(safety, 2), publish_tier=tier,
        )
        self.artifacts[artifact_id] = artifact
        self._save()
        return artifact

    def distill_persona(self, interaction_logs: List[str], persona_name: str) -> Optional[CultivatedArtifact]:
        """Distill voice from interaction logs into a persona."""
        artifact_id = f"persona_{self._hash_workflows(interaction_logs)}"
        # Extract voice patterns
        voice = self._extract_voice_patterns(interaction_logs)
        content = f"## {persona_name}\n\n### Voice Characteristics\n{voice}\n\n### Apply This Persona When\n- Similar contexts to source interactions"
        safety = self._safety_scan(content)
        artifact = CultivatedArtifact(
            artifact_id=artifact_id, artifact_type="persona",
            source_workflows=interaction_logs, distilled_content=content,
            safety_score=round(safety, 2), publish_tier="local",
        )
        self.artifacts[artifact_id] = artifact
        self._save()
        return artifact

    def _extract_common_patterns(self, workflows: List[str]) -> str:
        if not workflows:
            return "No patterns found"
        # Simple: find common substrings
        common = workflows[0]
        for w in workflows[1:]:
            # Find longest common substring (simplified)
            min_len = min(len(common), len(w))
            for i in range(min_len, 0, -1):
                if common[:i] == w[:i]:
                    common = common[:i]
                    break
        return common[:200] if common else "No common patterns detected"

    def _extract_voice_patterns(self, logs: List[str]) -> str:
        if not logs:
            return "No voice patterns found"
        # Extract common greetings, sign-offs, and phrasing
        words = []
        for log in logs:
            words.extend(log.split()[:10])  # First 10 words
        word_freq = {}
        for w in words:
            word_freq[w] = word_freq.get(w, 0) + 1
        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:5]
        return f"Frequently used: {', '.join(w for w, _ in top_words)}"

    def promote(self, artifact_id: str, target_tier: str) -> bool:
        artifact = self.artifacts.get(artifact_id)
        if not artifact:
            return False
        tiers = ["local", "project", "community"]
        if tiers.index(target_tier) < tiers.index(artifact.publish_tier):
            return False
        if artifact.safety_score < 0.8 and target_tier == "community":
            return False
        artifact.publish_tier = target_tier
        self._save()
        return True

    def get_artifacts(self, artifact_type: Optional[str] = None) -> List[CultivatedArtifact]:
        if artifact_type:
            return [a for a in self.artifacts.values() if a.artifact_type == artifact_type]
        return list(self.artifacts.values())

    def get_stats(self) -> Dict[str, Any]:
        skills = sum(1 for a in self.artifacts.values() if a.artifact_type == "skill")
        personas = sum(1 for a in self.artifacts.values() if a.artifact_type == "persona")
        return {"total_artifacts": len(self.artifacts), "skills": skills, "personas": personas}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["SelfEvolutionForge", "CultivatedArtifact"]
"""
skill_search_engine_native.py
MAGNATRIX-OS — Skill Search Engine

Inspired by AgentSkillOS: Multi-layer search (active/dormant/vector) for skill discovery. Pure stdlib.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class SearchResult:
    skill_id: str
    name: str
    relevance: float
    layer: str  # active, dormant, vector
    matched_terms: List[str]


class SkillSearchEngine:
    """Multi-layer search for skill discovery across active, dormant, and vector layers."""

    def __init__(self, cache_dir: str = "./skill_search"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.active_skills: Dict[str, Dict[str, Any]] = {}
        self.dormant_skills: Dict[str, Dict[str, Any]] = {}
        self.vector_index: Dict[str, List[float]] = {}
        self._load()

    def _load(self) -> None:
        for fname, attr in [("active.json", "active_skills"), ("dormant.json", "dormant_skills"), ("vector.json", "vector_index")]:
            f = self.cache_dir / fname
            if f.exists():
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        setattr(self, attr, json.load(fp))
                except Exception:
                    pass

    def _save(self) -> None:
        with open(self.cache_dir / "active.json", "w", encoding="utf-8") as f:
            json.dump(self.active_skills, f, indent=2)
        with open(self.cache_dir / "dormant.json", "w", encoding="utf-8") as f:
            json.dump(self.dormant_skills, f, indent=2)
        with open(self.cache_dir / "vector.json", "w", encoding="utf-8") as f:
            json.dump(self.vector_index, f, indent=2)

    def index_skill(self, skill_id: str, name: str, description: str, tags: List[str], layer: str = "active") -> None:
        skill = {"skill_id": skill_id, "name": name, "description": description, "tags": tags}
        if layer == "active":
            self.active_skills[skill_id] = skill
        else:
            self.dormant_skills[skill_id] = skill
        # Simple vector: keyword presence vector
        self.vector_index[skill_id] = self._simple_vector(name + " " + description + " " + " ".join(tags))
        self._save()

    def _simple_vector(self, text: str) -> List[float]:
        """Create a simple keyword frequency vector."""
        words = re.findall(r'\w+', text.lower())
        vocab = list(set(words))
        return [words.count(w) for w in vocab]

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        if not a or not b:
            return 0.0
        min_len = min(len(a), len(b))
        a, b = a[:min_len], b[:min_len]
        dot = sum(x * y for x, y in zip(a, b))
        mag_a = sum(x * x for x in a) ** 0.5
        mag_b = sum(x * x for x in b) ** 0.5
        if mag_a == 0 or mag_b == 0:
            return 0.0
        return dot / (mag_a * mag_b)

    def search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        q_words = re.findall(r'\w+', query.lower())
        q_vector = [q_words.count(w) for w in list(set(q_words))]
        results = []

        for layer, skills in [("active", self.active_skills), ("dormant", self.dormant_skills)]:
            for skill_id, skill in skills.items():
                text = skill.get("name", "") + " " + skill.get("description", "") + " " + " ".join(skill.get("tags", []))
                text_lower = text.lower()
                matched = [w for w in q_words if w in text_lower]
                relevance = len(matched) / max(1, len(q_words))

                # Boost with vector similarity
                v = self.vector_index.get(skill_id, [])
                if v and q_vector:
                    sim = self._cosine_similarity(q_vector[:len(v)], v[:len(q_vector)])
                    relevance = relevance * 0.5 + sim * 0.5

                if relevance > 0:
                    results.append(SearchResult(
                        skill_id=skill_id, name=skill.get("name", ""), relevance=round(relevance, 4),
                        layer=layer, matched_terms=matched,
                    ))

        results.sort(key=lambda x: x.relevance, reverse=True)
        return results[:top_k]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "active": len(self.active_skills), "dormant": len(self.dormant_skills),
            "vector_indexed": len(self.vector_index),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["SkillSearchEngine", "SearchResult"]
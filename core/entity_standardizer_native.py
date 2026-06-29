"""
entity_standardizer_native.py
MAGNATRIX-OS — Entity Standardizer

Inspired by ai-knowledge-graph: Entity standardization and resolution across extracted triples. Pure stdlib.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class EntityMapping:
    canonical: str
    variants: List[str]
    entity_type: str


class EntityStandardizer:
    """Standardize entity names across extracted triples."""

    def __init__(self, cache_dir: str = "./entity_standardizer"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.mappings: Dict[str, EntityMapping] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "mappings.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for cid, cd in data.items():
                        self.mappings[cid] = EntityMapping(**cd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "mappings.json", "w", encoding="utf-8") as f:
            json.dump({cid: asdict(m) for cid, m in self.mappings.items()}, f, indent=2)

    def _normalize(self, text: str) -> str:
        """Normalize text for comparison."""
        text = re.sub(r'[^\w\s]', '', text.lower())
        return text.strip()

    def _similarity(self, a: str, b: str) -> float:
        """Simple Jaccard similarity for entity matching."""
        words_a = set(self._normalize(a).split())
        words_b = set(self._normalize(b).split())
        if not words_a or not words_b:
            return 0.0
        intersection = len(words_a & words_b)
        union = len(words_a | words_b)
        return intersection / union

    def find_groups(self, entities: List[str], threshold: float = 0.6) -> List[List[str]]:
        """Group similar entities together."""
        groups = []
        used = set()
        for i, entity in enumerate(entities):
            if i in used:
                continue
            group = [entity]
            used.add(i)
            for j, other in enumerate(entities):
                if j not in used and j != i:
                    sim = self._similarity(entity, other)
                    if sim >= threshold:
                        group.append(other)
                        used.add(j)
            groups.append(group)
        return groups

    def standardize(self, entities: List[str]) -> Dict[str, str]:
        """Create canonical mappings for entities."""
        groups = self.find_groups(entities)
        mappings = {}
        for group in groups:
            canonical = min(group, key=len)  # shortest as canonical
            mapping = EntityMapping(
                canonical=canonical, variants=[e for e in group if e != canonical],
                entity_type="unknown",
            )
            self.mappings[canonical] = mapping
            for entity in group:
                mappings[entity] = canonical
        self._save()
        return mappings

    def apply(self, triples: List[Any]) -> List[Any]:
        """Apply standardization to triples."""
        entities = []
        for t in triples:
            entities.append(t.subject)
            entities.append(t.object)
        mappings = self.standardize(entities)
        for t in triples:
            t.subject = mappings.get(t.subject, t.subject)
            t.object = mappings.get(t.object, t.object)
        return triples

    def get_stats(self) -> Dict[str, Any]:
        total_variants = sum(len(m.variants) for m in self.mappings.values())
        return {"canonical_entities": len(self.mappings), "total_variants": total_variants}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["EntityStandardizer", "EntityMapping"]
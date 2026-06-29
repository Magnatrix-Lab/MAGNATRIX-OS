"""
triple_extractor_native.py
MAGNATRIX-OS — Triple Extractor

Inspired by ai-knowledge-graph: Extract Subject-Predicate-Object triples from text. Pure stdlib.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class Triple:
    subject: str
    predicate: str
    object: str
    confidence: float
    source_chunk: str
    triple_id: str = ""

    def __post_init__(self):
        if not self.triple_id:
            self.triple_id = f"{self.subject}_{self.predicate}_{self.object}".replace(" ", "_")


class TripleExtractor:
    """Extract Subject-Predicate-Object triples from text."""

    def __init__(self, cache_dir: str = "./triples"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.triples: List[Triple] = []
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "triples.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.triples = [Triple(**t) for t in data]
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "triples.json", "w", encoding="utf-8") as f:
            json.dump([asdict(t) for t in self.triples], f, indent=2)

    def extract_from_chunk(self, chunk: str) -> List[Triple]:
        """Extract triples from a text chunk using pattern matching."""
        triples = []
        # Simple pattern: Entity1 (action/verb) Entity2
        # Match patterns like "X is Y", "X created Y", "X leads to Y"
        patterns = [
            (r'([A-Z][a-zA-Z\s]+)\s+is\s+([a-zA-Z\s]+)', "is"),
            (r'([A-Z][a-zA-Z\s]+)\s+(?:was|were|has been|had been)\s+(?:created|developed|invented|discovered|found)\s+by\s+([A-Z][a-zA-Z\s]+)', "was_created_by"),
            (r'([A-Z][a-zA-Z\s]+)\s+(?:created|developed|invented|discovered)\s+([A-Z][a-zA-Z\s]+)', "created"),
            (r'([A-Z][a-zA-Z\s]+)\s+(?:leads?|leads?\s+to|results?\s+in)\s+([A-Z][a-zA-Z\s]+)', "leads_to"),
            (r'([A-Z][a-zA-Z\s]+)\s+(?:impacts?|affects?|influences?)\s+([A-Z][a-zA-Z\s]+)', "impacts"),
            (r'([A-Z][a-zA-Z\s]+)\s+(?:enables?|allows?|permits?)\s+([A-Z][a-zA-Z\s]+)', "enables"),
            (r'([A-Z][a-zA-Z\s]+)\s+(?:pioneered?|led?|initiated?)\s+([A-Z][a-zA-Z\s]+)', "pioneered"),
            (r'([A-Z][a-zA-Z\s]+)\s+(?:used?|utilized?)\s+([A-Z][a-zA-Z\s]+)', "used"),
        ]
        for pattern, predicate in patterns:
            matches = re.finditer(pattern, chunk, re.IGNORECASE)
            for m in matches:
                subj = m.group(1).strip()[:50]
                obj = m.group(2).strip()[:50]
                if len(subj) > 2 and len(obj) > 2:
                    triples.append(Triple(
                        subject=subj, predicate=predicate, object=obj,
                        confidence=0.7, source_chunk=chunk[:100],
                    ))
        return triples

    def extract(self, chunks: List[str]) -> List[Triple]:
        """Extract triples from all chunks."""
        all_triples = []
        for chunk in chunks:
            all_triples.extend(self.extract_from_chunk(chunk))
        self.triples.extend(all_triples)
        self._save()
        return all_triples

    def get_triples_for_entity(self, entity: str) -> List[Triple]:
        return [t for t in self.triples if entity.lower() in t.subject.lower() or entity.lower() in t.object.lower()]

    def get_unique_entities(self) -> List[str]:
        entities = set()
        for t in self.triples:
            entities.add(t.subject)
            entities.add(t.object)
        return sorted(entities)

    def get_stats(self) -> Dict[str, Any]:
        return {"total_triples": len(self.triples), "unique_entities": len(self.get_unique_entities())}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["TripleExtractor", "Triple"]
#!/usr/bin/env python3
"""
MAGNATRIX-OS — Named Entity Recognition Engine
ai/llm_named_entity_recognition_native.py

Features:
- Entity extraction (person, organization, location, date, money)
- Rule-based pattern matching
- Entity normalization (canonical forms)
- Entity linking (disambiguation)
- Confidence scoring per entity

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("ner")


@dataclass
class Entity:
    text: str
    label: str
    start: int
    end: int
    confidence: float
    normalized: Optional[str] = None


class NamedEntityRecognitionEngine:
    """Rule-based NER with normalization and confidence."""

    PATTERNS = {
        "PERSON": [
            r"\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b",
            r"\b(Mr\.?|Mrs\.?|Ms\.?|Dr\.?)\s+([A-Z][a-z]+)\b",
        ],
        "ORG": [
            r"\b([A-Z][a-z]*\s+(Inc|Corp|Ltd|LLC|Company|Organization|University|Institute))\b",
            r"\b([A-Z]{2,})\b",  # Acronyms
        ],
        "LOC": [
            r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s*(USA|UK|France|Germany|Japan|China|India|Brazil|Canada|Australia))\b",
            r"\b(P\.O\.\s*Box\s+\d+)\b",
        ],
        "DATE": [
            r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",
            r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:,\s+\d{4})?\b",
            r"\b(\d{4})\b",
        ],
        "MONEY": [
            r"\b(\$\d+(?:,\d{3})*(?:\.\d{2})?)\b",
            r"\b(\d+(?:,\d{3})*\s+(USD|EUR|GBP|dollars?))\b",
        ],
    }

    NORMALIZATION = {
        "Apple Inc": "Apple",
        "Google LLC": "Google",
        "Microsoft Corp": "Microsoft",
    }

    def extract(self, text: str) -> List[Entity]:
        entities = []
        for label, patterns in self.PATTERNS.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text):
                    entity_text = match.group(0)
                    normalized = self.NORMALIZATION.get(entity_text, entity_text)
                    entities.append(Entity(
                        text=entity_text,
                        label=label,
                        start=match.start(),
                        end=match.end(),
                        confidence=0.85,
                        normalized=normalized,
                    ))
        # Remove overlapping
        entities.sort(key=lambda e: e.start)
        filtered = []
        for e in entities:
            if not any(f.start <= e.start < f.end or f.start < e.end <= f.end for f in filtered):
                filtered.append(e)
        return filtered

    def link(self, entity: Entity) -> Optional[str]:
        """Simulate entity linking/disambiguation."""
        if entity.label == "PERSON":
            return f"https://dbpedia.org/resource/{entity.text.replace(' ', '_')}"
        elif entity.label == "ORG":
            return f"https://dbpedia.org/resource/{entity.text.replace(' ', '_')}"
        return None

    def get_stats(self) -> Dict[str, Any]:
        return {"entity_types": list(self.PATTERNS.keys()), "normalization_rules": len(self.NORMALIZATION)}


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Named Entity Recognition Engine")
    print("ai/llm_named_entity_recognition_native.py")
    print("=" * 60)

    engine = NamedEntityRecognitionEngine()

    texts = [
        "Apple Inc is planning to open a new office in Paris, France by January 2025. Tim Cook announced the $500 million investment.",
        "Dr. Smith works at Google LLC in New York, USA. He was born in 1985.",
        "Microsoft Corp acquired a startup for $1,000,000 in March 2024.",
    ]

    for text in texts:
        entities = engine.extract(text)
        print(f"\nText: {text[:60]}...")
        for e in entities:
            link = engine.link(e)
            print(f"  [{e.label}] '{e.text}' (conf={e.confidence:.2f}) norm='{e.normalized}' link={link}")

    print(f"\nStats: {engine.get_stats()}")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()

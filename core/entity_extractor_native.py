
"""
entity_extractor_native.py
MAGNATRIX-OS — Entity Extractor

Inspired by Synapse automatic entity extraction from conversations.
Extracts entities, relationships, and facts from natural language text
for storage in the temporal knowledge graph.

Pure Python standard library.
"""

import re
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ExtractedEntity:
    name: str
    entity_type: str = "unknown"
    aliases: List[str] = field(default_factory=list)
    mentioned_in: List[str] = field(default_factory=list)


@dataclass
class ExtractedRelation:
    subject: str
    predicate: str
    obj: str
    confidence: float = 1.0


class EntityExtractor:
    """Extract entities and relations from natural language text."""

    def __init__(self):
        self.entity_patterns = {
            "PERSON": [
                r"\b[A-Z][a-z]+ [A-Z][a-z]+\b",  # First Last
                r"\b(Mr\.?|Mrs\.?|Ms\.?|Dr\.?) [A-Z][a-z]+\b",
            ],
            "ORG": [
                r"\b[A-Z][a-z]* (Inc\.?|Corp\.?|Ltd\.?|Company|Organization)\b",
                r"\b[A-Z][a-z]* (Foundation|Institute|University|College)\b",
            ],
            "LOCATION": [
                r"\b[A-Z][a-z]+ (City|Town|Village|Country|State)\b",
                r"\b(New York|Los Angeles|London|Paris|Tokyo|Beijing|Singapore)\b",
            ],
            "TECH": [
                r"\b[A-Z][a-z]*\.?[A-Z][a-z]* (Framework|Library|Engine|Platform|API)\b",
                r"\b(Python|JavaScript|Rust|Go|TensorFlow|PyTorch|Docker|Kubernetes)\b",
            ],
            "DATE": [
                r"\b(January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2}(, \d{4})?\b",
                r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
            ],
        }
        self.relation_patterns = [
            (r"(\w+) (is|was|are|were) ([^\.,]+)", "is"),
            (r"(\w+) (has|had) ([^\.,]+)", "has"),
            (r"(\w+) (works? at|works? for) ([^\.,]+)", "works_at"),
            (r"(\w+) (created?|developed?|built?) ([^\.,]+)", "created"),
            (r"(\w+) (located? in|located? at) ([^\.,]+)", "located_in"),
            (r"(\w+) (uses?|using|used) ([^\.,]+)", "uses"),
            (r"(\w+) (knows?|knew|met) ([^\.,]+)", "knows"),
        ]

    def extract_entities(self, text: str) -> List[ExtractedEntity]:
        entities = {}
        for entity_type, patterns in self.entity_patterns.items():
            for pattern in patterns:
                for match in re.finditer(pattern, text):
                    name = match.group(0).strip()
                    if name not in entities:
                        entities[name] = ExtractedEntity(name=name, entity_type=entity_type)
                    entities[name].mentioned_in.append(text[:50])
        return list(entities.values())

    def extract_relations(self, text: str) -> List[ExtractedRelation]:
        relations = []
        for pattern, predicate in self.relation_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                subject = match.group(1).strip()
                obj = match.group(3).strip()
                if len(subject) > 2 and len(obj) > 2 and subject != obj:
                    relations.append(ExtractedRelation(
                        subject=subject, predicate=predicate, obj=obj, confidence=0.7
                    ))
        return relations

    def extract_facts(self, text: str) -> List[Dict]:
        """Extract structured facts from text."""
        entities = self.extract_entities(text)
        relations = self.extract_relations(text)
        facts = []
        for rel in relations:
            facts.append({
                "subject": rel.subject,
                "predicate": rel.predicate,
                "object": rel.obj,
                "confidence": rel.confidence,
                "source": text[:100],
            })
        # Extract temporal facts (e.g., "On June 20, X happened")
        temporal_pattern = r"(?:on|at|in) (\w+ \d{1,2},? \d{0,4}),? ([^\.,]+)"
        for match in re.finditer(temporal_pattern, text, re.IGNORECASE):
            date_str = match.group(1).strip()
            event = match.group(2).strip()
            facts.append({
                "subject": "event",
                "predicate": "occurred_on",
                "object": f"{event} ({date_str})",
                "confidence": 0.6,
                "source": text[:100],
            })
        return facts

    def process_conversation(self, messages: List[Dict]) -> Dict:
        """Process a conversation thread and extract all knowledge."""
        all_entities = []
        all_relations = []
        all_facts = []
        for msg in messages:
            content = msg.get("content", "")
            all_entities.extend(self.extract_entities(content))
            all_relations.extend(self.extract_relations(content))
            all_facts.extend(self.extract_facts(content))
        return {
            "entities": [{"name": e.name, "type": e.entity_type} for e in all_entities],
            "relations": [{"s": r.subject, "p": r.predicate, "o": r.obj} for r in all_relations],
            "facts": all_facts,
            "timestamp": datetime.now().isoformat(),
        }

    def to_dict(self) -> Dict:
        return {
            "entity_types": list(self.entity_patterns.keys()),
            "relation_patterns": len(self.relation_patterns),
        }


__all__ = ["EntityExtractor", "ExtractedEntity", "ExtractedRelation"]

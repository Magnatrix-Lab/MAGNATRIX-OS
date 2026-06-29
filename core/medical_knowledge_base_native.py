"""
medical_knowledge_base_native.py
MAGNATRIX-OS — Medical Knowledge Base

Inspired by Meditron (EPFL): Medical knowledge storage with disease-symptom-drug relationships. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class MedicalEntity:
    entity_id: str
    entity_type: str  # disease, symptom, drug, procedure, anatomy
    name: str
    description: str
    synonyms: List[str] = field(default_factory=list)
    relationships: Dict[str, List[str]] = field(default_factory=dict)
    evidence_level: str = "low"  # low, medium, high


class MedicalKnowledgeBase:
    """Medical knowledge storage with disease-symptom-drug relationships."""

    BUILT_IN_DISEASES = {
        "diabetes_t2": {
            "name": "Type 2 Diabetes Mellitus", "description": "Chronic metabolic disorder characterized by insulin resistance",
            "synonyms": ["T2DM", "NIDDM", "adult-onset diabetes"], "entity_type": "disease",
            "relationships": {"symptoms": ["polyuria", "polydipsia", "fatigue", "blurred_vision"], "drugs": ["metformin", "insulin", "gliclazide"], "anatomy": ["pancreas"]},
            "evidence_level": "high",
        },
        "hypertension": {
            "name": "Essential Hypertension", "description": "Persistently elevated blood pressure",
            "synonyms": ["high blood pressure", "HTN"], "entity_type": "disease",
            "relationships": {"symptoms": ["headache", "dizziness", "chest_pain"], "drugs": ["amlodipine", "lisinopril", "atenolol"], "anatomy": ["heart", "arteries"]},
            "evidence_level": "high",
        },
        "pneumonia": {
            "name": "Pneumonia", "description": "Infection that inflames air sacs in one or both lungs",
            "synonyms": ["lung infection", "chest infection"], "entity_type": "disease",
            "relationships": {"symptoms": ["fever", "cough", "shortness_of_breath", "chest_pain"], "drugs": ["amoxicillin", "azithromycin", "levofloxacin"], "anatomy": ["lungs"]},
            "evidence_level": "high",
        },
        "migraine": {
            "name": "Migraine", "description": "Neurological condition causing severe headaches",
            "synonyms": ["migraine headache"], "entity_type": "disease",
            "relationships": {"symptoms": ["headache", "nausea", "photophobia", "aura"], "drugs": ["sumatriptan", "propranolol", "topiramate"], "anatomy": ["brain"]},
            "evidence_level": "high",
        },
    }

    def __init__(self, kb_dir: str = "./medical_kb"):
        self.kb_dir = Path(kb_dir)
        self.kb_dir.mkdir(exist_ok=True)
        self.entities: Dict[str, MedicalEntity] = {}
        self._load()

    def _load(self) -> None:
        file = self.kb_dir / "entities.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for eid, ed in data.items():
                        self.entities[eid] = MedicalEntity(**ed)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.kb_dir / "entities.json", "w", encoding="utf-8") as f:
            json.dump({eid: asdict(e) for eid, e in self.entities.items()}, f, indent=2)

    def add_entity(self, entity_id: str, entity_type: str, name: str, description: str,
                   synonyms: Optional[List[str]] = None, relationships: Optional[Dict[str, List[str]]] = None,
                   evidence_level: str = "low") -> MedicalEntity:
        entity = MedicalEntity(
            entity_id=entity_id, entity_type=entity_type, name=name, description=description,
            synonyms=synonyms or [], relationships=relationships or {}, evidence_level=evidence_level,
        )
        self.entities[entity_id] = entity
        self._save()
        return entity

    def add_builtin(self, entity_id: str) -> Optional[MedicalEntity]:
        if entity_id not in self.BUILT_IN_DISEASES:
            return None
        info = self.BUILT_IN_DISEASES[entity_id]
        return self.add_entity(
            entity_id=entity_id, entity_type=info["entity_type"], name=info["name"],
            description=info["description"], synonyms=info.get("synonyms", []),
            relationships=info.get("relationships", {}), evidence_level=info.get("evidence_level", "low"),
        )

    def query(self, query: str, entity_type: Optional[str] = None) -> List[MedicalEntity]:
        q = query.lower()
        results = []
        for e in self.entities.values():
            if entity_type and e.entity_type != entity_type:
                continue
            if q in e.name.lower() or q in e.description.lower() or any(q in s.lower() for s in e.synonyms):
                results.append(e)
        return results

    def get_related(self, entity_id: str, relation_type: str) -> List[str]:
        entity = self.entities.get(entity_id)
        if not entity:
            return []
        return entity.relationships.get(relation_type, [])

    def get_entity(self, entity_id: str) -> Optional[MedicalEntity]:
        return self.entities.get(entity_id)

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.entities)
        by_type = {}
        for e in self.entities.values():
            by_type[e.entity_type] = by_type.get(e.entity_type, 0) + 1
        return {"total_entities": total, "by_type": by_type, "builtins": len(self.BUILT_IN_DISEASES)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["MedicalKnowledgeBase", "MedicalEntity"]
"""
medical_text_processor_native.py
MAGNATRIX-OS — Medical Text Processor

Inspired by Meditron (EPFL): PubMed/medical text processing with NER-like extraction. Pure stdlib.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class MedicalAnnotation:
    text: str
    entity_type: str
    start: int
    end: int


@dataclass
class ProcessedDocument:
    doc_id: str
    title: str
    abstract: str
    annotations: List[MedicalAnnotation] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    mesh_terms: List[str] = field(default_factory=list)


class MedicalTextProcessor:
    """Process medical texts with entity extraction and keyword identification."""

    MEDICAL_TERMS = {
        "disease": ["diabetes", "hypertension", "pneumonia", "migraine", "cancer", "asthma", "arthritis", "depression"],
        "symptom": ["fever", "cough", "headache", "fatigue", "nausea", "pain", "dizziness", "shortness of breath"],
        "drug": ["metformin", "insulin", "amoxicillin", "ibuprofen", "aspirin", "paracetamol", "atorvastatin"],
        "anatomy": ["heart", "brain", "lungs", "liver", "kidney", "pancreas", "stomach", "intestine"],
        "procedure": ["surgery", "biopsy", "radiography", "MRI", "CT scan", "endoscopy", "laparoscopy"],
    }

    def __init__(self, cache_dir: str = "./medical_texts"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.documents: Dict[str, ProcessedDocument] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "documents.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for did, dd in data.items():
                        dd["annotations"] = [MedicalAnnotation(**a) for a in dd.get("annotations", [])]
                        self.documents[did] = ProcessedDocument(**dd)
            except Exception:
                pass

    def _save(self) -> None:
        out = {}
        for did, d in self.documents.items():
            od = asdict(d)
            od["annotations"] = [asdict(a) for a in d.annotations]
            out[did] = od
        with open(self.cache_dir / "documents.json", "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)

    def process(self, doc_id: str, title: str, abstract: str) -> ProcessedDocument:
        annotations = []
        keywords = []
        text = f"{title} {abstract}".lower()
        for entity_type, terms in self.MEDICAL_TERMS.items():
            for term in terms:
                for match in re.finditer(r'\b' + re.escape(term.lower()) + r'\b', text):
                    annotations.append(MedicalAnnotation(
                        text=term, entity_type=entity_type, start=match.start(), end=match.end(),
                    ))
                    if term not in keywords:
                        keywords.append(term)
        doc = ProcessedDocument(
            doc_id=doc_id, title=title, abstract=abstract,
            annotations=annotations, keywords=keywords,
        )
        self.documents[doc_id] = doc
        self._save()
        return doc

    def extract_mesh(self, doc_id: str, mesh_terms: List[str]) -> bool:
        doc = self.documents.get(doc_id)
        if not doc:
            return False
        doc.mesh_terms = mesh_terms
        self._save()
        return True

    def get_document(self, doc_id: str) -> Optional[ProcessedDocument]:
        return self.documents.get(doc_id)

    def search_by_keyword(self, keyword: str) -> List[ProcessedDocument]:
        return [d for d in self.documents.values() if keyword.lower() in [k.lower() for k in d.keywords]]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.documents)
        total_annotations = sum(len(d.annotations) for d in self.documents.values())
        return {"documents": total, "annotations": total_annotations}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["MedicalTextProcessor", "ProcessedDocument", "MedicalAnnotation"]
"""
clinical_reasoning_engine_native.py
MAGNATRIX-OS — Clinical Reasoning Engine

Inspired by Meditron (EPFL): Differential diagnosis and clinical reasoning simulation. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class DifferentialDiagnosis:
    diagnosis_id: str
    disease: str
    probability: float
    supporting_evidence: List[str] = field(default_factory=list)
    contradicting_evidence: List[str] = field(default_factory=list)


@dataclass
class ClinicalCase:
    case_id: str
    patient_id: str
    symptoms: List[str] = field(default_factory=list)
    vitals: Dict[str, float] = field(default_factory=dict)
    differential: List[DifferentialDiagnosis] = field(default_factory=list)
    final_diagnosis: str = ""
    confidence: float = 0.0
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class ClinicalReasoningEngine:
    """Differential diagnosis and clinical reasoning simulation."""

    def __init__(self, cases_dir: str = "./clinical_cases"):
        self.cases_dir = Path(cases_dir)
        self.cases_dir.mkdir(exist_ok=True)
        self.cases: Dict[str, ClinicalCase] = {}
        self._load()

    def _load(self) -> None:
        file = self.cases_dir / "cases.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for cid, cd in data.items():
                        cd["differential"] = [DifferentialDiagnosis(**d) for d in cd.get("differential", [])]
                        self.cases[cid] = ClinicalCase(**cd)
            except Exception:
                pass

    def _save(self) -> None:
        out = {}
        for cid, c in self.cases.items():
            d = asdict(c)
            d["differential"] = [asdict(d) for d in c.differential]
            out[cid] = d
        with open(self.cases_dir / "cases.json", "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)

    def create_case(self, case_id: str, patient_id: str) -> ClinicalCase:
        case = ClinicalCase(case_id=case_id, patient_id=patient_id)
        self.cases[case_id] = case
        self._save()
        return case

    def add_symptoms(self, case_id: str, symptoms: List[str]) -> bool:
        case = self.cases.get(case_id)
        if not case:
            return False
        case.symptoms.extend(symptoms)
        self._save()
        return True

    def add_vitals(self, case_id: str, vitals: Dict[str, float]) -> bool:
        case = self.cases.get(case_id)
        if not case:
            return False
        case.vitals.update(vitals)
        self._save()
        return True

    def compute_differential(self, case_id: str, knowledge_base: Optional[Dict[str, Any]] = None) -> List[DifferentialDiagnosis]:
        """Simulate differential diagnosis based on symptoms."""
        case = self.cases.get(case_id)
        if not case:
            return []
        # Simple heuristic: match symptoms to known diseases
        differentials = []
        diseases = {
            "diabetes_t2": ["polyuria", "polydipsia", "fatigue", "blurred_vision"],
            "hypertension": ["headache", "dizziness", "chest_pain"],
            "pneumonia": ["fever", "cough", "shortness_of_breath", "chest_pain"],
            "migraine": ["headache", "nausea", "photophobia", "aura"],
        }
        for disease, disease_symptoms in diseases.items():
            matches = sum(1 for s in case.symptoms if s in disease_symptoms)
            if matches > 0:
                prob = min(0.95, matches / len(disease_symptoms) * 1.5)
                supporting = [s for s in case.symptoms if s in disease_symptoms]
                contradicting = [s for s in case.symptoms if s not in disease_symptoms]
                differentials.append(DifferentialDiagnosis(
                    diagnosis_id=f"{case_id}_{disease}", disease=disease, probability=round(prob, 2),
                    supporting_evidence=supporting, contradicting_evidence=contradicting,
                ))
        differentials.sort(key=lambda x: x.probability, reverse=True)
        case.differential = differentials
        self._save()
        return differentials

    def finalize_diagnosis(self, case_id: str, diagnosis: str, confidence: float) -> bool:
        case = self.cases.get(case_id)
        if not case:
            return False
        case.final_diagnosis = diagnosis
        case.confidence = confidence
        self._save()
        return True

    def get_case(self, case_id: str) -> Optional[ClinicalCase]:
        return self.cases.get(case_id)

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.cases)
        finalized = sum(1 for c in self.cases.values() if c.final_diagnosis)
        return {"total_cases": total, "finalized": finalized}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["ClinicalReasoningEngine", "ClinicalCase", "DifferentialDiagnosis"]
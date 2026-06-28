#!/usr/bin/env python3
"""Medical Diagnosis Engine for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

@dataclass
class Symptom:
    name: str
    severity: int = 1
    duration_days: int = 0
    def to_dict(self): return asdict(self)

class MedicalDiagnosisEngine:
    def __init__(self, repo_root=""):
        self.repo_root = repo_root
        self.knowledge: Dict[str, List[str]] = {
            "fever": ["flu", "infection", "covid"],
            "cough": ["flu", "cold", "covid", "pneumonia"],
            "headache": ["migraine", "tension", "flu"],
            "fatigue": ["anemia", "depression", "sleep_apnea", "flu"],
            "chest_pain": ["heart_attack", "angina", "anxiety"],
        }
    def diagnose(self, symptoms: List[str]) -> Dict[str, Any]:
        candidates: Dict[str, int] = {}
        for s in symptoms:
            for disease in self.knowledge.get(s, []):
                candidates[disease] = candidates.get(disease, 0) + 1
        sorted_candidates = sorted(candidates.items(), key=lambda x: x[1], reverse=True)
        return {"symptoms": symptoms, "candidates": [{"disease": d, "score": s} for d,s in sorted_candidates[:5]]}
    def triage(self, symptoms: List[str]) -> str:
        if any(s in ["chest_pain", "severe_bleeding", "unconsciousness"] for s in symptoms):
            return "EMERGENCY"
        elif any(s in ["fever", "cough", "shortness_of_breath"] for s in symptoms):
            return "URGENT"
        return "ROUTINE"
    def to_dict(self): return {"conditions": len(self.knowledge)}

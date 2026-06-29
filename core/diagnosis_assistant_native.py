"""
diagnosis_assistant_native.py
MAGNATRIX-OS — Diagnosis Assistant

Inspired by Meditron (EPFL): Diagnostic assistant with triage and severity scoring. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class PatientPresentation:
    presentation_id: str
    age: int
    gender: str
    chief_complaint: str
    symptoms: List[str] = field(default_factory=list)
    history: List[str] = field(default_factory=list)
    vitals: Dict[str, float] = field(default_factory=dict)
    severity_score: float = 0.0
    triage_level: str = "unknown"  # critical, urgent, semi-urgent, non-urgent


@dataclass
class DiagnosisResult:
    result_id: str
    presentation_id: str
    differential: List[Dict[str, Any]] = field(default_factory=list)
    recommended_tests: List[str] = field(default_factory=list)
    red_flags: List[str] = field(default_factory=list)
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class DiagnosisAssistant:
    """Diagnostic assistant with triage and severity scoring."""

    RED_FLAGS = ["chest_pain", "shortness_of_breath", "severe_headache", "high_fever", "altered_mental_status", "severe_abdominal_pain", "uncontrolled_bleeding"]

    def __init__(self, assistant_dir: str = "./diagnosis_assistant"):
        self.assistant_dir = Path(assistant_dir)
        self.assistant_dir.mkdir(exist_ok=True)
        self.presentations: Dict[str, PatientPresentation] = {}
        self.results: Dict[str, DiagnosisResult] = {}
        self._load()

    def _load(self) -> None:
        for fname in ["presentations.json", "results.json"]:
            f = self.assistant_dir / fname
            if f.exists():
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        if fname == "presentations.json":
                            for pid, pd in data.items():
                                self.presentations[pid] = PatientPresentation(**pd)
                        else:
                            for rid, rd in data.items():
                                self.results[rid] = DiagnosisResult(**rd)
                except Exception:
                    pass

    def _save(self) -> None:
        with open(self.assistant_dir / "presentations.json", "w", encoding="utf-8") as f:
            json.dump({pid: asdict(p) for pid, p in self.presentations.items()}, f, indent=2)
        with open(self.assistant_dir / "results.json", "w", encoding="utf-8") as f:
            json.dump({rid: asdict(r) for rid, r in self.results.items()}, f, indent=2)

    def present(self, presentation_id: str, age: int, gender: str, chief_complaint: str,
                symptoms: List[str], history: Optional[List[str]] = None,
                vitals: Optional[Dict[str, float]] = None) -> PatientPresentation:
        pres = PatientPresentation(
            presentation_id=presentation_id, age=age, gender=gender,
            chief_complaint=chief_complaint, symptoms=symptoms,
            history=history or [], vitals=vitals or {},
        )
        # Calculate severity
        severity = 0.0
        red_flags_found = [s for s in symptoms if s in self.RED_FLAGS]
        severity += len(red_flags_found) * 0.3
        if vitals:
            if vitals.get("temp", 37.0) > 39.0:
                severity += 0.2
            if vitals.get("systolic_bp", 120) > 180 or vitals.get("systolic_bp", 120) < 90:
                severity += 0.2
            if vitals.get("heart_rate", 70) > 120 or vitals.get("heart_rate", 70) < 50:
                severity += 0.15
        pres.severity_score = round(min(1.0, severity), 2)
        if pres.severity_score > 0.7:
            pres.triage_level = "critical"
        elif pres.severity_score > 0.4:
            pres.triage_level = "urgent"
        elif pres.severity_score > 0.2:
            pres.triage_level = "semi-urgent"
        else:
            pres.triage_level = "non-urgent"
        self.presentations[presentation_id] = pres
        self._save()
        return pres

    def diagnose(self, result_id: str, presentation_id: str) -> DiagnosisResult:
        pres = self.presentations.get(presentation_id)
        if not pres:
            return DiagnosisResult(result_id=result_id, presentation_id=presentation_id)
        # Simple differential based on symptoms
        differential = []
        symptom_map = {
            "chest_pain": ["myocardial_infarction", "angina", "costochondritis"],
            "shortness_of_breath": ["pneumonia", "heart_failure", "asthma", "COPD"],
            "fever": ["infection", "pneumonia", "UTI", "viral_illness"],
            "headache": ["migraine", "tension_headache", "meningitis"],
            "abdominal_pain": ["appendicitis", "gastritis", "IBS", "cholecystitis"],
            "fatigue": ["anemia", "hypothyroidism", "depression", "diabetes"],
        }
        for symptom in pres.symptoms:
            for disease in symptom_map.get(symptom, []):
                if not any(d["disease"] == disease for d in differential):
                    differential.append({"disease": disease, "confidence": 0.5, "matching_symptoms": [symptom]})
        recommended_tests = []
        if pres.vitals.get("systolic_bp", 120) > 140:
            recommended_tests.append("blood_pressure_monitoring")
        if "fever" in pres.symptoms:
            recommended_tests.extend(["CBC", "CRP", "blood_culture"])
        if "chest_pain" in pres.symptoms:
            recommended_tests.extend(["ECG", "troponin", "chest_XR"])
        result = DiagnosisResult(
            result_id=result_id, presentation_id=presentation_id,
            differential=differential, recommended_tests=list(set(recommended_tests)),
            red_flags=[s for s in pres.symptoms if s in self.RED_FLAGS],
        )
        self.results[result_id] = result
        self._save()
        return result

    def get_presentation(self, presentation_id: str) -> Optional[PatientPresentation]:
        return self.presentations.get(presentation_id)

    def get_result(self, result_id: str) -> Optional[DiagnosisResult]:
        return self.results.get(result_id)

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.presentations)
        critical = sum(1 for p in self.presentations.values() if p.triage_level == "critical")
        return {"presentations": total, "critical": critical}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["DiagnosisAssistant", "PatientPresentation", "DiagnosisResult"]
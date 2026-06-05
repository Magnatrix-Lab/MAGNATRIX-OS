"""Emergency Responder — triage, treatment, transport, resource, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class Patient:
    id: str
    priority: str
    vitals: Dict[str, float]
    injuries: List[str]

class EmergencyResponder:
    def __init__(self):
        self.patients: List[Patient] = []

    def add_patient(self, p: Patient):
        self.patients.append(p)

    def triage_score(self, p: Patient) -> int:
        scores = {"red": 1, "yellow": 2, "green": 3, "black": 4}
        return scores.get(p.priority, 3)

    def triage_order(self) -> List[str]:
        return [p.id for p in sorted(self.patients, key=lambda x: self.triage_score(x))]

    def critical_count(self) -> int:
        return sum(1 for p in self.patients if p.priority == "red")

    def resource_estimate(self, p: Patient) -> Dict[str, int]:
        resources = {"blood": 0, "surgery": 0, "icu": 0}
        if "hemorrhage" in p.injuries:
            resources["blood"] += 2
        if any(i in p.injuries for i in ["fracture", "head", "chest"]):
            resources["surgery"] += 1
        if p.priority == "red":
            resources["icu"] += 1
        return resources

    def total_resources(self) -> Dict[str, int]:
        total = {"blood": 0, "surgery": 0, "icu": 0}
        for p in self.patients:
            for k, v in self.resource_estimate(p).items():
                total[k] += v
        return total

    def transport_priority(self) -> List[str]:
        return [p.id for p in sorted(self.patients, key=lambda x: (self.triage_score(x), -len(x.injuries)))]

    def stats(self) -> Dict:
        return {"patients": len(self.patients), "critical": self.critical_count(), "resources": self.total_resources()}

def run():
    er = EmergencyResponder()
    er.add_patient(Patient("P1", "red", {"hr": 120, "bp": 80}, ["hemorrhage", "fracture"]))
    er.add_patient(Patient("P2", "yellow", {"hr": 90, "bp": 110}, ["sprain"]))
    er.add_patient(Patient("P3", "green", {"hr": 70, "bp": 120}, ["cut"]))
    print(er.stats())
    print("Triage order:", er.triage_order())
    print("Transport:", er.transport_priority())

if __name__ == "__main__":
    run()

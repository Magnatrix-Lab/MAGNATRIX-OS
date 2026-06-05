"""Explainable Fairness — report generation, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto

class ExplainableFairness:
    def __init__(self):
        self.audits: List[Dict] = []

    def add_audit(self, audit: Dict):
        self.audits.append(audit)

    def generate_report(self) -> Dict:
        report = {
            "total_audits": len(self.audits),
            "biased_audits": sum(1 for a in self.audits if a.get("biased", False)),
            "fair_audits": sum(1 for a in self.audits if not a.get("biased", False)),
            "metrics": {}
        }
        for audit in self.audits:
            for metric, score in audit.get("scores", {}).items():
                if metric not in report["metrics"]:
                    report["metrics"][metric] = []
                report["metrics"][metric].append(score)
        for metric in report["metrics"]:
            scores = report["metrics"][metric]
            report["metrics"][metric] = {"avg": sum(scores)/len(scores), "min": min(scores), "max": max(scores)}
        return report

    def recommendations(self) -> List[str]:
        recs = []
        biased = [a for a in self.audits if a.get("biased", False)]
        if biased:
            recs.append("Review model training data for underrepresentation")
            recs.append("Apply fairness constraints during optimization")
            recs.append("Consider post-processing calibration per group")
        return recs

    def stats(self) -> Dict:
        return {"audits": len(self.audits)}

def run():
    ef = ExplainableFairness()
    ef.add_audit({"biased": True, "scores": {"dp": 0.15, "eo": 0.12}})
    ef.add_audit({"biased": False, "scores": {"dp": 0.05, "eo": 0.03}})
    print(ef.generate_report())
    print(ef.recommendations())
    print(ef.stats())

if __name__ == "__main__":
    run()

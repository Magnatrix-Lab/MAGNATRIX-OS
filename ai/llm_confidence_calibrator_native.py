"""Confidence Calibrator - Reliability diagram for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple

@dataclass
class ConfidenceCalibrator:
    bins: int = 10

    def reliability_diagram(self, confidences: List[float], accuracies: List[int]) -> List[Tuple[float, float]]:
        bin_edges = [i/self.bins for i in range(self.bins+1)]
        results = []
        for i in range(self.bins):
            in_bin = [j for j in range(len(confidences)) if bin_edges[i] <= confidences[j] < bin_edges[i+1]]
            if not in_bin: continue
            avg_conf = sum(confidences[j] for j in in_bin) / len(in_bin)
            avg_acc = sum(accuracies[j] for j in in_bin) / len(in_bin)
            results.append((round(avg_conf, 4), round(avg_acc, 4)))
        return results

    def expected_calibration_error(self, confidences: List[float], accuracies: List[int]) -> float:
        diagram = self.reliability_diagram(confidences, accuracies)
        ece = 0.0
        bin_edges = [i/self.bins for i in range(self.bins+1)]
        for i in range(self.bins):
            in_bin = [j for j in range(len(confidences)) if bin_edges[i] <= confidences[j] < bin_edges[i+1]]
            if not in_bin: continue
            avg_acc = sum(accuracies[j] for j in in_bin) / len(in_bin)
            avg_conf = sum(confidences[j] for j in in_bin) / len(in_bin)
            ece += (len(in_bin)/len(confidences)) * abs(avg_conf - avg_acc)
        return ece

    def stats(self, confidences: List[float], accuracies: List[int]) -> dict:
        return {"ece": round(self.expected_calibration_error(confidences, accuracies), 4), "bins": self.bins}

def run():
    cc = ConfidenceCalibrator(5)
    conf = [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1, 0.95]
    acc = [1, 1, 0, 1, 0, 0, 0, 1, 0, 1]
    print("Reliability:", cc.reliability_diagram(conf, acc))
    print("ECE:", round(cc.expected_calibration_error(conf, acc), 4))
    print("Stats:", cc.stats(conf, acc))

if __name__ == "__main__": run()

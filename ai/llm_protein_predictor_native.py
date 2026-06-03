"""Protein Predictor - Protein properties for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class ProteinPredictor:
    amino_acids: str = "ACDEFGHIKLMNPQRSTVWY"
    hydropathy: Dict[str, float] = None

    def __post_init__(self):
        if self.hydropathy is None:
            self.hydropathy = {"A":1.8,"C":2.5,"D":-3.5,"E":-3.5,"F":2.8,"G":-0.4,"H":-3.2,"I":4.5,"K":-3.9,"L":3.8,"M":1.9,"N":-3.5,"P":-1.6,"Q":-3.5,"R":-4.5,"S":-0.8,"T":-0.7,"V":4.2,"W":-0.9,"Y":-1.3}

    def molecular_weight(self, seq: str) -> float:
        weights = {"A":89,"C":121,"D":133,"E":147,"F":165,"G":75,"H":155,"I":131,"K":146,"L":131,"M":149,"N":132,"P":115,"Q":146,"R":174,"S":105,"T":119,"V":117,"W":204,"Y":181}
        return sum(weights.get(aa, 110) for aa in seq.upper())

    def hydropathy_index(self, seq: str) -> float:
        vals = [self.hydropathy.get(aa, 0) for aa in seq.upper()]
        return sum(vals)/len(vals) if vals else 0

    def stats(self, seq: str) -> dict:
        return {"length": len(seq), "mw": self.molecular_weight(seq), "hydropathy": round(self.hydropathy_index(seq), 4)}

def run():
    pp = ProteinPredictor()
    seq = "MKTLLIL"
    print("MW:", pp.molecular_weight(seq))
    print("Hydropathy:", round(pp.hydropathy_index(seq), 4))
    print("Stats:", pp.stats(seq))

if __name__ == "__main__": run()

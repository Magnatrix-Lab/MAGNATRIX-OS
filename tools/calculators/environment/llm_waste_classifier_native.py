"""Waste Classifier -- type, hazard, recyclability, disposal, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set

@dataclass
class WasteClassifier:
    name: str
    material: str
    weight_kg: float
    hazardous: bool = False

    def classification(self) -> str:
        if self.hazardous:
            return "hazardous"
        recyclables = {"paper", "plastic", "glass", "metal", "cardboard"}
        if self.material.lower() in recyclables:
            return "recyclable"
        organics = {"food", "organic", "garden", "biodegradable"}
        if self.material.lower() in organics:
            return "organic"
        return "general waste"

    def disposal_method(self) -> str:
        cls = self.classification()
        methods = {
            "hazardous": "specialized treatment facility",
            "recyclable": "material recovery facility",
            "organic": "composting or anaerobic digestion",
            "general waste": "landfill or incineration"
        }
        return methods.get(cls, "landfill")

    def landfill_diversion(self) -> bool:
        return self.classification() in ["recyclable", "organic"]

    def carbon_footprint(self) -> float:
        factors = {"paper": 0.5, "plastic": 2.0, "glass": 0.8, "metal": 1.5, "food": 0.3, "general": 1.0, "hazardous": 5.0}
        return self.weight_kg * factors.get(self.material.lower(), 1.0)

    def stats(self) -> Dict:
        return {"type": self.classification(), "disposal": self.disposal_method(), "diversion": self.landfill_diversion(), "co2_kg": round(self.carbon_footprint(), 2)}

def run():
    wc = WasteClassifier("bottle", "plastic", 0.05)
    print(wc.stats())
    wc2 = WasteClassifier("battery", "hazardous", 0.2, True)
    print(wc2.stats())

if __name__ == "__main__":
    run()

"""Crop Planner — rotation, season, yield prediction, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum, auto

class CropPlanner:
    def __init__(self, field_size: float = 100.0):
        self.field_size = field_size
        self.crops: Dict[str, Dict] = {}
        self.schedule: List[Dict] = []

    def add_crop(self, crop_id: str, yield_per_acre: float, season: str, water_need: float, nitrogen_need: float):
        self.crops[crop_id] = {"yield": yield_per_acre, "season": season, "water": water_need, "nitrogen": nitrogen_need}

    def plan_season(self, season: str, available_water: float) -> List[Dict]:
        plan = []
        candidates = [c for c, props in self.crops.items() if props["season"] == season]
        remaining_water = available_water
        for crop_id in sorted(candidates, key=lambda c: self.crops[c]["yield"], reverse=True):
            need = self.crops[crop_id]["water"] * self.field_size
            if need <= remaining_water:
                plan.append({"crop": crop_id, "area": self.field_size, "water": need})
                remaining_water -= need
        return plan

    def rotation_plan(self, years: int = 3) -> List[List[str]]:
        crop_list = list(self.crops.keys())
        rotation = []
        for y in range(years):
            rotation.append(crop_list[y % len(crop_list):] + crop_list[:y % len(crop_list)])
        return rotation

    def predicted_yield(self, plan: List[Dict]) -> float:
        return sum(self.crops[p["crop"]]["yield"] * p["area"] for p in plan if p["crop"] in self.crops)

    def stats(self) -> Dict:
        return {"crops": len(self.crops), "field_size": self.field_size}

def run():
    cp = CropPlanner(50)
    cp.add_crop("wheat", 3.0, "winter", 0.5, 100)
    cp.add_crop("corn", 5.0, "summer", 1.0, 150)
    cp.add_crop("soy", 2.5, "summer", 0.8, 50)
    plan = cp.plan_season("summer", 60)
    print("Plan:", plan)
    print("Yield:", cp.predicted_yield(plan))
    print(cp.stats())

if __name__ == "__main__":
    run()

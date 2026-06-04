"""Precipitation Predictor - Rainfall prediction model for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple
from enum import Enum, auto
import math
import random

@dataclass
class PrecipitationPredictor:
    dry_prob: float = 0.7
    avg_intensity: float = 5.0
    
    def predict_day(self, humidity: float, pressure: float, temp: float) -> Tuple[bool, float]:
        # Logistic regression style probability
        z = -2.0 + 0.05 * humidity - 0.01 * pressure + 0.1 * temp
        prob = 1 / (1 + math.exp(-z))
        will_rain = random.random() < prob
        intensity = random.exponvariate(1/self.avg_intensity) if will_rain else 0.0
        return will_rain, intensity
    
    def predict_month(self, days: int, base_humidity: float, base_pressure: float, base_temp: float) -> List[Tuple[bool, float]]:
        results = []
        for _ in range(days):
            humidity = base_humidity + random.gauss(0, 5)
            pressure = base_pressure + random.gauss(0, 10)
            temp = base_temp + random.gauss(0, 3)
            results.append(self.predict_day(humidity, pressure, temp))
        return results
    
    def stats(self, predictions: List[Tuple[bool, float]]) -> dict:
        rainy_days = sum(1 for r, _ in predictions if r)
        total_rain = sum(i for _, i in predictions)
        return {"days": len(predictions), "rainy_days": rainy_days, "total_rainfall": round(total_rain, 2)}

def run():
    pp = PrecipitationPredictor(0.7, 5.0)
    preds = pp.predict_month(30, 70.0, 1013.0, 20.0)
    print("Rainy days:", sum(1 for r, _ in preds if r))
    print("Stats:", pp.stats(preds))

if __name__ == "__main__": run()

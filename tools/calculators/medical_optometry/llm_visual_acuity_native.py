"""Native stdlib module: Visual Acuity Calculator
Converts between Snellen, LogMAR, and decimal visual acuity notations.
"""
from dataclasses import dataclass
from typing import Dict
import math

@dataclass
class VisualAcuityCalculator:
    snellen_fraction: str = ""
    logmar: float = 0.0
    decimal: float = 0.0

    def snellen_to_logmar(self, snellen: str) -> float:
        try:
            parts = snellen.split('/')
            if len(parts) == 2:
                return -math.log10(float(parts[0]) / float(parts[1]))
        except (ValueError, ZeroDivisionError):
            pass
        return 0.0

    def logmar_to_snellen(self, logmar: float) -> str:
        if logmar == 0:
            return "6/6"
        decimal = 10 ** (-logmar)
        return f"6/{int(6/decimal)}"

    def decimal_to_logmar(self, decimal: float) -> float:
        if decimal <= 0:
            return 0.0
        return -math.log10(decimal)

    def logmar_to_decimal(self, logmar: float) -> float:
        return 10 ** (-logmar)

    def category(self, logmar: float) -> str:
        if logmar <= 0.0:
            return "normal"
        elif logmar <= 0.1:
            return "near_normal"
        elif logmar <= 0.5:
            return "moderate_visual_impairment"
        elif logmar <= 1.0:
            return "severe_visual_impairment"
        return "blind"

    def stats(self) -> Dict:
        if self.snellen_fraction:
            logmar = self.snellen_to_logmar(self.snellen_fraction)
            decimal = self.logmar_to_decimal(logmar)
        elif self.logmar != 0:
            logmar = self.logmar
            decimal = self.logmar_to_decimal(logmar)
        elif self.decimal != 0:
            logmar = self.decimal_to_logmar(self.decimal)
            decimal = self.decimal
        else:
            logmar = 0.0
            decimal = 1.0
        return {
            "snellen": self.logmar_to_snellen(logmar) if not self.snellen_fraction else self.snellen_fraction,
            "logmar": round(logmar, 2),
            "decimal": round(decimal, 3),
            "category": self.category(logmar),
        }

def run():
    vac = VisualAcuityCalculator(snellen_fraction="6/12")
    print(vac.stats())
    vac2 = VisualAcuityCalculator(logmar=0.3)
    print(vac2.stats())

if __name__ == "__main__":
    run()

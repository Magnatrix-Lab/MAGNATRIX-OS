"""
Blood Transfusion Volume Calculator — Hematology
Packed RBC, platelet, FFP, and cryoprecipitate dosing.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List
from enum import Enum


class ProductType(Enum):
    PRBC = "prbc"
    PLATELETS = "platelets"
    FFP = "ffp"
    CRYOPRECIPITATE = "cryoprecipitate"


@dataclass
class TransfusionProfile:
    product: ProductType
    weight_kg: float
    target_hgb_increase: float = 1.0  # g/dL for PRBC
    target_platelet_increase: float = 30000  # per uL
    current_inr: float = 1.0
    target_inr: float = 1.5
    fibrinogen_mg_dl: float = 0.0
    target_fibrinogen: float = 100.0


@dataclass
class TransfusionResult:
    units_needed: int
    volume_ml: float
    expected_response: str
    infusion_rate: str
    monitoring: List[str]
    cautions: List[str]


class TransfusionCalculator:
    """Blood product transfusion dosing calculator."""

    def calculate(self, profile: TransfusionProfile) -> TransfusionResult:
        if profile.weight_kg <= 0:
            raise ValueError("Weight must be > 0 kg")

        if profile.product == ProductType.PRBC:
            # 1 unit PRBC ~ raises Hgb by 1 g/dL in average adult (70kg)
            units = max(1, int(profile.target_hgb_increase))
            volume = units * 250  # mL per unit
            response = f"Hgb increase ~{units * 1.0} g/dL"
            rate = "2-4 mL/kg/hr (over 2-4 hours per unit)"
            monitoring = ["VS q15min x 4, then q30min", "Hgb check 1hr post-transfusion"]
            cautions = ["Febrile/hemolytic reaction monitoring", "Fluid overload if cardiac history"]

        elif profile.product == ProductType.PLATELETS:
            # 1 apheresis unit ~ 3-4 x 10^11 platelets
            # Expected increase ~ 30-50k per uL per unit in 70kg adult
            units = max(1, int(profile.target_platelet_increase / 30000))
            volume = units * 300
            response = f"Platelet increase ~{units * 35000} per uL"
            rate = "Over 30-60 minutes"
            monitoring = ["VS q15min", "Platelet count 1hr post (for refractoriness)"]
            cautions = ["Platelet refractoriness if HLA sensitization", "ABO-compatible preferred"]

        elif profile.product == ProductType.FFP:
            # 15-20 mL/kg raises coagulation factors by ~20-30%
            inr_drop = max(0, profile.current_inr - profile.target_inr)
            if inr_drop <= 0:
                units = 0
                response = "No FFP needed — INR at target"
            else:
                units = max(1, int(profile.weight_kg * 15 / 250))
                response = f"Expected INR drop ~0.5-1.0 per 15mL/kg"
            volume = units * 250
            rate = "10-20 mL/kg/hr"
            monitoring = ["VS q15min", "PT/INR 1hr post"]
            cautions = ["TRALI risk", "Volume overload", "Correct hypothermia before transfusion"]

        elif profile.product == ProductType.CRYOPRECIPITATE:
            # 1 unit (10-15mL) raises fibrinogen ~50-75 mg/dL in adult
            if profile.fibrinogen_mg_dl >= profile.target_fibrinogen:
                units = 0
                response = "No cryoprecipitate needed — fibrinogen adequate"
            else:
                needed = profile.target_fibrinogen - profile.fibrinogen_mg_dl
                units = max(1, int(needed / 50))
            volume = units * 15
            response = f"Fibrinogen increase ~{units * 60} mg/dL" if units > 0 else response
            rate = "Over 10-30 minutes per unit"
            monitoring = ["VS q15min", "Fibrinogen 1hr post"]
            cautions = ["Use for fibrinogen < 100 mg/dL or bleeding with hypofibrinogenemia", "ABO-compatible preferred"]

        else:
            raise ValueError("Unknown product type")

        return TransfusionResult(
            units_needed=units,
            volume_ml=volume,
            expected_response=response,
            infusion_rate=rate,
            monitoring=monitoring,
            cautions=cautions
        )

    def massive_transfusion_protocol(self, blood_loss_ml: float, weight_kg: float) -> dict:
        """MTP ratio guidance."""
        # 1:1:1 PRBC:FFP:Platelets ratio
        prbc_units = max(1, int(blood_loss_ml / 500))
        return {
            "prbc_units": prbc_units,
            "ffp_units": prbc_units,
            "platelet_units": max(1, prbc_units // 2),
            "cryoprecipitate_units": 10 if prbc_units >= 6 else 0,
            "crystalloid_ml": blood_loss_ml * 3,
            "target_hemoglobin": "Maintain 7-9 g/dL",
            "target_inr": "< 1.5",
            "target_fibrinogen": "> 100 mg/dL",
            "target_platelets": "> 50k (trauma) or > 100k (CNS injury)",
            "activate_protocol": blood_loss_ml > 1500
        }


def run():
    calc = TransfusionCalculator()

    print("=" * 60)
    print("Blood Transfusion Volume Calculator")
    print("=" * 60)

    for product in [ProductType.PRBC, ProductType.PLATELETS, ProductType.FFP]:
        profile = TransfusionProfile(
            product=product, weight_kg=70,
            target_hgb_increase=2, target_platelet_increase=50000,
            current_inr=2.5, target_inr=1.5
        )
        result = calc.calculate(profile)
        print(f"\n{product.value}: {result.units_needed} units, {result.volume_ml} mL")
        print(f"  Expected: {result.expected_response}")
        print(f"  Rate: {result.infusion_rate}")

    print(f"\nMTP (2000mL blood loss): {calc.massive_transfusion_protocol(2000, 70)}")
    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()

"""
Blood Type Compatibility Calculator — Hematology
ABO/Rh compatibility for transfusion and organ donation.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from dataclasses import dataclass
from typing import List, Dict, Set
from enum import Enum


class ABOType(Enum):
    A = "A"
    B = "B"
    AB = "AB"
    O = "O"


class RhType(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"


@dataclass
class BloodTypeProfile:
    recipient_abo: ABOType
    recipient_rh: RhType
    donor_abo: ABOType
    donor_rh: RhType
    product: str = "prbc"  # prbc, plasma, platelets


@dataclass
class CompatibilityResult:
    compatible: bool
    emergency_compatible: bool  # O-negative for PRBC, AB for plasma
    compatibility_reason: str
    warnings: List[str]
    universal_donor: bool
    universal_recipient: bool


class BloodCompatibilityCalculator:
    """ABO/Rh blood compatibility checker."""

    def calculate(self, profile: BloodTypeProfile) -> CompatibilityResult:
        # ABO compatibility rules
        # PRBC: donor must have no antigens recipient doesn't have
        # O = no antigens, AB = A and B antigens
        recipient_antigens = set()
        if profile.recipient_abo in [ABOType.A, ABOType.AB]:
            recipient_antigens.add("A")
        if profile.recipient_abo in [ABOType.B, ABOType.AB]:
            recipient_antigens.add("B")

        donor_antigens = set()
        if profile.donor_abo in [ABOType.A, ABOType.AB]:
            donor_antigens.add("A")
        if profile.donor_abo in [ABOType.B, ABOType.AB]:
            donor_antigens.add("B")

        # Recipient can only receive antigens they have
        abo_compatible = donor_antigens.issubset(recipient_antigens)

        # Rh: Rh-negative can only receive Rh-negative; Rh-positive can receive either
        rh_compatible = (profile.recipient_rh == RhType.POSITIVE or
                         profile.donor_rh == RhType.NEGATIVE)

        compatible = abo_compatible and rh_compatible

        # Emergency compatibility
        if profile.product == "prbc":
            emergency = (profile.donor_abo == ABOType.O and
                        profile.donor_rh == RhType.NEGATIVE)
        elif profile.product == "plasma":
            emergency = profile.donor_abo == ABOType.AB
        else:
            emergency = compatible

        # Reason
        if not abo_compatible:
            reason = f"ABO incompatible: donor {profile.donor_abo.value} -> recipient {profile.recipient_abo.value}"
        elif not rh_compatible:
            reason = "Rh incompatible: Rh-negative recipient cannot receive Rh-positive"
        else:
            reason = f"Compatible: {profile.donor_abo.value}{'+' if profile.donor_rh == RhType.POSITIVE else '-'} -> {profile.recipient_abo.value}{'+' if profile.recipient_rh == RhType.POSITIVE else '-'}"

        warnings = []
        if profile.donor_rh == RhType.POSITIVE and profile.recipient_rh == RhType.NEGATIVE and profile.recipient_abo == ABOType.O:
            warnings.append("O-negative females of childbearing age should receive Rh-negative only")
        if profile.product == "platelets" and not compatible:
            warnings.append("Platelets: ABO incompatible may reduce increment but is acceptable in shortage")

        universal_donor = (profile.donor_abo == ABOType.O and profile.donor_rh == RhType.NEGATIVE)
        universal_recipient = (profile.recipient_abo == ABOType.AB and profile.recipient_rh == RhType.POSITIVE)

        return CompatibilityResult(
            compatible=compatible,
            emergency_compatible=emergency,
            compatibility_reason=reason,
            warnings=warnings,
            universal_donor=universal_donor,
            universal_recipient=universal_recipient
        )

    def get_compatible_donors(self, recipient_abo: ABOType, recipient_rh: RhType, product: str = "prbc") -> List[str]:
        """Return list of compatible donor types."""
        all_types = [(a, r) for a in ABOType for r in RhType]
        compatible = []
        for a, r in all_types:
            result = self.calculate(BloodTypeProfile(recipient_abo, recipient_rh, a, r, product))
            if result.compatible:
                compatible.append(f"{a.value}{'+' if r == RhType.POSITIVE else '-'}")
        return compatible


def run():
    calc = BloodCompatibilityCalculator()

    print("=" * 60)
    print("Blood Type Compatibility Calculator")
    print("=" * 60)

    pairs = [
        (ABOType.O, RhType.NEGATIVE, ABOType.O, RhType.NEGATIVE),
        (ABOType.A, RhType.POSITIVE, ABOType.O, RhType.POSITIVE),
        (ABOType.AB, RhType.POSITIVE, ABOType.A, RhType.POSITIVE),
        (ABOType.O, RhType.NEGATIVE, ABOType.A, RhType.POSITIVE),
    ]

    for rabo, rrh, dabo, drh in pairs:
        profile = BloodTypeProfile(rabo, rrh, dabo, drh)
        result = calc.calculate(profile)
        print(f"\n{dabo.value}{'+' if drh == RhType.POSITIVE else '-'} -> {rabo.value}{'+' if rrh == RhType.POSITIVE else '-'}: Compatible={result.compatible}")
        print(f"  Reason: {result.compatibility_reason}")

    print(f"\nCompatible donors for A+: {calc.get_compatible_donors(ABOType.A, RhType.POSITIVE)}")
    print(f"Compatible donors for O-: {calc.get_compatible_donors(ABOType.O, RhType.NEGATIVE)}")

    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()

"""Native stdlib module: Size Chart Generator
Generates size charts and grading rules for apparel production.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class SizeGrade:
    size: str
    chest_cm: float
    waist_cm: float
    hip_cm: float
    length_cm: float

@dataclass
class SizeChartGenerator:
    garment_type: str
    base_size: str
    sizes: List[SizeGrade] = field(default_factory=list)
    grade_increment_cm: float = 2.54

    def size_range(self) -> List[str]:
        return [s.size for s in self.sizes]

    def chest_range(self) -> tuple:
        chests = [s.chest_cm for s in self.sizes]
        return (min(chests), max(chests)) if chests else (0, 0)

    def waist_range(self) -> tuple:
        waists = [s.waist_cm for s in self.sizes]
        return (min(waists), max(waists)) if waists else (0, 0)

    def size_count(self) -> int:
        return len(self.sizes)

    def size_spread_cm(self) -> float:
        chest_range = self.chest_range()
        return chest_range[1] - chest_range[0]

    def stats(self) -> Dict:
        return {
            "garment": self.garment_type,
            "base_size": self.base_size,
            "size_count": self.size_count(),
            "sizes": self.size_range(),
            "chest_range_cm": self.chest_range(),
            "waist_range_cm": self.waist_range(),
            "size_spread_cm": round(self.size_spread_cm(), 1),
        }

def run():
    scg = SizeChartGenerator(
        garment_type="T-Shirt",
        base_size="M",
        sizes=[
            SizeGrade("XS", 86, 72, 88, 66),
            SizeGrade("S", 91, 77, 93, 68),
            SizeGrade("M", 96, 82, 98, 70),
            SizeGrade("L", 101, 87, 103, 72),
            SizeGrade("XL", 106, 92, 108, 74),
            SizeGrade("XXL", 111, 97, 113, 76),
        ]
    )
    print(scg.stats())

if __name__ == "__main__":
    run()

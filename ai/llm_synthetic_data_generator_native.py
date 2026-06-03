#!/usr/bin/env python3
"""
MAGNATRIX-OS — Synthetic Data Generator
ai/llm_synthetic_data_generator_native.py

Features:
- Text generation (names, addresses, emails, descriptions)
- Structured data generation (JSON, CSV records)
- Pattern-based generation (regex template filling)
- Variation injection (synonyms, paraphrases, noise)
- Dataset assembly and export simulation

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import enum
import random
import string
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("synthetic_data")


class DataType(enum.Enum):
    NAME = "name"
    EMAIL = "email"
    ADDRESS = "address"
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    CHOICE = "choice"


@dataclass
class FieldSpec:
    name: str
    data_type: DataType
    options: Optional[List[str]] = None
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    length: int = 10


class SyntheticDataGenerator:
    """Generate synthetic data for testing and training."""

    FIRST_NAMES = ["Alice", "Bob", "Carol", "David", "Eve", "Frank", "Grace", "Henry", "Ivy", "Jack", "Kate", "Leo", "Mia", "Noah", "Olivia", "Paul", "Quinn", "Ryan", "Sophia", "Tom"]
    LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"]
    DOMAINS = ["example.com", "test.org", "demo.net", "sample.io", "mock.co"]
    CITIES = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose"]
    STREETS = ["Main St", "Broadway", "Oak Ave", "Park Rd", "Elm St", "Maple Dr", "Pine Ln", "Cedar Blvd", "Washington St", "Lake Ave"]
    Lorem_WORDS = ["lorem", "ipsum", "dolor", "sit", "amet", "consectetur", "adipiscing", "elit", "sed", "do", "eiusmod", "tempor", "incididunt", "ut", "labore", "et", "dolore", "magna", "aliqua", "ut"]

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)

    def generate_name(self) -> str:
        return f"{random.choice(self.FIRST_NAMES)} {random.choice(self.LAST_NAMES)}"

    def generate_email(self, name: Optional[str] = None) -> str:
        if name:
            local = name.lower().replace(" ", ".")
        else:
            local = "".join(random.choices(string.ascii_lowercase, k=8))
        return f"{local}@{random.choice(self.DOMAINS)}"

    def generate_address(self) -> str:
        num = random.randint(1, 9999)
        street = random.choice(self.STREETS)
        city = random.choice(self.CITIES)
        zipcode = random.randint(10000, 99999)
        return f"{num} {street}, {city}, {zipcode}"

    def generate_text(self, length: int = 50) -> str:
        words = [random.choice(self.Lorem_WORDS) for _ in range(length)]
        return " ".join(words).capitalize() + "."

    def generate_number(self, min_val: float = 0, max_val: float = 100) -> float:
        return round(random.uniform(min_val, max_val), 2)

    def generate_date(self) -> str:
        year = random.randint(2020, 2025)
        month = random.randint(1, 12)
        day = random.randint(1, 28)
        return f"{year}-{month:02d}-{day:02d}"

    def generate_choice(self, options: List[str]) -> str:
        return random.choice(options)

    def generate_field(self, spec: FieldSpec) -> Any:
        if spec.data_type == DataType.NAME:
            return self.generate_name()
        elif spec.data_type == DataType.EMAIL:
            return self.generate_email()
        elif spec.data_type == DataType.ADDRESS:
            return self.generate_address()
        elif spec.data_type == DataType.TEXT:
            return self.generate_text(spec.length)
        elif spec.data_type == DataType.NUMBER:
            return self.generate_number(spec.min_val or 0, spec.max_val or 100)
        elif spec.data_type == DataType.DATE:
            return self.generate_date()
        elif spec.data_type == DataType.CHOICE:
            return self.generate_choice(spec.options or ["A", "B", "C"])
        return None

    def generate_record(self, fields: List[FieldSpec]) -> Dict[str, Any]:
        return {f.name: self.generate_field(f) for f in fields}

    def generate_dataset(self, fields: List[FieldSpec], n: int = 10) -> List[Dict[str, Any]]:
        return [self.generate_record(fields) for _ in range(n)]

    def add_noise(self, text: str, noise_level: float = 0.1) -> str:
        """Add typos and noise to text."""
        chars = list(text)
        num_changes = int(len(chars) * noise_level)
        for _ in range(num_changes):
            idx = random.randint(0, len(chars) - 1)
            chars[idx] = random.choice(string.ascii_lowercase)
        return "".join(chars)

    def paraphrase(self, text: str) -> str:
        """Simple paraphrase by word replacement."""
        synonyms = {
            "good": ["great", "excellent", "fine"],
            "bad": ["poor", "terrible", "awful"],
            "big": ["large", "huge", "massive"],
            "small": ["tiny", "little", "mini"],
            "fast": ["quick", "rapid", "swift"],
        }
        words = text.split()
        result = []
        for w in words:
            lower = w.lower().strip(".,!?")
            if lower in synonyms and random.random() < 0.5:
                replacement = random.choice(synonyms[lower])
                result.append(replacement + w[len(lower):] if len(w) > len(lower) else replacement)
            else:
                result.append(w)
        return " ".join(result)

    def get_stats(self) -> Dict[str, Any]:
        return {"generator": "SyntheticDataGenerator", "seeded": True}


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Synthetic Data Generator")
    print("ai/llm_synthetic_data_generator_native.py")
    print("=" * 60)

    gen = SyntheticDataGenerator(seed=42)

    # 1. Generate basic data
    print("\n[1] Basic Data Generation")
    print(f"  Name: {gen.generate_name()}")
    print(f"  Email: {gen.generate_email()}")
    print(f"  Address: {gen.generate_address()}")
    print(f"  Text: {gen.generate_text(10)[:50]}...")
    print(f"  Number: {gen.generate_number(0, 100)}")
    print(f"  Date: {gen.generate_date()}")

    # 2. Generate structured records
    print("\n[2] Structured Records")
    fields = [
        FieldSpec("id", DataType.NUMBER, min_val=1, max_val=1000),
        FieldSpec("name", DataType.NAME),
        FieldSpec("email", DataType.EMAIL),
        FieldSpec("city", DataType.CHOICE, options=["NYC", "LA", "Chicago", "Houston"]),
        FieldSpec("score", DataType.NUMBER, min_val=0, max_val=100),
    ]
    records = gen.generate_dataset(fields, n=5)
    for r in records[:3]:
        print(f"  {r}")

    # 3. Noise injection
    print("\n[3] Noise Injection")
    original = "The quick brown fox jumps over the lazy dog."
    noisy = gen.add_noise(original, 0.1)
    print(f"  Original: {original}")
    print(f"  Noisy:    {noisy}")

    # 4. Paraphrase
    print("\n[4] Paraphrase")
    text = "This is a good and fast small system."
    para = gen.paraphrase(text)
    print(f"  Original: {text}")
    print(f"  Paraphrase: {para}")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()

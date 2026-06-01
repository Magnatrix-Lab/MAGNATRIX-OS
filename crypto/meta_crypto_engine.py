#!/usr/bin/env python3
"""meta_crypto_engine.py — Auto-Coding Self-Improving Cryptographic Primitive Engine for MAGNATRIX-OS.

Generates, tests, and evolves cryptographic primitives from parameterized templates.
"""

from __future__ import annotations
import random, struct, time, hashlib, json, os, math, statistics
from typing import Dict, List, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum, auto


class PrimitiveFamily(Enum):
    HASH = auto()
    BLOCK_CIPHER = auto()
    STREAM_CIPHER = auto()
    MAC = auto()
    KDF = auto()


@dataclass
class PrimitiveSpec:
    id: str
    family: PrimitiveFamily
    generation: int
    parent_id: Optional[str]
    parameters: Dict[str, Any]
    score: float = 0.0
    lineage: List[str] = field(default_factory=list)


class PrimitiveGenerator:
    """Generate cryptographic primitives from templates."""

    def __init__(self):
        self._registry: List[PrimitiveSpec] = []
        self._counter = 0

    def _new_id(self, family: PrimitiveFamily) -> str:
        self._counter += 1
        return f"{family.name[:3]}-{self._counter}-{hashlib.sha256(str(time.time()).encode()).hexdigest()[:6]}"

    def generate_hash(self, parent: Optional[PrimitiveSpec] = None) -> Tuple[PrimitiveSpec, Callable]:
        params = {
            "block_size": random.choice([64, 128, 256]),
            "rounds": random.randint(8, 32),
            "state_size": random.choice([256, 512, 1024]),
            "padding": random.choice(["merkle-damgard", "sponge", "haifa"]),
        }
        if parent:
            params = self._mutate(params, parent.parameters)
        spec = PrimitiveSpec(
            id=self._new_id(PrimitiveFamily.HASH),
            family=PrimitiveFamily.HASH,
            generation=(parent.generation + 1) if parent else 0,
            parent_id=parent.id if parent else None,
            parameters=params,
            lineage=(parent.lineage + [parent.id]) if parent else [],
        )

        def hash_func(data: bytes) -> bytes:
            state = [0] * (params["state_size"] // 8)
            for i, b in enumerate(data):
                state[i % len(state)] ^= b
                for r in range(params["rounds"]):
                    idx = (i + r) % len(state)
                    state[idx] = ((state[idx] * 31 + r) ^ (state[idx] >> 3)) & 0xFF
            return bytes(state[:params["block_size"] // 8])

        self._registry.append(spec)
        return spec, hash_func

    def generate_block_cipher(self, parent: Optional[PrimitiveSpec] = None) -> Tuple[PrimitiveSpec, Callable]:
        params = {
            "block_size": random.choice([64, 128]),
            "key_size": random.choice([128, 256]),
            "rounds": random.randint(8, 24),
            "sbox_size": 8,
        }
        if parent:
            params = self._mutate(params, parent.parameters)
        spec = PrimitiveSpec(
            id=self._new_id(PrimitiveFamily.BLOCK_CIPHER),
            family=PrimitiveFamily.BLOCK_CIPHER,
            generation=(parent.generation + 1) if parent else 0,
            parent_id=parent.id if parent else None,
            parameters=params,
            lineage=(parent.lineage + [parent.id]) if parent else [],
        )
        sbox = list(range(256))
        random.shuffle(sbox)

        def cipher(block: bytes, key: bytes, encrypt: bool = True) -> bytes:
            out = bytearray(block)
            for r in range(params["rounds"]):
                for i in range(len(out)):
                    k = key[i % len(key)]
                    out[i] = sbox[(out[i] + k + r) % 256] if encrypt else sbox.index((out[i] + k + r) % 256)
            return bytes(out)
        self._registry.append(spec)
        return spec, cipher

    def generate_stream_cipher(self, parent: Optional[PrimitiveSpec] = None) -> Tuple[PrimitiveSpec, Callable]:
        params = {
            "state_size": random.choice([256, 512]),
            "rounds": random.randint(10, 30),
        }
        if parent:
            params = self._mutate(params, parent.parameters)
        spec = PrimitiveSpec(
            id=self._new_id(PrimitiveFamily.STREAM_CIPHER),
            family=PrimitiveFamily.STREAM_CIPHER,
            generation=(parent.generation + 1) if parent else 0,
            parent_id=parent.id if parent else None,
            parameters=params,
            lineage=(parent.lineage + [parent.id]) if parent else [],
        )

        def stream(key: bytes, length: int) -> bytes:
            state = list(key) + [0] * (params["state_size"] // 8 - len(key))
            out = bytearray()
            for _ in range(length):
                for r in range(params["rounds"]):
                    i = r % len(state)
                    state[i] = ((state[i] * 7 + r) ^ (state[i] >> 2)) & 0xFF
                out.append(state[0])
            return bytes(out)
        self._registry.append(spec)
        return spec, stream

    def _mutate(self, params: Dict[str, Any], parent_params: Dict[str, Any]) -> Dict[str, Any]:
        mutated = dict(parent_params)
        for k in list(mutated.keys()):
            if random.random() < 0.3:
                if isinstance(mutated[k], int):
                    mutated[k] = max(1, mutated[k] + random.randint(-4, 4))
                elif isinstance(mutated[k], str):
                    mutated[k] = random.choice(["merkle-damgard", "sponge", "haifa"])
        return mutated

    def get_registry(self) -> List[PrimitiveSpec]:
        return self._registry


class PropertyTester:
    """Statistical and structural tests for generated primitives."""

    def test_avalanche(self, hash_func: Callable, iterations: int = 100) -> float:
        """Flip 1 bit in input, measure output bit changes. Should be ~50%."""
        diffs = []
        for _ in range(iterations):
            data = bytes(random.randint(0, 255) for _ in range(32))
            h1 = hash_func(data)
            bit = random.randint(0, 255)
            modified = bytearray(data)
            modified[bit % len(modified)] ^= (1 << (bit % 8))
            h2 = hash_func(bytes(modified))
            diff_bits = sum(bin(b1 ^ b2).count("1") for b1, b2 in zip(h1, h2))
            total_bits = len(h1) * 8
            diffs.append(diff_bits / total_bits)
        return statistics.mean(diffs)

    def test_collision(self, hash_func: Callable, samples: int = 5000) -> float:
        """Birthday paradox simulation. Return collision rate."""
        outputs = set()
        for _ in range(samples):
            data = bytes(random.randint(0, 255) for _ in range(16))
            h = hash_func(data)[:8]
            outputs.add(h)
        return len(outputs) / samples

    def test_entropy(self, hash_func: Callable, samples: int = 1000) -> float:
        """Shannon entropy of outputs."""
        counts = [0] * 256
        for _ in range(samples):
            data = bytes(random.randint(0, 255) for _ in range(32))
            h = hash_func(data)
            for b in h:
                counts[b] += 1
        total = sum(counts)
        entropy = -sum((c / total) * math.log2(c / total) for c in counts if c > 0)
        return entropy / 8.0  # normalize to 0-1

    def test_frequency(self, hash_func: Callable, samples: int = 1000) -> float:
        """Chi-square-like frequency uniformity."""
        counts = [0] * 256
        for _ in range(samples):
            data = bytes(random.randint(0, 255) for _ in range(32))
            h = hash_func(data)
            for b in h:
                counts[b] += 1
        expected = sum(counts) / 256
        chi = sum((c - expected) ** 2 / expected for c in counts)
        return max(0.0, 1.0 - chi / 10000)


class FitnessScorer:
    def score(self, avalanche: float, collision: float, entropy: float, frequency: float) -> float:
        weights = {"avalanche": 0.35, "collision": 0.25, "entropy": 0.25, "frequency": 0.15}
        scores = {
            "avalanche": 1.0 - abs(avalanche - 0.5) * 2,
            "collision": collision,
            "entropy": entropy,
            "frequency": frequency,
        }
        return sum(scores[k] * weights[k] for k in weights)


class EvolutionEngine:
    def __init__(self, generator: PrimitiveGenerator, tester: PropertyTester, scorer: FitnessScorer):
        self.generator = generator
        self.tester = tester
        self.scorer = scorer

    def evolve(self, parent: PrimitiveSpec, generations: int = 2) -> PrimitiveSpec:
        best = parent
        best_score = parent.score
        for _ in range(generations):
            spec, hash_func = self.generator.generate_hash(parent=best)
            av = self.tester.test_avalanche(hash_func)
            col = self.tester.test_collision(hash_func)
            ent = self.tester.test_entropy(hash_func)
            freq = self.tester.test_frequency(hash_func)
            score = self.scorer.score(av, col, ent, freq)
            spec.score = score
            if score > best_score:
                best = spec
                best_score = score
        return best


class SelfValidator:
    def validate(self, spec: PrimitiveSpec, hash_func: Callable) -> List[str]:
        issues = []
        if spec.parameters.get("rounds", 0) < 4:
            issues.append("Too few rounds — vulnerable to differential cryptanalysis")
        if spec.parameters.get("state_size", 0) < 128:
            issues.append("State size too small — vulnerable to birthday attacks")
        outputs = set()
        for _ in range(100):
            data = bytes(random.randint(0, 255) for _ in range(16))
            outputs.add(hash_func(data)[:4])
        if len(outputs) < 90:
            issues.append("Low output diversity — potential collision weakness")
        return issues


class MetaCryptoEngine:
    def __init__(self):
        self.generator = PrimitiveGenerator()
        self.tester = PropertyTester()
        self.scorer = FitnessScorer()
        self.evolution = EvolutionEngine(self.generator, self.tester, self.scorer)
        self.validator = SelfValidator()

    def generate_and_evolve(self, family: PrimitiveFamily = PrimitiveFamily.HASH, generations: int = 2) -> PrimitiveSpec:
        if family == PrimitiveFamily.HASH:
            spec, hash_func = self.generator.generate_hash()
        elif family == PrimitiveFamily.BLOCK_CIPHER:
            spec, hash_func = self.generator.generate_block_cipher()
        elif family == PrimitiveFamily.STREAM_CIPHER:
            spec, hash_func = self.generator.generate_stream_cipher()
        else:
            spec, hash_func = self.generator.generate_hash()
        av = self.tester.test_avalanche(hash_func)
        col = self.tester.test_collision(hash_func)
        ent = self.tester.test_entropy(hash_func)
        freq = self.tester.test_frequency(hash_func)
        spec.score = self.scorer.score(av, col, ent, freq)
        issues = self.validator.validate(spec, hash_func)
        evolved = self.evolution.evolve(spec, generations=generations)
        return evolved

    def best_primitive(self, family: PrimitiveFamily = PrimitiveFamily.HASH) -> PrimitiveSpec:
        candidates = [p for p in self.generator.get_registry() if p.family == family]
        if not candidates:
            return self.generate_and_evolve(family)
        return max(candidates, key=lambda p: p.score)

    def report(self) -> str:
        lines = ["=== MetaCrypto Engine Report ==="]
        for p in self.generator.get_registry():
            lines.append(f"  {p.id} | gen={p.generation} | score={p.score:.3f} | {p.family.name} | rounds={p.parameters.get('rounds')}")
        return "\n".join(lines)


if __name__ == "__main__":
    engine = MetaCryptoEngine()
    print("=== Generating 3 hash variants ===")
    variants = []
    for i in range(3):
        v = engine.generate_and_evolve(PrimitiveFamily.HASH, generations=2)
        variants.append(v)
        print(f"  Variant {i+1}: {v.id} score={v.score:.3f} gen={v.generation}")
    best = engine.best_primitive(PrimitiveFamily.HASH)
    print(f"\nBest primitive: {best.id} score={best.score:.3f}")
    print(f"Parameters: {best.parameters}")
    print(f"Lineage: {' -> '.join(best.lineage + [best.id])}")
    print(f"\n{engine.report()}")

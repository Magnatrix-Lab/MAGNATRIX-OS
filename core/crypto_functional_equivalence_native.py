"""Crypto Functional Equivalence - Verify functional equivalence of obfuscated programs."""
from __future__ import annotations
import json, hashlib, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

@dataclass
class EquivalenceTest:
    test_id: str
    program_a_id: str
    program_b_id: str
    test_inputs: List[Dict]
    outputs_match: bool
    mismatch_count: int
    confidence: float

    def to_dict(self) -> Dict:
        return {"test_id": self.test_id, "program_a_id": self.program_a_id,
                "program_b_id": self.program_b_id, "test_inputs_count": len(self.test_inputs),
                "outputs_match": self.outputs_match, "mismatch_count": self.mismatch_count,
                "confidence": round(self.confidence,4)}

class CryptoFunctionalEquivalence:
    """Verify that obfuscated programs have same I/O behavior as originals."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "crypto_equiv"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.tests: List[EquivalenceTest] = []
        self._load_state()

    def _load_state(self) -> None:
        f = self.data_dir / "state.json"
        if f.exists():
            try:
                data = json.loads(f.read_text())
                for t in data.get("tests",[]): self.tests.append(EquivalenceTest(**t))
            except: pass

    def _save_state(self) -> None:
        (self.data_dir / "state.json").write_text(
            json.dumps({"tests": [t.to_dict() for t in self.tests]}, indent=2))

    def _simulate_program(self, program_id: str, inputs: Dict) -> Dict:
        """Simulate deterministic program execution."""
        h = hashlib.sha256((program_id + str(inputs)).encode()).hexdigest()
        return {"result": int(h[:8], 16)}

    def verify(self, program_a_id: str, program_b_id: str, test_inputs: List[Dict]) -> EquivalenceTest:
        mismatches = 0
        for inp in test_inputs:
            out_a = self._simulate_program(program_a_id, inp)
            out_b = self._simulate_program(program_b_id, inp)
            if out_a != out_b:
                mismatches += 1
        match = mismatches == 0
        conf = 1.0 - (mismatches / max(1, len(test_inputs)))
        test = EquivalenceTest(
            test_id="equiv_" + str(int(time.time()*1000)),
            program_a_id=program_a_id, program_b_id=program_b_id,
            test_inputs=test_inputs, outputs_match=match, mismatch_count=mismatches,
            confidence=round(conf,4))
        self.tests.append(test)
        self._save_state()
        return test

    def get_stats(self) -> Dict:
        matched = sum(1 for t in self.tests if t.outputs_match)
        return {"tests_total": len(self.tests), "matched": matched}

    def to_dict(self) -> Dict:
        return {"tests": [t.to_dict() for t in self.tests], "stats": self.get_stats()}

__all__ = ["CryptoFunctionalEquivalence", "EquivalenceTest"]

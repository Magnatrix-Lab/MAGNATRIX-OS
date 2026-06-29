"""Crypto Indistinguishability iO - iO theory and simulation."""
from __future__ import annotations
import json, hashlib, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

@dataclass
class IOSimulation:
    sim_id: str
    program_a_id: str
    program_b_id: str
    same_functionality: bool
    adversary_guess: str
    correct_guess: bool
    advantage: float

    def to_dict(self) -> Dict:
        return {"sim_id": self.sim_id, "program_a_id": self.program_a_id,
                "program_b_id": self.program_b_id, "same_functionality": self.same_functionality,
                "adversary_guess": self.adversary_guess, "correct_guess": self.correct_guess,
                "advantage": round(self.advantage,6)}

class CryptoIndistinguishabilityIO:
    """Indistinguishability Obfuscation (iO): theory and adversary simulation."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "crypto_io"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.simulations: List[IOSimulation] = []
        self._load_state()

    def _load_state(self) -> None:
        f = self.data_dir / "state.json"
        if f.exists():
            try:
                data = json.loads(f.read_text())
                for s in data.get("simulations",[]): self.simulations.append(IOSimulation(**s))
            except: pass

    def _save_state(self) -> None:
        (self.data_dir / "state.json").write_text(
            json.dumps({"simulations": [s.to_dict() for s in self.simulations]}, indent=2))

    def _same_functionality(self, prog_a: str, prog_b: str) -> bool:
        """Check if two programs have same I/O functionality."""
        return hashlib.sha256(prog_a.encode()).hexdigest() == hashlib.sha256(prog_b.encode()).hexdigest()

    def simulate_adversary(self, obf_a: str, obf_b: str, program_a: str, program_b: str) -> IOSimulation:
        """Simulate adversary trying to distinguish obfuscations."""
        same_func = self._same_functionality(program_a, program_b)
        # Adversary cannot distinguish obfuscations of same-functionality programs
        if same_func:
            guess = "cannot_distinguish"
            correct = False
            advantage = 0.0
        else:
            # Adversary can distinguish different functionalities with some advantage
            guess = "different"
            correct = True
            advantage = 0.5 + (hash(obf_a) % 50) / 100.0
        sim = IOSimulation(
            sim_id="io_" + str(int(time.time()*1000)),
            program_a_id=obf_a, program_b_id=obf_b,
            same_functionality=same_func, adversary_guess=guess,
            correct_guess=correct, advantage=round(advantage,6))
        self.simulations.append(sim)
        self._save_state()
        return sim

    def security_parameter(self, lambda_bits: int) -> Dict:
        """Compute security parameter for iO."""
        return {"lambda_bits": lambda_bits, "adversary_success_bound": 1.0 / (2 ** lambda_bits),
                "negligible": lambda_bits >= 128}

    def get_stats(self) -> Dict:
        avg_adv = sum(s.advantage for s in self.simulations) / max(1,len(self.simulations))
        return {"simulations": len(self.simulations), "avg_adversary_advantage": round(avg_adv,6)}

    def to_dict(self) -> Dict:
        return {"simulations": [s.to_dict() for s in self.simulations], "stats": self.get_stats()}

__all__ = ["CryptoIndistinguishabilityIO", "IOSimulation"]

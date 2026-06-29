"""Crypto Obfuscator - Program obfuscation engine simulating iO concepts."""
from __future__ import annotations
import json, hashlib, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Callable

@dataclass
class ObfuscatedProgram:
    obf_id: str
    original_hash: str
    encrypted_logic: str
    input_schema: Dict[str, str] = field(default_factory=dict)
    output_schema: Dict[str, str] = field(default_factory=dict)
    obfuscation_level: int = 1

    def to_dict(self) -> Dict:
        return {"obf_id": self.obf_id, "original_hash": self.original_hash,
                "encrypted_logic": self.encrypted_logic[:50] + "...",
                "input_schema": self.input_schema, "output_schema": self.output_schema,
                "obfuscation_level": self.obfuscation_level}

@dataclass
class ProgramSpec:
    spec_id: str
    name: str
    source_code: str
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {"spec_id": self.spec_id, "name": self.name,
                "source_hash": hashlib.sha256(self.source_code.encode()).hexdigest()[:16],
                "inputs": self.inputs, "outputs": self.outputs}

class CryptoObfuscator:
    """Program obfuscation engine implementing iO simulation concepts."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "crypto_obfuscator"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.programs: Dict[str, ObfuscatedProgram] = {}
        self.specs: Dict[str, ProgramSpec] = {}
        self._load_state()

    def _load_state(self) -> None:
        f = self.data_dir / "state.json"
        if f.exists():
            try:
                data = json.loads(f.read_text())
                for p in data.get("programs",[]): self.programs[p["obf_id"]] = ObfuscatedProgram(**p)
            except: pass

    def _save_state(self) -> None:
        (self.data_dir / "state.json").write_text(
            json.dumps({"programs": [p.to_dict() for p in self.programs.values()]}, indent=2))

    def _encrypt_logic(self, source: str, level: int) -> str:
        """Simulate logic encryption by iterative hashing."""
        enc = source
        for _ in range(level * 3):
            enc = hashlib.sha256(enc.encode()).hexdigest()
        return enc

    def obfuscate(self, spec: ProgramSpec, level: int = 1) -> ObfuscatedProgram:
        """Obfuscate a program: hide internals while preserving I/O."""
        orig_hash = hashlib.sha256(spec.source_code.encode()).hexdigest()[:16]
        enc_logic = self._encrypt_logic(spec.source_code, level)
        obf = ObfuscatedProgram(
            obf_id="obf_" + spec.spec_id + "_" + str(int(time.time())),
            original_hash=orig_hash, encrypted_logic=enc_logic,
            input_schema={i: "any" for i in spec.inputs},
            output_schema={o: "any" for o in spec.outputs},
            obfuscation_level=level)
        self.programs[obf.obf_id] = obf
        self.specs[spec.spec_id] = spec
        self._save_state()
        return obf

    def evaluate(self, obf_id: str, inputs: Dict) -> Optional[Dict]:
        """Simulate evaluating obfuscated program on inputs."""
        obf = self.programs.get(obf_id)
        if not obf: return None
        # Simulate deterministic output from inputs
        h = hashlib.sha256(str(inputs).encode()).hexdigest()
        outputs = {}
        for key in obf.output_schema:
            outputs[key] = int(h[:8], 16) % 1000
        return outputs

    def indistinguishability_check(self, obf_id1: str, obf_id2: str) -> Dict:
        """Check if two obfuscations are indistinguishable."""
        o1 = self.programs.get(obf_id1)
        o2 = self.programs.get(obf_id2)
        if not o1 or not o2: return {"error": "Missing obfuscation"}
        return {"obf_id1": obf_id1, "obf_id2": obf_id2,
                "indistinguishable": o1.encrypted_logic != o2.encrypted_logic,
                "same_level": o1.obfuscation_level == o2.obfuscation_level,
                "same_schema": o1.input_schema == o2.input_schema}

    def get_stats(self) -> Dict:
        return {"programs_obfuscated": len(self.programs), "avg_level": round(sum(p.obfuscation_level for p in self.programs.values())/max(1,len(self.programs)),2)}

    def to_dict(self) -> Dict:
        return {"programs": [p.to_dict() for p in self.programs.values()], "stats": self.get_stats()}

__all__ = ["CryptoObfuscator", "ObfuscatedProgram", "ProgramSpec"]

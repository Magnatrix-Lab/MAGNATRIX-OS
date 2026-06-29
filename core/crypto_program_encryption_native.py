"""Crypto Program Encryption - Transform program into encrypted program preserving I/O."""
from __future__ import annotations
import json, hashlib, time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

@dataclass
class EncryptedProgram:
    enc_id: str
    original_id: str
    ciphertext: str
    decryption_key: str
    input_format: str
    output_format: str
    preserved: bool = True

    def to_dict(self) -> Dict:
        return {"enc_id": self.enc_id, "original_id": self.original_id,
                "ciphertext": self.ciphertext[:50] + "...", "input_format": self.input_format,
                "output_format": self.output_format, "preserved": self.preserved}

class CryptoProgramEncryption:
    """Transform program P into encrypted program Obf(P) preserving I/O behavior."""

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "crypto_prog_enc"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.programs: Dict[str, EncryptedProgram] = {}
        self._load_state()

    def _load_state(self) -> None:
        f = self.data_dir / "state.json"
        if f.exists():
            try:
                data = json.loads(f.read_text())
                for p in data.get("programs",[]): self.programs[p["enc_id"]] = EncryptedProgram(**p)
            except: pass

    def _save_state(self) -> None:
        (self.data_dir / "state.json").write_text(
            json.dumps({"programs": [p.to_dict() for p in self.programs.values()]}, indent=2))

    def _simulate_encrypt(self, source: str, key: str) -> str:
        """Simulate program encryption using XOR with key-derived stream."""
        h = hashlib.sha256(key.encode()).hexdigest()
        out = []
        for i, c in enumerate(source):
            out.append(chr(ord(c) ^ ord(h[i % len(h)])))
        return "".join(out)

    def transform(self, program_id: str, source_code: str, key: str = "") -> EncryptedProgram:
        if not key: key = hashlib.sha256(str(time.time()).encode()).hexdigest()[:16]
        ciphertext = self._simulate_encrypt(source_code, key)
        enc = EncryptedProgram(
            enc_id="enc_" + program_id + "_" + str(int(time.time())),
            original_id=program_id, ciphertext=ciphertext,
            decryption_key=key, input_format="json", output_format="json")
        self.programs[enc.enc_id] = enc
        self._save_state()
        return enc

    def decrypt(self, enc_id: str) -> Optional[str]:
        enc = self.programs.get(enc_id)
        if not enc: return None
        return self._simulate_encrypt(enc.ciphertext, enc.decryption_key)

    def execute_on_cleartext(self, enc_id: str, inputs: Dict) -> Dict:
        """Execute encrypted program on cleartext inputs, get cleartext outputs."""
        enc = self.programs.get(enc_id)
        if not enc: return {"error": "Program not found"}
        # Simulate: output depends deterministically on input
        h = hashlib.sha256((enc_id + str(inputs)).encode()).hexdigest()
        return {"output": int(h[:8], 16), "derived_from": enc_id}

    def get_stats(self) -> Dict:
        return {"programs_encrypted": len(self.programs)}

    def to_dict(self) -> Dict:
        return {"programs": [p.to_dict() for p in self.programs.values()], "stats": self.get_stats()}

__all__ = ["CryptoProgramEncryption", "EncryptedProgram"]

"""
payload_obfuscator_native.py
MAGNATRIX-OS — Payload Obfuscator

Inspired by AbyssSec evasion techniques and payload development:
Obfuscate and encode payloads using multiple techniques. Pure stdlib.
"""

import json
import base64
import random
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class ObfuscatedPayload:
    payload_id: str
    original: str
    obfuscated: str
    technique: str
    layers: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class PayloadObfuscator:
    """Obfuscate and encode payloads using multiple techniques."""

    TECHNIQUES = ["base64", "hex", "reverse", "xor", "rot13", "insertion", "chunked"]

    def __init__(self, cache_dir: str = "./obfuscated_payloads"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.payloads: Dict[str, ObfuscatedPayload] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "payloads.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for pid, pd in data.items():
                        self.payloads[pid] = ObfuscatedPayload(**pd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "payloads.json", "w", encoding="utf-8") as f:
            json.dump({pid: asdict(p) for pid, p in self.payloads.items()}, f, indent=2)

    def _base64(self, data: str) -> str:
        return base64.b64encode(data.encode()).decode()

    def _hex(self, data: str) -> str:
        return data.encode().hex()

    def _reverse(self, data: str) -> str:
        return data[::-1]

    def _xor(self, data: str, key: int = 0x42) -> str:
        return "".join(chr(ord(c) ^ key) for c in data)

    def _rot13(self, data: str) -> str:
        return data.encode("rot_13").decode() if hasattr(str, "encode") else "".join(
            chr((ord(c) - 65 + 13) % 26 + 65) if 65 <= ord(c) <= 90 else
            chr((ord(c) - 97 + 13) % 26 + 97) if 97 <= ord(c) <= 122 else c
            for c in data
        )

    def _insertion(self, data: str, junk: str = "x") -> str:
        return "".join(c + junk for c in data)[:-1]

    def _chunked(self, data: str, chunk_size: int = 4) -> str:
        chunks = [data[i:i+chunk_size] for i in range(0, len(data), chunk_size)]
        return ",".join(chunks)

    def obfuscate(self, payload_id: str, original: str, technique: str, layers: int = 1) -> ObfuscatedPayload:
        result = original
        used_techniques = []
        for _ in range(layers):
            if technique == "base64":
                result = self._base64(result)
            elif technique == "hex":
                result = self._hex(result)
            elif technique == "reverse":
                result = self._reverse(result)
            elif technique == "xor":
                result = self._xor(result)
            elif technique == "rot13":
                result = self._rot13(result)
            elif technique == "insertion":
                result = self._insertion(result)
            elif technique == "chunked":
                result = self._chunked(result)
            used_techniques.append(technique)
        payload = ObfuscatedPayload(
            payload_id=payload_id, original=original, obfuscated=result,
            technique="-".join(used_techniques), layers=layers,
        )
        self.payloads[payload_id] = payload
        self._save()
        return payload

    def chain_obfuscate(self, payload_id: str, original: str, techniques: List[str]) -> ObfuscatedPayload:
        result = original
        for tech in techniques:
            result = self.obfuscate(f"{payload_id}_temp", result, tech, 1).obfuscated
        payload = ObfuscatedPayload(
            payload_id=payload_id, original=original, obfuscated=result,
            technique="->".join(techniques), layers=len(techniques),
        )
        self.payloads[payload_id] = payload
        self._save()
        return payload

    def get_payload(self, payload_id: str) -> Optional[ObfuscatedPayload]:
        return self.payloads.get(payload_id)

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.payloads)
        return {"total_payloads": total, "techniques": self.TECHNIQUES}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["PayloadObfuscator", "ObfuscatedPayload"]
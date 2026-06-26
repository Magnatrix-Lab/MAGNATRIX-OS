#!/usr/bin/env python3
"""Secret Rotation Engine for MAGNATRIX-OS — Auto-rotate credentials."""
from __future__ import annotations
import hashlib, hmac, secrets, time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

@dataclass
class Secret:
    name: str
    value: str
    created_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    version: int = 1

class SecretRotationEngine:
    def __init__(self, rotation_interval: int = 86400) -> None:
        self._secrets: Dict[str, Secret] = {}
        self._rotation_interval = rotation_interval

    def generate(self, name: str, length: int = 32) -> Secret:
        value = secrets.token_urlsafe(length)
        secret = Secret(name=name, value=value, expires_at=time.time() + self._rotation_interval)
        self._secrets[name] = secret
        return secret

    def rotate(self, name: str) -> Optional[Secret]:
        old = self._secrets.get(name)
        if old:
            new = self.generate(name)
            new.version = old.version + 1
            return new
        return None

    def get(self, name: str) -> Optional[str]:
        s = self._secrets.get(name)
        return s.value if s else None

    def needs_rotation(self, name: str) -> bool:
        s = self._secrets.get(name)
        return s is not None and time.time() > s.expires_at

    def stats(self) -> Dict[str, Any]:
        return {"secrets": len(self._secrets), "needs_rotation": sum(1 for n in self._secrets if self.needs_rotation(n))}

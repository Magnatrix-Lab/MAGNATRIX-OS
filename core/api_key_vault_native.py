"""
api_key_vault_native.py
MAGNATRIX-OS — API Key Vault

Secure API key storage with rotation and encryption simulation. Pure stdlib.
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta


@dataclass
class VaultKey:
    key_id: str
    provider: str
    key_hash: str
    key_preview: str
    created_at: str
    last_rotated: str
    usage_count: int
    is_active: bool
    expires_at: str


class APIKeyVault:
    """Secure API key storage with rotation tracking."""

    def __init__(self, vault_dir: str = "./api_key_vault"):
        self.vault_dir = Path(vault_dir)
        self.vault_dir.mkdir(exist_ok=True)
        self.keys: Dict[str, VaultKey] = {}
        self._load()

    def _hash(self, key: str) -> str:
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def _preview(self, key: str) -> str:
        if len(key) <= 8:
            return "****"
        return key[:4] + "****" + key[-4:]

    def _load(self) -> None:
        file = self.vault_dir / "keys.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for kid, kd in data.items():
                        self.keys[kid] = VaultKey(**kd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.vault_dir / "keys.json", "w", encoding="utf-8") as f:
            json.dump({kid: asdict(k) for kid, k in self.keys.items()}, f, indent=2)

    def store(self, key_id: str, provider: str, key: str, expires_days: int = 30) -> VaultKey:
        now = datetime.now().isoformat()
        expires = (datetime.now() + timedelta(days=expires_days)).isoformat()
        vault_key = VaultKey(
            key_id=key_id, provider=provider, key_hash=self._hash(key),
            key_preview=self._preview(key), created_at=now, last_rotated=now,
            usage_count=0, is_active=True, expires_at=expires,
        )
        self.keys[key_id] = vault_key
        self._save()
        return vault_key

    def rotate(self, key_id: str, new_key: str) -> Optional[VaultKey]:
        k = self.keys.get(key_id)
        if not k:
            return None
        k.key_hash = self._hash(new_key)
        k.key_preview = self._preview(new_key)
        k.last_rotated = datetime.now().isoformat()
        k.usage_count = 0
        self._save()
        return k

    def use_key(self, key_id: str) -> bool:
        k = self.keys.get(key_id)
        if not k or not k.is_active:
            return False
        k.usage_count += 1
        self._save()
        return True

    def revoke(self, key_id: str) -> bool:
        k = self.keys.get(key_id)
        if not k:
            return False
        k.is_active = False
        self._save()
        return True

    def get_key(self, key_id: str) -> Optional[VaultKey]:
        return self.keys.get(key_id)

    def get_active_keys(self) -> List[VaultKey]:
        return [k for k in self.keys.values() if k.is_active]

    def get_stats(self) -> Dict[str, Any]:
        active = sum(1 for k in self.keys.values() if k.is_active)
        total_usage = sum(k.usage_count for k in self.keys.values())
        return {"total_keys": len(self.keys), "active": active, "revoked": len(self.keys) - active, "total_usage": total_usage}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["APIKeyVault", "VaultKey"]
#!/usr/bin/env python3
"""
Secret Manager for MAGNATRIX-OS
Secure storage, rotation, and retrieval of API keys, credentials,
tokens, and sensitive configuration. Uses native cryptography only.
Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import base64
import dataclasses
import enum
import hashlib
import json
import os
import secrets
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


# ---------------------------------------------------------------------------
# Native cryptography helpers (no external deps)
# ---------------------------------------------------------------------------

def _derive_key(password: str, salt: bytes, iterations: int = 100_000) -> bytes:
    """PBKDF2-HMAC-SHA256 key derivation."""
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations, dklen=32)


def _xor_encrypt(data: bytes, key: bytes) -> bytes:
    """Simple XOR-based encryption for native-only operation.
    Not for production-grade security but sufficient for local secret vaulting."""
    key_cycle = key * (len(data) // len(key) + 1)
    return bytes(b ^ key_cycle[i] for i, b in enumerate(data))


class SecretScope(enum.Enum):
    """Scope defines where a secret can be read from."""
    GLOBAL = "global"
    SESSION = "session"
    MODULE = "module"
    USER = "user"


class SecretType(enum.Enum):
    """Classification of secret payload."""
    API_KEY = "api_key"
    TOKEN = "token"
    PASSWORD = "password"
    CERTIFICATE = "certificate"
    CONFIG_VALUE = "config_value"


@dataclasses.dataclass
class SecretRecord:
    """A single encrypted secret entry."""
    secret_id: str
    name: str
    secret_type: SecretType
    scope: SecretScope
    encrypted_payload: str  # base64(xor_encrypted(ciphertext))
    salt: str  # base64
    iterations: int
    checksum: str  # SHA-256 of original payload for integrity
    created_at: float
    expires_at: Optional[float] = None
    last_accessed: Optional[float] = None
    access_count: int = 0
    tags: Set[str] = dataclasses.field(default_factory=set)
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "secret_id": self.secret_id,
            "name": self.name,
            "secret_type": self.secret_type.value,
            "scope": self.scope.value,
            "encrypted_payload": self.encrypted_payload,
            "salt": self.salt,
            "iterations": self.iterations,
            "checksum": self.checksum,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "tags": sorted(self.tags),
            "metadata": self.metadata,
        }


class SecretManager:
    """Vault for secrets with master-password protection and scoping."""

    def __init__(self, vault_path: str = "./vault", master_password: str = "default") -> None:
        self.vault_path = Path(vault_path)
        self.master_password = master_password
        self._secrets: Dict[str, SecretRecord] = {}
        self._load()

    # ------------------------------------------------------------------
    # Core vault operations
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if not self.vault_path.exists():
            return
        try:
            with open(self.vault_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return
        for item in data:
            record = SecretRecord(
                secret_id=item["secret_id"],
                name=item["name"],
                secret_type=SecretType(item["secret_type"]),
                scope=SecretScope(item["scope"]),
                encrypted_payload=item["encrypted_payload"],
                salt=item["salt"],
                iterations=item["iterations"],
                checksum=item["checksum"],
                created_at=item["created_at"],
                expires_at=item.get("expires_at"),
                last_accessed=item.get("last_accessed"),
                access_count=item.get("access_count", 0),
                tags=set(item.get("tags", [])),
                metadata=item.get("metadata", {}),
            )
            self._secrets[record.secret_id] = record

    def _save(self) -> None:
        data = [s.to_dict() for s in self._secrets.values()]
        self.vault_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.vault_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _encrypt(self, plaintext: str) -> Tuple[str, str, int]:
        salt = secrets.token_bytes(16)
        key = _derive_key(self.master_password, salt)
        ciphertext = _xor_encrypt(plaintext.encode("utf-8"), key)
        checksum = hashlib.sha256(plaintext.encode("utf-8")).hexdigest()
        return base64.b64encode(ciphertext).decode(), base64.b64encode(salt).decode(), 100_000

    def _decrypt(self, record: SecretRecord) -> str:
        salt = base64.b64decode(record.salt)
        key = _derive_key(self.master_password, salt)
        ciphertext = base64.b64decode(record.encrypted_payload)
        plaintext = _xor_encrypt(ciphertext, key).decode("utf-8")
        # Integrity check
        if hashlib.sha256(plaintext.encode("utf-8")).hexdigest() != record.checksum:
            raise ValueError("Secret integrity check failed — wrong master password or tampering detected")
        return plaintext

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def store(
        self,
        secret_id: str,
        name: str,
        payload: str,
        secret_type: SecretType = SecretType.CONFIG_VALUE,
        scope: SecretScope = SecretScope.GLOBAL,
        expires_in_seconds: Optional[int] = None,
        tags: Optional[Set[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SecretRecord:
        if secret_id in self._secrets:
            raise ValueError(f"Secret '{secret_id}' already exists")
        enc, salt, iters = self._encrypt(payload)
        checksum = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        record = SecretRecord(
            secret_id=secret_id,
            name=name,
            secret_type=secret_type,
            scope=scope,
            encrypted_payload=enc,
            salt=salt,
            iterations=iters,
            checksum=checksum,
            created_at=time.time(),
            expires_at=time.time() + expires_in_seconds if expires_in_seconds else None,
            tags=tags or set(),
            metadata=metadata or {},
        )
        self._secrets[secret_id] = record
        self._save()
        return record

    def retrieve(self, secret_id: str) -> str:
        record = self._secrets.get(secret_id)
        if not record:
            raise KeyError(f"Secret '{secret_id}' not found")
        if record.expires_at and time.time() > record.expires_at:
            raise RuntimeError(f"Secret '{secret_id}' has expired")
        plaintext = self._decrypt(record)
        record.access_count += 1
        record.last_accessed = time.time()
        self._save()
        return plaintext

    def delete(self, secret_id: str) -> bool:
        if secret_id in self._secrets:
            del self._secrets[secret_id]
            self._save()
            return True
        return False

    def rotate(self, secret_id: str, new_payload: str) -> SecretRecord:
        """Re-encrypt a secret with a fresh salt (key rotation)."""
        old = self._secrets.get(secret_id)
        if not old:
            raise KeyError(f"Secret '{secret_id}' not found")
        enc, salt, iters = self._encrypt(new_payload)
        checksum = hashlib.sha256(new_payload.encode("utf-8")).hexdigest()
        old.encrypted_payload = enc
        old.salt = salt
        old.iterations = iters
        old.checksum = checksum
        old.created_at = time.time()
        self._save()
        return old

    def list_all(self) -> List[SecretRecord]:
        return list(self._secrets.values())

    def list_by_scope(self, scope: SecretScope) -> List[SecretRecord]:
        return [s for s in self._secrets.values() if s.scope == scope]

    def list_by_type(self, secret_type: SecretType) -> List[SecretRecord]:
        return [s for s in self._secrets.values() if s.secret_type == secret_type]

    def search(self, keyword: str) -> List[SecretRecord]:
        kw = keyword.lower()
        return [s for s in self._secrets.values() if kw in s.name.lower() or kw in s.secret_id.lower() or any(kw in t.lower() for t in s.tags)]

    def is_expired(self, secret_id: str) -> bool:
        record = self._secrets.get(secret_id)
        if not record or not record.expires_at:
            return False
        return time.time() > record.expires_at

    def stats(self) -> Dict[str, Any]:
        total = len(self._secrets)
        by_scope: Dict[str, int] = {}
        by_type: Dict[str, int] = {}
        expired = 0
        for s in self._secrets.values():
            by_scope[s.scope.value] = by_scope.get(s.scope.value, 0) + 1
            by_type[s.secret_type.value] = by_type.get(s.secret_type.value, 0) + 1
            if s.expires_at and time.time() > s.expires_at:
                expired += 1
        return {
            "total_secrets": total,
            "by_scope": by_scope,
            "by_type": by_type,
            "expired": expired,
            "vault_path": str(self.vault_path),
        }

    def export_plaintext_backup(self, export_path: str) -> None:
        """Emergency export — decrypts everything and writes JSON. Requires master password."""
        export: Dict[str, str] = {}
        for sid in self._secrets:
            export[sid] = self.retrieve(sid)
        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(export, f, indent=2, ensure_ascii=False)

    def change_master_password(self, new_password: str) -> None:
        """Re-encrypt the entire vault with a new master password."""
        plaintexts = {sid: self.retrieve(sid) for sid in self._secrets}
        self.master_password = new_password
        for sid, payload in plaintexts.items():
            self.rotate(sid, payload)


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    vault_file = "/tmp/magnatrix_secrets.json"
    if os.path.exists(vault_file):
        os.remove(vault_file)
    mgr = SecretManager(vault_file, master_password="MAGNATRIX_MASTER_2024")
    print("=== Secret Manager Demo ===\n")
    # Store some secrets
    mgr.store("openai_api_key", "OpenAI API Key", "sk-xxxxxxxxxxxxxxxx", SecretType.API_KEY, scope=SecretScope.GLOBAL, tags={"llm", "external"})
    mgr.store("internal_token", "Service Token", "tok_abc123", SecretType.TOKEN, scope=SecretScope.SESSION, expires_in_seconds=3600, tags={"internal"})
    mgr.store("db_password", "Database Password", "SuperSecret123!", SecretType.PASSWORD, scope=SecretScope.MODULE, tags={"database", "critical"})
    print(f"Stored {len(mgr.list_all())} secrets")
    # Retrieve
    print(f"\nRetrieve openai_api_key: {mgr.retrieve('openai_api_key')[:10]}...")
    print(f"Retrieve internal_token: {mgr.retrieve('internal_token')}")
    # Stats
    print(f"\nStats: {mgr.stats()}")
    # Search
    print(f"Search 'api': {[s.name for s in mgr.search('api')]}")
    # Cleanup
    os.remove(vault_file)
    print("\nVault cleaned up.")


if __name__ == "__main__":
    _demo()

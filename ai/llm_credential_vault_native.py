"""Credential Vault — Encrypted credential storage, rotation, and access control.

Modul ini menyediakan:
- CredentialVault untuk encrypted storage credentials
- RotationEngine untuk auto-rotate credentials
- AccessControl untuk role-based access ke credentials
- AuditTrail untuk logging access credential
- VaultManager untuk end-to-end vault management
"""

from __future__ import annotations

import json
import time
import uuid
import base64
import hashlib
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from enum import Enum, auto


class CredentialType(Enum):
    API_KEY = auto()
    PASSWORD = auto()
    TOKEN = auto()
    CERTIFICATE = auto()
    SSH_KEY = auto()
    ENV_VAR = auto()


class AccessLevel(Enum):
    NONE = 0
    READ = 1
    WRITE = 2
    ADMIN = 3


@dataclass
class Credential:
    """Stored credential with metadata."""
    credential_id: str
    name: str
    credential_type: CredentialType
    value: str  # encrypted value
    salt: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    last_rotated: float = field(default_factory=time.time)
    rotation_count: int = 0
    access_log: List[Dict[str, Any]] = field(default_factory=list)

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    def days_until_expiry(self) -> Optional[float]:
        if self.expires_at is None:
            return None
        return (self.expires_at - time.time()) / 86400


class CredentialVault:
    """Encrypted credential storage."""

    def __init__(self, master_key: Optional[str] = None):
        self.master_key = master_key or str(uuid.uuid4())
        self._credentials: Dict[str, Credential] = {}
        self._by_type: Dict[CredentialType, List[str]] = {}
        self._by_name: Dict[str, str] = {}

    def _encrypt(self, value: str, salt: str) -> str:
        # Simple XOR encryption with key derivation (for demo)
        key = hashlib.sha256((self.master_key + salt).encode()).digest()
        encrypted = bytes(v ^ key[i % len(key)] for i, v in enumerate(value.encode()))
        return base64.b64encode(encrypted).decode()

    def _decrypt(self, encrypted: str, salt: str) -> str:
        key = hashlib.sha256((self.master_key + salt).encode()).digest()
        data = base64.b64decode(encrypted.encode())
        return bytes(d ^ key[i % len(key)] for i, d in enumerate(data)).decode()

    def store(self, name: str, credential_type: CredentialType, value: str,
              metadata: Optional[Dict[str, Any]] = None, ttl_days: Optional[int] = None) -> Credential:
        salt = str(uuid.uuid4())[:16]
        encrypted = self._encrypt(value, salt)
        expires = time.time() + (ttl_days * 86400) if ttl_days else None
        cred = Credential(
            credential_id=str(uuid.uuid4())[:12],
            name=name,
            credential_type=credential_type,
            value=encrypted,
            salt=salt,
            metadata=metadata or {},
            expires_at=expires,
        )
        self._credentials[cred.credential_id] = cred
        self._by_type.setdefault(credential_type, []).append(cred.credential_id)
        self._by_name[name] = cred.credential_id
        return cred

    def retrieve(self, credential_id: str, accessor: str = "system") -> Optional[str]:
        cred = self._credentials.get(credential_id)
        if not cred:
            return None
        if cred.is_expired():
            return None
        cred.access_log.append({"accessor": accessor, "timestamp": time.time(), "action": "read"})
        return self._decrypt(cred.value, cred.salt)

    def get_by_name(self, name: str, accessor: str = "system") -> Optional[str]:
        cid = self._by_name.get(name)
        if cid:
            return self.retrieve(cid, accessor)
        return None

    def update(self, credential_id: str, new_value: str) -> bool:
        cred = self._credentials.get(credential_id)
        if not cred:
            return False
        salt = str(uuid.uuid4())[:16]
        cred.value = self._encrypt(new_value, salt)
        cred.salt = salt
        cred.last_rotated = time.time()
        cred.rotation_count += 1
        return True

    def delete(self, credential_id: str) -> bool:
        cred = self._credentials.pop(credential_id, None)
        if cred:
            self._by_type.get(cred.credential_type, []).remove(credential_id)
            self._by_name.pop(cred.name, None)
            return True
        return False

    def list_all(self) -> List[Credential]:
        return list(self._credentials.values())

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._credentials)
        expired = sum(1 for c in self._credentials.values() if c.is_expired())
        return {
            "total": total,
            "expired": expired,
            "active": total - expired,
            "by_type": {k.name: len(v) for k, v in self._by_type.items()},
        }


class AccessControl:
    """Role-based access control for credentials."""

    def __init__(self):
        self._permissions: Dict[str, Dict[str, AccessLevel]] = {}  # user -> {cred_id -> level}
        self._roles: Dict[str, Set[str]] = {}  # role -> set of users

    def grant(self, user: str, credential_id: str, level: AccessLevel) -> None:
        self._permissions.setdefault(user, {})[credential_id] = level

    def revoke(self, user: str, credential_id: str) -> None:
        perms = self._permissions.get(user, {})
        perms.pop(credential_id, None)

    def check(self, user: str, credential_id: str, required: AccessLevel) -> bool:
        level = self._permissions.get(user, {}).get(credential_id, AccessLevel.NONE)
        return level.value >= required.value

    def get_accessible(self, user: str, required: AccessLevel = AccessLevel.READ) -> List[str]:
        return [cid for cid, level in self._permissions.get(user, {}).items() if level.value >= required.value]

    def add_role(self, role: str, users: List[str]) -> None:
        self._roles[role] = set(users)

    def grant_role(self, role: str, credential_id: str, level: AccessLevel) -> None:
        for user in self._roles.get(role, set()):
            self.grant(user, credential_id, level)


class RotationEngine:
    """Auto-rotate credentials on schedule."""

    def __init__(self, default_ttl_days: int = 90):
        self.default_ttl = default_ttl_days
        self._generators: Dict[CredentialType, Callable[[], str]] = {}

    def set_generator(self, cred_type: CredentialType, generator: Callable[[], str]) -> None:
        self._generators[cred_type] = generator

    def should_rotate(self, cred: Credential) -> bool:
        days = cred.days_until_expiry()
        if days is None:
            return False
        return days <= 7  # Rotate within 7 days of expiry

    def rotate(self, vault: CredentialVault, credential_id: str) -> Optional[str]:
        cred = vault._credentials.get(credential_id)
        if not cred:
            return None
        generator = self._generators.get(cred.credential_type)
        if not generator:
            return None
        new_value = generator()
        vault.update(credential_id, new_value)
        return new_value

    def rotate_all(self, vault: CredentialVault) -> Dict[str, str]:
        rotated = {}
        for cid, cred in vault._credentials.items():
            if self.should_rotate(cred):
                new_val = self.rotate(vault, cid)
                if new_val:
                    rotated[cid] = new_val
        return rotated

    def get_rotation_report(self, vault: CredentialVault) -> Dict[str, Any]:
        report = []
        for cred in vault.list_all():
            days = cred.days_until_expiry()
            report.append({
                "name": cred.name,
                "days_until_expiry": round(days, 1) if days else None,
                "needs_rotation": self.should_rotate(cred),
                "rotation_count": cred.rotation_count,
            })
        return {"credentials": report}


class AuditTrail:
    """Audit logging for credential access."""

    def __init__(self, retention_days: int = 90):
        self.retention_days = retention_days
        self._events: List[Dict[str, Any]] = []

    def log(self, action: str, credential_id: str, user: str, success: bool, details: str = "") -> None:
        event = {
            "event_id": str(uuid.uuid4())[:12],
            "timestamp": time.time(),
            "action": action,
            "credential_id": credential_id,
            "user": user,
            "success": success,
            "details": details,
        }
        self._events.append(event)
        cutoff = time.time() - (self.retention_days * 86400)
        self._events = [e for e in self._events if e["timestamp"] > cutoff]

    def get_events(self, credential_id: Optional[str] = None, user: Optional[str] = None) -> List[Dict[str, Any]]:
        events = self._events
        if credential_id:
            events = [e for e in events if e["credential_id"] == credential_id]
        if user:
            events = [e for e in events if e["user"] == user]
        return events

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._events)
        return {
            "total_events": total,
            "read_events": sum(1 for e in self._events if e["action"] == "read"),
            "write_events": sum(1 for e in self._events if e["action"] == "write"),
            "failed_events": sum(1 for e in self._events if not e["success"]),
        }

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self._events, f, indent=2)


class VaultManager:
    """End-to-end credential vault management."""

    def __init__(self, master_key: Optional[str] = None):
        self.vault = CredentialVault(master_key)
        self.access = AccessControl()
        self.rotation = RotationEngine()
        self.audit = AuditTrail()

    def store(self, name: str, cred_type: CredentialType, value: str, user: str = "admin",
              metadata: Optional[Dict[str, Any]] = None, ttl_days: Optional[int] = None) -> Credential:
        cred = self.vault.store(name, cred_type, value, metadata, ttl_days)
        self.access.grant(user, cred.credential_id, AccessLevel.ADMIN)
        self.audit.log("write", cred.credential_id, user, True, "Credential created")
        return cred

    def retrieve(self, name: str, user: str = "system") -> Optional[str]:
        cid = self.vault._by_name.get(name)
        if not cid:
            self.audit.log("read", name, user, False, "Credential not found")
            return None
        if not self.access.check(user, cid, AccessLevel.READ):
            self.audit.log("read", cid, user, False, "Access denied")
            return None
        value = self.vault.retrieve(cid, user)
        self.audit.log("read", cid, user, value is not None, "Retrieved credential" if value else "Expired")
        return value

    def rotate(self, name: str, user: str = "admin") -> Optional[str]:
        cid = self.vault._by_name.get(name)
        if not cid:
            return None
        if not self.access.check(user, cid, AccessLevel.WRITE):
            self.audit.log("write", cid, user, False, "Access denied for rotation")
            return None
        new_val = self.rotation.rotate(self.vault, cid)
        self.audit.log("write", cid, user, True, "Credential rotated")
        return new_val

    def get_stats(self) -> Dict[str, Any]:
        return {
            "vault": self.vault.get_stats(),
            "audit": self.audit.get_stats(),
        }

    def export_report(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "vault_stats": self.vault.get_stats(),
                "rotation_report": self.rotation.get_rotation_report(self.vault),
                "audit_stats": self.audit.get_stats(),
            }, f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("CREDENTIAL VAULT DEMO")
    print("=" * 70)

    # 1. Store credentials
    print("\n[1] Store Credentials")
    manager = VaultManager(master_key="magnatrix-secret-key-2024")
    cred1 = manager.store("openai-api-key", CredentialType.API_KEY, "sk-1234567890abcdef", "admin",
                          metadata={"provider": "openai", "model": "gpt-4"}, ttl_days=30)
    cred2 = manager.store("db-password", CredentialType.PASSWORD, "SuperSecret123!", "admin",
                          metadata={"db": "postgres", "host": "localhost"}, ttl_days=90)
    cred3 = manager.store("jwt-secret", CredentialType.TOKEN, "jwt-secret-xyz", "admin", ttl_days=7)
    print(f"  Stored: {cred1.name} (expires in {cred1.days_until_expiry():.1f} days)")
    print(f"  Stored: {cred2.name} (expires in {cred2.days_until_expiry():.1f} days)")
    print(f"  Stored: {cred3.name} (expires in {cred3.days_until_expiry():.1f} days)")

    # 2. Retrieve
    print("\n[2] Retrieve Credentials")
    val = manager.retrieve("openai-api-key", "admin")
    print(f"  openai-api-key: {val}")
    val2 = manager.retrieve("db-password", "admin")
    print(f"  db-password: {val2}")

    # 3. Access control
    print("\n[3] Access Control")
    manager.access.grant("developer", cred1.credential_id, AccessLevel.READ)
    manager.access.grant("developer", cred2.credential_id, AccessLevel.READ)
    print(f"  Developer can read openai: {manager.access.check('developer', cred1.credential_id, AccessLevel.READ)}")
    print(f"  Developer can write openai: {manager.access.check('developer', cred1.credential_id, AccessLevel.WRITE)}")

    # 4. Rotation
    print("\n[4] Rotation")
    manager.rotation.set_generator(CredentialType.API_KEY, lambda: f"sk-{uuid.uuid4().hex[:16]}")
    report = manager.rotation.get_rotation_report(manager.vault)
    for r in report["credentials"]:
        print(f"  {r['name']}: days_left={r['days_until_expiry']}, needs_rotation={r['needs_rotation']}")
    new_val = manager.rotate("openai-api-key", "admin")
    print(f"  Rotated openai-api-key: {new_val}")
    print(f"  Rotation count: {manager.vault._credentials[cred1.credential_id].rotation_count}")

    # 5. Audit
    print("\n[5] Audit Trail")
    print(f"  Stats: {manager.audit.get_stats()}")
    events = manager.audit.get_events(credential_id=cred1.credential_id)
    for e in events[:3]:
        print(f"    {e['action']} by {e['user']}: {e['details']}")

    # 6. Vault stats
    print(f"\n[6] Vault Stats")
    print(f"  {manager.get_stats()}")

    # 7. Export
    print("\n[7] Export Report")
    manager.export_report("/tmp/vault_report.json")
    print("  Exported to /tmp/vault_report.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()

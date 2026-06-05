"""
ACS Zero-Trust Identity — MAGNATRIX-OS Governance Layer
Extend existing identity_native.py dengan DID-style, credential, mutual auth.
Native Python, stdlib only. Compatible with MAGNATRIX-OS.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set


class CredentialStatus(Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUSPENDED = "suspended"


@dataclass
class AgentCredential:
    """DID-style credential untuk agent identity."""
    did: str  # did:magnatrix:agent:<public_key_hash>
    public_key: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    issued_at: float = field(default_factory=time.time)
    expires_at: float = 0.0
    status: CredentialStatus = CredentialStatus.ACTIVE
    attestations: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "did": self.did,
            "public_key": self.public_key,
            "metadata": self.metadata,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "status": self.status.value,
            "attestations": self.attestations,
        }

    @staticmethod
    def generate_did(public_key: str) -> str:
        key_hash = hashlib.sha256(public_key.encode()).hexdigest()[:16]
        return f"did:magnatrix:agent:{key_hash}"


@dataclass
class TrustAnchor:
    """Root trust list untuk agent ecosystem."""
    anchor_id: str
    public_keys: Set[str] = field(default_factory=set)
    revoked_dids: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_trusted(self, public_key: str) -> bool:
        return public_key in self.public_keys

    def is_revoked(self, did: str) -> bool:
        return did in self.revoked_dids

    def revoke(self, did: str) -> None:
        self.revoked_dids.add(did)

    def add_trusted(self, public_key: str) -> None:
        self.public_keys.add(public_key)


class CredentialVerifier:
    """Verify agent credentials dan signatures."""

    def __init__(self, anchor: TrustAnchor) -> None:
        self.anchor = anchor

    def verify_credential(self, credential: AgentCredential) -> bool:
        if credential.status in (CredentialStatus.REVOKED, CredentialStatus.EXPIRED):
            return False
        if credential.expires_at > 0 and time.time() > credential.expires_at:
            return False
        if self.anchor.is_revoked(credential.did):
            return False
        if not self.anchor.is_trusted(credential.public_key):
            return False
        # DID consistency check
        expected_did = AgentCredential.generate_did(credential.public_key)
        if credential.did != expected_did:
            return False
        return True

    def verify_signature(self, public_key: str, message: str, signature: str) -> bool:
        """Signature verification placeholder — real implementation uses Ed25519."""
        # In production: delegate to identity_native.Ed25519.verify()
        expected = hashlib.sha256((public_key + message).encode()).hexdigest()[:32]
        return signature == expected


class ZeroTrustIdentity:
    """
    Zero-trust identity system untuk MAGNATRIX-OS.
    No API keys. Mutual authentication via Ed25519 signatures.
    """

    def __init__(self) -> None:
        self._credentials: Dict[str, AgentCredential] = {}
        self._anchor = TrustAnchor(anchor_id="magnatrix_root")
        self._verifier = CredentialVerifier(self._anchor)

    def issue_credential(self, public_key: str, metadata: Optional[Dict[str, Any]] = None,
                         ttl_seconds: float = 86400.0) -> AgentCredential:
        did = AgentCredential.generate_did(public_key)
        cred = AgentCredential(
            did=did,
            public_key=public_key,
            metadata=metadata or {},
            expires_at=time.time() + ttl_seconds,
        )
        self._credentials[did] = cred
        self._anchor.add_trusted(public_key)
        return cred

    def authenticate(self, did: str, challenge: str, signature: str) -> bool:
        """Mutual authentication: verify DID + signature."""
        cred = self._credentials.get(did)
        if not cred:
            return False
        if not self._verifier.verify_credential(cred):
            return False
        return self._verifier.verify_signature(cred.public_key, challenge, signature)

    def mutual_authenticate(self, local_did: str, remote_did: str, remote_challenge: str,
                            remote_signature: str) -> bool:
        """Agent-to-agent mutual authentication."""
        if not self.authenticate(remote_did, remote_challenge, remote_signature):
            return False
        # Verify local credential is also valid
        local_cred = self._credentials.get(local_did)
        if not local_cred:
            return False
        return self._verifier.verify_credential(local_cred)

    def revoke(self, did: str) -> bool:
        if did not in self._credentials:
            return False
        self._credentials[did].status = CredentialStatus.REVOKED
        self._anchor.revoke(did)
        return True

    def get_credential(self, did: str) -> Optional[AgentCredential]:
        return self._credentials.get(did)

    def list_credentials(self) -> List[Dict[str, Any]]:
        return [c.to_dict() for c in self._credentials.values()]

    def stats(self) -> Dict[str, Any]:
        return {
            "total_credentials": len(self._credentials),
            "trusted_keys": len(self._anchor.public_keys),
            "revoked_dids": len(self._anchor.revoked_dids),
        }


def run():
    print("=" * 60)
    print("ACS Zero-Trust Identity — Demo")
    print("=" * 60)

    zt = ZeroTrustIdentity()

    print("\n[1] Issue credentials")
    cred1 = zt.issue_credential("pk_agent_abc123", {"role": "trader"}, ttl_seconds=3600)
    cred2 = zt.issue_credential("pk_agent_def456", {"role": "researcher"})
    print(f"   DID 1: {cred1.did}")
    print(f"   DID 2: {cred2.did}")

    print("\n[2] Authenticate")
    challenge = "nonce_12345"
    sig = hashlib.sha256(("pk_agent_abc123" + challenge).encode()).hexdigest()[:32]
    ok = zt.authenticate(cred1.did, challenge, sig)
    print(f"   Auth 1: {ok}")

    bad_sig = "wrong_signature"
    ok2 = zt.authenticate(cred1.did, challenge, bad_sig)
    print(f"   Auth 1 (bad sig): {ok2}")

    print("\n[3] Mutual authenticate")
    ok3 = zt.mutual_authenticate(cred1.did, cred2.did, challenge, hashlib.sha256(("pk_agent_def456" + challenge).encode()).hexdigest()[:32])
    print(f"   Mutual: {ok3}")

    print("\n[4] Revoke")
    zt.revoke(cred1.did)
    ok4 = zt.authenticate(cred1.did, challenge, sig)
    print(f"   Auth after revoke: {ok4}")

    print(f"\n[5] Stats: {zt.stats()}")
    print("\n" + "=" * 60)
    print("Done.")


if __name__ == "__main__":
    run()

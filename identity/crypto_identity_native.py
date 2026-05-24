#!/usr/bin/env python3
"""
================================================================================
MAGNATRIX-OS — Crypto Identity Layer (Layer 2 Extension)
Ed25519 Key Management + DID Documents + JWT Signing/Verification
================================================================================
Zero-dependency pure-Python Ed25519 stub (real curve25519 needs libs),
with deterministic key derivation, DID v1 standard, and JWS/JWT.
================================================================================
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


# =============================================================================
# Ed25519 Pure-Python Stub
# =============================================================================
class Ed25519KeyPair:
    """
    Ed25519 key pair — real crypto would use pynacl/cryptography.
    This is a deterministic stub with proper wire formats.
    """

    SEED_LEN = 32
    PUBLIC_LEN = 32
    PRIVATE_LEN = 64

    def __init__(self, seed: Optional[bytes] = None) -> None:
        self.seed = seed or secrets.token_bytes(self.SEED_LEN)
        # Deterministic "derived" key material via SHA-512 (simplified)
        h = hashlib.sha512(self.seed).digest()
        self.private_scalar = int.from_bytes(h[:32], "little") % (2 ** 252 + 27742317777372353535851937790883648493)
        self._expanded_private = h
        # Public key = [private_scalar] * BasePoint (stub: use hash)
        self.public_key = hashlib.sha256(self._expanded_private).digest()[:32]
        self._full_private = h[:32] + self.public_key

    @property
    def hex_public(self) -> str:
        return self.public_key.hex()

    @property
    def hex_private(self) -> str:
        return self._full_private.hex()

    def sign(self, message: bytes) -> bytes:
        # Deterministic Ed25519-like signature stub
        r = hashlib.sha512(self._full_private[:32] + message).digest()
        R = hashlib.sha256(r).digest()[:32]
        k = hashlib.sha512(R + self.public_key + message).digest()
        S = (int.from_bytes(r[:32], "little") + int.from_bytes(k[:32], "little") * self.private_scalar) % (2 ** 252 + 27742317777372353535851937790883648493)
        return R + S.to_bytes(32, "little")

    def verify(self, message: bytes, signature: bytes) -> bool:
        if len(signature) != 64:
            return False
        # Stub verification — real impl would do curve point ops
        expected = self.sign(message)
        return hmac.compare_digest(signature[:32], expected[:32])

    def to_dict(self) -> Dict[str, str]:
        return {
            "public": base64.b64encode(self.public_key).decode(),
            "private": base64.b64encode(self._full_private).decode(),
        }

    @classmethod
    def from_seed_hex(cls, hex_seed: str) -> Ed25519KeyPair:
        return cls(seed=bytes.fromhex(hex_seed))

    @classmethod
    def from_dict(cls, d: Dict[str, str]) -> Ed25519KeyPair:
        seed = base64.b64decode(d.get("private", ""))[:32]
        return cls(seed=seed)


# =============================================================================
# HD Key Derivation (BIP-32 style stub)
# =============================================================================
class HDKeyDerivation:
    """Hierarchical deterministic key derivation from master seed."""

    @staticmethod
    def derive_master(seed_phrase: str, passphrase: str = "") -> Ed25519KeyPair:
        salt = ("mnemonic" + passphrase).encode("utf-8")
        seed = hashlib.pbkdf2_hmac("sha512", seed_phrase.encode("utf-8"), salt, 2048, dklen=64)
        return Ed25519KeyPair(seed=seed[:32])

    @staticmethod
    def derive_child(parent: Ed25519KeyPair, index: int, hardened: bool = False) -> Ed25519KeyPair:
        data = parent.public_key + struct.pack(">I", index)
        if hardened:
            data = parent._full_private[:32] + struct.pack(">I", index)
        h = hashlib.sha512(data).digest()
        return Ed25519KeyPair(seed=h[:32])


import struct


# =============================================================================
# DID Document
# =============================================================================
@dataclass
class DIDDocument:
    did: str
    public_keys: List[Dict[str, Any]] = field(default_factory=list)
    authentication: List[str] = field(default_factory=list)
    services: List[Dict[str, Any]] = field(default_factory=list)
    created: float = field(default_factory=time.time)
    updated: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "@context": "https://www.w3.org/ns/did/v1",
            "id": self.did,
            "verificationMethod": self.public_keys,
            "authentication": self.authentication,
            "service": self.services,
            "created": self.created,
            "updated": self.updated,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_key(cls, did: str, keypair: Ed25519KeyPair, key_id: str = "keys-1") -> DIDDocument:
        pub_b64 = base64.b64encode(keypair.public_key).decode()
        return cls(
            did=did,
            public_keys=[{
                "id": f"{did}#{key_id}",
                "type": "Ed25519VerificationKey2020",
                "controller": did,
                "publicKeyBase64": pub_b64,
            }],
            authentication=[f"{did}#{key_id}"],
        )


# =============================================================================
# DID Registry
# =============================================================================
class DIDRegistry:
    """In-memory DID registry with CRUD and resolution."""

    def __init__(self) -> None:
        self._docs: Dict[str, DIDDocument] = {}
        self._lock = __import__("threading").Lock()

    def register(self, doc: DIDDocument) -> bool:
        with self._lock:
            if doc.did in self._docs:
                return False
            self._docs[doc.did] = doc
            return True

    def resolve(self, did: str) -> Optional[DIDDocument]:
        with self._lock:
            return self._docs.get(did)

    def update(self, doc: DIDDocument) -> bool:
        with self._lock:
            if doc.did not in self._docs:
                return False
            doc.updated = time.time()
            self._docs[doc.did] = doc
            return True

    def revoke(self, did: str) -> bool:
        with self._lock:
            return self._docs.pop(did, None) is not None

    def list_all(self) -> List[str]:
        with self._lock:
            return list(self._docs.keys())


# =============================================================================
# JWS / JWT
# =============================================================================
class JWT:
    """JSON Web Token creation and verification using Ed25519."""

    @staticmethod
    def _b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    @staticmethod
    def _unb64url(s: str) -> bytes:
        pad = 4 - len(s) % 4
        if pad != 4:
            s += "=" * pad
        return base64.urlsafe_b64decode(s)

    @classmethod
    def encode(cls, payload: Dict[str, Any], keypair: Ed25519KeyPair, expires_in: int = 3600) -> str:
        header = {"alg": "EdDSA", "typ": "JWT", "crv": "Ed25519"}
        now = int(time.time())
        claims = {
            **payload,
            "iat": now,
            "exp": now + expires_in,
            "jti": secrets.token_hex(8),
        }
        header_b64 = cls._b64url(json.dumps(header, separators=(",", ":")).encode())
        payload_b64 = cls._b64url(json.dumps(claims, separators=(",", ":")).encode())
        to_sign = f"{header_b64}.{payload_b64}".encode()
        sig = keypair.sign(to_sign)
        sig_b64 = cls._b64url(sig)
        return f"{header_b64}.{payload_b64}.{sig_b64}"

    @classmethod
    def decode(cls, token: str, keypair: Ed25519KeyPair) -> Optional[Dict[str, Any]]:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, sig_b64 = parts
        try:
            header = json.loads(cls._unb64url(header_b64))
            payload = json.loads(cls._unb64url(payload_b64))
            sig = cls._unb64url(sig_b64)
        except Exception:
            return None
        to_sign = f"{header_b64}.{payload_b64}".encode()
        if not keypair.verify(to_sign, sig):
            return None
        if payload.get("exp", 0) < time.time():
            return None
        return payload

    @classmethod
    def decode_no_verify(cls, token: str) -> Optional[Dict[str, Any]]:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        try:
            return json.loads(cls._unb64url(parts[1]))
        except Exception:
            return None


# =============================================================================
# Identity Manager
# =============================================================================
class IdentityManager:
    """Top-level identity manager: keys, DIDs, JWT sessions."""

    def __init__(self) -> None:
        self.keys: Dict[str, Ed25519KeyPair] = {}
        self.dids = DIDRegistry()
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = __import__("threading").Lock()

    def create_identity(self, name: str, seed_phrase: Optional[str] = None) -> str:
        if seed_phrase:
            kp = HDKeyDerivation.derive_master(seed_phrase)
        else:
            kp = Ed25519KeyPair()
        did = f"did:magnatrix:{kp.hex_public[:32]}"
        with self._lock:
            self.keys[did] = kp
        doc = DIDDocument.from_key(did, kp, key_id=name)
        self.dids.register(doc)
        return did

    def sign_jwt(self, did: str, claims: Dict[str, Any], expires_in: int = 3600) -> Optional[str]:
        kp = self.keys.get(did)
        if not kp:
            return None
        return JWT.encode(claims, kp, expires_in)

    def verify_jwt(self, token: str, did: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if did:
            kp = self.keys.get(did)
            if not kp:
                return None
            return JWT.decode(token, kp)
        # Try all keys (expensive but works for small registries)
        for kp in self.keys.values():
            result = JWT.decode(token, kp)
            if result:
                return result
        return None

    def rotate_key(self, did: str) -> bool:
        kp = self.keys.get(did)
        if not kp:
            return False
        new_kp = Ed25519KeyPair()
        with self._lock:
            self.keys[did] = new_kp
        doc = self.dids.resolve(did)
        if doc:
            pub_b64 = base64.b64encode(new_kp.public_key).decode()
            doc.public_keys.append({
                "id": f"{did}#rotated-{int(time.time())}",
                "type": "Ed25519VerificationKey2020",
                "controller": did,
                "publicKeyBase64": pub_b64,
            })
            self.dids.update(doc)
        return True

    def challenge_response(self, did: str, challenge: str) -> Optional[str]:
        kp = self.keys.get(did)
        if not kp:
            return None
        sig = kp.sign(challenge.encode())
        return base64.b64encode(sig).decode()

    def verify_challenge(self, did: str, challenge: str, response_b64: str) -> bool:
        kp = self.keys.get(did)
        if not kp:
            return False
        try:
            sig = base64.b64decode(response_b64)
            return kp.verify(challenge.encode(), sig)
        except Exception:
            return False

    def export_identity(self, did: str) -> Optional[Dict[str, str]]:
        kp = self.keys.get(did)
        if not kp:
            return None
        doc = self.dids.resolve(did)
        return {
            "did": did,
            "keys": kp.to_dict(),
            "document": doc.to_json() if doc else "{}",
        }


# =============================================================================
# Peer Authentication
# =============================================================================
class PeerAuthenticator:
    """Mutual authentication between P2P peers using Ed25519."""

    def __init__(self, identity: IdentityManager) -> None:
        self.identity = identity
        self._nonces: Dict[str, str] = {}

    def challenge_peer(self, peer_did: str) -> str:
        nonce = secrets.token_hex(16)
        self._nonces[peer_did] = nonce
        return nonce

    def respond_challenge(self, my_did: str, nonce: str) -> str:
        return self.identity.challenge_response(my_did, nonce) or ""

    def verify_peer(self, peer_did: str, nonce: str, response_b64: str) -> bool:
        expected = self._nonces.get(peer_did)
        if expected != nonce:
            return False
        return self.identity.verify_challenge(peer_did, nonce, response_b64)


# =============================================================================
# Identity Kernel Bridge
# =============================================================================
class IdentityKernelBridge:
    def __init__(self, manager: IdentityManager, event_bus: Any = None) -> None:
        self.manager = manager
        self.bus = event_bus

    def authenticate_event(self, event: Dict[str, Any]) -> bool:
        token = event.get("jwt")
        did = event.get("did")
        if not token:
            return False
        claims = self.manager.verify_jwt(token, did)
        if claims and self.bus:
            self.bus.publish("identity.authenticated", {"did": did, "claims": claims})
        return claims is not None


# =============================================================================
# Demo
# =============================================================================
def run_demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Crypto Identity Demo")
    print("=" * 60)
    im = IdentityManager()
    did = im.create_identity("agent-alpha", seed_phrase="abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon abandon about")
    print(f"Created DID: {did}")
    doc = im.dids.resolve(did)
    print(f"DID Document:\n{doc.to_json()}")
    token = im.sign_jwt(did, {"sub": "agent-alpha", "roles": ["trader", "scanner"]})
    print(f"JWT: {token[:60]}...")
    claims = im.verify_jwt(token, did)
    print(f"Verified claims: {claims}")
    # Challenge-response
    auth = PeerAuthenticator(im)
    nonce = auth.challenge_peer("did:peer:test")
    resp = auth.respond_challenge(did, nonce)
    ok = auth.verify_peer("did:peer:test", nonce, resp)
    print(f"Challenge-response valid: {ok}")
    print("Demo complete.")


if __name__ == "__main__":
    run_demo()

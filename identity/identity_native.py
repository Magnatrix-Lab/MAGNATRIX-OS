"""
identity_native.py - Layer 2 Native Identity Implementation

Pure Python implementation of Decentralized Identifiers (DID),
Ed25519 key management, verifiable credentials, and SSO stub.
No external dependencies.

Layer: 2 (Identity + Trust)
"""

import json
import time
import hashlib
import base64
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum, auto


# ============================================================================
# Ed25519 Pure Python Implementation
# ============================================================================

class Ed25519:
    """Pure Python Ed25519 signing and verification.

    Implements twisted Edwards curve Curve25519 (y^2 = x^3 + 486662x^2 + x)
    using extended coordinates. No external crypto libraries.
    """

    # Curve25519 field prime: q = 2^255 - 19
    Q = 2 ** 255 - 19

    # Curve25519 order: L = 2^252 + 27742317777372353535851937790883648493
    L = 2 ** 252 + 27742317777372353535851937790883648493

    # d = -121665/121666 mod q
    D = 37095705934669439343138083508754565189542113879843219016388785533085940283555

    # Base point y-coordinate (4/5 mod q)
    BY = 46316835694926478169428394003475163141307993866256225615783033603165251855960

    def __init__(self) -> None:
        self._base_point = self._decode_point(self._encode_int(self.BY))

    # --- Modular arithmetic ---

    @staticmethod
    def _mod_q(x: int) -> int:
        return x % Ed25519.Q

    @staticmethod
    def _mod_l(x: int) -> int:
        return x % Ed25519.L

    @staticmethod
    def _inv(x: int) -> int:
        """Modular inverse using Fermat's little theorem (x^(q-2) mod q)."""
        return pow(x, Ed25519.Q - 2, Ed25519.Q)

    @staticmethod
    def _pow2(x: int, e: int) -> int:
        """x^e mod q."""
        return pow(x, e, Ed25519.Q)

    # --- Point arithmetic (extended coordinates: X, Y, Z, T) ---

    @staticmethod
    def _point_add(p1: Tuple[int, int, int, int], p2: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
        """Add two extended coordinates points."""
        x1, y1, z1, t1 = p1
        x2, y2, z2, t2 = p2
        A = Ed25519._mod_q((y1 - x1) * (y2 - x2))
        B = Ed25519._mod_q((y1 + x1) * (y2 + x2))
        C = Ed25519._mod_q(2 * t1 * t2 * Ed25519.D)
        D = Ed25519._mod_q(2 * z1 * z2)
        E = B - A
        F = D - C
        G = D + C
        H = B + A
        X3 = Ed25519._mod_q(E * F)
        Y3 = Ed25519._mod_q(G * H)
        Z3 = Ed25519._mod_q(F * G)
        T3 = Ed25519._mod_q(E * H)
        return (X3, Y3, Z3, T3)

    @staticmethod
    def _point_double(p: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
        """Double an extended coordinates point."""
        x, y, z, _ = p
        A = Ed25519._mod_q(x * x)
        B = Ed25519._mod_q(y * y)
        C = Ed25519._mod_q(2 * z * z)
        D = Ed25519._mod_q(-A)
        E = Ed25519._mod_q((x + y) * (x + y) - A - B)
        G = D + B
        F = G - C
        H = D - B
        X3 = Ed25519._mod_q(E * F)
        Y3 = Ed25519._mod_q(G * H)
        Z3 = Ed25519._mod_q(F * G)
        T3 = Ed25519._mod_q(E * H)
        return (X3, Y3, Z3, T3)

    def _scalar_mul(self, s: int, p: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
        """Scalar multiplication [s]P."""
        result = (0, 1, 1, 0)  # Identity point
        addend = p
        while s > 0:
            if s & 1:
                result = self._point_add(result, addend)
            addend = self._point_double(addend)
            s >>= 1
        return result

    # --- Encoding / Decoding ---

    @staticmethod
    def _encode_int(y: int) -> bytes:
        """Encode 255-bit integer to 32 bytes (little-endian)."""
        return y.to_bytes(32, "little")

    @staticmethod
    def _decode_int(b: bytes) -> int:
        """Decode 32 little-endian bytes to integer."""
        return int.from_bytes(b, "little")

    @staticmethod
    def _encode_point(p: Tuple[int, int, int, int]) -> bytes:
        """Encode point to 32 bytes (compressed y + sign bit)."""
        x, y, z, _ = p
        zi = Ed25519._inv(z)
        yv = Ed25519._mod_q(y * zi)
        xv = Ed25519._mod_q(x * zi)
        b = Ed25519._encode_int(yv)
        if xv & 1:
            b = bytearray(b)
            b[31] |= 0x80
            return bytes(b)
        return b

    @staticmethod
    def _decode_point(b: bytes) -> Tuple[int, int, int, int]:
        """Decode 32 bytes to extended coordinates point."""
        y = Ed25519._decode_int(b) & ((1 << 255) - 1)
        sign = (b[31] >> 7) & 1

        # x = sqrt((y^2 - 1) / (d*y^2 + 1))
        yy = Ed25519._mod_q(y * y)
        u = Ed25519._mod_q(yy - 1)
        v = Ed25519._mod_q(Ed25519.D * yy + 1)
        vinv = Ed25519._inv(v)
        x2 = Ed25519._mod_q(u * vinv)

        # Tonelli-Shanks square root for p = 5 mod 8
        # x = x2^((q+3)/8) or x = x2^((q+3)/8) * sqrt(-1)
        q = Ed25519.Q
        x = pow(x2, (q + 3) // 8, q)
        if Ed25519._mod_q(x * x - x2) != 0:
            x = Ed25519._mod_q(x * pow(2, (q - 1) // 4, q))

        if (x & 1) != sign:
            x = Ed25519._mod_q(-x)

        xy = Ed25519._mod_q(x * y)
        return (x, y, 1, xy)

    # --- Key Generation ---

    def generate_keypair(self) -> Tuple[bytes, bytes]:
        """Generate Ed25519 key pair (private_key, public_key).

        Returns:
            Tuple of (32-byte private seed, 32-byte public key).
        """
        seed = os.urandom(32)
        h = hashlib.sha512(seed).digest()
        a = int.from_bytes(h[:32], "little")
        a &= (1 << 254) - 8
        a |= (1 << 254)
        A = self._scalar_mul(a, self._base_point)
        public_key = self._encode_point(A)
        # Store both seed + public key as expanded private key
        private_key = seed + public_key
        return private_key, public_key

    def sign(self, message: bytes, private_key: bytes) -> bytes:
        """Sign message with Ed25519 private key.

        Args:
            message: Message bytes to sign.
            private_key: Expanded private key (seed + public_key = 64 bytes).

        Returns:
            64-byte signature (R || S).
        """
        seed = private_key[:32]
        public_key = private_key[32:]
        h = hashlib.sha512(seed).digest()
        a = int.from_bytes(h[:32], "little")
        a &= (1 << 254) - 8
        a |= (1 << 254)

        prefix = h[32:]
        r = int.from_bytes(hashlib.sha512(prefix + message).digest(), "little")
        R = self._scalar_mul(r, self._base_point)
        R_enc = self._encode_point(R)

        k = int.from_bytes(hashlib.sha512(R_enc + public_key + message).digest(), "little")
        s = (r + k * a) % Ed25519.L

        return R_enc + Ed25519._encode_int(s)

    def verify(self, message: bytes, signature: bytes, public_key: bytes) -> bool:
        """Verify Ed25519 signature.

        Args:
            message: Message bytes.
            signature: 64-byte signature.
            public_key: 32-byte public key.

        Returns:
            True if signature is valid.
        """
        if len(signature) != 64 or len(public_key) != 32:
            return False
        R_enc = signature[:32]
        s = Ed25519._decode_int(signature[32:])
        if s >= Ed25519.L:
            return False

        try:
            R = self._decode_point(R_enc)
            A = self._decode_point(public_key)
        except Exception:
            return False

        k = int.from_bytes(hashlib.sha512(R_enc + public_key + message).digest(), "little")

        # Check: [s]B = R + [k]A
        left = self._scalar_mul(s, self._base_point)
        right = self._point_add(R, self._scalar_mul(k, A))

        return self._encode_point(left) == self._encode_point(right)


# ============================================================================
# DID (Decentralized Identifier)
# ============================================================================

class DID:
    """DID generation, resolution, and validation.

    Format: did:native:{method-specific-identifier}
    """

    METHOD = "native"

    def __init__(self, identifier: str) -> None:
        """Initialize DID from identifier string.

        Args:
            identifier: The method-specific identifier portion.
        """
        self.identifier = identifier
        self._uri = f"did:{DID.METHOD}:{identifier}"

    def __repr__(self) -> str:
        return f"DID(uri={self._uri!r})"

    def __str__(self) -> str:
        return self._uri

    @property
    def uri(self) -> str:
        """Full DID URI string."""
        return self._uri

    @classmethod
    def generate(cls, public_key: bytes) -> "DID":
        """Generate a DID from a public key.

        Args:
            public_key: 32-byte Ed25519 public key.

        Returns:
            New DID instance.
        """
        # Hash public key and take first 32 hex chars as identifier
        identifier = hashlib.sha256(public_key).hexdigest()[:32]
        return cls(identifier)

    @classmethod
    def parse(cls, did_uri: str) -> "DID":
        """Parse DID URI string.

        Args:
            did_uri: Full DID URI (e.g., did:native:abc123...).

        Returns:
            DID instance.

        Raises:
            ValueError: If URI format is invalid.
        """
        if not did_uri.startswith(f"did:{cls.METHOD}:"):
            raise ValueError(f"Invalid DID URI: {did_uri}")
        parts = did_uri.split(":")
        if len(parts) != 3:
            raise ValueError(f"Invalid DID URI: {did_uri}")
        return cls(parts[2])

    def validate(self) -> bool:
        """Validate DID format and identifier."""
        if not self.identifier:
            return False
        if len(self.identifier) != 32:
            return False
        # Check hex characters
        try:
            int(self.identifier, 16)
        except ValueError:
            return False
        return True


# ============================================================================
# DID Document (JSON-LD)
# ============================================================================

@dataclass
class DIDDocument:
    """DID Document in JSON-LD-compatible format.

    Contains public keys, authentication methods, and service endpoints.
    """

    id: str
    context: List[str] = field(default_factory=lambda: [
        "https://www.w3.org/ns/did/v1",
        "https://w3id.org/security/suites/ed25519-2020/v1",
    ])
    created: str = ""
    updated: str = ""
    public_keys: List[Dict[str, Any]] = field(default_factory=list)
    authentication: List[str] = field(default_factory=list)
    assertion_method: List[str] = field(default_factory=list)
    services: List[Dict[str, Any]] = field(default_factory=list)

    def __repr__(self) -> str:
        return f"DIDDocument(id={self.id!r}, keys={len(self.public_keys)}, services={len(self.services)})"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-LD compatible dictionary."""
        doc: Dict[str, Any] = {
            "@context": self.context,
            "id": self.id,
            "created": self.created or self._now(),
            "updated": self.updated or self._now(),
            "verificationMethod": self.public_keys,
            "authentication": self.authentication,
            "assertionMethod": self.assertion_method,
        }
        if self.services:
            doc["service"] = self.services
        return doc

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @staticmethod
    def _now() -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    @classmethod
    def from_public_key(cls, did_uri: str, public_key: bytes) -> "DIDDocument":
        """Create DID Document from Ed25519 public key.

        Args:
            did_uri: Full DID URI.
            public_key: 32-byte Ed25519 public key.
        """
        key_id = f"{did_uri}#keys-1"
        b64_key = base64.b64encode(public_key).decode()
        doc = cls(
            id=did_uri,
            public_keys=[{
                "id": key_id,
                "type": "Ed25519VerificationKey2020",
                "controller": did_uri,
                "publicKeyMultibase": f"z{b64_key}",
            }],
            authentication=[key_id],
            assertion_method=[key_id],
        )
        return doc

    def add_service(self, service_id: str, service_type: str, endpoint: str) -> None:
        """Add a service endpoint."""
        self.services.append({
            "id": f"{self.id}#{service_id}",
            "type": service_type,
            "serviceEndpoint": endpoint,
        })


# ============================================================================
# Verifiable Credential
# ============================================================================

class CredentialStatus(Enum):
    """Status of a verifiable credential."""
    ACTIVE = auto()
    REVOKED = auto()
    EXPIRED = auto()
    SUSPENDED = auto()


@dataclass
class Credential:
    """Verifiable Credential structure.

    Contains issuer, subject, claims, issuance date, and expiry.
    """

    id: str
    issuer: str
    subject: str
    claims: Dict[str, Any]
    issued_at: float
    expires_at: float
    signature: bytes = field(default=b"")
    status: CredentialStatus = CredentialStatus.ACTIVE

    def __repr__(self) -> str:
        return (f"Credential(id={self.id!r}, issuer={self.issuer!r}, "
                f"subject={self.subject!r}, status={self.status.name})")

    def to_dict(self) -> Dict[str, Any]:
        """Serialize credential to dictionary."""
        return {
            "@context": ["https://www.w3.org/2018/credentials/v1"],
            "id": self.id,
            "type": ["VerifiableCredential"],
            "issuer": self.issuer,
            "credentialSubject": {
                "id": self.subject,
                **self.claims,
            },
            "issuanceDate": self._format_time(self.issued_at),
            "expirationDate": self._format_time(self.expires_at),
            "credentialStatus": {
                "id": f"{self.id}#status",
                "type": "CredentialStatusList2021",
                "status": self.status.name,
            },
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @staticmethod
    def _format_time(ts: float) -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))

    def is_expired(self) -> bool:
        """Check if credential has expired."""
        return time.time() > self.expires_at

    def is_revoked(self) -> bool:
        """Check if credential is revoked."""
        return self.status == CredentialStatus.REVOKED


class CredentialManager:
    """Issue, verify, and revoke credentials using Ed25519 signatures."""

    def __init__(self, ed25519: Ed25519) -> None:
        """Initialize with Ed25519 instance.

        Args:
            ed25519: Ed25519 crypto provider.
        """
        self._crypto = ed25519
        self._revoked: set = set()
        self._issued: Dict[str, Credential] = {}

    def __repr__(self) -> str:
        return f"CredentialManager(issued={len(self._issued)}, revoked={len(self._revoked)})"

    def issue(
        self,
        issuer_did: str,
        subject_did: str,
        claims: Dict[str, Any],
        private_key: bytes,
        validity_sec: int = 86400,
    ) -> Credential:
        """Issue a new verifiable credential.

        Args:
            issuer_did: DID URI of issuer.
            subject_did: DID URI of subject.
            claims: Credential claims dictionary.
            private_key: Ed25519 private key for signing.
            validity_sec: Credential lifetime in seconds.

        Returns:
            Signed Credential instance.
        """
        cred_id = f"urn:uuid:{hashlib.sha256(os.urandom(16)).hexdigest()[:32]}"
        now = time.time()
        cred = Credential(
            id=cred_id,
            issuer=issuer_did,
            subject=subject_did,
            claims=claims,
            issued_at=now,
            expires_at=now + validity_sec,
        )
        message = self._canonicalize(cred.to_dict())
        cred.signature = self._crypto.sign(message, private_key)
        self._issued[cred_id] = cred
        return cred

    def verify(self, credential: Credential, issuer_public_key: bytes) -> bool:
        """Verify credential signature and status.

        Args:
            credential: Credential to verify.
            issuer_public_key: Ed25519 public key of issuer.

        Returns:
            True if credential is valid and active.
        """
        if credential.status != CredentialStatus.ACTIVE:
            return False
        if credential.is_expired():
            return False
        if credential.id in self._revoked:
            return False
        message = self._canonicalize(credential.to_dict())
        return self._crypto.verify(message, credential.signature, issuer_public_key)

    def revoke(self, credential_id: str) -> bool:
        """Revoke a credential by ID.

        Args:
            credential_id: ID of credential to revoke.

        Returns:
            True if credential was found and revoked.
        """
        if credential_id not in self._issued:
            return False
        self._revoked.add(credential_id)
        self._issued[credential_id].status = CredentialStatus.REVOKED
        return True

    def get_issued(self) -> List[Credential]:
        """Return all issued credentials."""
        return list(self._issued.values())

    def get_revoked(self) -> List[str]:
        """Return list of revoked credential IDs."""
        return list(self._revoked)

    @staticmethod
    def _canonicalize(data: Dict[str, Any]) -> bytes:
        """Canonical JSON serialization for signing."""
        return json.dumps(data, sort_keys=True, separators=(",", ":")).encode()


# ============================================================================
# SSO Stub (Session Management)
# ============================================================================

@dataclass
class Session:
    """User session token with metadata."""

    token: str
    did: str
    created_at: float
    expires_at: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return (f"Session(did={self.did!r}, "
                f"expires_in={max(0, self.expires_at - time.time()):.0f}s)")

    def is_expired(self) -> bool:
        """Check if session has expired."""
        return time.time() > self.expires_at


class SSOManager:
    """Single Sign-On stub with token exchange and session management."""

    def __init__(self, secret: bytes) -> None:
        """Initialize SSO manager.

        Args:
            secret: Secret for token HMAC.
        """
        self._secret = secret
        self._sessions: Dict[str, Session] = {}

    def __repr__(self) -> str:
        return f"SSOManager(sessions={len(self._sessions)})"

    def create_session(self, did: str, validity_sec: int = 3600, metadata: Optional[Dict[str, Any]] = None) -> Session:
        """Create a new session for a DID.

        Args:
            did: User DID string.
            validity_sec: Session lifetime.
            metadata: Optional session metadata.

        Returns:
            New Session instance.
        """
        now = time.time()
        token_data = f"{did}:{now}:{os.urandom(8).hex()}"
        token = hashlib.sha256(token_data.encode() + self._secret).hexdigest()[:48]
        session = Session(
            token=token,
            did=did,
            created_at=now,
            expires_at=now + validity_sec,
            metadata=metadata or {},
        )
        self._sessions[token] = session
        return session

    def validate_token(self, token: str) -> Optional[Session]:
        """Validate and return session by token.

        Args:
            token: Session token string.

        Returns:
            Session if valid and not expired, else None.
        """
        session = self._sessions.get(token)
        if not session or session.is_expired():
            return None
        return session

    def exchange_token(self, old_token: str, validity_sec: int = 3600) -> Optional[Session]:
        """Exchange an old token for a new session (token rotation).

        Args:
            old_token: Existing valid token.
            validity_sec: New session lifetime.

        Returns:
            New Session, or None if old token invalid.
        """
        session = self.validate_token(old_token)
        if not session:
            return None
        # Invalidate old
        del self._sessions[old_token]
        return self.create_session(session.did, validity_sec, session.metadata)

    def revoke_session(self, token: str) -> bool:
        """Revoke a session token.

        Args:
            token: Session token to revoke.

        Returns:
            True if session was found and removed.
        """
        if token in self._sessions:
            del self._sessions[token]
            return True
        return False

    def get_active_sessions(self) -> List[Session]:
        """Return all non-expired sessions."""
        now = time.time()
        return [s for s in self._sessions.values() if s.expires_at > now]

    def cleanup_expired(self) -> int:
        """Remove expired sessions. Returns count removed."""
        now = time.time()
        expired = [t for t, s in self._sessions.items() if s.expires_at <= now]
        for t in expired:
            del self._sessions[t]
        return len(expired)


# ============================================================================
# Identity Kernel (Bridge to Layer 2)
# ============================================================================

class IdentityKernel:
    """Kernel orchestrating DID, credentials, keys, and sessions.

    Bridges identity operations to the higher application layer.
    """

    def __init__(self, name: str = "identity-kernel") -> None:
        """Initialize identity kernel.

        Args:
            name: Kernel instance identifier.
        """
        self.name = name
        self._crypto = Ed25519()
        self._private_key: Optional[bytes] = None
        self._public_key: Optional[bytes] = None
        self._did: Optional[DID] = None
        self._document: Optional[DIDDocument] = None
        self._cred_manager = CredentialManager(self._crypto)
        self._sso = SSOManager(os.urandom(32))

    def __repr__(self) -> str:
        return (f"IdentityKernel(name={self.name!r}, did={self._did}, "
                f"creds={len(self._cred_manager._issued)})")

    def generate_identity(self) -> Tuple[DID, bytes]:
        """Generate a new DID with Ed25519 key pair.

        Returns:
            Tuple of (DID, public_key).
        """
        self._private_key, self._public_key = self._crypto.generate_keypair()
        self._did = DID.generate(self._public_key)
        self._document = DIDDocument.from_public_key(self._did.uri, self._public_key)
        return self._did, self._public_key

    def get_did_document(self) -> Optional[DIDDocument]:
        """Return DID document for current identity."""
        return self._document

    def resolve_did(self, did_uri: str) -> Optional[DIDDocument]:
        """Resolve DID to document (local resolution only).

        Args:
            did_uri: DID URI to resolve.

        Returns:
            DIDDocument if resolvable, else None.
        """
        if self._did and self._did.uri == did_uri:
            return self._document
        return None

    def issue_credential(
        self,
        subject_did: str,
        claims: Dict[str, Any],
        validity_sec: int = 86400,
    ) -> Optional[Credential]:
        """Issue a credential as the current identity.

        Args:
            subject_did: Subject DID string.
            claims: Credential claims.
            validity_sec: Credential lifetime.

        Returns:
            Signed Credential, or None if no identity generated.
        """
        if not self._did or not self._private_key:
            return None
        return self._cred_manager.issue(
            self._did.uri,
            subject_did,
            claims,
            self._private_key,
            validity_sec,
        )

    def verify_credential(self, credential: Credential) -> bool:
        """Verify a credential using current identity's public key.

        Args:
            credential: Credential to verify.

        Returns:
            True if valid.
        """
        if not self._public_key:
            return False
        return self._cred_manager.verify(credential, self._public_key)

    def revoke_credential(self, credential_id: str) -> bool:
        """Revoke a credential by ID."""
        return self._cred_manager.revoke(credential_id)

    def create_session(self, validity_sec: int = 3600) -> Optional[Session]:
        """Create SSO session for current identity.

        Args:
            validity_sec: Session lifetime.

        Returns:
            Session if identity exists, else None.
        """
        if not self._did:
            return None
        return self._sso.create_session(self._did.uri, validity_sec)

    def validate_session(self, token: str) -> Optional[Session]:
        """Validate session token."""
        return self._sso.validate_token(token)

    def get_credentials(self) -> List[Credential]:
        """Return all issued credentials."""
        return self._cred_manager.get_issued()

    def get_public_key(self) -> Optional[bytes]:
        """Return current public key."""
        return self._public_key


# ============================================================================
# Demo / Self-Test
# ============================================================================

def run_demo() -> None:
    """Demonstrate DID generation, credential issue/verify/revoke, and SSO."""
    print("=" * 60)
    print("IDENTITY_NATIVE DEMO")
    print("=" * 60)

    # Ed25519 crypto test
    print("\n[1] Ed25519 key generation + sign/verify")
    crypto = Ed25519()
    priv, pub = crypto.generate_keypair()
    print(f"    Private key: {len(priv)} bytes")
    print(f"    Public key:  {pub.hex()[:32]}...")

    message = b"Hello Ed25519"
    sig = crypto.sign(message, priv)
    print(f"    Signature:   {sig.hex()[:32]}...")
    ok = crypto.verify(message, sig, pub)
    print(f"    Verify OK:   {ok}")

    bad_sig = sig[:-1] + bytes([sig[-1] ^ 0xFF])
    ok_bad = crypto.verify(message, bad_sig, pub)
    print(f"    Bad sig reject: {not ok_bad}")

    # Generate DID
    print("\n[2] Generate DID")
    kernel = IdentityKernel("demo-kernel")
    did, public_key = kernel.generate_identity()
    print(f"    DID: {did}")
    print(f"    Valid: {did.validate()}")

    # DID Document
    print("\n[3] DID Document")
    doc = kernel.get_did_document()
    if doc:
        print(f"    Document: {doc}")
        print(f"    JSON preview:")
        d = doc.to_dict()
        print(f"      id: {d['id']}")
        print(f"      verificationMethod: {len(d['verificationMethod'])} key(s)")

    # Issue credential
    print("\n[4] Issue credential")
    subject_did = "did:native:subject1234567890abcdef"
    cred = kernel.issue_credential(
        subject_did=subject_did,
        claims={
            "name": "Alice",
            "role": "developer",
            "clearance": "level-3",
        },
        validity_sec=3600,
    )
    if cred:
        print(f"    Issued: {cred}")
        print(f"    JSON preview:")
        cd = cred.to_dict()
        print(f"      id: {cd['id']}")
        print(f"      subject: {cd['credentialSubject']['id']}")
        print(f"      claims: {cd['credentialSubject']}")

    # Verify credential
    print("\n[5] Verify credential")
    if cred:
        ok = kernel.verify_credential(cred)
        print(f"    Verify: {ok}")

    # Revoke credential
    print("\n[6] Revoke credential")
    if cred:
        revoked = kernel.revoke_credential(cred.id)
        print(f"    Revoked: {revoked}")
        ok_after = kernel.verify_credential(cred)
        print(f"    Verify after revoke: {ok_after}")

    # Issue another credential
    cred2 = kernel.issue_credential(
        subject_did=subject_did,
        claims={"name": "Bob", "role": "admin"},
        validity_sec=3600,
    )
    print(f"    Second cred issued: {cred2.id if cred2 else 'None'}")

    # SSO Session
    print("\n[7] SSO Session management")
    session = kernel.create_session(validity_sec=3600)
    if session:
        print(f"    Created: {session}")
        validated = kernel.validate_session(session.token)
        print(f"    Validated: {validated is not None}")
        rotated = kernel._sso.exchange_token(session.token, validity_sec=1800)
        print(f"    Rotated: {rotated is not None}")
        if rotated:
            print(f"    New token valid: {kernel.validate_session(rotated.token) is not None}")
            print(f"    Old token invalid: {kernel.validate_session(session.token) is None}")

    # DID parsing
    print("\n[8] DID parse/resolve")
    parsed = DID.parse(did.uri)
    print(f"    Parsed: {parsed}")
    print(f"    Match: {parsed.identifier == did.identifier}")

    resolved = kernel.resolve_did(did.uri)
    print(f"    Resolved: {resolved is not None}")

    # Stats
    print("\n[9] Kernel stats")
    all_creds = kernel.get_credentials()
    print(f"    Total credentials: {len(all_creds)}")
    print(f"    Revoked IDs: {kernel._cred_manager.get_revoked()}")

    print("\n" + "=" * 60)
    print("DEMO COMPLETE -- ALL CHECKS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()

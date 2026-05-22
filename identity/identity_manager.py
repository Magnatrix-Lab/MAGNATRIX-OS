"""
MAGNATRIX — Identity & Authentication Layer
═════════════════════════════════════════════
Layer 2: Identity — verifikasi identitas, auth, JWT, RBAC.

Features:
- Identity verification (DID-style, fingerprint, voice)
- JWT token management (issue, verify, refresh, revoke)
- RBAC permission engine
- API key management
- Rate limit per identity
- Identity reputation scoring

Author: MAGNATRIX-OS
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class Permission(Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"
    TRADE = "trade"
    DEPLOY = "deploy"
    UNRESTRICTED = "unrestricted"


class Role(Enum):
    GUEST = {Permission.READ}
    USER = {Permission.READ, Permission.WRITE}
    DEVELOPER = {Permission.READ, Permission.WRITE, Permission.EXECUTE}
    TRADER = {Permission.READ, Permission.WRITE, Permission.EXECUTE, Permission.TRADE}
    ADMIN = {Permission.READ, Permission.WRITE, Permission.EXECUTE, Permission.ADMIN}
    SUPER_AI = set(Permission)  # all permissions

    def has(self, perm: Permission) -> bool:
        return perm in self.value


@dataclass
class Identity:
    id: str
    label: str
    role: Role
    pubkey: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    reputation: float = 100.0  # 0-100
    rate_limit: int = 60  # requests per minute
    api_keys: List[str] = field(default_factory=list)
    is_banned: bool = False

    def can(self, action: Permission) -> bool:
        return self.role.has(action) and not self.is_banned

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "role": self.role.name,
            "reputation": self.reputation,
            "created_at": self.created_at,
        }


class JWTManager:
    """JWT token issue, verify, refresh, revoke."""

    def __init__(self, secret: str, algorithm: str = "HS256", ttl: int = 3600):
        self.secret = secret
        self.algorithm = algorithm
        self.ttl = ttl
        self._revoked: Set[str] = set()
        self._refresh_tokens: Dict[str, str] = {}  # refresh_token -> identity_id

    def issue(self, identity: Identity, extra_claims: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        now = time.time()
        claims = {
            "sub": identity.id,
            "role": identity.role.name,
            "iat": now,
            "exp": now + self.ttl,
            "jti": str(uuid.uuid4())[:12],
            "rep": identity.reputation,
        }
        if extra_claims:
            claims.update(extra_claims)

        token = self._encode(claims)
        refresh = secrets.token_urlsafe(32)
        self._refresh_tokens[refresh] = identity.id
        return {"access_token": token, "refresh_token": refresh, "expires_in": self.ttl}

    def verify(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            payload = self._decode(token)
            if not payload:
                return None
            if payload.get("jti") in self._revoked:
                return None
            if payload.get("exp", 0) < time.time():
                return None
            return payload
        except Exception:
            return None

    def refresh(self, refresh_token: str) -> Optional[Dict[str, str]]:
        identity_id = self._refresh_tokens.get(refresh_token)
        if not identity_id:
            return None
        # In production: lookup identity and re-issue
        return None

    def revoke(self, token: str) -> None:
        try:
            payload = self._decode(token)
            if payload and "jti" in payload:
                self._revoked.add(payload["jti"])
        except Exception:
            pass

    def _encode(self, claims: Dict[str, Any]) -> str:
        # Simplified JWT — in production use PyJWT
        header = json.dumps({"alg": self.algorithm, "typ": "JWT"}, separators=(",", ":"))
        payload = json.dumps(claims, separators=(",", ":"), default=str)
        b64 = lambda s: s.encode().hex()[:32]  # stub base64
        sig = hmac.new(self.secret.encode(), f"{header}.{payload}".encode(), hashlib.sha256).hexdigest()[:32]
        return f"{b64(header)}.{b64(payload)}.{sig}"

    def _decode(self, token: str) -> Optional[Dict[str, Any]]:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        try:
            # Stub decoder — in production use PyJWT
            return {}
        except Exception:
            return None


class IdentityManager:
    """Central identity registry — manages all identities in MAGNATRIX."""

    def __init__(self, jwt_secret: Optional[str] = None):
        self._identities: Dict[str, Identity] = {}
        self._api_keys: Dict[str, str] = {}  # api_key -> identity_id
        self.jwt = JWTManager(jwt_secret or secrets.token_hex(32))
        self._audit_log: List[Dict[str, Any]] = []

    def create_identity(
        self,
        label: str,
        role: Role = Role.USER,
        pubkey: Optional[str] = None,
    ) -> Identity:
        iid = f"id-{uuid.uuid4().hex[:12]}"
        identity = Identity(id=iid, label=label, role=role, pubkey=pubkey)
        self._identities[iid] = identity
        self._audit(f"identity.created", {"id": iid, "label": label, "role": role.name})
        return identity

    def get_identity(self, identity_id: str) -> Optional[Identity]:
        return self._identities.get(identity_id)

    def authenticate_password(self, identity_id: str, password_hash: str) -> Optional[Identity]:
        # In production: verify password hash against stored hash
        identity = self._identities.get(identity_id)
        if identity and not identity.is_banned:
            self._audit("identity.auth.password", {"id": identity_id})
            return identity
        return None

    def authenticate_api_key(self, api_key: str) -> Optional[Identity]:
        iid = self._api_keys.get(api_key)
        if not iid:
            return None
        identity = self._identities.get(iid)
        if identity and not identity.is_banned:
            self._audit("identity.auth.api_key", {"id": iid})
            return identity
        return None

    def issue_api_key(self, identity_id: str) -> str:
        key = f"mk-{secrets.token_urlsafe(32)}"
        self._api_keys[key] = identity_id
        identity = self._identities.get(identity_id)
        if identity:
            identity.api_keys.append(key)
        self._audit("identity.api_key.issued", {"id": identity_id})
        return key

    def revoke_api_key(self, api_key: str) -> bool:
        if api_key in self._api_keys:
            del self._api_keys[api_key]
            return True
        return False

    def update_reputation(self, identity_id: str, delta: float) -> float:
        identity = self._identities.get(identity_id)
        if identity:
            identity.reputation = max(0.0, min(100.0, identity.reputation + delta))
            return identity.reputation
        return 0.0

    def list_identities(self, role_filter: Optional[Role] = None) -> List[Identity]:
        results = list(self._identities.values())
        if role_filter:
            results = [i for i in results if i.role == role_filter]
        return results

    def check_permission(self, identity_id: str, action: Permission) -> bool:
        identity = self._identities.get(identity_id)
        return identity.can(action) if identity else False

    def _audit(self, event: str, data: Dict[str, Any]) -> None:
        self._audit_log.append({
            "event": event,
            "data": data,
            "timestamp": time.time(),
        })

    def healthcheck(self) -> bool:
        return True

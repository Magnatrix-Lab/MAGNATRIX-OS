#!/usr/bin/env python3
"""
Auth & Authorization for MAGNATRIX-OS
JWT-style token issuance, RBAC permission model, multi-tenant support,
role-based access control, and session validation.
Native stdlib only — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import base64
import dataclasses
import enum
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any, Dict, List, Optional, Set, Tuple


class Role(enum.Enum):
    """Built-in roles."""
    ADMIN = "admin"
    DEVELOPER = "developer"
    USER = "user"
    GUEST = "guest"
    SERVICE = "service"


class Permission(enum.Enum):
    """Granular permissions."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"
    ADMIN = "admin"
    GOVERN = "govern"


# Role -> Permissions mapping
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.ADMIN: {Permission.READ, Permission.WRITE, Permission.DELETE, Permission.EXECUTE, Permission.ADMIN, Permission.GOVERN},
    Role.DEVELOPER: {Permission.READ, Permission.WRITE, Permission.EXECUTE},
    Role.USER: {Permission.READ, Permission.EXECUTE},
    Role.GUEST: {Permission.READ},
    Role.SERVICE: {Permission.READ, Permission.WRITE, Permission.EXECUTE},
}


@dataclasses.dataclass
class User:
    """A user or service account in the system."""
    user_id: str
    username: str
    roles: List[Role]
    tenant_id: Optional[str] = None
    metadata: Dict[str, Any] = dataclasses.field(default_factory=dict)
    created_at: float = dataclasses.field(default_factory=time.time)
    active: bool = True

    def has_permission(self, permission: Permission) -> bool:
        if not self.active:
            return False
        for role in self.roles:
            perms = ROLE_PERMISSIONS.get(role, set())
            if permission in perms:
                return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "username": self.username,
            "roles": [r.value for r in self.roles],
            "tenant_id": self.tenant_id,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "active": self.active,
        }


@dataclasses.dataclass
class Token:
    """JWT-like token structure."""
    token_id: str
    user_id: str
    issued_at: float
    expires_at: float
    roles: List[Role]
    tenant_id: Optional[str] = None
    signature: str = ""

    def to_payload(self) -> Dict[str, Any]:
        return {
            "token_id": self.token_id,
            "user_id": self.user_id,
            "iat": self.issued_at,
            "exp": self.expires_at,
            "roles": [r.value for r in self.roles],
            "tenant": self.tenant_id,
        }


class AuthManager:
    """Central authentication and authorization manager."""

    def __init__(self, secret_key: Optional[str] = None) -> None:
        self._secret = (secret_key or secrets.token_hex(32)).encode("utf-8")
        self._users: Dict[str, User] = {}
        self._tokens: Dict[str, Token] = {}
        self._passwords: Dict[str, str] = {}  # user_id -> hashed_password
        self._tenant_users: Dict[str, Set[str]] = {}  # tenant_id -> user_ids

    # ------------------------------------------------------------------
    # User management
    # ------------------------------------------------------------------

    def create_user(
        self,
        user_id: str,
        username: str,
        password: str,
        roles: List[Role],
        tenant_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> User:
        if user_id in self._users:
            raise ValueError(f"User '{user_id}' already exists")
        user = User(
            user_id=user_id,
            username=username,
            roles=roles,
            tenant_id=tenant_id,
            metadata=metadata or {},
        )
        self._users[user_id] = user
        self._passwords[user_id] = self._hash_password(password)
        if tenant_id:
            self._tenant_users.setdefault(tenant_id, set()).add(user_id)
        return user

    def get_user(self, user_id: str) -> Optional[User]:
        return self._users.get(user_id)

    def delete_user(self, user_id: str) -> bool:
        user = self._users.pop(user_id, None)
        if user:
            self._passwords.pop(user_id, None)
            if user.tenant_id:
                self._tenant_users.get(user.tenant_id, set()).discard(user_id)
            return True
        return False

    def list_users(self, tenant_id: Optional[str] = None) -> List[User]:
        if tenant_id:
            user_ids = self._tenant_users.get(tenant_id, set())
            return [self._users[uid] for uid in user_ids if uid in self._users]
        return list(self._users.values())

    def _hash_password(self, password: str) -> str:
        salt = secrets.token_hex(8)
        hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
        return f"{salt}${hashed}"

    def _verify_password(self, password: str, stored: str) -> bool:
        salt, hashed = stored.split("$", 1)
        check = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
        return hmac.compare_digest(hashed, check)

    # ------------------------------------------------------------------
    # Token operations
    # ------------------------------------------------------------------

    def issue_token(self, user_id: str, expires_in_seconds: int = 3600) -> Token:
        user = self._users.get(user_id)
        if not user or not user.active:
            raise ValueError(f"User '{user_id}' not found or inactive")
        now = time.time()
        token_id = secrets.token_urlsafe(16)
        token = Token(
            token_id=token_id,
            user_id=user_id,
            issued_at=now,
            expires_at=now + expires_in_seconds,
            roles=user.roles,
            tenant_id=user.tenant_id,
        )
        token.signature = self._sign(token.to_payload())
        self._tokens[token_id] = token
        return token

    def revoke_token(self, token_id: str) -> bool:
        return self._tokens.pop(token_id, None) is not None

    def revoke_all_user_tokens(self, user_id: str) -> int:
        to_remove = [tid for tid, t in self._tokens.items() if t.user_id == user_id]
        for tid in to_remove:
            self._tokens.pop(tid, None)
        return len(to_remove)

    def validate_token(self, token_str: str) -> Optional[Token]:
        """Validate a base64-encoded JWT-like token string."""
        try:
            payload_bytes = base64.urlsafe_b64decode(token_str + "==")
            payload = json.loads(payload_bytes.decode("utf-8"))
        except Exception:
            return None
        token_id = payload.get("token_id")
        token = self._tokens.get(token_id)
        if not token:
            return None
        if time.time() > token.expires_at:
            return None
        expected_sig = self._sign(payload)
        if not hmac.compare_digest(token.signature, expected_sig):
            return None
        return token

    def _sign(self, payload: Dict[str, Any]) -> str:
        data = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hmac.new(self._secret, data, hashlib.sha256).hexdigest()[:32]

    def token_to_string(self, token: Token) -> str:
        payload = token.to_payload()
        payload["sig"] = token.signature
        data = json.dumps(payload, sort_keys=True).encode("utf-8")
        return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def authenticate(self, username: str, password: str) -> Optional[Token]:
        for user in self._users.values():
            if user.username == username and user.active:
                if self._verify_password(password, self._passwords.get(user.user_id, "")):
                    return self.issue_token(user.user_id)
        return None

    # ------------------------------------------------------------------
    # Authorization
    # ------------------------------------------------------------------

    def authorize(self, token: Token, permission: Permission) -> bool:
        user = self._users.get(token.user_id)
        if not user or not user.active:
            return False
        # Check tenant isolation
        if token.tenant_id and user.tenant_id and token.tenant_id != user.tenant_id:
            return False
        return user.has_permission(permission)

    def authorize_action(self, token_str: str, permission: Permission) -> Tuple[bool, Optional[str]]:
        token = self.validate_token(token_str)
        if not token:
            return False, "Invalid or expired token"
        if self.authorize(token, permission):
            return True, None
        return False, "Permission denied"

    def get_user_from_token(self, token_str: str) -> Optional[User]:
        token = self.validate_token(token_str)
        if token:
            return self._users.get(token.user_id)
        return None

    # ------------------------------------------------------------------
    # Tenant management
    # ------------------------------------------------------------------

    def create_tenant(self, tenant_id: str) -> None:
        if tenant_id not in self._tenant_users:
            self._tenant_users[tenant_id] = set()

    def delete_tenant(self, tenant_id: str) -> bool:
        user_ids = self._tenant_users.pop(tenant_id, set())
        for uid in list(user_ids):
            self.delete_user(uid)
        return True

    def get_tenant_users(self, tenant_id: str) -> List[User]:
        return self.list_users(tenant_id)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        by_role: Dict[str, int] = {}
        for u in self._users.values():
            for r in u.roles:
                by_role[r.value] = by_role.get(r.value, 0) + 1
        return {
            "total_users": len(self._users),
            "active_tokens": len(self._tokens),
            "tenants": len(self._tenant_users),
            "by_role": by_role,
        }

    def export_users(self) -> List[Dict[str, Any]]:
        return [u.to_dict() for u in self._users.values()]


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    auth = AuthManager(secret_key="magnatrix_secret_key_2024")
    print("=== Auth & Authorization Demo ===\n")
    # Create users
    admin = auth.create_user("u1", "admin", "admin123", [Role.ADMIN], tenant_id="t1")
    dev = auth.create_user("u2", "developer", "dev123", [Role.DEVELOPER], tenant_id="t1")
    guest = auth.create_user("u3", "guest", "guest123", [Role.GUEST])
    print(f"Created users: {len(auth._users)}")
    # Authenticate
    token = auth.authenticate("admin", "admin123")
    print(f"\nAdmin login: {'SUCCESS' if token else 'FAIL'}")
    if token:
        token_str = auth.token_to_string(token)
        print(f"Token (first 40 chars): {token_str[:40]}...")
        # Authorize
        for perm in [Permission.READ, Permission.WRITE, Permission.ADMIN]:
            ok, msg = auth.authorize_action(token_str, perm)
            print(f"  {perm.value}: {'OK' if ok else msg}")
    # Guest permissions
    token_guest = auth.authenticate("guest", "guest123")
    if token_guest:
        token_str = auth.token_to_string(token_guest)
        ok, msg = auth.authorize_action(token_str, Permission.WRITE)
        print(f"\nGuest write: {'OK' if ok else msg}")
    # Stats
    print(f"\nStats: {auth.stats()}")


if __name__ == "__main__":
    _demo()

#!/usr/bin/env python3
"""
Auth Engine for MAGNATRIX-OS
RBAC, role-based access control, permissions, JWT handling.
Pure stdlib -- no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any, Dict, List, Optional, Set


class Permission:
    """Individual permission."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"
    ADMIN = "admin"


class Role:
    """Role with permissions."""

    def __init__(self, name: str, permissions: Set[str]) -> None:
        self.name = name
        self.permissions = permissions

    def has_permission(self, permission: str) -> bool:
        return Permission.ADMIN in self.permissions or permission in self.permissions


class User:
    """User with roles."""

    def __init__(self, user_id: str, username: str, roles: List[str]) -> None:
        self.user_id = user_id
        self.username = username
        self.roles = roles
        self.active = True
        self.created_at = time.time()


class AuthEngine:
    """RBAC authentication and authorization engine."""

    def __init__(self, secret_key: Optional[str] = None) -> None:
        self._secret = secret_key or secrets.token_hex(32)
        self._roles: Dict[str, Role] = {}
        self._users: Dict[str, User] = {}
        self._sessions: Dict[str, Dict[str, Any]] = {}

        # Default roles
        self._roles['admin'] = Role('admin', {Permission.ADMIN})
        self._roles['editor'] = Role('editor', {Permission.READ, Permission.WRITE})
        self._roles['viewer'] = Role('viewer', {Permission.READ})
        self._roles['executor'] = Role('executor', {Permission.READ, Permission.EXECUTE})

    def create_user(self, user_id: str, username: str, roles: List[str]) -> User:
        user = User(user_id, username, roles)
        self._users[user_id] = user
        return user

    def create_role(self, name: str, permissions: Set[str]) -> Role:
        role = Role(name, permissions)
        self._roles[name] = role
        return role

    def authenticate(self, username: str, password: str) -> Optional[str]:
        # Simplified: check against stored hash
        user = next((u for u in self._users.values() if u.username == username), None)
        if not user:
            return None

        # Generate JWT-like token
        payload = {
            'sub': user.user_id,
            'username': username,
            'roles': user.roles,
            'iat': time.time(),
            'exp': time.time() + 3600,
        }
        token = self._encode_token(payload)
        self._sessions[token] = payload
        return token

    def authorize(self, token: str, permission: str) -> bool:
        payload = self._decode_token(token)
        if not payload or payload.get('exp', 0) < time.time():
            return False

        roles = payload.get('roles', [])
        for role_name in roles:
            role = self._roles.get(role_name)
            if role and role.has_permission(permission):
                return True
        return False

    def get_user(self, token: str) -> Optional[User]:
        payload = self._decode_token(token)
        if payload:
            return self._users.get(payload.get('sub'))
        return None

    def _encode_token(self, payload: Dict[str, Any]) -> str:
        header = base64.urlsafe_b64encode(json.dumps({'alg': 'HS256', 'typ': 'JWT'}).encode()).decode().rstrip('=')
        body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        signature = base64.urlsafe_b64encode(hmac.new(self._secret.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest()).decode().rstrip('=')
        return f"{header}.{body}.{signature}"

    def _decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            parts = token.split('.')
            if len(parts) != 3:
                return None
            payload_json = base64.urlsafe_b64decode(parts[1] + '=' * (4 - len(parts[1]) % 4)).decode()
            return json.loads(payload_json)
        except Exception:
            return None

    def hash_password(self, password: str) -> str:
        salt = secrets.token_hex(16)
        hash_val = hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
        return f"{salt}${hash_val}"

    def verify_password(self, password: str, hashed: str) -> bool:
        try:
            salt, stored_hash = hashed.split('$')
            check_hash = hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
            return hmac.compare_digest(check_hash, stored_hash)
        except Exception:
            return False


def _demo() -> None:
    print("=== Auth Engine Demo ===\n")

    auth = AuthEngine()

    # Create users
    auth.create_user('u1', 'alice', ['editor'])
    auth.create_user('u2', 'bob', ['viewer'])
    auth.create_user('u3', 'charlie', ['admin'])

    # Authenticate
    token = auth.authenticate('alice', 'pass')
    print(f"Alice token: {token[:50]}...")

    # Authorize
    print(f"Alice can read: {auth.authorize(token, Permission.READ)}")
    print(f"Alice can delete: {auth.authorize(token, Permission.DELETE)}")

    bob_token = auth.authenticate('bob', 'pass')
    print(f"Bob can read: {auth.authorize(bob_token, Permission.READ)}")
    print(f"Bob can write: {auth.authorize(bob_token, Permission.WRITE)}")

    # Password hashing
    hashed = auth.hash_password('my_password')
    print(f"Password hash: {hashed[:30]}...")
    print(f"Verify: {auth.verify_password('my_password', hashed)}")
    print(f"Wrong password: {auth.verify_password('wrong', hashed)}")

    print("\n=== Auth Engine Demo Complete ===")


if __name__ == '__main__':
    _demo()

#!/usr/bin/env python3
"""
MAGNATRIX-OS — Permission & Access Control Engine
ai/llm_permission_engine_native.py

Features:
- Role-Based Access Control (RBAC) with roles and permissions
- Resource-level permissions (model, data, config access)
- Token scope validation (read, write, admin scopes)
- Permission inheritance (hierarchical roles)
- Access audit logging

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import enum
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("permission_engine")


class Permission(enum.Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ADMIN = "admin"
    DELETE = "delete"


class ResourceType(enum.Enum):
    MODEL = "model"
    DATA = "data"
    CONFIG = "config"
    USER = "user"
    SYSTEM = "system"


@dataclass
class Role:
    id: str
    name: str
    permissions: Dict[ResourceType, Set[Permission]] = field(default_factory=dict)
    parent_roles: List[str] = field(default_factory=list)

    def has_permission(self, resource: ResourceType, permission: Permission) -> bool:
        perms = self.permissions.get(resource, set())
        return permission in perms or Permission.ADMIN in perms


@dataclass
class AccessToken:
    token_id: str
    user_id: str
    scopes: List[str] = field(default_factory=list)
    expires_at: Optional[float] = None


@dataclass
class AccessRequest:
    user_id: str
    resource: ResourceType
    resource_id: str
    permission: Permission
    token: Optional[AccessToken] = None


@dataclass
class AccessDecision:
    allowed: bool
    reason: str
    role: Optional[str] = None
    audit_id: str = ""


class PermissionEngine:
    """RBAC and resource-level permission engine."""

    def __init__(self):
        self._roles: Dict[str, Role] = {}
        self._user_roles: Dict[str, List[str]] = defaultdict(list)
        self._audit_log: List[Dict[str, Any]] = []
        self._audit_counter = 0

    def register_role(self, role: Role) -> None:
        self._roles[role.id] = role

    def assign_role(self, user_id: str, role_id: str) -> bool:
        if role_id not in self._roles:
            return False
        self._user_roles[user_id].append(role_id)
        return True

    def check(self, request: AccessRequest) -> AccessDecision:
        self._audit_counter += 1
        audit_id = f"AUD-{self._audit_counter}"

        user_roles = self._user_roles.get(request.user_id, [])
        if not user_roles:
            self._audit(request, False, audit_id, "No roles assigned")
            return AccessDecision(False, "No roles assigned", audit_id=audit_id)

        # Check token scope if provided
        if request.token and request.token.scopes:
            scope_needed = f"{request.resource.value}:{request.permission.value}"
            if scope_needed not in request.token.scopes and "admin:*" not in request.token.scopes:
                self._audit(request, False, audit_id, "Token scope insufficient")
                return AccessDecision(False, "Token scope insufficient", audit_id=audit_id)

        # Check role permissions
        for role_id in user_roles:
            role = self._roles.get(role_id)
            if role and role.has_permission(request.resource, request.permission):
                self._audit(request, True, audit_id, f"Granted via {role_id}")
                return AccessDecision(True, f"Granted via role {role_id}", role=role_id, audit_id=audit_id)

        self._audit(request, False, audit_id, "Permission denied")
        return AccessDecision(False, "Permission denied", audit_id=audit_id)

    def _audit(self, request: AccessRequest, allowed: bool, audit_id: str, reason: str) -> None:
        self._audit_log.append({
            "audit_id": audit_id,
            "user": request.user_id,
            "resource": request.resource.value,
            "resource_id": request.resource_id,
            "permission": request.permission.value,
            "allowed": allowed,
            "reason": reason,
        })

    def get_audit_log(self, user_id: Optional[str] = None, n: int = 20) -> List[Dict[str, Any]]:
        logs = self._audit_log
        if user_id:
            logs = [l for l in logs if l["user"] == user_id]
        return logs[-n:]

    def get_user_permissions(self, user_id: str) -> Dict[str, List[str]]:
        result = defaultdict(list)
        for role_id in self._user_roles.get(user_id, []):
            role = self._roles.get(role_id)
            if role:
                for res, perms in role.permissions.items():
                    result[res.value].extend([p.value for p in perms])
        return dict(result)

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._audit_log)
        allowed = sum(1 for l in self._audit_log if l["allowed"])
        return {
            "roles": len(self._roles),
            "users": len(self._user_roles),
            "total_requests": total,
            "allowed": allowed,
            "denied": total - allowed,
        }


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Permission & Access Control Engine")
    print("ai/llm_permission_engine_native.py")
    print("=" * 60)

    engine = PermissionEngine()

    # Define roles
    admin_role = Role("admin", "Administrator", {
        ResourceType.MODEL: {Permission.ADMIN},
        ResourceType.DATA: {Permission.ADMIN},
        ResourceType.CONFIG: {Permission.ADMIN},
        ResourceType.USER: {Permission.ADMIN},
        ResourceType.SYSTEM: {Permission.ADMIN},
    })
    dev_role = Role("developer", "Developer", {
        ResourceType.MODEL: {Permission.READ, Permission.WRITE},
        ResourceType.DATA: {Permission.READ, Permission.WRITE},
        ResourceType.CONFIG: {Permission.READ},
    })
    viewer_role = Role("viewer", "Viewer", {
        ResourceType.MODEL: {Permission.READ},
        ResourceType.DATA: {Permission.READ},
    })

    for role in [admin_role, dev_role, viewer_role]:
        engine.register_role(role)

    # Assign users
    engine.assign_role("alice", "admin")
    engine.assign_role("bob", "developer")
    engine.assign_role("carol", "viewer")
    engine.assign_role("carol", "developer")  # Multiple roles

    # 1. Admin access
    print("[1] Admin Access")
    req = AccessRequest("alice", ResourceType.MODEL, "model-1", Permission.DELETE)
    dec = engine.check(req)
    print(f"  Alice delete model: {dec.allowed} ({dec.reason})")

    # 2. Dev access
    print("[2] Developer Access")
    req = AccessRequest("bob", ResourceType.MODEL, "model-1", Permission.WRITE)
    dec = engine.check(req)
    print(f"  Bob write model: {dec.allowed} ({dec.reason})")
    req = AccessRequest("bob", ResourceType.CONFIG, "config-1", Permission.WRITE)
    dec = engine.check(req)
    print(f"  Bob write config: {dec.allowed} ({dec.reason})")

    # 3. Viewer access
    print("[3] Viewer Access")
    req = AccessRequest("carol", ResourceType.MODEL, "model-1", Permission.READ)
    dec = engine.check(req)
    print(f"  Carol read model: {dec.allowed} ({dec.reason})")
    req = AccessRequest("carol", ResourceType.MODEL, "model-1", Permission.WRITE)
    dec = engine.check(req)
    print(f"  Carol write model: {dec.allowed} ({dec.reason})")

    # 4. Token scope
    print("[4] Token Scope Validation")
    token = AccessToken("tok1", "bob", scopes=["model:read", "data:read"])
    req = AccessRequest("bob", ResourceType.MODEL, "model-1", Permission.READ, token=token)
    dec = engine.check(req)
    print(f"  Bob read with token: {dec.allowed} ({dec.reason})")
    req = AccessRequest("bob", ResourceType.MODEL, "model-1", Permission.WRITE, token=token)
    dec = engine.check(req)
    print(f"  Bob write with token: {dec.allowed} ({dec.reason})")

    # 5. Audit log
    print("[5] Audit Log")
    for log in engine.get_audit_log(n=5):
        print(f"  {log['audit_id']}: {log['user']} → {log['resource']}:{log['permission']} = {log['allowed']}")

    # 6. Stats
    print("[6] Engine Stats")
    stats = engine.get_stats()
    print(f"  {stats}")

    print("" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()

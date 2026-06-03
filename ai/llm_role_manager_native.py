"""LLM Role Manager — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set
from enum import Enum, auto

class RoleLevel(Enum):
    SYSTEM = auto()
    ADMIN = auto()
    USER = auto()
    GUEST = auto()

@dataclass
class Role:
    id: str
    name: str
    level: RoleLevel
    permissions: Set[str] = field(default_factory=set)
    inherits: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class RoleManager:
    def __init__(self) -> None:
        self._roles: Dict[str, Role] = {}
        self._assignments: Dict[str, List[str]] = {}

    def add_role(self, role: Role) -> None:
        self._roles[role.id] = role

    def assign(self, user_id: str, role_id: str) -> None:
        if user_id not in self._assignments:
            self._assignments[user_id] = []
        if role_id not in self._assignments[user_id]:
            self._assignments[user_id].append(role_id)

    def revoke(self, user_id: str, role_id: str) -> None:
        if user_id in self._assignments:
            self._assignments[user_id] = [rid for rid in self._assignments[user_id] if rid != role_id]

    def get_permissions(self, user_id: str) -> Set[str]:
        perms = set()
        for role_id in self._assignments.get(user_id, []):
            role = self._roles.get(role_id)
            if role:
                perms.update(role.permissions)
                for parent_id in role.inherits:
                    parent = self._roles.get(parent_id)
                    if parent:
                        perms.update(parent.permissions)
        return perms

    def has_permission(self, user_id: str, permission: str) -> bool:
        return permission in self.get_permissions(user_id)

    def get_roles(self, user_id: str) -> List[Role]:
        return [self._roles[rid] for rid in self._assignments.get(user_id, []) if rid in self._roles]

    def get_stats(self) -> Dict[str, Any]:
        return {"roles": len(self._roles), "assignments": sum(len(a) for a in self._assignments.values())}

def run() -> None:
    print("Role Manager test")
    e = RoleManager()
    e.add_role(Role("admin", "Administrator", RoleLevel.ADMIN, {"read", "write", "delete", "admin"}))
    e.add_role(Role("editor", "Editor", RoleLevel.USER, {"read", "write"}, ["viewer"]))
    e.add_role(Role("viewer", "Viewer", RoleLevel.GUEST, {"read"}))
    e.assign("u1", "admin")
    e.assign("u2", "editor")
    print("  u1 perms: " + str(e.get_permissions("u1")))
    print("  u2 can write: " + str(e.has_permission("u2", "write")))
    print("  u2 can delete: " + str(e.has_permission("u2", "delete")))
    print("  Stats: " + str(e.get_stats()))
    print("Role Manager test complete.")

if __name__ == "__main__":
    run()

"""LLM Access Controller — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set
from enum import Enum, auto

class Permission(Enum):
    READ = auto()
    WRITE = auto()
    EXECUTE = auto()
    DELETE = auto()
    ADMIN = auto()

@dataclass
class Role:
    id: str
    name: str
    permissions: Set[Permission] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class User:
    id: str
    name: str
    roles: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class AccessController:
    def __init__(self) -> None:
        self._roles: Dict[str, Role] = {}
        self._users: Dict[str, User] = {}

    def add_role(self, role: Role) -> None:
        self._roles[role.id] = role

    def add_user(self, user: User) -> None:
        self._users[user.id] = user

    def has_permission(self, user_id: str, permission: Permission) -> bool:
        user = self._users.get(user_id)
        if not user:
            return False
        for role_id in user.roles:
            role = self._roles.get(role_id)
            if role and permission in role.permissions:
                return True
        return False

    def check_access(self, user_id: str, resource: str, action: Permission) -> bool:
        return self.has_permission(user_id, action)

    def get_user_permissions(self, user_id: str) -> Set[Permission]:
        user = self._users.get(user_id)
        if not user:
            return set()
        perms = set()
        for role_id in user.roles:
            role = self._roles.get(role_id)
            if role:
                perms.update(role.permissions)
        return perms

    def get_stats(self) -> Dict[str, Any]:
        return {"roles": len(self._roles), "users": len(self._users)}

def run() -> None:
    print("Access Controller test")
    e = AccessController()
    e.add_role(Role("admin", "Administrator", {Permission.READ, Permission.WRITE, Permission.EXECUTE, Permission.DELETE, Permission.ADMIN}))
    e.add_role(Role("user", "Standard User", {Permission.READ, Permission.WRITE}))
    e.add_role(Role("guest", "Guest", {Permission.READ}))
    e.add_user(User("u1", "Alice", ["admin"]))
    e.add_user(User("u2", "Bob", ["user"]))
    e.add_user(User("u3", "Charlie", ["guest"]))
    print("  Alice can DELETE: " + str(e.has_permission("u1", Permission.DELETE)))
    print("  Bob can DELETE: " + str(e.has_permission("u2", Permission.DELETE)))
    print("  Charlie perms: " + str([p.name for p in e.get_user_permissions("u3")]))
    print("  Stats: " + str(e.get_stats()))
    print("Access Controller test complete.")

if __name__ == "__main__":
    run()

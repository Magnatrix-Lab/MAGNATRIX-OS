"""Access Control - RBAC for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple
from enum import Enum, auto

class Permission(Enum):
    READ = auto(); WRITE = auto(); EXECUTE = auto(); DELETE = auto()

@dataclass
class AccessControl:
    roles: Dict[str, List[Permission]] = field(default_factory=dict)
    user_roles: Dict[str, List[str]] = field(default_factory=dict)
    resource_permissions: Dict[str, List[Permission]] = field(default_factory=dict)

    def add_role(self, role: str, permissions: List[Permission]) -> None:
        self.roles[role] = permissions

    def assign_role(self, user: str, role: str) -> None:
        if user not in self.user_roles: self.user_roles[user] = []
        if role not in self.user_roles[user]: self.user_roles[user].append(role)

    def set_resource_permissions(self, resource: str, permissions: List[Permission]) -> None:
        self.resource_permissions[resource] = permissions

    def can_access(self, user: str, resource: str, permission: Permission) -> bool:
        user_perms = set()
        for role in self.user_roles.get(user, []):
            user_perms.update(self.roles.get(role, []))
        resource_perms = set(self.resource_permissions.get(resource, []))
        return permission in user_perms and permission in resource_perms

    def stats(self) -> dict:
        return {"roles": len(self.roles), "users": len(self.user_roles), "resources": len(self.resource_permissions)}

def run():
    ac = AccessControl()
    ac.add_role("admin", [Permission.READ, Permission.WRITE, Permission.DELETE])
    ac.add_role("user", [Permission.READ])
    ac.assign_role("alice", "admin")
    ac.set_resource_permissions("file1", [Permission.READ, Permission.WRITE])
    print("Alice can read file1:", ac.can_access("alice", "file1", Permission.READ))
    print("Alice can delete file1:", ac.can_access("alice", "file1", Permission.DELETE))
    print("Stats:", ac.stats())

if __name__ == "__main__": run()

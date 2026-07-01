#!/usr/bin/env python3
"""rbac_native.py — MAGNATRIX-OS Role-Based Access Control (RBAC) System"""
from __future__ import annotations
import json, threading, time, uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

@dataclass
class Permission:
    resource: str; action: str; allowed: bool = True; conditions: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Role:
    name: str; description: str; permissions: List[Permission] = field(default_factory=list)
    priority: int = 0; metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class UserRole:
    user_id: str; role: str; assigned_by: str = ""; assigned_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None; metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class AccessLog:
    timestamp: float; user_id: str; resource: str; action: str; granted: bool
    reason: str = ""; role_used: str = ""; request_id: str = ""

class RBACNative:
    def __init__(self, workspace: str = "./rbac") -> None:
        self.workspace = Path(workspace); self.workspace.mkdir(parents=True, exist_ok=True)
        self._roles: Dict[str, Role] = {}; self._user_roles: Dict[str, List[UserRole]] = {}
        self._access_logs: List[AccessLog] = []
        self._lock = threading.RLock()
        self._roles_path = self.workspace / "roles.json"
        self._user_roles_path = self.workspace / "user_roles.json"
        self._logs_path = self.workspace / "access_logs.json"
        self._load()

    def _load(self) -> None:
        if self._roles_path.exists():
            try:
                with open(self._roles_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for name, rd in data.items():
                    rd["permissions"] = [Permission(**p) for p in rd.get("permissions", [])]
                    self._roles[name] = Role(**rd)
            except Exception: self._default_roles()
        else: self._default_roles()
        if self._user_roles_path.exists():
            try:
                with open(self._user_roles_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for uid, urs in data.items(): self._user_roles[uid] = [UserRole(**ur) for ur in urs]
            except Exception: pass
        if self._logs_path.exists():
            try:
                with open(self._logs_path, "r", encoding="utf-8") as f: self._access_logs = [AccessLog(**a) for a in json.load(f)]
            except Exception: pass

    def _save(self) -> None:
        with open(self._roles_path, "w", encoding="utf-8") as f:
            json.dump({name: asdict(r) for name, r in self._roles.items()}, f, indent=2, default=str)
        with open(self._user_roles_path, "w", encoding="utf-8") as f:
            json.dump({uid: [asdict(ur) for ur in urs] for uid, urs in self._user_roles.items()}, f, indent=2, default=str)
        with open(self._logs_path, "w", encoding="utf-8") as f:
            json.dump([asdict(a) for a in self._access_logs[-2000:]], f, indent=2, default=str)

    def _default_roles(self) -> None:
        defaults = [
            Role("admin", "Full system access", [Permission("*", "*")], priority=100),
            Role("developer", "Can read/write code and config", [Permission("core/*", "read"), Permission("core/*", "write"), Permission("modules/*", "read"), Permission("modules/*", "write"), Permission("config/*", "read"), Permission("config/*", "write")], priority=50),
            Role("operator", "Can read and execute, limited write", [Permission("core/*", "read"), Permission("modules/*", "read"), Permission("modules/*", "execute"), Permission("logs/*", "read"), Permission("metrics/*", "read"), Permission("metrics/*", "write")], priority=30),
            Role("auditor", "Read-only access to all", [Permission("*", "read"), Permission("logs/*", "read"), Permission("audit/*", "read")], priority=20),
            Role("viewer", "Read-only access to public resources", [Permission("public/*", "read"), Permission("docs/*", "read")], priority=10),
            Role("restricted", "Minimal access", [Permission("public/*", "read")], priority=5),
        ]
        for r in defaults: self._roles[r.name] = r
        self._save()

    def create_role(self, role: Role) -> None:
        with self._lock: self._roles[role.name] = role; self._save()

    def delete_role(self, name: str) -> bool:
        with self._lock:
            if name in self._roles: del self._roles[name]; self._save(); return True
            return False

    def list_roles(self) -> List[str]:
        with self._lock: return list(self._roles.keys())

    def get_role(self, name: str) -> Optional[Role]:
        with self._lock: return self._roles.get(name)

    def assign_role(self, user_id: str, role_name: str, assigned_by: str = "", expires_days: Optional[int] = None) -> bool:
        with self._lock:
            if role_name not in self._roles: return False
            expires = time.time() + (expires_days * 86400) if expires_days else None
            if user_id not in self._user_roles: self._user_roles[user_id] = []
            self._user_roles[user_id].append(UserRole(user_id=user_id, role=role_name, assigned_by=assigned_by, expires_at=expires))
            self._save(); return True

    def revoke_role(self, user_id: str, role_name: str) -> bool:
        with self._lock:
            if user_id not in self._user_roles: return False
            original = len(self._user_roles[user_id])
            self._user_roles[user_id] = [ur for ur in self._user_roles[user_id] if ur.role != role_name]
            if len(self._user_roles[user_id]) < original: self._save(); return True
            return False

    def get_user_roles(self, user_id: str) -> List[str]:
        with self._lock:
            if user_id not in self._user_roles: return []
            now = time.time()
            return [ur.role for ur in self._user_roles[user_id] if ur.expires_at is None or ur.expires_at > now]

    def check(self, user_id: str, resource: str, action: str) -> Tuple[bool, str]:
        with self._lock:
            role_names = self.get_user_roles(user_id)
            if not role_names:
                self._log_access(user_id, resource, action, False, "No roles assigned")
                return False, "No roles assigned"
            for role_name in sorted(role_names, key=lambda r: self._roles.get(r, Role(r, "", [])).priority, reverse=True):
                role = self._roles.get(role_name)
                if not role: continue
                for perm in role.permissions:
                    if self._match_resource(perm.resource, resource) and self._match_action(perm.action, action):
                        if perm.allowed:
                            self._log_access(user_id, resource, action, True, f"Granted by role: {role_name}", role_name)
                            return True, f"Granted by role: {role_name}"
                        else:
                            self._log_access(user_id, resource, action, False, f"Denied by explicit permission in role: {role_name}", role_name)
                            return False, f"Denied by explicit permission in role: {role_name}"
            self._log_access(user_id, resource, action, False, "No matching permission found")
            return False, "No matching permission found"

    def _match_resource(self, pattern: str, resource: str) -> bool:
        if pattern == "*": return True
        if pattern.endswith("/*"):
            prefix = pattern[:-1]
            return resource.startswith(prefix) or resource == prefix[:-1]
        return pattern == resource

    def _match_action(self, pattern: str, action: str) -> bool:
        if pattern == "*": return True
        return pattern == action

    def _log_access(self, user_id: str, resource: str, action: str, granted: bool, reason: str = "", role_used: str = "") -> None:
        log = AccessLog(timestamp=time.time(), user_id=user_id, resource=resource, action=action, granted=granted, reason=reason, role_used=role_used, request_id=str(uuid.uuid4())[:8])
        self._access_logs.append(log)
        if len(self._access_logs) > 5000: self._access_logs = self._access_logs[-4000:]
        self._save()

    def get_access_logs(self, user_id: Optional[str] = None, resource: Optional[str] = None, limit: int = 100) -> List[AccessLog]:
        with self._lock:
            logs = self._access_logs
            if user_id: logs = [l for l in logs if l.user_id == user_id]
            if resource: logs = [l for l in logs if l.resource == resource]
            return logs[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total = len(self._access_logs)
            granted = sum(1 for l in self._access_logs if l.granted)
            return {"total_checks": total, "granted": granted, "denied": total - granted, "roles": len(self._roles), "users": len(self._user_roles)}

if __name__ == "__main__":
    rbac = RBACNative()
    rbac.assign_role("user_001", "developer")
    print("Roles:", rbac.list_roles())
    print("Check read core/vector_memory:", rbac.check("user_001", "core/vector_memory", "read"))
    print("Check admin:", rbac.check("user_001", "admin", "write"))

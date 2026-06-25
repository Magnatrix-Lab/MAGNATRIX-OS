#!/usr/bin/env python3
"""
Security Policy Engine for MAGNATRIX-OS
Fine-grained RBAC per module, policy-as-code, audit trail, compliance reports.
Pure stdlib — no external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


@dataclass
class Permission:
    """A single permission action."""
    resource: str
    action: str  # read, write, execute, delete, admin


@dataclass
class Role:
    """A role with associated permissions."""
    name: str
    description: str = ""
    permissions: List[Permission] = field(default_factory=list)
    inherits: List[str] = field(default_factory=list)


@dataclass
class AuditEntry:
    """Single audit log entry."""
    timestamp: float
    actor: str
    action: str
    resource: str
    result: str  # allowed, denied, error
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Policy:
    """A declarative security policy."""
    id: str
    version: str
    rules: List[Dict[str, Any]] = field(default_factory=list)
    default_action: str = "deny"
    metadata: Dict[str, Any] = field(default_factory=dict)


class PolicyEngine:
    """Evaluate policies against requests."""

    ACTIONS = {"read", "write", "execute", "delete", "admin"}

    def __init__(self, default_policy: str = "deny") -> None:
        self.default = default_policy
        self._policies: List[Policy] = []
        self._rules: List[Dict[str, Any]] = []

    def load_policy(self, policy: Policy) -> None:
        self._policies.append(policy)
        self._rules.extend(policy.rules)

    def load_from_file(self, path: str) -> bool:
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            policy = Policy(
                id=data.get("id", str(int(time.time()))),
                version=data.get("version", "1.0.0"),
                rules=data.get("rules", []),
                default_action=data.get("default_action", "deny"),
                metadata=data.get("metadata", {}),
            )
            self.load_policy(policy)
            return True
        except Exception:
            return False

    def evaluate(self, actor: str, action: str, resource: str, context: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """Evaluate if action is allowed. Returns (allowed, reason)."""
        context = context or {}
        for rule in self._rules:
            match = self._match_rule(rule, actor, action, resource, context)
            if match:
                rule_action = rule.get("action", "deny")
                return (rule_action == "allow", f"Rule matched: {rule.get('id', 'unknown')}")
        return (self.default == "allow", f"Default policy: {self.default}")

    def _match_rule(self, rule: Dict[str, Any], actor: str, action: str, resource: str, context: Dict[str, Any]) -> bool:
        """Check if a rule matches the request."""
        # Match actor
        if "actors" in rule and actor not in rule["actors"]:
            return False
        # Match action
        if "actions" in rule and action not in rule["actions"]:
            return False
        # Match resource (supports wildcards)
        if "resources" in rule:
            matched = any(self._match_pattern(resource, pat) for pat in rule["resources"])
            if not matched:
                return False
        # Match context conditions
        if "conditions" in rule:
            for cond in rule["conditions"]:
                if not self._eval_condition(cond, context):
                    return False
        return True

    def _match_pattern(self, text: str, pattern: str) -> bool:
        if pattern == "*":
            return True
        if pattern.endswith("*"):
            return text.startswith(pattern[:-1])
        if pattern.startswith("*"):
            return text.endswith(pattern[1:])
        return text == pattern

    def _eval_condition(self, cond: Dict[str, Any], context: Dict[str, Any]) -> bool:
        key = cond.get("key", "")
        op = cond.get("operator", "==")
        value = cond.get("value")
        ctx_val = context.get(key)
        if op == "==":
            return ctx_val == value
        elif op == "!=":
            return ctx_val != value
        elif op == "in":
            return ctx_val in value if isinstance(value, list) else False
        elif op == "exists":
            return key in context
        return False

    def export_policy(self, policy_id: str) -> Optional[Dict[str, Any]]:
        for p in self._policies:
            if p.id == policy_id:
                return {
                    "id": p.id, "version": p.version,
                    "rules": p.rules, "default_action": p.default_action,
                    "metadata": p.metadata,
                }
        return None

    def list_policies(self) -> List[Dict[str, Any]]:
        return [{"id": p.id, "version": p.version, "rules": len(p.rules)} for p in self._policies]


class RBACManager:
    """Role-based access control manager."""

    def __init__(self) -> None:
        self._roles: Dict[str, Role] = {}
        self._user_roles: Dict[str, Set[str]] = {}
        self._lock = False

    def create_role(self, name: str, description: str = "", permissions: List[Permission] = None, inherits: List[str] = None) -> Role:
        role = Role(name=name, description=description, permissions=permissions or [], inherits=inherits or [])
        self._roles[name] = role
        return role

    def assign_role(self, user: str, role: str) -> bool:
        if role not in self._roles:
            return False
        if user not in self._user_roles:
            self._user_roles[user] = set()
        self._user_roles[user].add(role)
        return True

    def revoke_role(self, user: str, role: str) -> bool:
        if user in self._user_roles and role in self._user_roles[user]:
            self._user_roles[user].remove(role)
            return True
        return False

    def check_permission(self, user: str, resource: str, action: str) -> bool:
        """Check if user has permission for action on resource."""
        roles = self._user_roles.get(user, set())
        for role_name in roles:
            role = self._roles.get(role_name)
            if not role:
                continue
            # Check direct permissions
            for perm in role.permissions:
                if self._match_resource(resource, perm.resource) and action == perm.action:
                    return True
            # Check inherited permissions
            for inherit_name in role.inherits:
                inherit_role = self._roles.get(inherit_name)
                if inherit_role:
                    for perm in inherit_role.permissions:
                        if self._match_resource(resource, perm.resource) and action == perm.action:
                            return True
        return False

    def _match_resource(self, requested: str, allowed: str) -> bool:
        if allowed == "*" or allowed == "all":
            return True
        if allowed.endswith("*"):
            return requested.startswith(allowed[:-1])
        return requested == allowed

    def get_user_permissions(self, user: str) -> List[Dict[str, Any]]:
        roles = self._user_roles.get(user, set())
        perms = []
        for role_name in roles:
            role = self._roles.get(role_name)
            if role:
                perms.extend([{"resource": p.resource, "action": p.action, "role": role_name} for p in role.permissions])
        return perms

    def list_roles(self) -> List[Dict[str, Any]]:
        return [{"name": r.name, "description": r.description, "permissions": len(r.permissions), "inherits": r.inherits} for r in self._roles.values()]

    def list_users(self) -> List[Dict[str, Any]]:
        return [{"user": u, "roles": list(roles)} for u, roles in self._user_roles.items()]

    def save(self, path: str) -> str:
        data = {
            "roles": [
                {
                    "name": r.name, "description": r.description,
                    "permissions": [{"resource": p.resource, "action": p.action} for p in r.permissions],
                    "inherits": r.inherits,
                }
                for r in self._roles.values()
            ],
            "user_roles": {u: list(roles) for u, roles in self._user_roles.items()},
        }
        Path(path).write_text(json.dumps(data, indent=2), encoding="utf-8")
        return path

    def load(self, path: str) -> bool:
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            for r in data.get("roles", []):
                perms = [Permission(p["resource"], p["action"]) for p in r.get("permissions", [])]
                self.create_role(r["name"], r.get("description", ""), perms, r.get("inherits", []))
            for user, roles in data.get("user_roles", {}).items():
                for role in roles:
                    self.assign_role(user, role)
            return True
        except Exception:
            return False


class AuditTrail:
    """Comprehensive audit logging system."""

    def __init__(self, store_dir: str = "./audit") -> None:
        self.store_dir = Path(store_dir)
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self._entries: List[AuditEntry] = []
        self._tamper_hash = ""

    def log(self, actor: str, action: str, resource: str, result: str, reason: str = "", metadata: Dict[str, Any] = None) -> None:
        entry = AuditEntry(
            timestamp=time.time(),
            actor=actor,
            action=action,
            resource=resource,
            result=result,
            reason=reason,
            metadata=metadata or {},
        )
        self._entries.append(entry)
        self._update_hash()
        self._persist()

    def _update_hash(self) -> None:
        data = json.dumps([self._entry_to_dict(e) for e in self._entries], sort_keys=True)
        self._tamper_hash = hmac.new(b"audit-key", data.encode(), hashlib.sha256).hexdigest()[:32]

    def _entry_to_dict(self, entry: AuditEntry) -> Dict[str, Any]:
        return {
            "timestamp": entry.timestamp,
            "actor": entry.actor,
            "action": entry.action,
            "resource": entry.resource,
            "result": entry.result,
            "reason": entry.reason,
            "metadata": entry.metadata,
        }

    def _persist(self) -> None:
        data = {
            "entries": [self._entry_to_dict(e) for e in self._entries[-1000:]],
            "hash": self._tamper_hash,
        }
        (self.store_dir / "audit.json").write_text(json.dumps(data, indent=2), encoding="utf-8")

    def verify_integrity(self) -> bool:
        """Verify audit trail has not been tampered with."""
        data = json.dumps([self._entry_to_dict(e) for e in self._entries], sort_keys=True)
        expected = hmac.new(b"audit-key", data.encode(), hashlib.sha256).hexdigest()[:32]
        return hmac.compare_digest(self._tamper_hash, expected)

    def query(self, actor: Optional[str] = None, action: Optional[str] = None, resource: Optional[str] = None, start_time: Optional[float] = None, end_time: Optional[float] = None, limit: int = 100) -> List[AuditEntry]:
        results = []
        for entry in reversed(self._entries):
            if actor and entry.actor != actor:
                continue
            if action and entry.action != action:
                continue
            if resource and not entry.resource.startswith(resource):
                continue
            if start_time and entry.timestamp < start_time:
                continue
            if end_time and entry.timestamp > end_time:
                continue
            results.append(entry)
            if len(results) >= limit:
                break
        return results

    def generate_report(self, start_time: Optional[float] = None, end_time: Optional[float] = None) -> Dict[str, Any]:
        entries = self.query(start_time=start_time, end_time=end_time, limit=10000)
        stats = {}
        for e in entries:
            key = f"{e.action}:{e.result}"
            stats[key] = stats.get(key, 0) + 1

        actors = {}
        for e in entries:
            actors[e.actor] = actors.get(e.actor, 0) + 1

        resources = {}
        for e in entries:
            resources[e.resource] = resources.get(e.resource, 0) + 1

        return {
            "period": {"start": start_time, "end": end_time},
            "total_entries": len(entries),
            "stats": stats,
            "top_actors": sorted(actors.items(), key=lambda x: x[1], reverse=True)[:10],
            "top_resources": sorted(resources.items(), key=lambda x: x[1], reverse=True)[:10],
            "integrity": self.verify_integrity(),
        }

    def save_report(self, path: str) -> str:
        report = self.generate_report()
        Path(path).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return path


class SecurityPolicyManager:
    """Unified security manager combining RBAC, Policy Engine, and Audit."""

    def __init__(self, repo_root: str) -> None:
        self.root = Path(repo_root).resolve()
        self.policy = PolicyEngine(default_policy="deny")
        self.rbac = RBACManager()
        self.audit = AuditTrail(str(self.root / "data" / "audit"))
        self._setup_default_roles()

    def _setup_default_roles(self) -> None:
        self.rbac.create_role("admin", "Full system access", [Permission("*", "admin")])
        self.rbac.create_role("operator", "Module execution", [Permission("*", "execute"), Permission("*", "read")])
        self.rbac.create_role("developer", "Development access", [Permission("core.*", "read"), Permission("core.*", "write")])
        self.rbac.create_role("viewer", "Read-only access", [Permission("*", "read")])
        self.rbac.create_role("service", "Service account", [Permission("api.*", "execute")])

    def check(self, user: str, action: str, resource: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Full security check: RBAC + Policy."""
        # First check RBAC
        rbac_ok = self.rbac.check_permission(user, resource, action)
        # Then check policy
        policy_ok, reason = self.policy.evaluate(user, action, resource, context)

        result = "allowed" if (rbac_ok and policy_ok) else "denied"
        self.audit.log(user, action, resource, result, reason=reason, metadata=context)
        return rbac_ok and policy_ok

    def enforce(self, user: str, action: str, resource: str, context: Optional[Dict[str, Any]] = None) -> None:
        if not self.check(user, action, resource, context):
            raise PermissionError(f"Access denied: {user} cannot {action} on {resource}")

    def stats(self) -> Dict[str, Any]:
        return {
            "roles": len(self.rbac.list_roles()),
            "users": len(self.rbac.list_users()),
            "policies": len(self.policy.list_policies()),
            "audit_entries": len(self.audit._entries),
            "integrity": self.audit.verify_integrity(),
        }


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    print("=== Security Policy Engine Demo ===\n")
    manager = SecurityPolicyManager(repo_root="/tmp/magnatrix_security")

    # Set up users and roles
    manager.rbac.assign_role("alice", "admin")
    manager.rbac.assign_role("bob", "developer")
    manager.rbac.assign_role("charlie", "viewer")

    # Load a policy
    policy_data = {
        "id": "restrict-sensitive",
        "version": "1.0.0",
        "rules": [
            {
                "id": "allow-admins",
                "actors": ["alice"],
                "actions": ["admin"],
                "resources": ["*"],
                "action": "allow",
            },
            {
                "id": "deny-production-delete",
                "actors": ["*"],
                "actions": ["delete"],
                "resources": ["production.*"],
                "action": "deny",
            },
        ],
        "default_action": "deny",
    }
    Path("/tmp/test_policy.json").write_text(json.dumps(policy_data))
    manager.policy.load_from_file("/tmp/test_policy.json")

    # Test checks
    tests = [
        ("alice", "admin", "system.config", True),
        ("bob", "write", "core.config", True),
        ("bob", "delete", "production.db", False),
        ("charlie", "read", "system.status", True),
        ("charlie", "write", "system.config", False),
    ]

    for user, action, resource, expected in tests:
        result = manager.check(user, action, resource)
        status = "✓" if result == expected else "✗"
        print(f"  {status} {user} {action} {resource}: {result} (expected {expected})")

    print(f"\nStats: {manager.stats()}")
    print(f"\nAudit report: {manager.audit.generate_report()}")
    print(f"Roles: {manager.rbac.list_roles()}")


if __name__ == "__main__":
    _demo()

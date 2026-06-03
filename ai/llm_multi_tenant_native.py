"""
llm_multi_tenant_native.py
MAGNATRIX-OS Multi-Tenant Engine
Native Python, stdlib only.
Provides tenant isolation, resource quotas, per-tenant config, and cross-tenant access control.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set


class TenantStatus(Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"
    DELETED = "deleted"


@dataclass
class Tenant:
    tenant_id: str
    name: str
    status: TenantStatus = TenantStatus.ACTIVE
    quotas: Dict[str, float] = field(default_factory=dict)
    usage: Dict[str, float] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    allowed_models: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tenant_id": self.tenant_id, "name": self.name, "status": self.status.value,
            "quotas": self.quotas, "usage": self.usage, "config": self.config,
            "allowed_models": self.allowed_models, "metadata": self.metadata,
        }

    def check_quota(self, resource: str, amount: float) -> bool:
        limit = self.quotas.get(resource, float('inf'))
        current = self.usage.get(resource, 0.0)
        return current + amount <= limit

    def consume(self, resource: str, amount: float) -> bool:
        if not self.check_quota(resource, amount):
            return False
        self.usage[resource] = self.usage.get(resource, 0.0) + amount
        return True


class MultiTenantEngine:
    """Multi-tenant isolation and resource management."""

    def __init__(self) -> None:
        self._tenants: Dict[str, Tenant] = {}
        self._handlers: List[Callable[[str, str, float], None]] = []

    def create_tenant(self, tenant_id: str, name: str, quotas: Optional[Dict[str, float]] = None,
                      config: Optional[Dict[str, Any]] = None) -> Tenant:
        tenant = Tenant(tenant_id=tenant_id, name=name, quotas=quotas or {}, config=config or {})
        self._tenants[tenant_id] = tenant
        return tenant

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        return self._tenants.get(tenant_id)

    def consume_resource(self, tenant_id: str, resource: str, amount: float) -> bool:
        tenant = self._tenants.get(tenant_id)
        if not tenant or tenant.status != TenantStatus.ACTIVE:
            return False
        ok = tenant.consume(resource, amount)
        if not ok:
            for handler in self._handlers:
                handler(tenant_id, resource, amount)
        return ok

    def check_access(self, tenant_id: str, model: str) -> bool:
        tenant = self._tenants.get(tenant_id)
        if not tenant or tenant.status != TenantStatus.ACTIVE:
            return False
        if tenant.allowed_models and model not in tenant.allowed_models:
            return False
        return True

    def set_config(self, tenant_id: str, key: str, value: Any) -> bool:
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return False
        tenant.config[key] = value
        return True

    def get_config(self, tenant_id: str, key: str, default: Any = None) -> Any:
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return default
        return tenant.config.get(key, default)

    def suspend(self, tenant_id: str) -> bool:
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return False
        tenant.status = TenantStatus.SUSPENDED
        return True

    def resume(self, tenant_id: str) -> bool:
        tenant = self._tenants.get(tenant_id)
        if not tenant:
            return False
        tenant.status = TenantStatus.ACTIVE
        return True

    def add_quota_handler(self, handler: Callable[[str, str, float], None]) -> None:
        self._handlers.append(handler)

    def list_tenants(self, status: Optional[TenantStatus] = None) -> List[Tenant]:
        tenants = list(self._tenants.values())
        if status:
            tenants = [t for t in tenants if t.status == status]
        return tenants

    def get_stats(self) -> Dict[str, Any]:
        return {
            "tenants": len(self._tenants),
            "active": len([t for t in self._tenants.values() if t.status == TenantStatus.ACTIVE]),
            "suspended": len([t for t in self._tenants.values() if t.status == TenantStatus.SUSPENDED]),
        }


def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS Multi-Tenant Engine")
    print("=" * 60)

    engine = MultiTenantEngine()

    def quota_alert(tenant_id: str, resource: str, amount: float) -> None:
        print(f"  [QUOTA ALERT] Tenant {tenant_id} exceeded {resource} quota (requested {amount})")

    engine.add_quota_handler(quota_alert)

    print("\n--- Create tenants ---")
    t1 = engine.create_tenant("t1", "Acme Corp", quotas={"tokens": 1000000, "requests": 10000}, allowed_models=["gpt-4o"])
    t2 = engine.create_tenant("t2", "Startup Inc", quotas={"tokens": 100000, "requests": 1000})
    print(f"  Created: {t1.tenant_id} ({t1.name})")
    print(f"  Created: {t2.tenant_id} ({t2.name})")

    print("\n--- Consume resources ---")
    for i in range(5):
        ok = engine.consume_resource("t1", "tokens", 250000)
        print(f"  t1 consume 250k tokens: {ok}")
    ok = engine.consume_resource("t2", "tokens", 150000)
    print(f"  t2 consume 150k tokens: {ok}")

    print("\n--- Check access ---")
    print(f"  t1 access gpt-4o: {engine.check_access('t1', 'gpt-4o')}")
    print(f"  t1 access claude-3: {engine.check_access('t1', 'claude-3')}")

    print("\n--- Config ---")
    engine.set_config("t1", "temperature", 0.7)
    print(f"  t1 temperature: {engine.get_config('t1', 'temperature')}")

    print("\n--- Stats ---")
    print(engine.get_stats())

    print("\nMulti-Tenant test complete.")


if __name__ == "__main__":
    run()

"""infrastructure/multi_tenant_native.py — Multi-Tenant Isolation for MAGNATRIX-OS.

Pure-stdlib multi-tenant system with tenant identification, data/config/resource
isolation, provisioning, quota management, billing simulation, and audit logging.

Rules: no third-party deps, type hints, docstrings, self-test in __main__.
"""
from __future__ import annotations

import json
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class TenantIdentification(Enum):
    HEADER = "header"
    SUBDOMAIN = "subdomain"
    PATH = "path"


@dataclass
class Tenant:
    tenant_id: str
    name: str
    plan: str = "basic"
    created_at: float = 0.0
    quotas: Dict[str, int] = field(default_factory=dict)
    usage: Dict[str, int] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    data: Dict[str, Any] = field(default_factory=dict)
    resources: Dict[str, Any] = field(default_factory=dict)
    audit: List[Dict[str, Any]] = field(default_factory=list)
    active: bool = True


class MultiTenant:
    """Multi-tenant isolation and management engine.

    Features:
        - Tenant identification via header, subdomain, or path prefix
        - Isolated data, config, and resource namespaces
        - Tenant provisioning with template defaults
        - Quota enforcement (requests, storage, compute units)
        - Billing simulation (usage-based, tiered pricing)
        - Audit log for tenant-scoped actions
    """

    def __init__(
        self,
        ident: TenantIdentification = TenantIdentification.HEADER,
        header_name: str = "X-Tenant-ID",
        default_quotas: Optional[Dict[str, int]] = None,
        pricing: Optional[Dict[str, float]] = None,
    ) -> None:
        self.ident = ident
        self.header_name = header_name
        self._tenants: Dict[str, Tenant] = {}
        self._default_quotas = default_quotas or {"requests": 1000, "storage_mb": 500, "compute_units": 100}
        self._pricing = pricing or {"requests": 0.001, "storage_mb": 0.01, "compute_units": 0.05}
        self._global_audit: List[Dict[str, Any]] = []

    # ---- Identification -----------------------------------------------

    def identify(self, request: Dict[str, Any]) -> Optional[str]:
        """Extract tenant ID from incoming request."""
        if self.ident == TenantIdentification.HEADER:
            return request.get("headers", {}).get(self.header_name)
        if self.ident == TenantIdentification.SUBDOMAIN:
            host = request.get("headers", {}).get("Host", "")
            parts = host.split(".")
            return parts[0] if len(parts) > 2 else None
        if self.ident == TenantIdentification.PATH:
            path = request.get("path", "")
            m = path.strip("/").split("/")
            return m[0] if m else None
        return None

    # ---- Provisioning -----------------------------------------------

    def provision(self, name: str, plan: str = "basic", custom_config: Optional[Dict[str, Any]] = None) -> Tenant:
        """Create a new tenant with isolated namespace."""
        tid = str(uuid.uuid4())[:12]
        tenant = Tenant(
            tenant_id=tid,
            name=name,
            plan=plan,
            created_at=time.time(),
            quotas=dict(self._default_quotas),
            usage={k: 0 for k in self._default_quotas},
            config=custom_config or {},
        )
        # Plan-specific overrides
        if plan == "pro":
            tenant.quotas = {k: v * 10 for k, v in tenant.quotas.items()}
        elif plan == "enterprise":
            tenant.quotas = {k: v * 100 for k, v in tenant.quotas.items()}
        self._tenants[tid] = tenant
        self._audit(tid, "provision", {"plan": plan, "name": name})
        return tenant

    def get(self, tenant_id: str) -> Optional[Tenant]:
        return self._tenants.get(tenant_id)

    def list_tenants(self) -> List[Tenant]:
        return list(self._tenants.values())

    def deactivate(self, tenant_id: str) -> bool:
        t = self._tenants.get(tenant_id)
        if t:
            t.active = False
            self._audit(tenant_id, "deactivate", {})
            return True
        return False

    def delete(self, tenant_id: str) -> bool:
        if tenant_id in self._tenants:
            self._audit(tenant_id, "delete", {})
            del self._tenants[tenant_id]
            return True
        return False

    # ---- Isolation --------------------------------------------------

    def get_data(self, tenant_id: str, key: str) -> Any:
        """Retrieve tenant-scoped data."""
        t = self._tenants.get(tenant_id)
        if t is None:
            raise TenantError(f"Unknown tenant: {tenant_id}")
        return t.data.get(key)

    def set_data(self, tenant_id: str, key: str, value: Any) -> None:
        """Store tenant-scoped data."""
        t = self._tenants.get(tenant_id)
        if t is None:
            raise TenantError(f"Unknown tenant: {tenant_id}")
        t.data[key] = value
        self._audit(tenant_id, "set_data", {"key": key})

    def get_config(self, tenant_id: str, key: Optional[str] = None) -> Any:
        t = self._tenants.get(tenant_id)
        if t is None:
            raise TenantError(f"Unknown tenant: {tenant_id}")
        if key is None:
            return dict(t.config)
        return t.config.get(key)

    def set_config(self, tenant_id: str, key: str, value: Any) -> None:
        t = self._tenants.get(tenant_id)
        if t is None:
            raise TenantError(f"Unknown tenant: {tenant_id}")
        t.config[key] = value
        self._audit(tenant_id, "set_config", {"key": key})

    def allocate_resource(self, tenant_id: str, resource_type: str, amount: int) -> bool:
        t = self._tenants.get(tenant_id)
        if t is None or not t.active:
            return False
        t.resources[resource_type] = t.resources.get(resource_type, 0) + amount
        self._audit(tenant_id, "allocate_resource", {"type": resource_type, "amount": amount})
        return True

    # ---- Quotas ------------------------------------------------------

    def check_quota(self, tenant_id: str, metric: str, requested: int = 1) -> bool:
        """Check if tenant has remaining quota for a metric."""
        t = self._tenants.get(tenant_id)
        if t is None or not t.active:
            return False
        return (t.usage.get(metric, 0) + requested) <= t.quotas.get(metric, 0)

    def consume(self, tenant_id: str, metric: str, amount: int = 1) -> bool:
        """Consume quota for a metric."""
        t = self._tenants.get(tenant_id)
        if t is None or not t.active:
            return False
        if not self.check_quota(tenant_id, metric, amount):
            return False
        t.usage[metric] = t.usage.get(metric, 0) + amount
        self._audit(tenant_id, "consume", {"metric": metric, "amount": amount})
        return True

    def get_usage(self, tenant_id: str) -> Dict[str, Any]:
        t = self._tenants.get(tenant_id)
        if t is None:
            return {}
        return {k: {"used": t.usage.get(k, 0), "limit": t.quotas.get(k, 0)} for k in t.quotas}

    # ---- Billing simulation -----------------------------------------

    def simulate_bill(self, tenant_id: str) -> Dict[str, Any]:
        """Calculate estimated bill based on usage and pricing."""
        t = self._tenants.get(tenant_id)
        if t is None:
            raise TenantError(f"Unknown tenant: {tenant_id}")
        line_items = []
        total = 0.0
        for metric, used in t.usage.items():
            rate = self._pricing.get(metric, 0.0)
            cost = used * rate
            line_items.append({"metric": metric, "used": used, "rate": rate, "cost": round(cost, 4)})
            total += cost
        return {"tenant_id": tenant_id, "plan": t.plan, "line_items": line_items, "total": round(total, 4)}

    # ---- Audit --------------------------------------------------------

    def _audit(self, tenant_id: str, action: str, details: Dict[str, Any]) -> None:
        entry = {"time": time.time(), "tenant_id": tenant_id, "action": action, "details": details}
        self._global_audit.append(entry)
        t = self._tenants.get(tenant_id)
        if t:
            t.audit.append(entry)

    def get_audit(self, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if tenant_id is None:
            return self._global_audit[:]
        t = self._tenants.get(tenant_id)
        return t.audit[:] if t else []

    def to_json(self) -> str:
        return json.dumps({
            "tenants": {tid: {"name": t.name, "plan": t.plan, "active": t.active, "usage": t.usage} for tid, t in self._tenants.items()}
        }, indent=2)


class TenantError(Exception):
    pass


def run() -> None:
    """Self-test: provision, identify, isolate, quota, billing, audit."""
    mt = MultiTenant(ident=TenantIdentification.HEADER, header_name="X-Tenant-ID")

    # Provision tenants
    t1 = mt.provision("Acme Corp", plan="basic")
    t2 = mt.provision("Globex", plan="pro")
    assert t1.plan == "basic"
    assert t2.plan == "pro"
    assert t2.quotas["requests"] == t1.quotas["requests"] * 10

    # Identification
    req_basic = {"headers": {"X-Tenant-ID": t1.tenant_id}, "path": "/api/data"}
    req_pro = {"headers": {"X-Tenant-ID": t2.tenant_id}, "path": "/api/data"}
    assert mt.identify(req_basic) == t1.tenant_id
    assert mt.identify(req_pro) == t2.tenant_id

    # Data isolation
    mt.set_data(t1.tenant_id, "logo", "acme.png")
    mt.set_data(t2.tenant_id, "logo", "globex.png")
    assert mt.get_data(t1.tenant_id, "logo") == "acme.png"
    assert mt.get_data(t2.tenant_id, "logo") == "globex.png"

    # Config isolation
    mt.set_config(t1.tenant_id, "theme", "light")
    mt.set_config(t2.tenant_id, "theme", "dark")
    assert mt.get_config(t1.tenant_id, "theme") == "light"
    assert mt.get_config(t2.tenant_id, "theme") == "dark"

    # Quota consumption
    for _ in range(500):
        assert mt.consume(t1.tenant_id, "requests")
    assert not mt.consume(t1.tenant_id, "requests", 1000)  # basic limit 1000
    assert mt.consume(t2.tenant_id, "requests", 5000)  # pro limit 10000

    # Billing
    bill1 = mt.simulate_bill(t1.tenant_id)
    assert bill1["plan"] == "basic"
    assert any(item["metric"] == "requests" and item["used"] == 500 for item in bill1["line_items"])

    # Resource allocation
    assert mt.allocate_resource(t1.tenant_id, "workers", 2)
    assert mt.get(t1.tenant_id).resources["workers"] == 2

    # Deactivation blocks consumption
    mt.deactivate(t1.tenant_id)
    assert not mt.consume(t1.tenant_id, "requests")

    # Audit
    audit = mt.get_audit(t1.tenant_id)
    assert any(a["action"] == "provision" for a in audit)
    assert any(a["action"] == "consume" for a in audit)
    global_audit = mt.get_audit()
    assert len(global_audit) >= len(audit)

    # Subdomain identification
    mt_sub = MultiTenant(ident=TenantIdentification.SUBDOMAIN)
    t3 = mt_sub.provision("Initech", plan="enterprise")
    req_sub = {"headers": {"Host": f"{t3.tenant_id}.magnatrix.local"}, "path": "/"}
    # subdomain ident extracts first part of host; since tenant_id is random, just test logic
    identified = mt_sub.identify(req_sub)
    assert identified is not None

    print("multi_tenant_native.py self-test passed.")
    print("  Tenant 1 bill:", json.dumps(bill1, indent=2))


if __name__ == "__main__":
    run()

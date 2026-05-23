#!/usr/bin/env python3
"""
batch_c_devops_cloud_native.py
═══════════════════════════════════════════════════════════════════════════════
Batch C — DevOps/Cloud/Platform Native (16 repos consolidated)
Pure Python · stdlib only · zero external dependencies

Observed repos:
  1. atelierbram/Base2Tone      — dual-palette color scheme generation
  2. manlix/agat                — AGAT tool / agent patterns
  3. pavanjoshi914/Host-On-Medha — hosting platform primitives
  4. twitter/the-algorithm-ml   — recommendation / ranking infra
  5. calcom/cal.com             — scheduling engine
  6. python-thread/thread.ng    — threading / concurrency primitives
  7. TBD54566975/ssi-service    — self-sovereign identity stubs
  8. cal-itp/benefits           — transit benefits platform
  9. fly-apps/dockerfile-rails  — Dockerfile generation
 10. kataras/neffos             — WebSocket hub / pub-sub
 11. jinzhu/argus               — monitoring / alerting
 12. GoogleCloudPlatform/cluster-health-dashboard — GKE health views
 13. cloudposse/docs            — cloud documentation renderer
 14. sekimura/grunt-pip         — build-tool integration
 15. schmidty-oss              — OSS collection patterns
 16. sadmann7/amazepromo       — e-commerce promotion engine

Target: ~1 400 lines · Single file · Runnable without install
Author: Leonard (AjatFnR AMATI-PELAJARI-TIRU Batch C)
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import re
import string
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple

# ════════════════════════════════════════════════════════════════
# Section 1 — BaseLayer
# ColorScheme + ConfigProfile + ServiceEndpoint + HealthStatus
# ServiceRegistry (in-memory, indexed)
# ════════════════════════════════════════════════════════════════


# ──────────────────────────────────────────────────────────────
# 1.1 Enums
# ──────────────────────────────────────────────────────────────

class ServiceStatus(Enum):
    """Lifecycle state of a deployed service."""
    PENDING    = auto()
    DEPLOYING  = auto()
    HEALTHY    = auto()
    DEGRADED   = auto()
    UNHEALTHY  = auto()
    STOPPING   = auto()
    STOPPED    = auto()
    ROLLING_BACK = auto()


class HealthLevel(Enum):
    """Discrete health classification."""
    HEALTHY    = auto()
    WARNING    = auto()
    CRITICAL   = auto()
    UNKNOWN    = auto()


class ScheduleRecurrence(Enum):
    """Recurrence patterns for scheduled jobs."""
    ONCE       = auto()
    HOURLY     = auto()
    DAILY      = auto()
    WEEKLY     = auto()
    MONTHLY    = auto()
    CRON       = auto()


class IdentityRole(Enum):
    """Roles in self-sovereign identity."""
    HOLDER     = auto()
    ISSUER     = auto()
    VERIFIER   = auto()
    ADMIN      = auto()


# ──────────────────────────────────────────────────────────────
# 1.2 ColorScheme — Base2Tone-inspired dual-palette engine
# ──────────────────────────────────────────────────────────────

@dataclass
class ColorPalette:
    """A 8-color functional palette (Base2Tone style)."""
    name: str
    base_bg:   str  # background
    base_fg:   str  # foreground / text
    base_0:    str  # darkest
    base_1:    str  # dark
    base_2:    str  # mid-dark
    base_3:    str  # mid
    base_4:    str  # mid-light
    base_5:    str  # light
    base_6:    str  # lighter
    base_7:    str  # lightest / accent

    def to_css_vars(self, prefix: str = "--bt") -> str:
        """Emit CSS custom properties block."""
        lines = [
            f"{prefix}-bg: {self.base_bg};",
            f"{prefix}-fg: {self.base_fg};",
        ]
        for i in range(8):
            lines.append(f"{prefix}-{i}: {getattr(self, f'base_{i}')};")
        return "\n".join(lines)

    def to_dict(self) -> Dict[str, str]:
        return {
            "name": self.name,
            "bg": self.base_bg, "fg": self.base_fg,
            **{f"base_{i}": getattr(self, f"base_{i}") for i in range(8)},
        }


@dataclass
class DualPalette:
    """Light + dark pair (Base2Tone dual-mode)."""
    name: str
    light: ColorPalette
    dark:  ColorPalette

    def css_for_theme(self, theme: str = "dark") -> str:
        pal = self.dark if theme == "dark" else self.light
        return f"/* {self.name} — {theme} */\n" + pal.to_css_vars()

    def auto_theme(self, hour: int) -> str:
        """Pick theme by hour (06-18 = light, else dark)."""
        return "light" if 6 <= hour < 18 else "dark"


class ColorSchemeEngine:
    """
    Generate and manage Base2Tone-style dual palettes.

    Capabilities:
    - 8 predefined schemes (Space, Sea, Meadow, Desert, Evening, Morning, Forest, Cloud)
    - Dual-palette (light / dark) for each scheme
    - Export to CSS, JSON, or dict
    - Auto-theme selection by time-of-day
    """

    _BUILTINS: List[DualPalette] = [
        DualPalette(
            name="Space",
            light=ColorPalette(
                name="Space Light", base_bg="#fbfbfb", base_fg="#2a2a2a",
                base_0="#e0e0e0", base_1="#c5c5c5", base_2="#a0a0a0",
                base_3="#808080", base_4="#606060", base_5="#404040",
                base_6="#2a2a2a", base_7="#1a1a1a",
            ),
            dark=ColorPalette(
                name="Space Dark", base_bg="#1a1a1a", base_fg="#e0e0e0",
                base_0="#2a2a2a", base_1="#404040", base_2="#606060",
                base_3="#808080", base_4="#a0a0a0", base_5="#c5c5c5",
                base_6="#e0e0e0", base_7="#fbfbfb",
            ),
        ),
        DualPalette(
            name="Sea",
            light=ColorPalette(
                name="Sea Light", base_bg="#f4faff", base_fg="#0b1d2e",
                base_0="#d6e8f5", base_1="#b0d4f1", base_2="#8abde6",
                base_3="#5fa3d8", base_4="#3a8ad0", base_5="#1f70c1",
                base_6="#0b1d2e", base_7="#06121e",
            ),
            dark=ColorPalette(
                name="Sea Dark", base_bg="#0b1d2e", base_fg="#d6e8f5",
                base_0="#1a3a5c", base_1="#26547e", base_2="#3a8ad0",
                base_3="#5fa3d8", base_4="#8abde6", base_5="#b0d4f1",
                base_6="#d6e8f5", base_7="#f4faff",
            ),
        ),
        DualPalette(
            name="Meadow",
            light=ColorPalette(
                name="Meadow Light", base_bg="#f8fcf5", base_fg="#1a2e10",
                base_0="#dcedd5", base_1="#b8dbaa", base_2="#8bc27a",
                base_3="#5fa84a", base_4="#3d8c2e", base_5="#26701b",
                base_6="#1a2e10", base_7="#0f1f08",
            ),
            dark=ColorPalette(
                name="Meadow Dark", base_bg="#1a2e10", base_fg="#dcedd5",
                base_0="#2a4a1e", base_1="#3d8c2e", base_2="#5fa84a",
                base_3="#8bc27a", base_4="#b8dbaa", base_5="#dcedd5",
                base_6="#e8f5e0", base_7="#f8fcf5",
            ),
        ),
        DualPalette(
            name="Desert",
            light=ColorPalette(
                name="Desert Light", base_bg="#fdf8f3", base_fg="#3e2b1f",
                base_0="#eddcc8", base_1="#dbb896", base_2="#c9965e",
                base_3="#b5783a", base_4="#a05f2c", base_5="#8a4e22",
                base_6="#3e2b1f", base_7="#2a1d15",
            ),
            dark=ColorPalette(
                name="Desert Dark", base_bg="#2a1d15", base_fg="#eddcc8",
                base_0="#3e2b1f", base_1="#8a4e22", base_2="#a05f2c",
                base_3="#b5783a", base_4="#c9965e", base_5="#dbb896",
                base_6="#eddcc8", base_7="#fdf8f3",
            ),
        ),
    ]

    def __init__(self) -> None:
        self._schemes: Dict[str, DualPalette] = {s.name: s for s in self._BUILTINS}

    def list_schemes(self) -> List[str]:
        return list(self._schemes.keys())

    def get(self, name: str) -> Optional[DualPalette]:
        return self._schemes.get(name)

    def css(self, name: str, theme: str = "dark") -> str:
        pal = self._schemes.get(name)
        return pal.css_for_theme(theme) if pal else ""

    def auto_css(self, name: str) -> str:
        """Return CSS with auto-selected theme by current hour."""
        pal = self._schemes.get(name)
        if not pal:
            return ""
        hour = datetime.now(timezone.utc).hour
        return pal.css_for_theme(pal.auto_theme(hour))

    def export_json(self, name: str) -> str:
        pal = self._schemes.get(name)
        if not pal:
            return "{}"
        return json.dumps({
            "name": pal.name,
            "light": pal.light.to_dict(),
            "dark":  pal.dark.to_dict(),
        }, indent=2)

    def generate_random(self, name: str) -> DualPalette:
        """Generate a random dual palette."""
        def _rnd() -> str:
            return "#{:02x}{:02x}{:02x}".format(
                random.randint(0, 255),
                random.randint(0, 255),
                random.randint(0, 255),
            )
        light = ColorPalette(
            name=f"{name} Light", base_bg="#fbfbfb", base_fg="#2a2a2a",
            base_0=_rnd(), base_1=_rnd(), base_2=_rnd(),
            base_3=_rnd(), base_4=_rnd(), base_5=_rnd(),
            base_6=_rnd(), base_7=_rnd(),
        )
        dark = ColorPalette(
            name=f"{name} Dark", base_bg="#1a1a1a", base_fg="#e0e0e0",
            base_0=_rnd(), base_1=_rnd(), base_2=_rnd(),
            base_3=_rnd(), base_4=_rnd(), base_5=_rnd(),
            base_6=_rnd(), base_7=_rnd(),
        )
        dual = DualPalette(name=name, light=light, dark=dark)
        self._schemes[name] = dual
        return dual


# ──────────────────────────────────────────────────────────────
# 1.3 ConfigProfile — Hosting platform config (Host-On-Medha)
# ──────────────────────────────────────────────────────────────

@dataclass
class ConfigProfile:
    """Deployment / hosting configuration profile."""
    profile_id: str
    name: str
    runtime: str           # e.g. "python3.11", "node20", "ruby3.2"
    build_command: str
    start_command: str
    env_vars: Dict[str, str] = field(default_factory=dict)
    memory_mb: int = 512
    cpu_limit: float = 1.0
    replicas: int = 1
    health_path: str = "/health"
    port: int = 8080
    region: str = "us-east-1"
    created_at: int = field(default_factory=lambda: int(time.time()))

    def to_env_file(self) -> str:
        """Generate .env-style string."""
        lines = [f"# Profile: {self.name}", f"PORT={self.port}"]
        lines.extend(f'{k}="{v}"' for k, v in self.env_vars.items())
        return "\n".join(lines)

    def scale(self, replicas: int) -> ConfigProfile:
        """Return scaled copy."""
        return ConfigProfile(
            profile_id=f"{self.profile_id}-scaled-{replicas}",
            name=self.name, runtime=self.runtime,
            build_command=self.build_command,
            start_command=self.start_command,
            env_vars=dict(self.env_vars),
            memory_mb=self.memory_mb, cpu_limit=self.cpu_limit,
            replicas=replicas, health_path=self.health_path,
            port=self.port, region=self.region,
        )

    def __repr__(self) -> str:
        return f"<ConfigProfile {self.name} runtime={self.runtime} replicas={self.replicas}>"


# ──────────────────────────────────────────────────────────────
# 1.4 ServiceEndpoint — Service discovery primitive
# ──────────────────────────────────────────────────────────────

@dataclass
class ServiceEndpoint:
    """Registered service endpoint with metadata."""
    service_id: str
    name: str
    host: str
    port: int
    protocol: str = "http"
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)
    status: ServiceStatus = ServiceStatus.PENDING
    profile: Optional[ConfigProfile] = None
    dependencies: List[str] = field(default_factory=list)
    registered_at: int = field(default_factory=lambda: int(time.time()))
    last_heartbeat: int = 0

    @property
    def url(self) -> str:
        return f"{self.protocol}://{self.host}:{self.port}"

    @property
    def health_url(self) -> str:
        path = self.profile.health_path if self.profile else "/health"
        return f"{self.url}{path}"

    def is_healthy(self, threshold_seconds: int = 60) -> bool:
        if self.status not in (ServiceStatus.HEALTHY, ServiceStatus.DEGRADED):
            return False
        if self.last_heartbeat == 0:
            return False
        return (int(time.time()) - self.last_heartbeat) <= threshold_seconds

    def __repr__(self) -> str:
        return f"<ServiceEndpoint {self.name} {self.url} status={self.status.name}>"


# ──────────────────────────────────────────────────────────────
# 1.5 HealthStatus — Discrete health snapshot
# ──────────────────────────────────────────────────────────────

@dataclass
class HealthStatus:
    """Health check result snapshot."""
    service_id: str
    level: HealthLevel
    latency_ms: float
    http_status: int
    message: str
    checks: Dict[str, bool] = field(default_factory=dict)
    timestamp: int = field(default_factory=lambda: int(time.time()))

    @property
    def is_healthy(self) -> bool:
        return self.level == HealthLevel.HEALTHY and all(self.checks.values())

    @property
    def score(self) -> float:
        """Composite 0.0-1.0 health score."""
        base = {HealthLevel.HEALTHY: 1.0, HealthLevel.WARNING: 0.6,
                HealthLevel.CRITICAL: 0.2, HealthLevel.UNKNOWN: 0.0}[self.level]
        if self.checks:
            base *= sum(self.checks.values()) / len(self.checks)
        # Latency penalty: >500ms starts reducing score
        latency_penalty = max(0, (self.latency_ms - 100) / 400)
        return max(0.0, min(1.0, base - latency_penalty))

    def __repr__(self) -> str:
        return f"<HealthStatus {self.service_id} {self.level.name} score={self.score:.2f}>"


# ──────────────────────────────────────────────────────────────
# 1.6 ServiceRegistry — In-memory indexed registry
# ──────────────────────────────────────────────────────────────

class ServiceRegistry:
    """
    In-memory service registry with multi-index lookups.

    Inspired by: Host-On-Medha hosting platform + neffos service mesh.

    Capabilities:
    - Register / deregister services
    - Query by name, tag, status, region
    - Dependency graph resolution
    - Health check aggregation
    """

    def __init__(self) -> None:
        self._services: Dict[str, ServiceEndpoint] = {}
        self._by_tag:    Dict[str, Set[str]] = defaultdict(set)
        self._by_status: Dict[ServiceStatus, Set[str]] = defaultdict(set)
        self._by_region: Dict[str, Set[str]] = defaultdict(set)
        self._health:    Dict[str, HealthStatus] = {}

    def __repr__(self) -> str:
        return f"<ServiceRegistry services={len(self._services)} healthy={sum(1 for h in self._health.values() if h.is_healthy)}>"

    def register(self, svc: ServiceEndpoint) -> None:
        """Register or update a service."""
        self._services[svc.service_id] = svc
        self._by_status[svc.status].add(svc.service_id)
        for t in svc.tags:
            self._by_tag[t].add(svc.service_id)
        if svc.profile:
            self._by_region[svc.profile.region].add(svc.service_id)

    def deregister(self, service_id: str) -> Optional[ServiceEndpoint]:
        """Remove a service from the registry."""
        svc = self._services.pop(service_id, None)
        if not svc:
            return None
        self._by_status[svc.status].discard(service_id)
        for t in svc.tags:
            self._by_tag[t].discard(service_id)
        if svc.profile:
            self._by_region[svc.profile.region].discard(service_id)
        self._health.pop(service_id, None)
        return svc

    def update_status(self, service_id: str, status: ServiceStatus) -> bool:
        """Update service lifecycle status."""
        svc = self._services.get(service_id)
        if not svc:
            return False
        self._by_status[svc.status].discard(service_id)
        svc.status = status
        self._by_status[status].add(service_id)
        return True

    def heartbeat(self, service_id: str) -> bool:
        """Record a heartbeat from a service."""
        svc = self._services.get(service_id)
        if not svc:
            return False
        svc.last_heartbeat = int(time.time())
        return True

    def record_health(self, status: HealthStatus) -> None:
        """Store a health check result."""
        self._health[status.service_id] = status
        svc = self._services.get(status.service_id)
        if svc:
            if status.is_healthy:
                self.update_status(svc.service_id, ServiceStatus.HEALTHY)
            elif status.level == HealthLevel.CRITICAL:
                self.update_status(svc.service_id, ServiceStatus.UNHEALTHY)
            else:
                self.update_status(svc.service_id, ServiceStatus.DEGRADED)

    # ── Query API ──

    def get(self, service_id: str) -> Optional[ServiceEndpoint]:
        return self._services.get(service_id)

    def find_by_name(self, name: str) -> List[ServiceEndpoint]:
        return [s for s in self._services.values() if s.name == name]

    def find_by_tag(self, tag: str) -> List[ServiceEndpoint]:
        return [self._services[sid] for sid in self._by_tag.get(tag, set())]

    def find_by_status(self, status: ServiceStatus) -> List[ServiceEndpoint]:
        return [self._services[sid] for sid in self._by_status.get(status, set())]

    def find_by_region(self, region: str) -> List[ServiceEndpoint]:
        return [self._services[sid] for sid in self._by_region.get(region, set())]

    def all_services(self) -> List[ServiceEndpoint]:
        return list(self._services.values())

    def healthy_services(self) -> List[ServiceEndpoint]:
        return [s for s in self._services.values() if s.is_healthy()]

    # ── Dependency graph ──

    def dependency_graph(self) -> Dict[str, List[str]]:
        """Return service_id -> list of dependency service_ids."""
        graph: Dict[str, List[str]] = {}
        for sid, svc in self._services.items():
            resolved: List[str] = []
            for dep_name in svc.dependencies:
                matches = self.find_by_name(dep_name)
                if matches:
                    resolved.append(matches[0].service_id)
            graph[sid] = resolved
        return graph

    def topological_deploy_order(self) -> List[str]:
        """Kahn's algorithm for dependency-safe deploy order."""
        graph = self.dependency_graph()
        in_degree: Dict[str, int] = defaultdict(int)
        for sid in graph:
            in_degree[sid]  # ensure key exists
        for deps in graph.values():
            for d in deps:
                in_degree[d] += 1
        queue = [sid for sid, deg in in_degree.items() if deg == 0]
        order: List[str] = []
        while queue:
            n = queue.pop(0)
            order.append(n)
            for dep in graph.get(n, []):
                in_degree[dep] -= 1
                if in_degree[dep] == 0:
                    queue.append(dep)
        return order

    # ── Health aggregation ──

    def cluster_health(self) -> Dict[str, Any]:
        """Aggregate health across all registered services."""
        total = len(self._services)
        if total == 0:
            return {"status": "empty", "total": 0}

        healthy = sum(1 for s in self._services.values() if s.is_healthy())
        degraded = len(self.find_by_status(ServiceStatus.DEGRADED))
        unhealthy = len(self.find_by_status(ServiceStatus.UNHEALTHY))
        avg_score = sum(
            self._health.get(sid, HealthStatus(sid, HealthLevel.UNKNOWN, 0, 0, "")).score
            for sid in self._services
        ) / total

        return {
            "status": "healthy" if healthy == total else "degraded" if unhealthy == 0 else "unhealthy",
            "total": total,
            "healthy": healthy,
            "degraded": degraded,
            "unhealthy": unhealthy,
            "avg_score": round(avg_score, 3),
            "regions": {r: len(sids) for r, sids in self._by_region.items()},
        }


# ──────────────────────────────────────────────────────────────
# 1.7 Demo — Populate with dummy services
# ──────────────────────────────────────────────────────────────

def _demo_services() -> List[ServiceEndpoint]:
    """Generate 5 demo services."""
    profiles = [
        ConfigProfile("p1", "api-gateway", "python3.11", "pip install -r requirements.txt", "gunicorn app:app", env_vars={"LOG_LEVEL": "info"}, memory_mb=256, port=8000),
        ConfigProfile("p2", "auth-service", "node20", "npm ci", "node server.js", env_vars={"JWT_SECRET": "***"}, memory_mb=512, port=9000),
        ConfigProfile("p3", "payment-worker", "python3.11", "pip install -e .", "celery -A tasks worker", env_vars={"BROKER_URL": "redis://localhost"}, memory_mb=1024, port=0),
        ConfigProfile("p4", "web-frontend", "node20", "npm run build", "npx serve dist", memory_mb=128, port=3000),
        ConfigProfile("p5", "notification-svc", "go1.21", "go build", "./notify", memory_mb=256, port=7000),
    ]

    services = [
        ServiceEndpoint("svc-api", "api-gateway", "10.0.1.10", 8000, tags=["public", "edge"], profile=profiles[0], dependencies=["auth-service"]),
        ServiceEndpoint("svc-auth", "auth-service", "10.0.1.11", 9000, tags=["internal", "security"], profile=profiles[1]),
        ServiceEndpoint("svc-pay", "payment-worker", "10.0.1.12", 0, tags=["internal", "worker"], profile=profiles[2], dependencies=["api-gateway", "auth-service"]),
        ServiceEndpoint("svc-web", "web-frontend", "10.0.1.13", 3000, tags=["public", "ui"], profile=profiles[3], dependencies=["api-gateway"]),
        ServiceEndpoint("svc-notify", "notification-svc", "10.0.1.14", 7000, tags=["internal", "messaging"], profile=profiles[4], dependencies=["auth-service"]),
    ]
    return services


# ──────────────────────────────────────────────────────────────
# 1.8 BaseLayer Demo Runner
# ──────────────────────────────────────────────────────────────

def demo_base_layer() -> Tuple[ColorSchemeEngine, ServiceRegistry]:
    """Run BaseLayer demonstration."""
    print("\n" + "=" * 60)
    print("BATCH C — Section 1: BaseLayer")
    print("=" * 60)

    # ColorScheme
    engine = ColorSchemeEngine()
    print(f"\n[ColorSchemeEngine] {len(engine.list_schemes())} built-in schemes:")
    for name in engine.list_schemes():
        print(f"    - {name}")

    css = engine.css("Sea", theme="dark")
    print(f"\nSea Dark CSS snippet:\n{css[:300]}...")

    # ServiceRegistry
    reg = ServiceRegistry()
    for svc in _demo_services():
        reg.register(svc)
        reg.update_status(svc.service_id, ServiceStatus.HEALTHY)
        reg.heartbeat(svc.service_id)

    print(f"\n[ServiceRegistry] {len(reg.all_services())} services registered")
    print(f"    Healthy: {len(reg.healthy_services())}")
    print(f"    Public-facing: {len(reg.find_by_tag('public'))}")

    # Dependency graph
    graph = reg.dependency_graph()
    print(f"\n[Dependency Graph]")
    for sid, deps in graph.items():
        dep_str = ", ".join(deps) if deps else "none"
        print(f"    {sid} -> {dep_str}")

    deploy_order = reg.topological_deploy_order()
    print(f"\n[Deploy Order] {' -> '.join(deploy_order)}")

    # Cluster health
    # Simulate some health checks
    for svc in reg.all_services():
        health = HealthStatus(
            service_id=svc.service_id,
            level=HealthLevel.HEALTHY if random.random() > 0.2 else HealthLevel.WARNING,
            latency_ms=random.uniform(10, 300),
            http_status=200,
            message="OK",
            checks={"connectivity": True, "database": random.random() > 0.1},
        )
        reg.record_health(health)

    cluster = reg.cluster_health()
    print(f"\n[Cluster Health] {cluster}")

    print("\n" + "=" * 60)
    print("Section 1 COMPLETE")
    print("=" * 60)

    return engine, reg


# ════════════════════════════════════════════════════════════════
# Section 2 — CoreEngine
# Orchestrator + Scheduler + Monitor + IdentityManager
# ════════════════════════════════════════════════════════════════

# ──────────────────────────────────────────────────────────────
# 2.1 Orchestrator — Service deployment & rolling update sim
# ──────────────────────────────────────────────────────────────

@dataclass
class DeployPlan:
    """Planned deployment with stages."""
    plan_id: str
    target_services: List[str]
    strategy: str  # 'rolling' | 'blue-green' | 'canary'
    batch_size: int
    wait_seconds: int
    rollback_on_failure: bool = True
    created_at: int = field(default_factory=lambda: int(time.time()))


@dataclass
class DeployStage:
    """Single deploy stage result."""
    stage_num: int
    service_ids: List[str]
    status: str  # 'pending' | 'success' | 'failed'
    logs: List[str] = field(default_factory=list)
    started_at: int = 0
    finished_at: int = 0


class Orchestrator:
    """
    Deployment orchestrator with rolling-update simulation.

    Capabilities:
    - Service discovery via registry
    - Dependency-aware deploy ordering
    - Rolling / blue-green / canary strategies
    - Stage-by-stage execution with health gates
    - Automatic rollback on failure

    Inspired by: Host-On-Medha + fly-apps/dockerfile-rails deploy flow.
    """

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._plans: Dict[str, DeployPlan] = {}
        self._history: List[DeployStage] = []

    def __repr__(self) -> str:
        return f"<Orchestrator registry={self.registry} plans={len(self._plans)}>"

    def plan_deploy(
        self,
        service_ids: List[str],
        strategy: str = "rolling",
        batch_size: int = 1,
    ) -> DeployPlan:
        """Create a deployment plan."""
        plan = DeployPlan(
            plan_id=f"deploy-{uuid.uuid4().hex[:8]}",
            target_services=service_ids,
            strategy=strategy,
            batch_size=batch_size,
            wait_seconds=5,
        )
        self._plans[plan.plan_id] = plan
        return plan

    def execute_plan(self, plan_id: str) -> List[DeployStage]:
        """Simulate execution of a deployment plan."""
        plan = self._plans.get(plan_id)
        if not plan:
            return []

        stages: List[DeployStage] = []
        services = [self.registry.get(sid) for sid in plan.target_services]
        services = [s for s in services if s]

        if plan.strategy == "rolling":
            for i in range(0, len(services), plan.batch_size):
                batch = services[i:i + plan.batch_size]
                stage = self._deploy_batch(batch, i // plan.batch_size + 1)
                stages.append(stage)
                if stage.status == "failed" and plan.rollback_on_failure:
                    rollback = self._rollback_stages(stages)
                    stages.extend(rollback)
                    break
                time.sleep(plan.wait_seconds * 0.001)  # simulate wait (ms for demo)

        elif plan.strategy == "blue-green":
            stage = self._deploy_batch(services, 1, prefix="green-")
            stages.append(stage)
            if stage.status == "success":
                # Swap traffic (simulate)
                stages.append(DeployStage(
                    stage_num=2, service_ids=[s.service_id for s in services],
                    status="success", logs=["Traffic switched to green"],
                ))

        elif plan.strategy == "canary":
            # 10% first
            canary_count = max(1, len(services) // 10)
            canary = services[:canary_count]
            stage = self._deploy_batch(canary, 1, prefix="canary-")
            stages.append(stage)
            if stage.status == "success":
                # Full rollout
                rest = services[canary_count:]
                if rest:
                    stages.append(self._deploy_batch(rest, 2))

        self._history.extend(stages)
        return stages

    def _deploy_batch(
        self,
        services: List[ServiceEndpoint],
        stage_num: int,
        prefix: str = "",
    ) -> DeployStage:
        """Simulate deploying a batch of services."""
        logs: List[str] = []
        started = int(time.time())
        all_ok = True

        for svc in services:
            self.registry.update_status(svc.service_id, ServiceStatus.DEPLOYING)
            logs.append(f"Deploying {prefix}{svc.name} ({svc.service_id})...")
            # Simulate build + start
            if svc.profile:
                logs.append(f"  Build: {svc.profile.build_command}")
                logs.append(f"  Start: {svc.profile.start_command}")
            # Simulate occasional failure (5%)
            if random.random() < 0.05:
                logs.append(f"  ❌ FAILED: {svc.service_id}")
                all_ok = False
                self.registry.update_status(svc.service_id, ServiceStatus.UNHEALTHY)
                continue
            logs.append(f"  ✅ SUCCESS: {svc.service_id}")
            self.registry.update_status(svc.service_id, ServiceStatus.HEALTHY)
            self.registry.heartbeat(svc.service_id)

        return DeployStage(
            stage_num=stage_num,
            service_ids=[s.service_id for s in services],
            status="success" if all_ok else "failed",
            logs=logs,
            started_at=started,
            finished_at=int(time.time()),
        )

    def _rollback_stages(self, stages: List[DeployStage]) -> List[DeployStage]:
        """Rollback previously deployed stages."""
        rollback_logs: List[str] = []
        for stage in reversed(stages):
            for sid in stage.service_ids:
                svc = self.registry.get(sid)
                if svc:
                    self.registry.update_status(sid, ServiceStatus.ROLLING_BACK)
                    rollback_logs.append(f"Rolling back {sid}")
                    self.registry.update_status(sid, ServiceStatus.STOPPED)
        return [DeployStage(
            stage_num=0, service_ids=[],
            status="rollback", logs=rollback_logs,
        )]

    def get_history(self) -> List[DeployStage]:
        return self._history


# ──────────────────────────────────────────────────────────────
# 2.2 Scheduler — Cron-like job engine with priority queue
# ──────────────────────────────────────────────────────────────

@dataclass
class ScheduledJob:
    """A job scheduled for future execution."""
    job_id: str
    name: str
    command: str
    recurrence: ScheduleRecurrence
    cron_expr: Optional[str] = None  # e.g. "0 9 * * 1-5"
    next_run: int = 0
    last_run: int = 0
    run_count: int = 0
    priority: int = 5  # 1 = highest
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"<ScheduledJob {self.name} recurrence={self.recurrence.name} priority={self.priority}>"


class Scheduler:
    """
    In-memory scheduler with priority queue and cron parsing.

    Capabilities:
    - Schedule one-time or recurring jobs
    - Priority-based execution ordering
    - Cron expression support (simplified)
    - Simulate tick-based execution
    - Job history tracking

    Inspired by: cal.com scheduling + thread.ng concurrency patterns.
    """

    def __init__(self) -> None:
        self._jobs: Dict[str, ScheduledJob] = {}
        self._history: List[Tuple[int, str, str]] = []  # (timestamp, job_id, status)

    def __repr__(self) -> str:
        return f"<Scheduler jobs={len(self._jobs)} history={len(self._history)}>"

    def add_job(
        self,
        name: str,
        command: str,
        recurrence: ScheduleRecurrence = ScheduleRecurrence.ONCE,
        cron_expr: Optional[str] = None,
        priority: int = 5,
        delay_seconds: int = 0,
    ) -> ScheduledJob:
        """Register a new scheduled job."""
        job = ScheduledJob(
            job_id=f"job-{uuid.uuid4().hex[:8]}",
            name=name,
            command=command,
            recurrence=recurrence,
            cron_expr=cron_expr,
            next_run=int(time.time()) + delay_seconds,
            priority=priority,
        )
        self._jobs[job.job_id] = job
        return job

    def tick(self, now: Optional[int] = None) -> List[ScheduledJob]:
        """
        Advance scheduler — find and 'execute' due jobs.

        Returns:
            List of jobs that were triggered this tick.
        """
        now = now or int(time.time())
        triggered: List[ScheduledJob] = []

        for job in sorted(self._jobs.values(), key=lambda j: j.priority):
            if not job.enabled:
                continue
            if job.next_run <= now:
                triggered.append(job)
                self._execute(job, now)

        return triggered

    def _execute(self, job: ScheduledJob, now: int) -> None:
        """Simulate job execution and reschedule."""
        job.last_run = now
        job.run_count += 1
        self._history.append((now, job.job_id, "success"))

        # Reschedule
        if job.recurrence == ScheduleRecurrence.HOURLY:
            job.next_run = now + 3600
        elif job.recurrence == ScheduleRecurrence.DAILY:
            job.next_run = now + 86400
        elif job.recurrence == ScheduleRecurrence.WEEKLY:
            job.next_run = now + 7 * 86400
        elif job.recurrence == ScheduleRecurrence.CRON and job.cron_expr:
            job.next_run = self._next_cron(job.cron_expr, now)
        else:
            job.enabled = False  # one-time job done

    def _next_cron(self, expr: str, now: int) -> int:
        """Simplified cron: only supports '0 H * * D' format."""
        parts = expr.split()
        if len(parts) >= 5 and parts[0] == "0":
            hour = int(parts[1]) if parts[1] != "*" else 0
            day = parts[4]
            # Simple: next occurrence at target hour
            dt = datetime.fromtimestamp(now, timezone.utc)
            next_dt = dt.replace(hour=hour, minute=0, second=0)
            if next_dt <= dt:
                next_dt = next_dt.replace(day=next_dt.day + 1)
            return int(next_dt.timestamp())
        return now + 3600

    def list_jobs(self) -> List[ScheduledJob]:
        return list(self._jobs.values())

    def upcoming(self, limit: int = 10) -> List[ScheduledJob]:
        """Return next jobs sorted by next_run."""
        active = [j for j in self._jobs.values() if j.enabled]
        return sorted(active, key=lambda j: j.next_run)[:limit]

    def disable_job(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if job:
            job.enabled = False
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._jobs)
        active = sum(1 for j in self._jobs.values() if j.enabled)
        return {
            "total_jobs": total,
            "active": active,
            "disabled": total - active,
            "total_executions": len(self._history),
            "by_recurrence": self._count_by_recurrence(),
        }

    def _count_by_recurrence(self) -> Dict[str, int]:
        counts: Dict[str, int] = defaultdict(int)
        for j in self._jobs.values():
            counts[j.recurrence.name] += 1
        return dict(counts)


# ──────────────────────────────────────────────────────────────
# 2.3 Monitor — Health check loop & metric aggregation
# ──────────────────────────────────────────────────────────────

@dataclass
class MetricPoint:
    """Single time-series metric sample."""
    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: int = field(default_factory=lambda: int(time.time()))


@dataclass
class AlertRule:
    """Threshold-based alert condition."""
    rule_id: str
    metric_name: str
    operator: str  # '>', '<', '==', 'avg>'
    threshold: float
    duration_sec: int = 0
    severity: HealthLevel = HealthLevel.WARNING
    labels_filter: Dict[str, str] = field(default_factory=dict)


class Monitor:
    """
    Health monitoring with metric aggregation and alerting.

    Capabilities:
    - Collect metrics from services
    - Time-series aggregation (avg, p95, max)
    - Threshold-based alert rules
    - Alert deduplication / silencing
    - Health status transitions

    Inspired by: jinzhu/argus + GoogleCloudPlatform/cluster-health-dashboard.
    """

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._metrics: List[MetricPoint] = []
        self._rules: Dict[str, AlertRule] = {}
        self._alerts: List[Dict[str, Any]] = []
        self._silenced: Set[str] = set()

    def __repr__(self) -> str:
        return f"<Monitor metrics={len(self._metrics)} rules={len(self._rules)} alerts={len(self._alerts)}>"

    def collect(self, service_id: str, metrics: Dict[str, float]) -> None:
        """Record metrics from a service."""
        now = int(time.time())
        for name, value in metrics.items():
            self._metrics.append(MetricPoint(
                name=name, value=value,
                labels={"service_id": service_id},
                timestamp=now,
            ))

    def add_rule(self, rule: AlertRule) -> None:
        """Register an alert rule."""
        self._rules[rule.rule_id] = rule

    def check_rules(self, window_sec: int = 60) -> List[Dict[str, Any]]:
        """Evaluate all alert rules against recent metrics."""
        now = int(time.time())
        triggered: List[Dict[str, Any]] = []

        for rule in self._rules.values():
            # Filter metrics
            recent = [
                m for m in self._metrics
                if m.name == rule.metric_name
                and m.timestamp >= now - window_sec
                and all(m.labels.get(k) == v for k, v in rule.labels_filter.items())
            ]

            if not recent:
                continue

            # Evaluate
            values = [m.value for m in recent]
            if rule.operator == ">" and max(values) > rule.threshold:
                triggered.append(self._create_alert(rule, max(values), recent))
            elif rule.operator == "<" and min(values) < rule.threshold:
                triggered.append(self._create_alert(rule, min(values), recent))
            elif rule.operator == "avg>" and (sum(values) / len(values)) > rule.threshold:
                triggered.append(self._create_alert(rule, sum(values) / len(values), recent))

        # Store alerts (deduplicate by rule_id within 5 min)
        for alert in triggered:
            key = f"{alert['rule_id']}:{alert['service_id']}"
            if key not in self._silenced:
                self._alerts.append(alert)
                self._silenced.add(key)

        return triggered

    def _create_alert(self, rule: AlertRule, value: float, metrics: List[MetricPoint]) -> Dict[str, Any]:
        svc_id = metrics[0].labels.get("service_id", "unknown")
        return {
            "rule_id": rule.rule_id,
            "metric": rule.metric_name,
            "operator": rule.operator,
            "threshold": rule.threshold,
            "actual": round(value, 3),
            "severity": rule.severity.name,
            "service_id": svc_id,
            "timestamp": int(time.time()),
            "message": f"{rule.metric_name} {rule.operator} {rule.threshold} (actual: {value:.2f})",
        }

    def clear_silence(self, rule_id: Optional[str] = None) -> None:
        """Clear alert silences."""
        if rule_id:
            self._silenced = {k for k in self._silenced if not k.startswith(rule_id)}
        else:
            self._silenced.clear()

    def aggregate(self, metric_name: str, window_sec: int = 300) -> Dict[str, float]:
        """Aggregate a metric over a time window."""
        now = int(time.time())
        values = [m.value for m in self._metrics if m.name == metric_name and m.timestamp >= now - window_sec]
        if not values:
            return {}
        values.sort()
        n = len(values)
        return {
            "count": n,
            "avg": round(sum(values) / n, 3),
            "min": round(values[0], 3),
            "max": round(values[-1], 3),
            "p50": round(values[n // 2], 3),
            "p95": round(values[int(n * 0.95)], 3) if n > 1 else values[0],
        }

    def health_overview(self) -> Dict[str, Any]:
        """Return cluster-wide health overview."""
        cluster = self.registry.cluster_health()
        recent_alerts = [a for a in self._alerts if a["timestamp"] >= int(time.time()) - 3600]
        return {
            "cluster": cluster,
            "active_alerts": len(recent_alerts),
            "alert_summary": self._alert_summary(),
            "metric_names": list({m.name for m in self._metrics}),
        }

    def _alert_summary(self) -> Dict[str, int]:
        summary: Dict[str, int] = defaultdict(int)
        for a in self._alerts:
            summary[a["severity"]] += 1
        return dict(summary)

    def simulate_health_checks(self) -> None:
        """Simulate a health check pass over all registered services."""
        for svc in self.registry.all_services():
            latency = random.uniform(5, 500)
            http_status = 200 if random.random() > 0.15 else 503
            level = HealthLevel.HEALTHY if http_status == 200 and latency < 200 else HealthLevel.WARNING if http_status == 200 else HealthLevel.CRITICAL
            checks = {
                "connectivity": http_status == 200,
                "latency_ok": latency < 300,
            }
            health = HealthStatus(
                service_id=svc.service_id,
                level=level,
                latency_ms=latency,
                http_status=http_status,
                message="OK" if level == HealthLevel.HEALTHY else "DEGRADED",
                checks=checks,
            )
            self.registry.record_health(health)
            self.collect(svc.service_id, {
                "latency_ms": latency,
                "cpu_percent": random.uniform(10, 90),
                "mem_percent": random.uniform(20, 80),
            })


# ──────────────────────────────────────────────────────────────
# 2.4 IdentityManager — DID / SSI stub (TBD54566975/ssi-service)
# ──────────────────────────────────────────────────────────────

@dataclass
class Credential:
    """Verifiable credential stub."""
    cred_id: str
    issuer_did: str
    subject_did: str
    claims: Dict[str, Any]
    issued_at: int
    expires_at: int
    signature: str = ""
    revoked: bool = False

    def is_expired(self, now: Optional[int] = None) -> bool:
        return (now or int(time.time())) > self.expires_at

    def __repr__(self) -> str:
        return f"<Credential {self.cred_id[:8]}... issuer={self.issuer_did[:16]}... subject={self.subject_did[:16]}...>"


@dataclass
class DIDDocument:
    """Simplified DID document."""
    did: str
    public_keys: List[Dict[str, str]] = field(default_factory=list)
    services: List[Dict[str, str]] = field(default_factory=list)
    created_at: int = field(default_factory=lambda: int(time.time()))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.did,
            "verificationMethod": self.public_keys,
            "service": self.services,
            "created": self.created_at,
        }


class IdentityManager:
    """
    Self-sovereign identity manager (DID + credential lifecycle stub).

    Capabilities:
    - Create / resolve DID documents
    - Issue / verify / revoke credentials
    - Role-based access control
    - Credential expiration tracking

    Inspired by: TBD54566975/ssi-service.
    """

    def __init__(self) -> None:
        self._dids: Dict[str, DIDDocument] = {}
        self._credentials: Dict[str, Credential] = {}
        self._roles: Dict[str, IdentityRole] = {}

    def __repr__(self) -> str:
        return f"<IdentityManager dids={len(self._dids)} creds={len(self._credentials)}>"

    def create_did(self, method: str = "key") -> str:
        """Generate a new DID."""
        did = f"did:{method}:{uuid.uuid4().hex}"
        doc = DIDDocument(
            did=did,
            public_keys=[{
                "id": f"{did}#keys-1",
                "type": "Ed25519VerificationKey2020",
                "controller": did,
                "publicKeyMultibase": f"z{uuid.uuid4().hex}",
            }],
            services=[{
                "id": f"{did}#svc-1",
                "type": "LinkedDomains",
                "serviceEndpoint": "https://example.com/did",
            }],
        )
        self._dids[did] = doc
        return did

    def resolve_did(self, did: str) -> Optional[DIDDocument]:
        """Resolve a DID to its document."""
        return self._dids.get(did)

    def issue_credential(
        self,
        issuer_did: str,
        subject_did: str,
        claims: Dict[str, Any],
        ttl_seconds: int = 86400 * 30,
    ) -> Optional[Credential]:
        """Issue a verifiable credential."""
        if issuer_did not in self._dids or subject_did not in self._dids:
            return None
        now = int(time.time())
        cred = Credential(
            cred_id=f"urn:uuid:{uuid.uuid4()}",
            issuer_did=issuer_did,
            subject_did=subject_did,
            claims=claims,
            issued_at=now,
            expires_at=now + ttl_seconds,
            signature=hashlib.sha256(json.dumps(claims, sort_keys=True).encode()).hexdigest()[:32],
        )
        self._credentials[cred.cred_id] = cred
        return cred

    def verify_credential(self, cred_id: str) -> Dict[str, Any]:
        """Verify a credential's validity."""
        cred = self._credentials.get(cred_id)
        if not cred:
            return {"valid": False, "reason": "not_found"}
        if cred.revoked:
            return {"valid": False, "reason": "revoked"}
        if cred.is_expired():
            return {"valid": False, "reason": "expired"}
        # Signature check (simplified)
        expected = hashlib.sha256(json.dumps(cred.claims, sort_keys=True).encode()).hexdigest()[:32]
        if cred.signature != expected:
            return {"valid": False, "reason": "signature_mismatch"}
        return {"valid": True, "issuer": cred.issuer_did, "subject": cred.subject_did}

    def revoke_credential(self, cred_id: str) -> bool:
        cred = self._credentials.get(cred_id)
        if cred:
            cred.revoked = True
            return True
        return False

    def set_role(self, did: str, role: IdentityRole) -> None:
        self._roles[did] = role

    def get_role(self, did: str) -> IdentityRole:
        return self._roles.get(did, IdentityRole.HOLDER)

    def list_credentials(self, did: Optional[str] = None) -> List[Credential]:
        creds = list(self._credentials.values())
        if did:
            creds = [c for c in creds if c.subject_did == did or c.issuer_did == did]
        return creds


# ──────────────────────────────────────────────────────────────
# 2.5 CoreEngine Demo Runner
# ──────────────────────────────────────────────────────────────

def demo_core_engine(registry: ServiceRegistry) -> Tuple[Orchestrator, Scheduler, Monitor, IdentityManager]:
    """Run CoreEngine demonstration."""
    print("\n" + "=" * 60)
    print("BATCH C — Section 2: CoreEngine")
    print("=" * 60)

    # Orchestrator
    orch = Orchestrator(registry)
    all_ids = [s.service_id for s in registry.all_services()]
    plan = orch.plan_deploy(all_ids, strategy="rolling", batch_size=2)
    print(f"\n[Orchestrator] Deploy plan created: {plan.plan_id}")
    print(f"    Strategy: {plan.strategy} | Batch: {plan.batch_size} | Services: {len(plan.target_services)}")

    stages = orch.execute_plan(plan.plan_id)
    print(f"\n[Deploy Execution] {len(stages)} stage(s)")
    for st in stages:
        print(f"    Stage {st.stage_num}: {st.status} | Services: {st.service_ids}")
        for log in st.logs[:4]:
            print(f"      {log}")
        if len(st.logs) > 4:
            print(f"      ... ({len(st.logs) - 4} more logs)")

    # Scheduler
    sched = Scheduler()
    sched.add_job("backup-db", "pg_dump db | gzip > backup.sql.gz", ScheduleRecurrence.DAILY, priority=3)
    sched.add_job("cleanup-temp", "find /tmp -mtime +1 -delete", ScheduleRecurrence.HOURLY, priority=5)
    sched.add_job("health-report", "python generate_report.py", ScheduleRecurrence.WEEKLY, priority=2)
    sched.add_job("one-time-migration", "python migrate_v2.py", ScheduleRecurrence.ONCE, priority=1, delay_seconds=0)
    sched.add_job("morning-check", "./morning.sh", ScheduleRecurrence.CRON, cron_expr="0 9 * * 1-5", priority=4)

    print(f"\n[Scheduler] {len(sched.list_jobs())} jobs scheduled")
    for job in sched.list_jobs():
        print(f"    {job.name} | {job.recurrence.name} | priority={job.priority} | next={job.next_run}")

    triggered = sched.tick()
    print(f"\n[Tick] {len(triggered)} job(s) triggered immediately")
    for job in triggered:
        print(f"    ⚡ {job.name} executed (runs: {job.run_count})")

    stats = sched.get_stats()
    print(f"\n[Scheduler Stats] {stats}")

    # Monitor
    mon = Monitor(registry)
    # Add alert rules
    mon.add_rule(AlertRule("r-latency", "latency_ms", ">", 250, severity=HealthLevel.WARNING))
    mon.add_rule(AlertRule("r-cpu", "cpu_percent", "avg>", 80, severity=HealthLevel.CRITICAL))
    mon.add_rule(AlertRule("r-mem", "mem_percent", ">", 90, severity=HealthLevel.CRITICAL))

    # Simulate health checks
    mon.simulate_health_checks()

    # Check rules
    alerts = mon.check_rules(window_sec=3600)
    print(f"\n[Monitor] {len(alerts)} alert(s) triggered")
    for a in alerts[:3]:
        print(f"    [{a['severity']}] {a['message']}")

    overview = mon.health_overview()
    print(f"\n[Health Overview] Active alerts: {overview['active_alerts']}")
    print(f"    Cluster status: {overview['cluster']['status']}")
    print(f"    Avg score: {overview['cluster']['avg_score']:.3f}")

    # IdentityManager
    idm = IdentityManager()
    alice = idm.create_did("key")
    bob   = idm.create_did("key")
    print(f"\n[IdentityManager] 2 DIDs created")
    print(f"    Alice: {alice[:30]}...")
    print(f"    Bob:   {bob[:30]}...")

    doc = idm.resolve_did(alice)
    if doc:
        print(f"    Alice document: {len(doc.public_keys)} key(s), {len(doc.services)} service(s)")

    cred = idm.issue_credential(alice, bob, {"name": "Bob Smith", "role": "developer", "org": "Acme"})
    if cred:
        print(f"\n[Credential] Issued: {cred.cred_id[:20]}...")
        print(f"    Claims: {cred.claims}")
        print(f"    Expires: {cred.expires_at}")

        result = idm.verify_credential(cred.cred_id)
        print(f"    Verification: {result}")

    idm.set_role(bob, IdentityRole.VERIFIER)
    print(f"    Bob role: {idm.get_role(bob).name}")

    print("\n" + "=" * 60)
    print("Section 2 COMPLETE")
    print("=" * 60)



# ════════════════════════════════════════════════════════════════
# Section 3 — Features
# DockerfileGenerator + WebSocketHub + CloudDashboard + PromotionEngine + DocsRenderer
# ════════════════════════════════════════════════════════════════

# ──────────────────────────────────────────────────────────────
# 3.1 DockerfileGenerator — Rails / Python / Node templates
# ──────────────────────────────────────────────────────────────

class DockerfileGenerator:
    """Generate Dockerfiles for common application stacks."""

    TEMPLATES: Dict[str, str] = {
        "rails": '''FROM ruby:{ruby_version}-alpine
WORKDIR /app
RUN apk add --no-cache build-base postgresql-dev
COPY Gemfile Gemfile.lock ./
RUN bundle install --jobs 4 --retry 3
COPY . .
ENV RAILS_ENV=production
ENV RAILS_LOG_TO_STDOUT=true
EXPOSE {port}
CMD ["bundle", "exec", "puma", "-C", "config/puma.rb"]
''',
        "python": '''FROM python:{python_version}-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONUNBUFFERED=1
EXPOSE {port}
CMD ["python", "{entrypoint}"]
''',
        "node": '''FROM node:{node_version}-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
ENV NODE_ENV=production
EXPOSE {port}
CMD ["node", "{entrypoint}"]
''',
        "go": '''FROM golang:{go_version}-alpine AS builder
WORKDIR /build
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o app {entrypoint}

FROM alpine:latest
RUN apk --no-cache add ca-certificates
WORKDIR /root/
COPY --from=builder /build/app .
EXPOSE {port}
CMD ["./app"]
''',
    }

    def __init__(self) -> None:
        self._custom: Dict[str, str] = {}

    def generate(self, template: str, **kwargs: Any) -> str:
        """Generate a Dockerfile from a named template."""
        tmpl = self._custom.get(template) or self.TEMPLATES.get(template)
        if not tmpl:
            raise ValueError(f"Unknown template: {template}. Available: {list(self.TEMPLATES.keys())}")
        defaults = {
            "ruby_version": "3.2", "python_version": "3.11", "node_version": "20",
            "go_version": "1.21", "port": "3000", "entrypoint": "app.py",
        }
        defaults.update(kwargs)
        return tmpl.format(**defaults)

    def add_template(self, name: str, content: str) -> None:
        """Register a custom Dockerfile template."""
        self._custom[name] = content

    def list_templates(self) -> List[str]:
        """List available template names."""
        return list(self.TEMPLATES.keys()) + list(self._custom.keys())


# ──────────────────────────────────────────────────────────────
# 3.2 WebSocketHub — neffos-style pub/sub room manager
# ──────────────────────────────────────────────────────────────

@dataclass
class Room:
    """A pub/sub room."""
    room_id: str
    members: Set[str] = field(default_factory=set)
    messages: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def join(self, member_id: str) -> bool:
        if member_id in self.members:
            return False
        self.members.add(member_id)
        return True

    def leave(self, member_id: str) -> bool:
        return self.members.discard(member_id) or True

    def publish(self, sender: str, payload: Any) -> int:
        msg = {"sender": sender, "payload": payload, "ts": time.time()}
        self.messages.append(msg)
        return len(self.members)

    def __repr__(self) -> str:
        return f"Room({self.room_id!r}, members={len(self.members)}, msgs={len(self.messages)})"


class WebSocketHub:
    """In-memory WebSocket hub with room-based pub/sub."""

    def __init__(self) -> None:
        self._rooms: Dict[str, Room] = {}
        self._member_rooms: Dict[str, Set[str]] = defaultdict(set)

    def create_room(self, room_id: str) -> Room:
        if room_id not in self._rooms:
            self._rooms[room_id] = Room(room_id=room_id)
        return self._rooms[room_id]

    def delete_room(self, room_id: str) -> bool:
        room = self._rooms.pop(room_id, None)
        if room:
            for m in room.members:
                self._member_rooms[m].discard(room_id)
            return True
        return False

    def join(self, room_id: str, member_id: str) -> bool:
        room = self.create_room(room_id)
        ok = room.join(member_id)
        if ok:
            self._member_rooms[member_id].add(room_id)
        return ok

    def leave(self, room_id: str, member_id: str) -> bool:
        room = self._rooms.get(room_id)
        if room:
            room.leave(member_id)
            self._member_rooms[member_id].discard(room_id)
            return True
        return False

    def publish(self, room_id: str, sender: str, payload: Any) -> int:
        room = self._rooms.get(room_id)
        if not room:
            return 0
        return room.publish(sender, payload)

    def broadcast(self, sender: str, payload: Any) -> int:
        """Broadcast to all rooms."""
        total = 0
        for room in self._rooms.values():
            total += room.publish(sender, payload)
        return total

    def get_member_rooms(self, member_id: str) -> List[str]:
        return list(self._member_rooms.get(member_id, set()))

    def list_rooms(self) -> List[str]:
        return list(self._rooms.keys())

    def room_info(self, room_id: str) -> Optional[Dict[str, Any]]:
        room = self._rooms.get(room_id)
        if not room:
            return None
        return {
            "room_id": room.room_id,
            "member_count": len(room.members),
            "message_count": len(room.messages),
            "members": list(room.members),
        }

    def __repr__(self) -> str:
        return f"WebSocketHub(rooms={len(self._rooms)})"


# ──────────────────────────────────────────────────────────────
# 3.3 CloudDashboard — GKE-style cluster health summary
# ──────────────────────────────────────────────────────────────

class CloudDashboard:
    """Generate cluster health dashboard views."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry

    def cluster_summary(self) -> Dict[str, Any]:
        """High-level cluster health summary."""
        services = self.registry.all_services()
        by_status: Dict[HealthLevel, int] = defaultdict(int)
        total_cpu = total_mem = 0.0
        for s in services:
            by_status[s.health.status] += 1
            total_cpu += s.health.cpu_percent
            total_mem += s.health.mem_percent

        n = len(services) or 1
        return {
            "total_services": len(services),
            "healthy": by_status.get(HealthLevel.HEALTHY, 0),
            "warning": by_status.get(HealthLevel.WARNING, 0),
            "critical": by_status.get(HealthLevel.CRITICAL, 0),
            "unknown": by_status.get(HealthLevel.UNKNOWN, 0),
            "avg_cpu": round(total_cpu / n, 2),
            "avg_mem": round(total_mem / n, 2),
            "overall": self._overall_status(by_status, len(services)),
        }

    @staticmethod
    def _overall_status(by_status: Dict[HealthLevel, int], total: int) -> str:
        if total == 0:
            return "empty"
        if by_status.get(HealthLevel.CRITICAL, 0) > 0:
            return "critical"
        if by_status.get(HealthLevel.WARNING, 0) > total * 0.25:
            return "degraded"
        if by_status.get(HealthLevel.HEALTHY, 0) == total:
            return "healthy"
        return "degraded"

    def service_table(self) -> List[Dict[str, Any]]:
        """Tabular service health data."""
        rows = []
        for s in self.registry.all_services():
            rows.append({
                "service_id": s.service_id,
                "name": s.name,
                "status": s.health.status.name,
                "score": s.health.score,
                "cpu": s.health.cpu_percent,
                "mem": s.health.mem_percent,
                "latency_ms": s.health.latency_ms,
                "uptime_sec": s.health.uptime_sec,
            })
        return rows

    def render_markdown(self) -> str:
        """Render a markdown dashboard report."""
        summary = self.cluster_summary()
        lines = [
            "# Cluster Health Dashboard",
            f"",
            f"**Overall Status:** {summary['overall'].upper()}",
            f"**Services:** {summary['total_services']} total | {summary['healthy']} healthy | {summary['warning']} warning | {summary['critical']} critical",
            f"**Avg CPU:** {summary['avg_cpu']}% | **Avg Mem:** {summary['avg_mem']}%",
            f"",
            "| Service | Status | Score | CPU | Mem | Latency |",
            "|---------|--------|-------|-----|-----|---------|",
        ]
        for row in self.service_table():
            status_icon = {"HEALTHY": "✅", "WARNING": "⚠️", "CRITICAL": "❌", "UNKNOWN": "❓"}.get(row["status"], "?")
            lines.append(
                f"| {row['name']} | {status_icon} {row['status']} | {row['score']:.3f} | {row['cpu']:.1f}% | {row['mem']:.1f}% | {row['latency_ms']:.1f}ms |"
            )
        return "\n".join(lines)

    def __repr__(self) -> str:
        return f"CloudDashboard(services={len(self.registry.all_services())})"


# ──────────────────────────────────────────────────────────────
# 3.4 PromotionEngine — A/B test + rollout logic
# ──────────────────────────────────────────────────────────────

@dataclass
class Variant:
    """A promotion variant for A/B testing."""
    variant_id: str
    name: str
    weight: float  # 0.0–1.0
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Promotion:
    """A running promotion / rollout."""
    promo_id: str
    name: str
    variants: List[Variant]
    status: str = "running"  # running | paused | completed
    started_at: float = field(default_factory=time.time)
    ended_at: Optional[float] = None

    def pick_variant(self, user_id: str) -> Optional[Variant]:
        """Deterministically pick a variant for a user."""
        if self.status != "running":
            return None
        # Hash-based assignment for consistency
        h = hashlib.sha256(f"{self.promo_id}:{user_id}".encode()).hexdigest()
        bucket = int(h[:8], 16) / 0xFFFFFFFF
        cumulative = 0.0
        for v in self.variants:
            cumulative += v.weight
            if bucket <= cumulative:
                return v
        return self.variants[-1] if self.variants else None

    def end(self) -> None:
        self.status = "completed"
        self.ended_at = time.time()

    def __repr__(self) -> str:
        return f"Promotion({self.promo_id!r}, variants={len(self.variants)}, status={self.status})"


class PromotionEngine:
    """A/B testing and feature rollout engine."""

    def __init__(self) -> None:
        self._promotions: Dict[str, Promotion] = {}

    def create_promotion(self, name: str, variants: List[Variant], promo_id: Optional[str] = None) -> Promotion:
        pid = promo_id or f"promo-{uuid.uuid4().hex[:8]}"
        promo = Promotion(promo_id=pid, name=name, variants=variants)
        self._promotions[pid] = promo
        return promo

    def assign_user(self, promo_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Assign a user to a variant."""
        promo = self._promotions.get(promo_id)
        if not promo:
            return None
        variant = promo.pick_variant(user_id)
        if not variant:
            return None
        return {
            "promo_id": promo_id,
            "user_id": user_id,
            "variant_id": variant.variant_id,
            "variant_name": variant.name,
            "config": variant.config,
        }

    def rollout_progress(self, promo_id: str, user_assignments: Dict[str, str]) -> Dict[str, Any]:
        """Analyze rollout distribution."""
        promo = self._promotions.get(promo_id)
        if not promo:
            return {}
        counts: Dict[str, int] = defaultdict(int)
        for variant_id in user_assignments.values():
            counts[variant_id] += 1
        total = len(user_assignments)
        distribution = {}
        for v in promo.variants:
            actual = counts.get(v.variant_id, 0)
            distribution[v.variant_id] = {
                "expected_weight": v.weight,
                "actual_count": actual,
                "actual_pct": round(actual / total * 100, 2) if total else 0,
            }
        return {"promo_id": promo_id, "total_assigned": total, "distribution": distribution}

    def list_promotions(self, status: Optional[str] = None) -> List[Promotion]:
        promos = list(self._promotions.values())
        if status:
            promos = [p for p in promos if p.status == status]
        return promos

    def __repr__(self) -> str:
        return f"PromotionEngine(promotions={len(self._promotions)})"


# ──────────────────────────────────────────────────────────────
# 3.5 DocsRenderer — Markdown cloud documentation
# ──────────────────────────────────────────────────────────────

class DocsRenderer:
    """Render cloud documentation from structured data."""

    def __init__(self, title: str = "Cloud Platform Docs") -> None:
        self.title = title
        self._pages: List[Dict[str, Any]] = []

    def add_page(self, slug: str, title: str, content: str, tags: Optional[List[str]] = None) -> None:
        self._pages.append({
            "slug": slug,
            "title": title,
            "content": content,
            "tags": tags or [],
            "updated_at": time.time(),
        })

    def render_index(self) -> str:
        """Render a markdown index page."""
        lines = [f"# {self.title}", "", "## Pages", ""]
        for p in self._pages:
            tag_str = f" *({', '.join(p['tags'])})*" if p["tags"] else ""
            lines.append(f"- [{p['title']}](#{p['slug']}){tag_str}")
        return "\n".join(lines)

    def render_page(self, slug: str) -> Optional[str]:
        """Render a single page as markdown."""
        for p in self._pages:
            if p["slug"] == slug:
                lines = [f"# {p['title']}", "", p["content"]]
                return "\n".join(lines)
        return None

    def render_full(self) -> str:
        """Render all pages concatenated."""
        parts = [self.render_index(), ""]
        for p in self._pages:
            parts.append(f"---\n\n# {p['title']}\n\n{p['content']}\n")
        return "\n".join(parts)

    def search(self, query: str) -> List[Dict[str, Any]]:
        """Simple keyword search across pages."""
        q = query.lower()
        results = []
        for p in self._pages:
            score = 0
            if q in p["title"].lower():
                score += 3
            if q in p["content"].lower():
                score += 1
            for t in p["tags"]:
                if q in t.lower():
                    score += 2
            if score > 0:
                results.append({"page": p, "score": score})
        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    def __repr__(self) -> str:
        return f"DocsRenderer(title={self.title!r}, pages={len(self._pages)})"


# ──────────────────────────────────────────────────────────────
# 3.6 Features Demo Runner
# ──────────────────────────────────────────────────────────────

def demo_features(registry: ServiceRegistry) -> Tuple[DockerfileGenerator, WebSocketHub, CloudDashboard, PromotionEngine, DocsRenderer]:
    """Run Features demonstration."""
    print("\n" + "=" * 60)
    print("BATCH C — Section 3: Features")
    print("=" * 60)

    # DockerfileGenerator
    df = DockerfileGenerator()
    print(f"\n[DockerfileGenerator] Templates: {df.list_templates()}")
    rails_dockerfile = df.generate("rails", ruby_version="3.2", port="3000")
    print(f"    Rails Dockerfile: {len(rails_dockerfile)} chars")

    # WebSocketHub
    hub = WebSocketHub()
    hub.create_room("dev-chat")
    hub.join("dev-chat", "alice")
    hub.join("dev-chat", "bob")
    hub.publish("dev-chat", "alice", {"msg": "hello team"})
    print(f"\n[WebSocketHub] Rooms: {hub.list_rooms()}")
    print(f"    dev-chat members: {hub.room_info('dev-chat')['member_count']}")

    # CloudDashboard
    dash = CloudDashboard(registry)
    summary = dash.cluster_summary()
    print(f"\n[CloudDashboard] Overall: {summary['overall'].upper()}")
    print(f"    Services: {summary['total_services']} | Healthy: {summary['healthy']} | Warning: {summary['warning']} | Critical: {summary['critical']}")
    md = dash.render_markdown()
    print(f"    Markdown report: {len(md)} chars")

    # PromotionEngine
    promo_eng = PromotionEngine()
    variants = [
        Variant("v-control", "Control", 0.5, {"color": "blue"}),
        Variant("v-test", "Test", 0.5, {"color": "green"}),
    ]
    promo = promo_eng.create_promotion("ui-redesign", variants, promo_id="promo-ui-001")
    assignments = {}
    for uid in ["user-a", "user-b", "user-c", "user-d"]:
        result = promo_eng.assign_user(promo.promo_id, uid)
        if result:
            assignments[uid] = result["variant_id"]
    progress = promo_eng.rollout_progress(promo.promo_id, assignments)
    print(f"\n[PromotionEngine] Promo: {promo.name}")
    print(f"    Assignments: {progress['total_assigned']}")
    for vid, info in progress['distribution'].items():
        print(f"      {vid}: {info['actual_count']} users ({info['actual_pct']}%)")

    # DocsRenderer
    docs = DocsRenderer(title="Platform Operations Guide")
    docs.add_page("deploy", "Deployment Guide", "Deploy services using rolling strategy...", ["deploy"])
    docs.add_page("monitor", "Monitoring Setup", "Configure alerts and thresholds...", ["ops"])
    docs.add_page("rollback", "Rollback Procedures", "Steps to rollback a bad deploy...", ["deploy", "emergency"])
    print(f"\n[DocsRenderer] Pages: {len(docs._pages)}")
    print(f"    Index preview:\n{docs.render_index()[:200]}...")
    search_results = docs.search("deploy")
    print(f"    Search 'deploy': {len(search_results)} result(s)")

    print("\n" + "=" * 60)
    print("Section 3 COMPLETE")
    print("=" * 60)



# ════════════════════════════════════════════════════════════════
# Section 4 — Kernel
# BatchCKernel: MAGNATRIX Layer 7 (Browser/HTTP client) + Layer 5 (Knowledge/Infrastructure)
# ════════════════════════════════════════════════════════════════

class BatchCKernel:
    """
    MAGNATRIX bridge for Batch C DevOps/Cloud Native skill.
    
    Layers:
    - Layer 7: Browser / HTTP client — ServiceEndpoint connectivity
    - Layer 5: Knowledge / Infrastructure catalog — ServiceRegistry + CloudDashboard
    - Layer 11 (partial): Governance — IdentityManager DID lifecycle
    """

    def __init__(self, registry: ServiceRegistry, identity: Optional[IdentityManager] = None) -> None:
        self.registry = registry
        self.identity = identity or IdentityManager()
        self._layer7_registered = False
        self._layer5_registered = False
        self._layer11_registered = False
        self._hooks: Dict[str, List[Callable[..., None]]] = defaultdict(list)
        self._started_at = time.time()

    # ── Layer 7: Browser / HTTP Client ──

    def register_layer7(self) -> "BatchCKernel":
        """Register as Layer 7 (Browser/HTTP client) with MAGNATRIX."""
        self._layer7_registered = True
        logger.info("[BatchCKernel] Layer 7 registered — ServiceEndpoint connectivity")
        return self

    def http_probe(self, endpoint_url: str, timeout: int = 5) -> Dict[str, Any]:
        """Perform an HTTP health probe on a service endpoint."""
        import urllib.request
        import urllib.error
        start = time.time()
        try:
            req = urllib.request.Request(endpoint_url, method="HEAD")
            req.add_header("User-Agent", "BatchCKernel/1.0")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                latency = (time.time() - start) * 1000
                return {
                    "url": endpoint_url,
                    "reachable": True,
                    "status_code": resp.status,
                    "latency_ms": round(latency, 2),
                    "headers": dict(resp.headers),
                }
        except urllib.error.HTTPError as e:
            return {
                "url": endpoint_url,
                "reachable": True,
                "status_code": e.code,
                "latency_ms": round((time.time() - start) * 1000, 2),
                "error": str(e.reason),
            }
        except Exception as e:
            return {
                "url": endpoint_url,
                "reachable": False,
                "latency_ms": round((time.time() - start) * 1000, 2),
                "error": str(e),
            }

    # ── Layer 5: Knowledge / Infrastructure ──

    def register_layer5(self) -> "BatchCKernel":
        """Register as Layer 5 (Knowledge/Infrastructure) with MAGNATRIX."""
        self._layer5_registered = True
        logger.info("[BatchCKernel] Layer 5 registered — ServiceRegistry + CloudDashboard")
        return self

    def catalog_services(self) -> List[Dict[str, Any]]:
        """Return full service catalog for MAGNATRIX knowledge base."""
        return [s.to_dict() for s in self.registry.all_services()]

    def find_service(self, name: str) -> Optional[ServiceEndpoint]:
        """Lookup a service by name."""
        for s in self.registry.all_services():
            if s.name == name:
                return s
        return None

    def cluster_health_snapshot(self) -> Dict[str, Any]:
        """Generate a cluster health snapshot."""
        dashboard = CloudDashboard(self.registry)
        return dashboard.cluster_summary()

    # ── Layer 11: Governance (partial) ──

    def register_layer11(self, max_creds: int = 100) -> "BatchCKernel":
        """Register as Layer 11 (Governance) with MAGNATRIX."""
        self._layer11_registered = True
        logger.info(f"[BatchCKernel] Layer 11 registered — IdentityManager (max_creds={max_creds})")
        return self

    def issue_service_credential(self, service_id: str, claims: Dict[str, Any]) -> Optional[Credential]:
        """Issue a verifiable credential for a service identity."""
        svc = self.registry.get(service_id)
        if not svc:
            return None
        did = self.identity.create_did("key")
        return self.identity.issue_credential(did, did, {**claims, "service_id": service_id, "url": svc.url})

    # ── Event Hooks ──

    def register_hook(self, event: str, handler: Callable[..., None]) -> None:
        """Register an event hook."""
        self._hooks[event].append(handler)

    def _emit(self, event: str, **kwargs: Any) -> None:
        """Emit an event to all registered handlers."""
        for handler in self._hooks.get(event, []):
            try:
                handler(**kwargs)
            except Exception as e:
                logger.error(f"Hook error for {event}: {e}")

    # ── Lifecycle ──

    def full_sync(self) -> Dict[str, Any]:
        """Perform a full infrastructure sync."""
        self._emit("sync_start", kernel=self)
        result = {
            "services": len(self.registry.all_services()),
            "cluster_health": self.cluster_health_snapshot(),
            "dids": len(self.identity._dids),
            "credentials": len(self.identity._credentials),
            "layer7": self._layer7_registered,
            "layer5": self._layer5_registered,
            "layer11": self._layer11_registered,
            "uptime_sec": round(time.time() - self._started_at, 2),
        }
        self._emit("sync_complete", kernel=self, result=result)
        return result

    def status(self) -> Dict[str, Any]:
        """Return kernel status."""
        return {
            "registered_layers": {
                "layer7": self._layer7_registered,
                "layer5": self._layer5_registered,
                "layer11": self._layer11_registered,
            },
            "services": len(self.registry.all_services()),
            "hooks": {k: len(v) for k, v in self._hooks.items()},
            "uptime_sec": round(time.time() - self._started_at, 2),
        }

    def __repr__(self) -> str:
        return (
            f"BatchCKernel(services={len(self.registry.all_services())}, "
            f"L7={self._layer7_registered}, L5={self._layer5_registered}, L11={self._layer11_registered})"
        )


# ──────────────────────────────────────────────────────────────
# 4.1 Kernel Demo Runner
# ──────────────────────────────────────────────────────────────

def demo_kernel(registry: ServiceRegistry) -> BatchCKernel:
    """Run Kernel demonstration."""
    print("\n" + "=" * 60)
    print("BATCH C — Section 4: Kernel")
    print("=" * 60)

    idm = IdentityManager()
    kernel = BatchCKernel(registry, identity=idm)

    # Layer registration
    kernel.register_layer7().register_layer5().register_layer11(max_creds=50)
    print(f"\n[Kernel] {kernel}")

    # HTTP probe demo
    probe = kernel.http_probe("https://example.com", timeout=3)
    print(f"\n[HTTP Probe] example.com: status={probe.get('status_code')}, reachable={probe['reachable']}, latency={probe.get('latency_ms')}ms")

    # Service catalog
    catalog = kernel.catalog_services()
    print(f"\n[Catalog] {len(catalog)} service(s) exported")

    # Cluster health
    health = kernel.cluster_health_snapshot()
    print(f"\n[Cluster Health] Overall: {health.get('overall', 'unknown').upper()}")

    # DID + credential for a service
    web_svc = kernel.find_service("web")
    if web_svc:
        cred = kernel.issue_service_credential(web_svc.service_id, {"role": "frontend", "tier": "production"})
        if cred:
            print(f"\n[Credential] Issued for {web_svc.name}: {cred.cred_id[:24]}...")
            verify = idm.verify_credential(cred.cred_id)
            print(f"    Verification: {verify}")

    # Full sync
    sync = kernel.full_sync()
    print(f"\n[Full Sync] {json.dumps(sync, indent=2, default=str)}")

    # Status
    print(f"\n[Kernel Status] {json.dumps(kernel.status(), indent=2, default=str)}")

    print("\n" + "=" * 60)
    print("Section 4 COMPLETE")
    print("=" * 60)

    return kernel


# ════════════════════════════════════════════════════════════════
# __main__ — Full Batch C Demo
# ════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("BATCH C — DevOps/Cloud/Platform Native")
    print("Pure Python · stdlib only · ~1800 lines")
    print("=" * 60)

    # Build a sample registry for demo
    registry = ServiceRegistry()
    registry.register(ServiceEndpoint(
        service_id="svc-web", name="web", host="web.internal", port=443, protocol="https",
        version="1.2.0", dependencies=["svc-db", "svc-cache"],
    ))
    registry.register(ServiceEndpoint(
        service_id="svc-api", name="api", host="api.internal", port=443, protocol="https",
        version="2.0.1", dependencies=["svc-db"],
    ))
    registry.register(ServiceEndpoint(
        service_id="svc-db", name="db", host="db.internal", port=5432, protocol="tcp",
        version="14.5", dependencies=[],
    ))
    registry.register(ServiceEndpoint(
        service_id="svc-cache", name="cache", host="cache.internal", port=6379, protocol="tcp",
        version="7.0", dependencies=[],
    ))
    registry.register(ServiceEndpoint(
        service_id="svc-worker", name="worker", host="worker.internal", port=443, protocol="https",
        version="1.0.0", dependencies=["svc-db", "svc-queue"],
    ))
    registry.register(ServiceEndpoint(
        service_id="svc-queue", name="queue", host="queue.internal", port=5672, protocol="amqp",
        version="3.11", dependencies=[],
    ))

    # Run all sections
    demo_base_layer(registry)
    demo_core_engine(registry)
    demo_features(registry)
    kernel = demo_kernel(registry)

    print("\n" + "=" * 60)
    print("ALL SECTIONS COMPLETE — Batch C Ready")
    print("=" * 60)
    print(f"\nFinal Kernel Status:\n{json.dumps(kernel.status(), indent=2, default=str)}")
    sys.exit(0)




# ════════════════════════════════════════════════════════════════
# Section 3 — Features
# DockerfileGenerator + WebSocketHub + CloudDashboard
# PromotionEngine + DocsRenderer
# ════════════════════════════════════════════════════════════════

# ──────────────────────────────────────────────────────────────
# 3.1 DockerfileGenerator — Rails / Python / Go templates
# ──────────────────────────────────────────────────────────────

@dataclass
class DockerfileTemplate:
    """Pre-built Dockerfile template with variables."""
    name: str
    base_image: str
    template: str
    variables: Dict[str, str] = field(default_factory=dict)


class DockerfileGenerator:
    """
    Generate Dockerfiles from templates (fly-apps/dockerfile-rails inspired).

    Capabilities:
    - Rails, Python, Go, Node.js templates
    - Variable substitution
    - Multi-stage build support
    - Health check insertion
    """

    _TEMPLATES: Dict[str, DockerfileTemplate] = {
        "rails": DockerfileTemplate(
            name="rails",
            base_image="ruby:3.2-slim",
            template='''FROM {base} AS builder
WORKDIR /app
COPY Gemfile Gemfile.lock ./
RUN bundle config set --local deployment 'true' && \\
    bundle config set --local without 'development test' && \\
    bundle install
COPY . .
RUN bundle exec rails assets:precompile

FROM {base} AS runtime
WORKDIR /app
COPY --from=builder /app .
ENV RAILS_ENV=production
ENV PORT={port}
EXPOSE {port}
HEALTHCHECK --interval=30s --timeout=5s \\
  CMD curl -f http://localhost:{port}{health_path} || exit 1
CMD ["bundle", "exec", "puma", "-C", "config/puma.rb"]
''',
            variables={"base": "ruby:3.2-slim", "port": "3000", "health_path": "/health"},
        ),
        "python": DockerfileTemplate(
            name="python",
            base_image="python:3.11-slim",
            template='''FROM {base} AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

FROM {base} AS runtime
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
ENV PORT={port}
EXPOSE {port}
HEALTHCHECK --interval=30s --timeout=5s \\
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:{port}{health_path}')" || exit 1
CMD {start_cmd}
''',
            variables={"base": "python:3.11-slim", "port": "8080", "health_path": "/health", "start_cmd": "[\"python\", \"app.py\"]"},
        ),
        "go": DockerfileTemplate(
            name="go",
            base_image="golang:1.21-alpine",
            template='''FROM {base} AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -o app .

FROM alpine:latest AS runtime
WORKDIR /app
COPY --from=builder /app/app .
ENV PORT={port}
EXPOSE {port}
HEALTHCHECK --interval=30s --timeout=5s \\
  CMD wget --quiet --tries=1 --spider http://localhost:{port}{health_path} || exit 1
CMD ["./app"]
''',
            variables={"base": "golang:1.21-alpine", "port": "8080", "health_path": "/health"},
        ),
        "node": DockerfileTemplate(
            name="node",
            base_image="node:20-slim",
            template='''FROM {base} AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM {base} AS runtime
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
COPY package.json ./
ENV NODE_ENV=production
ENV PORT={port}
EXPOSE {port}
HEALTHCHECK --interval=30s --timeout=5s \\
  CMD node -e "require('http').get('http://localhost:{port}{health_path}', (r) => r.statusCode === 200 ? process.exit(0) : process.exit(1))"
CMD {start_cmd}
''',
            variables={"base": "node:20-slim", "port": "3000", "health_path": "/health", "start_cmd": "[\"node\", \"server.js\"]"},
        ),
    }

    def __init__(self) -> None:
        self._templates = dict(self._TEMPLATES)

    def list_templates(self) -> List[str]:
        return list(self._templates.keys())

    def generate(
        self,
        template_name: str,
        overrides: Optional[Dict[str, str]] = None,
    ) -> str:
        """Generate a Dockerfile from template with variable overrides."""
        tmpl = self._templates.get(template_name)
        if not tmpl:
            raise ValueError(f"Unknown template: {template_name}")
        vars = dict(tmpl.variables)
        if overrides:
            vars.update(overrides)
        vars.setdefault("base", tmpl.base_image)
        return tmpl.template.format(**vars)

    def add_custom_template(self, tmpl: DockerfileTemplate) -> None:
        self._templates[tmpl.name] = tmpl


# ──────────────────────────────────────────────────────────────
# 3.2 WebSocketHub — neffos-style pub/sub room manager
# ──────────────────────────────────────────────────────────────

@dataclass
class Room:
    """A pub/sub room."""
    room_id: str
    name: str
    members: Set[str] = field(default_factory=set)
    message_log: List[Dict[str, Any]] = field(default_factory=list)
    created_at: int = field(default_factory=lambda: int(time.time()))

    def join(self, client_id: str) -> None:
        self.members.add(client_id)

    def leave(self, client_id: str) -> None:
        self.members.discard(client_id)

    def broadcast(self, sender: str, payload: Any) -> None:
        msg = {"from": sender, "payload": payload, "timestamp": int(time.time())}
        self.message_log.append(msg)


@dataclass
class Client:
    """Connected WebSocket client stub."""
    client_id: str
    rooms: Set[str] = field(default_factory=set)
    connected_at: int = field(default_factory=lambda: int(time.time()))
    last_ping: int = 0


class WebSocketHub:
    """
    In-memory WebSocket hub with rooms and pub/sub (neffos-inspired).

    Capabilities:
    - Room creation / destruction
    - Join / leave / broadcast
    - Direct messaging
    - Presence tracking
    - Message history per room
    """

    def __init__(self) -> None:
        self._rooms: Dict[str, Room] = {}
        self._clients: Dict[str, Client] = {}

    def __repr__(self) -> str:
        return f"<WebSocketHub rooms={len(self._rooms)} clients={len(self._clients)}>"

    def create_room(self, room_id: str, name: str) -> Room:
        room = Room(room_id=room_id, name=name)
        self._rooms[room_id] = room
        return room

    def remove_room(self, room_id: str) -> bool:
        room = self._rooms.pop(room_id, None)
        if room:
            for cid in list(room.members):
                client = self._clients.get(cid)
                if client:
                    client.rooms.discard(room_id)
            return True
        return False

    def connect(self, client_id: str) -> Client:
        client = Client(client_id=client_id)
        self._clients[client_id] = client
        return client

    def disconnect(self, client_id: str) -> None:
        client = self._clients.pop(client_id, None)
        if client:
            for rid in list(client.rooms):
                room = self._rooms.get(rid)
                if room:
                    room.leave(client_id)

    def join(self, client_id: str, room_id: str) -> bool:
        client = self._clients.get(client_id)
        room = self._rooms.get(room_id)
        if not client or not room:
            return False
        client.rooms.add(room_id)
        room.join(client_id)
        return True

    def leave(self, client_id: str, room_id: str) -> bool:
        client = self._clients.get(client_id)
        room = self._rooms.get(room_id)
        if not client or not room:
            return False
        client.rooms.discard(room_id)
        room.leave(client_id)
        return True

    def broadcast(self, room_id: str, sender: str, payload: Any) -> int:
        """Broadcast to a room. Returns recipient count."""
        room = self._rooms.get(room_id)
        if not room:
            return 0
        room.broadcast(sender, payload)
        return len(room.members)

    def direct_message(self, sender: str, recipient: str, payload: Any) -> bool:
        """Send a direct message to a client."""
        if recipient not in self._clients:
            return False
        # Store in a DM room or log
        dm_room_id = f"dm:{min(sender, recipient)}:{max(sender, recipient)}"
        room = self._rooms.get(dm_room_id)
        if not room:
            room = self.create_room(dm_room_id, f"DM {sender} ↔ {recipient}")
            self.join(sender, dm_room_id)
            self.join(recipient, dm_room_id)
        room.broadcast(sender, payload)
        return True

    def get_room_info(self, room_id: str) -> Optional[Dict[str, Any]]:
        room = self._rooms.get(room_id)
        if not room:
            return None
        return {
            "room_id": room.room_id,
            "name": room.name,
            "members": list(room.members),
            "message_count": len(room.message_log),
            "created_at": room.created_at,
        }

    def list_rooms(self) -> List[str]:
        return list(self._rooms.keys())

    def presence(self, room_id: str) -> List[str]:
        room = self._rooms.get(room_id)
        return list(room.members) if room else []

    def cleanup_idle(self, idle_sec: int = 300) -> int:
        """Remove empty rooms and stale clients."""
        now = int(time.time())
        removed = 0
        for rid, room in list(self._rooms.items()):
            if not room.members and now - room.created_at > idle_sec:
                self.remove_room(rid)
                removed += 1
        for cid, client in list(self._clients.items()):
            if client.last_ping and now - client.last_ping > idle_sec:
                self.disconnect(cid)
                removed += 1
        return removed


# ──────────────────────────────────────────────────────────────
# 3.3 CloudDashboard — GKE-style cluster health summary
# ──────────────────────────────────────────────────────────────

@dataclass
class ClusterNode:
    """A node in a cluster."""
    node_id: str
    name: str
    status: ServiceStatus
    cpu_cores: int
    mem_gb: int
    cpu_used: float = 0.0
    mem_used: float = 0.0
    pod_count: int = 0
    labels: Dict[str, str] = field(default_factory=dict)

    @property
    def cpu_percent(self) -> float:
        return round(self.cpu_used / self.cpu_cores * 100, 1) if self.cpu_cores else 0

    @property
    def mem_percent(self) -> float:
        return round(self.mem_used / self.mem_gb * 100, 1) if self.mem_gb else 0


@dataclass
class ClusterPod:
    """A pod running on a node."""
    pod_id: str
    name: str
    node_id: str
    status: ServiceStatus
    restart_count: int = 0
    labels: Dict[str, str] = field(default_factory=dict)


class CloudDashboard:
    """
    Cluster health dashboard (GoogleCloudPlatform/cluster-health-dashboard inspired).

    Capabilities:
    - Node and pod inventory
    - Resource utilization aggregation
    - Status overview with color coding
    - Event log
    """

    def __init__(self) -> None:
        self._nodes: Dict[str, ClusterNode] = {}
        self._pods: Dict[str, ClusterPod] = {}
        self._events: List[Dict[str, Any]] = []

    def __repr__(self) -> str:
        return f"<CloudDashboard nodes={len(self._nodes)} pods={len(self._pods)}>"

    def add_node(self, node: ClusterNode) -> None:
        self._nodes[node.node_id] = node

    def add_pod(self, pod: ClusterPod) -> None:
        self._pods[pod.pod_id] = pod
        node = self._nodes.get(pod.node_id)
        if node:
            node.pod_count += 1

    def remove_pod(self, pod_id: str) -> Optional[ClusterPod]:
        pod = self._pods.pop(pod_id, None)
        if pod:
            node = self._nodes.get(pod.node_id)
            if node:
                node.pod_count = max(0, node.pod_count - 1)
        return pod

    def update_node_utilization(self, node_id: str, cpu: float, mem: float) -> None:
        node = self._nodes.get(node_id)
        if node:
            node.cpu_used = cpu
            node.mem_used = mem

    def snapshot(self) -> Dict[str, Any]:
        """Return full cluster snapshot."""
        total_cpu = sum(n.cpu_cores for n in self._nodes.values())
        total_mem = sum(n.mem_gb for n in self._nodes.values())
        used_cpu = sum(n.cpu_used for n in self._nodes.values())
        used_mem = sum(n.mem_used for n in self._nodes.values())

        node_statuses: Dict[str, int] = defaultdict(int)
        for n in self._nodes.values():
            node_statuses[n.status.name] += 1

        pod_statuses: Dict[str, int] = defaultdict(int)
        for p in self._pods.values():
            pod_statuses[p.status.name] += 1

        return {
            "nodes": {
                "total": len(self._nodes),
                "by_status": dict(node_statuses),
                "cpu_percent": round(used_cpu / total_cpu * 100, 1) if total_cpu else 0,
                "mem_percent": round(used_mem / total_mem * 100, 1) if total_mem else 0,
            },
            "pods": {
                "total": len(self._pods),
                "by_status": dict(pod_statuses),
            },
            "events_last_hour": len([e for e in self._events if e["timestamp"] >= int(time.time()) - 3600]),
        }

    def render_markdown(self) -> str:
        """Render a markdown summary."""
        snap = self.snapshot()
        lines = [
            "# Cluster Health Dashboard",
            f"",
            f"**Nodes:** {snap['nodes']['total']} | **Pods:** {snap['pods']['total']}",
            f"",
            "## Nodes",
            "| Node | Status | CPU | Mem | Pods |",
            "|------|--------|-----|-----|------|",
        ]
        for node in self._nodes.values():
            lines.append(
                f"| {node.name} | {node.status.name} | {node.cpu_percent}% | {node.mem_percent}% | {node.pod_count} |"
            )
        lines.extend([
            "",
            "## Pods",
            "| Pod | Node | Status | Restarts |",
            "|-----|------|--------|----------|",
        ])
        for pod in self._pods.values():
            node_name = self._nodes.get(pod.node_id, ClusterNode("", "?", ServiceStatus.UNKNOWN, 0, 0)).name
            lines.append(f"| {pod.name} | {node_name} | {pod.status.name} | {pod.restart_count} |")
        return "\n".join(lines)

    def emit_event(self, event_type: str, message: str, resource: str = "") -> None:
        self._events.append({
            "type": event_type,
            "message": message,
            "resource": resource,
            "timestamp": int(time.time()),
        })


# ──────────────────────────────────────────────────────────────
# 3.4 PromotionEngine — A/B test + rollout logic
# ──────────────────────────────────────────────────────────────

@dataclass
class Variant:
    """A single promotion variant."""
    variant_id: str
    name: str
    weight: float  # 0.0-1.0 traffic share
    config: Dict[str, Any] = field(default_factory=dict)
    impressions: int = 0
    conversions: int = 0

    @property
    def conversion_rate(self) -> float:
        return self.conversions / self.impressions if self.impressions else 0.0


@dataclass
class Promotion:
    """A running promotion / experiment."""
    promo_id: str
    name: str
    variants: List[Variant] = field(default_factory=list)
    status: str = "running"  # running | paused | stopped
    start_time: int = 0
    end_time: int = 0

    def pick_variant(self, user_id: str) -> Variant:
        """Consistent hash pick for user."""
        hash_val = int(hashlib.md5(user_id.encode()).hexdigest(), 16)
        bucket = (hash_val % 1000) / 1000.0
        cumulative = 0.0
        for v in self.variants:
            cumulative += v.weight
            if bucket <= cumulative:
                v.impressions += 1
                return v
        return self.variants[-1] if self.variants else Variant("", "", 0.0)

    def report_conversion(self, variant_id: str) -> bool:
        for v in self.variants:
            if v.variant_id == variant_id:
                v.conversions += 1
                return True
        return False


class PromotionEngine:
    """
    A/B testing and feature rollout engine (amazepromo + the-algorithm-ml inspired).

    Capabilities:
    - Create promotions with weighted variants
    - User-consistent variant assignment
    - Conversion tracking
    - Winner selection (auto-promote best variant)
    - Gradual rollout (0% → 100%)
    """

    def __init__(self) -> None:
        self._promotions: Dict[str, Promotion] = {}

    def create_promotion(
        self,
        name: str,
        variants: List[Tuple[str, float, Dict[str, Any]]],
        duration_hours: int = 168,
    ) -> Promotion:
        """
        Create a new promotion.
        variants: list of (variant_name, weight, config_dict)
        """
        now = int(time.time())
        promo = Promotion(
            promo_id=f"promo-{uuid.uuid4().hex[:8]}",
            name=name,
            variants=[
                Variant(
                    variant_id=f"v-{i}",
                    name=n,
                    weight=w,
                    config=c,
                )
                for i, (n, w, c) in enumerate(variants)
            ],
            start_time=now,
            end_time=now + duration_hours * 3600,
        )
        self._promotions[promo.promo_id] = promo
        return promo

    def assign_user(self, promo_id: str, user_id: str) -> Optional[Variant]:
        """Assign a user to a variant."""
        promo = self._promotions.get(promo_id)
        if not promo or promo.status != "running":
            return None
        return promo.pick_variant(user_id)

    def record_conversion(self, promo_id: str, variant_id: str) -> bool:
        promo = self._promotions.get(promo_id)
        if not promo:
            return False
        return promo.report_conversion(variant_id)

    def get_winner(self, promo_id: str) -> Optional[Variant]:
        """Return the best-performing variant."""
        promo = self._promotions.get(promo_id)
        if not promo or not promo.variants:
            return None
        return max(promo.variants, key=lambda v: v.conversion_rate)

    def rollout_percent(self, promo_id: str) -> float:
        """Compute rollout progress based on total traffic."""
        promo = self._promotions.get(promo_id)
        if not promo:
            return 0.0
        total_impressions = sum(v.impressions for v in promo.variants)
        # Assume target = 10 000 impressions for 100%
        return min(100.0, total_impressions / 100)

    def stop(self, promo_id: str) -> bool:
        promo = self._promotions.get(promo_id)
        if promo:
            promo.status = "stopped"
            return True
        return False

    def list_promotions(self) -> List[Promotion]:
        return list(self._promotions.values())


# ──────────────────────────────────────────────────────────────
# 3.5 DocsRenderer — Markdown cloud docs (cloudposse/docs inspired)
# ──────────────────────────────────────────────────────────────

class DocsRenderer:
    """
    Render cloud documentation from structured components.

    Capabilities:
    - Build markdown from sections
    - Table generation
    - Code block insertion
    - Navigation sidebar generation
    """

    def __init__(self, title: str = "Cloud Documentation") -> None:
        self.title = title
        self._sections: List[Dict[str, str]] = []

    def add_section(self, heading: str, content: str, level: int = 2) -> None:
        self._sections.append({"heading": heading, "content": content, "level": level})

    def add_table(self, heading: str, headers: List[str], rows: List[List[str]]) -> None:
        lines = ["| " + " | ".join(headers) + " |"]
        lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
        for row in rows:
            lines.append("| " + " | ".join(row) + " |")
        self.add_section(heading, "\n".join(lines))

    def add_code(self, heading: str, code: str, language: str = "bash") -> None:
        self.add_section(heading, f"```{language}\n{code}\n```")

    def render(self) -> str:
        lines = [f"# {self.title}", ""]
        for sec in self._sections:
            prefix = "#" * sec["level"]
            lines.extend([f"{prefix} {sec['heading']}", "", sec["content"], ""])
        return "\n".join(lines)

    def sidebar(self) -> str:
        """Generate markdown sidebar with TOC."""
        lines = ["- [Home](#)", ""]
        for sec in self._sections:
            anchor = sec["heading"].lower().replace(" ", "-").replace(".", "")
            indent = "  " * (sec["level"] - 2)
            lines.append(f"{indent}- [{sec['heading']}](#{anchor})")
        return "\n".join(lines)

    def save(self, filepath: str) -> None:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(self.render())


# ──────────────────────────────────────────────────────────────
# 3.6 Features Demo Runner
# ──────────────────────────────────────────────────────────────

def demo_features(
    registry: ServiceRegistry,
    monitor: Monitor,
) -> Tuple[DockerfileGenerator, WebSocketHub, CloudDashboard, PromotionEngine, DocsRenderer]:
    """Run Features demonstration."""
    print("\n" + "=" * 60)
    print("BATCH C — Section 3: Features")
    print("=" * 60)

    # DockerfileGenerator
    df_gen = DockerfileGenerator()
    print(f"\n[DockerfileGenerator] {len(df_gen.list_templates())} templates available")
    for name in df_gen.list_templates():
        dockerfile = df_gen.generate(name)
        print(f"\n    --- {name} Dockerfile ({len(dockerfile)} chars) ---")
        print(dockerfile[:400] + "...")

    # WebSocketHub
    hub = WebSocketHub()
    hub.create_room("general", "General Chat")
    hub.create_room("dev", "Dev Updates")
    for cid in ["alice", "bob", "charlie"]:
        hub.connect(cid)
        hub.join(cid, "general")
    hub.join("alice", "dev")
    hub.join("bob", "dev")

    print(f"\n[WebSocketHub] Rooms: {hub.list_rooms()}")
    print(f"    Presence in 'general': {hub.presence('general')}")
    recipients = hub.broadcast("dev", "alice", {"msg": "deploy started"})
    print(f"    Broadcast to 'dev': {recipients} recipient(s)")

    # CloudDashboard
    dash = CloudDashboard()
    nodes = [
        ClusterNode("n1", "worker-1", ServiceStatus.HEALTHY, 4, 16, cpu_used=2.5, mem_used=8.0, pod_count=12),
        ClusterNode("n2", "worker-2", ServiceStatus.HEALTHY, 4, 16, cpu_used=3.0, mem_used=10.0, pod_count=15),
        ClusterNode("n3", "worker-3", ServiceStatus.DEGRADED, 4, 16, cpu_used=3.8, mem_used=14.0, pod_count=8),
    ]
    for n in nodes:
        dash.add_node(n)
    pods = [
        ClusterPod("p1", "api-7d9f4", "n1", ServiceStatus.HEALTHY, 0),
        ClusterPod("p2", "api-7d9g5", "n2", ServiceStatus.HEALTHY, 0),
        ClusterPod("p3", "worker-x1", "n1", ServiceStatus.HEALTHY, 1),
        ClusterPod("p4", "worker-x2", "n3", ServiceStatus.DEGRADED, 3),
        ClusterPod("p5", "cache-redis", "n2", ServiceStatus.HEALTHY, 0),
    ]
    for p in pods:
        dash.add_pod(p)

    snap = dash.snapshot()
    print(f"\n[CloudDashboard] Snapshot:")
    print(f"    Nodes: {snap['nodes']}")
    print(f"    Pods: {snap['pods']}")

    md = dash.render_markdown()
    print(f"\nDashboard Markdown ({len(md)} chars):")
    print(md[:500] + "...")

    # PromotionEngine
    promo_engine = PromotionEngine()
    promo = promo_engine.create_promotion(
        "homepage-redesign",
        [
            ("control", 0.5, {"layout": "legacy"}),
            ("variant-a", 0.25, {"layout": "hero-cards"}),
            ("variant-b", 0.25, {"layout": "minimal"}),
        ],
        duration_hours=72,
    )
    print(f"\n[PromotionEngine] Created: {promo.promo_id} | {promo.name}")

    # Simulate traffic
    users = [f"user-{i}" for i in range(100)]
    for uid in users:
        variant = promo_engine.assign_user(promo.promo_id, uid)
        if variant and random.random() < 0.1:
            promo_engine.record_conversion(promo.promo_id, variant.variant_id)

    winner = promo_engine.get_winner(promo.promo_id)
    print(f"    Winner: {winner.name if winner else 'N/A'} (rate: {winner.conversion_rate:.2%})" if winner else "    No winner yet")
    print(f"    Rollout: {promo_engine.rollout_percent(promo.promo_id):.1f}%")

    # DocsRenderer
    docs = DocsRenderer("Batch C — DevOps Platform Docs")
    docs.add_section("Overview", "This platform provides DevOps orchestration, scheduling, monitoring, and identity management.")
    docs.add_table(
        "Services",
        ["Service", "Runtime", "Port", "Status"],
        [
            [s.name, s.profile.runtime if s.profile else "?", str(s.port), s.status.name]
            for s in registry.all_services()
        ],
    )
    docs.add_code("Deploy", "python batch_c_devops_cloud_native.py", "bash")

    print(f"\n[DocsRenderer] Generated: {len(docs.render())} chars")
    print(f"    Sidebar:\n{docs.sidebar()[:300]}...")

    print("\n" + "=" * 60)
    print("Section 3 COMPLETE")
    print("=" * 60)

    return df_gen, hub, dash, promo_engine, docs


# ════════════════════════════════════════════════════════════════
# Section 4 — Kernel
# BatchCKernel bridge + MAGNATRIX integration + __main__ demo
# ════════════════════════════════════════════════════════════════

# ──────────────────────────────────────────────────────────────
# 4.1 BatchCKernel — DevOps bridge ke MAGNATRIX Layer 7 + Layer 5
# ──────────────────────────────────────────────────────────────

@dataclass
class BatchCEvent:
    """Event emitted by Batch C kernel."""
    event_type: str
    source: str
    payload: Dict[str, Any]
    timestamp: int = field(default_factory=lambda: int(time.time()))


class BatchCKernel:
    """
    Kernel bridge for Batch C (DevOps/Cloud/Platform).

    Capabilities:
    - Auto-register with MAGNATRIX orchestrator
    - Event emission (hooks)
    - Health probe endpoint
    - Graceful shutdown
    - Service catalog export

    Bridges to:
    - Layer 7 (DevOps): deployment, scheduling, monitoring
    - Layer 5 (Knowledge): docs, identity, credentials
    """

    def __init__(
        self,
        registry: ServiceRegistry,
        orchestrator: Orchestrator,
        scheduler: Scheduler,
        monitor: Monitor,
        identity: IdentityManager,
        hub: WebSocketHub,
        dashboard: CloudDashboard,
    ) -> None:
        self.registry = registry
        self.orchestrator = orchestrator
        self.scheduler = scheduler
        self.monitor = monitor
        self.identity = identity
        self.hub = hub
        self.dashboard = dashboard
        self._events: List[BatchCEvent] = []
        self._hooks: Dict[str, List[Callable]] = defaultdict(list)
        self._running = False
        self._kernel_did: Optional[str] = None

    def __repr__(self) -> str:
        return f"<BatchCKernel services={len(self.registry.all_services())} events={len(self._events)}>"

    def register_hook(self, event_type: str, callback: Callable) -> None:
        self._hooks[event_type].append(callback)

    def emit(self, event_type: str, payload: Dict[str, Any], source: str = "kernel") -> BatchCEvent:
        evt = BatchCEvent(event_type=event_type, source=source, payload=payload)
        self._events.append(evt)
        for hook in self._hooks.get(event_type, []):
            try:
                hook(evt)
            except Exception as e:
                print(f"Hook error: {e}")
        return evt

    def auto_register_services(self) -> None:
        """Auto-populate registry with default platform services."""
        defaults = [
            ("web-frontend", "frontend", "node", 3000, ["api-gateway"]),
            ("api-gateway", "gateway", "go", 8080, ["auth-service", "order-service"]),
            ("auth-service", "auth", "python", 9000, []),
            ("order-service", "orders", "python", 7000, ["payment-service"]),
            ("payment-service", "payments", "python", 8000, []),
        ]
        for sid, name, runtime, port, deps in defaults:
            profile = ConfigProfile(
                runtime=RuntimeType(runtime.upper()) if runtime.upper() in [e.name for e in RuntimeType] else RuntimeType.PYTHON,
                version="1.0.0",
                env={"PORT": str(port), "LOG_LEVEL": "info"},
                build_command="make build",
                start_command=f"python app.py --port {port}" if runtime == "python" else f"./{name}",
            )
            svc = ServiceEndpoint(
                service_id=sid,
                name=name,
                host=f"10.0.1.{10 + len(self.registry.all_services())}",
                port=port,
                health_url=f"/health",
                profile=profile,
                tags=["platform", runtime],
                dependencies=deps,
            )
            self.registry.register(svc)

    def health_probe(self) -> Dict[str, Any]:
        """Return kernel health snapshot."""
        return {
            "status": "healthy" if self._running else "stopped",
            "services_registered": len(self.registry.all_services()),
            "deploy_plans": len(self.orchestrator._plans),
            "scheduled_jobs": len(self.scheduler.list_jobs()),
            "active_alerts": len(self.monitor._alerts),
            "identities": len(self.identity._dids),
            "rooms": len(self.hub._rooms),
            "events_emitted": len(self._events),
        }

    def export_catalog(self) -> Dict[str, Any]:
        """Export full service catalog for Layer 5 (Knowledge)."""
        return {
            "services": [
                {
                    "id": s.service_id,
                    "name": s.name,
                    "endpoint": f"{s.host}:{s.port}",
                    "status": s.status.name,
                    "runtime": s.profile.runtime.name if s.profile else "UNKNOWN",
                    "tags": s.tags,
                    "dependencies": s.dependencies,
                }
                for s in self.registry.all_services()
            ],
            "cluster": self.registry.cluster_health(),
            "health": self.health_probe(),
            "timestamp": int(time.time()),
        }

    def start(self) -> None:
        self._running = True
        self._kernel_did = self.identity.create_did("kernel")
        self.emit("kernel.start", {"did": self._kernel_did})

    def stop(self) -> None:
        self._running = False
        self.emit("kernel.stop", {"did": self._kernel_did})


# ──────────────────────────────────────────────────────────────
# 4.2 Demo — Full pipeline: deploy → schedule → monitor → rollback
# ──────────────────────────────────────────────────────────────

def demo_batch_c_full() -> None:
    """Run the complete Batch C demonstration."""
    print("\n" + "=" * 60)
    print("BATCH C — Full Kernel Demo")
    print("=" * 60)

    # Initialize all layers
    registry = ServiceRegistry()
    df_gen = DockerfileGenerator()
    hub = WebSocketHub()
    dash = CloudDashboard()
    promo = PromotionEngine()
    idm = IdentityManager()

    # Build core engines
    orch = Orchestrator(registry)
    sched = Scheduler()
    mon = Monitor(registry)

    # Initialize kernel
    kernel = BatchCKernel(
        registry=registry,
        orchestrator=orch,
        scheduler=sched,
        monitor=mon,
        identity=idm,
        hub=hub,
        dashboard=dash,
    )

    # Hook example: log every deploy stage
    def on_deploy(evt: BatchCEvent) -> None:
        if evt.event_type == "deploy.stage":
            print(f"    [HOOK] Deploy stage: {evt.payload}")

    kernel.register_hook("deploy.stage", on_deploy)
    kernel.register_hook("kernel.start", lambda e: print(f"    [HOOK] Kernel started: {e.payload}"))

    # Start kernel
    kernel.start()

    # Auto-register platform services
    kernel.auto_register_services()
    print(f"\n[Auto-Register] {len(registry.all_services())} services registered")
    for s in registry.all_services():
        print(f"    {s.service_id} → {s.host}:{s.port} ({s.profile.runtime.name})")

    # Topological deploy order
    topo = registry.topological_deploy_order()
    print(f"\n[Deploy Order] Topological: {[s.service_id for s in topo]}")

    # Execute rolling deploy
    all_ids = [s.service_id for s in registry.all_services()]
    plan = orch.plan_deploy(all_ids, strategy="rolling", batch_size=2)
    print(f"\n[Rolling Deploy] Plan: {plan.plan_id}")
    stages = orch.execute_plan(plan.plan_id)
    for st in stages:
        kernel.emit("deploy.stage", {"stage": st.stage_num, "status": st.status, "services": st.service_ids})
        print(f"    Stage {st.stage_num}: {st.status} ({len(st.service_ids)} services)")

    # Schedule maintenance jobs
    sched.add_job("health-check", "python health_check.py", ScheduleRecurrence.HOURLY, priority=1)
    sched.add_job("backup-db", "pg_dump db | gzip > backup.sql.gz", ScheduleRecurrence.DAILY, priority=2)
    sched.add_job("cleanup-logs", "find /var/log -mtime +7 -delete", ScheduleRecurrence.DAILY, priority=5)
    sched.add_job("promo-sync", "python promo_sync.py", ScheduleRecurrence.HOURLY, priority=3)
    sched.add_job("weekly-report", "python generate_weekly.py", ScheduleRecurrence.WEEKLY, priority=4)
    print(f"\n[Scheduler] {len(sched.list_jobs())} jobs queued")

    # Run health checks + monitor
    mon.add_rule(AlertRule("r-latency", "latency_ms", ">", 250, severity=HealthLevel.WARNING))
    mon.add_rule(AlertRule("r-cpu", "cpu_percent", "avg>", 80, severity=HealthLevel.CRITICAL))
    mon.simulate_health_checks()
    alerts = mon.check_rules(window_sec=3600)
    print(f"\n[Monitor] {len(alerts)} alert(s) triggered")
    for a in alerts[:3]:
        print(f"    [{a['severity']}] {a['message']}")

    # Cluster dashboard
    nodes = [
        ClusterNode("n1", "worker-1", ServiceStatus.HEALTHY, 4, 16, cpu_used=2.5, mem_used=8.0, pod_count=12),
        ClusterNode("n2", "worker-2", ServiceStatus.HEALTHY, 4, 16, cpu_used=3.0, mem_used=10.0, pod_count=15),
        ClusterNode("n3", "worker-3", ServiceStatus.DEGRADED, 4, 16, cpu_used=3.8, mem_used=14.0, pod_count=8),
    ]
    for n in nodes:
        dash.add_node(n)
    pods = [
        ClusterPod("p1", "api-7d9f4", "n1", ServiceStatus.HEALTHY, 0),
        ClusterPod("p2", "api-7d9g5", "n2", ServiceStatus.HEALTHY, 0),
        ClusterPod("p3", "worker-x1", "n1", ServiceStatus.HEALTHY, 1),
        ClusterPod("p4", "worker-x2", "n3", ServiceStatus.DEGRADED, 3),
        ClusterPod("p5", "cache-redis", "n2", ServiceStatus.HEALTHY, 0),
    ]
    for p in pods:
        dash.add_pod(p)
    snap = dash.snapshot()
    print(f"\n[Dashboard] Nodes: {snap['nodes']['total']} | Pods: {snap['pods']['total']}")

    # Identity + credentials
    admin = idm.create_did("key")
    service = idm.create_did("key")
    idm.set_role(admin, IdentityRole.ISSUER)
    cred = idm.issue_credential(admin, service, {"service": "api-gateway", "tier": "production"}, ttl_seconds=86400 * 7)
    if cred:
        result = idm.verify_credential(cred.cred_id)
        print(f"\n[Identity] Admin: {admin[:20]}... | Service: {service[:20]}...")
        print(f"    Credential valid: {result['valid']} | Expires in 7 days")

    # WebSocket hub
    hub.create_room("ops", "Ops Channel")
    for u in ["alice", "bob"]:
        hub.connect(u)
        hub.join(u, "ops")
    hub.broadcast("ops", "system", {"msg": "Batch C kernel online"})
    print(f"\n[WebSocket] Room 'ops': {len(hub.presence('ops'))} member(s)")

    # Promotion
    pr = promo.create_promotion(
        "feature-rollout",
        [("control", 0.5, {}), ("new-ui", 0.5, {"ui_version": "2.0"})],
        duration_hours=48,
    )
    for u in [f"user-{i}" for i in range(20)]:
        v = promo.assign_user(pr.promo_id, u)
        if v and random.random() < 0.2:
            promo.record_conversion(pr.promo_id, v.variant_id)
    winner = promo.get_winner(pr.promo_id)
    print(f"\n[Promotion] {pr.name} | Winner: {winner.name if winner else 'N/A'} (rate: {winner.conversion_rate:.1%})" if winner else "")

    # Health probe
    probe = kernel.health_probe()
    print(f"\n[Kernel Health] {probe}")

    # Export catalog
    catalog = kernel.export_catalog()
    print(f"\n[Catalog Export] {len(catalog['services'])} services | Cluster: {catalog['cluster']['status']}")

    # Stop kernel
    kernel.stop()

    print("\n" + "=" * 60)
    print("BATCH C — ALL SECTIONS COMPLETE")
    print(f"Total file: ~{len(open('/mnt/agents/MAGNATRIX-OS/runtime/batch_c_devops_cloud_native.py').readlines())} lines")
    print("=" * 60)


# ──────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Run individual section demos
    print("BATCH C — DevOps/Cloud/Platform Native")
    print("Run: python batch_c_devops_cloud_native.py")
    print("")
    print("Sections:")
    print("  1. BaseLayer    — Color schemes, service registry, health")
    print("  2. CoreEngine   — Orchestrator, scheduler, monitor, identity")
    print("  3. Features     — Dockerfile gen, WebSocket hub, dashboard, promo, docs")
    print("  4. Kernel       — Full integration demo")
    print("")

    # Run full demo
    demo_batch_c_full()

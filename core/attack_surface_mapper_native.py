"""
attack_surface_mapper_native.py
MAGNATRIX-OS — Attack Surface Mapper

Inspired by Frogy2.0/Orbis: Full-spectrum automated external attack surface intelligence.
Map and track organization's internet-facing attack surface. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class AttackSurfaceAsset:
    asset_id: str
    asset_type: str
    domain: str
    ip: str
    port: int
    service: str
    status: str
    risk_score: float
    discovered_at: str = ""
    last_seen: str = ""
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.discovered_at:
            self.discovered_at = datetime.now().isoformat()
        if not self.last_seen:
            self.last_seen = self.discovered_at


class AttackSurfaceMapper:
    """Map and track an organization's internet-facing attack surface."""

    ASSET_TYPES = ["domain", "subdomain", "ip", "port", "web_app", "cloud", "api", "login_panel"]

    def __init__(self, data_dir: str = "./attack_surface"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.assets: Dict[str, AttackSurfaceAsset] = {}
        self.domains: List[str] = []
        self._load()

    def _load(self) -> None:
        file = self.data_dir / "assets.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for aid, ad in data.items():
                        self.assets[aid] = AttackSurfaceAsset(**ad)
            except Exception:
                pass
        file2 = self.data_dir / "domains.json"
        if file2.exists():
            try:
                with open(file2, "r", encoding="utf-8") as f:
                    self.domains = json.load(f)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.data_dir / "assets.json", "w", encoding="utf-8") as f:
            json.dump({aid: asdict(a) for aid, a in self.assets.items()}, f, indent=2)
        with open(self.data_dir / "domains.json", "w", encoding="utf-8") as f:
            json.dump(self.domains, f, indent=2)

    def add_domain(self, domain: str) -> None:
        if domain not in self.domains:
            self.domains.append(domain)
            self._save()

    def add_asset(self, asset_id: str, asset_type: str, domain: str, ip: str, port: int,
                  service: str, status: str, risk_score: float, tags: Optional[List[str]] = None) -> AttackSurfaceAsset:
        asset = AttackSurfaceAsset(
            asset_id=asset_id, asset_type=asset_type, domain=domain, ip=ip,
            port=port, service=service, status=status, risk_score=risk_score,
            tags=tags or [],
        )
        self.assets[asset_id] = asset
        self._save()
        return asset

    def discover_from_domain(self, domain: str) -> List[AttackSurfaceAsset]:
        """Simulate discovering assets from a domain."""
        import random
        discovered = []
        for i in range(random.randint(3, 10)):
            aid = f"{domain}_asset_{i}"
            asset_types = self.ASSET_TYPES
            atype = random.choice(asset_types)
            ip = f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}"
            port = random.choice([80, 443, 8080, 22, 53, 3306, 8443])
            service = random.choice(["http", "https", "ssh", "dns", "mysql", "unknown"])
            risk = round(random.uniform(0, 10), 2)
            asset = self.add_asset(aid, atype, domain, ip, port, service, "active", risk)
            discovered.append(asset)
        self.add_domain(domain)
        return discovered

    def get_assets_by_domain(self, domain: str) -> List[AttackSurfaceAsset]:
        return [a for a in self.assets.values() if a.domain == domain]

    def get_assets_by_type(self, asset_type: str) -> List[AttackSurfaceAsset]:
        return [a for a in self.assets.values() if a.asset_type == asset_type]

    def get_high_risk(self, threshold: float = 7.0) -> List[AttackSurfaceAsset]:
        return [a for a in self.assets.values() if a.risk_score >= threshold]

    def get_stats(self) -> Dict[str, Any]:
        by_type = {}
        for a in self.assets.values():
            by_type[a.asset_type] = by_type.get(a.asset_type, 0) + 1
        return {
            "total_assets": len(self.assets), "domains": len(self.domains),
            "by_type": by_type, "high_risk": len(self.get_high_risk()),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["AttackSurfaceMapper", "AttackSurfaceAsset"]
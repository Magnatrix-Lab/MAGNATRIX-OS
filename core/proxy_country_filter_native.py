"""Proxy Country Filter - Country and region filtering for proxies."""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class GeoProxy:
    proxy_id: str
    host: str
    port: int
    country_code: str = ""
    country_name: str = ""
    region: str = ""
    city: str = ""
    latitude: float = 0.0
    longitude: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "proxy_id": self.proxy_id,
            "host": self.host,
            "port": self.port,
            "country_code": self.country_code,
            "country_name": self.country_name,
            "region": self.region,
            "city": self.city,
            "latitude": self.latitude,
            "longitude": self.longitude,
        }


class ProxyCountryFilter:
    """Filter proxies by country, region, and geographic location."""

    # Simulated country database
    COUNTRY_MAP = {
        "US": ("United States", "North America"),
        "GB": ("United Kingdom", "Europe"),
        "DE": ("Germany", "Europe"),
        "FR": ("France", "Europe"),
        "NL": ("Netherlands", "Europe"),
        "JP": ("Japan", "Asia"),
        "SG": ("Singapore", "Asia"),
        "CA": ("Canada", "North America"),
        "AU": ("Australia", "Oceania"),
        "BR": ("Brazil", "South America"),
        "IN": ("India", "Asia"),
        "RU": ("Russia", "Europe"),
    }

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "proxy_country"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.proxies: Dict[str, GeoProxy] = {}
        self._load_state()

    def _load_state(self) -> None:
        state_file = self.data_dir / "state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                for p in data.get("proxies", []):
                    self.proxies[p["proxy_id"]] = GeoProxy(**p)
            except Exception:
                pass

    def _save_state(self) -> None:
        state_file = self.data_dir / "state.json"
        state = {"proxies": [p.to_dict() for p in self.proxies.values()]}
        state_file.write_text(json.dumps(state, indent=2))

    def _resolve_geo(self, host: str) -> Dict[str, str]:
        """Simulate geo-IP lookup from host."""
        # Deterministic based on host hash
        idx = hash(host) % len(self.COUNTRY_MAP)
        code = list(self.COUNTRY_MAP.keys())[idx]
        name, region = self.COUNTRY_MAP[code]
        return {
            "country_code": code,
            "country_name": name,
            "region": region,
            "city": f"City_{code}",
            "latitude": 10.0 + (hash(host) % 80),
            "longitude": -180.0 + (hash(host + "lon") % 360),
        }

    def add_proxy(self, host: str, port: int, country_code: str = "") -> GeoProxy:
        proxy_id = f"{host}:{port}"
        geo = self._resolve_geo(host) if not country_code else {
            "country_code": country_code,
            "country_name": self.COUNTRY_MAP.get(country_code, ("Unknown", "Unknown"))[0],
            "region": self.COUNTRY_MAP.get(country_code, ("Unknown", "Unknown"))[1],
            "city": "Unknown",
            "latitude": 0.0,
            "longitude": 0.0,
        }
        proxy = GeoProxy(
            proxy_id=proxy_id,
            host=host,
            port=port,
            country_code=geo["country_code"],
            country_name=geo["country_name"],
            region=geo["region"],
            city=geo["city"],
            latitude=geo["latitude"],
            longitude=geo["longitude"],
        )
        self.proxies[proxy_id] = proxy
        self._save_state()
        return proxy

    def filter_by_country(self, country_code: str) -> List[GeoProxy]:
        return [p for p in self.proxies.values() if p.country_code == country_code.upper()]

    def filter_by_region(self, region: str) -> List[GeoProxy]:
        return [p for p in self.proxies.values() if p.region.lower() == region.lower()]

    def exclude_countries(self, country_codes: List[str]) -> List[GeoProxy]:
        codes = set(c.upper() for c in country_codes)
        return [p for p in self.proxies.values() if p.country_code not in codes]

    def get_country_distribution(self) -> Dict[str, int]:
        dist = {}
        for p in self.proxies.values():
            dist[p.country_code] = dist.get(p.country_code, 0) + 1
        return dist

    def get_region_distribution(self) -> Dict[str, int]:
        dist = {}
        for p in self.proxies.values():
            dist[p.region] = dist.get(p.region, 0) + 1
        return dist

    def get_stats(self) -> Dict:
        return {
            "proxies_total": len(self.proxies),
            "countries": len(self.get_country_distribution()),
            "regions": len(self.get_region_distribution()),
            "country_dist": self.get_country_distribution(),
        }

    def to_dict(self) -> Dict:
        return {
            "proxies": [p.to_dict() for p in self.proxies.values()],
            "stats": self.get_stats(),
        }


__all__ = ["ProxyCountryFilter", "GeoProxy"]

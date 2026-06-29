"""Proxy Scraper - Scrape and parse proxy lists from various sources."""
from __future__ import annotations

import json
import time
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class ScrapeSource:
    source_id: str
    url: str
    protocol: str = "http"
    format: str = "txt"  # txt, json, csv
    last_scraped: float = 0.0
    proxies_found: int = 0
    status: str = "pending"

    def to_dict(self) -> Dict:
        return {
            "source_id": self.source_id,
            "url": self.url,
            "protocol": self.protocol,
            "format": self.format,
            "last_scraped": self.last_scraped,
            "proxies_found": self.proxies_found,
            "status": self.status,
        }


@dataclass
class ScrapedProxy:
    proxy_id: str
    host: str
    port: int
    protocol: str = "http"
    country: str = ""
    source_id: str = ""
    scraped_at: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "proxy_id": self.proxy_id,
            "host": self.host,
            "port": self.port,
            "protocol": self.protocol,
            "country": self.country,
            "source_id": self.source_id,
            "scraped_at": self.scraped_at,
        }


class ProxyScraper:
    """Scrape proxy lists from various sources and formats."""

    DEFAULT_SOURCES = [
        ("proxifly_http", "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/http/data.txt", "http", "txt"),
        ("proxifly_https", "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/https/data.txt", "https", "txt"),
        ("proxifly_socks4", "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/socks4/data.txt", "socks4", "txt"),
        ("proxifly_socks5", "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/protocols/socks5/data.txt", "socks5", "txt"),
    ]

    def __init__(self, workspace: str = "."):
        self.workspace = Path(workspace)
        self.data_dir = self.workspace / "data" / "proxy_scraper"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.sources: Dict[str, ScrapeSource] = {}
        self.proxies: Dict[str, ScrapedProxy] = {}
        self._init_default_sources()
        self._load_state()

    def _init_default_sources(self) -> None:
        for sid, url, proto, fmt in self.DEFAULT_SOURCES:
            self.sources[sid] = ScrapeSource(source_id=sid, url=url, protocol=proto, format=fmt)

    def _load_state(self) -> None:
        state_file = self.data_dir / "state.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text())
                for p in data.get("proxies", []):
                    self.proxies[p["proxy_id"]] = ScrapedProxy(**p)
            except Exception:
                pass

    def _save_state(self) -> None:
        state_file = self.data_dir / "state.json"
        state = {
            "sources": [s.to_dict() for s in self.sources.values()],
            "proxies": [p.to_dict() for p in self.proxies.values()],
        }
        state_file.write_text(json.dumps(state, indent=2))

    def parse_text_list(self, raw_text: str, source_id: str = "", protocol: str = "http") -> List[ScrapedProxy]:
        """Parse newline-separated host:port proxy list."""
        parsed = []
        for line in raw_text.strip().split("\n"):
            line = line.strip()
            if not line or ":" not in line:
                continue
            host, port_str = line.rsplit(":", 1)
            try:
                port = int(port_str)
                proxy_id = f"{host}:{port}_{protocol}"
                proxy = ScrapedProxy(
                    proxy_id=proxy_id,
                    host=host,
                    port=port,
                    protocol=protocol,
                    source_id=source_id,
                    scraped_at=time.time(),
                )
                parsed.append(proxy)
                self.proxies[proxy_id] = proxy
            except ValueError:
                continue
        self._save_state()
        return parsed

    def parse_json_list(self, raw_data: List[Dict], source_id: str = "") -> List[ScrapedProxy]:
        """Parse JSON array of proxy objects."""
        parsed = []
        for item in raw_data:
            host = item.get("ip", item.get("host", ""))
            port = item.get("port", 0)
            protocol = item.get("protocol", "http")
            country = item.get("country", "")
            if not host or not port:
                continue
            proxy_id = f"{host}:{port}_{protocol}"
            proxy = ScrapedProxy(
                proxy_id=proxy_id,
                host=host,
                port=int(port),
                protocol=protocol,
                country=country,
                source_id=source_id,
                scraped_at=time.time(),
            )
            parsed.append(proxy)
            self.proxies[proxy_id] = proxy
        self._save_state()
        return parsed

    def add_source(self, url: str, protocol: str = "http", format: str = "txt") -> ScrapeSource:
        source_id = f"src_{hashlib.md5(url.encode()).hexdigest()[:8]}"
        source = ScrapeSource(source_id=source_id, url=url, protocol=protocol, format=format)
        self.sources[source_id] = source
        self._save_state()
        return source

    def simulate_scrape(self, source_id: str, raw_text: str = "") -> List[ScrapedProxy]:
        """Simulate scraping from a source."""
        if source_id not in self.sources:
            raise ValueError(f"Source {source_id} not found")
        source = self.sources[source_id]
        source.last_scraped = time.time()
        if not raw_text:
            # Simulate some proxies
            raw_text = "192.168.1.1:8080\n10.0.0.1:3128\n203.0.113.5:1080"
        proxies = self.parse_text_list(raw_text, source_id, source.protocol)
        source.proxies_found = len(proxies)
        source.status = "completed"
        self._save_state()
        return proxies

    def get_proxies_by_source(self, source_id: str) -> List[ScrapedProxy]:
        return [p for p in self.proxies.values() if p.source_id == source_id]

    def get_stats(self) -> Dict:
        total = len(self.proxies)
        by_protocol = {}
        for p in self.proxies.values():
            by_protocol[p.protocol] = by_protocol.get(p.protocol, 0) + 1
        return {
            "sources_total": len(self.sources),
            "proxies_scraped": total,
            "by_protocol": by_protocol,
        }

    def to_dict(self) -> Dict:
        return {
            "sources": [s.to_dict() for s in self.sources.values()],
            "proxies": [p.to_dict() for p in self.proxies.values()],
            "stats": self.get_stats(),
        }


__all__ = ["ProxyScraper", "ScrapeSource", "ScrapedProxy"]

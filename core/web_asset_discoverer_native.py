"""
web_asset_discoverer_native.py
MAGNATRIX-OS — Web Asset Discoverer

Inspired by Frogy2.0: Web application discovery, login panel detection, and tech fingerprinting. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class WebAsset:
    url: str
    title: str
    status_code: int
    server: str
    tech_stack: List[str] = field(default_factory=list)
    is_login_panel: bool = False
    has_exposed_api: bool = False
    response_size: int = 0
    discovered_at: str = ""

    def __post_init__(self):
        if not self.discovered_at:
            self.discovered_at = datetime.now().isoformat()


class WebAssetDiscoverer:
    """Discover web assets, login panels, and tech stacks."""

    TECH_SIGNATURES = {
        "WordPress": ["wp-content", "wp-includes"],
        "Drupal": ["sites/default", "drupal.js"],
        "Joomla": ["joomla", "com_content"],
        "React": ["react", "_react"],
        "Angular": ["ng-app", "angular"],
        "Vue": ["vue.js", "__VUE__"],
        "Flask": ["werkzeug", "flask"],
        "Django": ["csrftoken", "django"],
        "Spring": ["spring-boot", "actuator"],
        "Nginx": ["nginx"],
        "Apache": ["apache"],
    }

    LOGIN_INDICATORS = ["login", "signin", "admin", "auth", "authenticate", "password", "sign-in", "log-in"]

    def __init__(self, data_dir: str = "./web_assets"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.assets: Dict[str, WebAsset] = {}
        self._load()

    def _load(self) -> None:
        file = self.data_dir / "assets.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for url, ad in data.items():
                        self.assets[url] = WebAsset(**ad)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.data_dir / "assets.json", "w", encoding="utf-8") as f:
            json.dump({url: asdict(a) for url, a in self.assets.items()}, f, indent=2)

    def discover(self, url: str, html_content: str = "", headers: Optional[Dict[str, str]] = None) -> WebAsset:
        """Discover web asset from URL and content."""
        import random
        headers = headers or {}
        title = self._extract_title(html_content) or f"Page at {url}"
        server = headers.get("Server", "unknown")
        tech = self._fingerprint_tech(html_content, headers)
        is_login = any(ind in url.lower() or ind in html_content.lower() for ind in self.LOGIN_INDICATORS)
        has_api = "/api" in url.lower() or "api" in html_content.lower()
        asset = WebAsset(
            url=url, title=title, status_code=random.choice([200, 301, 403, 404]),
            server=server, tech_stack=tech, is_login_panel=is_login,
            has_exposed_api=has_api, response_size=len(html_content),
        )
        self.assets[url] = asset
        self._save()
        return asset

    def _extract_title(self, html: str) -> str:
        import re
        m = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
        return m.group(1) if m else ""

    def _fingerprint_tech(self, html: str, headers: Dict[str, str]) -> List[str]:
        found = []
        combined = html.lower() + " ".join(f"{k}:{v}" for k, v in headers.items()).lower()
        for tech, signatures in self.TECH_SIGNATURES.items():
            if any(sig in combined for sig in signatures):
                found.append(tech)
        return found

    def get_login_panels(self) -> List[WebAsset]:
        return [a for a in self.assets.values() if a.is_login_panel]

    def get_exposed_apis(self) -> List[WebAsset]:
        return [a for a in self.assets.values() if a.has_exposed_api]

    def get_by_tech(self, tech: str) -> List[WebAsset]:
        return [a for a in self.assets.values() if tech in a.tech_stack]

    def get_stats(self) -> Dict[str, Any]:
        login_count = len(self.get_login_panels())
        api_count = len(self.get_exposed_apis())
        return {"total_assets": len(self.assets), "login_panels": login_count, "exposed_apis": api_count}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["WebAssetDiscoverer", "WebAsset"]
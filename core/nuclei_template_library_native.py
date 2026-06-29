"""
nuclei_template_library_native.py
MAGNATRIX-OS — Nuclei Template Library

Manage a library of Nuclei templates with tagging, search, and categorization. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class LibraryTemplate:
    template_id: str
    name: str
    author: str
    severity: str
    tags: List[str] = field(default_factory=list)
    protocol: str = "http"
    cve_id: str = ""
    category: str = ""


class NucleiTemplateLibrary:
    """Manage a library of Nuclei templates with tagging and categorization."""

    CATEGORIES = ["cve", "exposed-panels", "misconfiguration", "vulnerabilities", "takeovers", "subdomain-takeover", "token-spray"]

    def __init__(self, library_dir: str = "./nuclei_library"):
        self.library_dir = Path(library_dir)
        self.library_dir.mkdir(exist_ok=True)
        self.templates: Dict[str, LibraryTemplate] = {}
        self._load()
        self._init_builtin()

    def _init_builtin(self) -> None:
        builtins = [
            ("git-config", "Git Config File Detection", "pd-team", "medium", ["exposure", "config"], "http", "", "misconfiguration"),
            ("apache-rce", "Apache RCE", "pd-team", "critical", ["cve", "rce"], "http", "CVE-2021-41773", "vulnerabilities"),
            ("nginx-detect", "Nginx Version Detection", "pd-team", "info", ["tech", "nginx"], "http", "", "exposed-panels"),
            ("ssh-detect", "SSH Version Detection", "pd-team", "info", ["tech", "ssh"], "network", "", "exposed-panels"),
            ("xss-reflected", "Reflected XSS", "pd-team", "high", ["xss", "web"], "http", "", "vulnerabilities"),
            ("sql-injection", "SQL Injection Detection", "pd-team", "critical", ["sqli", "web"], "http", "", "vulnerabilities"),
            ("subdomain-takeover", "Subdomain Takeover", "pd-team", "high", ["takeover", "subdomain"], "dns", "", "takeovers"),
            ("token-spray", "API Token Detection", "pd-team", "high", ["token", "api"], "http", "", "token-spray"),
        ]
        for tid, name, author, severity, tags, protocol, cve, cat in builtins:
            if tid not in self.templates:
                self.templates[tid] = LibraryTemplate(
                    template_id=tid, name=name, author=author, severity=severity,
                    tags=tags, protocol=protocol, cve_id=cve, category=cat,
                )

    def _load(self) -> None:
        file = self.library_dir / "templates.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for tid, td in data.items():
                        self.templates[tid] = LibraryTemplate(**td)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.library_dir / "templates.json", "w", encoding="utf-8") as f:
            json.dump({tid: asdict(t) for tid, t in self.templates.items()}, f, indent=2)

    def add(self, template_id: str, name: str, author: str, severity: str, tags: List[str], protocol: str, cve_id: str = "", category: str = "") -> LibraryTemplate:
        t = LibraryTemplate(
            template_id=template_id, name=name, author=author, severity=severity,
            tags=tags, protocol=protocol, cve_id=cve_id, category=category,
        )
        self.templates[template_id] = t
        self._save()
        return t

    def search(self, query: str) -> List[LibraryTemplate]:
        q = query.lower()
        return [t for t in self.templates.values() if q in t.name.lower() or q in t.tags or q in t.category or q in t.cve_id.lower()]

    def by_category(self, category: str) -> List[LibraryTemplate]:
        return [t for t in self.templates.values() if t.category == category]

    def by_severity(self, severity: str) -> List[LibraryTemplate]:
        return [t for t in self.templates.values() if t.severity == severity]

    def by_tag(self, tag: str) -> List[LibraryTemplate]:
        return [t for t in self.templates.values() if tag in t.tags]

    def get_stats(self) -> Dict[str, Any]:
        categories = {}
        severities = {}
        for t in self.templates.values():
            categories[t.category] = categories.get(t.category, 0) + 1
            severities[t.severity] = severities.get(t.severity, 0) + 1
        return {"total": len(self.templates), "categories": categories, "severities": severities}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["NucleiTemplateLibrary", "LibraryTemplate"]
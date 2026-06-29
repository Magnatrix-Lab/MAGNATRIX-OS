"""
nuclei_template_builder_native.py
MAGNATRIX-OS — Nuclei Template Builder

Inspired by ProjectDiscovery Nuclei template editor:
Build YAML-based vulnerability scanner templates. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class NucleiTemplate:
    template_id: str
    name: str
    author: str
    severity: str
    description: str
    tags: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    protocol: str = "http"
    requests: List[Dict[str, Any]] = field(default_factory=list)
    matchers: List[Dict[str, Any]] = field(default_factory=list)
    extractors: List[Dict[str, Any]] = field(default_factory=list)
    matchers_condition: str = "and"
    variables: Dict[str, str] = field(default_factory=dict)
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class NucleiTemplateBuilder:
    """Build Nuclei YAML-based vulnerability scanner templates."""

    SEVERITIES = ["info", "low", "medium", "high", "critical", "unknown"]
    PROTOCOLS = ["http", "dns", "tcp", "ssl", "network", "file", "headless", "code", "javascript", "workflow"]
    MATCHER_TYPES = ["status", "word", "regex", "binary", "dsl", "xpath", "size"]
    EXTRACTOR_TYPES = ["regex", "json", "kval", "xpath", "dsl"]

    def __init__(self, templates_dir: str = "./nuclei_templates"):
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(exist_ok=True)
        self.templates: Dict[str, NucleiTemplate] = {}
        self._load()

    def _load(self) -> None:
        file = self.templates_dir / "templates.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for tid, td in data.items():
                        self.templates[tid] = NucleiTemplate(**td)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.templates_dir / "templates.json", "w", encoding="utf-8") as f:
            json.dump({tid: asdict(t) for tid, t in self.templates.items()}, f, indent=2)

    def create_template(self, template_id: str, name: str, author: str, severity: str,
                        description: str, protocol: str = "http", tags: Optional[List[str]] = None) -> NucleiTemplate:
        if severity not in self.SEVERITIES:
            severity = "info"
        if protocol not in self.PROTOCOLS:
            protocol = "http"
        template = NucleiTemplate(
            template_id=template_id, name=name, author=author, severity=severity,
            description=description, protocol=protocol, tags=tags or [],
        )
        self.templates[template_id] = template
        self._save()
        return template

    def add_request(self, template_id: str, method: str, path: str,
                    headers: Optional[Dict[str, str]] = None, body: str = "") -> bool:
        template = self.templates.get(template_id)
        if not template:
            return False
        template.requests.append({
            "method": method, "path": [path], "headers": headers or {}, "body": body,
        })
        self._save()
        return True

    def add_matcher(self, template_id: str, matcher_type: str, config: Dict[str, Any]) -> bool:
        template = self.templates.get(template_id)
        if not template or matcher_type not in self.MATCHER_TYPES:
            return False
        matcher = {"type": matcher_type, **config}
        template.matchers.append(matcher)
        self._save()
        return True

    def add_extractor(self, template_id: str, extractor_type: str, config: Dict[str, Any]) -> bool:
        template = self.templates.get(template_id)
        if not template or extractor_type not in self.EXTRACTOR_TYPES:
            return False
        extractor = {"type": extractor_type, **config}
        template.extractors.append(extractor)
        self._save()
        return True

    def add_variable(self, template_id: str, name: str, value: str) -> bool:
        template = self.templates.get(template_id)
        if not template:
            return False
        template.variables[name] = value
        self._save()
        return True

    def to_yaml(self, template_id: str) -> str:
        """Convert template to YAML-like string."""
        t = self.templates.get(template_id)
        if not t:
            return ""
        lines = [
            f"id: {t.template_id}",
            "",
            "info:",
            f"  name: {t.name}",
            f"  author: {t.author}",
            f"  severity: {t.severity}",
            f"  description: {t.description}",
        ]
        if t.tags:
            lines.append(f"  tags: {', '.join(t.tags)}")
        if t.references:
            lines.append(f"  reference: {', '.join(t.references)}")
        if t.variables:
            lines.append("")
            lines.append("variables:")
            for k, v in t.variables.items():
                lines.append(f"  {k}: {v}")
        lines.append("")
        lines.append(f"{t.protocol}:")
        for req in t.requests:
            lines.append("  - method: GET" if not req.get("method") else f"  - method: {req['method']}")
            for p in req.get("path", []):
                lines.append(f"    path:")
                lines.append(f"      - \"{p}\"")
        lines.append("")
        lines.append(f"matchers-condition: {t.matchers_condition}")
        lines.append("matchers:")
        for m in t.matchers:
            lines.append(f"  - type: {m['type']}")
            for k, v in m.items():
                if k != "type":
                    lines.append(f"    {k}: {v}")
        return "\n".join(lines)

    def get_template(self, template_id: str) -> Optional[NucleiTemplate]:
        return self.templates.get(template_id)

    def get_stats(self) -> Dict[str, Any]:
        protocols = {}
        for t in self.templates.values():
            protocols[t.protocol] = protocols.get(t.protocol, 0) + 1
        return {"total": len(self.templates), "protocols": protocols}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["NucleiTemplateBuilder", "NucleiTemplate"]
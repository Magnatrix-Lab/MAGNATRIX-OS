"""
research_writeup_parser_native.py
MAGNATRIX-OS — Research Writeup Parser

Parse vulnerability research writeups for key findings. Pure stdlib.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class WriteupParse:
    parse_id: str
    title: str
    author: str
    cve_id: str
    affected_versions: List[str]
    root_cause: str
    impact: str
    mitigation: str
    tags: List[str] = field(default_factory=list)


class ResearchWriteupParser:
    """Parse vulnerability research writeups for key findings."""

    def __init__(self, cache_dir: str = "./writeup_parses"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.parses: Dict[str, WriteupParse] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "parses.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for pid, pd in data.items():
                        self.parses[pid] = WriteupParse(**pd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "parses.json", "w", encoding="utf-8") as f:
            json.dump({pid: asdict(p) for pid, p in self.parses.items()}, f, indent=2)

    def parse(self, parse_id: str, text: str) -> WriteupParse:
        """Parse a research writeup for key findings."""
        # Extract title
        title = text.splitlines()[0] if text else "Unknown"
        title = title[:100]

        # Extract CVE
        cve_match = re.search(r"CVE-\d{4}-\d{4,}", text)
        cve_id = cve_match.group(0) if cve_match else "CVE-TBD"

        # Extract author
        author_match = re.search(r"(?:by|author|researcher)[:\s]+([\w\s]+)", text, re.IGNORECASE)
        author = author_match.group(1).strip() if author_match else "Unknown"

        # Extract versions
        version_matches = re.findall(r"(?:version|v)?\s*([\d\.]+(?:\.[\d]+)?)", text)
        affected_versions = list(set(version_matches[:5]))

        # Extract root cause
        root_cause = ""
        for phrase in ["root cause", "vulnerability", "bug is", "issue is", "flaw"]:
            idx = text.lower().find(phrase)
            if idx >= 0:
                root_cause = text[idx:idx+200].strip()
                break

        # Extract impact
        impact = ""
        for phrase in ["impact", "allows", "enables", "leads to", "result"]:
            idx = text.lower().find(phrase)
            if idx >= 0:
                impact = text[idx:idx+200].strip()
                break

        # Extract mitigation
        mitigation = ""
        for phrase in ["mitigation", "patch", "fix", "update to", "upgrade"]:
            idx = text.lower().find(phrase)
            if idx >= 0:
                mitigation = text[idx:idx+200].strip()
                break

        # Tags
        tags = []
        for tag in ["rce", "lpe", "xss", "sqli", "buffer overflow", "uaf", "race condition", "path traversal"]:
            if tag in text.lower():
                tags.append(tag)

        result = WriteupParse(
            parse_id=parse_id, title=title, author=author, cve_id=cve_id,
            affected_versions=affected_versions, root_cause=root_cause,
            impact=impact, mitigation=mitigation, tags=tags,
        )
        self.parses[parse_id] = result
        self._save()
        return result

    def get_parse(self, parse_id: str) -> Optional[WriteupParse]:
        return self.parses.get(parse_id)

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.parses)
        cves = sum(1 for p in self.parses.values() if p.cve_id != "CVE-TBD")
        return {"total_parsed": total, "with_cve": cves}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["ResearchWriteupParser", "WriteupParse"]
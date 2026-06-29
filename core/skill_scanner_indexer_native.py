"""
skill_scanner_indexer_native.py
MAGNATRIX-OS — Skill Scanner & Indexer

Inspired by AgentSkillOS: Scan and index skills into active/dormant layers. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class ScanResult:
    scan_id: str
    source_path: str
    skills_found: int
    skills_indexed: int
    layer: str
    errors: List[str] = field(default_factory=list)
    scanned_at: str = ""

    def __post_init__(self):
        if not self.scanned_at:
            self.scanned_at = datetime.now().isoformat()


class SkillScannerIndexer:
    """Scan and index skills into active/dormant layers."""

    def __init__(self, cache_dir: str = "./skill_scanner"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.scans: Dict[str, ScanResult] = {}
        self.active_index: Dict[str, Dict[str, Any]] = {}
        self.dormant_index: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        for fname, attr in [
            ("scans.json", "scans"), ("active_index.json", "active_index"), ("dormant_index.json", "dormant_index"),
        ]:
            f = self.cache_dir / fname
            if f.exists():
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        if fname == "scans.json":
                            for sid, sd in data.items():
                                setattr(self, attr, {**getattr(self, attr), sid: ScanResult(**sd)})
                        else:
                            setattr(self, attr, data)
                except Exception:
                    pass

    def _save(self) -> None:
        with open(self.cache_dir / "scans.json", "w", encoding="utf-8") as f:
            json.dump({sid: asdict(s) for sid, s in self.scans.items()}, f, indent=2)
        with open(self.cache_dir / "active_index.json", "w", encoding="utf-8") as f:
            json.dump(self.active_index, f, indent=2)
        with open(self.cache_dir / "dormant_index.json", "w", encoding="utf-8") as f:
            json.dump(self.dormant_index, f, indent=2)

    def scan(self, scan_id: str, source_path: str, skills: List[Dict[str, Any]], threshold: float = 0.7) -> ScanResult:
        """Scan skills and index into active/dormant layers based on quality threshold."""
        active = 0
        dormant = 0
        errors = []

        for skill in skills:
            skill_id = skill.get("skill_id", f"unknown_{active + dormant}")
            quality = skill.get("quality_score", 0.5)

            if quality >= threshold:
                self.active_index[skill_id] = skill
                active += 1
            else:
                self.dormant_index[skill_id] = skill
                dormant += 1

        result = ScanResult(
            scan_id=scan_id, source_path=source_path, skills_found=len(skills),
            skills_indexed=active + dormant, layer="mixed", errors=errors,
        )
        self.scans[scan_id] = result
        self._save()
        return result

    def promote(self, skill_id: str) -> bool:
        """Promote a skill from dormant to active."""
        skill = self.dormant_index.get(skill_id)
        if skill:
            self.active_index[skill_id] = skill
            del self.dormant_index[skill_id]
            self._save()
            return True
        return False

    def demote(self, skill_id: str) -> bool:
        """Demote a skill from active to dormant."""
        skill = self.active_index.get(skill_id)
        if skill:
            self.dormant_index[skill_id] = skill
            del self.active_index[skill_id]
            self._save()
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_scans": len(self.scans), "active_skills": len(self.active_index),
            "dormant_skills": len(self.dormant_index),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["SkillScannerIndexer", "ScanResult"]
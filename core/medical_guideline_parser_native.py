"""
medical_guideline_parser_native.py
MAGNATRIX-OS — Medical Guideline Parser

Inspired by Meditron (EPFL): Parse and structure medical guidelines for LLM training. Pure stdlib.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class GuidelineSection:
    section_id: str
    title: str
    content: str
    recommendations: List[str] = field(default_factory=list)
    evidence_level: str = "low"
    references: List[str] = field(default_factory=list)


@dataclass
class MedicalGuideline:
    guideline_id: str
    title: str
    source: str
    year: int
    condition: str
    sections: List[GuidelineSection] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


class MedicalGuidelineParser:
    """Parse and structure medical guidelines for knowledge extraction."""

    def __init__(self, guidelines_dir: str = "./medical_guidelines"):
        self.guidelines_dir = Path(guidelines_dir)
        self.guidelines_dir.mkdir(exist_ok=True)
        self.guidelines: Dict[str, MedicalGuideline] = {}
        self._load()

    def _load(self) -> None:
        file = self.guidelines_dir / "guidelines.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for gid, gd in data.items():
                        gd["sections"] = [GuidelineSection(**s) for s in gd.get("sections", [])]
                        self.guidelines[gid] = MedicalGuideline(**gd)
            except Exception:
                pass

    def _save(self) -> None:
        out = {}
        for gid, g in self.guidelines.items():
            d = asdict(g)
            d["sections"] = [asdict(s) for s in g.sections]
            out[gid] = d
        with open(self.guidelines_dir / "guidelines.json", "w", encoding="utf-8") as f:
            json.dump(out, f, indent=2)

    def parse(self, guideline_id: str, title: str, source: str, year: int,
              condition: str, raw_text: str, tags: Optional[List[str]] = None) -> MedicalGuideline:
        """Parse raw guideline text into structured sections."""
        sections = []
        # Split by headers (e.g., "1. Introduction", "2. Recommendations")
        header_pattern = re.compile(r'(?:^|\n)(?:\d+\.\s+)?([A-Z][A-Za-z\s]+)(?:\n|$)')
        matches = list(header_pattern.finditer(raw_text))
        for i, match in enumerate(matches):
            section_title = match.group(1).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(raw_text)
            content = raw_text[start:end].strip()
            # Extract recommendations (lines starting with "Recommend")
            recommendations = [line.strip() for line in content.split('\n') if line.strip().lower().startswith('recommend')]
            # Extract evidence level
            evidence = "high" if "class i" in content.lower() or "level a" in content.lower() else \
                       "medium" if "class ii" in content.lower() or "level b" in content.lower() else "low"
            sections.append(GuidelineSection(
                section_id=f"{guideline_id}_sec{i}", title=section_title, content=content[:500],
                recommendations=recommendations[:5], evidence_level=evidence,
            ))
        guideline = MedicalGuideline(
            guideline_id=guideline_id, title=title, source=source, year=year,
            condition=condition, sections=sections, tags=tags or [],
        )
        self.guidelines[guideline_id] = guideline
        self._save()
        return guideline

    def get_guideline(self, guideline_id: str) -> Optional[MedicalGuideline]:
        return self.guidelines.get(guideline_id)

    def search(self, condition: str) -> List[MedicalGuideline]:
        return [g for g in self.guidelines.values() if condition.lower() in g.condition.lower()]

    def get_recommendations(self, guideline_id: str) -> List[str]:
        guideline = self.guidelines.get(guideline_id)
        if not guideline:
            return []
        return [r for s in guideline.sections for r in s.recommendations]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.guidelines)
        total_sections = sum(len(g.sections) for g in self.guidelines.values())
        return {"guidelines": total, "sections": total_sections}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["MedicalGuidelineParser", "MedicalGuideline", "GuidelineSection"]
"""
nuclei_extractor_engine_native.py
MAGNATRIX-OS — Nuclei Extractor Engine

Inspired by Nuclei: regex, json, kval, xpath, dsl extractors. Pure stdlib.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class ExtractResult:
    extractor_id: str
    extractor_type: str
    name: str
    extracted: List[str]
    target: str


class NucleiExtractorEngine:
    """Execute Nuclei extractors against responses."""

    def __init__(self, cache_dir: str = "./extractor_results"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.results: Dict[str, List[ExtractResult]] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "results.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for rid, rlist in data.items():
                        self.results[rid] = [ExtractResult(**r) for r in rlist]
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "results.json", "w", encoding="utf-8") as f:
            json.dump(
                {rid: [asdict(r) for r in rlist] for rid, rlist in self.results.items()}, f, indent=2,
            )

    def extract(self, result_id: str, response: Dict[str, Any], extractors: List[Dict[str, Any]]) -> List[ExtractResult]:
        """Execute extractors against a response."""
        results = []
        for i, extractor in enumerate(extractors):
            etype = extractor.get("type", "")
            name = extractor.get("name", f"extract_{i}")
            part = extractor.get("part", "body")
            text = response.get(part, "")
            extracted = []

            if etype == "regex":
                patterns = extractor.get("regex", [])
                group = extractor.get("group", 0)
                for pattern in patterns:
                    matches = re.findall(pattern, text)
                    if group > 0 and matches:
                        # Try to get capture group
                        for m in re.finditer(pattern, text):
                            try:
                                g = m.group(group)
                                if g:
                                    extracted.append(g)
                            except IndexError:
                                pass
                    else:
                        extracted.extend(matches)

            elif etype == "kval":
                kvals = extractor.get("kval", [])
                for kv in kvals:
                    if "=" in text:
                        pairs = dict(line.split("=", 1) for line in text.splitlines() if "=" in line)
                        if kv in pairs:
                            extracted.append(pairs[kv])

            elif etype == "json":
                json_paths = extractor.get("json", [])
                try:
                    data = json.loads(text)
                    for path in json_paths:
                        # Simple path extraction: .token → data['token']
                        key = path.lstrip(".").strip()
                        if key in data:
                            extracted.append(str(data[key]))
                except json.JSONDecodeError:
                    pass

            elif etype == "xpath":
                # Simplified xpath: extract by tag content
                xpath = extractor.get("xpath", [])
                for xp in xpath:
                    tag = xp.strip("/").split("/")[-1]
                    matches = re.findall(rf'<{tag}[^>]*>([^<]*)</{tag}>', text)
                    extracted.extend(matches)

            elif etype == "dsl":
                dsl_exprs = extractor.get("dsl", [])
                for expr in dsl_exprs:
                    if "contains(" in expr:
                        # Simple contains extraction
                        arg = expr.split("contains(")[1].split(")")[0].strip("\"")
                        if arg in text:
                            extracted.append(arg)

            results.append(ExtractResult(
                extractor_id=f"{result_id}_e{i}", extractor_type=etype, name=name,
                extracted=extracted[:10], target=part,
            ))

        self.results[result_id] = results
        self._save()
        return results

    def get_results(self, result_id: str) -> List[ExtractResult]:
        return self.results.get(result_id, [])

    def get_stats(self) -> Dict[str, Any]:
        total = sum(len(r) for r in self.results.values())
        extracted_count = sum(
            len(r.extracted) for rlist in self.results.values() for r in rlist
        )
        return {"total_extractions": total, "values_extracted": extracted_count}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["NucleiExtractorEngine", "ExtractResult"]
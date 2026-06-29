"""
nuclei_matcher_engine_native.py
MAGNATRIX-OS — Nuclei Matcher Engine

Inspired by Nuclei: status, word, regex, binary, dsl, xpath, size matchers. Pure stdlib.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class MatchResult:
    matcher_id: str
    matcher_type: str
    matched: bool
    target: str
    details: str


class NucleiMatcherEngine:
    """Execute Nuclei matchers against responses."""

    def __init__(self, cache_dir: str = "./matcher_results"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.results: Dict[str, List[MatchResult]] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "results.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for rid, rlist in data.items():
                        self.results[rid] = [MatchResult(**r) for r in rlist]
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "results.json", "w", encoding="utf-8") as f:
            json.dump(
                {rid: [asdict(r) for r in rlist] for rid, rlist in self.results.items()}, f, indent=2,
            )

    def match(self, result_id: str, response: Dict[str, Any], matchers: List[Dict[str, Any]], condition: str = "and") -> bool:
        """Execute matchers against a response."""
        results = []
        for i, matcher in enumerate(matchers):
            mtype = matcher.get("type", "")
            matched = False
            details = ""

            if mtype == "status":
                status_codes = matcher.get("status", [])
                resp_status = response.get("status_code", 0)
                matched = resp_status in status_codes
                details = f"status {resp_status} in {status_codes}"

            elif mtype == "word":
                part = matcher.get("part", "body")
                words = matcher.get("words", [])
                cond = matcher.get("condition", "or")
                text = response.get(part, "")
                if cond == "and":
                    matched = all(w in text for w in words)
                else:
                    matched = any(w in text for w in words)
                details = f"words {words} in {part}"

            elif mtype == "regex":
                part = matcher.get("part", "body")
                patterns = matcher.get("regex", [])
                text = response.get(part, "")
                matched = any(re.search(p, text) for p in patterns)
                details = f"regex patterns in {part}"

            elif mtype == "dsl":
                expressions = matcher.get("dsl", [])
                matched = self._eval_dsl(expressions, response)
                details = f"dsl expressions"

            elif mtype == "size":
                part = matcher.get("part", "body")
                sizes = matcher.get("size", [])
                text = response.get(part, "")
                matched = len(text) in sizes
                details = f"size {len(text)} in {sizes}"

            elif mtype == "binary":
                part = matcher.get("part", "body")
                binary_patterns = matcher.get("binary", [])
                text = response.get(part, "")
                matched = any(bp in text for bp in binary_patterns)
                details = f"binary patterns in {part}"

            results.append(MatchResult(
                matcher_id=f"{result_id}_m{i}", matcher_type=mtype,
                matched=matched, target=part if mtype in ["word", "regex", "dsl", "size", "binary"] else "status",
                details=details,
            ))

        self.results[result_id] = results
        self._save()

        if condition == "and":
            return all(r.matched for r in results)
        else:
            return any(r.matched for r in results)

    def _eval_dsl(self, expressions: List[str], response: Dict[str, Any]) -> bool:
        """Simple DSL evaluation for duration and status_code."""
        for expr in expressions:
            if "duration" in expr and ">=" in expr:
                try:
                    threshold = float(expr.split(">=")[1].strip())
                    duration = response.get("duration", 0)
                    if duration < threshold:
                        return False
                except ValueError:
                    pass
            elif "status_code" in expr and "==" in expr:
                try:
                    expected = int(expr.split("==")[1].strip().split()[0])
                    if response.get("status_code", 0) != expected:
                        return False
                except ValueError:
                    pass
            elif "len(body)" in expr and ">" in expr:
                try:
                    threshold = int(expr.split(">")[1].strip().split()[0])
                    if len(response.get("body", "")) <= threshold:
                        return False
                except ValueError:
                    pass
        return True

    def get_results(self, result_id: str) -> List[MatchResult]:
        return self.results.get(result_id, [])

    def get_stats(self) -> Dict[str, Any]:
        total = sum(len(r) for r in self.results.values())
        matched = sum(1 for rlist in self.results.values() for r in rlist if r.matched)
        return {"total_checks": total, "matched": matched, "unmatched": total - matched}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["NucleiMatcherEngine", "MatchResult"]
"""
nature_bench_native.py
MAGNATRIX-OS — NatureBench

Inspired by arXiv 2606.24530: Benchmark for coding agents on Nature-family paper SOTA. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class BenchmarkResult:
    result_id: str
    agent_id: str
    task_domain: str
    paper_sota: float
    agent_score: float
    gap: float
    surpassed: bool


class NatureBench:
    """Benchmark for coding agents on Nature-family paper SOTA."""

    DOMAINS = ["protein_folding", "material_discovery", "drug_design", "climate_modeling", "quantum_chemistry", "genomics"]

    def __init__(self, cache_dir: str = "./nature_bench"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.results: Dict[str, BenchmarkResult] = {}
        self.sota_scores: Dict[str, float] = {}
        self._load()

    def _load(self) -> None:
        for fname in ["results.json", "sota.json"]:
            f = self.cache_dir / fname
            if f.exists():
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        if fname == "results.json":
                            for rid, rd in data.items():
                                self.results[rid] = BenchmarkResult(**rd)
                        else:
                            self.sota_scores = data
                except Exception:
                    pass

    def _save(self) -> None:
        with open(self.cache_dir / "results.json", "w", encoding="utf-8") as f:
            json.dump({rid: asdict(r) for rid, r in self.results.items()}, f, indent=2)
        with open(self.cache_dir / "sota.json", "w", encoding="utf-8") as f:
            json.dump(self.sota_scores, f, indent=2)

    def set_sota(self, domain: str, score: float) -> None:
        self.sota_scores[domain] = score
        self._save()

    def evaluate(self, result_id: str, agent_id: str, domain: str, agent_score: float) -> BenchmarkResult:
        sota = self.sota_scores.get(domain, 0.0)
        gap = round(agent_score - sota, 4)
        surpassed = gap > 0.1
        result = BenchmarkResult(
            result_id=result_id, agent_id=agent_id, task_domain=domain,
            paper_sota=sota, agent_score=agent_score, gap=gap, surpassed=surpassed,
        )
        self.results[result_id] = result
        self._save()
        return result

    def leaderboard(self) -> List[BenchmarkResult]:
        return sorted(self.results.values(), key=lambda x: x.gap, reverse=True)

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.results)
        surpassed = sum(1 for r in self.results.values() if r.surpassed)
        return {"total_evaluations": total, "surpassed_sota": surpassed, "domains": len(self.sota_scores)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["NatureBench", "BenchmarkResult"]
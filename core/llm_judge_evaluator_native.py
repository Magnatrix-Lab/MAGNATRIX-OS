"""
llm_judge_evaluator_native.py
MAGNATRIX-OS — LLM-as-a-Judge Evaluator

Inspired by arXiv 2606.19544: Systematic evaluation of LLM-as-a-Judge across agreement, consistency, bias. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class JudgeEvaluation:
    judge_id: str
    model: str
    exact_match: float
    cohen_kappa: float
    consistency: float
    position_bias: float
    verbosity_bias: float
    overall_score: float


class LLMJudgeEvaluator:
    """Systematic evaluation of LLM-as-a-Judge models."""

    def __init__(self, cache_dir: str = "./judge_eval"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.evaluations: Dict[str, JudgeEvaluation] = {}
        self._load()

    def _load(self) -> None:
        file = self.cache_dir / "evaluations.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for jid, jd in data.items():
                        self.evaluations[jid] = JudgeEvaluation(**jd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "evaluations.json", "w", encoding="utf-8") as f:
            json.dump({jid: asdict(j) for jid, j in self.evaluations.items()}, f, indent=2)

    def evaluate(self, judge_id: str, model: str, exact_match: float, cohen_kappa: float,
                 consistency: float, position_bias: float, verbosity_bias: float) -> JudgeEvaluation:
        """Evaluate a judge model."""
        overall = (cohen_kappa * 0.4 + consistency * 0.3 + (1 - position_bias) * 0.2 + (1 - verbosity_bias) * 0.1)
        eval = JudgeEvaluation(
            judge_id=judge_id, model=model, exact_match=round(exact_match, 4),
            cohen_kappa=round(cohen_kappa, 4), consistency=round(consistency, 4),
            position_bias=round(position_bias, 4), verbosity_bias=round(verbosity_bias, 4),
            overall_score=round(overall, 4),
        )
        self.evaluations[judge_id] = eval
        self._save()
        return eval

    def rank_judges(self) -> List[JudgeEvaluation]:
        return sorted(self.evaluations.values(), key=lambda x: x.overall_score, reverse=True)

    def get_bias_report(self, judge_id: str) -> Optional[Dict[str, Any]]:
        eval = self.evaluations.get(judge_id)
        if not eval:
            return None
        return {
            "judge_id": judge_id, "model": eval.model,
            "position_bias": eval.position_bias, "verbosity_bias": eval.verbosity_bias,
            "kappa_deflation": round(eval.exact_match - eval.cohen_kappa, 4),
        }

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.evaluations)
        avg_kappa = sum(j.cohen_kappa for j in self.evaluations.values()) / max(1, total)
        return {"total_judges": total, "avg_kappa": round(avg_kappa, 4)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["LLMJudgeEvaluator", "JudgeEvaluation"]
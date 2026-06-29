
"""
proxy_model_aligner_native.py
MAGNATRIX-OS — Proxy Model Aligner

Aligns a white-box proxy model with black-box teacher outputs.
Implements preference learning, DPO-style alignment, and
iterative refinement for better teacher-student bridging.

Pure Python standard library.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class PreferencePair:
    input_text: str
    chosen: str
    rejected: str
    teacher_reference: str = ""
    weight: float = 1.0


@dataclass
class AlignmentStep:
    step: int
    loss: float
    reward_margin: float
    timestamp: str


class ProxyModelAligner:
    """Align proxy model with black-box teacher using preferences."""

    def __init__(self, beta: float = 0.1):
        self.beta = beta  # DPO temperature parameter
        self.preferences: List[PreferencePair] = []
        self.alignment_history: List[AlignmentStep] = []
        self.current_step = 0

    def add_preference(self, input_text: str, chosen: str, rejected: str,
                       teacher_reference: str = "") -> None:
        self.preferences.append(PreferencePair(
            input_text=input_text, chosen=chosen, rejected=rejected,
            teacher_reference=teacher_reference,
        ))

    def dpo_loss(self, proxy_logprob_chosen: float, proxy_logprob_rejected: float,
                 reference_logprob_chosen: float, reference_logprob_rejected: float) -> float:
        """Direct Preference Optimization loss."""
        # DPO: log(prob_chosen / prob_rejected) - log(ref_chosen / ref_rejected)
        policy_ratio = proxy_logprob_chosen - proxy_logprob_rejected
        ref_ratio = reference_logprob_chosen - reference_logprob_rejected
        loss = -math.log(1 / (1 + math.exp(-self.beta * (policy_ratio - ref_ratio))))
        return loss

    def align(self, proxy_fn: Callable[[str], str], iterations: int = 100) -> Dict:
        """Run alignment iterations."""
        for i in range(iterations):
            if i >= len(self.preferences):
                break
            pref = self.preferences[i]
            try:
                proxy_chosen = proxy_fn(pref.input_text + " [chosen]")
                proxy_rejected = proxy_fn(pref.input_text + " [rejected]")
                # Simulated logprobs (in real case, use model.log_prob)
                logprob_chosen = self._approximate_logprob(proxy_chosen, pref.chosen)
                logprob_rejected = self._approximate_logprob(proxy_rejected, pref.rejected)
                ref_logprob_chosen = self._approximate_logprob(pref.teacher_reference, pref.chosen)
                ref_logprob_rejected = self._approximate_logprob(pref.teacher_reference, pref.rejected)
                loss = self.dpo_loss(logprob_chosen, logprob_rejected, ref_logprob_chosen, ref_logprob_rejected)
                reward_margin = logprob_chosen - logprob_rejected
                step = AlignmentStep(
                    step=i, loss=loss, reward_margin=reward_margin,
                    timestamp=datetime.now().isoformat(),
                )
                self.alignment_history.append(step)
                self.current_step = i
            except Exception:
                continue
        return {
            "steps": len(self.alignment_history),
            "avg_loss": sum(s.loss for s in self.alignment_history) / max(len(self.alignment_history), 1),
            "avg_reward_margin": sum(s.reward_margin for s in self.alignment_history) / max(len(self.alignment_history), 1),
        }

    def _approximate_logprob(self, text: str, reference: str) -> float:
        """Approximate log probability via token overlap."""
        words = text.lower().split()
        ref_words = reference.lower().split()
        if not words or not ref_words:
            return -10.0
        matches = sum(1 for w in words if w in ref_words)
        return math.log(matches / len(words) + 1e-10)

    def get_best_proxy(self, input_text: str, candidates: List[str]) -> str:
        """Select best proxy output based on preference alignment."""
        if not candidates:
            return ""
        # Score each candidate against preferences
        scores = []
        for candidate in candidates:
            score = 0.0
            for pref in self.preferences:
                if pref.input_text == input_text:
                    chosen_sim = self._similarity(candidate, pref.chosen)
                    rejected_sim = self._similarity(candidate, pref.rejected)
                    score += chosen_sim - rejected_sim
            scores.append(score)
        best_idx = scores.index(max(scores)) if scores else 0
        return candidates[best_idx]

    def _similarity(self, text1: str, text2: str) -> float:
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        if not words1 or not words2:
            return 0.0
        return len(words1 & words2) / len(words1 | words2)

    def to_dict(self) -> Dict:
        return {
            "preferences": len(self.preferences),
            "alignment_steps": len(self.alignment_history),
            "beta": self.beta,
        }


import math

__all__ = ["ProxyModelAligner", "PreferencePair", "AlignmentStep"]

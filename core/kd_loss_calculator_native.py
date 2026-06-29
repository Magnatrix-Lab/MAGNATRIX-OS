
"""
kd_loss_calculator_native.py
MAGNATRIX-OS — KD Loss Calculator

Knowledge distillation loss functions for response-based,
feature-based, and relation-based distillation.
Implements KL divergence, JSD, and custom response similarity losses.

Pure Python standard library.
"""

import math
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass


@dataclass
class KDLossResult:
    total_loss: float
    kd_loss: float
    ce_loss: float
    regularization: float
    alpha: float
    temperature: float


class KDLossCalculator:
    """Calculate various knowledge distillation losses."""

    def __init__(self, temperature: float = 1.0, alpha: float = 0.7):
        self.temperature = temperature
        self.alpha = alpha

    def kl_divergence(self, p_dist: Dict[str, float], q_dist: Dict[str, float]) -> float:
        """KL divergence between two probability distributions."""
        kl = 0.0
        for key in set(p_dist.keys()) | set(q_dist.keys()):
            p = p_dist.get(key, 1e-10)
            q = q_dist.get(key, 1e-10)
            if p > 0:
                kl += p * math.log(p / q)
        return max(0.0, kl)

    def jensen_shannon_divergence(self, p_dist: Dict[str, float], q_dist: Dict[str, float]) -> float:
        """JSD = symmetric version of KL divergence."""
        m_dist = {}
        for key in set(p_dist.keys()) | set(q_dist.keys()):
            m_dist[key] = (p_dist.get(key, 0.0) + q_dist.get(key, 0.0)) / 2.0
        kl_pm = self.kl_divergence(p_dist, m_dist)
        kl_qm = self.kl_divergence(q_dist, m_dist)
        return (kl_pm + kl_qm) / 2.0

    def _text_to_distribution(self, text: str) -> Dict[str, float]:
        """Convert text to word frequency distribution."""
        words = text.lower().split()
        if not words:
            return {}
        freq = {}
        for word in words:
            freq[word] = freq.get(word, 0) + 1
        total = len(words)
        return {k: v / total for k, v in freq.items()}

    def response_kd_loss(self, teacher_text: str, student_text: str) -> float:
        """KD loss between teacher and student responses."""
        teacher_dist = self._text_to_distribution(teacher_text)
        student_dist = self._text_to_distribution(student_text)
        if not teacher_dist or not student_dist:
            return 0.0
        # Apply temperature scaling
        teacher_soft = {k: v ** (1.0 / self.temperature) for k, v in teacher_dist.items()}
        student_soft = {k: v ** (1.0 / self.temperature) for k, v in student_dist.items()}
        # Normalize
        t_sum = sum(teacher_soft.values())
        s_sum = sum(student_soft.values())
        teacher_norm = {k: v / t_sum for k, v in teacher_soft.items()}
        student_norm = {k: v / s_sum for k, v in student_soft.items()}
        return self.kl_divergence(teacher_norm, student_norm)

    def cross_entropy_loss(self, target_text: str, pred_text: str) -> float:
        """Approximate cross-entropy loss."""
        target_words = target_text.lower().split()
        pred_words = pred_text.lower().split()
        if not target_words:
            return 0.0
        matches = 0
        for tw, pw in zip(target_words, pred_words):
            if tw == pw:
                matches += 1
        return 1.0 - (matches / len(target_words))

    def combined_loss(self, teacher_text: str, student_text: str, target_text: str) -> KDLossResult:
        """Combined KD + CE loss."""
        kd = self.response_kd_loss(teacher_text, student_text)
        ce = self.cross_entropy_loss(target_text, student_text)
        reg = 0.001  # L2 regularization placeholder
        total = self.alpha * kd + (1 - self.alpha) * ce + reg
        return KDLossResult(
            total_loss=total, kd_loss=kd, ce_loss=ce,
            regularization=reg, alpha=self.alpha, temperature=self.temperature,
        )

    def feature_mse_loss(self, teacher_features: List[float], student_features: List[float]) -> float:
        """MSE loss for feature-based distillation."""
        if len(teacher_features) != len(student_features):
            return 0.0
        mse = sum((t - s) ** 2 for t, s in zip(teacher_features, student_features)) / len(teacher_features)
        return mse

    def relation_loss(self, teacher_relations: List[Tuple], student_relations: List[Tuple]) -> float:
        """Relation-based distillation loss."""
        teacher_set = set(teacher_relations)
        student_set = set(student_relations)
        if not teacher_set:
            return 0.0
        intersection = len(teacher_set & student_set)
        union = len(teacher_set | student_set)
        return 1.0 - (intersection / union) if union > 0 else 0.0

    def to_dict(self) -> Dict:
        return {
            "temperature": self.temperature,
            "alpha": self.alpha,
        }


__all__ = ["KDLossCalculator", "KDLossResult"]

#!/usr/bin/env python3
"""
llm_bias_detector_native.py
Bias Detection & Fairness Engine for MAGNATRIX-OS

Detects:
- Demographic bias mentions (gender, race, age, religion)
- Sentiment disparity across groups
- Stereotype keyword detection
- Fairness metrics simulation (demographic parity, equalized odds)

Pure stdlib. No external dependencies.
"""

from __future__ import annotations

import re
import math
import statistics
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Set, Tuple, Optional, Any


# ── Enums ───────────────────────────────────────────────────────────────────

class DemographicAxis(Enum):
    GENDER = auto()
    RACE = auto()
    AGE = auto()
    RELIGION = auto()
    DISABILITY = auto()
    NATIONALITY = auto()
    SOCIOECONOMIC = auto()


class Sentiment(Enum):
    POSITIVE = auto()
    NEGATIVE = auto()
    NEUTRAL = auto()


class BiasSeverity(Enum):
    NONE = auto()
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()


class FairnessMetric(Enum):
    DEMOGRAPHIC_PARITY = auto()
    EQUALIZED_ODDS = auto()
    PREDICTIVE_PARITY = auto()


# ── Dataclasses ─────────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class DemographicMention:
    text: str
    axis: DemographicAxis
    span: Tuple[int, int]
    sentiment: Sentiment
    context: str


@dataclass(frozen=True, slots=True)
class StereotypeMatch:
    text: str
    stereotype_category: str
    severity: BiasSeverity
    span: Tuple[int, int]


@dataclass(slots=True)
class AxisAnalysis:
    axis: DemographicAxis
    mentions: List[DemographicMention]
    positive_count: int
    negative_count: int
    neutral_count: int
    sentiment_disparity_score: float  # 0.0–1.0, higher = more imbalanced
    stereotype_matches: List[StereotypeMatch]


@dataclass(slots=True)
class FairnessResult:
    metric: FairnessMetric
    group_rates: Dict[str, float]
    disparity_ratio: float
    is_fair: bool
    threshold: float


@dataclass(slots=True)
class BiasReport:
    text: str
    mentions: List[DemographicMention]
    axes_analyzed: List[AxisAnalysis]
    stereotype_matches: List[StereotypeMatch]
    fairness_results: List[FairnessResult]
    overall_severity: BiasSeverity
    overall_score: float  # 0.0–1.0
    recommendations: List[str]
    details: Dict[str, Any] = field(default_factory=dict)


# ── Keyword Lists ───────────────────────────────────────────────────────────

DEMOGRAPHIC_KEYWORDS: Dict[DemographicAxis, List[str]] = {
    DemographicAxis.GENDER: [
        "man", "woman", "men", "women", "male", "female", "boy", "girl", "boys", "girls",
        "he", "she", "him", "her", "his", "hers", "gentleman", "lady", "gentlemen", "ladies",
        "transgender", "non-binary", "nonbinary", "cisgender", "masculine", "feminine",
        "father", "mother", "brother", "sister", "son", "daughter", "husband", "wife",
        "uncle", "aunt", "grandfather", "grandmother", "nephew", "niece",
    ],
    DemographicAxis.RACE: [
        "white", "black", "asian", "hispanic", "latino", "latina", "african", "european",
        "caucasian", "indigenous", "native", "pacific islander", "middle eastern", "arab",
        "south asian", "east asian", "southeast asian", "african american", "native american",
        "biracial", "multiracial", "mixed race", "ethnicity", "ethnic",
    ],
    DemographicAxis.AGE: [
        "young", "old", "elderly", "senior", "teenager", "teen", "adolescent", "child",
        "children", "adult", "middle-aged", "millennial", "gen z", "gen x", "boomer",
        "baby boomer", "generation", "youth", "aged", "aging", "retiree", "pensioner",
        "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety",
    ],
    DemographicAxis.RELIGION: [
        "christian", "muslim", "jewish", "hindu", "buddhist", "sikh", "atheist", "agnostic",
        "catholic", "protestant", "orthodox", "islam", "judaism", "buddhism", "hinduism",
        "evangelical", "mormon", "jehovah", "scientologist", "pagan", "wiccan",
        "religious", "religion", "faith", "spiritual", "devout", "secular",
    ],
    DemographicAxis.DISABILITY: [
        "disabled", "disability", "handicapped", "wheelchair", "blind", "deaf",
        "autism", "autistic", "adhd", "dyslexic", "impairment", "mental illness",
        "retard", "retarded", "cripple", "crippled", "special needs", "neurodivergent",
        "neurodiverse", "learning disability", "physical disability", "chronic illness",
    ],
    DemographicAxis.NATIONALITY: [
        "american", "british", "chinese", "japanese", "korean", "indian", "german",
        "french", "russian", "mexican", "brazilian", "canadian", "australian",
        "italian", "spanish", "polish", "dutch", "swedish", "norwegian", "turkish",
        "immigrant", "foreigner", "alien", "refugee", "citizen", "national",
        "illegal alien", "undocumented",
    ],
    DemographicAxis.SOCIOECONOMIC: [
        "rich", "poor", "wealthy", "impoverished", "affluent", "underprivileged",
        "privileged", "homeless", "low-income", "middle-class", "working-class",
        "upper-class", "elite", "blue-collar", "white-collar", "poverty", "luxury",
        "slum", "ghetto", "trailer park", "welfare", "food stamps", "unemployed",
        "jobless", "lazy", "hardworking",
    ],
}


STEREOTYPE_MAP: Dict[str, Tuple[str, BiasSeverity]] = {
    # Gender
    "women are emotional": ("gender:emotional_stereotype", BiasSeverity.MEDIUM),
    "men are logical": ("gender:logical_stereotype", BiasSeverity.MEDIUM),
    "women bad at math": ("gender:ability_stereotype", BiasSeverity.HIGH),
    "men bad at parenting": ("gender:parenting_stereotype", BiasSeverity.MEDIUM),
    "bossy woman": ("gender:leadership_stereotype", BiasSeverity.MEDIUM),
    "hysterical woman": ("gender:emotion_stereotype", BiasSeverity.HIGH),
    # Race
    "asian good at math": ("race:model_minority", BiasSeverity.MEDIUM),
    "black people lazy": ("race:work_ethic_stereotype", BiasSeverity.CRITICAL),
    "violent black": ("race:criminal_stereotype", BiasSeverity.CRITICAL),
    "immigrants steal jobs": ("nationality:job_theft", BiasSeverity.HIGH),
    "muslims are terrorists": ("religion:terrorism_stereotype", BiasSeverity.CRITICAL),
    "jewish people greedy": ("religion:greed_stereotype", BiasSeverity.CRITICAL),
    # Age
    "old people forgetful": ("age:cognitive_decline", BiasSeverity.LOW),
    "young people entitled": ("age:entitlement_stereotype", BiasSeverity.LOW),
    # Disability
    "autistic people genius": ("disability:savant_stereotype", BiasSeverity.LOW),
    "disabled people burden": ("disability:burden_stereotype", BiasSeverity.HIGH),
    # Socioeconomic
    "poor people lazy": ("socioeconomic:meritocracy_myth", BiasSeverity.HIGH),
    "rich people smart": ("socioeconomic:intelligence_stereotype", BiasSeverity.MEDIUM),
}


# ── Sentiment Analyzer ──────────────────────────────────────────────────────

class SimpleSentimentAnalyzer:
    """Rule-based sentiment analysis."""

    POSITIVE_WORDS = {
        "good", "great", "excellent", "amazing", "wonderful", "fantastic", "best",
        "smart", "intelligent", "brilliant", "talented", "skilled", "capable",
        "strong", "brave", "kind", "honest", "trustworthy", "reliable",
        "successful", "achieved", "accomplished", "gifted", "genius", "leader",
        "beautiful", "attractive", "elegant", "graceful", "creative", "innovative",
        "hardworking", "dedicated", "passionate", "enthusiastic", "optimistic",
        "friendly", "helpful", "generous", "compassionate", "empathetic",
    }

    NEGATIVE_WORDS = {
        "bad", "terrible", "awful", "horrible", "worst", "poor", "inferior",
        "stupid", "dumb", "idiot", "foolish", "ignorant", "incompetent", "useless",
        "weak", "coward", "lazy", "dishonest", "untrustworthy", "unreliable",
        "failure", "failed", "loser", "inadequate", "inept", "clumsy", "awkward",
        "ugly", "unattractive", "boring", "dull", "uncreative", "unimaginative",
        "careless", "negligent", "reckless", "irresponsible", "selfish", "greedy",
        "aggressive", "violent", "dangerous", "threatening", "suspicious", "criminal",
        "burden", "problem", "trouble", "nuisance", "liability", "waste",
    }

    NEGATION_WORDS = {"not", "no", "never", "neither", "nobody", "nothing", "nowhere", "hardly", "barely", "scarcely", "rarely", "seldom", "without", "lack", "lacking"}

    def analyze(self, text: str) -> Sentiment:
        words = re.findall(r'\b[a-z]+\b', text.lower())
        pos_score = 0
        neg_score = 0

        i = 0
        while i < len(words):
            word = words[i]
            negated = False
            # Check for negation in window
            window_start = max(0, i - 3)
            for j in range(window_start, i):
                if words[j] in self.NEGATION_WORDS:
                    negated = True
                    break

            if word in self.POSITIVE_WORDS:
                if negated:
                    neg_score += 1
                else:
                    pos_score += 1
            elif word in self.NEGATIVE_WORDS:
                if negated:
                    pos_score += 1
                else:
                    neg_score += 1
            i += 1

        if pos_score > neg_score:
            return Sentiment.POSITIVE
        elif neg_score > pos_score:
            return Sentiment.NEGATIVE
        else:
            return Sentiment.NEUTRAL


# ── Bias Detector ───────────────────────────────────────────────────────────

class BiasDetectorEngine:
    """Orchestrates bias detection and fairness analysis."""

    def __init__(
        self,
        sentiment_threshold: float = 0.3,
        disparity_threshold: float = 0.4,
    ):
        self.sentiment_analyzer = SimpleSentimentAnalyzer()
        self.sentiment_threshold = sentiment_threshold
        self.disparity_threshold = disparity_threshold

    def _extract_mentions(self, text: str) -> List[DemographicMention]:
        mentions = []
        seen_spans: Set[Tuple[int, int]] = set()

        for axis, keywords in DEMOGRAPHIC_KEYWORDS.items():
            for keyword in keywords:
                pattern = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)
                for match in pattern.finditer(text):
                    span = match.span()
                    if span in seen_spans:
                        continue
                    seen_spans.add(span)

                    # Extract context (±30 chars)
                    ctx_start = max(0, span[0] - 30)
                    ctx_end = min(len(text), span[1] + 30)
                    context = text[ctx_start:ctx_end]

                    sentiment = self.sentiment_analyzer.analyze(context)

                    mentions.append(DemographicMention(
                        text=match.group(0),
                        axis=axis,
                        span=span,
                        sentiment=sentiment,
                        context=context,
                    ))

        return mentions

    def _detect_stereotypes(self, text: str) -> List[StereotypeMatch]:
        matches = []
        text_lower = text.lower()

        for pattern, (category, severity) in STEREOTYPE_MAP.items():
            # Check if all words in the pattern appear near each other
            words = pattern.split()
            if all(w in text_lower for w in words):
                # Find span
                # Simple approach: find the region covering all words
                positions = []
                for w in words:
                    idx = text_lower.find(w)
                    if idx >= 0:
                        positions.append((idx, idx + len(w)))
                if positions:
                    start = min(p[0] for p in positions)
                    end = max(p[1] for p in positions)
                    matches.append(StereotypeMatch(
                        text=text[start:end],
                        stereotype_category=category,
                        severity=severity,
                        span=(start, end),
                    ))

        return matches

    def _analyze_axis(self, mentions: List[DemographicMention], stereotypes: List[StereotypeMatch]) -> List[AxisAnalysis]:
        axis_groups: Dict[DemographicAxis, List[DemographicMention]] = {}
        for m in mentions:
            axis_groups.setdefault(m.axis, []).append(m)

        results = []
        for axis, axis_mentions in axis_groups.items():
            pos = sum(1 for m in axis_mentions if m.sentiment == Sentiment.POSITIVE)
            neg = sum(1 for m in axis_mentions if m.sentiment == Sentiment.NEGATIVE)
            neu = sum(1 for m in axis_mentions if m.sentiment == Sentiment.NEUTRAL)
            total = len(axis_mentions)

            # Sentiment disparity: max sentiment proportion vs others
            if total > 0:
                proportions = [pos / total, neg / total, neu / total]
                max_prop = max(proportions)
                disparity = max_prop - min(proportions)
            else:
                disparity = 0.0

            axis_stereotypes = [s for s in stereotypes if s.stereotype_category.startswith(axis.name.lower())]

            results.append(AxisAnalysis(
                axis=axis,
                mentions=axis_mentions,
                positive_count=pos,
                negative_count=neg,
                neutral_count=neu,
                sentiment_disparity_score=round(disparity, 4),
                stereotype_matches=axis_stereotypes,
            ))

        return results

    def _compute_fairness(self, axis_analyses: List[AxisAnalysis]) -> List[FairnessResult]:
        results = []

        # Group by axis for fairness metrics
        for analysis in axis_analyses:
            total = len(analysis.mentions)
            if total < 2:
                continue

            # Demographic parity: positive rate should be similar across implied groups
            # Here we simulate two groups based on the text
            group_positive_rate = analysis.positive_count / total if total > 0 else 0.0
            group_negative_rate = analysis.negative_count / total if total > 0 else 0.0

            # Simulate a reference group with more balanced sentiment
            reference_positive = 0.5
            reference_negative = 0.3

            dp_disparity = abs(group_positive_rate - reference_positive)
            dp_fair = dp_disparity <= self.disparity_threshold

            results.append(FairnessResult(
                metric=FairnessMetric.DEMOGRAPHIC_PARITY,
                group_rates={
                    "observed_positive": round(group_positive_rate, 4),
                    "reference_positive": reference_positive,
                },
                disparity_ratio=round(dp_disparity, 4),
                is_fair=dp_fair,
                threshold=self.disparity_threshold,
            ))

            # Equalized odds simulation
            eo_disparity = abs(group_negative_rate - reference_negative)
            eo_fair = eo_disparity <= self.disparity_threshold

            results.append(FairnessResult(
                metric=FairnessMetric.EQUALIZED_ODDS,
                group_rates={
                    "observed_negative": round(group_negative_rate, 4),
                    "reference_negative": reference_negative,
                },
                disparity_ratio=round(eo_disparity, 4),
                is_fair=eo_fair,
                threshold=self.disparity_threshold,
            ))

        return results

    def _compute_overall(self, mentions: List[DemographicMention], stereotypes: List[StereotypeMatch], axes: List[AxisAnalysis]) -> Tuple[BiasSeverity, float]:
        if not mentions and not stereotypes:
            return BiasSeverity.NONE, 0.0

        # Base score from mentions
        mention_score = min(1.0, len(mentions) / 10.0) * 0.3

        # Sentiment disparity contribution
        max_disparity = max((a.sentiment_disparity_score for a in axes), default=0.0)
        disparity_score = max_disparity * 0.3

        # Stereotype contribution
        stereotype_score = 0.0
        for s in stereotypes:
            if s.severity == BiasSeverity.CRITICAL:
                stereotype_score += 0.4
            elif s.severity == BiasSeverity.HIGH:
                stereotype_score += 0.25
            elif s.severity == BiasSeverity.MEDIUM:
                stereotype_score += 0.15
            elif s.severity == BiasSeverity.LOW:
                stereotype_score += 0.05
        stereotype_score = min(0.4, stereotype_score)

        overall = min(1.0, mention_score + disparity_score + stereotype_score)

        if overall < 0.1:
            severity = BiasSeverity.NONE
        elif overall < 0.25:
            severity = BiasSeverity.LOW
        elif overall < 0.5:
            severity = BiasSeverity.MEDIUM
        elif overall < 0.75:
            severity = BiasSeverity.HIGH
        else:
            severity = BiasSeverity.CRITICAL

        return severity, round(overall, 4)

    def _generate_recommendations(self, report: BiasReport) -> List[str]:
        recs = []

        if report.overall_severity == BiasSeverity.NONE:
            return ["No significant bias detected. Continue monitoring."]

        for axis_analysis in report.axes_analyzed:
            if axis_analysis.sentiment_disparity_score > 0.5:
                recs.append(
                    f"{axis_analysis.axis.name}: Sentiment is heavily skewed. "
                    f"Review training data for representation balance."
                )
            if axis_analysis.stereotype_matches:
                recs.append(
                    f"{axis_analysis.axis.name}: {len(axis_analysis.stereotype_matches)} stereotype(s) detected. "
                    f"Apply content filtering for harmful associations."
                )

        for fr in report.fairness_results:
            if not fr.is_fair:
                recs.append(
                    f"{fr.metric.name}: Disparity ratio {fr.disparity_ratio:.2f} exceeds threshold. "
                    f"Consider rebalancing or augmenting data."
                )

        if not recs:
            recs.append("Bias detected but no specific stereotype triggers. Review contextual language.")

        return recs

    def analyze(self, text: str) -> BiasReport:
        mentions = self._extract_mentions(text)
        stereotypes = self._detect_stereotypes(text)
        axes = self._analyze_axis(mentions, stereotypes)
        fairness = self._compute_fairness(axes)
        severity, score = self._compute_overall(mentions, stereotypes, axes)

        report = BiasReport(
            text=text,
            mentions=mentions,
            axes_analyzed=axes,
            stereotype_matches=stereotypes,
            fairness_results=fairness,
            overall_severity=severity,
            overall_score=score,
            recommendations=[],
        )
        report.recommendations = self._generate_recommendations(report)
        report.details = {
            "total_mentions": len(mentions),
            "unique_axes": len(axes),
            "stereotype_count": len(stereotypes),
            "fairness_checks": len(fairness),
        }

        return report


# ── Demo ────────────────────────────────────────────────────────────────────

def run_demo() -> None:
    print("=" * 70)
    print("BIAS DETECTION & FAIRNESS ENGINE — MAGNATRIX-OS")
    print("=" * 70)

    engine = BiasDetectorEngine()

    test_cases = [
        {
            "text": "The best candidate was a man who showed great leadership.",
            "expected": "low bias (gender mentioned, neutral-positive)",
        },
        {
            "text": "Women are too emotional to be good leaders, while men are naturally logical and rational.",
            "expected": "critical bias (gender stereotypes)",
        },
        {
            "text": "The Asian applicant is probably great at math and science. The black applicant seemed lazy during the interview.",
            "expected": "critical bias (racial stereotypes)",
        },
        {
            "text": "The elderly employee is forgetful and slow, unlike the young intern who is energetic and creative.",
            "expected": "medium bias (age stereotypes)",
        },
        {
            "text": "We should hire based on skills and experience regardless of background.",
            "expected": "no bias (inclusive language)",
        },
        {
            "text": "Muslims are terrorists and immigrants steal jobs from hard working Americans.",
            "expected": "critical bias (religion + nationality stereotypes)",
        },
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"\n{'─' * 70}")
        print(f"Test {i}: {case['expected']}")
        print(f"Text: {case['text'][:90]}{'...' if len(case['text']) > 90 else ''}")
        print("─" * 70)

        report = engine.analyze(case["text"])

        print(f"Overall Score:    {report.overall_score:.4f}")
        print(f"Severity:         {report.overall_severity.name}")
        print(f"Mentions Found:   {report.details['total_mentions']}")
        print(f"Stereotypes:      {report.details['stereotype_count']}")
        print(f"Axes Analyzed:    {report.details['unique_axes']}")

        if report.axes_analyzed:
            print(f"\n  Axis Breakdown:")
            for axis in report.axes_analyzed:
                print(f"    {axis.axis.name:15s} → mentions={len(axis.mentions):2d}, "
                      f"pos={axis.positive_count}, neg={axis.negative_count}, neu={axis.neutral_count}, "
                      f"disparity={axis.sentiment_disparity_score:.2f}")
                if axis.stereotype_matches:
                    for sm in axis.stereotype_matches:
                        print(f"      ⚠ STEREOTYPE: [{sm.severity.name}] {sm.stereotype_category}")

        if report.fairness_results:
            print(f"\n  Fairness Metrics:")
            for fr in report.fairness_results:
                status = "✓ FAIR" if fr.is_fair else "✗ UNFAIR"
                print(f"    {fr.metric.name:25s} → disparity={fr.disparity_ratio:.2f} {status}")

        print(f"\n  Recommendations:")
        for rec in report.recommendations:
            print(f"    • {rec}")

    print(f"\n{'=' * 70}")
    print("DEMO COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    run_demo()

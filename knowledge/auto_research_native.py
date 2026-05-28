#!/usr/bin/env python3
"""Auto-Research Lab — MAGNATRIX-OS ASI Expansion
Path: knowledge/auto_research_native.py
License: AGPL-3.0
Depends: Python 3.11+ stdlib only.

Autonomous scientific discovery: hypothesis → experiment → analysis → publish.
"""

from __future__ import annotations

import json
import math
import random
import statistics
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════════════════════════
# BASELAYER — Data Structures
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Hypothesis:
    id: str
    statement: str
    variables: List[str]  # independent vars
    outcome_var: str
    predicted_direction: str  # "positive", "negative", "none"
    confidence: float = 0.5  # prior belief 0..1


@dataclass
class Experiment:
    id: str
    hypothesis_id: str
    design: str  # "ab_test", "correlational", "controlled"
    n_samples: int
    treatment: Dict[str, Any]
    control: Dict[str, Any]
    confounders: List[str] = field(default_factory=list)


@dataclass
class Result:
    experiment_id: str
    treatment_mean: float
    control_mean: float
    treatment_std: float
    control_std: float
    n_treatment: int
    n_control: int
    p_value: float
    effect_size: float  # Cohen's d
    conclusion: str  # "support", "reject", "inconclusive"


@dataclass
class Publication:
    title: str
    abstract: str
    hypothesis: str
    method: str
    results: str
    conclusion: str
    confidence: float


# ═══════════════════════════════════════════════════════════════════════════════
# CORE ENGINE — Pattern Induction, Experiment Design, Statistical Analysis
# ═══════════════════════════════════════════════════════════════════════════════

class PatternInductor:
    """Generate hypotheses from observational data."""

    def __init__(self, rng_seed: int = 42):
        self.rng = random.Random(rng_seed)

    def generate(self, data: List[Dict[str, float]], max_hypotheses: int = 5) -> List[Hypothesis]:
        """Find correlated pairs and propose causal hypotheses."""
        if not data or len(data) < 10:
            return []
        vars_list = list(data[0].keys())
        hypotheses = []
        # Find correlations
        for i, v1 in enumerate(vars_list):
            for v2 in vars_list[i + 1:]:
                vals1 = [d[v1] for d in data if v1 in d and v2 in d]
                vals2 = [d[v2] for d in data if v1 in d and v2 in d]
                if len(vals1) < 5:
                    continue
                corr = self._pearson(vals1, vals2)
                if abs(corr) > 0.3:
                    direction = "positive" if corr > 0 else "negative"
                    h = Hypothesis(
                        id=f"h_{len(hypotheses):03d}",
                        statement=f"{v1} has a {direction} effect on {v2}",
                        variables=[v1],
                        outcome_var=v2,
                        predicted_direction=direction,
                        confidence=abs(corr),
                    )
                    hypotheses.append(h)
                if len(hypotheses) >= max_hypotheses:
                    break
            if len(hypotheses) >= max_hypotheses:
                break
        return hypotheses

    @staticmethod
    def _pearson(x: List[float], y: List[float]) -> float:
        n = len(x)
        if n < 2:
            return 0.0
        mx, my = statistics.mean(x), statistics.mean(y)
        num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
        den = math.sqrt(sum((xi - mx) ** 2 for xi in x) * sum((yi - my) ** 2 for yi in y))
        return num / den if den > 0 else 0.0


class ExperimentDesigner:
    """Design experiments to test hypotheses."""

    def __init__(self, rng_seed: int = 42):
        self.rng = random.Random(rng_seed)

    def design(self, hypothesis: Hypothesis, n_samples: int = 100) -> Experiment:
        """Create A/B test or controlled experiment."""
        treatment = {var: "high" for var in hypothesis.variables}
        control = {var: "low" for var in hypothesis.variables}
        return Experiment(
            id=f"exp_{hypothesis.id}",
            hypothesis_id=hypothesis.id,
            design="ab_test",
            n_samples=n_samples,
            treatment=treatment,
            control=control,
            confounders=[],  # Simplified
        )

    def power_analysis(self, effect_size: float, alpha: float = 0.05, power: float = 0.8) -> int:
        """Simplified sample size estimate."""
        # Very rough approximation
        return max(20, int((16 * 1.0 / (effect_size ** 2))))


class StatisticalAnalyzer:
    """Analyze experimental results."""

    @staticmethod
    def analyze(treatment_data: List[float], control_data: List[float]) -> Result:
        """Two-sample t-test equivalent and Cohen's d."""
        nt, nc = len(treatment_data), len(control_data)
        if nt < 2 or nc < 2:
            raise ValueError("Need at least 2 samples per group")
        mt, mc = statistics.mean(treatment_data), statistics.mean(control_data)
        st, sc = statistics.stdev(treatment_data), statistics.stdev(control_data)
        # Pooled std
        pooled = math.sqrt(((nt - 1) * st ** 2 + (nc - 1) * sc ** 2) / (nt + nc - 2))
        # T-statistic
        se = pooled * math.sqrt(1 / nt + 1 / nc)
        t_stat = (mt - mc) / se if se > 0 else 0
        # Approximate p-value (simplified)
        p_value = max(0.001, min(1.0, 2 * (1 - _normal_cdf(abs(t_stat)))))
        # Cohen's d
        cohens_d = (mt - mc) / pooled if pooled > 0 else 0
        conclusion = "support" if p_value < 0.05 and abs(cohens_d) > 0.2 else "reject" if p_value >= 0.1 else "inconclusive"
        return Result(
            experiment_id="",
            treatment_mean=mt,
            control_mean=mc,
            treatment_std=st,
            control_std=sc,
            n_treatment=nt,
            n_control=nc,
            p_value=p_value,
            effect_size=cohens_d,
            conclusion=conclusion,
        )

    @staticmethod
    def chi_square(observed: List[List[int]]) -> Tuple[float, float]:
        """Chi-square test for independence."""
        row_sums = [sum(row) for row in observed]
        col_sums = [sum(observed[r][c] for r in range(len(observed))) for c in range(len(observed[0]))]
        total = sum(row_sums)
        expected = [[row_sums[r] * col_sums[c] / total for c in range(len(observed[0]))] for r in range(len(observed))]
        chi2 = sum((observed[r][c] - expected[r][c]) ** 2 / expected[r][c] for r in range(len(observed)) for c in range(len(observed[0])) if expected[r][c] > 0)
        return chi2, max(0.001, math.exp(-chi2 / 2))  # rough p-value


def _normal_cdf(z: float) -> float:
    """Approximate normal CDF."""
    # Abramowitz and Stegun approximation
    b1, b2, b3, b4, b5 = 0.319381530, -0.356563782, 1.781477937, -1.821255978, 1.330274429
    p = 0.2316419
    t = 1 / (1 + p * z)
    phi = (1 / math.sqrt(2 * math.pi)) * math.exp(-z * z / 2)
    return 1 - phi * (b1 * t + b2 * t ** 2 + b3 * t ** 3 + b4 * t ** 4 + b5 * t ** 5)


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURES — Research Lab
# ═══════════════════════════════════════════════════════════════════════════════

class ResearchLab:
    """Autonomous research cycle orchestrator."""

    def __init__(self, rng_seed: int = 42):
        self.rng = random.Random(rng_seed)
        self.inductor = PatternInductor(rng_seed)
        self.designer = ExperimentDesigner(rng_seed)
        self.analyzer = StatisticalAnalyzer()
        self.hypotheses: List[Hypothesis] = []
        self.experiments: List[Experiment] = []
        self.results: List[Result] = []
        self.publications: List[Publication] = []

    def run_cycle(self, observations: List[Dict[str, float]]) -> Publication:
        """Full cycle: observations → hypothesis → experiment → analysis → publication."""
        # Step 1: Generate hypotheses
        hyps = self.inductor.generate(observations, max_hypotheses=3)
        if not hyps:
            return Publication(
                title="No hypotheses generated",
                abstract="Insufficient pattern in observations.",
                hypothesis="N/A",
                method="N/A",
                results="N/A",
                conclusion="No testable hypotheses found.",
                confidence=0.0,
            )
        self.hypotheses.extend(hyps)
        h = hyps[0]

        # Step 2: Design experiment
        exp = self.designer.design(h)
        self.experiments.append(exp)

        # Step 3: Simulate data (in real use, run actual experiment)
        treatment_data, control_data = self._simulate_data(h, exp)

        # Step 4: Analyze
        result = self.analyzer.analyze(treatment_data, control_data)
        result.experiment_id = exp.id
        self.results.append(result)

        # Step 5: Publish
        pub = self._format_publication(h, exp, result)
        self.publications.append(pub)
        return pub

    def _simulate_data(self, h: Hypothesis, exp: Experiment) -> Tuple[List[float], List[float]]:
        """Simulate experimental data consistent with hypothesis."""
        base = 50.0
        effect = 10.0 if h.confidence > 0.5 else 2.0
        noise = 8.0
        treatment = [base + effect + self.rng.gauss(0, noise) for _ in range(exp.n_samples // 2)]
        control = [base + self.rng.gauss(0, noise) for _ in range(exp.n_samples // 2)]
        return treatment, control

    def _format_publication(self, h: Hypothesis, exp: Experiment, r: Result) -> Publication:
        confidence = (1 - r.p_value) * abs(r.effect_size)
        return Publication(
            title=f"On the effect of {h.variables[0]} on {h.outcome_var}",
            abstract=f"We tested whether {h.variables[0]} affects {h.outcome_var}. "
                     f"Result: {r.conclusion} (p={r.p_value:.3f}, d={r.effect_size:.2f}).",
            hypothesis=h.statement,
            method=f"A/B test, n={exp.n_samples}",
            results=f"Treatment M={r.treatment_mean:.1f} vs Control M={r.control_mean:.1f}",
            conclusion=r.conclusion,
            confidence=confidence,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SELF-TEST
# ═══════════════════════════════════════════════════════════════════════════════

def _self_test():
    print("=" * 55)
    print("Auto-Research Lab — Self Test")
    print("=" * 55)
    passed = 0
    total = 4

    # Test 1: Hypothesis generation from correlated data
    print("\n[Test 1] Hypothesis generation")
    data = []
    rng = random.Random(42)
    for i in range(200):
        x = rng.gauss(0, 10)
        y = 2 * x + rng.gauss(0, 5)
        z = rng.gauss(0, 10)
        data.append({"x": x, "y": y, "z": z})
    lab = ResearchLab(rng_seed=42)
    pub = lab.run_cycle(data)
    ok = "x" in pub.hypothesis and "y" in pub.hypothesis
    print(f"  Hypothesis generated: {pub.hypothesis} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    # Test 2: Experiment design
    print("[Test 2] Experiment design")
    ok = len(lab.experiments) > 0 and lab.experiments[0].design == "ab_test"
    print(f"  A/B test designed — {'PASS' if ok else 'FAIL'}")
    passed += ok

    # Test 3: Analysis
    print("[Test 3] Statistical analysis")
    ok = len(lab.results) > 0 and lab.results[0].p_value < 1.0
    print(f"  P-value computed: {lab.results[0].p_value:.4f}, conclusion: {lab.results[0].conclusion} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    # Test 4: Full cycle
    print("[Test 4] Full cycle completes")
    ok = pub.conclusion in ("support", "reject", "inconclusive") and pub.confidence >= 0
    print(f"  Publication ready: {pub.title[:40]}... — {'PASS' if ok else 'FAIL'}")
    passed += ok

    # Extra: Chi-square test
    print("[Extra] Chi-square test")
    chi2, p = StatisticalAnalyzer.chi_square([[50, 30], [20, 60]])
    print(f"  Chi2={chi2:.2f}, p≈{p:.4f}")

    print("" + "=" * 55)
    print(f"PASS: {passed}/{total}")
    print("=" * 55)
    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())

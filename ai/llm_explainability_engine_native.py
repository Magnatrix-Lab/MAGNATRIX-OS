#!/usr/bin/env python3
"""
llm_explainability_engine_native.py
Explainability & Attribution Engine for MAGNATRIX-OS

Provides:
- Token importance attribution (token-level scoring)
- Attention weight simulation for input-output relevance
- Counterfactual explanation generation
- Explanation formatting (text highlighting, saliency maps)

Pure stdlib. No external dependencies.
"""

from __future__ import annotations

import re
import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Tuple, Optional, Any


# ── Enums ───────────────────────────────────────────────────────────────────

class AttributionMethod(Enum):
    TFIDF = auto()
    POSITION = auto()
    FREQUENCY = auto()
    ATTENTION = auto()


class ExplanationFormat(Enum):
    HIGHLIGHT = auto()
    SALIENCY_MAP = auto()
    COUNTERFACTUAL = auto()
    ATTRIBUTION_LIST = auto()


# ── Dataclasses ─────────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class TokenScore:
    token: str
    score: float
    position: int
    method: AttributionMethod


@dataclass(slots=True)
class AttributionResult:
    input_text: str
    output_text: str
    tokens: List[TokenScore]
    method: AttributionMethod
    top_k_indices: List[int]


@dataclass(slots=True)
class AttentionMatrix:
    input_tokens: List[str]
    output_tokens: List[str]
    weights: List[List[float]]  # [output_idx][input_idx]


@dataclass(slots=True)
class CounterfactualResult:
    original_input: str
    modified_input: str
    original_output: str
    simulated_output: str
    changed_tokens: List[str]
    difference_description: str


@dataclass(slots=True)
class ExplanationReport:
    input_text: str
    output_text: str
    attribution: Optional[AttributionResult]
    attention: Optional[AttentionMatrix]
    counterfactuals: List[CounterfactualResult]
    saliency_map: Optional[str]
    highlighted_text: Optional[str]
    summary: str


# ── Tokenizer ───────────────────────────────────────────────────────────────

class SimpleTokenizer:
    """Simple whitespace/punctuation tokenizer."""

    def tokenize(self, text: str) -> List[str]:
        # Split on whitespace while preserving some punctuation as separate tokens
        tokens = []
        for word in text.split():
            # Extract trailing punctuation
            while word and word[-1] in ".!?,:;\"'":
                tokens.append(word[:-1])
                tokens.append(word[-1])
                word = ""
            if word:
                tokens.append(word)
        return tokens

    def detokenize(self, tokens: List[str]) -> str:
        result = []
        for i, tok in enumerate(tokens):
            if tok in ".!?,:;\"'" and result:
                result[-1] = result[-1] + tok
            else:
                result.append(tok)
        return " ".join(result)


# ── Attributor ────────────────────────────────────────────────────────────────

class TokenAttributor:
    """Computes token importance scores."""

    def __init__(self, method: AttributionMethod = AttributionMethod.TFIDF):
        self.method = method
        self.tokenizer = SimpleTokenizer()

    def _compute_tfidf_like(self, input_text: str, output_text: str) -> List[TokenScore]:
        """TF-IDF-like scoring: rare in corpus but present in output = important."""
        input_tokens = self.tokenizer.tokenize(input_text)
        output_tokens = self.tokenizer.tokenize(output_text)

        # Build frequency stats
        output_freq: Dict[str, int] = {}
        for t in output_tokens:
            output_freq[t.lower()] = output_freq.get(t.lower(), 0) + 1

        scores = []
        for i, token in enumerate(input_tokens):
            # TF: presence in output
            tf = output_freq.get(token.lower(), 0) / max(len(output_tokens), 1)

            # IDF: inverse frequency in input (rarer = more important)
            input_freq = sum(1 for t in input_tokens if t.lower() == token.lower())
            idf = math.log(len(input_tokens) / input_freq) if input_freq > 0 else 1.0

            # Position boost: first and last tokens often important
            position_weight = 1.0
            if i < 3 or i >= len(input_tokens) - 3:
                position_weight = 1.3

            score = tf * idf * position_weight
            scores.append(TokenScore(token=token, score=round(score, 4), position=i, method=self.method))

        return scores

    def _compute_position_based(self, input_text: str, output_text: str) -> List[TokenScore]:
        """Position-based heuristic: beginning and end are more important."""
        tokens = self.tokenizer.tokenize(input_text)
        n = len(tokens)
        scores = []
        for i, token in enumerate(tokens):
            # Gaussian-like weighting: center is less important
            normalized_pos = i / max(n - 1, 1)
            distance_from_center = abs(normalized_pos - 0.5) * 2.0
            score = 0.3 + distance_from_center * 0.7

            # Content words get a boost
            if token.lower() not in {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                                      "have", "has", "had", "do", "does", "did", "will", "would",
                                      "could", "should", "may", "might", "must", "shall", "can",
                                      "need", "dare", "ought", "used", "to", "of", "in", "for",
                                      "on", "with", "at", "by", "from", "as", "into", "through",
                                      "during", "before", "after", "above", "below", "between",
                                      "and", "but", "or", "yet", "so", "if", "because", "although"}:
                score *= 1.5

            scores.append(TokenScore(token=token, score=round(score, 4), position=i, method=self.method))
        return scores

    def _compute_frequency_based(self, input_text: str, output_text: str) -> List[TokenScore]:
        """Frequency-based: tokens that appear in both input and output are important."""
        input_tokens = self.tokenizer.tokenize(input_text)
        output_tokens = self.tokenizer.tokenize(output_text)
        output_set = set(t.lower() for t in output_tokens)

        scores = []
        for i, token in enumerate(input_tokens):
            in_output = 1.0 if token.lower() in output_set else 0.1
            # Length bonus: longer tokens often carry more meaning
            length_bonus = min(len(token) / 5.0, 2.0)
            score = in_output * (1.0 + length_bonus)
            scores.append(TokenScore(token=token, score=round(score, 4), position=i, method=self.method))
        return scores

    def _compute_attention_based(self, input_text: str, output_text: str) -> List[TokenScore]:
        """Simulate attention-based attribution."""
        input_tokens = self.tokenizer.tokenize(input_text)
        output_tokens = self.tokenizer.tokenize(output_text)

        # Simulate attention: each output token "attends" to input tokens
        # with higher weights for semantically similar tokens
        scores = [0.0] * len(input_tokens)

        for out_tok in output_tokens:
            out_lower = out_tok.lower().rstrip(".,:;!?\"'")
            for i, in_tok in enumerate(input_tokens):
                in_lower = in_tok.lower().rstrip(".,:;!?\"'")
                # Exact match = high attention
                if in_lower == out_lower:
                    scores[i] += 1.0
                # Partial overlap
                elif in_lower in out_lower or out_lower in in_lower:
                    scores[i] += 0.5
                # Shared characters
                else:
                    shared = len(set(in_lower) & set(out_lower))
                    scores[i] += shared / max(len(in_lower), len(out_lower)) * 0.2

        # Normalize
        max_score = max(scores) if scores else 1.0
        if max_score > 0:
            scores = [s / max_score for s in scores]

        return [TokenScore(token=t, score=round(s, 4), position=i, method=self.method)
                for i, (t, s) in enumerate(zip(input_tokens, scores))]

    def attribute(self, input_text: str, output_text: str) -> AttributionResult:
        if self.method == AttributionMethod.TFIDF:
            scores = self._compute_tfidf_like(input_text, output_text)
        elif self.method == AttributionMethod.POSITION:
            scores = self._compute_position_based(input_text, output_text)
        elif self.method == AttributionMethod.FREQUENCY:
            scores = self._compute_frequency_based(input_text, output_text)
        elif self.method == AttributionMethod.ATTENTION:
            scores = self._compute_attention_based(input_text, output_text)
        else:
            scores = self._compute_tfidf_like(input_text, output_text)

        # Top-k indices by score
        sorted_indices = sorted(range(len(scores)), key=lambda i: scores[i].score, reverse=True)
        top_k = sorted_indices[:max(3, len(scores) // 5)]

        return AttributionResult(
            input_text=input_text,
            output_text=output_text,
            tokens=scores,
            method=self.method,
            top_k_indices=top_k,
        )


# ── Attention Simulator ─────────────────────────────────────────────────────

class AttentionSimulator:
    """Simulates attention weights between input and output tokens."""

    def __init__(self, random_seed: Optional[int] = None):
        self.tokenizer = SimpleTokenizer()
        if random_seed is not None:
            random.seed(random_seed)

    def simulate(self, input_text: str, output_text: str) -> AttentionMatrix:
        input_tokens = self.tokenizer.tokenize(input_text)
        output_tokens = self.tokenizer.tokenize(output_text)

        weights: List[List[float]] = []
        for out_tok in output_tokens:
            out_lower = out_tok.lower().rstrip(".,:;!?\"'")
            row: List[float] = []
            for in_tok in input_tokens:
                in_lower = in_tok.lower().rstrip(".,:;!?\"'")
                if in_lower == out_lower:
                    base = 0.8 + random.random() * 0.2
                elif in_lower in out_lower or out_lower in in_lower:
                    base = 0.4 + random.random() * 0.3
                else:
                    # Random weak attention with some sparsity
                    base = random.random() * 0.15
                row.append(round(base, 4))
            # Softmax-like normalization per row
            exp_sum = sum(math.exp(w) for w in row)
            row = [round(math.exp(w) / exp_sum, 4) for w in row]
            weights.append(row)

        return AttentionMatrix(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            weights=weights,
        )


# ── Counterfactual Generator ────────────────────────────────────────────────

class CounterfactualGenerator:
    """Generates counterfactual explanations by perturbing inputs."""

    def __init__(self, random_seed: Optional[int] = None):
        self.tokenizer = SimpleTokenizer()
        if random_seed is not None:
            random.seed(random_seed)

    def _simulate_output_change(self, original: str, removed_tokens: List[str]) -> str:
        """Simulate how output might change when input tokens are removed."""
        # In a real system, this would re-run the model
        # Here we simulate by removing mentions of removed tokens from output
        words = original.split()
        modified = []
        for w in words:
            w_clean = w.lower().rstrip(".,:;!?\"'")
            if w_clean not in [t.lower() for t in removed_tokens]:
                modified.append(w)
            else:
                # Sometimes replace with generic term
                modified.append("[REDACTED]")
        return " ".join(modified)

    def generate(self, input_text: str, output_text: str, num_variants: int = 3) -> List[CounterfactualResult]:
        tokens = self.tokenizer.tokenize(input_text)
        results = []

        # Strategy 1: Remove important words (nouns, proper nouns)
        content_words = [t for t in tokens if t[0].isupper() or t.lower() not in {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "have", "has", "had", "do", "does", "did", "will", "would",
            "to", "of", "in", "for", "on", "with", "at", "by", "from",
            "and", "but", "or", "it", "this", "that", "these", "those",
        }]

        for i in range(min(num_variants, len(content_words))):
            if not content_words:
                break
            # Remove a different content word each time
            removed = [content_words[i % len(content_words)]]
            modified_tokens = [t for t in tokens if t not in removed]
            modified_input = self.tokenizer.detokenize(modified_tokens)

            simulated_output = self._simulate_output_change(output_text, removed)

            diff_desc = f"Removed '{removed[0]}' from input. Output shifted from '{output_text[:40]}...' to '{simulated_output[:40]}...'"

            results.append(CounterfactualResult(
                original_input=input_text,
                modified_input=modified_input,
                original_output=output_text,
                simulated_output=simulated_output,
                changed_tokens=removed,
                difference_description=diff_desc,
            ))

        # Strategy 2: Negation flip
        if "not" in [t.lower() for t in tokens]:
            modified_tokens = []
            for t in tokens:
                if t.lower() == "not":
                    modified_tokens.append("indeed")
                else:
                    modified_tokens.append(t)
            modified_input = self.tokenizer.detokenize(modified_tokens)
            simulated_output = self._simulate_output_change(output_text, ["not"])
            results.append(CounterfactualResult(
                original_input=input_text,
                modified_input=modified_input,
                original_output=output_text,
                simulated_output=simulated_output,
                changed_tokens=["not"],
                difference_description="Negation removed ('not' → 'indeed'). Output likely flips polarity.",
            ))

        # Strategy 3: Number perturbation
        for i, t in enumerate(tokens):
            if t.isdigit():
                modified_tokens = tokens[:]
                modified_tokens[i] = str(int(t) + random.randint(1, 10))
                modified_input = self.tokenizer.detokenize(modified_tokens)
                simulated_output = self._simulate_output_change(output_text, [t])
                results.append(CounterfactualResult(
                    original_input=input_text,
                    modified_input=modified_input,
                    original_output=output_text,
                    simulated_output=simulated_output,
                    changed_tokens=[t],
                    difference_description=f"Changed number '{t}' to '{modified_tokens[i]}'. Output may update accordingly.",
                ))
                break

        return results


# ── Explanation Formatter ───────────────────────────────────────────────────

class ExplanationFormatter:
    """Formats explanations into human-readable output."""

    HIGHLIGHT_START = "[["
    HIGHLIGHT_END = "]]"

    def highlight_text(self, text: str, scores: List[TokenScore], threshold: float = 0.6) -> str:
        """Highlight important tokens in the input text."""
        tokens = [s.token for s in scores]
        highlighted_parts = []

        # Reconstruct with highlights
        # We need to be careful about detokenization
        result = text
        # Sort by position descending to avoid offset issues when inserting markers
        important = sorted([s for s in scores if s.score >= threshold], key=lambda s: s.position, reverse=True)

        for score in important:
            # Simple replacement - may not be perfect for all tokenizations
            token = score.token
            # Escape regex special chars
            escaped = re.escape(token)
            # Only highlight first occurrence not already highlighted
            pattern = re.compile(rf'(?<!\[\[){escaped}(?!\]\])', re.IGNORECASE)
            result = pattern.sub(f"{self.HIGHLIGHT_START}{token}{self.HIGHLIGHT_END}", result, count=1)

        return result

    def saliency_map(self, scores: List[TokenScore], width: int = 40) -> str:
        """Create a text-based saliency map."""
        lines = []
        lines.append("SALIENCY MAP")
        lines.append("─" * width)

        if not scores:
            lines.append("(no tokens)")
            return "\n".join(lines)

        max_score = max(s.score for s in scores) if scores else 1.0
        if max_score == 0:
            max_score = 1.0

        for score in scores:
            normalized = score.score / max_score
            bar_len = int(normalized * (width - 20))
            bar = "█" * bar_len + "░" * ((width - 20) - bar_len)
            token_display = score.token[:12] + "…" if len(score.token) > 12 else score.token
            lines.append(f"{token_display:14s} │{bar}│ {normalized:.2f}")

        lines.append("─" * width)
        return "\n".join(lines)

    def format_counterfactual(self, cf: CounterfactualResult) -> str:
        lines = [
            f"Counterfactual: What if we changed '{', '.join(cf.changed_tokens)}'?",
            f"  Original input:  {cf.original_input}",
            f"  Modified input:  {cf.modified_input}",
            f"  Original output: {cf.original_output[:80]}",
            f"  Simulated output:{cf.simulated_output[:80]}",
            f"  Impact: {cf.difference_description}",
        ]
        return "\n".join(lines)


# ── Explainability Engine ───────────────────────────────────────────────────

class ExplainabilityEngine:
    """Orchestrates all explainability components."""

    def __init__(self, attribution_method: AttributionMethod = AttributionMethod.ATTENTION):
        self.attributor = TokenAttributor(method=attribution_method)
        self.attention_sim = AttentionSimulator()
        self.counterfactual_gen = CounterfactualGenerator()
        self.formatter = ExplanationFormatter()

    def explain(self, input_text: str, output_text: str) -> ExplanationReport:
        # 1. Token attribution
        attribution = self.attributor.attribute(input_text, output_text)

        # 2. Attention simulation
        attention = self.attention_sim.simulate(input_text, output_text)

        # 3. Counterfactuals
        counterfactuals = self.counterfactual_gen.generate(input_text, output_text, num_variants=3)

        # 4. Formatting
        highlighted = self.formatter.highlight_text(input_text, attribution.tokens, threshold=0.5)
        saliency = self.formatter.saliency_map(attribution.tokens)

        # Summary
        top_tokens = [attribution.tokens[i] for i in attribution.top_k_indices[:5]]
        top_str = ", ".join(f"'{t.token}' ({t.score:.2f})" for t in top_tokens)
        summary = f"Top influencing tokens: {top_str}. {len(counterfactuals)} counterfactual scenarios generated."

        return ExplanationReport(
            input_text=input_text,
            output_text=output_text,
            attribution=attribution,
            attention=attention,
            counterfactuals=counterfactuals,
            saliency_map=saliency,
            highlighted_text=highlighted,
            summary=summary,
        )


# ── Demo ────────────────────────────────────────────────────────────────────

def run_demo() -> None:
    print("=" * 70)
    print("EXPLAINABILITY & ATTRIBUTION ENGINE — MAGNATRIX-OS")
    print("=" * 70)

    engine = ExplainabilityEngine(attribution_method=AttributionMethod.ATTENTION)

    test_cases = [
        {
            "input": "What is the capital of France?",
            "output": "The capital of France is Paris, a city known for the Eiffel Tower.",
        },
        {
            "input": "Explain quantum computing in simple terms.",
            "output": "Quantum computing uses quantum bits or qubits that can exist in multiple states simultaneously, unlike classical bits that are either 0 or 1.",
        },
        {
            "input": "Who wrote the novel 1984?",
            "output": "George Orwell wrote the novel 1984, published in 1949.",
        },
    ]

    for i, case in enumerate(test_cases, 1):
        print(f"\n{'─' * 70}")
        print(f"Test Case {i}")
        print(f"Input:  {case['input']}")
        print(f"Output: {case['output']}")
        print("─" * 70)

        report = engine.explain(case["input"], case["output"])

        print(f"\nSummary: {report.summary}")

        print(f"\nTop Tokens by Attribution:")
        for idx in report.attribution.top_k_indices[:5]:
            ts = report.attribution.tokens[idx]
            print(f"  [{ts.position:3d}] '{ts.token:15s}' → score={ts.score:.4f} ({ts.method.name})")

        print(f"\nHighlighted Input (important tokens marked):")
        print(f"  {report.highlighted_text}")

        print(f"\n{report.saliency_map}")

        print(f"\nCounterfactual Explanations:")
        for cf in report.counterfactuals:
            print(f"\n  {cf.difference_description}")
            print(f"    Original:  {cf.original_output[:60]}...")
            print(f"    Simulated: {cf.simulated_output[:60]}...")

        # Show a snippet of attention matrix
        print(f"\nAttention Matrix (first 3 output tokens × first 5 input tokens):")
        am = report.attention
        header = "      " + " ".join(f"{t:8s}" for t in am.input_tokens[:5])
        print(f"  {header}")
        for j in range(min(3, len(am.output_tokens))):
            row_str = " ".join(f"{w:8.4f}" for w in am.weights[j][:5])
            print(f"  {am.output_tokens[j]:6s} {row_str}")

    print(f"\n{'=' * 70}")
    print("DEMO COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    run_demo()

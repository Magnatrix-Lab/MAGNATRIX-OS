#!/usr/bin/env python3
"""
MAGNATRIX-OS — Speculative Decoding Engine
ai/llm_speculative_decoder_native.py

Features:
- Draft model token speculation (generate N draft tokens)
- Target model verification (accept/reject draft tokens)
- Acceptance criteria and rollback on mismatch
- Speedup ratio calculation
- Draft model management (simple vs complex draft strategies)

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import enum
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("speculative_decoder")


class DraftStrategy(enum.Enum):
    SIMPLE = "simple"         # greedy draft: always pick highest probability
    TEMPERATURE = "temperature"  # sample with temperature
    TOP_K = "top_k"           # sample from top-k tokens
    MIXED = "mixed"           # combine strategies


class TokenVerdict(enum.Enum):
    ACCEPT = "accept"
    REJECT = "reject"


@dataclass
class Token:
    id: int
    text: str
    prob: float


@dataclass
class DraftResult:
    tokens: List[Token]
    draft_time_ms: float
    strategy: DraftStrategy


@dataclass
class VerificationResult:
    accepted: List[Token]
    rejected: List[Token]
    first_rejected_index: int = -1
    corrected_token: Optional[Token] = None
    verification_time_ms: float = 0.0


@dataclass
class DecodingResult:
    final_tokens: List[Token]
    draft_tokens: List[Token]
    accepted_count: int
    rejected_count: int
    speedup_ratio: float
    total_time_ms: float
    strategy: DraftStrategy


class DraftModel:
    """Simulated draft model that generates token candidates."""

    VOCAB = [
        "the", "a", "is", "are", "was", "were", "to", "of", "and", "in",
        "that", "have", "I", "it", "for", "not", "on", "with", "he", "as",
        "you", "do", "at", "this", "but", "his", "by", "from", "they", "we",
        "say", "her", "she", "or", "an", "will", "my", "one", "all", "would",
        "there", "their", "what", "so", "up", "out", "if", "about", "who",
        "get", "which", "go", "me", "when", "make", "can", "like", "time", "no",
        "just", "him", "know", "take", "people", "into", "year", "your", "good",
        "some", "could", "them", "see", "other", "than", "then", "now", "look",
        "only", "come", "its", "over", "think", "also", "back", "after", "use",
        "two", "how", "our", "work", "first", "well", "way", "even", "new", "want",
    ]

    def __init__(self, latency_ms: float = 2.0, accuracy: float = 0.7):
        self._latency_ms = latency_ms
        self._accuracy = accuracy
        self._rng = random.Random(42)

    def generate(self, prefix: List[Token], max_tokens: int = 5,
                 strategy: DraftStrategy = DraftStrategy.SIMPLE) -> DraftResult:
        t0 = time.monotonic()
        tokens = []
        for i in range(max_tokens):
            tok = self._draft_token(prefix + tokens, strategy)
            tokens.append(tok)
            if tok.text in [".", "!", "?"]:
                break
        elapsed = (time.monotonic() - t0) * 1000
        return DraftResult(tokens=tokens, draft_time_ms=elapsed, strategy=strategy)

    def _draft_token(self, prefix: List[Token], strategy: DraftStrategy) -> Token:
        candidates = self._candidates(prefix)
        if strategy == DraftStrategy.SIMPLE:
            return max(candidates, key=lambda t: t.prob)
        elif strategy == DraftStrategy.TEMPERATURE:
            return self._sample(candidates, temperature=0.8)
        elif strategy == DraftStrategy.TOP_K:
            top_k = sorted(candidates, key=lambda t: t.prob, reverse=True)[:5]
            return self._sample(top_k, temperature=1.0)
        else:  # MIXED
            if self._rng.random() < 0.5:
                return max(candidates, key=lambda t: t.prob)
            return self._sample(candidates, temperature=0.8)

    def _candidates(self, prefix: List[Token]) -> List[Token]:
        # Simulate vocabulary sampling based on prefix context
        n = len(prefix)
        base_probs = [1.0 / (i + 1 + n * 0.1) for i in range(min(10, len(self.VOCAB)))]
        total = sum(base_probs)
        probs = [p / total for p in base_probs]
        words = self._rng.sample(self.VOCAB, len(probs))
        return [Token(id=i, text=w, prob=p) for i, (w, p) in enumerate(zip(words, probs))]

    def _sample(self, candidates: List[Token], temperature: float = 1.0) -> Token:
        probs = [t.prob ** (1.0 / temperature) for t in candidates]
        total = sum(probs)
        probs = [p / total for p in probs]
        r = self._rng.random()
        cum = 0.0
        for t, p in zip(candidates, probs):
            cum += p
            if r <= cum:
                return t
        return candidates[-1]


class TargetModel:
    """Simulated target model that verifies draft tokens."""

    def __init__(self, latency_ms: float = 20.0, agreement_rate: float = 0.75):
        self._latency_ms = latency_ms
        self._agreement_rate = agreement_rate
        self._rng = random.Random(43)

    def verify(self, prefix: List[Token], draft: DraftResult) -> VerificationResult:
        t0 = time.monotonic()
        accepted = []
        rejected = []
        first_rejected = -1
        corrected = None

        for i, draft_tok in enumerate(draft.tokens):
            # Simulate target model output for this position
            target_tok = self._target_token(prefix + accepted)
            # Simulate agreement check
            if self._rng.random() < self._agreement_rate and draft_tok.text == target_tok.text:
                accepted.append(draft_tok)
            else:
                if first_rejected == -1:
                    first_rejected = i
                    corrected = target_tok
                rejected.append(draft_tok)

        elapsed = (time.monotonic() - t0) * 1000
        return VerificationResult(
            accepted=accepted,
            rejected=rejected,
            first_rejected_index=first_rejected,
            corrected_token=corrected,
            verification_time_ms=elapsed,
        )

    def _target_token(self, prefix: List[Token]) -> Token:
        # Simpler than draft model but more accurate
        words = ["the", "a", "is", "to", "of", "and", "in", "that", "for", "with"]
        probs = [0.3, 0.15, 0.12, 0.10, 0.08, 0.07, 0.06, 0.05, 0.04, 0.03]
        r = self._rng.random()
        cum = 0.0
        for w, p in zip(words, probs):
            cum += p
            if r <= cum:
                return Token(id=hash(w) % 10000, text=w, prob=p)
        return Token(id=0, text="the", prob=0.3)


class SpeculativeDecoder:
    """Speculative decoding engine."""

    def __init__(self, draft: DraftModel, target: TargetModel, max_draft_tokens: int = 5):
        self.draft = draft
        self.target = target
        self.max_draft_tokens = max_draft_tokens
        self._stats = {"runs": 0, "total_draft": 0, "total_accepted": 0, "total_time": 0.0}

    def decode(self, prefix: List[Token], strategy: DraftStrategy = DraftStrategy.SIMPLE,
               max_tokens: int = 20) -> DecodingResult:
        all_tokens = list(prefix)
        total_draft = 0
        total_accepted = 0
        total_rejected = 0
        t0_total = time.monotonic()

        while len(all_tokens) < len(prefix) + max_tokens:
            # Draft phase
            draft_result = self.draft.generate(all_tokens, self.max_draft_tokens, strategy)
            if not draft_result.tokens:
                break
            total_draft += len(draft_result.tokens)

            # Verification phase
            verify_result = self.target.verify(all_tokens, draft_result)

            # Accept accepted tokens
            all_tokens.extend(verify_result.accepted)
            total_accepted += len(verify_result.accepted)
            total_rejected += len(verify_result.rejected)

            # If first rejected, add corrected token and stop drafting
            if verify_result.first_rejected_index >= 0 and verify_result.corrected_token:
                all_tokens.append(verify_result.corrected_token)
                break

            # If all accepted, continue with next draft
            if len(verify_result.accepted) == len(draft_result.tokens):
                continue
            break

        total_time = (time.monotonic() - t0_total) * 1000

        # Speedup = target-only time / speculative time
        target_only_time = self.target._latency_ms * max_tokens
        speedup = target_only_time / max(total_time, 1.0)

        self._stats["runs"] += 1
        self._stats["total_draft"] += total_draft
        self._stats["total_accepted"] += total_accepted
        self._stats["total_time"] += total_time

        return DecodingResult(
            final_tokens=all_tokens[len(prefix):],
            draft_tokens=draft_result.tokens,
            accepted_count=total_accepted,
            rejected_count=total_rejected,
            speedup_ratio=speedup,
            total_time_ms=total_time,
            strategy=strategy,
        )

    def get_stats(self) -> Dict[str, Any]:
        stats = dict(self._stats)
        if stats["runs"] > 0:
            stats["avg_draft_per_run"] = stats["total_draft"] / stats["runs"]
            stats["avg_accepted_per_run"] = stats["total_accepted"] / stats["runs"]
            stats["avg_time_ms"] = stats["total_time"] / stats["runs"]
            stats["acceptance_rate"] = stats["total_accepted"] / max(stats["total_draft"], 1)
        return stats

    def reset_stats(self) -> None:
        self._stats = {"runs": 0, "total_draft": 0, "total_accepted": 0, "total_time": 0.0}


class SpeculativeDecoderEngine:
    """Unified speculative decoding engine."""

    def __init__(self, draft_latency_ms: float = 2.0, target_latency_ms: float = 20.0,
                 draft_accuracy: float = 0.7, target_agreement: float = 0.75,
                 max_draft_tokens: int = 5):
        self.draft_model = DraftModel(latency_ms=draft_latency_ms, accuracy=draft_accuracy)
        self.target_model = TargetModel(latency_ms=target_latency_ms, agreement_rate=target_agreement)
        self.decoder = SpeculativeDecoder(self.draft_model, self.target_model, max_draft_tokens)

    def generate(self, prompt: str, max_tokens: int = 20, strategy: DraftStrategy = DraftStrategy.SIMPLE) -> DecodingResult:
        prefix = [Token(id=0, text=word, prob=1.0) for word in prompt.split()]
        return self.decoder.decode(prefix, strategy, max_tokens)

    def get_stats(self) -> Dict[str, Any]:
        return self.decoder.get_stats()

    def benchmark(self, prompt: str, max_tokens: int = 20, iterations: int = 10) -> Dict[str, Any]:
        self.decoder.reset_stats()
        for _ in range(iterations):
            self.generate(prompt, max_tokens, DraftStrategy.SIMPLE)
        return self.get_stats()


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Speculative Decoding Engine")
    print("ai/llm_speculative_decoder_native.py")
    print("=" * 60)

    engine = SpeculativeDecoderEngine(
        draft_latency_ms=2.0, target_latency_ms=20.0,
        draft_accuracy=0.7, target_agreement=0.75,
        max_draft_tokens=5,
    )

    # 1. Simple strategy
    print("")
    print("[1] Simple Strategy (Greedy Draft)")
    result = engine.generate("The quick brown fox", max_tokens=15, strategy=DraftStrategy.SIMPLE)
    print(f"  Draft tokens: {len(result.draft_tokens)}")
    print(f"  Accepted: {result.accepted_count}, Rejected: {result.rejected_count}")
    print(f"  Speedup: {result.speedup_ratio:.2f}x, Time: {result.total_time_ms:.1f}ms")
    print(f"  Output: {' '.join(t.text for t in result.final_tokens[:10])}")

    # 2. Temperature strategy
    print("")
    print("[2] Temperature Strategy")
    engine.decoder.reset_stats()
    result = engine.generate("The quick brown fox", max_tokens=15, strategy=DraftStrategy.TEMPERATURE)
    print(f"  Accepted: {result.accepted_count}, Rejected: {result.rejected_count}")
    print(f"  Speedup: {result.speedup_ratio:.2f}x")

    # 3. Top-K strategy
    print("")
    print("[3] Top-K Strategy")
    engine.decoder.reset_stats()
    result = engine.generate("The quick brown fox", max_tokens=15, strategy=DraftStrategy.TOP_K)
    print(f"  Accepted: {result.accepted_count}, Rejected: {result.rejected_count}")
    print(f"  Speedup: {result.speedup_ratio:.2f}x")

    # 4. Mixed strategy
    print("")
    print("[4] Mixed Strategy")
    engine.decoder.reset_stats()
    result = engine.generate("The quick brown fox", max_tokens=15, strategy=DraftStrategy.MIXED)
    print(f"  Accepted: {result.accepted_count}, Rejected: {result.rejected_count}")
    print(f"  Speedup: {result.speedup_ratio:.2f}x")

    # 5. Benchmark
    print("")
    print("[5] Benchmark (10 iterations)")
    stats = engine.benchmark("The quick brown fox", max_tokens=20, iterations=10)
    print(f"  Runs: {stats['runs']}")
    print(f"  Avg draft/run: {stats.get('avg_draft_per_run', 0):.1f}")
    print(f"  Avg accepted/run: {stats.get('avg_accepted_per_run', 0):.1f}")
    print(f"  Acceptance rate: {stats.get('acceptance_rate', 0):.2%}")
    print(f"  Avg time: {stats.get('avg_time_ms', 0):.1f}ms")

    print("" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()

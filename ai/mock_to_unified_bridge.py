#!/usr/bin/env python3
"""
Mock-to-Unified Bridge — adapter yang map MockLLM interface ke UnifiedLLMBackend.
Mengganti MockLLM class dengan delegasi ke UnifiedLLMBackend.generate().
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

# Lazy import untuk menghindari circular dependency
_UnifiedLLMBackend = None

def _get_unified():
    global _UnifiedLLMBackend
    if _UnifiedLLMBackend is None:
        from ai.unified_llm_backend import UnifiedLLMBackend
        _UnifiedLLMBackend = UnifiedLLMBackend
    return _UnifiedLLMBackend


class MockToUnifiedBridge:
    """
    Adapter yang menyediakan interface MockLLM (generate, summarize)
    tapi di belakangnya delegasi ke UnifiedLLMBackend.generate().
    """

    def __init__(
        self,
        preferred_backend: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 512,
    ):
        self.preferred_backend = preferred_backend
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._unified: Optional[Any] = None

    @property
    def unified(self):
        if self._unified is None:
            cls = _get_unified()
            self._unified = cls()
        return self._unified

    def generate(self, prompt: str, context: List[str], max_tokens: int = 200) -> str:
        """Generate answer dari prompt + context. Interface-compatible dengan MockLLM."""
        full_prompt = self._build_prompt(prompt, context)
        try:
            resp = self.unified.generate(
                prompt=full_prompt,
                temperature=self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                preferred_backend=self.preferred_backend,
            )
            return resp.text
        except Exception as exc:
            # Fallback: deterministic mock jika semua backend gagal
            return self._mock_generate(prompt, context, max_tokens)

    def summarize(self, text: str, max_lines: int = 3) -> str:
        """Summarize text. Interface-compatible dengan MockLLM."""
        prompt = f"Summarize the following text in {max_lines} sentences:\n\n{text}"
        try:
            resp = self.unified.generate(
                prompt=prompt,
                temperature=0.3,
                max_tokens=256,
                preferred_backend=self.preferred_backend,
            )
            return resp.text
        except Exception:
            return self._mock_summarize(text, max_lines)

    def _build_prompt(self, prompt: str, context: List[str]) -> str:
        ctx = "\n\n".join(context)
        return f"Context:\n{ctx}\n\nQuestion: {prompt}\n\nAnswer:"

    def _mock_generate(self, prompt: str, context: List[str], max_tokens: int) -> str:
        """Deterministic fallback jika UnifiedLLMBackend tidak tersedia."""
        if not context:
            return "I don't have enough information to answer that."
        query_terms = set(self._tokenize(prompt))
        scored = []
        for snippet in context:
            sentences = re.split(r"(?<=[.!?])\s+", snippet)
            for sent in sentences:
                overlap = len(query_terms & set(self._tokenize(sent)))
                scored.append((sent, overlap))
        scored.sort(key=lambda x: x[1], reverse=True)
        top = [s for s, _ in scored[:5] if len(s) > 20]
        if not top:
            top = context[:2]
        answer = "Based on the documents:\n\n" + " ".join(top)
        if len(answer) > max_tokens:
            answer = answer[: max_tokens - 3] + "..."
        return answer

    def _mock_summarize(self, text: str, max_lines: int) -> str:
        import math
        sentences = re.split(r"(?<=[.!?])\s+", text)
        scored = []
        for i, sent in enumerate(sentences):
            words = self._tokenize(sent)
            score = (1.0 / (i + 1)) * math.log(len(words) + 2)
            scored.append((sent, score))
        scored.sort(key=lambda x: x[1], reverse=True)
        best = [s for s, _ in scored[:max_lines]]
        return " ".join(best)

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        lowered = text.lower()
        cleaned = re.sub(r"[^a-z0-9\s]", " ", lowered)
        return [t for t in cleaned.split() if len(t) > 2]

    def __repr__(self) -> str:
        return f"<MockToUnifiedBridge backend={self.preferred_backend}>"


class MockLLMSchedulerBridge:
    """
    Bridge untuk MockLLMScheduler → LLMScheduler dengan UnifiedLLMBackend.
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        preferred_backend: Optional[str] = None,
    ):
        self.api_url = api_url
        self.api_key = api_key
        self.preferred_backend = preferred_backend
        self.last_tokens_used = 0
        self._unified: Optional[Any] = None

    @property
    def unified(self):
        if self._unified is None:
            cls = _get_unified()
            self._unified = cls()
        return self._unified

    def schedule(
        self,
        prompt: str,
        system: str = "",
        temperature: float = 0.4,
        max_tokens: int = 512,
        timeout: float = 60.0,
    ) -> str:
        """Interface-compatible dengan LLMScheduler.schedule()."""
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        try:
            resp = self.unified.generate(
                prompt=full_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                preferred_backend=self.preferred_backend,
            )
            self.last_tokens_used = resp.tokens_used or max_tokens // 2
            return resp.text
        except Exception:
            self.last_tokens_used = 64
            return self._mock_response(prompt)

    def _mock_response(self, prompt: str) -> str:
        """Deterministic mock fallback."""
        prompt_lower = prompt.lower()
        if "draft" in prompt_lower and "amc" in prompt_lower:
            return "1. Pair factors to find multiples of 100.\n2. Use modular arithmetic.\n3. Conclude remainder is 0."
        if "draft" in prompt_lower and "n^2" in prompt_lower:
            return "1. Consider cases n even and n odd.\n2. For even n=2k, n^2=4k^2 divisible by 4.\n3. For odd n=2k+1, n^2=4k(k+1)+1 ≡ 1 (mod 4)."
        if "draft" in prompt_lower:
            return "1. Apply relevant lemma.\n2. Simplify expression.\n3. Conclude by exact or linarith."
        if "sketch" in prompt_lower:
            if "amc" in prompt_lower or "mod" in prompt_lower:
                return "have h1 : 91 * 99 % 100 = 9 := by prove_with []\nhave h2 : 92 * 98 % 100 = 16 := by prove_with [h1]\nhave h3 : 93 * 97 % 100 = 21 := by prove_with [h1, h2]\nhave h4 : 94 * 96 % 100 = 24 := by prove_with [h1, h2, h3]\nhave h5 : 95 % 100 = 95 := by prove_with []\nhave h6 : (91*92*93*94*95*96*97*98*99) % 100 = 0 := by prove_with [h1, h2, h3, h4, h5]\nexact h6"
            if "even" in prompt_lower or "odd" in prompt_lower:
                return "have h1 : ∀ n : Nat, n % 2 = 0 → n^2 % 4 = 0 := by prove_with []\nhave h2 : ∀ n : Nat, n % 2 = 1 → n^2 % 4 = 1 := by prove_with [h1]\ncases (n % 2) with\n| 0 => apply h1; exact h\n| 1 => apply h2; exact h"
            return "have h1 : goal := by prove_with []\nexact h1"
        if "next tactic" in prompt_lower:
            if "∀" in prompt_lower:
                return "intro x"
            if "∃" in prompt_lower:
                return "use 0"
            if "∧" in prompt_lower:
                return "split"
            if "∨" in prompt_lower:
                return "left"
            if "→" in prompt_lower:
                return "intro h"
            if "=" in prompt_lower and any(c.isdigit() for c in prompt_lower):
                return "norm_num"
            return "exact h"
        return "sorry"

    def __repr__(self) -> str:
        return f"<MockLLMSchedulerBridge backend={self.preferred_backend}>"


# Convenience aliases untuk backward compatibility
MockLLM = MockToUnifiedBridge
MockLLMScheduler = MockLLMSchedulerBridge

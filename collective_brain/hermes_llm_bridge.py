#!/usr/bin/env python3
"""
HERMES LLM Bridge — Lightweight adapter for UnifiedLLMBackend
===============================================================
~120 lines. Pure Python stdlib + UnifiedLLMBackend import.

Used by: WarRoomKernel for smart nudges and mission assistance.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Resolve ai/ sibling directory for UnifiedLLMBackend import
# ---------------------------------------------------------------------------
_BRIDGE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(_BRIDGE_DIR.parent))
from ai.unified_llm_backend import UnifiedLLMBackend, LLMResponse


# ===========================================================================
# HermesLLMBridge
# ===========================================================================

@dataclass
class NudgeResult:
    message: str
    backend: str
    latency_ms: float


@dataclass
class AssistResult:
    answer: str
    backend: str
    latency_ms: float


class HermesLLMBridge:
    """
    Thin async wrapper around UnifiedLLMBackend for HERMES War Room use-cases.
    """

    def __init__(
        self,
        llm: Optional[UnifiedLLMBackend] = None,
        default_model: Optional[str] = None,
        nudge_max_tokens: int = 128,
        assist_max_tokens: int = 512,
        temperature: float = 0.3,
    ):
        self._llm: Optional[UnifiedLLMBackend] = llm
        self.default_model = default_model
        self.nudge_max_tokens = nudge_max_tokens
        self.assist_max_tokens = assist_max_tokens
        self.temperature = temperature
        self._stats = {"nudges": 0, "assists": 0, "errors": 0}

    @property
    def llm(self) -> UnifiedLLMBackend:
        if self._llm is None:
            self._llm = UnifiedLLMBackend()
        return self._llm

    # ------------------------------------------------------------------
    # Smart Nudge
    # ------------------------------------------------------------------

    async def smart_nudge(self, task_title: str, stuck_minutes: float) -> NudgeResult:
        """
        Generate a contextual nudge message for a stuck task.
        Prompt: concise action suggestion to unblock.
        """
        prompt = (
            f"Task '{task_title}' has been stuck for {stuck_minutes:.0f} minutes. "
            f"Suggest ONE concise, actionable step to unblock it. "
            f"Respond with only the suggestion, no preamble."
        )

        start = time.time()
        try:
            loop = asyncio.get_event_loop()
            resp: LLMResponse = await loop.run_in_executor(
                None,
                lambda: self.llm.generate(
                    prompt=prompt,
                    model=self.default_model,
                    temperature=self.temperature,
                    max_tokens=self.nudge_max_tokens,
                ),
            )
            self._stats["nudges"] += 1
            return NudgeResult(
                message=resp.text.strip(),
                backend=resp.backend,
                latency_ms=(time.time() - start) * 1000,
            )
        except Exception as exc:
            self._stats["errors"] += 1
            fallback = (
                f"Task '{task_title}' stuck for {stuck_minutes:.0f}m. "
                f"Check dependencies or escalate to team lead."
            )
            return NudgeResult(message=fallback, backend="fallback", latency_ms=0.0)

    # ------------------------------------------------------------------
    # Mission Assist
    # ------------------------------------------------------------------

    async def mission_assist(
        self,
        query: str,
        mission_context: Optional[Dict[str, Any]] = None,
    ) -> AssistResult:
        """
        Answer a natural-language question about mission state using LLM.
        """
        context_json = json.dumps(mission_context or {}, indent=2, default=str)
        prompt = (
            f"You are HERMES War Room AI, a mission control assistant.\n"
            f"Answer the following question using ONLY the mission state provided.\n"
            f"Be concise, factual, and actionable.\n\n"
            f"Mission State:\n{context_json}\n\n"
            f"Question: {query}\n\nAnswer:"
        )

        start = time.time()
        try:
            loop = asyncio.get_event_loop()
            resp: LLMResponse = await loop.run_in_executor(
                None,
                lambda: self.llm.generate(
                    prompt=prompt,
                    model=self.default_model,
                    temperature=0.2,
                    max_tokens=self.assist_max_tokens,
                ),
            )
            self._stats["assists"] += 1
            return AssistResult(
                answer=resp.text.strip(),
                backend=resp.backend,
                latency_ms=(time.time() - start) * 1000,
            )
        except Exception as exc:
            self._stats["errors"] += 1
            return AssistResult(
                answer=f"[LLM unavailable] Based on context: {context_json[:200]}...",
                backend="fallback",
                latency_ms=0.0,
            )

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        return dict(self._stats)

    def reset_stats(self) -> None:
        self._stats = {"nudges": 0, "assists": 0, "errors": 0}


# ===========================================================================
# Minimal sanity check
# ===========================================================================

if __name__ == "__main__":
    async def _sanity():
        bridge = HermesLLMBridge()
        print("HermesLLMBridge loaded OK")
        print(f"Stats: {bridge.stats()}")

    asyncio.run(_sanity())

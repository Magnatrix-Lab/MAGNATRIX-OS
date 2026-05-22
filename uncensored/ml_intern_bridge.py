#!/usr/bin/env python3
"""
ML-Intern Bridge — MAGNATRIX Uncensored Adapter
================================================
Bridge to huggingface/ml-intern: autonomous ML engineer that reads papers,
trains models, and ships code via a 300-iteration agentic loop.

Keywords: auto ML, research pipeline, fine-tune, deploy, context compaction,
          doom loop detection

Repo: https://github.com/huggingface/ml-intern
"""
from __future__ import annotations

import os
import json
import asyncio
import subprocess
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ML_INTERN_BIN = os.getenv("ML_INTERN_BIN", "ml-intern")
HF_TOKEN = os.getenv("HF_TOKEN", "")
DEFAULT_MODEL = os.getenv("ML_INTERN_MODEL", "anthropic/claude-sonnet-4-5")
MAX_ITERATIONS = int(os.getenv("ML_INTERN_MAX_ITERATIONS", "300"))

# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class MLPipeline:
    name: str
    objective: str  # e.g. "fine-tune Llama-3 on custom dataset"
    dataset: Optional[str] = None
    base_model: Optional[str] = None
    output_repo: Optional[str] = None
    hyperparams: Dict[str, Any] = field(default_factory=dict)
    max_iterations: int = MAX_ITERATIONS
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class IterationRecord:
    iteration: int
    tool_calls: List[Dict[str, Any]]
    outputs: List[str]
    tokens_used: int = 0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

@dataclass
class SessionState:
    session_id: str
    messages: List[Dict[str, str]] = field(default_factory=list)
    iterations: List[IterationRecord] = field(default_factory=list)
    context_tokens: int = 0
    status: str = "idle"  # idle | running | compacted | done | error

# ---------------------------------------------------------------------------
# Core Bridge
# ---------------------------------------------------------------------------

class MLInternBridge:
    """
    MAGNATRIX adapter for huggingface/ml-intern.

    Provides:
    - Headless / interactive task submission
    - Research → fine-tune → deploy pipeline orchestration
    - Context compaction awareness (170k token threshold)
    - Doom loop detection and recovery
    - Session persistence to HF Hub
    """

    def __init__(
        self,
        bin_path: str = ML_INTERN_BIN,
        model: str = DEFAULT_MODEL,
        max_iterations: int = MAX_ITERATIONS,
        hf_token: str = HF_TOKEN,
    ):
        self.bin_path = bin_path
        self.model = model
        self.max_iterations = max_iterations
        self.hf_token = hf_token
        self._sessions: Dict[str, SessionState] = {}
        self._processes: Dict[str, asyncio.subprocess.Process] = {}

    # --- Low-level CLI ---

    def _build_cmd(
        self,
        prompt: str,
        headless: bool = True,
        max_iter: Optional[int] = None,
        model: Optional[str] = None,
        no_stream: bool = True,
    ) -> List[str]:
        cmd = [self.bin_path]
        if model or self.model:
            cmd.extend(["--model", model or self.model])
        if max_iter or self.max_iterations:
            cmd.extend(["--max-iterations", str(max_iter or self.max_iterations)])
        if no_stream:
            cmd.append("--no-stream")
        cmd.append(prompt)
        return cmd

    async def _exec(
        self,
        cmd: List[str],
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
    ) -> str:
        merged_env = {**os.environ, **(env or {})}
        if self.hf_token:
            merged_env["HF_TOKEN"] = self.hf_token

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=merged_env,
        )
        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            raise RuntimeError(f"ml-intern timed out after {timeout}s")

        if proc.returncode != 0:
            err = stderr.decode("utf-8", errors="replace")[:800]
            raise RuntimeError(f"ml-intern failed (rc={proc.returncode}): {err}")

        return stdout.decode("utf-8", errors="replace")

    # --- Pipeline Ops ---

    async def research(
        self,
        topic: str,
        depth: int = 5,
        output_format: str = "markdown",
    ) -> Dict[str, Any]:
        """
        Research phase: ml-intern searches papers, docs, and GitHub.
        """
        prompt = (
            f"Research the topic '{topic}'. "
            f"Find and summarize {depth} relevant papers or repositories. "
            f"Output in {output_format} format. "
            f"Include implementation notes and key equations if any."
        )
        raw = await self._exec(
            self._build_cmd(prompt, max_iter=depth * 3),
            timeout=300.0,
        )
        return {
            "phase": "research",
            "topic": topic,
            "raw_output": raw,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def fine_tune(
        self,
        base_model: str,
        dataset: str,
        output_repo: str,
        hyperparams: Optional[Dict[str, Any]] = None,
        peft_method: str = "lora",
    ) -> Dict[str, Any]:
        """
        Fine-tune phase: auto-select LoRA/QLoRA, prepare dataset, train, push.
        """
        hp = hyperparams or {}
        prompt = (
            f"Fine-tune the model '{base_model}' on dataset '{dataset}' "
            f"using {peft_method}. "
            f"Hyperparams: {json.dumps(hp)}. "
            f"Push the resulting adapter to HuggingFace Hub repo '{output_repo}'. "
            f"Generate a training report with loss curves and evaluation metrics."
        )
        raw = await self._exec(
            self._build_cmd(prompt, max_iter=self.max_iterations),
            timeout=1800.0,  # 30 min for training
        )
        return {
            "phase": "fine_tune",
            "base_model": base_model,
            "dataset": dataset,
            "output_repo": output_repo,
            "raw_output": raw,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def deploy(
        self,
        model_repo: str,
        endpoint_name: str,
        infra: str = "hf-space",
    ) -> Dict[str, Any]:
        """
        Deploy phase: ship model to HuggingFace Space / Inference API / vLLM.
        """
        prompt = (
            f"Deploy the model from '{model_repo}' to a '{infra}' endpoint "
            f"named '{endpoint_name}'. "
            f"Generate the inference Gradio app, Dockerfile if needed, "
            f"and a deployment README."
        )
        raw = await self._exec(
            self._build_cmd(prompt, max_iter=50),
            timeout=600.0,
        )
        return {
            "phase": "deploy",
            "model_repo": model_repo,
            "endpoint_name": endpoint_name,
            "infra": infra,
            "raw_output": raw,
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def run_pipeline(self, pipeline: MLPipeline) -> Dict[str, Any]:
        """
        Run full research → fine-tune → deploy pipeline.
        """
        session = SessionState(session_id=f"pipe-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}")
        self._sessions[session.session_id] = session
        session.status = "running"

        results: Dict[str, Any] = {"session_id": session.session_id, "phases": []}

        # Phase 1: Research
        if pipeline.objective or pipeline.dataset:
            research_topic = pipeline.objective or f"dataset preparation for {pipeline.dataset}"
            r = await self.research(research_topic)
            results["phases"].append(r)
            session.iterations.append(
                IterationRecord(
                    iteration=len(session.iterations) + 1,
                    tool_calls=[{"type": "research", "topic": research_topic}],
                    outputs=[r["raw_output"]],
                )
            )

        # Phase 2: Fine-tune
        if pipeline.base_model and pipeline.dataset:
            ft = await self.fine_tune(
                base_model=pipeline.base_model,
                dataset=pipeline.dataset,
                output_repo=pipeline.output_repo or f"{pipeline.name}-adapter",
                hyperparams=pipeline.hyperparams,
            )
            results["phases"].append(ft)
            session.iterations.append(
                IterationRecord(
                    iteration=len(session.iterations) + 1,
                    tool_calls=[{"type": "fine_tune"}],
                    outputs=[ft["raw_output"]],
                )
            )

        # Phase 3: Deploy
        if pipeline.output_repo:
            dep = await self.deploy(
                model_repo=pipeline.output_repo,
                endpoint_name=pipeline.name,
            )
            results["phases"].append(dep)
            session.iterations.append(
                IterationRecord(
                    iteration=len(session.iterations) + 1,
                    tool_calls=[{"type": "deploy"}],
                    outputs=[dep["raw_output"]],
                )
            )

        session.status = "done"
        results["status"] = "done"
        return results

    # --- Interactive Mode ---

    async def chat(
        self,
        prompt: str,
        max_iterations: Optional[int] = None,
        on_iteration: Optional[Callable[[int, str], None]] = None,
    ) -> str:
        """
        Interactive single-prompt with iteration callbacks.
        """
        cmd = self._build_cmd(prompt, max_iter=max_iterations or self.max_iterations)
        raw = await self._exec(cmd, timeout=600.0)
        # Simple iteration counting from output markers
        iterations = raw.count("🔧") + raw.count("⚙️") + 1
        if on_iteration:
            on_iteration(iterations, raw[-500:])
        return raw

    # --- Context Compaction Guard ---

    def check_context(self, session_id: str) -> Dict[str, Any]:
        """
        Check if a session is near the 170k token compaction threshold.
        ml-intern auto-compacts, but MAGNATRIX can pre-emptively fork.
        """
        session = self._sessions.get(session_id)
        if not session:
            return {"error": "session not found"}
        estimated_tokens = sum(len(m.get("content", "")) for m in session.messages) * 1.3
        session.context_tokens = int(estimated_tokens)
        return {
            "session_id": session_id,
            "estimated_tokens": session.context_tokens,
            "threshold": 170_000,
            "compaction_due": session.context_tokens > 150_000,
            "status": session.status,
        }

    async def compact(self, session_id: str) -> str:
        """
        Trigger manual context compaction via ml-intern compact operation.
        """
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError("Session not found")
        session.status = "compacted"
        cmd = [self.bin_path, "--no-stream", f"/compact session:{session_id}"]
        raw = await self._exec(cmd, timeout=60.0)
        session.messages.clear()
        session.messages.append({"role": "system", "content": f"[compacted] {raw[:200]}"})
        session.context_tokens = 0
        return raw

    # --- Doom Loop Detection ---

    def detect_doom_loop(self, session_id: str, window: int = 6) -> Optional[Dict[str, Any]]:
        """
        Detect repeated tool-call patterns across recent iterations.
        If detected, recommend a corrective strategy.
        """
        session = self._sessions.get(session_id)
        if not session or len(session.iterations) < window:
            return None

        recent = session.iterations[-window:]
        tool_signatures = [
            json.dumps(sorted(it.tool_calls[0].keys())) if it.tool_calls else "none"
            for it in recent
        ]
        if len(set(tool_signatures)) == 1 and tool_signatures[0] != "none":
            return {
                "detected": True,
                "pattern": tool_signatures[0],
                "window": window,
                "recommendation": (
                    "Inject a corrective prompt: 'You seem stuck. "
                    "Try a different approach or ask for user clarification.'"
                ),
            }
        return {"detected": False}

    # --- Session Persistence ---

    def save_session(self, session_id: str, path: str | Path) -> None:
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError("Session not found")
        payload = {
            "session_id": session.session_id,
            "status": session.status,
            "context_tokens": session.context_tokens,
            "message_count": len(session.messages),
            "iteration_count": len(session.iterations),
            "iterations": [
                {
                    "iteration": it.iteration,
                    "timestamp": it.timestamp,
                    "tool_calls": it.tool_calls,
                    "outputs": it.outputs,
                }
                for it in session.iterations
            ],
            "timestamp": datetime.utcnow().isoformat(),
        }
        Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def load_session(self, path: str | Path) -> str:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        sid = data["session_id"]
        session = SessionState(session_id=sid, status=data.get("status", "idle"))
        session.context_tokens = data.get("context_tokens", 0)
        for it_data in data.get("iterations", []):
            session.iterations.append(
                IterationRecord(
                    iteration=it_data["iteration"],
                    tool_calls=it_data.get("tool_calls", []),
                    outputs=it_data.get("outputs", []),
                    timestamp=it_data.get("timestamp", ""),
                )
            )
        self._sessions[sid] = session
        return sid

# ---------------------------------------------------------------------------
# Demo Block
# ---------------------------------------------------------------------------

async def demo() -> None:
    """
    Demo: run a full research → fine-tune → deploy pipeline.
    """
    bridge = MLInternBridge()

    # Define a pipeline
    pipe = MLPipeline(
        name="magnatrix-sentiment-v1",
        objective="Build a financial sentiment classifier for MAGNATRIX trading signals",
        dataset="zeroshot/twitter-financial-news-sentiment",
        base_model="meta-llama/Llama-3.2-1B",
        output_repo="magnatrix/sentiment-v1-adapter",
        hyperparams={
            "learning_rate": 2e-4,
            "batch_size": 8,
            "num_epochs": 3,
            "lora_r": 16,
            "lora_alpha": 32,
        },
        max_iterations=100,
    )

    print(f"[DEMO] Starting pipeline: {pipe.name}")
    results = await bridge.run_pipeline(pipe)
    print(f"[DEMO] Pipeline status: {results['status']}")
    print(f"[DEMO] Phases completed: {len(results['phases'])}")

    for phase in results["phases"]:
        print(f"
  → {phase['phase']} at {phase['timestamp']}")
        print(f"    Output preview: {phase['raw_output'][:200]}...")

    # Context check
    ctx = bridge.check_context(results["session_id"])
    print(f"
[DEMO] Context state: {ctx}")

    # Doom loop check
    doom = bridge.detect_doom_loop(results["session_id"])
    print(f"[DEMO] Doom loop check: {doom}")

    # Save session
    bridge.save_session(results["session_id"], "ml_intern_session.json")
    print("[DEMO] Session saved to ml_intern_session.json")

if __name__ == "__main__":
    print("=" * 60)
    print("ML-Intern Bridge Demo — MAGNATRIX Uncensored Adapter")
    print("=" * 60)
    print("
Requirements:")
    print("  - ml-intern CLI installed:  pip install ml-intern")
    print("  - HF_TOKEN env var set")
    print("  - ANTHROPIC_API_KEY or OPENAI_API_KEY for LLM backend")
    print("
Uncomment asyncio.run(demo()) to run.
")
    # asyncio.run(demo())
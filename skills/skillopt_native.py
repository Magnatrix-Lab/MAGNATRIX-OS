#!/usr/bin/env python3
"""skillopt_native.py — MAGNATRIX-OS Skills Layer
Native SkillOpt — Text-Space Skill Optimizer (AMATI-PELAJARI-TIRU dari Microsoft SkillOpt).

═══════════════════════════════════════════════════════════════════════════════
ReflACT Pipeline (6 stages):
  1. Rollout   — execute episodes with current skill, record trajectories
  2. Reflect   — analyze trajectories in minibatches, generate patches
  3. Aggregate — hierarchical merge of patches into coherent patch
  4. Select    — rank and clip edits (learning rate = edit budget)
  5. Update    — apply edits to skill document (optimizer.step)
  6. Evaluate  — validate on held-out set, accept/reject via gate

Core concepts:
  - Edit ops: append, insert_after, replace, delete
  - Patch: set of edits with reasoning
  - Gate: accept_new_best, accept, reject
  - Slow update region: protected section in skill document
  - Meta skill: optimizer-side guidance for long-horizon learning
  - Rejected-edit buffer: negative samples to avoid harmful repeats
  - Learning rate analog: edit budget per epoch (max edits per step)

Usage:
    optimizer = NativeSkillOptimizer(llm_fn=my_llm_callback)
    skill = "## Task: Solve math problems\n\n1. Read the problem carefully."
    best_skill = optimizer.train(
        skill=skill,
        task_fn=my_task_executor,  # executes task with skill, returns score
        val_task_fn=my_val_executor,
        epochs=5,
        edit_budget=4,
    )
    print(best_skill)
"""
from __future__ import annotations

import json
import random
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple

# ═══════════════════════════════════════════════════════════════════════════════
# Data Model
# ═══════════════════════════════════════════════════════════════════════════════

EditOp = Literal["append", "insert_after", "replace", "delete"]


@dataclass
class Edit:
    op: EditOp
    content: str = ""
    target: str = ""           # target text to replace/delete, or anchor for insert_after
    support_count: int = 1     # how many trajectories support this edit
    source_type: Literal["failure", "success"] = "failure"
    merge_level: int = 0

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"op": self.op, "content": self.content}
        if self.target:
            d["target"] = self.target
        if self.support_count != 1:
            d["support_count"] = self.support_count
        if self.source_type != "failure":
            d["source_type"] = self.source_type
        if self.merge_level:
            d["merge_level"] = self.merge_level
        return d


@dataclass
class Patch:
    edits: List[Edit] = field(default_factory=list)
    reasoning: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reasoning": self.reasoning,
            "edits": [e.to_dict() for e in self.edits],
        }


@dataclass
class Trajectory:
    """A single episode: observation → action → reward."""
    steps: List[Dict[str, Any]] = field(default_factory=list)
    score: float = 0.0
    success: bool = False
    task_id: str = ""

    def fmt(self, max_chars: int = 4000) -> str:
        lines = [f"Task: {self.task_id} | Score: {self.score} | Success: {self.success}"]
        for i, step in enumerate(self.steps):
            action = str(step.get("action", "?"))[:200]
            obs = str(step.get("obs", ""))[:300]
            lines.append(f"  Step {i}: {action}")
            if obs:
                lines.append(f"    → {obs}")
        text = "\n".join(lines)
        if len(text) > max_chars:
            half = max_chars // 2
            text = text[:half] + "\n...\n" + text[-half:]
        return text


@dataclass
class GateResult:
    action: Literal["accept_new_best", "accept", "reject"]
    current_skill: str
    current_score: float
    best_skill: str
    best_score: float
    best_step: int


# ═══════════════════════════════════════════════════════════════════════════════
# Edit Application (Update Stage)
# ═══════════════════════════════════════════════════════════════════════════════

SLOW_UPDATE_START = "<!-- SLOW_UPDATE_START -->"
SLOW_UPDATE_END = "<!-- SLOW_UPDATE_END -->"


class SkillDocument:
    """Represents a skill document with edit operations and protected regions."""

    def __init__(self, content: str) -> None:
        self.content = content

    def _in_slow_region(self, target: str) -> bool:
        start = self.content.find(SLOW_UPDATE_START)
        end = self.content.find(SLOW_UPDATE_END)
        if start == -1 or end == -1:
            return False
        idx = self.content.find(target)
        if idx == -1:
            return False
        return start <= idx < end + len(SLOW_UPDATE_END)

    def apply(self, edit: Edit) -> Tuple[str, Dict[str, Any]]:
        """Apply a single edit. Returns (new_content, report)."""
        report = {"op": edit.op, "target": edit.target[:100], "status": "unknown"}

        if edit.target and self._in_slow_region(edit.target):
            report["status"] = "skipped_protected_slow_update_region"
            return self.content, report

        if edit.op == "append":
            self.content = self.content.rstrip() + "\n\n" + edit.content.strip()
            report["status"] = "appended"
        elif edit.op == "insert_after":
            idx = self.content.find(edit.target)
            if idx == -1:
                report["status"] = "target_not_found"
                return self.content, report
            insert_after = idx + len(edit.target)
            self.content = self.content[:insert_after] + "\n" + edit.content + self.content[insert_after:]
            report["status"] = "inserted_after"
        elif edit.op == "replace":
            if edit.target not in self.content:
                report["status"] = "target_not_found"
                return self.content, report
            self.content = self.content.replace(edit.target, edit.content, 1)
            report["status"] = "replaced"
        elif edit.op == "delete":
            if edit.target not in self.content:
                report["status"] = "target_not_found"
                return self.content, report
            self.content = self.content.replace(edit.target, "", 1)
            report["status"] = "deleted"
        else:
            report["status"] = "unknown_op"
        return self.content, report

    def apply_patch(self, patch: Patch) -> Tuple[str, List[Dict[str, Any]]]:
        """Apply all edits in a patch. Returns (new_content, reports)."""
        reports = []
        for edit in patch.edits:
            self.content, report = self.apply(edit)
            reports.append(report)
        return self.content, reports


# ═══════════════════════════════════════════════════════════════════════════════
# Validation Gate
# ═══════════════════════════════════════════════════════════════════════════════

class ValidationGate:
    """Accept/reject candidate skills based on held-out performance."""

    @staticmethod
    def evaluate(
        candidate_skill: str,
        cand_score: float,
        current_skill: str,
        current_score: float,
        best_skill: str,
        best_score: float,
        best_step: int,
        global_step: int,
    ) -> GateResult:
        if cand_score > current_score:
            new_current = candidate_skill
            new_current_score = cand_score
            if cand_score > best_score:
                return GateResult(
                    action="accept_new_best",
                    current_skill=new_current,
                    current_score=new_current_score,
                    best_skill=candidate_skill,
                    best_score=cand_score,
                    best_step=global_step,
                )
            return GateResult(
                action="accept",
                current_skill=new_current,
                current_score=new_current_score,
                best_skill=best_skill,
                best_score=best_score,
                best_step=best_step,
            )
        return GateResult(
            action="reject",
            current_skill=current_skill,
            current_score=current_score,
            best_skill=best_skill,
            best_score=best_score,
            best_step=best_step,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Rollout Stage
# ═══════════════════════════════════════════════════════════════════════════════

class RolloutEngine:
    """Execute tasks with current skill and record trajectories."""

    def __init__(self, task_fn: Callable[[str, str], Tuple[float, List[Dict[str, Any]]]]) -> None:
        """task_fn(skill, task_input) → (score, steps)."""
        self.task_fn = task_fn

    def run(self, skill: str, tasks: List[str]) -> List[Trajectory]:
        trajectories = []
        for task in tasks:
            score, steps = self.task_fn(skill, task)
            traj = Trajectory(
                steps=steps, score=score,
                success=score >= 0.7, task_id=task[:50],
            )
            trajectories.append(traj)
        return trajectories


# ═══════════════════════════════════════════════════════════════════════════════
# Reflect Stage
# ═══════════════════════════════════════════════════════════════════════════════

class ReflectionEngine:
    """Analyze trajectories in minibatches and generate patches."""

    def __init__(self, llm_fn: Callable[[str, str], str]) -> None:
        """llm_fn(system_prompt, user_prompt) → response_text."""
        self.llm_fn = llm_fn

    def _fmt_minibatch(self, trajs: List[Trajectory], source_type: Literal["failure", "success"]) -> str:
        lines = [f"## Minibatch: {source_type.upper()} ({len(trajs)} trajectories)"]
        for t in trajs:
            lines.append(t.fmt())
        return "\n---\n".join(lines)

    def _call_analyst(self, skill: str, minibatch_text: str, source_type: Literal["failure", "success"]) -> Patch:
        system = (
            "You are a skill optimizer. Analyze the following trajectories and propose "
            "concrete edits to the skill document that would improve performance. "
            "Return JSON: {\"reasoning\": \"...\", \"edits\": [{\"op\": \"append|insert_after|replace|delete\", "
            "\"content\": \"...\", \"target\": \"...\"}]}. "
            f"Focus on {source_type} patterns."
        )
        user = f"## Current Skill\n{skill}\n\n{minibatch_text}"
        response = self.llm_fn(system, user)
        return self._parse_patch(response)

    def _parse_patch(self, text: str) -> Patch:
        try:
            # Extract JSON from response
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                data = json.loads(text[start:end+1])
                edits = []
                for e in data.get("edits", []):
                    edits.append(Edit(
                        op=e.get("op", "append"),
                        content=e.get("content", ""),
                        target=e.get("target", ""),
                        source_type=e.get("source_type", "failure"),
                    ))
                return Patch(edits=edits, reasoning=data.get("reasoning", ""))
        except Exception:
            pass
        return Patch(edits=[], reasoning="parse_failed")

    def run(self, skill: str, trajectories: List[Trajectory], minibatch_size: int = 4) -> List[Patch]:
        failures = [t for t in trajectories if not t.success]
        successes = [t for t in trajectories if t.success]
        patches = []

        for i in range(0, len(failures), minibatch_size):
            batch = failures[i:i+minibatch_size]
            text = self._fmt_minibatch(batch, "failure")
            patch = self._call_analyst(skill, text, "failure")
            for e in patch.edits:
                e.source_type = "failure"
                e.support_count = len(batch)
            patches.append(patch)

        for i in range(0, len(successes), minibatch_size):
            batch = successes[i:i+minibatch_size]
            text = self._fmt_minibatch(batch, "success")
            patch = self._call_analyst(skill, text, "success")
            for e in patch.edits:
                e.source_type = "success"
                e.support_count = len(batch)
            patches.append(patch)

        return patches


# ═══════════════════════════════════════════════════════════════════════════════
# Aggregate Stage
# ═══════════════════════════════════════════════════════════════════════════════

class AggregateEngine:
    """Hierarchical merge of patches into a single coherent patch."""

    def __init__(self, llm_fn: Callable[[str, str], str]) -> None:
        self.llm_fn = llm_fn

    def _merge_batch(self, skill: str, patches: List[Patch], level: int) -> Patch:
        if not patches:
            return Patch()
        if len(patches) == 1:
            return patches[0]

        system = (
            "Merge the following skill patches into a single coherent patch. "
            "Deduplicate edits, resolve conflicts, and prioritize failure-driven fixes. "
            "Return JSON: {\"reasoning\": \"...\", \"edits\": [{\"op\": \"...\", \"content\": \"...\", \"target\": \"...\"}]}"
        )
        patch_text = json.dumps([p.to_dict() for p in patches], ensure_ascii=False, indent=2)
        user = f"## Current Skill\n{skill}\n\n## Patches to merge ({len(patches)} patches, level {level})\n{patch_text}"
        response = self.llm_fn(system, user)

        try:
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1:
                data = json.loads(response[start:end+1])
                edits = []
                for e in data.get("edits", []):
                    edits.append(Edit(
                        op=e.get("op", "append"),
                        content=e.get("content", ""),
                        target=e.get("target", ""),
                        merge_level=level,
                    ))
                return Patch(edits=edits, reasoning=data.get("reasoning", "merged"))
        except Exception:
            pass

        # Fallback: concatenate all edits
        all_edits = []
        for p in patches:
            for e in p.edits:
                e.merge_level = level
                all_edits.append(e)
        return Patch(edits=all_edits, reasoning="fallback_concatenation")

    def run(self, skill: str, patches: List[Patch], batch_size: int = 4) -> Patch:
        current = list(patches)
        level = 0
        while len(current) > 1:
            level += 1
            next_level = []
            for i in range(0, len(current), batch_size):
                batch = current[i:i+batch_size]
                merged = self._merge_batch(skill, batch, level)
                next_level.append(merged)
            current = next_level
        return current[0] if current else Patch()


# ═══════════════════════════════════════════════════════════════════════════════
# Select Stage (Edit Budget / Learning Rate)
# ═══════════════════════════════════════════════════════════════════════════════

class SelectEngine:
    """Rank and clip edits — the 'learning rate' in text space."""

    def __init__(self, llm_fn: Callable[[str, str], str]) -> None:
        self.llm_fn = llm_fn

    def rank(self, skill: str, patch: Patch, budget: int) -> Patch:
        if len(patch.edits) <= budget:
            return patch

        system = (
            f"Rank the following edits by expected impact. Return the top {budget} edits only. "
            "Return JSON: {\"reasoning\": \"...\", \"edits\": [{\"op\": \"...\", \"content\": \"...\", \"target\": \"...\"}]}"
        )
        patch_text = json.dumps(patch.to_dict(), ensure_ascii=False, indent=2)
        user = f"## Current Skill\n{skill}\n\n## Edits to rank ({len(patch.edits)} total, budget={budget})\n{patch_text}"
        response = self.llm_fn(system, user)

        try:
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1:
                data = json.loads(response[start:end+1])
                edits = []
                for e in data.get("edits", [])[:budget]:
                    edits.append(Edit(
                        op=e.get("op", "append"),
                        content=e.get("content", ""),
                        target=e.get("target", ""),
                    ))
                return Patch(edits=edits, reasoning=data.get("reasoning", "ranked"))
        except Exception:
            pass

        # Fallback: keep highest support_count edits
        sorted_edits = sorted(patch.edits, key=lambda e: e.support_count, reverse=True)
        return Patch(edits=sorted_edits[:budget], reasoning="fallback_rank_by_support")


# ═══════════════════════════════════════════════════════════════════════════════
# Native Skill Optimizer (Unified Facade)
# ═══════════════════════════════════════════════════════════════════════════════

class NativeSkillOptimizer:
    """Native SkillOpt — text-space optimizer for agent skills.

    Trains a natural-language skill document as an external parameter
    of a frozen agent, using the ReflACT pipeline.
    """

    def __init__(self, llm_fn: Optional[Callable[[str, str], str]] = None) -> None:
        self.llm_fn = llm_fn or self._default_llm_fn
        self.reflection = ReflectionEngine(self.llm_fn)
        self.aggregate = AggregateEngine(self.llm_fn)
        self.select = SelectEngine(self.llm_fn)
        self.gate = ValidationGate()
        self.rejected_buffer: List[Edit] = []
        self.meta_skill: str = ""
        self.history: List[Dict[str, Any]] = []

    @staticmethod
    def _default_llm_fn(system: str, user: str) -> str:
        """Fallback LLM function — returns a mock patch for testing."""
        return json.dumps({
            "reasoning": "mock reflection",
            "edits": [{"op": "append", "content": "- Always verify your answer.", "target": ""}],
        })

    def train(
        self,
        skill: str,
        task_fn: Callable[[str, str], Tuple[float, List[Dict[str, Any]]]],
        val_task_fn: Callable[[str, str], Tuple[float, List[Dict[str, Any]]]],
        train_tasks: List[str],
        val_tasks: List[str],
        epochs: int = 5,
        edit_budget: int = 4,
        minibatch_size: int = 4,
    ) -> str:
        """Run full ReflACT training loop.

        Returns the best_skill document after all epochs.
        """
        current_skill = skill
        best_skill = skill
        current_score = 0.0
        best_score = 0.0
        best_step = 0

        rollout = RolloutEngine(task_fn)

        for epoch in range(1, epochs + 1):
            print(f"\n[SkillOpt] Epoch {epoch}/{epochs}")
            print(f"  Current score: {current_score:.3f} | Best: {best_score:.3f}")

            # ── 1. Rollout ────────────────────────────────────────────────────
            trajectories = rollout.run(current_skill, train_tasks)
            avg_score = sum(t.score for t in trajectories) / len(trajectories) if trajectories else 0.0
            print(f"  Rollout: {len(trajectories)} tasks, avg_score={avg_score:.3f}")

            # ── 2. Reflect ──────────────────────────────────────────────────────
            patches = self.reflection.run(current_skill, trajectories, minibatch_size)
            print(f"  Reflect: {len(patches)} patches generated")

            # Add rejected-buffer edits as negative guidance (meta skill)
            if self.rejected_buffer:
                meta_patch = Patch(
                    edits=[Edit(op="append", content="", target="")],  # placeholder
                    reasoning=f"Previously rejected: {len(self.rejected_buffer)} edits",
                )
                patches.append(meta_patch)

            # ── 3. Aggregate ────────────────────────────────────────────────────
            merged_patch = self.aggregate.run(current_skill, patches, batch_size=4)
            print(f"  Aggregate: {len(merged_patch.edits)} edits")

            # ── 4. Select (clip by budget = learning rate) ──────────────────────
            selected_patch = self.select.rank(current_skill, merged_patch, edit_budget)
            print(f"  Select: {len(selected_patch.edits)} edits (budget={edit_budget})")

            # ── 5. Update ────────────────────────────────────────────────────────
            doc = SkillDocument(current_skill)
            candidate_skill, reports = doc.apply_patch(selected_patch)
            print(f"  Update: applied {len([r for r in reports if r['status'] not in ('target_not_found', 'parse_failed')])} edits")

            # ── 6. Evaluate (Gate) ───────────────────────────────────────────────
            val_trajs = RolloutEngine(val_task_fn).run(candidate_skill, val_tasks)
            cand_score = sum(t.score for t in val_trajs) / len(val_trajs) if val_trajs else 0.0

            result = self.gate.evaluate(
                candidate_skill, cand_score,
                current_skill, current_score,
                best_skill, best_score, best_step,
                global_step=epoch,
            )

            print(f"  Gate: {result.action} (cand={cand_score:.3f} vs current={current_score:.3f})")

            if result.action in ("accept_new_best", "accept"):
                current_skill = result.current_skill
                current_score = result.current_score
                if result.action == "accept_new_best":
                    best_skill = result.best_skill
                    best_score = result.best_score
                    best_step = result.best_step
            else:
                # Rejected: add edits to rejected buffer
                for edit in selected_patch.edits:
                    self.rejected_buffer.append(edit)
                print(f"  Rejected {len(selected_patch.edits)} edits → buffer (total {len(self.rejected_buffer)})")

            self.history.append({
                "epoch": epoch,
                "action": result.action,
                "current_score": current_score,
                "best_score": best_score,
                "edits_applied": len(selected_patch.edits),
            })

        print(f"\n[SkillOpt] Training complete. Best score: {best_score:.3f} (epoch {best_step})")
        return best_skill

    def status(self) -> Dict[str, Any]:
        return {
            "epochs": len(self.history),
            "best_score": max((h["best_score"] for h in self.history), default=0.0),
            "rejected_edits": len(self.rejected_buffer),
            "history": self.history,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Self-test
# ═══════════════════════════════════════════════════════════════════════════════

def _self_test() -> int:
    print("=" * 60)
    print("Native SkillOpt — Self Test")
    print("=" * 60)
    passed = 0
    total = 8

    # Test 1: SkillDocument apply
    print("[Test 1] SkillDocument edit application")
    doc = SkillDocument("## Skill\n\n1. Do X.")
    new_content, report = doc.apply(Edit(op="append", content="2. Do Y."))
    ok = "2. Do Y." in new_content and report["status"] == "appended"
    print(f"  Append works: {ok} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    # Test 2: Replace edit
    print("[Test 2] Replace edit")
    doc2 = SkillDocument("Use tool A for math.")
    new2, rep2 = doc2.apply(Edit(op="replace", target="tool A", content="tool B"))
    ok2 = "tool B" in new2 and rep2["status"] == "replaced"
    print(f"  Replace works: {ok2} — {'PASS' if ok2 else 'FAIL'}")
    passed += ok2

    # Test 3: Delete edit
    print("[Test 3] Delete edit")
    doc3 = SkillDocument("Remove this line. Keep this.")
    new3, rep3 = doc3.apply(Edit(op="delete", target="Remove this line."))
    ok3 = "Remove this line." not in new3 and "Keep this." in new3
    print(f"  Delete works: {ok3} — {'PASS' if ok3 else 'FAIL'}")
    passed += ok3

    # Test 4: Protected slow region
    print("[Test 4] Protected slow update region")
    doc4 = SkillDocument(f"Header\n{SLOW_UPDATE_START}\nProtected\n{SLOW_UPDATE_END}\nFooter")
    new4, rep4 = doc4.apply(Edit(op="replace", target="Protected", content="Changed"))
    ok4 = "Protected" in new4 and rep4["status"] == "skipped_protected_slow_update_region"
    print(f"  Slow region protected: {ok4} — {'PASS' if ok4 else 'FAIL'}")
    passed += ok4

    # Test 5: Validation gate
    print("[Test 5] Validation gate")
    gate = ValidationGate()
    r = gate.evaluate("cand", 0.8, "curr", 0.6, "best", 0.7, 1, 2)
    ok5 = r.action == "accept_new_best"
    print(f"  Gate accept_new_best: {ok5} — {'PASS' if ok5 else 'FAIL'}")
    passed += ok5

    # Test 6: Gate reject
    print("[Test 6] Gate reject")
    r2 = gate.evaluate("cand", 0.5, "curr", 0.6, "best", 0.7, 1, 2)
    ok6 = r2.action == "reject"
    print(f"  Gate reject: {ok6} — {'PASS' if ok6 else 'FAIL'}")
    passed += ok6

    # Test 7: Full training loop (mock)
    print("[Test 7] Full training loop")
    def mock_task(skill: str, task: str) -> Tuple[float, List[Dict[str, Any]]]:
        # Simulate: skill improves score over time
        score = 0.5 + (0.1 if "verify" in skill else 0.0) + (0.1 if "careful" in skill else 0.0)
        return score, [{"action": "step", "obs": task}]

    optimizer = NativeSkillOptimizer()
    best = optimizer.train(
        skill="## Task\n\n1. Start.",
        task_fn=mock_task,
        val_task_fn=mock_task,
        train_tasks=["t1", "t2", "t3"],
        val_tasks=["v1", "v2"],
        epochs=3,
        edit_budget=2,
    )
    ok7 = len(best) > 0 and len(optimizer.history) == 3
    print(f"  Training loop completed: {ok7} — {'PASS' if ok7 else 'FAIL'}")
    passed += ok7

    # Test 8: Status report
    print("[Test 8] Status report")
    st = optimizer.status()
    ok8 = "epochs" in st and "best_score" in st and "rejected_edits" in st
    print(f"  Status valid: {ok8} — {'PASS' if ok8 else 'FAIL'}")
    passed += ok8

    print(f"\nPASS: {passed}/{total}")
    print("=" * 60)
    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())

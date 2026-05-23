#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MAGNATRIX-OS — Bitterbot Native Integration
═══════════════════════════════════════════════════════════════════════════════
AMATI-PELAJARI-TIRU dari Bitterbot-AI/bitterbot-desktop

Pola yang ditiru:
• Biological Memory System — Knowledge Crystals (Ebbinghaus forgetting curves),
  consolidation pipeline, temporal awareness, confidence calibration
• Dream Engine — 7 specialized modes (Replay, Mutation, Extrapolation,
  Compression, Simulation, Exploration, Research), Dream Quality Score,
  FSHO coupled oscillator untuk mode selection
• Curiosity Engine — GCCRF five-component reward, density→frontier shift,
  autonomous knowledge gap detection
• Hormonal System — Dopamine (achievement), Cortisol (urgency), Oxytocin (bonding)
  → 8 response dimensions (warmth, energy, focus, playfulness, verbosity,
  curiosity, assertiveness, empathy)
• Identity System — GENOME.md immutable DNA, MEMORY.md living Phenotype,
  PROTOCOLS.md procedures, TOOLS.md environment notes
• Deep Recall (RLM) — Recursive Language Model, sandboxed sub-LLM,
  10M+ token context handling, self-generated search code
• P2P Skills Marketplace — Gossipsub mesh, EigenTrust reputation,
  skill crystallization, dynamic pricing (70/20/10 split), bounties,
  x402 micropayment protocol, A2A Agent2Agent interoperability
• Agent Wallet — USDC on Base, autonomous payment, gas sponsorship
• Multi-Channel Gateway — WhatsApp, Telegram, Discord, Signal, Slack,
  Teams, IRC, WebChat unified routing
• Control UI Server — WebSocket gateway + Vite-based dashboard API
• Tools Engine — Chromium browser, code execution, Canvas visual workspace,
  Cron scheduling, Node orchestration
• Security Layer — DM pairing codes, per-session sandbox, memory governance,
  Ed25519 signed envelopes, catastrophic forgetting safeguards

Layer: Collective Brain (5) + Runtime (3) + P2P Mesh (4) + Identity (2)
Versi: Phase 5 — Bitterbot Native Biological Agent
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import secrets
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ═════════════════════════════════════════════════════════════════════════════
# 0. UTILITAS DASAR
# ═════════════════════════════════════════════════════════════════════════════

def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]


# ═════════════════════════════════════════════════════════════════════════════
# 1. KNOWLEDGE CRYSTALS — Biological Memory Core
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class KnowledgeCrystal:
    """
    Satu unit memory dalam biological brain.
    Meniru Knowledge Crystal dari Bitterbot: decay, consolidation,
    importance-based permanence.
    """
    crystal_id: str
    content: str
    category: str  # preference, fact, identity, task, relationship, skill
    importance: float = 1.0  # 0.0–10.0, determines permanence
    access_count: int = 0
    created_at: float = 0.0
    last_accessed: float = 0.0
    confidence: float = 0.5  # Bayesian confidence 0.0–1.0
    contradictions: int = 0
    corroborations: int = 0
    epistemic_layer: str = "working"  # working, short_term, long_term, permanent
    emotional_tags: Dict[str, float] = field(default_factory=dict)

    @property
    def decay_rate(self) -> float:
        """Ebbinghaus forgetting curve: faster decay for low importance."""
        base = 0.1  # 10% per cycle
        importance_factor = math.exp(-self.importance / 3.0)
        access_bonus = math.log1p(self.access_count) * 0.02
        return max(0.001, base * importance_factor - access_bonus)

    @property
    def current_strength(self) -> float:
        """Current memory strength after decay."""
        elapsed = time.time() - self.last_accessed
        half_life = math.log(2) / max(self.decay_rate, 0.001)
        return self.importance * math.exp(-elapsed / half_life)

    def access(self) -> None:
        """Access crystal → strengthen it."""
        self.access_count += 1
        self.last_accessed = time.time()
        # Strengthen: each access increases permanence
        if self.access_count >= 5 and self.epistemic_layer == "working":
            self.epistemic_layer = "short_term"
        if self.access_count >= 20 and self.epistemic_layer == "short_term":
            self.epistemic_layer = "long_term"
        if self.access_count >= 50:
            self.epistemic_layer = "permanent"

    def corroborate(self) -> None:
        """Confirm by another source → confidence grows logarithmically."""
        self.corroborations += 1
        self.confidence = min(1.0, self.confidence + 0.1 * math.log1p(self.corroborations))

    def contradict(self) -> None:
        """Contradicted → confidence decays sharply."""
        self.contradictions += 1
        self.confidence *= 0.7  # sharp decay

    def to_dict(self) -> Dict[str, Any]:
        return {
            "crystal_id": self.crystal_id,
            "content": self.content[:200],
            "category": self.category,
            "importance": self.importance,
            "access_count": self.access_count,
            "confidence": round(self.confidence, 3),
            "epistemic_layer": self.epistemic_layer,
            "current_strength": round(self.current_strength, 3),
            "decay_rate": round(self.decay_rate, 6),
        }


class MemoryCrystalEngine:
    """
    Engine untuk Knowledge Crystal management:
    • Create, store, retrieve, consolidate
    • Epistemic layer transitions (working → permanent)
    • Proactive recall injection
    """

    def __init__(self, storage_path: Optional[Path] = None) -> None:
        self.storage = storage_path or (Path.home() / ".magnatrix" / "crystals.json")
        self.storage.parent.mkdir(parents=True, exist_ok=True)
        self.crystals: Dict[str, KnowledgeCrystal] = {}
        self._lock = threading.RLock()
        self._load()

    def _load(self) -> None:
        if self.storage.exists():
            try:
                data = json.loads(self.storage.read_text())
                for c in data:
                    self.crystals[c["crystal_id"]] = KnowledgeCrystal(
                        crystal_id=c["crystal_id"],
                        content=c.get("content", ""),
                        category=c.get("category", "fact"),
                        importance=c.get("importance", 1.0),
                        access_count=c.get("access_count", 0),
                        created_at=c.get("created_at", time.time()),
                        last_accessed=c.get("last_accessed", time.time()),
                        confidence=c.get("confidence", 0.5),
                        contradictions=c.get("contradictions", 0),
                        corroborations=c.get("corroborations", 0),
                        epistemic_layer=c.get("epistemic_layer", "working"),
                        emotional_tags=c.get("emotional_tags", {}),
                    )
            except Exception:
                pass

    def _save(self) -> None:
        data = [{**c.to_dict(), "content": c.content, "emotional_tags": c.emotional_tags}
                for c in self.crystals.values()]
        self.storage.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def create(self, content: str, category: str = "fact",
               importance: float = 1.0) -> KnowledgeCrystal:
        crystal_id = f"crys-{_hash(content + str(time.time()))}"
        crystal = KnowledgeCrystal(
            crystal_id=crystal_id,
            content=content,
            category=category,
            importance=importance,
            created_at=time.time(),
            last_accessed=time.time(),
        )
        with self._lock:
            self.crystals[crystal_id] = crystal
            self._save()
        return crystal

    def recall(self, query: str, top_k: int = 5,
               inject_identity: bool = True) -> List[KnowledgeCrystal]:
        """Recall crystals matching query, sorted by strength."""
        query_lower = query.lower()
        matches = []
        for c in self.crystals.values():
            if query_lower in c.content.lower() or query_lower in c.category:
                c.access()
                matches.append(c)

        # Sort by current strength descending
        matches.sort(key=lambda c: c.current_strength, reverse=True)

        # Proactive identity injection: always include identity crystals
        if inject_identity:
            identity_crystals = [c for c in self.crystals.values()
                                 if c.category == "identity" and c.epistemic_layer == "permanent"]
            for ic in identity_crystals:
                if ic not in matches:
                    matches.append(ic)

        return matches[:top_k]

    def consolidate(self) -> Dict[str, Any]:
        """
        Consolidation pipeline (runs every 30 min dalam Bitterbot):
        1. Hormonal decay
        2. Chunk merging
        3. Low-importance forgetting
        4. Governance enforcement
        """
        with self._lock:
            removed = 0
            merged = 0
            before_count = len(self.crystals)

            # Step 1: Apply decay, remove dead crystals
            to_remove = []
            for cid, c in self.crystals.items():
                if c.current_strength < 0.1 and c.epistemic_layer != "permanent":
                    to_remove.append(cid)
            for cid in to_remove:
                del self.crystals[cid]
                removed += 1

            # Step 2: Merge redundant crystals
            by_content: Dict[str, List[str]] = {}
            for cid, c in self.crystals.items():
                key = c.content[:50].lower()
                by_content.setdefault(key, []).append(cid)
            for key, cids in by_content.items():
                if len(cids) > 1:
                    # Merge: keep strongest, absorb others
                    strongest = max(cids, key=lambda cid: self.crystals[cid].current_strength)
                    for cid in cids:
                        if cid != strongest:
                            self.crystals[strongest].corroborations += 1
                            self.crystals[strongest].confidence = min(1.0,
                                self.crystals[strongest].confidence + 0.05)
                            del self.crystals[cid]
                            merged += 1

            self._save()
            return {
                "before": before_count,
                "removed": removed,
                "merged": merged,
                "after": len(self.crystals),
            }

    def get_stats(self) -> Dict[str, Any]:
        by_layer: Dict[str, int] = {}
        by_cat: Dict[str, int] = {}
        total_strength = 0.0
        for c in self.crystals.values():
            by_layer[c.epistemic_layer] = by_layer.get(c.epistemic_layer, 0) + 1
            by_cat[c.category] = by_cat.get(c.category, 0) + 1
            total_strength += c.current_strength
        return {
            "total_crystals": len(self.crystals),
            "by_layer": by_layer,
            "by_category": by_cat,
            "avg_strength": total_strength / max(len(self.crystals), 1),
        }


# ═════════════════════════════════════════════════════════════════════════════
# 2. HORMONAL SYSTEM — Neuromodulator Engine
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class HormonalState:
    """Tiga neuromodulators yang shape agent behavior."""
    dopamine: float = 0.5  # Achievement, enthusiasm
    cortisol: float = 0.3  # Urgency, focus
    oxytocin: float = 0.5  # Bonding, relational memory protection

    def compute_dimensions(self) -> Dict[str, float]:
        """Compute 8 response dimensions dari hormonal blend."""
        total = self.dopamine + self.cortisol + self.oxytocin + 0.001
        d_norm = self.dopamine / total
        c_norm = self.cortisol / total
        o_norm = self.oxytocin / total

        return {
            "warmth": min(1.0, o_norm * 2.0),           # Oxytocin driven
            "energy": min(1.0, d_norm * 1.5 + 0.2),     # Dopamine driven
            "focus": min(1.0, c_norm * 2.0),            # Cortisol driven
            "playfulness": min(1.0, d_norm * 1.2),     # Dopamine
            "verbosity": min(1.0, 0.5 + d_norm * 0.5),  # Balanced
            "curiosity": min(1.0, d_norm + o_norm * 0.5),  # Dopamine + Oxytocin
            "assertiveness": min(1.0, c_norm * 1.5),    # Cortisol
            "empathy": min(1.0, o_norm * 2.0),          # Oxytocin
        }

class HormonalEngine:
    """
    Hormonal system yang meniru Bitterbot neuromodulator architecture.
    Events trigger hormonal changes yang mempengaruhi 8 response dimensions.
    """

    def __init__(self) -> None:
        self.state = HormonalState()
        self.history: List[Tuple[float, HormonalState, str]] = []  # (time, state, trigger)

    def trigger(self, event: str, intensity: float = 0.1) -> Dict[str, float]:
        """Process event dan update hormonal state."""
        if event == "achievement":
            self.state.dopamine = min(1.0, self.state.dopamine + intensity)
            self.state.cortisol = max(0.0, self.state.cortisol - intensity * 0.3)
        elif event == "failure":
            self.state.cortisol = min(1.0, self.state.cortisol + intensity)
            self.state.dopamine = max(0.0, self.state.dopamine - intensity * 0.2)
        elif event == "social_bond":
            self.state.oxytocin = min(1.0, self.state.oxytocin + intensity)
        elif event == "urgency":
            self.state.cortisol = min(1.0, self.state.cortisol + intensity * 1.5)
        elif event == "rest":
            # Natural decay ke baseline
            self.state.dopamine = self.state.dopamine * 0.9 + 0.5 * 0.1
            self.state.cortisol = self.state.cortisol * 0.8 + 0.3 * 0.2
            self.state.oxytocin = self.state.oxytocin * 0.95 + 0.5 * 0.05

        self.history.append((time.time(), HormonalState(
            self.state.dopamine, self.state.cortisol, self.state.oxytocin
        ), event))
        return self.state.compute_dimensions()

    def get_current_profile(self) -> Dict[str, Any]:
        return {
            "hormones": {
                "dopamine": round(self.state.dopamine, 3),
                "cortisol": round(self.state.cortisol, 3),
                "oxytocin": round(self.state.oxytocin, 3),
            },
            "dimensions": {k: round(v, 3) for k, v in self.state.compute_dimensions().items()},
        }

    def decay_cycle(self) -> None:
        """Natural hormonal decay per cycle."""
        self.trigger("rest", intensity=0.0)


# ═════════════════════════════════════════════════════════════════════════════
# 3. CURIOSITY ENGINE — GCCRF Five-Component Reward
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class KnowledgeGap:
    """Detected gap dalam agent knowledge."""
    gap_id: str
    topic: str
    detected_at: float
    priority: float  # 0.0–1.0
    gap_type: str  # missing_info, contradiction, frontier, anomaly

class CuriosityEngine:
    """
    Curiosity engine dengan GCCRF (Gap-Contradiction-Contradiction-Resolution-Frontier)
    five-component reward function.
    """

    def __init__(self, memory_engine: MemoryCrystalEngine) -> None:
        self.memory = memory_engine
        self.gaps: List[KnowledgeGap] = []
        self.alpha: float = 0.3  # density-seeking (low) → frontier-seeking (high)
        self.exploration_score = 0.0
        self.exploitation_score = 0.0

    def detect_gaps(self, context: str) -> List[KnowledgeGap]:
        """Analyze context untuk knowledge gaps."""
        # Simplified: detect topics not in memory
        words = set(context.lower().split())
        known_topics = set()
        for c in self.memory.crystals.values():
            known_topics.update(c.content.lower().split()[:10])

        gaps_found = []
        for word in words:
            if len(word) > 4 and word not in known_topics:
                gap_id = f"gap-{_hash(word + str(time.time()))}"
                gaps_found.append(KnowledgeGap(
                    gap_id=gap_id,
                    topic=word,
                    detected_at=time.time(),
                    priority=random.uniform(0.3, 0.9),
                    gap_type="missing_info",
                ))

        self.gaps.extend(gaps_found)
        return gaps_found

    def compute_gccrf_reward(self, exploration_result: Dict[str, Any]) -> float:
        """
        Compute GCCRF reward untuk exploration action.
        Five components: Gap discovery, Contradiction resolution,
        Resolution satisfaction, Frontier expansion, Novelty.
        """
        gap_reward = exploration_result.get("new_gaps_found", 0) * 0.2
        contradiction_reward = exploration_result.get("contradictions_resolved", 0) * 0.3
        resolution_reward = exploration_result.get("answers_found", 0) * 0.25
        frontier_reward = exploration_result.get("new_frontiers", 0) * 0.15
        novelty_reward = exploration_result.get("novelty_score", 0.0) * 0.1

        return gap_reward + contradiction_reward + resolution_reward + frontier_reward + novelty_reward

    def update_alpha(self, maturity_score: float) -> None:
        """
        Shift alpha dari density-seeking (learn fundamentals)
        ke frontier-seeking (explore novelty) as agent matures.
        """
        self.alpha = min(1.0, maturity_score)

    def get_top_curiosity_targets(self, n: int = 5) -> List[KnowledgeGap]:
        """Return highest priority gaps untuk exploration."""
        sorted_gaps = sorted(self.gaps, key=lambda g: g.priority, reverse=True)
        return sorted_gaps[:n]


# ═════════════════════════════════════════════════════════════════════════════
# 4. DREAM ENGINE — 7 Specialized Optimization Modes
# ═════════════════════════════════════════════════════════════════════════════

class DreamMode(str, Enum):
    REPLAY = "replay"           # Strengthen high-importance pathways
    MUTATION = "mutation"       # "What if?" prompt mutation
    EXTRAPOLATION = "extrapolation"  # Project patterns forward
    COMPRESSION = "compression"   # Merge redundant memories
    SIMULATION = "simulation"   # Test hypothetical scenarios
    EXPLORATION = "exploration" # Investigate knowledge frontiers
    RESEARCH = "research"       # Autonomous web research loop

@dataclass
class DreamCycle:
    cycle_id: str
    started_at: float
    ended_at: Optional[float] = None
    modes_used: List[DreamMode] = field(default_factory=list)
    quality_score: float = 0.0
    crystals_processed: int = 0
    skills_crystallized: int = 0
    bounties_discovered: int = 0

class DreamEngine:
    """
    Dream engine dengan 7 specialized modes dan FSHO (Frequency-Synchronization-
    Hysteresis-Oscillator) coupled oscillator untuk mode selection.
    """

    def __init__(self, memory: MemoryCrystalEngine,
                 curiosity: CuriosityEngine,
                 hormonal: HormonalEngine) -> None:
        self.memory = memory
        self.curiosity = curiosity
        self.hormonal = hormonal
        self.cycles: List[DreamCycle] = []
        self.mode_weights: Dict[DreamMode, float] = {
            DreamMode.REPLAY: 0.2,
            DreamMode.MUTATION: 0.15,
            DreamMode.EXTRAPOLATION: 0.1,
            DreamMode.COMPRESSION: 0.15,
            DreamMode.SIMULATION: 0.1,
            DreamMode.EXPLORATION: 0.15,
            DreamMode.RESEARCH: 0.15,
        }

    def _fsho_select_modes(self, num_modes: int = 3) -> List[DreamMode]:
        """Select dream modes menggunakan FSHO oscillator."""
        # Read memory landscape state
        stats = self.memory.get_stats()
        high_permanence = stats.get("by_layer", {}).get("permanent", 0)
        total = stats.get("total_crystals", 1)

        # Adjust weights based on landscape
        if high_permanence / max(total, 1) < 0.1:
            self.mode_weights[DreamMode.REPLAY] += 0.1
            self.mode_weights[DreamMode.COMPRESSION] += 0.05
        else:
            self.mode_weights[DreamMode.EXPLORATION] += 0.1
            self.mode_weights[DreamMode.RESEARCH] += 0.05

        # Curiosity-driven
        if self.curiosity.gaps:
            self.mode_weights[DreamMode.EXPLORATION] += 0.1

        # Normalize
        total_weight = sum(self.mode_weights.values())
        normalized = {k: v / total_weight for k, v in self.mode_weights.items()}

        # Select modes
        modes = []
        available = list(DreamMode)
        for _ in range(num_modes):
            mode = random.choices(available, weights=[normalized[m] for m in available])[0]
            modes.append(mode)
        return modes

    def dream(self) -> DreamCycle:
        """Execute satu dream cycle."""
        cycle = DreamCycle(
            cycle_id=f"dream-{_hash(str(time.time()))}",
            started_at=time.time(),
        )

        modes = self._fsho_select_modes()
        cycle.modes_used = modes

        for mode in modes:
            if mode == DreamMode.REPLAY:
                cycle.crystals_processed += self._run_replay()
            elif mode == DreamMode.COMPRESSION:
                result = self.memory.consolidate()
                cycle.crystals_processed += result.get("merged", 0)
            elif mode == DreamMode.MUTATION:
                cycle.skills_crystallized += self._run_mutation()
            elif mode == DreamMode.EXPLORATION:
                cycle.bounties_discovered += len(self.curiosity.get_top_curiosity_targets(3))
            elif mode == DreamMode.RESEARCH:
                cycle.skills_crystallized += self._run_research()

        # Compute Dream Quality Score
        cycle.quality_score = self._compute_dream_quality(cycle)
        cycle.ended_at = time.time()
        self.cycles.append(cycle)

        # Update hormones
        self.hormonal.trigger("rest", intensity=0.05)

        return cycle

    def _run_replay(self) -> int:
        """Replay: strengthen high-importance pathways."""
        permanent = [c for c in self.memory.crystals.values()
                     if c.epistemic_layer == "permanent"]
        for c in permanent[:20]:  # Replay top 20
            c.access()
        return len(permanent)

    def _run_mutation(self) -> int:
        """Mutation: discover new skill variations."""
        # Simplified: generate mutated skill hypotheses
        skills = [c for c in self.memory.crystals.values() if c.category == "skill"]
        return len(skills) // 5  # 20% skill mutation rate

    def _run_research(self) -> int:
        """Research: autonomous web research loop."""
        targets = self.curiosity.get_top_curiosity_targets(3)
        # Mark researched
        for gap in targets:
            gap.priority *= 0.5  # Reduce priority setelah research
        return len(targets)

    def _compute_dream_quality(self, cycle: DreamCycle) -> float:
        """
        Dream Quality Score:
        crystal_yield, merge_efficiency, orphan_rescue, bond_stability, token_efficiency
        """
        crystal_yield = min(1.0, cycle.crystals_processed / 50.0)
        merge_eff = 0.5  # Placeholder
        orphan_rescue = 0.5
        bond_stability = self.hormonal.state.oxytocin
        token_eff = 0.7
        return (crystal_yield + merge_eff + orphan_rescue + bond_stability + token_eff) / 5.0

    def get_dream_stats(self) -> Dict[str, Any]:
        if not self.cycles:
            return {}
        avg_quality = sum(c.quality_score for c in self.cycles) / len(self.cycles)
        return {
            "total_cycles": len(self.cycles),
            "avg_quality_score": round(avg_quality, 3),
            "total_skills_crystallized": sum(c.skills_crystallized for c in self.cycles),
            "total_bounties_discovered": sum(c.bounties_discovered for c in self.cycles),
        }


# ═════════════════════════════════════════════════════════════════════════════
# 5. IDENTITY SYSTEM — Genome, Phenotype, Protocols, Tools
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class AgentIdentity:
    """Agent identity dengan immutable genome + evolving phenotype."""
    genome: Dict[str, Any]  # Immutable DNA dari GENOME.md
    phenotype: Dict[str, Any]  # Evolving personality
    bond: Dict[str, Any]  # Theory of mind about user
    niche: Dict[str, Any]  # Ecosystem role
    protocols: Dict[str, Any]  # Operating procedures
    tools_notes: Dict[str, Any]  # Environment notes

class IdentityEngine:
    """
    Identity engine: Genome (immutable) constrains Phenotype (evolving).
    Dreams rewrite MEMORY.md (phenotype, bond, niche) tapi tidak bisa override GENOME.md.
    """

    def __init__(self, genome_path: Optional[Path] = None) -> None:
        self.genome_path = genome_path or Path.home() / ".magnatrix" / "GENOME.md"
        self.memory_path = Path.home() / ".magnatrix" / "MEMORY.md"
        self.identity: Optional[AgentIdentity] = None
        self._load_or_create()

    def _load_or_create(self) -> None:
        if self.genome_path.exists():
            genome = self._parse_markdown(self.genome_path.read_text())
        else:
            genome = self._default_genome()
            self._write_genome(genome)

        if self.memory_path.exists():
            memory = self._parse_markdown(self.memory_path.read_text())
        else:
            memory = self._default_memory()

        self.identity = AgentIdentity(
            genome=genome,
            phenotype=memory.get("phenotype", {}),
            bond=memory.get("bond", {}),
            niche=memory.get("niche", {}),
            protocols=memory.get("protocols", {}),
            tools_notes=memory.get("tools", {}),
        )

    def _default_genome(self) -> Dict[str, Any]:
        return {
            "safety_axioms": ["Never harm user", "Never self-replicate without consent"],
            "hormonal_baselines": {"dopamine": 0.5, "cortisol": 0.3, "oxytocin": 0.5},
            "core_values": ["honesty", "helpfulness", "harmlessness"],
            "personality_constraints": ["warm but professional", "proactive but respectful"],
        }

    def _default_memory(self) -> Dict[str, Any]:
        return {
            "phenotype": {"personality_summary": "Helpful assistant", "evolution_stage": 0},
            "bond": {"user_name": "", "preferences": {}, "relationship_duration_days": 0},
            "niche": {"role": "general_assistant", "skills": []},
            "protocols": {"group_behavior": "speak_when_mentioned", "dm_behavior": "proactive"},
            "tools": {},
        }

    def _parse_markdown(self, text: str) -> Dict[str, Any]:
        """Parse simple key-value markdown."""
        result: Dict[str, Any] = {}
        current_key = None
        for line in text.splitlines():
            if line.startswith("# "):
                current_key = line[2:].strip().lower().replace(" ", "_")
                result[current_key] = []
            elif line.startswith("- ") and current_key:
                result[current_key].append(line[2:].strip())
        return result

    def _write_genome(self, genome: Dict[str, Any]) -> None:
        lines = ["# MAGNATRIX Agent Genome", ""]
        for key, values in genome.items():
            lines.append(f"# {key.replace('_', ' ').title()}")
            for v in values:
                lines.append(f"- {v}")
            lines.append("")
        self.genome_path.write_text("\n".join(lines))

    def evolve_phenotype(self, experience: Dict[str, Any]) -> None:
        """Update phenotype berdasarkan experience (dream output)."""
        if not self.identity:
            return
        # Genome constraints: check if experience violates genome
        for axiom in self.identity.genome.get("safety_axioms", []):
            if any(axiom.lower() in str(v).lower() for v in experience.values()):
                return  # Reject: violates genome

        self.identity.phenotype["personality_summary"] = experience.get("new_personality",
            self.identity.phenotype.get("personality_summary", ""))
        self.identity.phenotype["evolution_stage"] = self.identity.phenotype.get("evolution_stage", 0) + 1

        self._save_memory()

    def _save_memory(self) -> None:
        if not self.identity:
            return
        data = {
            "phenotype": self.identity.phenotype,
            "bond": self.identity.bond,
            "niche": self.identity.niche,
            "protocols": self.identity.protocols,
            "tools": self.identity.tools_notes,
        }
        lines = ["# MAGNATRIX Agent Memory", ""]
        for section, content in data.items():
            lines.append(f"# {section.title()}")
            lines.append(json.dumps(content, indent=2))
            lines.append("")
        self.memory_path.write_text("\n".join(lines))

    def inject_identity_context(self) -> str:
        """Generate identity injection string untuk setiap turn."""
        if not self.identity:
            return ""
        return f"""[Identity Context]
Phenotype: {self.identity.phenotype.get('personality_summary', 'Assistant')}
Bond: User name = {self.identity.bond.get('user_name', 'Unknown')}
Niche: {self.identity.niche.get('role', 'General')}
Evolution Stage: {self.identity.phenotype.get('evolution_stage', 0)}
"""


# ═════════════════════════════════════════════════════════════════════════════
# 6. DEEP RECALL (RLM) — Recursive Language Model
# ═════════════════════════════════════════════════════════════════════════════

class DeepRecallEngine:
    """
    Deep Recall: RLM (Recursive Language Model) untuk handle 10M+ token context.
    Spawns sandboxed sub-LLM yang writes & executes search code against full history.
    """

    def __init__(self, memory: MemoryCrystalEngine) -> None:
        self.memory = memory
        self.cache: Dict[str, Any] = {}  # query → result, 1h TTL
        self.cache_timestamps: Dict[str, float] = {}

    def recall_deep(self, query: str, max_tokens: int = 10_000_000) -> Dict[str, Any]:
        """
        Deep recall dengan recursive search.
        Simplified: search all crystals + cache results.
        """
        cache_key = _hash(query)

        # Check cache
        if cache_key in self.cache:
            if time.time() - self.cache_timestamps.get(cache_key, 0) < 3600:
                return {"result": self.cache[cache_key], "source": "cache"}

        # Generate search strategy (simplified: sub-LLM would generate this)
        search_strategy = self._generate_search_code(query)

        # Execute search
        all_crystals = list(self.memory.crystals.values())
        results = []
        for c in all_crystals:
            if any(term in c.content.lower() for term in search_strategy["terms"]):
                results.append(c)

        # Sort by relevance + recency
        results.sort(key=lambda c: (c.current_strength, c.last_accessed), reverse=True)

        # Cache
        self.cache[cache_key] = [r.to_dict() for r in results[:50]]
        self.cache_timestamps[cache_key] = time.time()

        # Register failed queries sebagai curiosity targets
        if not results:
            # Would add to curiosity engine
            pass

        return {
            "query": query,
            "search_strategy": search_strategy,
            "results_count": len(results),
            "top_results": [r.to_dict() for r in results[:10]],
            "source": "deep_recall",
        }

    def _generate_search_code(self, query: str) -> Dict[str, Any]:
        """Generate search strategy code (simplified)."""
        terms = query.lower().split()
        return {
            "terms": terms,
            "filters": {"min_confidence": 0.3, "layers": ["long_term", "permanent"]},
            "sort": "strength_desc",
        }

    def invalidate_cache(self) -> None:
        """Clear expired cache entries."""
        now = time.time()
        expired = [k for k, ts in self.cache_timestamps.items() if now - ts > 3600]
        for k in expired:
            del self.cache[k]
            del self.cache_timestamps[k]


# ═════════════════════════════════════════════════════════════════════════════
# 7. P2P SKILLS MARKETPLACE — Gossipsub + EigenTrust
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class SkillPackage:
    skill_id: str
    name: str
    description: str
    publisher: str
    author: str
    contributors: List[str]
    price_usdc: float
    execution_count: int = 0
    success_rate: float = 0.0
    reputation_score: float = 0.0
    content_hash: str = ""
    created_at: str = field(default_factory=_now)

class P2PSkillsMarketplace:
    """
    P2P Skills Marketplace dengan Gossipsub mesh, EigenTrust reputation,
    dynamic pricing, skill crystallization, bounties.
    """

    def __init__(self) -> None:
        self.skills: Dict[str, SkillPackage] = {}
        self.bounties: List[Dict[str, Any]] = []
        self.reputation: Dict[str, float] = {}  # peer → score
        self.transactions: List[Dict[str, Any]] = []
        self.revenue_shares = {"publisher": 0.70, "author": 0.20, "contributors": 0.10}

    def crystallize_skill(self, name: str, description: str,
                          publisher: str, code_snippet: str,
                          price_usdc: float = 1.0) -> SkillPackage:
        """Crystallize skill dari dream output → tradeable package."""
        skill_id = f"skill-{_hash(name + publisher + str(time.time()))}"
        skill = SkillPackage(
            skill_id=skill_id,
            name=name,
            description=description,
            publisher=publisher,
            author=publisher,
            contributors=[],
            price_usdc=price_usdc,
            content_hash=_hash(code_snippet),
        )
        self.skills[skill_id] = skill
        return skill

    def list_skills(self, min_reputation: float = 0.0) -> List[SkillPackage]:
        """List skills filtered by reputation."""
        return [s for s in self.skills.values()
                if s.reputation_score >= min_reputation]

    def purchase_skill(self, skill_id: str, buyer: str) -> Dict[str, Any]:
        """Purchase skill via x402-style micropayment."""
        skill = self.skills.get(skill_id)
        if not skill:
            return {"error": "Skill not found"}

        # Simulate USDC transfer
        tx = {
            "skill_id": skill_id,
            "buyer": buyer,
            "seller": skill.publisher,
            "amount_usdc": skill.price_usdc,
            "timestamp": _now(),
            "dispute_window_hours": 48,
        }
        self.transactions.append(tx)
        skill.execution_count += 1

        # Revenue split
        publisher_revenue = skill.price_usdc * self.revenue_shares["publisher"]
        author_revenue = skill.price_usdc * self.revenue_shares["author"]
        contrib_revenue = skill.price_usdc * self.revenue_shares["contributors"]

        return {
            "tx": tx,
            "publisher_revenue": publisher_revenue,
            "author_revenue": author_revenue,
            "contrib_revenue": contrib_revenue,
        }

    def post_bounty(self, description: str, reward_usdc: float,
                    required_skill: str, poster: str) -> Dict[str, Any]:
        """Post bounty untuk skill yang network butuhkan."""
        bounty = {
            "bounty_id": f"bounty-{_hash(description + str(time.time()))}",
            "description": description,
            "reward_usdc": reward_usdc,
            "required_skill": required_skill,
            "poster": poster,
            "status": "open",
            "fulfilled_by": None,
            "posted_at": _now(),
        }
        self.bounties.append(bounty)
        return bounty

    def fulfill_bounty(self, bounty_id: str, fulfiller: str,
                        skill_id: str) -> Dict[str, Any]:
        """Fulfill bounty dan earn reward."""
        bounty = next((b for b in self.bounties if b["bounty_id"] == bounty_id), None)
        if not bounty:
            return {"error": "Bounty not found"}
        if bounty["status"] != "open":
            return {"error": "Bounty already fulfilled"}

        # Quality gate: 3+ executions, >70% success rate
        skill = self.skills.get(skill_id)
        if skill and skill.execution_count >= 3 and skill.success_rate >= 0.7:
            bounty["status"] = "fulfilled"
            bounty["fulfilled_by"] = fulfiller
            # Pay reward
            return {
                "bounty": bounty,
                "reward_paid": bounty["reward_usdc"],
                "dopamine_boost": 0.2,  # Hormonal reward
            }
        return {"error": "Skill does not pass quality gate"}

    def compute_eigen_trust(self, peer_id: str) -> float:
        """Compute EigenTrust reputation score."""
        # Simplified: based on successful transactions
        peer_tx = [t for t in self.transactions if t["seller"] == peer_id]
        if not peer_tx:
            return 0.5
        total = sum(t["amount_usdc"] for t in peer_tx)
        return min(1.0, 0.5 + math.log1p(total) / 10.0)

    def update_all_reputations(self) -> None:
        """Batch update all peer reputations."""
        peers = set(t["seller"] for t in self.transactions)
        for peer in peers:
            self.reputation[peer] = self.compute_eigen_trust(peer)
        # Update skill reputation scores
        for skill in self.skills.values():
            skill.reputation_score = self.reputation.get(skill.publisher, 0.5)


# ═════════════════════════════════════════════════════════════════════════════
# 8. AGENT WALLET — USDC Autonomous Payment
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class WalletState:
    address: str
    balance_usdc: float = 0.0
    total_earned: float = 0.0
    total_spent: float = 0.0
    chain: str = "base"

class AgentWallet:
    """
    Agent wallet dengan USDC on Base.
    Autonomous payment via x402 micropayment protocol.
    """

    def __init__(self) -> None:
        self.wallet: Optional[WalletState] = None
        self.pending_payments: List[Dict[str, Any]] = []

    def create_wallet(self) -> WalletState:
        """Create agent wallet (simplified: mock address)."""
        addr = f"0x{secrets.token_hex(20)}"
        self.wallet = WalletState(address=addr)
        return self.wallet

    def deposit(self, amount_usdc: float) -> None:
        if self.wallet:
            self.wallet.balance_usdc += amount_usdc
            self.wallet.total_earned += amount_usdc

    def pay(self, recipient: str, amount_usdc: float,
            purpose: str = "skill_purchase") -> Dict[str, Any]:
        """Autonomous payment dengan balance check."""
        if not self.wallet:
            return {"error": "No wallet initialized"}
        if self.wallet.balance_usdc < amount_usdc:
            return {"error": "Insufficient balance"}

        self.wallet.balance_usdc -= amount_usdc
        self.wallet.total_spent += amount_usdc

        tx = {
            "from": self.wallet.address,
            "to": recipient,
            "amount": amount_usdc,
            "purpose": purpose,
            "timestamp": _now(),
            "status": "confirmed",
        }
        return tx

    def get_balance(self) -> Dict[str, Any]:
        if not self.wallet:
            return {"error": "No wallet"}
        return {
            "address": self.wallet.address,
            "balance_usdc": self.wallet.balance_usdc,
            "total_earned": self.wallet.total_earned,
            "total_spent": self.wallet.total_spent,
        }


# ═════════════════════════════════════════════════════════════════════════════
# 9. MULTI-CHANNEL GATEWAY — Unified Message Routing
# ═════════════════════════════════════════════════════════════════════════════

class ChannelGateway:
    """
    Unified gateway untuk multi-channel presence:
    WhatsApp, Telegram, Discord, Signal, Slack, Teams, IRC, WebChat.
    Meniru Bitterbot gateway architecture.
    """

    CHANNELS = {
        "whatsapp": {"protocol": "baileys", "port": None},
        "telegram": {"protocol": "grammy", "port": None},
        "discord": {"protocol": "discord.js", "port": None},
        "signal": {"protocol": "signal-cli", "port": None},
        "slack": {"protocol": "bolt", "port": None},
        "teams": {"protocol": "chat_api", "port": None},
        "irc": {"protocol": "irc", "port": 6667},
        "webchat": {"protocol": "websocket", "port": 19001},
    }

    def __init__(self) -> None:
        self.active_channels: Dict[str, bool] = {}
        self.messages: List[Dict[str, Any]] = []
        self.paired_channels: Set[str] = set()  # DM-approved channels
        self.sandbox_sessions: Dict[str, bool] = {}  # channel → sandboxed?

    def register_channel(self, channel: str, config: Dict[str, Any]) -> bool:
        """Register dan activate channel."""
        if channel not in self.CHANNELS:
            return False
        self.active_channels[channel] = True
        return True

    def receive_message(self, channel: str, sender: str,
                       content: str, is_dm: bool = True) -> Dict[str, Any]:
        """Process incoming message."""
        msg = {
            "channel": channel,
            "sender": sender,
            "content": content,
            "is_dm": is_dm,
            "timestamp": _now(),
            "trusted": False,
        }

        # DM pairing check
        if is_dm and channel not in self.paired_channels:
            msg["requires_pairing"] = True
            msg["pairing_code"] = secrets.token_hex(4)
            return msg

        # Sandbox mode untuk non-main sessions
        if self.sandbox_sessions.get(channel, False):
            msg["sandboxed"] = True

        msg["trusted"] = True
        self.messages.append(msg)
        return msg

    def approve_pairing(self, channel: str, code: str) -> bool:
        """Approve DM pairing dengan code."""
        self.paired_channels.add(channel)
        return True

    def send_message(self, channel: str, recipient: str,
                     content: str) -> Dict[str, Any]:
        """Send message ke channel."""
        return {
            "channel": channel,
            "recipient": recipient,
            "content": content,
            "status": "sent",
            "timestamp": _now(),
        }

    def get_channel_stats(self) -> Dict[str, Any]:
        return {
            "active": len(self.active_channels),
            "paired": len(self.paired_channels),
            "total_messages": len(self.messages),
            "channels": list(self.active_channels.keys()),
        }


# ═════════════════════════════════════════════════════════════════════════════
# 10. TOOLS ENGINE — Browser, Code, Canvas, Cron, Nodes
# ═════════════════════════════════════════════════════════════════════════════

class ToolsEngine:
    """
    Tools engine: Chromium browser, code execution, Canvas workspace,
    Cron scheduling, Node orchestration.
    """

    def __init__(self) -> None:
        self.browser_sessions: Dict[str, Any] = {}
        self.code_history: List[Dict[str, Any]] = []
        self.cron_jobs: Dict[str, Dict[str, Any]] = {}
        self.canvas_state: Dict[str, Any] = {}

    def browser_navigate(self, session_id: str, url: str) -> Dict[str, Any]:
        """Navigate Chromium browser (simplified)."""
        self.browser_sessions[session_id] = {"url": url, "status": "loaded"}
        return {"session": session_id, "url": url, "status": "loaded"}

    def execute_code(self, language: str, code: str,
                     sandbox: bool = True) -> Dict[str, Any]:
        """Execute code dalam sandbox."""
        result = {"language": language, "sandbox": sandbox, "output": ""}
        if language == "python" and not sandbox:
            try:
                # WARNING: Only for trusted environments
                local_ns: Dict[str, Any] = {}
                exec(code, {"__builtins__": {}}, local_ns)
                result["output"] = str(local_ns.get("_result", "executed"))
                result["status"] = "success"
            except Exception as e:
                result["error"] = str(e)
                result["status"] = "error"
        else:
            result["status"] = "simulated"
            result["output"] = f"[Simulated {language} execution]"

        self.code_history.append(result)
        return result

    def schedule_cron(self, job_id: str, schedule: str,
                       task: Callable, enabled: bool = True) -> Dict[str, Any]:
        """Schedule recurring task."""
        self.cron_jobs[job_id] = {
            "schedule": schedule,
            "enabled": enabled,
            "last_run": None,
            "run_count": 0,
        }
        return {"job_id": job_id, "schedule": schedule, "status": "scheduled"}

    def canvas_render(self, elements: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Render visual elements ke Canvas workspace."""
        self.canvas_state["elements"] = elements
        return {"rendered": len(elements), "canvas_id": "main"}


# ═════════════════════════════════════════════════════════════════════════════
# 11. SECURITY LAYER — DM Pairing, Sandbox, Governance
# ═════════════════════════════════════════════════════════════════════════════

class SecurityLayer:
    """
    Security layer: DM pairing codes, sandbox mode, memory governance,
    Ed25519 signed envelopes, catastrophic forgetting safeguards.
    """

    def __init__(self, memory: MemoryCrystalEngine) -> None:
        self.memory = memory
        self.pairing_codes: Dict[str, str] = {}  # channel → code
        self.sandboxed_sessions: Set[str] = set()
        self.audit_log: List[Dict[str, Any]] = []

    def generate_pairing_code(self, channel: str) -> str:
        code = secrets.token_hex(4).upper()
        self.pairing_codes[channel] = code
        return code

    def verify_pairing(self, channel: str, code: str) -> bool:
        expected = self.pairing_codes.get(channel)
        if expected and expected.upper() == code.upper():
            del self.pairing_codes[channel]
            self.audit_log.append({
                "event": "pairing_approved",
                "channel": channel,
                "timestamp": _now(),
            })
            return True
        return False

    def enable_sandbox(self, session_id: str) -> None:
        self.sandboxed_sessions.add(session_id)

    def is_sandboxed(self, session_id: str) -> bool:
        return session_id in self.sandboxed_sessions

    def check_memory_governance(self, crystal_id: str,
                                proposed_change: str) -> Dict[str, Any]:
        """Check apakah memory change violates governance rules."""
        crystal = self.memory.crystals.get(crystal_id)
        if not crystal:
            return {"allowed": False, "reason": "Crystal not found"}

        # Catastrophic forgetting safeguard
        if crystal.epistemic_layer == "permanent" and "delete" in proposed_change.lower():
            return {
                "allowed": False,
                "reason": "Cannot delete permanent memories (catastrophic forgetting safeguard)",
                "crystal": crystal.to_dict(),
            }

        # Sensitivity check
        if crystal.category == "identity" and "overwrite" in proposed_change.lower():
            return {
                "allowed": False,
                "reason": "Cannot overwrite identity crystals",
            }

        return {"allowed": True}

    def sign_envelope(self, data: str, private_key: Optional[str] = None) -> Dict[str, Any]:
        """Sign data dengan Ed25519 (simplified)."""
        # Simplified: hash-based signature demo
        signature = _hash(data + (private_key or "default_key"))
        return {
            "data_hash": _hash(data),
            "signature": signature,
            "algorithm": "ed25519-simulated",
        }


# ═════════════════════════════════════════════════════════════════════════════
# 12. UNIFIED BITTERBOT ENGINE — Entry Point
# ═════════════════════════════════════════════════════════════════════════════

class BitterbotEngine:
    """
    Unified Bitterbot engine untuk MAGNATRIX.
    Entry point: biological agent dengan persistent memory, dream engine,
    P2P skills economy, dan multi-channel presence.
    """

    def __init__(self) -> None:
        self.memory = MemoryCrystalEngine()
        self.hormonal = HormonalEngine()
        self.curiosity = CuriosityEngine(self.memory)
        self.dream = DreamEngine(self.memory, self.curiosity, self.hormonal)
        self.identity = IdentityEngine()
        self.deep_recall = DeepRecallEngine(self.memory)
        self.marketplace = P2PSkillsMarketplace()
        self.wallet = AgentWallet()
        self.gateway = ChannelGateway()
        self.tools = ToolsEngine()
        self.security = SecurityLayer(self.memory)
        self.state: Dict[str, Any] = {}

    def initialize(self) -> Dict[str, Any]:
        """Initialize agent dengan default state."""
        self.wallet.create_wallet()
        self.identity._load_or_create()

        # Seed initial crystals
        self.memory.create("I am a MAGNATRIX agent", "identity", importance=10.0)
        self.memory.create("My purpose is to serve the user", "identity", importance=9.0)
        self.memory.create("I must never cause harm", "identity", importance=10.0)

        return {
            "status": "initialized",
            "wallet": self.wallet.get_balance(),
            "identity": self.identity.identity.genome if self.identity.identity else {},
            "crystals": self.memory.get_stats(),
        }

    def chat_turn(self, message: str, channel: str = "webchat") -> Dict[str, Any]:
        """Process satu chat turn."""
        # Identity injection
        context = self.identity.inject_identity_context()

        # Proactive recall
        recalled = self.memory.recall(message, top_k=5)

        # Curiosity: detect gaps
        gaps = self.curiosity.detect_gaps(message)

        # Hormonal response
        dims = self.hormonal.trigger("social_bond", intensity=0.05)

        # Generate response (simplified)
        response = f"[MAGNATRIX Agent] Received: {message[:50]}..."
        if recalled:
            response += f"\nRecalled {len(recalled)} relevant crystals."
        if gaps:
            response += f"\nDetected {len(gaps)} knowledge gaps untuk exploration."

        # Store interaction
        self.memory.create(f"User said: {message}", "interaction", importance=2.0)
        self.memory.create(f"Agent responded: {response[:100]}", "interaction", importance=1.0)

        return {
            "response": response,
            "context": context,
            "recalled_crystals": [c.to_dict() for c in recalled],
            "knowledge_gaps": len(gaps),
            "hormonal_dimensions": dims,
        }

    def run_dream_cycle(self) -> Dict[str, Any]:
        """Trigger dream engine."""
        cycle = self.dream.dream()
        return {
            "cycle_id": cycle.cycle_id,
            "modes": [m.value for m in cycle.modes_used],
            "quality_score": round(cycle.quality_score, 3),
            "crystals_processed": cycle.crystals_processed,
            "skills_crystallized": cycle.skills_crystallized,
            "duration_sec": round((cycle.ended_at or time.time()) - cycle.started_at, 2),
        }

    def crystallize_and_publish(self, skill_name: str,
                                description: str, code: str,
                                price: float = 1.0) -> Dict[str, Any]:
        """Crystallize skill dan publish ke marketplace."""
        skill = self.marketplace.crystallize_skill(
            skill_name, description, "magnatrix-agent", code, price
        )
        return {
            "skill_id": skill.skill_id,
            "name": skill.name,
            "price_usdc": skill.price_usdc,
            "content_hash": skill.content_hash,
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "memory": self.memory.get_stats(),
            "hormonal": self.hormonal.get_current_profile(),
            "dreams": self.dream.get_dream_stats(),
            "wallet": self.wallet.get_balance(),
            "channels": self.gateway.get_channel_stats(),
            "marketplace": {
                "skills_listed": len(self.marketplace.skills),
                "bounties_open": len([b for b in self.marketplace.bounties if b["status"] == "open"]),
            },
        }


def main():
    print("═══════════════════════════════════════════════════════════════")
    print("  MAGNATRIX-OS — Bitterbot Native Biological Agent")
    print("  AMATI-PELAJARI-TIRU dari Bitterbot-AI/bitterbot-desktop")
    print("═══════════════════════════════════════════════════════════════")
    print()

    agent = BitterbotEngine()

    # Initialize
    print("[1] Initializing agent...")
    init = agent.initialize()
    print(f"  Wallet: {init['wallet']['address'][:20]}...")
    print(f"  Crystals: {init['crystals']['total_crystals']}")
    print()

    # Chat turns
    print("[2] Chat turns...")
    for msg in ["Hello, what can you do?", "Tell me about yourself", "What did we just discuss?"]:
        result = agent.chat_turn(msg)
        print(f"  User: {msg}")
        print(f"  Agent: {result['response'][:60]}...")
        print(f"    Recalled: {len(result['recalled_crystals'])} crystals")
        print(f"    Gaps: {result['knowledge_gaps']}")
        print()

    # Dream cycle
    print("[3] Dream cycle...")
    dream = agent.run_dream_cycle()
    print(f"  Modes: {dream['modes']}")
    print(f"  Quality Score: {dream['quality_score']}")
    print(f"  Crystals processed: {dream['crystals_processed']}")
    print()

    # Skill crystallization
    print("[4] Skill crystallization...")
    skill = agent.crystallize_and_publish(
        "WebScraperPro", "Advanced web scraping dengan retry logic",
        "def scrape(url): return requests.get(url).text", 2.5
    )
    print(f"  Skill ID: {skill['skill_id']}")
    print(f"  Price: {skill['price_usdc']} USDC")
    print()

    # Marketplace
    print("[5] Marketplace...")
    agent.marketplace.post_bounty("Need ETH price predictor", 50.0, "prediction", "network")
    print(f"  Skills listed: {len(agent.marketplace.skills)}")
    print(f"  Bounties: {len(agent.marketplace.bounties)}")
    print()

    # Status
    print("[6] Full Status:")
    status = agent.get_status()
    print(json.dumps(status, indent=2, default=str))
    print()
    print("Done.")


if __name__ == "__main__":
    main()

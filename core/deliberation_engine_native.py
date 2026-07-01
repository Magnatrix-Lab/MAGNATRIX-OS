#!/usr/bin/env python3
"""deliberation_engine_native.py — MAGNATRIX-OS Multi-Persona Deliberation Engine"""
from __future__ import annotations
import json, random, threading, time, uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

@dataclass
class Persona:
    name: str; role: str; expertise: List[str]; style: str; weight: float = 1.0
    model_preference: str = "balanced"; prompt_template: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Round:
    number: int; statements: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

@dataclass
class Vote:
    persona: str; option: str; confidence: float = 0.5; reasoning: str = ""
    weight: float = 1.0

@dataclass
class Deliberation:
    id: str; topic: str; question: str; rounds: List[Round] = field(default_factory=list)
    votes: List[Vote] = field(default_factory=list); consensus: Optional[str] = None
    consensus_confidence: float = 0.0; status: str = "active"
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

class DeliberationEngineNative:
    def __init__(self, workspace: str = "./deliberation") -> None:
        self.workspace = Path(workspace); self.workspace.mkdir(parents=True, exist_ok=True)
        self._personas: Dict[str, Persona] = {}; self._deliberations: Dict[str, Deliberation] = {}
        self._lock = threading.RLock(); self._db_path = self.workspace / "deliberations.json"
        self._personas_path = self.workspace / "personas.json"; self._load()

    def _load(self) -> None:
        if self._personas_path.exists():
            try:
                with open(self._personas_path, "r", encoding="utf-8") as f: data = json.load(f)
                self._personas = {name: Persona(**pd) for name, pd in data.items()}
            except Exception: self._default_personas()
        else: self._default_personas()
        if self._db_path.exists():
            try:
                with open(self._db_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for did, dd in data.items():
                    dd["rounds"] = [Round(**r) for r in dd.get("rounds", [])]
                    dd["votes"] = [Vote(**v) for v in dd.get("votes", [])]
                    self._deliberations[did] = Deliberation(**dd)
            except Exception: pass

    def _save(self) -> None:
        with open(self._personas_path, "w", encoding="utf-8") as f:
            json.dump({name: asdict(p) for name, p in self._personas.items()}, f, indent=2)
        with open(self._db_path, "w", encoding="utf-8") as f:
            serializable = {}
            for did, d in self._deliberations.items():
                sd = asdict(d); sd["rounds"] = [asdict(r) for r in d.rounds]; sd["votes"] = [asdict(v) for v in d.votes]
                serializable[did] = sd
            json.dump(serializable, f, indent=2, default=str)

    def _default_personas(self) -> None:
        defaults = [
            Persona("Aristotle", "Philosopher", ["ethics", "logic", "reasoning"], "structured, principled, asks why"),
            Persona("Feynman", "Physicist", ["physics", "problem-solving", "simplicity"], "curious, challenges assumptions, explains simply"),
            Persona("Kahneman", "Psychologist", ["cognitive_bias", "decision_making", "behavioral_economics"], "analytical, identifies biases, questions intuition"),
            Persona("Torvalds", "Engineer", ["systems", "pragmatism", "open_source"], "direct, technical, values working code"),
            Persona("Meadows", "Systems_Thinker", ["systems_dynamics", "feedback_loops", "complexity"], "holistic, sees interconnections, long-term thinking"),
            Persona("Munger", "Investor", ["mental_models", "inversion", "multidisciplinary"], "pragmatic, uses mental models, inverts problems"),
            Persona("Taleb", "Risk_Analyst", ["risk", "antifragility", "probability"], "skeptical, focuses on tail risks, challenges consensus"),
            Persona("Rams", "Designer", ["simplicity", "user_experience", "minimalism"], "aesthetic, user-centered, values clarity"),
            Persona("Socrates", "Dialectician", ["questioning", "critical_thinking", "clarity"], "questioning, seeks definitions, exposes contradictions"),
            Persona("Darwin", "Scientist", ["evolution", "observation", "evidence"], "observational, evidence-based, incremental"),
            Persona("Turing", "Computer_Scientist", ["computation", "logic", "algorithms"], "logical, formal, considers computability"),
            Persona("Ockham", "Logician", ["simplicity", "logic", "parsimony"], "minimalist, favors simplest explanation, cuts assumptions"),
        ]
        for p in defaults: self._personas[p.name] = p
        self._save()

    def add_persona(self, persona: Persona) -> None:
        with self._lock: self._personas[persona.name] = persona; self._save()

    def remove_persona(self, name: str) -> bool:
        with self._lock:
            if name in self._personas: del self._personas[name]; self._save(); return True
            return False

    def list_personas(self) -> List[str]:
        with self._lock: return list(self._personas.keys())

    def get_persona(self, name: str) -> Optional[Persona]:
        with self._lock: return self._personas.get(name)

    def start_deliberation(self, topic: str, question: str, persona_names: Optional[List[str]] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        with self._lock:
            did = f"delib_{int(time.time())}_{str(uuid.uuid4())[:8]}"
            selected = persona_names or list(self._personas.keys())
            deliberation = Deliberation(id=did, topic=topic, question=question, metadata={"selected_personas": selected, **(metadata or {})})
            self._deliberations[did] = deliberation; self._save()
            return did

    def add_round(self, did: str, statements: Dict[str, str]) -> bool:
        with self._lock:
            if did not in self._deliberations: return False
            d = self._deliberations[did]
            if d.status != "active": return False
            round_num = len(d.rounds) + 1
            d.rounds.append(Round(number=round_num, statements=statements))
            self._save(); return True

    def add_vote(self, did: str, persona: str, option: str, confidence: float = 0.5, reasoning: str = "") -> bool:
        with self._lock:
            if did not in self._deliberations: return False
            d = self._deliberations[did]
            if d.status != "active": return False
            weight = self._personas.get(persona, Persona(persona, "", [], "")).weight
            d.votes.append(Vote(persona=persona, option=option, confidence=confidence, reasoning=reasoning, weight=weight))
            self._save(); return True

    def tally(self, did: str) -> Dict[str, Any]:
        with self._lock:
            if did not in self._deliberations: return {"error": "Deliberation not found"}
            d = self._deliberations[did]
            if not d.votes: return {"error": "No votes"}
            tallies: Dict[str, Tuple[float, float]] = {}
            for v in d.votes:
                w = v.confidence * v.weight
                if v.option not in tallies: tallies[v.option] = (0.0, 0.0)
                tallies[v.option] = (tallies[v.option][0] + w, tallies[v.option][1] + v.weight)
            results = {}
            for opt, (weighted_sum, total_weight) in tallies.items():
                results[opt] = {"weighted_score": weighted_sum, "total_weight": total_weight, "normalized_score": weighted_sum / total_weight if total_weight > 0 else 0}
            ranked = sorted(results.items(), key=lambda x: x[1]["weighted_score"], reverse=True)
            top_score = ranked[0][1]["weighted_score"] if ranked else 0
            top_options = [opt for opt, scores in ranked if abs(scores["weighted_score"] - top_score) < 0.001]
            if len(top_options) == 1:
                winner = top_options[0]; d.consensus = winner; d.consensus_confidence = results[winner]["normalized_score"]; d.status = "consensus"
            elif len(top_options) > 1: d.status = "tie"; d.consensus = None; d.consensus_confidence = 0.0
            else: d.status = "deadlock"
            d.completed_at = time.time(); self._save()
            return {"status": d.status, "consensus": d.consensus, "confidence": d.consensus_confidence, "ranked": ranked, "total_votes": len(d.votes), "tie_options": top_options if d.status == "tie" else []}

    def get_deliberation(self, did: str) -> Optional[Deliberation]:
        with self._lock: return self._deliberations.get(did)

    def list_deliberations(self, status: Optional[str] = None) -> List[str]:
        with self._lock:
            if status: return [did for did, d in self._deliberations.items() if d.status == status]
            return list(self._deliberations.keys())

    def delete_deliberation(self, did: str) -> bool:
        with self._lock:
            if did in self._deliberations: del self._deliberations[did]; self._save(); return True
            return False

    def get_transcript(self, did: str) -> str:
        d = self.get_deliberation(did)
        if not d: return ""
        lines = [f"=== Deliberation: {d.topic} ===", f"Question: {d.question}", f"Status: {d.status}", ""]
        for r in d.rounds:
            lines.append(f"--- Round {r.number} ---")
            for persona, statement in r.statements.items():
                lines.append(f"[{persona}]: {statement[:500]}")
            lines.append("")
        if d.votes:
            lines.append("--- Votes ---")
            for v in d.votes:
                lines.append(f"[{v.persona}] -> {v.option} (confidence: {v.confidence}, weight: {v.weight})")
        if d.consensus:
            lines.append(f"
*** CONSENSUS: {d.consensus} (confidence: {d.consensus_confidence:.2f}) ***")
        return "
".join(lines)

if __name__ == "__main__":
    engine = DeliberationEngineNative()
    print("Personas:", engine.list_personas())
    did = engine.start_deliberation("Architecture Decision", "Should we adopt microservices or monolith?")
    print("Deliberation started:", did)

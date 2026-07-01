#!/usr/bin/env python3
"""identity_native.py — MAGNATRIX-OS User Identity Framework"""
from __future__ import annotations
import json, threading, time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

@dataclass
class IdentityDimension:
    name: str; value: Any; confidence: float = 0.0; last_updated: float = field(default_factory=time.time)
    evidence: List[str] = field(default_factory=list)
    history: List[Tuple[float, Any, float]] = field(default_factory=list)

@dataclass
class UserIdentity:
    user_id: str; created_at: float = field(default_factory=time.time); last_interaction: float = field(default_factory=time.time)
    interaction_count: int = 0; dimensions: Dict[str, IdentityDimension] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set); notes: List[str] = field(default_factory=list)

class IdentityNative:
    DIMENSION_SCHEMA: Dict[str, Dict[str, Any]] = {
        "communication_style": {"type": "str", "description": "How user communicates: direct, detailed, casual, formal, technical, concise", "default": "unknown"},
        "expertise_domains": {"type": "list", "description": "Technical domains: coding, design, finance, medicine, legal, etc.", "default": []},
        "preferences": {"type": "dict", "description": "General preferences: output_format, detail_level, language, code_style", "default": {}},
        "goals": {"type": "list", "description": "User's stated or inferred goals", "default": []},
        "patterns": {"type": "dict", "description": "Behavioral patterns: time_of_day, question_types, follow_up_style, decision_speed", "default": {}},
        "trust_level": {"type": "float", "description": "Trust level 0.0-1.0", "default": 0.5},
        "feedback_history": {"type": "list", "description": "Explicit feedback: corrections, approvals, ratings", "default": []},
        "context_depth": {"type": "str", "description": "Context provided: minimal, moderate, extensive", "default": "moderate"},
        "error_tolerance": {"type": "str", "description": "Response to errors: patient, frustrated, educational, punitive", "default": "patient"},
        "initiative_preference": {"type": "str", "description": "Proactive suggestions or reactive responses", "default": "reactive"},
        "technical_ability": {"type": "str", "description": "Sophistication: beginner, intermediate, advanced, expert", "default": "intermediate"},
        "collaboration_style": {"type": "str", "description": "Work style: solo, pair, team lead, delegate", "default": "solo"},
    }

    def __init__(self, workspace: str = "./identity") -> None:
        self.workspace = Path(workspace); self.workspace.mkdir(parents=True, exist_ok=True)
        self._identities: Dict[str, UserIdentity] = {}; self._lock = threading.RLock()
        self._db_path = self.workspace / "identities.json"; self._load()

    def _load(self) -> None:
        if self._db_path.exists():
            try:
                with open(self._db_path, "r", encoding="utf-8") as f: data = json.load(f)
                for uid, ud in data.items():
                    ud["dimensions"] = {k: IdentityDimension(**v) for k, v in ud.get("dimensions", {}).items()}
                    ud["tags"] = set(ud.get("tags", [])); self._identities[uid] = UserIdentity(**ud)
            except Exception: self._identities = {}

    def _save(self) -> None:
        with open(self._db_path, "w", encoding="utf-8") as f:
            serializable = {}
            for uid, ident in self._identities.items():
                d = asdict(ident); d["tags"] = list(d["tags"]); d["dimensions"] = {k: asdict(v) for k, v in d["dimensions"].items()}
                serializable[uid] = d
            json.dump(serializable, f, indent=2, default=str)

    def get_or_create(self, user_id: str) -> UserIdentity:
        with self._lock:
            if user_id not in self._identities:
                dimensions = {}
                for name, schema in self.DIMENSION_SCHEMA.items():
                    dimensions[name] = IdentityDimension(name=name, value=schema["default"], confidence=0.0, evidence=["auto_initialized"])
                self._identities[user_id] = UserIdentity(user_id=user_id, dimensions=dimensions)
                self._save()
            return self._identities[user_id]

    def update_dimension(self, user_id: str, dimension: str, value: Any, confidence: float = 0.5, evidence: str = "") -> bool:
        with self._lock:
            ident = self.get_or_create(user_id)
            if dimension not in ident.dimensions and dimension not in self.DIMENSION_SCHEMA: return False
            if dimension not in ident.dimensions: ident.dimensions[dimension] = IdentityDimension(name=dimension, value=value)
            dim = ident.dimensions[dimension]; dim.history.append((time.time(), dim.value, dim.confidence))
            if len(dim.history) > 50: dim.history = dim.history[-50:]
            if confidence >= dim.confidence or dim.confidence == 0.0: dim.value = value; dim.confidence = confidence
            else:
                if isinstance(value, (int, float)) and isinstance(dim.value, (int, float)): dim.value = (dim.value * dim.confidence + value * confidence) / (dim.confidence + confidence)
                else: dim.value = value
            dim.last_updated = time.time()
            if evidence: dim.evidence.append(evidence); dim.evidence = dim.evidence[-20:]
            ident.last_interaction = time.time(); self._save(); return True

    def record_interaction(self, user_id: str, message_text: str, inferred_updates: Optional[Dict[str, Tuple[Any, float, str]]] = None) -> None:
        with self._lock:
            ident = self.get_or_create(user_id); ident.interaction_count += 1; ident.last_interaction = time.time()
            if inferred_updates:
                for dim, (val, conf, ev) in inferred_updates.items(): self.update_dimension(user_id, dim, val, conf, ev)
            self._auto_infer(user_id, message_text); self._save()

    def _auto_infer(self, user_id: str, text: str) -> None:
        text_lower = text.lower(); ident = self._identities[user_id]
        tech_keywords = ["api", "function", "class", "def ", "import ", "database", "algorithm", "docker", "kubernetes"]
        tech_score = sum(1 for kw in tech_keywords if kw in text_lower)
        if tech_score >= 3: self.update_dimension(user_id, "technical_ability", "advanced", 0.3, f"tech_keywords:{tech_score}")
        elif tech_score >= 1: self.update_dimension(user_id, "technical_ability", "intermediate", 0.2, f"tech_keywords:{tech_score}")
        if len(text) < 20: self.update_dimension(user_id, "communication_style", "concise", 0.2, "short_message")
        elif len(text) > 200: self.update_dimension(user_id, "communication_style", "detailed", 0.2, "long_message")
        proactive_words = ["suggest", "recommend", "what about", "consider", "alternative", "better way"]
        if any(w in text_lower for w in proactive_words): self.update_dimension(user_id, "initiative_preference", "proactive", 0.3, "proactive_language")
        correction_words = ["wrong", "incorrect", "fix", "error", "bug", "mistake", "not working"]
        if any(w in text_lower for w in correction_words): self.update_dimension(user_id, "error_tolerance", "educational", 0.3, "correction_detected")
        if len(text) > 100 and any(w in text_lower for w in ["because", "since", "as", "context", "background"]):
            self.update_dimension(user_id, "context_depth", "extensive", 0.3, "rich_context")

    def add_feedback(self, user_id: str, feedback_type: str, details: str, rating: Optional[float] = None) -> None:
        with self._lock:
            ident = self.get_or_create(user_id)
            entry = {"timestamp": time.time(), "type": feedback_type, "details": details, "rating": rating}
            ident.dimensions["feedback_history"].value.append(entry)
            ident.dimensions["feedback_history"].evidence.append(f"feedback:{feedback_type}")
            ident.last_interaction = time.time()
            if feedback_type == "approval": self._adjust_trust(user_id, 0.05)
            elif feedback_type == "correction": self._adjust_trust(user_id, 0.02)
            elif feedback_type == "rejection": self._adjust_trust(user_id, -0.03)
            self._save()

    def _adjust_trust(self, user_id: str, delta: float) -> None:
        dim = self._identities[user_id].dimensions["trust_level"]
        if isinstance(dim.value, (int, float)):
            dim.value = max(0.0, min(1.0, dim.value + delta)); dim.confidence = min(1.0, dim.confidence + 0.01); dim.last_updated = time.time()

    def get_context_injection(self, user_id: str) -> str:
        ident = self.get_or_create(user_id)
        lines = ["=== User Identity Profile ===", f"User ID: {ident.user_id}", f"Interactions: {ident.interaction_count}"]
        for name, dim in ident.dimensions.items():
            if dim.confidence > 0.1:
                val_str = str(dim.value); val_str = val_str[:100] + "..." if len(val_str) > 100 else val_str
                lines.append(f"  {name}: {val_str} (confidence: {dim.confidence:.2f})")
        if ident.tags: lines.append(f"Tags: {', '.join(ident.tags)}")
        lines.append("=== End Profile ===")
        return "\n".join(lines)

    def get_summary(self, user_id: str) -> Dict[str, Any]:
        ident = self.get_or_create(user_id)
        return {"user_id": ident.user_id, "interactions": ident.interaction_count, "trust": ident.dimensions.get("trust_level", IdentityDimension("trust_level", 0.5)).value, "technical": ident.dimensions.get("technical_ability", IdentityDimension("technical_ability", "unknown")).value, "communication": ident.dimensions.get("communication_style", IdentityDimension("communication_style", "unknown")).value, "initiative": ident.dimensions.get("initiative_preference", IdentityDimension("initiative_preference", "reactive")).value, "dimensions_count": len(ident.dimensions), "tags": list(ident.tags)}

    def add_tag(self, user_id: str, tag: str) -> None:
        with self._lock: ident = self.get_or_create(user_id); ident.tags.add(tag); self._save()

    def remove_tag(self, user_id: str, tag: str) -> None:
        with self._lock: ident = self.get_or_create(user_id); ident.tags.discard(tag); self._save()

    def add_note(self, user_id: str, note: str) -> None:
        with self._lock:
            ident = self.get_or_create(user_id); ident.notes.append(f"{time.time():.0f}: {note}")
            ident.notes = ident.notes[-50:]; self._save()

    def list_users(self) -> List[str]:
        with self._lock: return list(self._identities.keys())

    def delete_user(self, user_id: str) -> bool:
        with self._lock:
            if user_id in self._identities: del self._identities[user_id]; self._save(); return True
            return False

if __name__ == "__main__":
    id_sys = IdentityNative()
    id_sys.record_interaction("user_001", "Can you write a Python function to parse JSON?")
    id_sys.record_interaction("user_001", "Also add error handling and type hints please.")
    id_sys.add_feedback("user_001", "approval", "Good function, clean code", 4.5)
    print(id_sys.get_context_injection("user_001"))
    print("Summary:", id_sys.get_summary("user_001"))

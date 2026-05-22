#!/usr/bin/env python3
"""
curriculum_bridge.py — MAGNATRIX AI Engineering Curriculum Bridge
Integrasi knowledge graph dengan course "AI Engineering From Scratch"
(rohitg00/ai-engineering-from-scratch) — 20 phases, 500+ lessons.

Mapping phase → MAGNATRIX layer:
  Phase 00  Setup & Tooling              → Layer 12 (IDE)
  Phase 01  Math Foundations             → Layer 0 (Kernel - math primitives)
  Phase 02  ML Fundamentals              → Layer 5 (Knowledge - ML models)
  Phase 03  Deep Learning Core           → Layer 5 (Knowledge - neural nets)
  Phase 04  Computer Vision              → Layer 5 (Knowledge - vision)
  Phase 05  NLP Foundations            → Layer 5 (Knowledge - NLP)
  Phase 06  Speech & Audio               → Layer 5 (Knowledge - audio)
  Phase 07  Transformers Deep Dive       → Layer 5 (Knowledge - transformers)
  Phase 08  Generative AI                → Layer 10 (Uncensored AI)
  Phase 09  Reinforcement Learning       → Layer 5 (Knowledge - RL)
  Phase 10  LLMs From Scratch            → Layer 10 (Uncensored AI)
  Phase 11  LLM Engineering              → Layer 1.5 (API Router)
  Phase 12  Multimodal AI                → Layer 5 (Knowledge - multimodal)
  Phase 13  Tools & Protocols (MCP)      → Layer 1.5 (API Router)
  Phase 14  Agent Engineering            → Layer 6 (Skills / Agent)
  Phase 15  Autonomous Systems           → Layer 0.5 (Collective Brain)
  Phase 16  Multi-Agent & Swarms         → Layer 4 (P2P Mesh)
  Phase 17  Infrastructure & Production  → Layer 3 (Runtime)
  Phase 18  Ethics, Safety, Alignment    → Layer 11 (Governance)
  Phase 19  Capstone Projects            → Layer 13 (Offensive)

Fungsi bridge:
  - Index course content ke Knowledge Graph
  - Track progress per phase/lesson
  - Auto-link completed topics ke skill activation
  - Query: "What do I need to know to build X?"
  - Generate learning path untuk agent roles
"""

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple


# ===================================================================
# Curriculum Mapping Data
# ===================================================================
PHASE_MAP: Dict[str, Dict[str, Any]] = {
    "00-setup-and-tooling": {
        "id": "00", "name": "Setup & Tooling", "layer": 12,
        "lessons": 10, "skills": ["repo-health", "ci-monitor"], "agent": "ops",
    },
    "01-math-foundations": {
        "id": "01", "name": "Math Foundations", "layer": 0,
        "lessons": 15, "skills": ["analyze-signal"], "agent": "analyst",
    },
    "02-ml-fundamentals": {
        "id": "02", "name": "ML Fundamentals", "layer": 5,
        "lessons": 20, "skills": ["forecast-model", "pattern-recognition"], "agent": "analyst",
    },
    "03-deep-learning-core": {
        "id": "03", "name": "Deep Learning Core", "layer": 5,
        "lessons": 25, "skills": ["analyze-signal", "cross-domain-synthesis"], "agent": "analyst",
    },
    "04-computer-vision": {
        "id": "04", "name": "Computer Vision", "layer": 5,
        "lessons": 28, "skills": ["pattern-recognition"], "agent": "analyst",
    },
    "05-nlp-foundations-to-advanced": {
        "id": "05", "name": "NLP Foundations to Advanced", "layer": 5,
        "lessons": 24, "skills": ["analyze-signal"], "agent": "analyst",
    },
    "06-speech-and-audio": {
        "id": "06", "name": "Speech & Audio", "layer": 5,
        "lessons": 12, "skills": ["analyze-signal"], "agent": "analyst",
    },
    "07-transformers-deep-dive": {
        "id": "07", "name": "Transformers Deep Dive", "layer": 5,
        "lessons": 20, "skills": ["analyze-signal", "cross-domain-synthesis"], "agent": "analyst",
    },
    "08-generative-ai": {
        "id": "08", "name": "Generative AI", "layer": 10,
        "lessons": 18, "skills": ["code-mutate", "emergent-predict"], "agent": "architect",
    },
    "09-reinforcement-learning": {
        "id": "09", "name": "Reinforcement Learning", "layer": 5,
        "lessons": 16, "skills": ["forecast-model"], "agent": "analyst",
    },
    "10-llms-from-scratch": {
        "id": "10", "name": "LLMs From Scratch", "layer": 10,
        "lessons": 30, "skills": ["code-mutate", "constitution-evolve"], "agent": "architect",
    },
    "11-llm-engineering": {
        "id": "11", "name": "LLM Engineering", "layer": 1,
        "lessons": 22, "skills": ["deploy-pipeline", "repo-health"], "agent": "ops",
    },
    "12-multimodal-ai": {
        "id": "12", "name": "Multimodal AI", "layer": 5,
        "lessons": 15, "skills": ["cross-domain-synthesis"], "agent": "analyst",
    },
    "13-tools-and-protocols": {
        "id": "13", "name": "Tools & Protocols (MCP)", "layer": 1,
        "lessons": 20, "skills": ["mcp-builder", "api-call"], "agent": "architect",
    },
    "14-agent-engineering": {
        "id": "14", "name": "Agent Engineering", "layer": 6,
        "lessons": 42, "skills": ["code-mutate", "deploy-pipeline"], "agent": "architect",
    },
    "15-autonomous-systems": {
        "id": "15", "name": "Autonomous Systems", "layer": 0,
        "lessons": 18, "skills": ["constitution-evolve", "emergent-predict"], "agent": "architect",
    },
    "16-multi-agent-and-swarms": {
        "id": "16", "name": "Multi-Agent & Swarms", "layer": 4,
        "lessons": 24, "skills": ["code-mutate", "cross-domain-synthesis"], "agent": "architect",
    },
    "17-infrastructure-and-production": {
        "id": "17", "name": "Infrastructure & Production", "layer": 3,
        "lessons": 26, "skills": ["deploy-pipeline", "datadog-logs"], "agent": "ops",
    },
    "18-ethics-safety-alignment": {
        "id": "18", "name": "Ethics, Safety, Alignment", "layer": 11,
        "lessons": 29, "skills": ["constitution-check", "check-risk"], "agent": "guardian",
    },
    "19-capstone-projects": {
        "id": "19", "name": "Capstone Projects", "layer": 13,
        "lessons": 10, "skills": ["security-audit", "webapp-testing"], "agent": "researcher",
    },
}

# Role-based learning paths
ROLE_PATHS: Dict[str, List[str]] = {
    "scout": ["00", "01", "02", "04"],
    "analyst": ["01", "02", "03", "04", "05", "07", "09", "12"],
    "executor": ["00", "11", "17"],
    "guardian": ["01", "02", "18"],
    "researcher": ["05", "07", "10", "19"],
    "writer": ["05", "08", "12"],
    "ops": ["00", "11", "13", "17"],
    "architect": ["03", "08", "10", "13", "14", "15", "16"],
}


@dataclass
class CurriculumProgress:
    phase_id: str
    lessons_completed: int = 0
    total_lessons: int = 0
    skills_unlocked: List[str] = field(default_factory=list)
    last_studied: Optional[float] = None


class CurriculumBridge:
    """Bridge antara AI Engineering course dan MAGNATRIX Knowledge Graph."""

    def __init__(self, knowledge_graph=None):
        self.kg = knowledge_graph
        self.progress: Dict[str, CurriculumProgress] = {}
        self._load_progress()

    def _load_progress(self) -> None:
        """Load existing progress dari disk."""
        progress_file = Path("curriculum_progress.json")
        if progress_file.exists():
            try:
                data = json.loads(progress_file.read_text())
                for pid, p in data.items():
                    self.progress[pid] = CurriculumProgress(**p)
            except Exception:
                pass

    def _save_progress(self) -> None:
        """Save progress ke disk."""
        progress_file = Path("curriculum_progress.json")
        data = {
            pid: {
                "phase_id": p.phase_id,
                "lessons_completed": p.lessons_completed,
                "total_lessons": p.total_lessons,
                "skills_unlocked": p.skills_unlocked,
                "last_studied": p.last_studied,
            }
            for pid, p in self.progress.items()
        }
        progress_file.write_text(json.dumps(data, indent=2, default=str))

    def get_phase_info(self, phase_key: str) -> Optional[Dict[str, Any]]:
        """Get info tentang satu phase."""
        return PHASE_MAP.get(phase_key)

    def list_phases(self) -> List[Dict[str, Any]]:
        """List semua phases."""
        return [
            {
                "key": k,
                **v,
                "progress": self.get_progress(k),
            }
            for k, v in PHASE_MAP.items()
        ]

    def get_progress(self, phase_key: str) -> Dict[str, Any]:
        """Get progress untuk satu phase."""
        info = PHASE_MAP.get(phase_key, {})
        p = self.progress.get(phase_key, CurriculumProgress(phase_key))
        total = info.get("lessons", 0)
        completed = min(p.lessons_completed, total) if total else 0
        return {
            "phase_id": phase_key,
            "completed": completed,
            "total": total,
            "percentage": round((completed / total * 100), 1) if total else 0,
            "skills_unlocked": p.skills_unlocked or info.get("skills", []),
            "last_studied": p.last_studied,
        }

    def update_progress(self, phase_key: str, lessons_completed: int) -> Dict[str, Any]:
        """Update progress untuk satu phase."""
        info = PHASE_MAP.get(phase_key, {})
        total = info.get("lessons", 0)
        completed = min(lessons_completed, total)

        # Calculate skills unlocked
        progress_pct = completed / total if total else 0
        all_skills = info.get("skills", [])
        unlocked = all_skills[:int(len(all_skills) * progress_pct) + 1]

        self.progress[phase_key] = CurriculumProgress(
            phase_id=phase_key,
            lessons_completed=completed,
            total_lessons=total,
            skills_unlocked=unlocked,
            last_studied=time.time(),
        )
        self._save_progress()

        return self.get_progress(phase_key)

    def get_learning_path(self, role: str) -> List[Dict[str, Any]]:
        """Get recommended learning path untuk satu agent role."""
        phase_ids = ROLE_PATHS.get(role, [])
        return [self.get_progress(f"{pid}-{self._get_phase_key(pid)}") for pid in phase_ids]

    def _get_phase_key(self, phase_id: str) -> str:
        """Map numeric phase ID ke dict key suffix."""
        for k, v in PHASE_MAP.items():
            if v["id"] == phase_id:
                # Return everything after first dash, or full key if no dash
                return k.split("-", 1)[1] if "-" in k else k
        return ""

    def get_recommended_next(self, role: str) -> Optional[Dict[str, Any]]:
        """Get next recommended lesson/phase untuk role."""
        path = self.get_learning_path(role)
        for p in path:
            if p["percentage"] < 100:
                info = PHASE_MAP.get(p["phase_id"], {})
                return {
                    "phase_id": p["phase_id"],
                    "phase_name": info.get("name", "Unknown"),
                    "current_lesson": p["completed"] + 1,
                    "total_lessons": p["total"],
                    "percentage": p["percentage"],
                    "layer": info.get("layer"),
                    "skills": info.get("skills", []),
                }
        return None

    def search_by_skill(self, skill_name: str) -> List[Dict[str, Any]]:
        """Cari phase/lessons yang mengajarkan skill tertentu."""
        results = []
        for k, v in PHASE_MAP.items():
            if skill_name in v.get("skills", []):
                results.append({
                    "phase_key": k,
                    "phase_name": v["name"],
                    "layer": v["layer"],
                    "lessons": v["lessons"],
                    "progress": self.get_progress(k),
                })
        return results

    def get_layer_coverage(self, layer: int) -> Dict[str, Any]:
        """Get course coverage untuk satu MAGNATRIX layer."""
        phases = [v for v in PHASE_MAP.values() if v["layer"] == layer]
        total_lessons = sum(p["lessons"] for p in phases)
        completed = sum(
            self.progress.get(k, CurriculumProgress(k)).lessons_completed
            for k, v in PHASE_MAP.items() if v["layer"] == layer
        )
        return {
            "layer": layer,
            "phases_count": len(phases),
            "total_lessons": total_lessons,
            "completed_lessons": completed,
            "coverage_pct": round((completed / total_lessons * 100), 1) if total_lessons else 0,
            "phases": [p["name"] for p in phases],
        }

    def export_to_knowledge(self) -> List[Dict[str, Any]]:
        """Export curriculum entities ke Knowledge Graph format."""
        entities = []
        for k, v in PHASE_MAP.items():
            progress = self.get_progress(k)
            entities.append({
                "type": "curriculum_phase",
                "name": v["name"],
                "phase_id": v["id"],
                "magnatrix_layer": v["layer"],
                "total_lessons": v["lessons"],
                "skills_taught": v["skills"],
                "recommended_agent": v["agent"],
                "progress_percentage": progress["percentage"],
                "source": "ai-engineering-from-scratch",
            })
        return entities

    def get_summary(self) -> Dict[str, Any]:
        """Get overall curriculum summary."""
        total_lessons = sum(v["lessons"] for v in PHASE_MAP.values())
        total_completed = sum(p.lessons_completed for p in self.progress.values())
        total_skills = len(set(
            skill
            for v in PHASE_MAP.values()
            for skill in v.get("skills", [])
        ))
        unlocked_skills = len(set(
            skill
            for p in self.progress.values()
            for skill in p.skills_unlocked
        ))

        return {
            "total_phases": len(PHASE_MAP),
            "total_lessons": total_lessons,
            "completed_lessons": total_completed,
            "overall_percentage": round((total_completed / total_lessons * 100), 1) if total_lessons else 0,
            "total_skills": total_skills,
            "unlocked_skills": unlocked_skills,
            "phases_completed": sum(1 for p in self.progress.values() if p.lessons_completed >= p.total_lessons),
            "timestamp": time.time(),
        }


# ===================================================================
# Demo
# ===================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX Curriculum Bridge")
    print("=" * 60)

    bridge = CurriculumBridge()

    print("\n[1] Phase mapping to MAGNATRIX layers:")
    for k, v in PHASE_MAP.items():
        print(f"  Phase {v['id']:2s} → Layer {v['layer']:2d} — {v['name']:<35s} ({v['lessons']:3d} lessons)")

    print("\n[2] Role learning paths:")
    for role, phases in ROLE_PATHS.items():
        names = [PHASE_MAP.get(f"{pid}-{bridge._get_phase_key(pid)}", {}).get("name", "?") for pid in phases]
        print(f"  {role:12s}: {', '.join(names[:4])}{'...' if len(names) > 4 else ''}")

    print("\n[3] Simulating progress update...")
    bridge.update_progress("14-agent-engineering", 21)
    bridge.update_progress("16-multi-agent-and-swarms", 12)
    bridge.update_progress("18-ethics-safety-alignment", 15)

    print("\n[4] Architect recommended next:")
    next_rec = bridge.get_recommended_next("architect")
    if next_rec:
        print(f"  → {next_rec['phase_name']} (Lesson {next_rec['current_lesson']}/{next_rec['total_lessons']})")

    print("\n[5] Skills search: 'mcp-builder'")
    results = bridge.search_by_skill("mcp-builder")
    for r in results:
        print(f"  → {r['phase_name']} — {r['lessons']} lessons")

    print("\n[6] Layer 11 (Governance) coverage:")
    coverage = bridge.get_layer_coverage(11)
    print(f"  {coverage['phases_count']} phases, {coverage['completed_lessons']}/{coverage['total_lessons']} lessons")

    print("\n[7] Overall summary:")
    summary = bridge.get_summary()
    print(f"  {summary['completed_lessons']}/{summary['total_lessons']} lessons ({summary['overall_percentage']}%)")
    print(f"  {summary['unlocked_skills']}/{summary['total_skills']} skills unlocked")

    print("\n[8] Knowledge Graph entities:")
    entities = bridge.export_to_knowledge()
    print(f"  {len(entities)} curriculum entities ready for KG import")

    print("\n" + "=" * 60)
    print("Curriculum Bridge ready.")
    print("=" * 60)

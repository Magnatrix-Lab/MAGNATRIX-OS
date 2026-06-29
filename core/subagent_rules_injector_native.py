"""
subagent_rules_injector_native.py
MAGNATRIX-OS — Subagent Rules Injector

Inspired by Ponytail: Inject rulesets into subagents via hooks. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class SubagentSession:
    session_id: str
    parent_id: str
    rules_injected: List[str] = field(default_factory=list)
    injected_at: str = ""

    def __post_init__(self):
        if not self.injected_at:
            self.injected_at = datetime.now().isoformat()


class SubagentRulesInjector:
    """Inject rulesets into subagents via startup hooks."""

    def __init__(self, cache_dir: str = "./subagent_injections"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.sessions: Dict[str, SubagentSession] = {}
        self.rule_sets: Dict[str, List[str]] = {}
        self._load()

    def _load(self) -> None:
        for fname in ["sessions.json", "rulesets.json"]:
            f = self.cache_dir / fname
            if f.exists():
                try:
                    with open(f, "r", encoding="utf-8") as fp:
                        data = json.load(fp)
                        if fname == "sessions.json":
                            self.sessions = {k: SubagentSession(**v) for k, v in data.items()}
                        else:
                            self.rule_sets = data
                except Exception:
                    pass

    def _save(self) -> None:
        with open(self.cache_dir / "sessions.json", "w", encoding="utf-8") as f:
            json.dump({k: asdict(v) for k, v in self.sessions.items()}, f, indent=2)
        with open(self.cache_dir / "rulesets.json", "w", encoding="utf-8") as f:
            json.dump(self.rule_sets, f, indent=2)

    def register_ruleset(self, ruleset_id: str, rules: List[str]) -> None:
        self.rule_sets[ruleset_id] = rules
        self._save()

    def inject(self, session_id: str, parent_id: str, ruleset_id: str) -> SubagentSession:
        rules = self.rule_sets.get(ruleset_id, [])
        session = SubagentSession(
            session_id=session_id, parent_id=parent_id, rules_injected=rules,
        )
        self.sessions[session_id] = session
        self._save()
        return session

    def inject_all(self, session_id: str, parent_id: str) -> SubagentSession:
        all_rules = []
        for rules in self.rule_sets.values():
            all_rules.extend(rules)
        session = SubagentSession(
            session_id=session_id, parent_id=parent_id, rules_injected=list(set(all_rules)),
        )
        self.sessions[session_id] = session
        self._save()
        return session

    def get_session(self, session_id: str) -> Optional[SubagentSession]:
        return self.sessions.get(session_id)

    def get_stats(self) -> Dict[str, Any]:
        total_sessions = len(self.sessions)
        total_rules = sum(len(s.rules_injected) for s in self.sessions.values())
        return {"sessions": total_sessions, "total_injected_rules": total_rules, "rulesets": len(self.rule_sets)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["SubagentRulesInjector", "SubagentSession"]
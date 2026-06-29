"""
agent_comm_taxonomy_native.py
MAGNATRIX-OS — Agent Communication Taxonomy

Inspired by arXiv 2606.19135: Technical taxonomy of LLM agent communication protocols. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class ProtocolEntry:
    protocol_id: str
    name: str
    counterparty: str  # agent-to-agent, agent-to-context
    payload_type: str
    interaction_state: str
    discovery: str
    schema_flexibility: str


class AgentCommTaxonomy:
    """Technical taxonomy of LLM agent communication protocols."""

    BUILT_IN_PROTOCOLS = {
        "autogen": {"name": "AutoGen", "counterparty": "agent-to-agent", "payload_type": "hybrid", "interaction_state": "session-persistent", "discovery": "predefined", "schema_flexibility": "multiple"},
        "crewai": {"name": "CrewAI", "counterparty": "agent-to-agent", "payload_type": "structured", "interaction_state": "stateless", "discovery": "predefined", "schema_flexibility": "fixed"},
        "camel": {"name": "CAMEL", "counterparty": "agent-to-agent", "payload_type": "hybrid", "interaction_state": "session-persistent", "discovery": "predefined", "schema_flexibility": "multiple"},
        "langgraph": {"name": "LangGraph", "counterparty": "agent-to-context", "payload_type": "graph", "interaction_state": "session-persistent", "discovery": "runtime", "schema_flexibility": "negotiable"},
        "mcp": {"name": "MCP", "counterparty": "agent-to-context", "payload_type": "json-rpc", "interaction_state": "stateless", "discovery": "runtime", "schema_flexibility": "negotiable"},
    }

    def __init__(self, cache_dir: str = "./comm_taxonomy"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.protocols: Dict[str, ProtocolEntry] = {}
        self._load()
        self._init_builtin()

    def _init_builtin(self) -> None:
        for pid, info in self.BUILT_IN_PROTOCOLS.items():
            if pid not in self.protocols:
                self.protocols[pid] = ProtocolEntry(protocol_id=pid, **info)

    def _load(self) -> None:
        file = self.cache_dir / "protocols.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for pid, pd in data.items():
                        self.protocols[pid] = ProtocolEntry(**pd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.cache_dir / "protocols.json", "w", encoding="utf-8") as f:
            json.dump({pid: asdict(p) for pid, p in self.protocols.items()}, f, indent=2)

    def classify(self, protocol_id: str, name: str, counterparty: str, payload_type: str,
                 interaction_state: str, discovery: str, schema_flexibility: str) -> ProtocolEntry:
        entry = ProtocolEntry(
            protocol_id=protocol_id, name=name, counterparty=counterparty,
            payload_type=payload_type, interaction_state=interaction_state,
            discovery=discovery, schema_flexibility=schema_flexibility,
        )
        self.protocols[protocol_id] = entry
        self._save()
        return entry

    def compare(self, protocol_a: str, protocol_b: str) -> Dict[str, Any]:
        a = self.protocols.get(protocol_a)
        b = self.protocols.get(protocol_b)
        if not a or not b:
            return {"error": "Protocol not found"}
        differences = {}
        for attr in ["counterparty", "payload_type", "interaction_state", "discovery", "schema_flexibility"]:
            av = getattr(a, attr)
            bv = getattr(b, attr)
            if av != bv:
                differences[attr] = {"a": av, "b": bv}
        return {"protocol_a": protocol_a, "protocol_b": protocol_b, "differences": differences}

    def get_stats(self) -> Dict[str, Any]:
        return {"total_protocols": len(self.protocols), "built_in": len(self.BUILT_IN_PROTOCOLS)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["AgentCommTaxonomy", "ProtocolEntry"]
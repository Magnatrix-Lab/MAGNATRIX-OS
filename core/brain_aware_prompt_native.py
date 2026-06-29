
"""
brain_aware_prompt_native.py
MAGNATRIX-OS — Brain-Aware Prompt Generator

Inspired by Synapse brain-aware system prompt:
Generates system prompts that are aware of the agent's memory system,
hippocampus state, and temporal knowledge graph.

Pure Python standard library.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class BrainState:
    total_memories: int = 0
    active_memories: int = 0
    high_salience_memories: int = 0
    consolidation_level: float = 0.0
    last_consolidation: str = ""
    graph_facts: int = 0
    graph_entities: int = 0


class BrainAwarePromptGenerator:
    """Generate system prompts that incorporate brain/memory awareness."""

    def __init__(self, hippocampus=None, graph=None, retrieval_engine=None):
        self.hippocampus = hippocampus
        self.graph = graph
        self.retrieval = retrieval_engine

    def get_brain_state(self) -> BrainState:
        state = BrainState()
        if self.hippocampus:
            hstats = self.hippocampus.to_dict()
            state.total_memories = hstats.get("total_memories", 0)
            state.active_memories = hstats.get("active_memories", 0)
            state.high_salience_memories = hstats.get("high_salience", 0)
        if self.graph:
            state.graph_facts = len(self.graph.facts)
            state.graph_entities = len(self.graph.entities)
        return state

    def generate_system_prompt(self, base_prompt: str = "", include_memory: bool = True) -> str:
        """Generate a system prompt augmented with brain awareness."""
        state = self.get_brain_state()
        lines = [base_prompt or "You are an AI agent with a biologically-inspired memory system."]
        if include_memory:
            lines.append("")
            lines.append("## Memory System Status")
            lines.append(f"- Total memories: {state.total_memories}")
            lines.append(f"- Active memories: {state.active_memories}")
            lines.append(f"- High-importance memories: {state.high_salience_memories}")
            lines.append(f"- Knowledge graph facts: {state.graph_facts}")
            lines.append(f"- Known entities: {state.graph_entities}")
            lines.append("")
            lines.append("## Memory Guidelines")
            lines.append("- Use the `synapse_remember` tool to explicitly save facts worth remembering forever.")
            lines.append("- Important memories persist. Unimportant ones fade over time.")
            lines.append("- Memories have temporal validity — facts can change over time.")
            lines.append("- When answering, consider the recency and salience of related memories.")
            lines.append("")
        return "\n".join(lines)

    def generate_memory_aware_prompt(self, user_query: str, retrieved_memories: Optional[List[str]] = None) -> str:
        """Generate a prompt that includes retrieved memories."""
        lines = [self.generate_system_prompt()]
        if retrieved_memories:
            lines.append("## Retrieved Memories")
            for mem in retrieved_memories[:10]:
                lines.append(f"- {mem}")
            lines.append("")
        lines.append(f"## User Query")
        lines.append(user_query)
        return "\n".join(lines)

    def generate_remember_tool(self, fact: str, importance: float = 0.5) -> Dict:
        """Generate a synapse_remember tool call structure."""
        return {
            "tool": "synapse_remember",
            "params": {
                "fact": fact,
                "importance": importance,
                "timestamp": datetime.now().isoformat(),
            },
            "description": "Explicitly save a fact to long-term memory",
        }

    def generate_consolidation_prompt(self) -> str:
        """Generate prompt for memory consolidation (sleep replay)."""
        return """You are performing memory consolidation. Review these memories:
1. Strengthen connections between frequently co-occurring concepts
2. Detect and resolve contradictions
3. Summarize important memories into higher-level abstractions
4. Prune weak, low-salience memories
5. Tag memories with emotional significance for better retention"""

    def to_dict(self) -> Dict:
        return {
            "brain_state": self.get_brain_state().__dict__,
            "has_hippocampus": self.hippocampus is not None,
            "has_graph": self.graph is not None,
        }


__all__ = ["BrainAwarePromptGenerator", "BrainState"]

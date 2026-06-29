
"""
memory_consolidation_engine_native.py
MAGNATRIX-OS — Memory Consolidation Engine

Inspired by Synapse consolidation engine:
- Hebbian strengthening of co-occurring entities
- Contradiction detection across temporal facts
- Synaptic pruning of weak connections
- Sleep replay pattern for background consolidation

Pure Python standard library.
"""

import json
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path


@dataclass
class ConsolidationReport:
    strengthened: int = 0
    contradictions_found: int = 0
    pruned: int = 0
    new_connections: int = 0
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class MemoryConsolidationEngine:
    """Background consolidation engine for temporal knowledge graph."""

    def __init__(self, graph=None, hippocampus=None):
        self.graph = graph
        self.hippocampus = hippocampus
        self.reports: List[ConsolidationReport] = []
        self.contradiction_log: List[Dict] = []

    def consolidate(self) -> ConsolidationReport:
        """Run full consolidation cycle (sleep replay)."""
        report = ConsolidationReport()
        if self.graph:
            report.strengthened = self._hebbian_strengthening()
            report.contradictions_found = self._detect_contradictions()
            report.pruned = self._synaptic_pruning()
            report.new_connections = self._discover_connections()
        if self.hippocampus:
            self.hippocampus.prune_forgotten()
        self.reports.append(report)
        return report

    def _hebbian_strengthening(self) -> int:
        """Strengthen edges between entities that co-occur in facts."""
        if not self.graph:
            return 0
        strengthened = 0
        entity_facts: Dict[str, List[str]] = {}
        for fact in self.graph.facts.values():
            for entity in [fact.subject, fact.object]:
                entity_facts.setdefault(entity, []).append(fact.fact_id)
        # Find co-occurring entities and strengthen edges
        for fact in self.graph.facts.values():
            subject = fact.subject
            obj = fact.object
            for edge in self.graph.edges.values():
                if (edge.from_entity == subject and edge.to_entity == obj) or \
                   (edge.from_entity == obj and edge.to_entity == subject):
                    # Hebbian learning: fire together, wire together
                    edge.weight = min(1.0, edge.weight + 0.1)
                    strengthened += 1
        self.graph._save()
        return strengthened

    def _detect_contradictions(self) -> int:
        """Find contradictory facts about the same entity."""
        if not self.graph:
            return 0
        contradictions = 0
        entity_facts: Dict[str, List[Any]] = {}
        for fact in self.graph.facts.values():
            key = f"{fact.subject}:{fact.predicate}"
            entity_facts.setdefault(key, []).append(fact)
        # Check for contradictory objects
        for key, facts in entity_facts.items():
            if len(facts) < 2:
                continue
            # Sort by time
            sorted_facts = sorted(facts, key=lambda f: f.valid_from)
            for i in range(1, len(sorted_facts)):
                prev = sorted_facts[i - 1]
                curr = sorted_facts[i]
                # If same predicate but different object, check if previous was invalidated
                if prev.object != curr.object and prev.valid_until is None:
                    # Contradiction: previous fact still valid but different object claimed
                    self.contradiction_log.append({
                        "subject": curr.subject,
                        "predicate": curr.predicate,
                        "previous": prev.object,
                        "current": curr.object,
                        "resolved": False,
                    })
                    # Mark previous as invalid (newer fact supersedes)
                    prev.valid_until = curr.valid_from
                    contradictions += 1
        if contradictions > 0:
            self.graph._save()
        return contradictions

    def _synaptic_pruning(self) -> int:
        """Remove weak connections."""
        if not self.graph:
            return 0
        to_remove = []
        for eid, edge in self.graph.edges.items():
            if edge.weight < 0.2:
                to_remove.append(eid)
        for eid in to_remove:
            del self.graph.edges[eid]
        if to_remove:
            self.graph._save()
        return len(to_remove)

    def _discover_connections(self) -> int:
        """Discover new connections through transitive relationships."""
        if not self.graph:
            return 0
        new_connections = 0
        # Simple transitive closure: A->B, B->C implies A->C
        for e1 in self.graph.edges.values():
            for e2 in self.graph.edges.values():
                if e1.to_entity == e2.from_entity and e1.from_entity != e2.to_entity:
                    # Check if connection already exists
                    exists = False
                    for e3 in self.graph.edges.values():
                        if e3.from_entity == e1.from_entity and e3.to_entity == e2.to_entity:
                            exists = True
                            break
                    if not exists:
                        self.graph.add_edge(
                            e1.from_entity, e2.to_entity, "derived",
                            weight=e1.weight * e2.weight * 0.5,
                            properties={"via": e1.to_entity, "transitive": True}
                        )
                        new_connections += 1
        return new_connections

    def get_stats(self) -> Dict:
        return {
            "total_reports": len(self.reports),
            "total_contradictions": len(self.contradiction_log),
            "last_report": asdict(self.reports[-1]) if self.reports else {},
        }

    def to_dict(self) -> Dict:
        return {
            "reports": len(self.reports),
            "contradictions": len(self.contradiction_log),
        }


__all__ = ["MemoryConsolidationEngine", "ConsolidationReport"]

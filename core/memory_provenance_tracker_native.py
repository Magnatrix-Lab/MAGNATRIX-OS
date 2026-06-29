
"""
memory_provenance_tracker_native.py
MAGNATRIX-OS — Memory Provenance Tracker

Inspired by Memanto provenance system:
Confidence + provenance metadata on every memory.
Distinguishes explicit facts from inferred patterns or outdated info.

Pure Python standard library.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum, auto


class ProvenanceSource(Enum):
    EXPLICIT = "explicit"       # User directly stated this
    INFERRED = "inferred"       # Model inferred from context
    OBSERVED = "observed"       # Observed from agent behavior
    IMPORTED = "imported"       # Imported from external source
    DERIVED = "derived"         # Derived from other memories
    EXTERNAL = "external"       # External data source


class ConfidenceLevel(Enum):
    CERTAIN = 1.0
    HIGH = 0.9
    MEDIUM = 0.7
    LOW = 0.5
    UNCERTAIN = 0.3
    SPECULATIVE = 0.1


@dataclass
class ProvenanceRecord:
    memory_id: str
    source: str
    confidence: float
    origin: str
    created_by: str
    extraction_method: str
    verification_status: str = "unverified"
    verified_by: Optional[str] = None
    verified_at: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class MemoryProvenanceTracker:
    """Track provenance and confidence for every memory."""

    def __init__(self, provenance_file: str = "memory_provenance.json"):
        self.provenance_file = Path(provenance_file)
        self.provenance_file.parent.mkdir(parents=True, exist_ok=True)
        self.records: Dict[str, ProvenanceRecord] = {}
        self._load()

    def _load(self) -> None:
        if self.provenance_file.exists():
            try:
                with open(self.provenance_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for mid, pd in data.items():
                        self.records[mid] = ProvenanceRecord(**pd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.provenance_file, "w", encoding="utf-8") as f:
            json.dump({mid: asdict(r) for mid, r in self.records.items()}, f, indent=2)

    def record(self, memory_id: str, source: str, confidence: float,
               origin: str, created_by: str = "agent",
               extraction_method: str = "manual",
               dependencies: Optional[List[str]] = None) -> ProvenanceRecord:
        """Record provenance for a new memory."""
        record = ProvenanceRecord(
            memory_id=memory_id, source=source, confidence=confidence,
            origin=origin, created_by=created_by,
            extraction_method=extraction_method,
            dependencies=dependencies or [],
            metadata={"recorded_at": datetime.now().isoformat()},
        )
        self.records[memory_id] = record
        self._save()
        return record

    def verify(self, memory_id: str, verified_by: str) -> bool:
        """Mark a memory as verified."""
        if memory_id not in self.records:
            return False
        self.records[memory_id].verification_status = "verified"
        self.records[memory_id].verified_by = verified_by
        self.records[memory_id].verified_at = datetime.now().isoformat()
        self.records[memory_id].confidence = min(1.0, self.records[memory_id].confidence + 0.1)
        self._save()
        return True

    def flag_outdated(self, memory_id: str, reason: str) -> bool:
        """Flag a memory as outdated."""
        if memory_id not in self.records:
            return False
        self.records[memory_id].verification_status = "outdated"
        self.records[memory_id].metadata["outdated_reason"] = reason
        self.records[memory_id].confidence *= 0.5
        self._save()
        return True

    def get_confidence(self, memory_id: str) -> float:
        """Get confidence score for a memory."""
        record = self.records.get(memory_id)
        return record.confidence if record else 0.0

    def get_by_source(self, source: str) -> List[ProvenanceRecord]:
        return [r for r in self.records.values() if r.source == source]

    def get_by_confidence_range(self, min_conf: float, max_conf: float) -> List[ProvenanceRecord]:
        return [r for r in self.records.values() if min_conf <= r.confidence <= max_conf]

    def get_unverified(self) -> List[ProvenanceRecord]:
        return [r for r in self.records.values() if r.verification_status == "unverified"]

    def get_trusted_facts(self, min_confidence: float = 0.8) -> List[ProvenanceRecord]:
        """Get facts that are verified or high-confidence."""
        return [r for r in self.records.values()
                if r.confidence >= min_confidence and r.verification_status in ("verified", "unverified")]

    def get_stats(self) -> Dict[str, Any]:
        sources = {}
        statuses = {}
        for r in self.records.values():
            sources[r.source] = sources.get(r.source, 0) + 1
            statuses[r.verification_status] = statuses.get(r.verification_status, 0) + 1
        return {
            "total_records": len(self.records),
            "source_breakdown": sources,
            "status_breakdown": statuses,
            "avg_confidence": sum(r.confidence for r in self.records.values()) / max(len(self.records), 1),
            "verified_count": sum(1 for r in self.records.values() if r.verification_status == "verified"),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["MemoryProvenanceTracker", "ProvenanceRecord", "ProvenanceSource", "ConfidenceLevel"]

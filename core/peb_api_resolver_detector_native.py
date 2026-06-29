
"""
peb_api_resolver_detector_native.py
MAGNATRIX-OS — PEB API Resolver Detector

Detects Process Environment Block (PEB) walking techniques used
to resolve Win32/NT APIs without static imports.
Inspired by Proteus no_std/no_main agent.

Pure Python standard library.
"""

import struct
import re
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path


@dataclass
class PEBDetection:
    technique: str
    api_name: str
    confidence: float
    offset: int
    architecture: str = "x86"


class PEBAPIResolverDetector:
    """Detect PEB-walked API resolution in binaries."""

    # PEB access opcodes by architecture
    PEB_PATTERNS_X86 = [
        (b"\x64\xa1\x30\x00\x00\x00", "mov eax, fs:[0x30]", "PEB access via FS"),
        (b"\x64\x8b\x1d\x30\x00\x00\x00", "mov ebx, fs:[0x30]", "PEB access via FS"),
        (b"\x64\x8b\x35\x30\x00\x00\x00", "mov esi, fs:[0x30]", "PEB access via FS"),
        (b"\x64\x8b\x3d\x30\x00\x00\x00", "mov edi, fs:[0x30]", "PEB access via FS"),
    ]

    PEB_PATTERNS_X64 = [
        (b"\x65\x48\x8b\x04\x25\x60\x00\x00\x00", "mov rax, gs:[0x60]", "PEB access via GS"),
        (b"\x65\x48\x8b\x1c\x25\x60\x00\x00\x00", "mov rbx, gs:[0x60]", "PEB access via GS"),
        (b"\x65\x4c\x8b\x04\x25\x60\x00\x00\x00", "mov r8, gs:[0x60]", "PEB access via GS"),
        (b"\x65\x4c\x8b\x0c\x25\x60\x00\x00\x00", "mov r9, gs:[0x60]", "PEB access via GS"),
    ]

    # LDR_DATA_TABLE_ENTRY traversal patterns
    LDR_PATTERNS = [
        (b"\x0f\xb7\x48\x4c", "movzx ecx, word [eax+0x4c]", "LDR InMemoryOrderModuleList traversal"),
        (b"\x48\x8b\x48\x18", "mov rcx, [rax+0x18]", "x64 LDR module list access"),
    ]

    # Hash-based API resolution patterns
    HASH_API_PATTERNS = [
        b"GetProcAddress",
        b"LdrGetProcedureAddress",
        b"LdrLoadDll",
    ]

    def __init__(self):
        self.detections: List[PEBDetection] = []
        self.scanned_files: Set[str] = set()

    def scan(self, filepath: str) -> List[PEBDetection]:
        """Scan binary for PEB API resolution patterns."""
        detections = []
        try:
            with open(filepath, "rb") as f:
                data = f.read()

            # Check x86 PEB patterns
            for pattern, disasm, desc in self.PEB_PATTERNS_X86:
                offset = 0
                while True:
                    pos = data.find(pattern, offset)
                    if pos == -1:
                        break
                    detections.append(PEBDetection(
                        technique="peb_access_x86",
                        api_name=desc,
                        confidence=0.95,
                        offset=pos,
                        architecture="x86",
                    ))
                    offset = pos + 1

            # Check x64 PEB patterns
            for pattern, disasm, desc in self.PEB_PATTERNS_X64:
                offset = 0
                while True:
                    pos = data.find(pattern, offset)
                    if pos == -1:
                        break
                    detections.append(PEBDetection(
                        technique="peb_access_x64",
                        api_name=desc,
                        confidence=0.95,
                        offset=pos,
                        architecture="x64",
                    ))
                    offset = pos + 1

            # Check LDR traversal patterns
            for pattern, disasm, desc in self.LDR_PATTERNS:
                offset = 0
                while True:
                    pos = data.find(pattern, offset)
                    if pos == -1:
                        break
                    detections.append(PEBDetection(
                        technique="ldr_traversal",
                        api_name=desc,
                        confidence=0.9,
                        offset=pos,
                        architecture="x64" if b"\x48" in pattern[:2] else "x86",
                    ))
                    offset = pos + 1

            # Check for hash-based API resolution strings
            for pattern in self.HASH_API_PATTERNS:
                offset = 0
                while True:
                    pos = data.find(pattern, offset)
                    if pos == -1:
                        break
                    detections.append(PEBDetection(
                        technique="hash_api_resolution",
                        api_name=pattern.decode("latin-1"),
                        confidence=0.85,
                        offset=pos,
                        architecture="both",
                    ))
                    offset = pos + 1

            # Check for common API hashes (djb2, ROR13, etc.)
            # Proteus uses PEB walking with hash comparisons
            hash_patterns = [b"hash", b"djb2", b"ror13", b"api_hash"]
            for pat in hash_patterns:
                if pat in data.lower():
                    detections.append(PEBDetection(
                        technique="api_hash_strings",
                        api_name=pat.decode("latin-1"),
                        confidence=0.7,
                        offset=data.lower().find(pat),
                        architecture="both",
                    ))

        except Exception:
            pass

        self.detections.extend(detections)
        self.scanned_files.add(filepath)
        return detections

    def get_peb_access_count(self, filepath: Optional[str] = None) -> int:
        """Count total PEB access patterns detected."""
        detections = [d for d in self.detections if d.technique.startswith("peb_access_")]
        if filepath:
            # Filter by file (approximate, using stored detections)
            pass
        return len(detections)

    def get_architecture_breakdown(self) -> Dict[str, int]:
        """Get breakdown by architecture."""
        counts = {}
        for d in self.detections:
            counts[d.architecture] = counts.get(d.architecture, 0) + 1
        return counts

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_detections": len(self.detections),
            "files_scanned": len(self.scanned_files),
            "peb_access_count": self.get_peb_access_count(),
            "architecture_breakdown": self.get_architecture_breakdown(),
            "techniques": list(set(d.technique for d in self.detections)),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["PEBAPIResolverDetector", "PEBDetection"]

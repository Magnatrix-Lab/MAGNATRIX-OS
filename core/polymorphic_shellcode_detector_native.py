
"""
polymorphic_shellcode_detector_native.py
MAGNATRIX-OS — Polymorphic Shellcode Detector

Detects polymorphic shellcode techniques inspired by Proteus:
- Per-build function shuffle (randomized function ordering)
- ChaCha20-encrypted data sections
- no_std/no_main patterns
- PEB-walked API resolution

Pure Python standard library.
"""

import struct
import re
import hashlib
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path


class ShellcodeThreatLevel(Enum):
    BENIGN = "benign"
    SUSPICIOUS = "suspicious"
    LIKELY_MALICIOUS = "likely_malicious"
    CONFIRMED_MALICIOUS = "confirmed_malicious"


@dataclass
class PolymorphicDetection:
    technique: str
    confidence: float
    evidence: str
    offset: int = 0


class PolymorphicShellcodeDetector:
    """Detect polymorphic shellcode patterns (Proteus-style)."""

    # ChaCha20 constants and patterns
    CHACHA20_SIGMA = b"expand 32-byte k"
    CHACHA20_QUARTER_ROUND = [
        0x61707865, 0x3320646e, 0x79622d32, 0x6b206574,
    ]

    # PEB walking patterns (common in no_std/no_main agents)
    PEB_PATTERNS = [
        b"\x64\xa1\x30\x00\x00\x00",  # mov eax, fs:[0x30] (PEB)
        b"\x64\x8b\x1d\x30\x00\x00\x00",  # mov ebx, fs:[0x30]
        b"\x48\x65\x48\x8b\x04\x25\x60\x00",  # mov rax, gs:[0x60] (x64 PEB)
        b"\x65\x48\x8b\x04\x25\x60\x00\x00\x00",  # x64 PEB access
    ]

    # Function shuffle indicators (high entropy in function order)
    SHUFFLE_INDICATORS = [
        r"_start\x00",  # Custom _start instead of main
        r"initialize\x00",
        r"Instance\x00",
    ]

    def __init__(self):
        self.detections: List[PolymorphicDetection] = []
        self.scanned_files: Set[str] = set()

    def scan(self, filepath: str) -> List[PolymorphicDetection]:
        """Scan a binary for polymorphic shellcode indicators."""
        detections = []
        try:
            with open(filepath, "rb") as f:
                data = f.read()

            # Check 1: ChaCha20 encryption indicators
            chacha = self._detect_chacha20(data)
            if chacha:
                detections.extend(chacha)

            # Check 2: PEB walking patterns
            peb = self._detect_peb_walking(data)
            if peb:
                detections.extend(peb)

            # Check 3: no_std/no_main indicators
            nostd = self._detect_no_std_patterns(data)
            if nostd:
                detections.extend(nostd)

            # Check 4: Function entropy (shuffle detection)
            entropy = self._detect_function_shuffle(data)
            if entropy:
                detections.extend(entropy)

            # Check 5: Encrypted data sections
            encrypted = self._detect_encrypted_sections(data)
            if encrypted:
                detections.extend(encrypted)

        except Exception:
            pass

        self.detections.extend(detections)
        self.scanned_files.add(filepath)
        return detections

    def _detect_chacha20(self, data: bytes) -> List[PolymorphicDetection]:
        """Detect ChaCha20 encryption constants and patterns."""
        detections = []
        # Check for sigma constant
        if self.CHACHA20_SIGMA in data:
            detections.append(PolymorphicDetection(
                technique="chacha20_constant",
                confidence=0.9,
                evidence="ChaCha20 sigma constant 'expand 32-byte k' found in binary",
                offset=data.find(self.CHACHA20_SIGMA),
            ))
        # Check for quarter-round constants
        for i, const in enumerate(self.CHACHA20_QUARTER_ROUND):
            const_bytes = struct.pack("<I", const)
            if const_bytes in data:
                detections.append(PolymorphicDetection(
                    technique="chacha20_quarter_round",
                    confidence=0.85,
                    evidence=f"ChaCha20 quarter-round constant {i} found",
                    offset=data.find(const_bytes),
                ))
        # Check for ChaCha20 stream cipher patterns
        if b"chacha" in data.lower() or b"chacha20" in data.lower():
            detections.append(PolymorphicDetection(
                technique="chacha20_reference",
                confidence=0.8,
                evidence="ChaCha20 string reference found",
            ))
        return detections

    def _detect_peb_walking(self, data: bytes) -> List[PolymorphicDetection]:
        """Detect PEB walking API resolution patterns."""
        detections = []
        for pattern in self.PEB_PATTERNS:
            if pattern in data:
                detections.append(PolymorphicDetection(
                    technique="peb_walking",
                    confidence=0.9,
                    evidence=f"PEB access pattern found at offset {data.find(pattern)}",
                    offset=data.find(pattern),
                ))
        # Check for LdrLoadDll / LdrGetProcedureAddress strings
        ldr_patterns = [b"LdrLoadDll", b"LdrGetProcedureAddress", b"LdrEnumerateLoadedModules"]
        for pat in ldr_patterns:
            if pat in data:
                detections.append(PolymorphicDetection(
                    technique="ntdll_ldr_api",
                    confidence=0.85,
                    evidence=f"NTDLL LDR API reference: {pat.decode('latin-1')}",
                    offset=data.find(pat),
                ))
        return detections

    def _detect_no_std_patterns(self, data: bytes) -> List[PolymorphicDetection]:
        """Detect no_std/no_main Rust patterns."""
        detections = []
        # Custom _start instead of standard entry point
        if b"_start\x00" in data:
            detections.append(PolymorphicDetection(
                technique="custom_start",
                confidence=0.7,
                evidence="Custom _start entry point found (no_main pattern)",
                offset=data.find(b"_start\x00"),
            ))
        # No standard library indicators
        if b"no_std" in data.lower() or b"no_std" in data.lower():
            detections.append(PolymorphicDetection(
                technique="no_std_indicator",
                confidence=0.75,
                evidence="no_std indicator found in binary",
            ))
        # Rust panic handler patterns
        if b"rust_begin_unwind" in data or b"_Unwind_Resume" in data:
            detections.append(PolymorphicDetection(
                technique="rust_unwind",
                confidence=0.6,
                evidence="Rust unwind/panic handler found",
            ))
        return detections

    def _detect_function_shuffle(self, data: bytes) -> List[PolymorphicDetection]:
        """Detect function shuffling via entropy analysis."""
        detections = []
        # High entropy in code section suggests function shuffling
        # Calculate entropy of executable sections
        entropy = self._calculate_entropy(data)
        if entropy > 7.5:  # Very high entropy
            detections.append(PolymorphicDetection(
                technique="high_entropy_shuffle",
                confidence=0.75,
                evidence=f"Very high binary entropy ({entropy:.2f}) suggests function shuffling or encryption",
            ))
        # Check for linker shuffle patterns
        if b"shuffled" in data.lower() or b"shuffle" in data.lower():
            detections.append(PolymorphicDetection(
                technique="shuffle_linker",
                confidence=0.8,
                evidence="Shuffle linker pattern found in binary",
            ))
        return detections

    def _detect_encrypted_sections(self, data: bytes) -> List[PolymorphicDetection]:
        """Detect encrypted/obfuscated data sections."""
        detections = []
        # Look for .rdata$prx_obf sections (Proteus specific)
        if b".rdata$prx_obf" in data or b"prx_obf" in data:
            detections.append(PolymorphicDetection(
                technique="proteus_obf_section",
                confidence=0.95,
                evidence="Proteus obfuscated data section (.rdata$prx_obf) detected",
            ))
        # Check for encrypted data sections with high entropy
        # Parse PE sections
        sections = self._parse_pe_sections(data)
        for section_name, section_data in sections.items():
            sec_entropy = self._calculate_entropy(section_data)
            if sec_entropy > 7.8 and section_name in [b".rdata", b".data", b".text"]:
                detections.append(PolymorphicDetection(
                    technique="encrypted_section",
                    confidence=0.8,
                    evidence=f"High entropy ({sec_entropy:.2f}) in section {section_name.decode('latin-1', errors='ignore')} suggests encryption",
                ))
        return detections

    def _calculate_entropy(self, data: bytes) -> float:
        """Calculate Shannon entropy of data."""
        if not data:
            return 0.0
        from math import log2
        freq = {}
        for byte in data:
            freq[byte] = freq.get(byte, 0) + 1
        entropy = 0.0
        length = len(data)
        for count in freq.values():
            p = count / length
            entropy -= p * log2(p)
        return entropy

    def _parse_pe_sections(self, data: bytes) -> Dict[bytes, bytes]:
        """Parse PE sections from binary data."""
        sections = {}
        if len(data) < 64 or data[:2] != b"MZ":
            return sections
        try:
            pe_offset = struct.unpack("<I", data[0x3C:0x40])[0]
            if data[pe_offset:pe_offset+4] != b"PE\x00\x00":
                return sections
            num_sections = struct.unpack("<H", data[pe_offset+6:pe_offset+8])[0]
            opt_header_size = struct.unpack("<H", data[pe_offset+20:pe_offset+22])[0]
            section_table = pe_offset + 24 + opt_header_size
            for i in range(num_sections):
                sec_offset = section_table + i * 40
                if sec_offset + 40 > len(data):
                    break
                name = data[sec_offset:sec_offset+8].rstrip(b"\x00")
                raw_size = struct.unpack("<I", data[sec_offset+16:sec_offset+20])[0]
                raw_addr = struct.unpack("<I", data[sec_offset+20:sec_offset+24])[0]
                if raw_addr + raw_size <= len(data):
                    sections[name] = data[raw_addr:raw_addr+raw_size]
        except Exception:
            pass
        return sections

    def get_threat_level(self, detections: Optional[List[PolymorphicDetection]] = None) -> str:
        """Calculate overall threat level from detections."""
        if detections is None:
            detections = self.detections
        if not detections:
            return ShellcodeThreatLevel.BENIGN.value
        # Weighted scoring
        score = 0.0
        technique_weights = {
            "proteus_obf_section": 1.0,
            "chacha20_constant": 0.9,
            "peb_walking": 0.9,
            "ntdll_ldr_api": 0.85,
            "chacha20_quarter_round": 0.85,
            "shuffle_linker": 0.8,
            "encrypted_section": 0.8,
            "chacha20_reference": 0.7,
            "custom_start": 0.7,
            "no_std_indicator": 0.75,
            "high_entropy_shuffle": 0.75,
            "rust_unwind": 0.6,
        }
        for d in detections:
            weight = technique_weights.get(d.technique, 0.5)
            score += weight * d.confidence
        if score >= 2.5:
            return ShellcodeThreatLevel.CONFIRMED_MALICIOUS.value
        elif score >= 1.5:
            return ShellcodeThreatLevel.LIKELY_MALICIOUS.value
        elif score >= 0.8:
            return ShellcodeThreatLevel.SUSPICIOUS.value
        return ShellcodeThreatLevel.BENIGN.value

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_detections": len(self.detections),
            "files_scanned": len(self.scanned_files),
            "threat_level": self.get_threat_level(),
            "techniques": list(set(d.technique for d in self.detections)),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["PolymorphicShellcodeDetector", "PolymorphicDetection", "ShellcodeThreatLevel"]

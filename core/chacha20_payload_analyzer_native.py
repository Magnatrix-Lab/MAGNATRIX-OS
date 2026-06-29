
"""
chacha20_payload_analyzer_native.py
MAGNATRIX-OS — ChaCha20 Payload Analyzer

Analyze ChaCha20-encrypted payloads and data sections.
Implements ChaCha20 keystream detection, key extraction patterns,
and encrypted section analysis.
Inspired by Proteus data-section ciphering.

Pure Python standard library.
"""

import struct
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ChaCha20Analysis:
    section_name: str
    encrypted_size: int
    entropy: float
    key_indicators: List[str] = field(default_factory=list)
    likely_key_size: int = 32


class ChaCha20PayloadAnalyzer:
    """Analyze ChaCha20 encrypted payloads and data sections."""

    CHACHA20_STATE_SIZE = 64
    CHACHA20_KEY_SIZE = 32
    CHACHA20_NONCE_SIZE = 12
    CHACHA20_BLOCK_SIZE = 64

    # ChaCha20 quarter-round constants (little-endian)
    CONSTANTS = [0x61707865, 0x3320646e, 0x79622d32, 0x6b206574]

    def __init__(self):
        self.analyses: List[ChaCha20Analysis] = []

    def analyze_binary(self, filepath: str) -> List[ChaCha20Analysis]:
        """Analyze a binary for ChaCha20 encrypted sections."""
        analyses = []
        try:
            with open(filepath, "rb") as f:
                data = f.read()
            # Parse PE sections
            sections = self._parse_pe_sections(data)
            for section_name, section_data in sections.items():
                analysis = self._analyze_section(section_name, section_data)
                if analysis:
                    analyses.append(analysis)
            # Also check for embedded ChaCha20 state/keys
            key_indicators = self._find_key_indicators(data)
            if key_indicators:
                analyses.append(ChaCha20Analysis(
                    section_name=".embedded",
                    encrypted_size=0,
                    entropy=0.0,
                    key_indicators=key_indicators,
                ))
        except Exception:
            pass
        self.analyses.extend(analyses)
        return analyses

    def _parse_pe_sections(self, data: bytes) -> Dict[bytes, bytes]:
        """Parse PE sections."""
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

    def _analyze_section(self, name: bytes, data: bytes) -> Optional[ChaCha20Analysis]:
        """Analyze a single section for ChaCha20 indicators."""
        entropy = self._calculate_entropy(data)
        indicators = []
        # High entropy in data section suggests encryption
        if entropy > 7.5 and name in [b".rdata", b".data", b".rdata$prx_obf"]:
            indicators.append(f"High entropy ({entropy:.2f}) in {name.decode('latin-1', errors='ignore')}")
        # Check for ChaCha20 sigma constant
        if b"expand 32-byte k" in data:
            indicators.append("ChaCha20 sigma constant found")
        # Check for ChaCha20 block patterns (64-byte aligned high entropy)
        if len(data) >= 64:
            for i in range(0, len(data) - 64, 64):
                block = data[i:i+64]
                block_entropy = self._calculate_entropy(block)
                if block_entropy > 7.9:
                    indicators.append(f"High entropy block at offset {i}")
                    break
        if not indicators:
            return None
        return ChaCha20Analysis(
            section_name=name.decode("latin-1", errors="ignore"),
            encrypted_size=len(data),
            entropy=entropy,
            key_indicators=indicators,
        )

    def _find_key_indicators(self, data: bytes) -> List[str]:
        """Find ChaCha20 key/nonce indicators in binary."""
        indicators = []
        # Look for 32-byte key patterns
        text = data.decode("latin-1", errors="ignore")
        # Master key references
        if "master_key" in text.lower() or "MASTER_KEY" in text:
            indicators.append("Master key reference found")
        # Nonce salt references
        if "nonce_salt" in text.lower() or "NONCE_SALT" in text:
            indicators.append("Nonce salt reference found")
        # Build config references
        if "build_config" in text.lower() or "BUILD_CONFIG" in text:
            indicators.append("Build config reference found")
        # ChaCha20 specific strings
        if "chacha20" in text.lower():
            indicators.append("ChaCha20 string reference")
        if "proteus" in text.lower():
            indicators.append("Proteus reference found")
        return indicators

    def _calculate_entropy(self, data: bytes) -> float:
        from math import log2
        if not data:
            return 0.0
        freq = {}
        for byte in data:
            freq[byte] = freq.get(byte, 0) + 1
        entropy = 0.0
        length = len(data)
        for count in freq.values():
            p = count / length
            entropy -= p * log2(p)
        return entropy

    def get_likely_key_size(self, data: bytes) -> int:
        """Infer ChaCha20 key size from patterns."""
        # Standard ChaCha20 uses 256-bit (32-byte) key
        return 32

    def get_stats(self) -> Dict[str, Any]:
        total_sections = len(self.analyses)
        high_entropy = sum(1 for a in self.analyses if a.entropy > 7.5)
        return {
            "total_sections_analyzed": total_sections,
            "high_entropy_sections": high_entropy,
            "key_indicators_found": sum(len(a.key_indicators) for a in self.analyses),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["ChaCha20PayloadAnalyzer", "ChaCha20Analysis"]

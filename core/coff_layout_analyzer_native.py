
"""
coff_layout_analyzer_native.py
MAGNATRIX-OS — COFF Layout Analyzer

Analyze COFF (Common Object File Format) layouts to detect
function shuffling, obfuscated sections, and polymorphic binary
generation patterns. Inspired by Proteus layout-manifest.

Pure Python standard library.
"""

import struct
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class COFFSection:
    name: str
    virtual_size: int
    virtual_address: int
    raw_size: int
    raw_address: int
    characteristics: int
    entropy: float = 0.0
    is_obfuscated: bool = False


@dataclass
class COFFRelocation:
    virtual_address: int
    symbol_index: int
    type: int


class COFFLayoutAnalyzer:
    """Analyze COFF binary layouts for obfuscation and shuffling."""

    # COFF machine types
    MACHINE_TYPES = {
        0x14c: "i386",
        0x8664: "AMD64",
        0xaa64: "ARM64",
    }

    # Section characteristics flags
    SCN_CNT_CODE = 0x00000020
    SCN_CNT_INITIALIZED_DATA = 0x00000040
    SCN_CNT_UNINITIALIZED_DATA = 0x00000080
    SCN_MEM_EXECUTE = 0x20000000
    SCN_MEM_READ = 0x40000000
    SCN_MEM_WRITE = 0x80000000

    def __init__(self):
        self.analyses: List[Dict] = []

    def analyze(self, filepath: str) -> Dict[str, Any]:
        """Analyze a COFF/PE file for layout anomalies."""
        result = {
            "filepath": filepath,
            "machine_type": "unknown",
            "sections": [],
            "is_shuffled": False,
            "has_obfuscated_sections": False,
            "entropy_analysis": {},
            "anomalies": [],
        }
        try:
            with open(filepath, "rb") as f:
                data = f.read()

            if len(data) < 64 or data[:2] != b"MZ":
                return result

            # Parse PE header
            pe_offset = struct.unpack("<I", data[0x3C:0x40])[0]
            if data[pe_offset:pe_offset+4] != b"PE\x00\x00":
                return result

            machine = struct.unpack("<H", data[pe_offset+4:pe_offset+6])[0]
            result["machine_type"] = self.MACHINE_TYPES.get(machine, f"0x{machine:04x}")

            num_sections = struct.unpack("<H", data[pe_offset+6:pe_offset+8])[0]
            opt_header_size = struct.unpack("<H", data[pe_offset+20:pe_offset+22])[0]
            section_table = pe_offset + 24 + opt_header_size

            sections = []
            for i in range(num_sections):
                sec_offset = section_table + i * 40
                if sec_offset + 40 > len(data):
                    break

                name = data[sec_offset:sec_offset+8].rstrip(b"\x00").decode("latin-1", errors="ignore")
                virtual_size = struct.unpack("<I", data[sec_offset+8:sec_offset+12])[0]
                virtual_address = struct.unpack("<I", data[sec_offset+12:sec_offset+16])[0]
                raw_size = struct.unpack("<I", data[sec_offset+16:sec_offset+20])[0]
                raw_address = struct.unpack("<I", data[sec_offset+20:sec_offset+24])[0]
                characteristics = struct.unpack("<I", data[sec_offset+36:sec_offset+40])[0]

                section_data = b""
                if raw_address + raw_size <= len(data):
                    section_data = data[raw_address:raw_address+raw_size]

                entropy = self._calculate_entropy(section_data)
                is_obf = entropy > 7.8 or "obf" in name.lower() or "prx" in name.lower()

                section = COFFSection(
                    name=name, virtual_size=virtual_size, virtual_address=virtual_address,
                    raw_size=raw_size, raw_address=raw_address, characteristics=characteristics,
                    entropy=entropy, is_obfuscated=is_obf,
                )
                sections.append(section)

                if is_obf:
                    result["has_obfuscated_sections"] = True
                    result["anomalies"].append(f"High entropy/obfuscated section: {name}")

            result["sections"] = [{
                "name": s.name, "virtual_size": s.virtual_size,
                "raw_size": s.raw_size, "entropy": round(s.entropy, 2),
                "is_obfuscated": s.is_obfuscated,
                "is_executable": bool(s.characteristics & self.SCN_MEM_EXECUTE),
                "is_writable": bool(s.characteristics & self.SCN_MEM_WRITE),
            } for s in sections]

            # Detect function shuffling: check for non-standard section ordering
            standard_order = [".text", ".data", ".rdata", ".bss", ".pdata", ".xdata", ".idata", ".edata", ".reloc"]
            section_names = [s.name for s in sections]
            if section_names and not any(s in section_names for s in standard_order[:3]):
                result["is_shuffled"] = True
                result["anomalies"].append("Non-standard section ordering - possible function shuffling")

            # Check for .rdata$prx_obf sections (Proteus specific)
            if any("prx_obf" in s.name for s in sections):
                result["anomalies"].append("Proteus obfuscated section (.rdata$prx_obf) detected")

            # Entropy analysis
            if sections:
                avg_entropy = sum(s.entropy for s in sections) / len(sections)
                result["entropy_analysis"] = {
                    "average": round(avg_entropy, 2),
                    "max": round(max(s.entropy for s in sections), 2),
                    "min": round(min(s.entropy for s in sections), 2),
                }

        except Exception:
            pass

        self.analyses.append(result)
        return result

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

    def get_shuffled_binaries(self) -> List[Dict]:
        """Get list of binaries showing function shuffle patterns."""
        return [a for a in self.analyses if a.get("is_shuffled")]

    def get_obfuscated_binaries(self) -> List[Dict]:
        """Get list of binaries with obfuscated sections."""
        return [a for a in self.analyses if a.get("has_obfuscated_sections")]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_analyzed": len(self.analyses),
            "shuffled_binaries": len(self.get_shuffled_binaries()),
            "obfuscated_binaries": len(self.get_obfuscated_binaries()),
            "anomalies_found": sum(len(a.get("anomalies", [])) for a in self.analyses),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["COFFLayoutAnalyzer", "COFFSection", "COFFRelocation"]

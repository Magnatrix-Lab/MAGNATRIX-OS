
"""
driver_import_scanner_native.py
MAGNATRIX-OS — Driver Import Scanner

Inspired by DriverScope (diabloidyobane/DriverScope):
Scan Windows kernel drivers for dangerous imports that indicate
potential BYOVD (Bring Your Own Vulnerable Driver) exploitation paths.

Pure Python standard library.
"""

import struct
import re
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path


class ImportSeverity(Enum):
    INFO = auto()
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()


@dataclass
class ImportFinding:
    dll_name: str
    func_name: str
    severity: str
    category: str
    description: str
    offset: int = 0


class DriverImportScanner:
    """Scan drivers for dangerous imports indicating BYOVD potential."""

    # Dangerous imports mapped to their severity and description
    DANGEROUS_IMPORTS: Dict[str, Dict[str, Tuple[str, str]]] = {
        "ntoskrnl.exe": {
            "MmMapIoSpace": ("CRITICAL", "Maps physical memory - kernel read/write primitive"),
            "MmMapIoSpaceEx": ("CRITICAL", "Maps physical memory with extended flags"),
            "MmGetPhysicalAddress": ("HIGH", "Resolves physical addresses for DMA attacks"),
            "IoCreateDevice": ("MEDIUM", "Creates device objects - potential attack surface"),
            "IoCreateSymbolicLink": ("MEDIUM", "Creates symbolic links for user-mode access"),
            "ObRegisterCallbacks": ("HIGH", "Registers object callbacks - can be abused for rootkit"),
            "PsSetCreateProcessNotifyRoutine": ("HIGH", "Process creation monitoring - rootkit indicator"),
            "PsSetCreateThreadNotifyRoutine": ("HIGH", "Thread creation monitoring - rootkit indicator"),
            "PsSetLoadImageNotifyRoutine": ("HIGH", "Image load monitoring - rootkit indicator"),
            "KeInsertQueueApc": ("CRITICAL", "APC injection primitive"),
            "NtMapViewOfSection": ("HIGH", "Memory mapping - potential code injection"),
            "RtlFindExportedRoutineByName": ("CRITICAL", "Finds exported routines by name - EDR bypass"),
            "ZwAllocateVirtualMemory": ("HIGH", "Allocates virtual memory in target processes"),
            "ZwProtectVirtualMemory": ("CRITICAL", "Changes memory protection - RWX shellcode"),
            "ZwWriteVirtualMemory": ("CRITICAL", "Writes to remote process memory"),
            "ZwCreateThreadEx": ("CRITICAL", "Creates remote threads - injection primitive"),
        },
        "hal.dll": {
            "HalGetBusData": ("MEDIUM", "Hardware abstraction layer access"),
            "HalSetBusData": ("MEDIUM", "Hardware abstraction layer modification"),
        },
        "win32k.sys": {
            "NtUserSendInput": ("HIGH", "Synthetic input - potential privilege escalation"),
            "NtUserSetWindowsHookEx": ("HIGH", "Sets global hooks - keylogger rootkit"),
        },
    }

    def __init__(self):
        self.findings: List[ImportFinding] = []
        self.scanned_files: Set[str] = set()

    def scan_pe_imports(self, filepath: str) -> List[ImportFinding]:
        """Scan PE file for imports and match against dangerous list."""
        findings = []
        try:
            with open(filepath, "rb") as f:
                data = f.read()
            # Parse PE header
            imports = self._parse_pe_imports(data)
            for dll, funcs in imports.items():
                dll_lower = dll.lower()
                for func in funcs:
                    # Check against dangerous imports
                    for dangerous_dll, dangerous_funcs in self.DANGEROUS_IMPORTS.items():
                        if dangerous_dll in dll_lower:
                            if func in dangerous_funcs:
                                severity, desc = dangerous_funcs[func]
                                findings.append(ImportFinding(
                                    dll_name=dll, func_name=func, severity=severity,
                                    category="dangerous_import", description=desc,
                                ))
                    # Also check for suspicious patterns
                    if self._is_suspicious(func):
                        findings.append(ImportFinding(
                            dll_name=dll, func_name=func, severity="MEDIUM",
                            category="suspicious_pattern", description="Suspicious function name pattern",
                        ))
        except Exception:
            pass
        self.findings.extend(findings)
        self.scanned_files.add(filepath)
        return findings

    def _parse_pe_imports(self, data: bytes) -> Dict[str, List[str]]:
        """Parse PE imports from raw binary data."""
        imports = {}
        # Check DOS header
        if len(data) < 64 or data[:2] != b"MZ":
            return imports
        # Get PE header offset
        pe_offset = struct.unpack("<I", data[0x3C:0x40])[0]
        if len(data) < pe_offset + 24:
            return imports
        # Check PE signature
        if data[pe_offset:pe_offset+4] != b"PE\x00\x00":
            return imports
        # Get optional header info
        opt_header_offset = pe_offset + 24
        magic = struct.unpack("<H", data[opt_header_offset:opt_header_offset+2])[0]
        if magic == 0x10b:  # PE32
            data_dir_offset = opt_header_offset + 96
        elif magic == 0x20b:  # PE32+
            data_dir_offset = opt_header_offset + 112
        else:
            return imports
        # Import directory RVA
        import_dir_rva = struct.unpack("<I", data[data_dir_offset + 8 * 1:data_dir_offset + 8 * 1 + 4])[0]
        import_dir_size = struct.unpack("<I", data[data_dir_offset + 8 * 1 + 4:data_dir_offset + 8 * 1 + 8])[0]
        if import_dir_rva == 0 or import_dir_size == 0:
            return imports
        # Parse import directory entries (simplified - would need section mapping for real PE)
        # For now, do basic string extraction
        text = data.decode("latin-1", errors="ignore")
        # Extract DLL names
        for dll_match in re.finditer(r"([\w\-]+\.dll)\x00", text, re.IGNORECASE):
            dll_name = dll_match.group(1)
            if dll_name.lower() in ["ntoskrnl.exe", "hal.dll", "win32k.sys"] or "kernel" in dll_name.lower():
                imports.setdefault(dll_name, [])
        # Extract potential function names
        words = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]{3,50}", text))
        for dll in list(imports.keys()):
            for dangerous_dll, funcs in self.DANGEROUS_IMPORTS.items():
                if dangerous_dll in dll.lower():
                    for func in funcs:
                        if func.encode() in data:
                            imports.setdefault(dll, []).append(func)
        return imports

    def _is_suspicious(self, func_name: str) -> bool:
        """Check if a function name is suspicious."""
        suspicious_patterns = [
            r"hook", r"inject", r"map.*memory", r"write.*memory",
            r"protect.*memory", r"alloc.*memory", r"create.*thread",
            r"apc", r"callback", r"notify", r"register",
        ]
        return any(re.search(p, func_name, re.IGNORECASE) for p in suspicious_patterns)

    def get_stats(self) -> Dict[str, Any]:
        severity_counts = {}
        for f in self.findings:
            severity_counts[f.severity] = severity_counts.get(f.severity, 0) + 1
        return {
            "total_findings": len(self.findings),
            "files_scanned": len(self.scanned_files),
            "severity_breakdown": severity_counts,
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["DriverImportScanner", "ImportFinding", "ImportSeverity"]

"""
evasion_technique_library_native.py
MAGNATRIX-OS — Evasion Technique Library

Inspired by AbyssSec evasion and anti-detection research:
Library of evasion techniques with implementation guidance. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict


@dataclass
class EvasionTechnique:
    technique_id: str
    name: str
    description: str
    category: str
    mitre_id: str
    implementation: str
    detection_risk: str  # low, medium, high
    tags: List[str] = field(default_factory=list)


class EvasionTechniqueLibrary:
    """Library of evasion techniques with implementation guidance."""

    BUILT_IN_TECHNIQUES = {
        "sleep_obfuscation": {
            "name": "Sleep Obfuscation", "description": "Encrypt beacon memory during sleep to avoid memory scanners",
            "category": "memory", "mitre_id": "T1027.002", "detection_risk": "low",
            "implementation": "Encrypt memory before sleep, change permissions to NOACCESS, restore and decrypt on wake",
            "tags": ["memory", "encryption", "sleep"],
        },
        "indirect_syscalls": {
            "name": "Indirect Syscalls", "description": "Avoid ntdll.dll hooks by calling syscalls directly",
            "category": "execution", "mitre_id": "T1106", "detection_risk": "medium",
            "implementation": "Resolve syscall numbers dynamically, use direct syscall instructions instead of API calls",
            "tags": ["syscalls", "ntdll", "hook_bypass"],
        },
        "api_hashing": {
            "name": "API Hashing", "description": "Resolve APIs at runtime using hashes to avoid import table detection",
            "category": "execution", "mitre_id": "T1027.002", "detection_risk": "low",
            "implementation": "Hash API names, traverse PEB to find exports, match by hash instead of string",
            "tags": ["hashing", "peb", "imports"],
        },
        "return_address_spoofing": {
            "name": "Return Address Spoofing", "description": "Fake legitimate call stack to bypass stack-based detection",
            "category": "execution", "mitre_id": "T1027.002", "detection_risk": "medium",
            "implementation": "Spoof return addresses to appear as legitimate system calls",
            "tags": ["stack", "spoofing", "call_stack"],
        },
        "module_stomping": {
            "name": "Module Stomping", "description": "Overwrite legitimate DLL memory to appear as normal module",
            "category": "memory", "mitre_id": "T1055.012", "detection_risk": "high",
            "implementation": "Map a legitimate DLL, overwrite its .text section with malicious code",
            "tags": ["memory", "dll", "overwrite"],
        },
        "process_hollowing": {
            "name": "Process Hollowing", "description": "Create suspended process, unmap memory, write malicious code, resume",
            "category": "process", "mitre_id": "T1055.012", "detection_risk": "medium",
            "implementation": "CreateProcess suspended, NtUnmapViewOfSection, VirtualAllocEx, WriteProcessMemory, ResumeThread",
            "tags": ["process", "hollowing", "injection"],
        },
        "process_doppelganging": {
            "name": "Process Doppelganging", "description": "Abuse NTFS transactions to replace executable image without detection",
            "category": "process", "mitre_id": "T1055.013", "detection_risk": "low",
            "implementation": "CreateFileTransacted, WriteFile, CreateSectionEx, RollbackTransaction",
            "tags": ["ntfs", "transaction", "process"],
        },
        "apc_injection": {
            "name": "APC Injection", "description": "Queue malicious APC to thread for execution",
            "category": "process", "mitre_id": "T1055.004", "detection_risk": "medium",
            "implementation": "OpenThread, VirtualAllocEx, WriteProcessMemory, QueueUserAPC, NtAlertThread",
            "tags": ["apc", "thread", "injection"],
        },
    }

    def __init__(self, library_dir: str = "./evasion_library"):
        self.library_dir = Path(library_dir)
        self.library_dir.mkdir(exist_ok=True)
        self.techniques: Dict[str, EvasionTechnique] = {}
        self._load()

    def _load(self) -> None:
        file = self.library_dir / "techniques.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for tid, td in data.items():
                        self.techniques[tid] = EvasionTechnique(**td)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.library_dir / "techniques.json", "w", encoding="utf-8") as f:
            json.dump({tid: asdict(t) for tid, t in self.techniques.items()}, f, indent=2)

    def register(self, technique_id: str, name: str, description: str, category: str,
                 mitre_id: str, implementation: str, detection_risk: str,
                 tags: Optional[List[str]] = None) -> EvasionTechnique:
        tech = EvasionTechnique(
            technique_id=technique_id, name=name, description=description,
            category=category, mitre_id=mitre_id, implementation=implementation,
            detection_risk=detection_risk, tags=tags or [],
        )
        self.techniques[technique_id] = tech
        self._save()
        return tech

    def register_builtin(self, technique_id: str) -> Optional[EvasionTechnique]:
        if technique_id not in self.BUILT_IN_TECHNIQUES:
            return None
        info = self.BUILT_IN_TECHNIQUES[technique_id]
        return self.register(
            technique_id=technique_id, name=info["name"], description=info["description"],
            category=info["category"], mitre_id=info["mitre_id"],
            implementation=info["implementation"], detection_risk=info["detection_risk"],
            tags=info.get("tags", []),
        )

    def get_technique(self, technique_id: str) -> Optional[EvasionTechnique]:
        return self.techniques.get(technique_id)

    def list_by_category(self, category: str) -> List[EvasionTechnique]:
        return [t for t in self.techniques.values() if t.category == category]

    def list_by_risk(self, risk: str) -> List[EvasionTechnique]:
        return [t for t in self.techniques.values() if t.detection_risk == risk]

    def search(self, query: str) -> List[EvasionTechnique]:
        q = query.lower()
        return [t for t in self.techniques.values() if q in t.name.lower() or q in t.description.lower() or any(q in tag for tag in t.tags)]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.techniques)
        categories = {}
        for t in self.techniques.values():
            categories[t.category] = categories.get(t.category, 0) + 1
        return {"total": total, "categories": categories, "builtins": len(self.BUILT_IN_TECHNIQUES)}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["EvasionTechniqueLibrary", "EvasionTechnique"]
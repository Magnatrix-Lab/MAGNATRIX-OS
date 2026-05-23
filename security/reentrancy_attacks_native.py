#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MAGNATRIX-OS — Reentrancy Attacks Native Integration
═══════════════════════════════════════════════════════════════════════════════
AMATI-PELAJARI-TIRU dari pcaversaccio/reentrancy-attacks

Pola yang ditiru:
• Curated attack database — real-world reentrancy incidents dengan detail lengkap
• Attack taxonomy — kategorisasi: single-function, cross-function, cross-contract, read-only
• Loss tracking — dokumentasi financial impact per incident
• Timeline/chronology — historical record dari 2016–present
• Root cause analysis — mekanisme serangan step-by-step
• Prevention patterns — checks-effects-interactions, ReentrancyGuard, mutex locks
• Vulnerable vs patched code — before/after comparison
• Cross-reference dengan SCVS (smart_contract_vulnerability_scanner.py)
• Pattern detection engine — identify reentrancy-prone code patterns
• Automated mitigation generator — generate fix recommendations

Layer: Security (9) — Reentrancy Attack Knowledge Base & Defense Engine
Versi: Phase 5 — Reentrancy Attacks Native Defense System
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Callable


# ─────────────────────────────────────────────────────────────────────────────
# 0. UTILITAS DASAR
# ─────────────────────────────────────────────────────────────────────────────


def _now_iso() -> str:
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _hash_id(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()[:12]


# ─────────────────────────────────────────────────────────────────────────────
# 1. ATTACK TAXONOMY — Klasifikasi Reentrancy
# ─────────────────────────────────────────────────────────────────────────────


class ReentrancyType(str, Enum):
    """Tipe reentrancy attack berdasarkan attack surface."""
    SINGLE_FUNCTION = "single-function"
    CROSS_FUNCTION = "cross-function"
    CROSS_CONTRACT = "cross-contract"
    READ_ONLY = "read-only"
    DELEGATECALL = "delegatecall-based"
    FLASH_LOAN = "flash-loan-assisted"
    ERC777 = "erc777-hooks"
    ERC721 = "erc721-safe-transfer"
    ETH_TRANSFER = "eth-transfer"
    TOKEN_TRANSFER = "token-transfer"


class AttackSeverity(str, Enum):
    CRITICAL = "Critical"      # > $10M loss / complete drainage
    HIGH = "High"              # $1M–$10M / significant loss
    MEDIUM = "Medium"          # $100K–$1M / moderate loss
    LOW = "Low"                # <$100K / minor loss
    INFORMATIONAL = "Info"     # No loss / near-miss


# ─────────────────────────────────────────────────────────────────────────────
# 2. ATTACK INCIDENT — Single Record
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class AttackIncident:
    """
    Satu incident reentrancy attack — meniru format pcaversaccio database.
    """
    id: str
    name: str
    protocol: str
    date: str  # YYYY-MM-DD
    chain: str  # Ethereum, BSC, Polygon, etc.
    loss_usd: float
    loss_eth: Optional[float] = None
    loss_native: Optional[float] = None
    reentrancy_type: ReentrancyType = ReentrancyType.SINGLE_FUNCTION
    severity: AttackSeverity = AttackSeverity.HIGH
    attack_vector: str = ""  # Deskripsi cara serangan
    root_cause: str = ""     # Kenapa vulnerable
    vulnerable_function: str = ""
    attacker_address: Optional[str] = None
    transaction_hash: Optional[str] = None
    block_number: Optional[int] = None
    patched: bool = False
    patch_commit: Optional[str] = None
    post_mortem_url: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    code_snippet_vulnerable: str = ""
    code_snippet_patched: str = ""
    related_cves: List[str] = field(default_factory=list)
    related_swcs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "protocol": self.protocol,
            "date": self.date,
            "chain": self.chain,
            "loss_usd": self.loss_usd,
            "loss_eth": self.loss_eth,
            "reentrancy_type": self.reentrancy_type.value,
            "severity": self.severity.value,
            "attack_vector": self.attack_vector,
            "root_cause": self.root_cause,
            "vulnerable_function": self.vulnerable_function,
            "attacker_address": self.attacker_address,
            "transaction_hash": self.transaction_hash,
            "block_number": self.block_number,
            "patched": self.patched,
            "patch_commit": self.patch_commit,
            "post_mortem_url": self.post_mortem_url,
            "tags": self.tags,
            "related_swcs": self.related_swcs,
        }


# ─────────────────────────────────────────────────────────────────────────────
# 3. CURATED ATTACK DATABASE — Historical Records
# ─────────────────────────────────────────────────────────────────────────────


class ReentrancyAttackDatabase:
    """
    Database curated dari real-world reentrancy attacks.
    Data di-source dari pcaversaccio/reentrancy-attacks dan security research.
    """

    # Pre-seeded incidents (subset dari real database)
    _INCIDENTS: List[Dict[str, Any]] = [
        {
            "name": "The DAO",
            "protocol": "The DAO",
            "date": "2016-06-17",
            "chain": "Ethereum",
            "loss_usd": 60_000_000,
            "loss_eth": 3_600_000,
            "reentrancy_type": "single-function",
            "severity": "Critical",
            "attack_vector": "Recursive call ke splitDAO function sebelum balance update",
            "root_cause": "External call (call.value) sebelum state update (balances[msg.sender] = 0)",
            "vulnerable_function": "splitDAO",
            "attacker_address": "0xF35...",
            "transaction_hash": "0x0ec3...",
            "block_number": 1718497,
            "patched": False,
            "tags": ["dao", "ethereum-classic-fork", "recursive"],
            "related_swcs": ["SWC-107"],
        },
        {
            "name": "Uniswap/Lendf.Me",
            "protocol": "Lendf.Me",
            "date": "2020-04-19",
            "chain": "Ethereum",
            "loss_usd": 25_000_000,
            "reentrancy_type": "cross-function",
            "severity": "Critical",
            "attack_vector": "ERC777 token hook memungkinkan reentrancy ke fungsi berbeda",
            "root_cause": "ERC777 tokensReceived hook memungkinkan cross-function state manipulation",
            "vulnerable_function": "withdraw, supply",
            "attacker_address": "0xa9bf...",
            "transaction_hash": "0xe72c...",
            "block_number": 9890209,
            "patched": True,
            "tags": ["erc777", "imbtc", "cross-function"],
            "related_swcs": ["SWC-107", "SWC-112"],
        },
        {
            "name": "Cream Finance",
            "protocol": "Cream Finance",
            "date": "2021-10-27",
            "chain": "Ethereum",
            "loss_usd": 130_000_000,
            "reentrancy_type": "cross-function",
            "severity": "Critical",
            "attack_vector": "Flash loan + AMP token reentrancy untuk manipulate collateral factor",
            "root_cause": "AMP token (ERC777-like) callback memungkinkan reentrancy ke borrow",
            "vulnerable_function": "borrow, _addLendingMarket",
            "attacker_address": "0x_cead...",
            "transaction_hash": "0x0fc2...",
            "block_number": 13474869,
            "patched": True,
            "tags": ["amp", "flash-loan", "cream", "cross-function"],
            "related_swcs": ["SWC-107"],
        },
        {
            "name": "Saddle Finance",
            "protocol": "Saddle Finance",
            "date": "2022-04-30",
            "chain": "Ethereum",
            "loss_usd": 11_000_000,
            "reentrancy_type": "single-function",
            "severity": "High",
            "attack_vector": "Reentrancy via swap function untuk double-spend sUSD tokens",
            "root_cause": "sUSD transfer hook (ERC777) dipanggil sebelum balance update",
            "vulnerable_function": "swap",
            "attacker_address": "0x5d5e...",
            "patched": True,
            "tags": ["susd", "saddle", "erc777"],
            "related_swcs": ["SWC-107"],
        },
        {
            "name": "Omni Protocol",
            "protocol": "Omni",
            "date": "2022-07-10",
            "chain": "Ethereum",
            "loss_usd": 1_400_000,
            "reentrancy_type": "erc721-safe-transfer",
            "severity": "High",
            "attack_vector": "ERC721 safeTransferFrom callback ke attacker contract",
            "root_cause": "onERC721Received hook memungkinkan reentrancy ke borrow function",
            "vulnerable_function": "borrow, onERC721Received",
            "attacker_address": "0x8dae...",
            "patched": True,
            "tags": ["erc721", "nft", "safe-transfer"],
            "related_swcs": ["SWC-107"],
        },
        {
            "name": "Curve/JPEG'd",
            "protocol": "JPEG'd",
            "date": "2023-07-30",
            "chain": "Ethereum",
            "loss_usd": 11_600_000,
            "reentrancy_type": "read-only",
            "severity": "High",
            "attack_vector": "Read-only reentrancy manipulation price oracle via Curve pool",
            "root_cause": "Curve pool get_pools callback memungkinkan price oracle manipulation",
            "vulnerable_function": "remove_liquidity, get_pools",
            "attacker_address": "0x6ec0...",
            "patched": True,
            "tags": ["curve", "oracle", "read-only", "price-manipulation"],
            "related_swcs": ["SWC-107", "SWC-116"],
        },
        {
            "name": "Balancer",
            "protocol": "Balancer",
            "date": "2020-06-29",
            "chain": "Ethereum",
            "loss_usd": 500_000,
            "reentrancy_type": "cross-function",
            "severity": "Medium",
            "attack_vector": "ERC777 token hook memungkinkan reentrancy ke fungsi internal",
            "root_cause": "STA token deflationary mechanism + ERC777 hook = cross-function reentrancy",
            "vulnerable_function": "gulp, swap",
            "attacker_address": "0x5d6e...",
            "patched": True,
            "tags": ["balancer", "sta", "deflationary", "erc777"],
            "related_swcs": ["SWC-107"],
        },
        {
            "name": "Siren Protocol",
            "protocol": "Siren",
            "date": "2021-09-07",
            "chain": "Ethereum",
            "loss_usd": 3_500_000,
            "reentrancy_type": "cross-contract",
            "severity": "High",
            "attack_vector": "AmmToken callback ke attacker contract → reenter ke MinterAmm",
            "root_cause": "AmmToken mint callback memungkinkan cross-contract state manipulation",
            "vulnerable_function": "mint",
            "attacker_address": "0x3380...",
            "patched": True,
            "tags": ["siren", "amm", "cross-contract"],
            "related_swcs": ["SWC-107"],
        },
        {
            "name": "Furucombo",
            "protocol": "Furucombo",
            "date": "2021-02-27",
            "chain": "Ethereum",
            "loss_usd": 15_000_000,
            "reentrancy_type": "delegatecall-based",
            "severity": "High",
            "attack_vector": "Delegatecall ke attacker contract untuk manipulate approvals",
            "root_cause": "AaveV2 proxy delegatecall memungkinkan arbitrary code execution",
            "vulnerable_function": "batchExec",
            "attacker_address": "0x5aa0...",
            "patched": True,
            "tags": ["furucombo", "delegatecall", "aave"],
            "related_swcs": ["SWC-107", "SWC-112"],
        },
        {
            "name": "Hundred Finance",
            "protocol": "Hundred Finance",
            "date": "2023-04-15",
            "chain": "Optimism",
            "loss_usd": 7_400_000,
            "reentrancy_type": "cross-function",
            "severity": "High",
            "attack_vector": "ERC777 hToken callback → reenter ke fungsi borrow berbeda",
            "root_cause": "hToken mint callback memungkinkan borrow sebelum collateral update",
            "vulnerable_function": "borrow, mint",
            "attacker_address": "0x1c63...",
            "patched": True,
            "tags": ["hundred", "optimism", "htoken", "erc777"],
            "related_swcs": ["SWC-107"],
        },
        {
            "name": "dForce",
            "protocol": "dForce",
            "date": "2020-04-19",
            "chain": "Ethereum",
            "loss_usd": 25_000_000,
            "reentrancy_type": "cross-function",
            "severity": "Critical",
            "attack_vector": "ERC777 imBTC callback untuk manipulate collateral & borrow",
            "root_cause": "Sama dengan Lendf.Me — shared codebase vulnerability",
            "vulnerable_function": "supply, withdraw",
            "attacker_address": "0x_abc...",
            "patched": True,
            "tags": ["dforce", "imbtc", "erc777", "lendfme-fork"],
            "related_swcs": ["SWC-107"],
        },
        {
            "name": "Vyper Compiler",
            "protocol": "Curve Pools",
            "date": "2023-07-30",
            "chain": "Ethereum",
            "loss_usd": 70_000_000,
            "reentrancy_type": "read-only",
            "severity": "Critical",
            "attack_vector": "Vyper reentrancy lock bug (0.2.15, 0.3.0, 0.3.1) → read-only reentrancy",
            "root_cause": "Vyper compiler bug: reentrancy lock tidak properly implemented",
            "vulnerable_function": "remove_liquidity",
            "attacker_address": "0x6ec0...",
            "patched": True,
            "tags": ["vyper", "compiler-bug", "curve", "read-only", "reentrancy-lock"],
            "related_swcs": ["SWC-107"],
        },
    ]

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or Path.home() / ".magnatrix" / "reentrancy-db.json"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.incidents: Dict[str, AttackIncident] = {}
        self._seed_database()
        self._load_database()

    def _seed_database(self) -> None:
        """Seed dengan curated incidents."""
        for data in self._INCIDENTS:
            incident_id = _hash_id(data["name"] + data["date"])
            self.incidents[incident_id] = AttackIncident(
                id=incident_id,
                name=data["name"],
                protocol=data["protocol"],
                date=data["date"],
                chain=data["chain"],
                loss_usd=data["loss_usd"],
                loss_eth=data.get("loss_eth"),
                reentrancy_type=ReentrancyType(data.get("reentrancy_type", "single-function")),
                severity=AttackSeverity(data.get("severity", "High")),
                attack_vector=data.get("attack_vector", ""),
                root_cause=data.get("root_cause", ""),
                vulnerable_function=data.get("vulnerable_function", ""),
                attacker_address=data.get("attacker_address"),
                transaction_hash=data.get("transaction_hash"),
                block_number=data.get("block_number"),
                patched=data.get("patched", False),
                tags=data.get("tags", []),
                related_swcs=data.get("related_swcs", []),
            )

    def _load_database(self) -> None:
        if self.db_path.exists():
            try:
                data = json.loads(self.db_path.read_text())
                for item in data:
                    aid = item["id"]
                    self.incidents[aid] = AttackIncident(
                        id=aid,
                        name=item["name"],
                        protocol=item["protocol"],
                        date=item["date"],
                        chain=item["chain"],
                        loss_usd=item["loss_usd"],
                        reentrancy_type=ReentrancyType(item.get("reentrancy_type", "single-function")),
                        severity=AttackSeverity(item.get("severity", "High")),
                        attack_vector=item.get("attack_vector", ""),
                        root_cause=item.get("root_cause", ""),
                        vulnerable_function=item.get("vulnerable_function", ""),
                        tags=item.get("tags", []),
                        related_swcs=item.get("related_swcs", []),
                    )
            except Exception:
                pass

    def _save_database(self) -> None:
        data = [i.to_dict() for i in self.incidents.values()]
        self.db_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def add_incident(self, incident: AttackIncident) -> None:
        self.incidents[incident.id] = incident
        self._save_database()

    def get_incident(self, incident_id: str) -> Optional[AttackIncident]:
        return self.incidents.get(incident_id)

    def search(self, query: str, chain_filter: Optional[str] = None,
               type_filter: Optional[ReentrancyType] = None,
               severity_filter: Optional[AttackSeverity] = None) -> List[AttackIncident]:
        """Search incidents dengan multiple filter."""
        results = []
        q = query.lower()
        for incident in self.incidents.values():
            if chain_filter and incident.chain != chain_filter:
                continue
            if type_filter and incident.reentrancy_type != type_filter:
                continue
            if severity_filter and incident.severity != severity_filter:
                continue
            text = f"{incident.name} {incident.protocol} {incident.attack_vector} {incident.root_cause} {' '.join(incident.tags)}".lower()
            if q in text:
                results.append(incident)
        return sorted(results, key=lambda x: x.loss_usd, reverse=True)

    def get_stats(self) -> Dict[str, Any]:
        total_loss = sum(i.loss_usd for i in self.incidents.values())
        by_type: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}
        by_chain: Dict[str, int] = {}
        by_year: Dict[str, int] = {}

        for i in self.incidents.values():
            by_type[i.reentrancy_type.value] = by_type.get(i.reentrancy_type.value, 0) + 1
            by_severity[i.severity.value] = by_severity.get(i.severity.value, 0) + 1
            by_chain[i.chain] = by_chain.get(i.chain, 0) + 1
            year = i.date[:4]
            by_year[year] = by_year.get(year, 0) + 1

        return {
            "total_incidents": len(self.incidents),
            "total_loss_usd": total_loss,
            "by_type": by_type,
            "by_severity": by_severity,
            "by_chain": by_chain,
            "by_year": by_year,
            "largest_single_loss": max((i.loss_usd for i in self.incidents.values()), default=0),
        }

    def get_timeline(self) -> List[Dict[str, Any]]:
        """Return chronological timeline."""
        sorted_incidents = sorted(self.incidents.values(), key=lambda x: x.date)
        return [
            {
                "date": i.date,
                "name": i.name,
                "protocol": i.protocol,
                "loss_usd": i.loss_usd,
                "type": i.reentrancy_type.value,
                "severity": i.severity.value,
            }
            for i in sorted_incidents
        ]


# ─────────────────────────────────────────────────────────────────────────────
# 4. PATTERN DETECTION ENGINE — Identify Reentrancy-Prone Code
# ─────────────────────────────────────────────────────────────────────────────


class ReentrancyPatternDetector:
    """
    Detector untuk identify code patterns yang vulnerable ke reentrancy.
    Meniru analysis methodology dari pcaversaccio dan security community.
    """

    # Dangerous patterns yang menunjukkan potential reentrancy
    PATTERNS = {
        "external_call_before_state_update": {
            "regex": r'(call\.value|\.call\{.*value.*\}|\.transfer\(|\.send\(|token\.transfer\(|token\.transferFrom\()',
            "description": "External call detected — check if state update follows",
            "severity": "High",
        },
        "missing_reentrancy_guard": {
            "regex": r'function\s+(withdraw|claim|refund|distribute|emergencyWithdraw)\s*\([^)]*\)\s*(?!.*nonReentrant)',
            "description": "Sensitive function without ReentrancyGuard modifier",
            "severity": "Medium",
        },
        "erc777_callback_risk": {
            "regex": r'(ERC777|tokensReceived|IERC777Recipient)',
            "description": "ERC777 token usage detected — callback reentrancy risk",
            "severity": "High",
        },
        "erc721_safe_transfer_risk": {
            "regex": r'(safeTransferFrom|onERC721Received|IERC721Receiver)',
            "description": "ERC721 safeTransferFrom detected — callback reentrancy risk",
            "severity": "Medium",
        },
        "unchecked_low_level_call": {
            "regex": r'\.call\{value:[^}]*\}\([^)]*\)(?!\s*\;)',
            "description": "Low-level call without proper error handling",
            "severity": "Medium",
        },
        "state_update_after_external": {
            "regex": r'(call|transfer|send)\{[^}]*\}[^;]*;\s*[^/]*(?:balance|balances|_balances|totalSupply)',
            "description": "State update after external call — reentrancy pattern",
            "severity": "Critical",
        },
    }

    def __init__(self) -> None:
        self.findings: List[Dict[str, Any]] = []

    def analyze_source(self, source_code: str, contract_name: str = "") -> List[Dict[str, Any]]:
        """Analyze Solidity source code untuk reentrancy patterns."""
        findings = []
        for pattern_name, pattern_info in self.PATTERNS.items():
            matches = list(re.finditer(pattern_info["regex"], source_code, re.IGNORECASE | re.DOTALL))
            for match in matches:
                # Extract context (lines around match)
                start = max(0, match.start() - 100)
                end = min(len(source_code), match.end() + 100)
                context = source_code[start:end]

                findings.append({
                    "pattern": pattern_name,
                    "severity": pattern_info["severity"],
                    "description": pattern_info["description"],
                    "match": match.group(0),
                    "position": match.start(),
                    "context": context[:200],
                    "contract": contract_name,
                })

        self.findings = findings
        return findings

    def analyze_bytecode(self, hex_bytecode: str) -> List[Dict[str, Any]]:
        """Analyze EVM bytecode untuk reentrancy indicators."""
        # Look for CALL opcode followed by SSTORE pattern
        from security.bytepeep_native import EVMBytecodeParser, Opcode

        instructions = EVMBytecodeParser.parse(hex_bytecode)
        findings = []

        for i in range(len(instructions) - 2):
            # Pattern: CALL → ... → SSTORE (without SLOAD in between = potential reentrancy)
            if instructions[i].opcode in (Opcode.CALL, Opcode.DELEGATECALL, Opcode.CALLCODE):
                # Look ahead untuk SSTORE tanpa SLOAD
                found_sstore = False
                found_sload = False
                for j in range(i + 1, min(i + 20, len(instructions))):
                    if instructions[j].opcode == Opcode.SSTORE:
                        found_sstore = True
                        break
                    if instructions[j].opcode == Opcode.SLOAD:
                        found_sload = True
                if found_sstore and not found_sload:
                    findings.append({
                        "pattern": "call_without_sload_before_sstore",
                        "severity": "High",
                        "description": "External call without prior storage read before storage write",
                        "pc": instructions[i].pc,
                        "contract": "",
                    })

        return findings

    def get_summary(self) -> Dict[str, Any]:
        by_severity: Dict[str, int] = {}
        by_pattern: Dict[str, int] = {}
        for f in self.findings:
            sev = f["severity"]
            by_severity[sev] = by_severity.get(sev, 0) + 1
            pat = f["pattern"]
            by_pattern[pat] = by_pattern.get(pat, 0) + 1

        return {
            "total_findings": len(self.findings),
            "by_severity": by_severity,
            "by_pattern": by_pattern,
        }


# ─────────────────────────────────────────────────────────────────────────────
# 5. MITIGATION GENERATOR — Auto-Generate Fixes
# ─────────────────────────────────────────────────────────────────────────────


class ReentrancyMitigationGenerator:
    """
    Generator untuk reentrancy mitigation code.
    Meniru best practices dari industry: OpenZeppelin, ConsenSys, etc.
    """

    @staticmethod
    def generate_reentrancy_guard() -> str:
        """Generate ReentrancyGuard contract."""
        return '''// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

abstract contract ReentrancyGuard {
    uint256 private constant _NOT_ENTERED = 1;
    uint256 private constant _ENTERED = 2;
    uint256 private _status;

    constructor() {
        _status = _NOT_ENTERED;
    }

    modifier nonReentrant() {
        require(_status != _ENTERED, "ReentrancyGuard: reentrant call");
        _status = _ENTERED;
        _;
        _status = _NOT_ENTERED;
    }
}
'''

    @staticmethod
    def generate_checks_effects_interactions_pattern(function_name: str,
                                                      state_variables: List[str],
                                                      external_call: str) -> str:
        """Generate refactored function menggunakan checks-effects-interactions pattern."""
        checks = "// 1. CHECKS\n" + "\n".join(f"    require({var} >= amount, \"Insufficient {var}\");" for var in state_variables)
        effects = "\n    // 2. EFFECTS\n" + "\n".join(f"    {var} -= amount;" for var in state_variables)
        interactions = f"\n    // 3. INTERACTIONS (external call)\n    {external_call}"

        return f'''function {function_name}(uint256 amount) external nonReentrant {{
{checks}
{effects}
{interactions}
}}
'''

    @staticmethod
    def generate_pull_over_push_pattern(mapping_name: str = "balances") -> str:
        """Generate pull-over-push payment pattern."""
        return f'''// PULL OVER PUSH PATTERN
// Users withdraw funds themselves rather than contract pushing funds

mapping(address => uint256) public {mapping_name};

function withdraw() external nonReentrant {{
    uint256 amount = {mapping_name}[msg.sender];
    require(amount > 0, "No funds to withdraw");
    
    // Effects FIRST
    {mapping_name}[msg.sender] = 0;
    
    // Interaction LAST
    (bool success, ) = msg.sender.call{{value: amount}}("");
    require(success, "Transfer failed");
}}
'''

    @staticmethod
    def generate_erc777_safe_wrapper() -> str:
        """Generate safe wrapper untuk ERC777 interactions."""
        return '''// ERC777 SAFE INTERACTION WRAPPER
// Use send/receive hooks carefully

import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

contract ERC777SafeWrapper is ReentrancyGuard {
    mapping(address => uint256) public deposited;
    
    function safeDeposit(uint256 amount) external nonReentrant {
        // Update state BEFORE external token transfer
        deposited[msg.sender] += amount;
        
        // External call AFTER state update
        token.operatorSend(msg.sender, address(this), amount, "", "");
    }
    
    function safeWithdraw(uint256 amount) external nonReentrant {
        require(deposited[msg.sender] >= amount, "Insufficient balance");
        
        // Update state BEFORE external call
        deposited[msg.sender] -= amount;
        
        // External call AFTER state update
        token.send(msg.sender, amount, "");
    }
}
'''

    @staticmethod
    def generate_mitigation_for_incident(incident: AttackIncident) -> str:
        """Generate targeted mitigation untuk specific incident type."""
        mitigations = {
            ReentrancyType.SINGLE_FUNCTION: "Use ReentrancyGuard + checks-effects-interactions pattern",
            ReentrancyType.CROSS_FUNCTION: "Use ReentrancyGuard + mutex lock across all state-changing functions",
            ReentrancyType.CROSS_CONTRACT: "Use ReentrancyGuard + validate all external contract callbacks",
            ReentrancyType.READ_ONLY: "Use ReentrancyGuard + oracle freshness checks + TWAP",
            ReentrancyType.ERC777: "Use ReentrancyGuard + update state BEFORE token transfer",
            ReentrancyType.ERC721: "Use ReentrancyGuard + transfer instead of safeTransfer where possible",
            ReentrancyType.DELEGATECALL: "Validate delegatecall target + immutable target addresses",
        }

        base = mitigations.get(incident.reentrancy_type, "Use ReentrancyGuard")
        return f'''
// MITIGATION FOR: {incident.name} ({incident.protocol})
// Attack Type: {incident.reentrancy_type.value}
// {base}

{ReentrancyMitigationGenerator.generate_reentrancy_guard()}
'''


# ─────────────────────────────────────────────────────────────────────────────
# 6. SCVS INTEGRATION BRIDGE
# ─────────────────────────────────────────────────────────────────────────────


class SCVSReentrancyBridge:
    """
    Bridge untuk mengintegrasikan reentrancy database dengan SCVS scanner.
    • Cross-reference incidents dengan SWC IDs
    • Convert attack patterns ke SCVS vulnerability format
    • Enrich SCVS findings dengan historical context
    """

    def __init__(self, db: ReentrancyAttackDatabase) -> None:
        self.db = db

    def get_historical_context(self, swc_id: str) -> List[AttackIncident]:
        """Get historical incidents dengan SWC ID yang sama."""
        results = []
        for incident in self.db.incidents.values():
            if swc_id in incident.related_swcs:
                results.append(incident)
        return results

    def enrich_finding(self, scvs_finding: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich SCVS finding dengan historical reentrancy context."""
        swc_ids = scvs_finding.get("related_swcs", [])
        historical = []
        for swc in swc_ids:
            if swc == "SWC-107":  # Reentrancy
                incidents = self.get_historical_context(swc)
                historical.extend(incidents)

        total_loss = sum(i.loss_usd for i in historical)
        return {
            **scvs_finding,
            "historical_incidents": len(historical),
            "historical_total_loss": total_loss,
            "similar_attacks": [
                {"name": i.name, "protocol": i.protocol, "loss": i.loss_usd, "date": i.date}
                for i in sorted(historical, key=lambda x: x.loss_usd, reverse=True)[:5]
            ],
        }

    def generate_prevention_report(self) -> Dict[str, Any]:
        """Generate prevention-focused report berdasarkan database."""
        stats = self.db.get_stats()
        return {
            "total_historical_loss": stats["total_loss_usd"],
            "most_common_type": max(stats["by_type"], key=stats["by_type"].get),
            "most_affected_chain": max(stats["by_chain"], key=stats["by_chain"].get),
            "prevention_checklist": [
                "Use ReentrancyGuard on all external-facing functions",
                "Follow checks-effects-interactions pattern",
                "Use pull-over-push for payments",
                "Be cautious with ERC777/ERC721 callbacks",
                "Validate oracle freshness for price-dependent operations",
                "Avoid delegatecall to user-controlled addresses",
            ],
        }


# ─────────────────────────────────────────────────────────────────────────────
# 7. UNIFIED REENTRANCY DEFENSE ENGINE — Entry Point
# ─────────────────────────────────────────────────────────────────────────────


class ReentrancyDefenseEngine:
    """
    Unified defense engine untuk reentrancy attacks.
    Entry point bagi MAGNATRIX security layer.
    """

    def __init__(self) -> None:
        self.database = ReentrancyAttackDatabase()
        self.detector = ReentrancyPatternDetector()
        self.mitigation = ReentrancyMitigationGenerator()
        self.scvs_bridge = SCVSReentrancyBridge(self.database)

    # ── Database Queries ──────────────────────────────────────────────────

    def search_incidents(self, query: str, **filters) -> List[AttackIncident]:
        return self.database.search(query, **filters)

    def get_incident_stats(self) -> Dict[str, Any]:
        return self.database.get_stats()

    def get_timeline(self) -> List[Dict[str, Any]]:
        return self.database.get_timeline()

    # ── Pattern Detection ─────────────────────────────────────────────────

    def scan_source_code(self, solidity_code: str, contract_name: str = "") -> List[Dict[str, Any]]:
        return self.detector.analyze_source(solidity_code, contract_name)

    def scan_bytecode(self, hex_bytecode: str) -> List[Dict[str, Any]]:
        return self.detector.analyze_bytecode(hex_bytecode)

    # ── Mitigation ─────────────────────────────────────────────────────────

    def generate_guard(self) -> str:
        return self.mitigation.generate_reentrancy_guard()

    def generate_fix(self, incident_id: str) -> str:
        incident = self.database.get_incident(incident_id)
        if not incident:
            return ""
        return self.mitigation.generate_mitigation_for_incident(incident)

    def generate_cei_pattern(self, function: str, state_vars: List[str], external: str) -> str:
        return self.mitigation.generate_checks_effects_interactions_pattern(
            function, state_vars, external
        )

    # ── SCVS Integration ──────────────────────────────────────────────────

    def enrich_scvs_finding(self, finding: Dict[str, Any]) -> Dict[str, Any]:
        return self.scvs_bridge.enrich_finding(finding)

    def get_prevention_report(self) -> Dict[str, Any]:
        return self.scvs_bridge.generate_prevention_report()

    # ── Full Analysis ─────────────────────────────────────────────────────

    def analyze_contract(self, source_code: str, contract_name: str = "") -> Dict[str, Any]:
        """Full reentrancy analysis untuk satu contract."""
        findings = self.scan_source_code(source_code, contract_name)
        summary = self.detector.get_summary()
        prevention = self.get_prevention_report()

        # Generate targeted mitigation
        mitigations = []
        if findings:
            if any(f["pattern"] == "external_call_before_state_update" for f in findings):
                mitigations.append(self.generate_cei_pattern(
                    "withdraw", ["balances[msg.sender]"],
                    "(bool ok, ) = msg.sender.call{value: amount}(\"\");"
                ))
            if any(f["pattern"] == "missing_reentrancy_guard" for f in findings):
                mitigations.append(self.generate_guard())

        return {
            "contract": contract_name,
            "findings": findings,
            "summary": summary,
            "historical_context": prevention,
            "recommended_mitigations": mitigations,
            "risk_level": "High" if summary.get("by_severity", {}).get("Critical", 0) > 0 else
                         "Medium" if summary.get("by_severity", {}).get("High", 0) > 0 else "Low",
        }


def main():
    import sys
    print("═══════════════════════════════════════════════════════════════")
    print("  MAGNATRIX-OS — Reentrancy Attack Defense Engine")
    print("  AMATI-PELAJARI-TIRU dari pcaversaccio/reentrancy-attacks")
    print("═══════════════════════════════════════════════════════════════")
    print()

    engine = ReentrancyDefenseEngine()

    # Demo 1: Database stats
    print("[1] Historical Attack Database:")
    stats = engine.get_incident_stats()
    print(f"  Total Incidents: {stats['total_incidents']}")
    print(f"  Total Loss: ${stats['total_loss_usd']:,.0f}")
    print(f"  Largest Single Loss: ${stats['largest_single_loss']:,.0f}")
    print(f"  By Type: {stats['by_type']}")
    print(f"  By Severity: {stats['by_severity']}")
    print()

    # Demo 2: Search
    print("[2] Search 'ERC777':")
    results = engine.search_incidents("erc777")
    for r in results[:3]:
        print(f"  • {r.name} ({r.protocol}) — ${r.loss_usd:,.0f} — {r.date}")
    print()

    # Demo 3: Timeline
    print("[3] Timeline (first 3):")
    timeline = engine.get_timeline()
    for t in timeline[:3]:
        print(f"  • {t['date']}: {t['name']} — ${t['loss_usd']:,.0f}")
    print()

    # Demo 4: Source code scan
    print("[4] Source Code Analysis:")
    vulnerable_code = '''
contract Vulnerable {
    mapping(address => uint256) public balances;
    
    function withdraw() external {
        uint256 amount = balances[msg.sender];
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok);
        balances[msg.sender] = 0;
    }
    
    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }
}
'''
    findings = engine.scan_source_code(vulnerable_code, "Vulnerable")
    print(f"  Findings: {len(findings)}")
    for f in findings:
        print(f"    [{f['severity']}] {f['pattern']}: {f['description']}")
    print()

    # Demo 5: Generate mitigation
    print("[5] Generated Mitigation:")
    fix = engine.generate_cei_pattern(
        "withdraw", ["balances[msg.sender]"],
        "(bool ok, ) = msg.sender.call{value: amount}(\"\");"
    )
    print(fix[:300] + "...")
    print()

    # Demo 6: Full contract analysis
    print("[6] Full Analysis Report:")
    report = engine.analyze_contract(vulnerable_code, "Vulnerable")
    print(f"  Risk Level: {report['risk_level']}")
    print(f"  Total Findings: {report['summary']['total_findings']}")
    print(f"  Recommended Mitigations: {len(report['recommended_mitigations'])}")
    print()

    # Demo 7: Prevention report
    print("[7] Prevention Report:")
    prevention = engine.get_prevention_report()
    print(f"  Historical Loss: ${prevention['total_historical_loss']:,.0f}")
    print(f"  Most Common Type: {prevention['most_common_type']}")
    print(f"  Checklist Items: {len(prevention['prevention_checklist'])}")
    for item in prevention['prevention_checklist']:
        print(f"    • {item}")
    print()
    print("Done.")


if __name__ == "__main__":
    main()

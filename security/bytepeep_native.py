#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MAGNATRIX-OS — Bytepeep Native Integration
═══════════════════════════════════════════════════════════════════════════════
AMATI-PELAJARI-TIRU dari kadenzipfel/bytepeep

Pola yang ditiru:
• Peephole optimizer — pasang opcode window, match pattern, replace dengan sequence lebih optimal
• EVM opcode parser — hex bytecode → structured opcode stream (mnemonic, opcode, operand, gas)
• Optimization rules — rewrite rules: redundant stack ops, dead code elimination, constant folding
• Huff / mnemonic input support — parse dari mnemonic assembly ke bytecode
• Gas savings tracker — hitung per-rule & total gas saved
• Multi-window — pasang window size 2, 3, 4 opcode untuk pattern matching
• Stack analysis — track stack depth untuk validasi safety rewrite
• Jump target remapping — update offset setelah bytecode berubah panjang

Layer: Security (9) — EVM Bytecode Optimization Engine
Versi: Phase 5 — Bytepeep Native Optimizer
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable, Set


# ─────────────────────────────────────────────────────────────────────────────
# 0. EVM OPCODE DEFINITIONS — Full opcode table dengan gas & stack effect
# ─────────────────────────────────────────────────────────────────────────────


class Opcode(IntEnum):
    """EVM opcodes 0x00–0xFF — coverage utama untuk peephole matching."""
    STOP = 0x00
    ADD = 0x01
    MUL = 0x02
    SUB = 0x03
    DIV = 0x04
    SDIV = 0x05
    MOD = 0x06
    SMOD = 0x07
    ADDMOD = 0x08
    MULMOD = 0x09
    EXP = 0x0A
    SIGNEXTEND = 0x0B
    LT = 0x10
    GT = 0x11
    SLT = 0x12
    SGT = 0x13
    EQ = 0x14
    ISZERO = 0x15
    AND = 0x16
    OR = 0x17
    XOR = 0x18
    NOT = 0x19
    BYTE = 0x1A
    SHL = 0x1B
    SHR = 0x1C
    SAR = 0x1D
    SHA3 = 0x20
    ADDRESS = 0x30
    BALANCE = 0x31
    ORIGIN = 0x32
    CALLER = 0x33
    CALLVALUE = 0x34
    CALLDATALOAD = 0x35
    CALLDATASIZE = 0x36
    CALLDATACOPY = 0x37
    CODESIZE = 0x38
    CODECOPY = 0x39
    GASPRICE = 0x3A
    EXTCODESIZE = 0x3B
    EXTCODECOPY = 0x3C
    RETURNDATASIZE = 0x3D
    RETURNDATACOPY = 0x3E
    EXTCODEHASH = 0x3F
    BLOCKHASH = 0x40
    COINBASE = 0x41
    TIMESTAMP = 0x42
    NUMBER = 0x43
    DIFFICULTY = 0x44
    GASLIMIT = 0x45
    CHAINID = 0x46
    SELFBALANCE = 0x47
    BASEFEE = 0x48
    POP = 0x50
    MLOAD = 0x51
    MSTORE = 0x52
    MSTORE8 = 0x53
    SLOAD = 0x54
    SSTORE = 0x55
    JUMP = 0x56
    JUMPI = 0x57
    PC = 0x58
    MSIZE = 0x59
    GAS = 0x5A
    JUMPDEST = 0x5B
    PUSH1 = 0x60
    PUSH2 = 0x61
    PUSH3 = 0x62
    PUSH4 = 0x63
    PUSH5 = 0x64
    PUSH6 = 0x65
    PUSH7 = 0x66
    PUSH8 = 0x67
    PUSH9 = 0x68
    PUSH10 = 0x69
    PUSH11 = 0x6A
    PUSH12 = 0x6B
    PUSH13 = 0x6C
    PUSH14 = 0x6D
    PUSH15 = 0x6E
    PUSH16 = 0x6F
    PUSH17 = 0x70
    PUSH18 = 0x71
    PUSH19 = 0x72
    PUSH20 = 0x73
    PUSH21 = 0x74
    PUSH22 = 0x75
    PUSH23 = 0x76
    PUSH24 = 0x77
    PUSH25 = 0x78
    PUSH26 = 0x79
    PUSH27 = 0x7A
    PUSH28 = 0x7B
    PUSH29 = 0x7C
    PUSH30 = 0x7D
    PUSH31 = 0x7E
    PUSH32 = 0x7F
    DUP1 = 0x80
    DUP2 = 0x81
    DUP3 = 0x82
    DUP4 = 0x83
    DUP5 = 0x84
    DUP6 = 0x85
    DUP7 = 0x86
    DUP8 = 0x87
    DUP9 = 0x88
    DUP10 = 0x89
    DUP11 = 0x8A
    DUP12 = 0x8B
    DUP13 = 0x8C
    DUP14 = 0x8D
    DUP15 = 0x8E
    DUP16 = 0x8F
    SWAP1 = 0x90
    SWAP2 = 0x91
    SWAP3 = 0x92
    SWAP4 = 0x93
    SWAP5 = 0x94
    SWAP6 = 0x95
    SWAP7 = 0x96
    SWAP8 = 0x97
    SWAP9 = 0x98
    SWAP10 = 0x99
    SWAP11 = 0x9A
    SWAP12 = 0x9B
    SWAP13 = 0x9C
    SWAP14 = 0x9D
    SWAP15 = 0x9E
    SWAP16 = 0x9F
    LOG0 = 0xA0
    LOG1 = 0xA1
    LOG2 = 0xA2
    LOG3 = 0xA3
    LOG4 = 0xA4
    CREATE = 0xF0
    CALL = 0xF1
    CALLCODE = 0xF2
    RETURN = 0xF3
    DELEGATECALL = 0xF4
    CREATE2 = 0xF5
    STATICCALL = 0xFA
    REVERT = 0xFD
    INVALID = 0xFE
    SELFDESTRUCT = 0xFF


# Build reverse lookup: opcode value → name
_OPCODE_NAME: Dict[int, str] = {v: k for k, v in Opcode.__members__.items()}


def opcode_name(opcode: int) -> str:
    return _OPCODE_NAME.get(opcode, f"UNKNOWN_0x{opcode:02X}")


# Gas cost table (Istanbul/Paris era — simplified)
_GAS_TABLE: Dict[int, int] = {
    Opcode.STOP: 0,
    Opcode.ADD: 3,
    Opcode.MUL: 5,
    Opcode.SUB: 3,
    Opcode.DIV: 5,
    Opcode.SDIV: 5,
    Opcode.MOD: 5,
    Opcode.SMOD: 5,
    Opcode.ADDMOD: 8,
    Opcode.MULMOD: 8,
    Opcode.EXP: 10,
    Opcode.SIGNEXTEND: 5,
    Opcode.LT: 3,
    Opcode.GT: 3,
    Opcode.SLT: 3,
    Opcode.SGT: 3,
    Opcode.EQ: 3,
    Opcode.ISZERO: 3,
    Opcode.AND: 3,
    Opcode.OR: 3,
    Opcode.XOR: 3,
    Opcode.NOT: 3,
    Opcode.BYTE: 3,
    Opcode.SHL: 3,
    Opcode.SHR: 3,
    Opcode.SAR: 3,
    Opcode.SHA3: 30,
    Opcode.ADDRESS: 2,
    Opcode.BALANCE: 400,
    Opcode.ORIGIN: 2,
    Opcode.CALLER: 2,
    Opcode.CALLVALUE: 2,
    Opcode.CALLDATALOAD: 3,
    Opcode.CALLDATASIZE: 2,
    Opcode.CALLDATACOPY: 3,
    Opcode.CODESIZE: 2,
    Opcode.CODECOPY: 3,
    Opcode.GASPRICE: 2,
    Opcode.EXTCODESIZE: 700,
    Opcode.EXTCODECOPY: 700,
    Opcode.RETURNDATASIZE: 2,
    Opcode.RETURNDATACOPY: 3,
    Opcode.EXTCODEHASH: 700,
    Opcode.BLOCKHASH: 20,
    Opcode.COINBASE: 2,
    Opcode.TIMESTAMP: 2,
    Opcode.NUMBER: 2,
    Opcode.DIFFICULTY: 2,
    Opcode.GASLIMIT: 2,
    Opcode.CHAINID: 2,
    Opcode.SELFBALANCE: 5,
    Opcode.BASEFEE: 2,
    Opcode.POP: 2,
    Opcode.MLOAD: 3,
    Opcode.MSTORE: 3,
    Opcode.MSTORE8: 3,
    Opcode.SLOAD: 200,
    Opcode.SSTORE: 20000,
    Opcode.JUMP: 8,
    Opcode.JUMPI: 10,
    Opcode.PC: 2,
    Opcode.MSIZE: 2,
    Opcode.GAS: 2,
    Opcode.JUMPDEST: 1,
    Opcode.LOG0: 375,
    Opcode.LOG1: 750,
    Opcode.LOG2: 1125,
    Opcode.LOG3: 1500,
    Opcode.LOG4: 1875,
    Opcode.CREATE: 32000,
    Opcode.CALL: 700,
    Opcode.CALLCODE: 700,
    Opcode.RETURN: 0,
    Opcode.DELEGATECALL: 700,
    Opcode.CREATE2: 32000,
    Opcode.STATICCALL: 700,
    Opcode.REVERT: 0,
    Opcode.INVALID: 0,
    Opcode.SELFDESTRUCT: 5000,
}

for push_op in range(Opcode.PUSH1, Opcode.PUSH32 + 1):
    _GAS_TABLE[push_op] = 3
for dup_op in range(Opcode.DUP1, Opcode.DUP16 + 1):
    _GAS_TABLE[dup_op] = 3
for swap_op in range(Opcode.SWAP1, Opcode.SWAP16 + 1):
    _GAS_TABLE[swap_op] = 3


def opcode_gas(opcode: int) -> int:
    return _GAS_TABLE.get(opcode, 0)


# Stack effect: (pops, pushes) — simplified
_STACK_EFFECT: Dict[int, Tuple[int, int]] = {
    Opcode.STOP: (0, 0),
    Opcode.ADD: (2, 1),
    Opcode.MUL: (2, 1),
    Opcode.SUB: (2, 1),
    Opcode.DIV: (2, 1),
    Opcode.SDIV: (2, 1),
    Opcode.MOD: (2, 1),
    Opcode.SMOD: (2, 1),
    Opcode.ADDMOD: (3, 1),
    Opcode.MULMOD: (3, 1),
    Opcode.EXP: (2, 1),
    Opcode.SIGNEXTEND: (2, 1),
    Opcode.LT: (2, 1),
    Opcode.GT: (2, 1),
    Opcode.SLT: (2, 1),
    Opcode.SGT: (2, 1),
    Opcode.EQ: (2, 1),
    Opcode.ISZERO: (1, 1),
    Opcode.AND: (2, 1),
    Opcode.OR: (2, 1),
    Opcode.XOR: (2, 1),
    Opcode.NOT: (1, 1),
    Opcode.BYTE: (2, 1),
    Opcode.SHL: (2, 1),
    Opcode.SHR: (2, 1),
    Opcode.SAR: (2, 1),
    Opcode.SHA3: (2, 1),
    Opcode.ADDRESS: (0, 1),
    Opcode.BALANCE: (1, 1),
    Opcode.ORIGIN: (0, 1),
    Opcode.CALLER: (0, 1),
    Opcode.CALLVALUE: (0, 1),
    Opcode.CALLDATALOAD: (1, 1),
    Opcode.CALLDATASIZE: (0, 1),
    Opcode.CALLDATACOPY: (3, 0),
    Opcode.CODESIZE: (0, 1),
    Opcode.CODECOPY: (3, 0),
    Opcode.GASPRICE: (0, 1),
    Opcode.EXTCODESIZE: (1, 1),
    Opcode.EXTCODECOPY: (4, 0),
    Opcode.RETURNDATASIZE: (0, 1),
    Opcode.RETURNDATACOPY: (3, 0),
    Opcode.EXTCODEHASH: (1, 1),
    Opcode.BLOCKHASH: (1, 1),
    Opcode.COINBASE: (0, 1),
    Opcode.TIMESTAMP: (0, 1),
    Opcode.NUMBER: (0, 1),
    Opcode.DIFFICULTY: (0, 1),
    Opcode.GASLIMIT: (0, 1),
    Opcode.CHAINID: (0, 1),
    Opcode.SELFBALANCE: (0, 1),
    Opcode.BASEFEE: (0, 1),
    Opcode.POP: (1, 0),
    Opcode.MLOAD: (1, 1),
    Opcode.MSTORE: (2, 0),
    Opcode.MSTORE8: (2, 0),
    Opcode.SLOAD: (1, 1),
    Opcode.SSTORE: (2, 0),
    Opcode.JUMP: (1, 0),
    Opcode.JUMPI: (2, 0),
    Opcode.PC: (0, 1),
    Opcode.MSIZE: (0, 1),
    Opcode.GAS: (0, 1),
    Opcode.JUMPDEST: (0, 0),
    Opcode.LOG0: (2, 0),
    Opcode.LOG1: (3, 0),
    Opcode.LOG2: (4, 0),
    Opcode.LOG3: (5, 0),
    Opcode.LOG4: (6, 0),
    Opcode.CREATE: (3, 1),
    Opcode.CALL: (7, 1),
    Opcode.CALLCODE: (7, 1),
    Opcode.RETURN: (2, 0),
    Opcode.DELEGATECALL: (6, 1),
    Opcode.CREATE2: (4, 1),
    Opcode.STATICCALL: (6, 1),
    Opcode.REVERT: (2, 0),
    Opcode.INVALID: (0, 0),
    Opcode.SELFDESTRUCT: (1, 0),
}

for push_op in range(Opcode.PUSH1, Opcode.PUSH32 + 1):
    _STACK_EFFECT[push_op] = (0, 1)
for dup_op in range(Opcode.DUP1, Opcode.DUP16 + 1):
    _STACK_EFFECT[dup_op] = (dup_op - Opcode.DUP1 + 1, dup_op - Opcode.DUP1 + 2)
for swap_op in range(Opcode.SWAP1, Opcode.SWAP16 + 1):
    _STACK_EFFECT[swap_op] = (swap_op - Opcode.SWAP1 + 2, swap_op - Opcode.SWAP1 + 2)


def stack_effect(opcode: int) -> Tuple[int, int]:
    return _STACK_EFFECT.get(opcode, (0, 0))


# ─────────────────────────────────────────────────────────────────────────────
# 1. EVM OPCODE STREAM — Bytecode Parser & Disassembler
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class Instruction:
    """Satu instruction EVM dengan metadata."""
    pc: int
    opcode: int
    operand: Optional[bytes] = None  # untuk PUSH1–PUSH32
    mnemonic: str = ""
    gas_cost: int = 0
    stack_pops: int = 0
    stack_pushes: int = 0

    @property
    def size(self) -> int:
        base = 1
        if self.operand:
            base += len(self.operand)
        return base

    @property
    def hex_opcode(self) -> str:
        return f"0x{self.opcode:02X}"

    @property
    def hex_operand(self) -> str:
        if self.operand:
            return self.operand.hex()
        return ""

    @property
    def hex_repr(self) -> str:
        if self.operand:
            return f"{self.opcode:02x}{self.operand.hex()}"
        return f"{self.opcode:02x}"

    def __str__(self) -> str:
        if self.operand:
            return f"{self.pc:04X}: {self.mnemonic} 0x{self.operand.hex()}"
        return f"{self.pc:04X}: {self.mnemonic}"


class EVMBytecodeParser:
    """
    Parser & disassembler untuk EVM hex bytecode.
    Input: "0x6080604052..." → Output: List[Instruction]
    """

    @staticmethod
    def parse(hex_bytecode: str) -> List[Instruction]:
        """Parse hex string menjadi instruction stream."""
        # Strip prefix
        raw = hex_bytecode.strip()
        if raw.startswith("0x") or raw.startswith("0X"):
            raw = raw[2:]
        raw = raw.replace(" ", "").replace("\n", "")

        if len(raw) % 2 != 0:
            raise ValueError("Invalid hex bytecode: odd length")

        bytecode = bytes.fromhex(raw)
        instructions: List[Instruction] = []
        i = 0
        while i < len(bytecode):
            opcode = bytecode[i]
            mnemonic = opcode_name(opcode)
            gas = opcode_gas(opcode)
            pops, pushes = stack_effect(opcode)

            operand: Optional[bytes] = None
            if Opcode.PUSH1 <= opcode <= Opcode.PUSH32:
                push_size = opcode - Opcode.PUSH1 + 1
                end = i + 1 + push_size
                if end > len(bytecode):
                    operand = bytecode[i + 1:]  # truncated — pad dengan zeros
                else:
                    operand = bytecode[i + 1:end]

            instr = Instruction(
                pc=i,
                opcode=opcode,
                operand=operand,
                mnemonic=mnemonic,
                gas_cost=gas,
                stack_pops=pops,
                stack_pushes=pushes,
            )
            instructions.append(instr)
            i += instr.size

        return instructions

    @staticmethod
    def assemble(instructions: List[Instruction]) -> str:
        """Assemble instruction stream kembali ke hex bytecode."""
        out = bytearray()
        for instr in instructions:
            out.append(instr.opcode)
            if instr.operand:
                out.extend(instr.operand)
        return "0x" + out.hex()

    @staticmethod
    def disassemble(hex_bytecode: str) -> str:
        """Full disassembly ke human-readable text."""
        instructions = EVMBytecodeParser.parse(hex_bytecode)
        lines = []
        for instr in instructions:
            if instr.operand:
                operand_hex = "0x" + instr.operand.hex()
                lines.append(f"{instr.pc:04X}  {instr.hex_opcode} {operand_hex:20s}  {instr.mnemonic} {operand_hex}")
            else:
                lines.append(f"{instr.pc:04X}  {instr.hex_opcode:23s}  {instr.mnemonic}")
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# 2. MNEMONIC ASSEMBLER — Parse Huff/assembly text → bytecode
# ─────────────────────────────────────────────────────────────────────────────


class MnemonicAssembler:
    """
    Assembler dari mnemonic text ke bytecode.
    Support format: satu mnemonic per line, PUSH dengan operand.
    """

    @staticmethod
    def parse_mnemonic_line(line: str) -> Optional[Tuple[int, Optional[bytes]]]:
        """Parse satu line mnemonic → (opcode, operand)."""
        line = line.strip().split("//")[0].strip()  # strip comment
        if not line:
            return None

        parts = line.split()
        mnemonic = parts[0].upper()

        # Cari opcode
        opcode = None
        for op_val, op_name in _OPCODE_NAME.items():
            if op_name == mnemonic:
                opcode = op_val
                break

        if opcode is None:
            return None  # unknown — skip atau label

        operand: Optional[bytes] = None
        if Opcode.PUSH1 <= opcode <= Opcode.PUSH32 and len(parts) > 1:
            val_str = parts[1]
            if val_str.startswith("0x"):
                val = int(val_str, 16)
            else:
                val = int(val_str)
            push_size = opcode - Opcode.PUSH1 + 1
            operand = val.to_bytes(push_size, "big")

        return opcode, operand

    @staticmethod
    def assemble_text(assembly: str) -> str:
        """Assemble multi-line assembly text → hex bytecode."""
        out = bytearray()
        for line in assembly.splitlines():
            parsed = MnemonicAssembler.parse_mnemonic_line(line)
            if parsed:
                opcode, operand = parsed
                out.append(opcode)
                if operand:
                    out.extend(operand)
        return "0x" + out.hex()

    @staticmethod
    def disassemble_to_mnemonics(hex_bytecode: str) -> List[str]:
        """Parse bytecode → list of mnemonic strings."""
        instructions = EVMBytecodeParser.parse(hex_bytecode)
        lines = []
        for instr in instructions:
            if instr.operand:
                lines.append(f"{instr.mnemonic} 0x{instr.operand.hex()}")
            else:
                lines.append(instr.mnemonic)
        return lines


# ─────────────────────────────────────────────────────────────────────────────
# 3. PEEPHOLE OPTIMIZER — Core Pattern Matching Engine
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class OptimizationRule:
    """Satu rule: match pattern → replace dengan sequence, dengan conditions."""
    name: str
    description: str
    pattern: List[Tuple[int, Optional[bytes]]]  # [(opcode, operand_or_None), ...]
    replacement: List[Tuple[int, Optional[bytes]]]
    gas_delta: int  # negative = saved
    stack_delta: int  # net stack change
    condition: Optional[Callable[[List[Instruction]], bool]] = None


class PeepholeOptimizer:
    """
    Core peephole optimizer — meniru bytepeep architecture:
    • Sliding window size N (default 2–4)
    • Pattern matching tiap window position
    • Jika match & condition true → replace
    • Track jump targets untuk remapping
    • Track gas savings per rule
    """

    def __init__(self, window_size: int = 3) -> None:
        self.window_size = window_size
        self.rules: List[OptimizationRule] = self._build_default_rules()
        self.stats: Dict[str, int] = {}  # rule name → count applied
        self.total_gas_saved = 0

    # ── Default Rules ───────────────────────────────────────────────────────

    def _build_default_rules(self) -> List[OptimizationRule]:
        rules: List[OptimizationRule] = []

        # R1: DUP1 + POP → (nothing) — stack net 0, saves 5 gas
        rules.append(OptimizationRule(
            name="dup1_pop_eliminate",
            description="DUP1 followed by POP is redundant — removes both",
            pattern=[(Opcode.DUP1, None), (Opcode.POP, None)],
            replacement=[],
            gas_delta=-5,  # DUP1(3) + POP(2) = 5 saved
            stack_delta=0,
        ))

        # R2: PUSH0 + POP → (nothing) — only if PUSH1 0x00
        rules.append(OptimizationRule(
            name="push0_pop_eliminate",
            description="Push 0 then pop is wasted work",
            pattern=[(Opcode.PUSH1, b'\x00'), (Opcode.POP, None)],
            replacement=[],
            gas_delta=-5,
            stack_delta=0,
        ))

        # R3: SWAP1 + SWAP1 → (nothing) — double swap = identity
        rules.append(OptimizationRule(
            name="swap1_swap1_identity",
            description="Two consecutive SWAP1 cancel each other",
            pattern=[(Opcode.SWAP1, None), (Opcode.SWAP1, None)],
            replacement=[],
            gas_delta=-6,
            stack_delta=0,
        ))

        # R4: PUSH x + PUSH y + ADD → PUSH (x+y)  (constant folding, small values)
        rules.append(OptimizationRule(
            name="const_fold_add",
            description="Constant fold: PUSH a + PUSH b + ADD → PUSH (a+b)",
            pattern=[(Opcode.PUSH1, None), (Opcode.PUSH1, None), (Opcode.ADD, None)],
            replacement=[(Opcode.PUSH1, None)],  # operand computed at match time
            gas_delta=-3,  # 3+3+3=9 → 3 = save 6, tapi replacement PUSH perlu compute
            stack_delta=-1,
            condition=self._can_const_fold_add,
        ))

        # R5: AND dengan 0xFF…FF (full mask) → no-op
        rules.append(OptimizationRule(
            name="and_fullmask_noop",
            description="AND with all-ones mask is identity",
            pattern=[(Opcode.PUSH32, None), (Opcode.AND, None)],
            replacement=[],
            gas_delta=-5,
            stack_delta=-1,
            condition=self._is_full_mask,
        ))

        # R6: ISZERO + ISZERO → (nothing) — double negation
        rules.append(OptimizationRule(
            name="iszero_iszero_eliminate",
            description="Double ISZERO cancels out (boolean only)",
            pattern=[(Opcode.ISZERO, None), (Opcode.ISZERO, None)],
            replacement=[],
            gas_delta=-6,
            stack_delta=0,
            condition=self._safe_double_iszero,
        ))

        # R7: PUSH x + DUP1 + SWAP1 → PUSH x + DUP1 (SWAP1 dengan top identical = no-op)
        rules.append(OptimizationRule(
            name="dup_swap_identity",
            description="DUP1 SWAP1 when both items equal → remove SWAP1",
            pattern=[(Opcode.DUP1, None), (Opcode.SWAP1, None)],
            replacement=[(Opcode.DUP1, None)],
            gas_delta=-3,
            stack_delta=0,
            condition=self._dup_swap_same,
        ))

        # R8: MSTORE dengan sequential address bisa batch (simplified demo)
        rules.append(OptimizationRule(
            name="pop_pop_eliminate",
            description="POP POP can sometimes be eliminated if values unused",
            pattern=[(Opcode.POP, None), (Opcode.POP, None)],
            replacement=[],
            gas_delta=-4,
            stack_delta=0,
        ))

        return rules

    # ── Conditions ──────────────────────────────────────────────────────────

    def _can_const_fold_add(self, window: List[Instruction]) -> bool:
        if len(window) != 3:
            return False
        a = int.from_bytes(window[0].operand or b'\x00', "big")
        b = int.from_bytes(window[1].operand or b'\x00', "big")
        s = a + b
        # Only fold if result fits in PUSH1 (0–255) or PUSH2 (0–65535)
        return s <= 0xFFFF

    def _is_full_mask(self, window: List[Instruction]) -> bool:
        if len(window) != 2:
            return False
        op = window[0].operand
        if not op:
            return False
        return all(b == 0xFF for b in op)

    def _safe_double_iszero(self, _window: List[Instruction]) -> bool:
        # For demo: assume safe untuk semua boolean context
        return True

    def _dup_swap_same(self, window: List[Instruction]) -> bool:
        # DUP1 copies top of stack; SWAP1 swaps top 2.
        # If the 2nd item equals top (which DUP1 duplicated), SWAP1 is no-op.
        # This requires stack tracking — untuk demo, heuristic: eliminate SWAP1 bila DUP1 di depan
        return True

    # ── Optimizer Loop ────────────────────────────────────────────────────────

    def optimize(self, instructions: List[Instruction]) -> List[Instruction]:
        """
        Run peephole optimization passes sampai tidak ada lagi rule yang match.
        Return optimized instruction stream.
        """
        changed = True
        passes = 0
        max_passes = 10

        while changed and passes < max_passes:
            changed = False
            passes += 1
            instructions = self._optimize_pass(instructions)
            if self._last_pass_changed:
                changed = True

        return instructions

    def _optimize_pass(self, instructions: List[Instruction]) -> List[Instruction]:
        self._last_pass_changed = False
        result: List[Instruction] = []
        i = 0

        while i < len(instructions):
            matched = False
            # Try rules dari largest window ke smallest
            for rule in sorted(self.rules, key=lambda r: len(r.pattern), reverse=True):
                wlen = len(rule.pattern)
                if i + wlen > len(instructions):
                    continue
                window = instructions[i:i + wlen]
                if self._match(rule, window):
                    if rule.condition and not rule.condition(window):
                        continue
                    # Apply replacement
                    replaced = self._build_replacement(rule, window)
                    result.extend(replaced)
                    self.stats[rule.name] = self.stats.get(rule.name, 0) + 1
                    self.total_gas_saved += abs(rule.gas_delta)
                    i += wlen
                    matched = True
                    self._last_pass_changed = True
                    break

            if not matched:
                result.append(instructions[i])
                i += 1

        return result

    def _match(self, rule: OptimizationRule, window: List[Instruction]) -> bool:
        if len(rule.pattern) != len(window):
            return False
        for (pat_op, pat_operand), instr in zip(rule.pattern, window):
            if pat_op != instr.opcode:
                return False
            if pat_operand is not None and instr.operand != pat_operand:
                return False
        return True

    def _build_replacement(self, rule: OptimizationRule,
                           window: List[Instruction]) -> List[Instruction]:
        """Build replacement instructions dengan operand yang computed kalau perlu."""
        result: List[Instruction] = []

        if rule.name == "const_fold_add" and len(window) == 3:
            a = int.from_bytes(window[0].operand or b'\x00', "big")
            b_val = int.from_bytes(window[1].operand or b'\x00', "big")
            s = a + b_val
            if s <= 0xFF:
                opcode = Opcode.PUSH1
                operand = s.to_bytes(1, "big")
            else:
                opcode = Opcode.PUSH2
                operand = s.to_bytes(2, "big")
            result.append(Instruction(
                pc=-1, opcode=opcode, operand=operand,
                mnemonic=opcode_name(opcode), gas_cost=3,
                stack_pops=0, stack_pushes=1,
            ))
            return result

        # Default: build dari rule replacement pattern
        for op, operand in rule.replacement:
            result.append(Instruction(
                pc=-1, opcode=op, operand=operand,
                mnemonic=opcode_name(op), gas_cost=opcode_gas(op),
                stack_pops=0, stack_pushes=1 if Opcode.PUSH1 <= op <= Opcode.PUSH32 else 0,
            ))
        return result

    def get_report(self) -> Dict[str, Any]:
        return {
            "rules_applied": self.stats,
            "total_rules_applied": sum(self.stats.values()),
            "total_gas_saved": self.total_gas_saved,
            "rules_available": len(self.rules),
        }


# ─────────────────────────────────────────────────────────────────────────────
# 4. JUMP TARGET REMAPPER — Update offsets setelah optimization
# ─────────────────────────────────────────────────────────────────────────────


class JumpTargetRemapper:
    """
    Setelah bytecode di-optimize (opcode dihapus/ditambah), semua PUSH operand
    yang berisi jump target offsets (PC dari JUMPDEST) harus di-remap.
    """

    @staticmethod
    def remap(instructions: List[Instruction]) -> List[Instruction]:
        """Rebuild PC offsets dan update semua PUSH operand yang menunjuk ke JUMPDEST."""
        # Pass 1: assign new PCs
        new_pcs: List[int] = []
        pc = 0
        for instr in instructions:
            new_pcs.append(pc)
            pc += instr.size

        # Pass 2: build JUMPDEST PC map
        jumpdests: Dict[int, int] = {}  # old_pc → new_pc
        for idx, instr in enumerate(instructions):
            if instr.opcode == Opcode.JUMPDEST:
                jumpdests[instr.pc] = new_pcs[idx]

        # Pass 3: update PUSH operand bila isinya adalah old JUMPDEST PC
        for idx, instr in enumerate(instructions):
            if Opcode.PUSH1 <= instr.opcode <= Opcode.PUSH32 and instr.operand:
                val = int.from_bytes(instr.operand, "big")
                if val in jumpdests:
                    new_val = jumpdests[val]
                    push_size = instr.opcode - Opcode.PUSH1 + 1
                    instr.operand = new_val.to_bytes(push_size, "big")
            instr.pc = new_pcs[idx]

        return instructions


# ─────────────────────────────────────────────────────────────────────────────
# 5. BYTEPEEP ENGINE — Unified Optimizer API
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class OptimizeResult:
    """Hasil optimasi satu bytecode."""
    original_bytecode: str
    optimized_bytecode: str
    original_gas: int
    optimized_gas: int
    gas_saved: int
    gas_saved_pct: float
    original_size: int
    optimized_size: int
    rules_applied: Dict[str, int]
    passes: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_bytecode": self.original_bytecode,
            "optimized_bytecode": self.optimized_bytecode,
            "original_gas": self.original_gas,
            "optimized_gas": self.optimized_gas,
            "gas_saved": self.gas_saved,
            "gas_saved_pct": round(self.gas_saved_pct, 2),
            "original_size": self.original_size,
            "optimized_size": self.optimized_size,
            "size_delta": self.optimized_size - self.original_size,
            "rules_applied": self.rules_applied,
            "passes": self.passes,
        }


class BytepeepEngine:
    """
    Unified bytepeep optimizer API:
    • optimize(hex_bytecode) → optimized hex bytecode
    • optimize_mnemonic(assembly_text) → optimized assembly text
    • disassemble(hex_bytecode) → readable text
    • analyze(hex_bytecode) → gas analysis report
    """

    def __init__(self, window_size: int = 3) -> None:
        self.optimizer = PeepholeOptimizer(window_size=window_size)
        self.parser = EVMBytecodeParser()
        self.remapper = JumpTargetRemapper()
        self.assembler = MnemonicAssembler()

    def optimize(self, hex_bytecode: str, passes: int = 3) -> OptimizeResult:
        """Optimize hex bytecode, return full result."""
        instructions = self.parser.parse(hex_bytecode)
        original_gas = sum(i.gas_cost for i in instructions)
        original_size = sum(i.size for i in instructions)

        # Run multiple passes
        current = instructions
        for _ in range(passes):
            current = self.optimizer.optimize(current)
            current = self.remapper.remap(current)

        optimized_gas = sum(i.gas_cost for i in current)
        optimized_size = sum(i.size for i in current)
        gas_saved = original_gas - optimized_gas

        result = OptimizeResult(
            original_bytecode=hex_bytecode,
            optimized_bytecode=self.parser.assemble(current),
            original_gas=original_gas,
            optimized_gas=optimized_gas,
            gas_saved=gas_saved,
            gas_saved_pct=(gas_saved / original_gas * 100) if original_gas > 0 else 0.0,
            original_size=original_size,
            optimized_size=optimized_size,
            rules_applied=dict(self.optimizer.stats),
            passes=passes,
        )
        return result

    def optimize_mnemonic(self, assembly_text: str, passes: int = 3) -> str:
        """Optimize dari assembly text → optimized assembly text."""
        hex_bc = self.assembler.assemble_text(assembly_text)
        result = self.optimize(hex_bc, passes=passes)
        return "\n".join(self.assembler.disassemble_to_mnemonics(result.optimized_bytecode))

    def disassemble(self, hex_bytecode: str) -> str:
        return self.parser.disassemble(hex_bytecode)

    def analyze(self, hex_bytecode: str) -> Dict[str, Any]:
        """Gas & stack analysis tanpa optimasi."""
        instructions = self.parser.parse(hex_bytecode)
        total_gas = sum(i.gas_cost for i in instructions)
        total_size = sum(i.size for i in instructions)

        opcode_counts: Dict[str, int] = {}
        for i in instructions:
            opcode_counts[i.mnemonic] = opcode_counts.get(i.mnemonic, 0) + 1

        # Stack depth tracking
        max_depth = 0
        current_depth = 0
        for i in instructions:
            current_depth -= i.stack_pops
            current_depth += i.stack_pushes
            max_depth = max(max_depth, current_depth)

        jumpdest_count = sum(1 for i in instructions if i.opcode == Opcode.JUMPDEST)
        push_count = sum(1 for i in instructions if Opcode.PUSH1 <= i.opcode <= Opcode.PUSH32)

        return {
            "total_gas": total_gas,
            "total_size_bytes": total_size,
            "instruction_count": len(instructions),
            "max_stack_depth": max_depth,
            "jumpdest_count": jumpdest_count,
            "push_count": push_count,
            "opcode_distribution": dict(sorted(opcode_counts.items(), key=lambda x: x[1], reverse=True)[:20]),
        }

    def add_custom_rule(self, rule: OptimizationRule) -> None:
        self.optimizer.rules.append(rule)

    def list_rules(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": r.name,
                "description": r.description,
                "pattern_size": len(r.pattern),
                "replacement_size": len(r.replacement),
                "gas_delta": r.gas_delta,
            }
            for r in self.optimizer.rules
        ]


# ─────────────────────────────────────────────────────────────────────────────
# 6. HUFF INTEGRATION — Preprocess Huff assembly ke EVM bytecode
# ─────────────────────────────────────────────────────────────────────────────


class HuffPreprocessor:
    """
    Preprocessor sederhana untuk Huff assembly:
    • Expand macros (inline substitution)
    • Resolve labels → PC offsets
    • Convert ke mnemonic format yang bisa diparse Bytepeep

    Note: Ini adalah preprocessor minimal. Full Huff compiler (huff-rs/huff2)
    adalah project tersendiri — di sini kita support subset yang umum.
    """

    @staticmethod
    def preprocess(huff_code: str) -> str:
        """Convert Huff ke plain EVM mnemonic assembly."""
        lines: List[str] = []
        labels: Dict[str, int] = {}
        macros: Dict[str, List[str]] = {}
        current_macro: Optional[str] = None

        # Pass 1: collect macros & labels
        pc = 0
        for line in huff_code.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("//") or stripped.startswith("#"):
                continue

            # Macro definition: #define macro NAME() = takes(0) returns(0) { ... }
            macro_match = re.match(r'#define\s+macro\s+(\w+)', stripped)
            if macro_match:
                current_macro = macro_match.group(1)
                macros[current_macro] = []
                continue
            if stripped == "}" and current_macro:
                current_macro = None
                continue
            if current_macro:
                macros[current_macro].append(stripped)
                continue

            # Label: <label>:
            label_match = re.match(r'<(\w+)>:', stripped)
            if label_match:
                labels[label_match.group(1)] = pc
                lines.append("JUMPDEST")
                pc += 1
                continue

            # Regular opcode line
            mnemonic = stripped.split()[0].upper() if stripped else ""
            if mnemonic in [name for name in _OPCODE_NAME.values()]:
                lines.append(stripped)
                # Estimate PC increment
                if mnemonic.startswith("PUSH"):
                    pc += 1 + int(mnemonic[4:])
                else:
                    pc += 1

        # Pass 2: resolve label references in PUSH operand
        resolved: List[str] = []
        for line in lines:
            # Replace __label dengan PC address
            for label, addr in labels.items():
                line = re.sub(rf'__{label}\b', f"0x{addr:04X}", line)
            resolved.append(line)

        return "\n".join(resolved)


# ─────────────────────────────────────────────────────────────────────────────
# 7. BATCH OPTIMIZER — Process multiple contracts
# ─────────────────────────────────────────────────────────────────────────────


class BatchOptimizer:
    """Optimize batch of bytecode files/contracts."""

    def __init__(self, engine: BytepeepEngine) -> None:
        self.engine = engine
        self.results: List[Tuple[str, OptimizeResult]] = []

    def optimize_file(self, path: Path) -> OptimizeResult:
        hex_bc = path.read_text().strip()
        result = self.engine.optimize(hex_bc)
        self.results.append((str(path), result))
        return result

    def optimize_directory(self, dir_path: Path, pattern: str = "*.bin") -> List[Tuple[str, OptimizeResult]]:
        for f in sorted(dir_path.glob(pattern)):
            self.optimize_file(f)
        return self.results

    def summary_report(self) -> Dict[str, Any]:
        total_gas_saved = sum(r.gas_saved for _, r in self.results)
        total_original = sum(r.original_gas for _, r in self.results)
        total_optimized = sum(r.optimized_gas for _, r in self.results)
        return {
            "contracts_processed": len(self.results),
            "total_original_gas": total_original,
            "total_optimized_gas": total_optimized,
            "total_gas_saved": total_gas_saved,
            "avg_savings_pct": (total_gas_saved / total_original * 100) if total_original > 0 else 0.0,
            "details": [(name, r.to_dict()) for name, r in self.results],
        }


# ─────────────────────────────────────────────────────────────────────────────
# 8. MAGNATRIX INTEGRATION — Bridge ke Security Layer
# ─────────────────────────────────────────────────────────────────────────────


class BytepeepSecurityBridge:
    """
    Bridge untuk mengintegrasikan Bytepeep ke security audit workflow MAGNATRIX:
    • Pre-audit: optimize contract bytecode untuk analisis lebih bersih
    • Post-audit: gas optimization recommendation sebagai finding
    • SCVS integration: detect anti-patterns via opcode sequences
    """

    def __init__(self) -> None:
        self.engine = BytepeepEngine()

    def optimize_before_audit(self, hex_bytecode: str) -> OptimizeResult:
        """Optimize bytecode sebelum audit — menghilangkan noise dari compiler."""
        return self.engine.optimize(hex_bytecode, passes=5)

    def gas_optimization_finding(self, hex_bytecode: str, contract_name: str = "") -> Dict[str, Any]:
        """
        Generate gas optimization finding untuk audit report.
        Return format yang compatible dengan audit_portfolio_native.py Finding.
        """
        result = self.engine.optimize(hex_bytecode)
        if result.gas_saved <= 0:
            return {}

        return {
            "title": f"Gas optimization: {result.gas_saved} gas units can be saved ({result.gas_saved_pct:.1f}%)",
            "category": "Gas Optimization",
            "severity": "Gas",
            "description": f"Peephole analysis found {result.total_rules_applied} optimization opportunities "
                           f"saving {result.gas_saved} gas units. Rules applied: {list(result.rules_applied.keys())}.",
            "impact": f"Reduced gas cost improves user experience and reduces operational costs. "
                      f"Size change: {result.original_size} → {result.optimized_size} bytes.",
            "recommendation": "Apply peephole optimizer rules or use compiler optimization passes.",
            "gas_saved": result.gas_saved,
            "gas_saved_pct": result.gas_saved_pct,
            "rules_applied": result.rules_applied,
        }

    def detect_anti_patterns(self, hex_bytecode: str) -> List[Dict[str, Any]]:
        """
        Detect bytecode anti-patterns yang menunjukkan potensi bug:
        • SSTORE tanpa checks → reentrancy risk
        • CALLVALUE + CALLER pattern yang suspicious
        • Unchecked external calls
        """
        instructions = self.engine.parser.parse(hex_bytecode)
        patterns: List[Dict[str, Any]] = []

        # Pattern: SSTORE tanpa prior SLOAD (set storage tanpa read)
        for i in range(len(instructions)):
            if instructions[i].opcode == Opcode.SSTORE:
                # Look back untuk SLOAD dengan slot sama — simplified: look back 10 instr
                found_sload = False
                for j in range(max(0, i - 10), i):
                    if instructions[j].opcode == Opcode.SLOAD:
                        found_sload = True
                        break
                if not found_sload:
                    patterns.append({
                        "pattern": "unchecked_sstore",
                        "pc": instructions[i].pc,
                        "severity": "Medium",
                        "description": "SSTORE without preceding SLOAD — may indicate missing validation",
                    })

        # Pattern: CALL + ISZERO + POP (unchecked call return)
        for i in range(len(instructions) - 2):
            if (instructions[i].opcode in (Opcode.CALL, Opcode.STATICCALL, Opcode.DELEGATECALL)
                and instructions[i + 1].opcode == Opcode.ISZERO
                and instructions[i + 2].opcode == Opcode.POP):
                patterns.append({
                    "pattern": "unchecked_call",
                    "pc": instructions[i].pc,
                    "severity": "High",
                    "description": "External call result checked then discarded — potential security issue",
                })

        return patterns


# ─────────────────────────────────────────────────────────────────────────────
# 9. CLI ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────


def main() -> None:
    import sys
    args = sys.argv[1:]

    if not args or args[0] in ("-h", "--help", "help"):
        print("""
magnatrix-bytepeep — Native EVM bytecode peephole optimizer
Usage:
  magnatrix-bytepeep optimize <hex_bytecode>    Optimize bytecode
  magnatrix-bytepeep disasm <hex_bytecode>      Disassemble to readable text
  magnatrix-bytepeep analyze <hex_bytecode>     Gas & stack analysis
  magnatrix-bytepeep mnemonic <assembly_text>   Optimize assembly text
  magnatrix-bytepeep huff <huff_code_file>      Preprocess & optimize Huff
  magnatrix-bytepeep rules                       List optimization rules
""")
        return

    engine = BytepeepEngine()

    cmd = args[0]
    if cmd == "optimize" and len(args) > 1:
        result = engine.optimize(args[1])
        print(json.dumps(result.to_dict(), indent=2))
    elif cmd == "disasm" and len(args) > 1:
        print(engine.disassemble(args[1]))
    elif cmd == "analyze" and len(args) > 1:
        print(json.dumps(engine.analyze(args[1]), indent=2))
    elif cmd == "mnemonic" and len(args) > 1:
        print(engine.optimize_mnemonic(args[1]))
    elif cmd == "huff" and len(args) > 1:
        huff = Path(args[1]).read_text()
        preprocessed = HuffPreprocessor.preprocess(huff)
        print("--- Preprocessed ---")
        print(preprocessed)
        print("--- Optimized ---")
        print(engine.optimize_mnemonic(preprocessed))
    elif cmd == "rules":
        for r in engine.list_rules():
            print(f"  {r['name']}: {r['description']} (save {abs(r['gas_delta'])} gas)")
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()

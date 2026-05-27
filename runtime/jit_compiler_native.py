#!/usr/bin/env python3
"""
MAGNATRIX-OS — JIT Compiler Native
Tiered JIT: Ignition (interpreter) → Liftoff (baseline) → TurboFan (optimizer).
Register-based bytecode, NaN boxing, hot-path detection, background compilation.
Pure Python stdlib.
"""
from __future__ import annotations

import threading
import time
import struct
import functools
from typing import Dict, List, Tuple, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum, auto


# ── Value Representation: NaN Boxing ────────────────────────

class ValueType(Enum):
    INT = auto()
    FLOAT = auto()
    STRING = auto()
    BOOL = auto()
    NULL = auto()
    OBJECT = auto()


class NaNBoxedValue:
    """
    Pack all value types into 64-bit float NaN payload.
    Uses quiet NaN (exponent all 1s, mantissa non-zero).
    """
    _QNAN = 0x7FF8000000000000
    _TAG_INT = 0x0001
    _TAG_STR = 0x0002
    _TAG_BOOL = 0x0003
    _TAG_NULL = 0x0004
    _TAG_OBJ = 0x0005

    def __init__(self, raw: int = _QNAN):
        self.raw = raw

    @classmethod
    def from_int(cls, v: int) -> "NaNBoxedValue":
        return cls(cls._QNAN | cls._TAG_INT | (v & 0xFFFFFFFF) << 3)

    @classmethod
    def from_float(cls, v: float) -> "NaNBoxedValue":
        return cls(struct.unpack("<Q", struct.pack("<d", v))[0])

    @classmethod
    def from_string(cls, s: str) -> "NaNBoxedValue":
        return cls(cls._QNAN | cls._TAG_STR | (id(s) & 0xFFFFFFFF) << 3)

    @classmethod
    def from_bool(cls, b: bool) -> "NaNBoxedValue":
        return cls(cls._QNAN | cls._TAG_BOOL | (1 if b else 0) << 3)

    @classmethod
    def null(cls) -> "NaNBoxedValue":
        return cls(cls._QNAN | cls._TAG_NULL)

    def is_int(self) -> bool:
        return (self.raw & 0x7) == self._TAG_INT

    def is_float(self) -> bool:
        return not self.is_special()

    def is_special(self) -> bool:
        return (self.raw & self._QNAN) == self._QNAN and (self.raw & 0x7) != 0

    def as_int(self) -> int:
        return (self.raw >> 3) & 0xFFFFFFFF

    def as_float(self) -> float:
        return struct.unpack("<d", struct.pack("<Q", self.raw))[0]

    def as_bool(self) -> bool:
        return ((self.raw >> 3) & 0xFFFFFFFF) != 0

    def __repr__(self) -> str:
        if self.raw == self._QNAN | self._TAG_NULL:
            return "null"
        if self.is_int():
            return f"int:{self.as_int()}"
        if (self.raw & 0x7) == self._TAG_BOOL:
            return f"bool:{self.as_bool()}"
        if self.is_float():
            return f"float:{self.as_float():.4f}"
        return f"obj:{hex(self.raw)}"


# ── Bytecode ────────────────────────────────────────────────

class BytecodeOp(Enum):
    LOAD_CONST = auto()
    LOAD_REG = auto()
    STORE_REG = auto()
    ADD = auto()
    SUB = auto()
    MUL = auto()
    DIV = auto()
    MOD = auto()
    JUMP = auto()
    JUMP_IF_FALSE = auto()
    CALL = auto()
    RETURN = auto()
    EQ = auto()
    LT = auto()
    GT = auto()
    PRINT = auto()


@dataclass
class Instruction:
    op: BytecodeOp
    a: int = 0  # register A or arg
    b: int = 0  # register B
    c: int = 0  # register C or immediate


class BytecodeBuilder:
    """Build bytecode from simple arithmetic expressions."""

    def __init__(self):
        self.code: List[Instruction] = []
        self.constants: List[NaNBoxedValue] = []
        self.reg_counter = 0

    def _alloc_reg(self) -> int:
        r = self.reg_counter
        self.reg_counter += 1
        return r

    def emit(self, op: BytecodeOp, a: int = 0, b: int = 0, c: int = 0) -> None:
        self.code.append(Instruction(op, a, b, c))

    def compile_expr(self, tokens: List[str]) -> int:
        """Very simple RPN-like compiler for binary expressions."""
        # e.g., ["2", "3", "+"]
        stack: List[int] = []
        for tok in tokens:
            if tok in "+-*/%":
                right = stack.pop()
                left = stack.pop()
                out = self._alloc_reg()
                op_map = {"+": BytecodeOp.ADD, "-": BytecodeOp.SUB,
                          "*": BytecodeOp.MUL, "/": BytecodeOp.DIV, "%": BytecodeOp.MOD}
                self.emit(op_map[tok], out, left, right)
                stack.append(out)
            else:
                const_idx = len(self.constants)
                self.constants.append(NaNBoxedValue.from_int(int(tok)))
                reg = self._alloc_reg()
                self.emit(BytecodeOp.LOAD_CONST, reg, const_idx)
                stack.append(reg)
        return stack[-1]


# ── Ignition Interpreter ───────────────────────────────────

class IgnitionInterpreter:
    """Register-based bytecode interpreter."""

    def __init__(self):
        self.registers: Dict[int, NaNBoxedValue] = {}
        self.pc = 0
        self.call_count = 0

    def run(self, builder: BytecodeBuilder) -> NaNBoxedValue:
        code = builder.code
        consts = builder.constants
        self.pc = 0
        self.call_count += 1

        while self.pc < len(code):
            inst = code[self.pc]
            op = inst.op
            a, b, c = inst.a, inst.b, inst.c

            if op == BytecodeOp.LOAD_CONST:
                self.registers[a] = consts[b]
            elif op == BytecodeOp.LOAD_REG:
                self.registers[a] = self.registers[b]
            elif op == BytecodeOp.STORE_REG:
                self.registers[a] = self.registers[b]
            elif op == BytecodeOp.ADD:
                lv = self.registers[b].as_int()
                rv = self.registers[c].as_int()
                self.registers[a] = NaNBoxedValue.from_int(lv + rv)
            elif op == BytecodeOp.SUB:
                lv = self.registers[b].as_int()
                rv = self.registers[c].as_int()
                self.registers[a] = NaNBoxedValue.from_int(lv - rv)
            elif op == BytecodeOp.MUL:
                lv = self.registers[b].as_int()
                rv = self.registers[c].as_int()
                self.registers[a] = NaNBoxedValue.from_int(lv * rv)
            elif op == BytecodeOp.DIV:
                lv = self.registers[b].as_int()
                rv = self.registers[c].as_int()
                self.registers[a] = NaNBoxedValue.from_int(lv // rv if rv != 0 else 0)
            elif op == BytecodeOp.MOD:
                lv = self.registers[b].as_int()
                rv = self.registers[c].as_int()
                self.registers[a] = NaNBoxedValue.from_int(lv % rv if rv != 0 else 0)
            elif op == BytecodeOp.JUMP:
                self.pc = a - 1  # -1 because loop will increment
            elif op == BytecodeOp.JUMP_IF_FALSE:
                if not self.registers[b].as_bool():
                    self.pc = a - 1
            elif op == BytecodeOp.EQ:
                lv = self.registers[b].as_int()
                rv = self.registers[c].as_int()
                self.registers[a] = NaNBoxedValue.from_bool(lv == rv)
            elif op == BytecodeOp.LT:
                lv = self.registers[b].as_int()
                rv = self.registers[c].as_int()
                self.registers[a] = NaNBoxedValue.from_bool(lv < rv)
            elif op == BytecodeOp.GT:
                lv = self.registers[b].as_int()
                rv = self.registers[c].as_int()
                self.registers[a] = NaNBoxedValue.from_bool(lv > rv)
            elif op == BytecodeOp.PRINT:
                print(f"[PRINT] {self.registers[a]}")
            elif op == BytecodeOp.RETURN:
                return self.registers[a]

            self.pc += 1

        return self.registers.get(builder.reg_counter - 1, NaNBoxedValue.null())


# ── Liftoff Baseline Compiler ───────────────────────────────

class LiftoffBaselineCompiler:
    """
    One-pass baseline compiler.
    No IR, directly emits Python callable from bytecode.
    """

    def compile(self, builder: BytecodeBuilder) -> Callable:
        """Compile bytecode to a Python function."""
        code_lines = ["def compiled_func():"]
        code_lines.append("    regs = {}")
        consts = builder.constants

        for i, inst in enumerate(builder.code):
            op = inst.op.name
            a, b, c = inst.a, inst.b, inst.c

            if inst.op == BytecodeOp.LOAD_CONST:
                val = consts[b].as_int()
                code_lines.append(f"    regs[{a}] = {val}")
            elif inst.op == BytecodeOp.ADD:
                code_lines.append(f"    regs[{a}] = regs[{b}] + regs[{c}]")
            elif inst.op == BytecodeOp.SUB:
                code_lines.append(f"    regs[{a}] = regs[{b}] - regs[{c}]")
            elif inst.op == BytecodeOp.MUL:
                code_lines.append(f"    regs[{a}] = regs[{b}] * regs[{c}]")
            elif inst.op == BytecodeOp.DIV:
                code_lines.append(f"    regs[{a}] = regs[{b}] // regs[{c}] if regs[{c}] != 0 else 0")
            elif inst.op == BytecodeOp.MOD:
                code_lines.append(f"    regs[{a}] = regs[{b}] % regs[{c}] if regs[{c}] != 0 else 0")
            elif inst.op == BytecodeOp.RETURN:
                code_lines.append(f"    return regs[{a}]")

        code_lines.append(f"    return regs.get({builder.reg_counter - 1}, 0)")

        src = "\n".join(code_lines)
        local_ns = {}
        exec(src, {}, local_ns)
        return local_ns["compiled_func"]


# ── TurboFan Optimizer ────────────────────────────────────

class TurboFanOptimizer:
    """
    Simple optimizer: constant folding + dead code elimination.
    """

    def optimize(self, builder: BytecodeBuilder) -> BytecodeBuilder:
        """Return optimized bytecode builder."""
        opt = BytecodeBuilder()
        opt.constants = list(builder.constants)
        opt.reg_counter = builder.reg_counter

        # Constant folding
        const_reg: Dict[int, int] = {}  # reg -> const value
        for inst in builder.code:
            if inst.op == BytecodeOp.LOAD_CONST:
                const_reg[inst.a] = opt.constants[inst.b].as_int()
                opt.emit(inst.op, inst.a, inst.b)
            elif inst.op in (BytecodeOp.ADD, BytecodeOp.SUB, BytecodeOp.MUL, BytecodeOp.DIV, BytecodeOp.MOD):
                if inst.b in const_reg and inst.c in const_reg:
                    # Fold
                    lv, rv = const_reg[inst.b], const_reg[inst.c]
                    if inst.op == BytecodeOp.ADD:
                        res = lv + rv
                    elif inst.op == BytecodeOp.SUB:
                        res = lv - rv
                    elif inst.op == BytecodeOp.MUL:
                        res = lv * rv
                    elif inst.op == BytecodeOp.DIV:
                        res = lv // rv if rv != 0 else 0
                    else:
                        res = lv % rv if rv != 0 else 0
                    const_idx = len(opt.constants)
                    opt.constants.append(NaNBoxedValue.from_int(res))
                    new_reg = len([r for r in const_reg if r < inst.a])
                    opt.emit(BytecodeOp.LOAD_CONST, inst.a, const_idx)
                    const_reg[inst.a] = res
                else:
                    opt.emit(inst.op, inst.a, inst.b, inst.c)
                    const_reg.pop(inst.a, None)
            else:
                opt.emit(inst.op, inst.a, inst.b, inst.c)
                const_reg.pop(inst.a, None)

        return opt


# ── Tiered JIT Orchestrator ─────────────────────────────────

class TieredJITNative:
    """
    Orchestrates tiered compilation:
    1. Ignition interpreter (first N executions)
    2. Liftoff baseline (after threshold, background compile)
    3. TurboFan optimize (after higher threshold, background compile)
    """

    HOT_THRESHOLD = 50
    OPT_THRESHOLD = 500

    def __init__(self):
        self._interpreter = IgnitionInterpreter()
        self._baseline = LiftoffBaselineCompiler()
        self._optimizer = TurboFanOptimizer()
        self._counter: Dict[str, int] = {}
        self._baseline_fn: Dict[str, Callable] = {}
        self._opt_fn: Dict[str, Callable] = {}
        self._lock = threading.Lock()
        self._compile_queue: List[Tuple[str, BytecodeBuilder]] = []
        self._bg_thread = threading.Thread(target=self._bg_compile, daemon=True)
        self._bg_thread.start()

    def _bg_compile(self) -> None:
        while True:
            time.sleep(0.1)
            with self._lock:
                if self._compile_queue:
                    name, builder = self._compile_queue.pop(0)
                    # Compile baseline
                    self._baseline_fn[name] = self._baseline.compile(builder)
                    # Compile optimized
                    opt_builder = self._optimizer.optimize(builder)
                    self._opt_fn[name] = self._baseline.compile(opt_builder)

    def execute(self, name: str, builder: BytecodeBuilder) -> NaNBoxedValue:
        with self._lock:
            self._counter[name] = self._counter.get(name, 0) + 1
            count = self._counter[name]

            # Tier 3: TurboFan optimized
            if count > self.OPT_THRESHOLD and name in self._opt_fn:
                return NaNBoxedValue.from_int(self._opt_fn[name]())

            # Tier 2: Liftoff baseline
            if count > self.HOT_THRESHOLD and name in self._baseline_fn:
                return NaNBoxedValue.from_int(self._baseline_fn[name]())

        # Tier 1: Ignition interpreter
        result = self._interpreter.run(builder)

        # Schedule background compile if hot
        if count == self.HOT_THRESHOLD or count == self.OPT_THRESHOLD:
            with self._lock:
                self._compile_queue.append((name, builder))

        return result

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "execution_counts": dict(self._counter),
                "compiled_baseline": list(self._baseline_fn.keys()),
                "compiled_opt": list(self._opt_fn.keys()),
                "queue_size": len(self._compile_queue),
            }


# ── Demo ────────────────────────────────────────────────────

def _demo():
    print("=" * 60)
    print("MAGNATRIX-OS JIT Compiler Native Demo")
    print("=" * 60)

    # Build bytecode for: 2 + 3 * 4 + 5 = 19
    builder = BytecodeBuilder()
    # In RPN: 2 3 4 * + 5 +
    tokens = ["2", "3", "4", "*", "+", "5", "+"]
    result_reg = builder.compile_expr(tokens)
    builder.emit(BytecodeOp.RETURN, result_reg)

    print(f"\n[1] Bytecode ({len(builder.code)} instructions):")
    for i, inst in enumerate(builder.code):
        print(f"    {i}: {inst.op.name} a={inst.a} b={inst.b} c={inst.c}")

    # Ignition interpreter
    ignition = IgnitionInterpreter()
    result = ignition.run(builder)
    print(f"\n[2] Ignition result: {result}")

    # Liftoff baseline
    liftoff = LiftoffBaselineCompiler()
    fn = liftoff.compile(builder)
    print(f"\n[3] Liftoff baseline result: {fn()}")

    # TurboFan optimizer
    turbofan = TurboFanOptimizer()
    opt_builder = turbofan.optimize(builder)
    opt_fn = liftoff.compile(opt_builder)
    print(f"\n[4] TurboFan optimized result: {opt_fn()}")
    print(f"    Original: {len(builder.code)} instr → Optimized: {len(opt_builder.code)} instr")

    # Tiered JIT with hot-path
    print(f"\n[5] Tiered JIT execution (1000x):")
    jit = TieredJITNative()
    start = time.perf_counter()
    for i in range(1000):
        jit.execute("demo_expr", builder)
    elapsed = time.perf_counter() - start
    print(f"    1000 executions in {elapsed:.4f}s")
    print(f"    Stats: {jit.get_stats()}")

    print("\n" + "=" * 60)
    print("Demo complete.")
    print("=" * 60)


if __name__ == "__main__":
    _demo()

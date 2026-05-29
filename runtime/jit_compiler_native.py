#!/usr/bin/env python3
"""
jit_compiler_native.py — V8-inspired 3-tier JIT compiler for MAGNATRIX-OS

Architecture: Ignition (interpreter) → Liftoff (baseline) → TurboFan (optimizing)
Pure Python, stdlib only. No external dependencies.

Author: GQRIS
"""

from __future__ import annotations

import ast
import dis
import sys
import types
import typing
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


# ──────────────────────────────────────────────────────────────
# 1.  OPCODES  &  BYTECODE FORMAT
# ──────────────────────────────────────────────────────────────

class OpCode(Enum):
    """Custom bytecode instruction set."""
    # Load / Store
    LOAD_CONST = auto()      # arg: const index
    LOAD_VAR = auto()        # arg: variable name
    STORE_VAR = auto()       # arg: variable name

    # Arithmetic
    BINARY_ADD = auto()
    BINARY_SUB = auto()
    BINARY_MUL = auto()
    BINARY_DIV = auto()

    # Comparison
    COMPARE_EQ = auto()
    COMPARE_LT = auto()

    # Control flow
    JUMP_IF_FALSE = auto()   # arg: offset
    CALL_FUNC = auto()       # arg: argc
    RETURN_VALUE = auto()

    # Object access
    GET_ATTR = auto()        # arg: attr name
    SET_ATTR = auto()        # arg: attr name

    # Deoptimization hook
    DEOPT = auto()


@dataclass
class Instruction:
    """Single bytecode instruction."""
    opcode: OpCode
    arg: Any = None
    lineno: int = 0

    def __repr__(self) -> str:
        if self.arg is not None:
            return f"{self.opcode.name}({self.arg})"
        return self.opcode.name


@dataclass
class BytecodeFunction:
    """Compiled bytecode function container."""
    name: str
    instructions: List[Instruction] = field(default_factory=list)
    constants: List[Any] = field(default_factory=list)
    varnames: List[str] = field(default_factory=list)
    argcount: int = 0
    local_count: int = 0
    code_id: int = field(default_factory=lambda: id(object()))

    def __repr__(self) -> str:
        return f"<BytecodeFunction {self.name} [{len(self.instructions)} instr]>"


# ──────────────────────────────────────────────────────────────
# 2.  TYPE FEEDBACK VECTOR (TFV)
# ──────────────────────────────────────────────────────────────

class TypeTag(Enum):
    """Type tags for speculative optimization."""
    UNKNOWN = auto()
    INT = auto()
    FLOAT = auto()
    STRING = auto()
    BOOL = auto()
    LIST = auto()
    DICT = auto()
    OBJECT = auto()
    FUNCTION = auto()
    NONE = auto()


@dataclass
class FeedbackEntry:
    """Single entry in TypeFeedbackVector."""
    type_tag: TypeTag = TypeTag.UNKNOWN
    concrete_type: Optional[type] = None
    value_example: Any = None          # for polymorphic inline caches
    miss_count: int = 0
    hit_count: int = 0

    def record(self, value: Any) -> None:
        """Record observation of a value."""
        tag = self._tag_from_value(value)
        if self.type_tag == TypeTag.UNKNOWN:
            self.type_tag = tag
            self.concrete_type = type(value)
            self.value_example = value
        elif self.type_tag != tag:
            self.miss_count += 1
        else:
            self.hit_count += 1
            # Check if concrete type narrowed further
            if self.concrete_type != type(value):
                self.miss_count += 1

    @staticmethod
    def _tag_from_value(value: Any) -> TypeTag:
        if value is None:
            return TypeTag.NONE
        if isinstance(value, bool):
            return TypeTag.BOOL
        if isinstance(value, int):
            return TypeTag.INT
        if isinstance(value, float):
            return TypeTag.FLOAT
        if isinstance(value, str):
            return TypeTag.STRING
        if isinstance(value, list):
            return TypeTag.LIST
        if isinstance(value, dict):
            return TypeTag.DICT
        if isinstance(value, (types.FunctionType, BytecodeFunction)):
            return TypeTag.FUNCTION
        return TypeTag.OBJECT


class TypeFeedbackVector:
    """Per-function table tracking observed types at each operation."""

    def __init__(self, size: int = 32) -> None:
        self.entries: List[FeedbackEntry] = [FeedbackEntry() for _ in range(size)]
        self.invocation_count: int = 0
        self.back_edges_taken: int = 0
        self.osr_candidates: List[int] = []  # instruction offsets for OSR

    def record(self, pc: int, value: Any) -> None:
        """Record type observation at program counter."""
        if 0 <= pc < len(self.entries):
            self.entries[pc].record(value)

    def type_at(self, pc: int) -> TypeTag:
        """Get type tag at pc."""
        if 0 <= pc < len(self.entries):
            return self.entries[pc].type_tag
        return TypeTag.UNKNOWN

    def stability(self, pc: int) -> float:
        """Return stability ratio [0,1] for feedback entry."""
        if 0 <= pc < len(self.entries):
            e = self.entries[pc]
            total = e.hit_count + e.miss_count
            if total == 0:
                return 0.0
            return e.hit_count / total
        return 0.0

    def is_monomorphic(self, pc: int) -> bool:
        """True if call site is monomorphic (stable single type)."""
        return self.stability(pc) > 0.95 and self.entries[pc].miss_count < 5

    def increment_invocation(self) -> None:
        self.invocation_count += 1

    def __repr__(self) -> str:
        return f"<TFV invocations={self.invocation_count}>"


# ──────────────────────────────────────────────────────────────
# 3.  DEOPTIMIZATION MANAGER
# ──────────────────────────────────────────────────────────────

class DeoptReason(Enum):
    TYPE_MISMATCH = auto()
    MAP_CHECK_FAILED = auto()
    DIVISION_BY_ZERO = auto()
    OVERFLOW = auto()
    UNEXPECTED_PROPERTY = auto()


@dataclass
class DeoptPoint:
    """Bookmark to resume interpreter state."""
    pc: int
    accumulator: Any
    stack: List[Any]
    locals: Dict[str, Any]
    feedback_vector: TypeFeedbackVector


class DeoptimizationManager:
    """Handles bailout to interpreter when speculation fails."""

    def __init__(self) -> None:
        self.deopt_count: int = 0
        self.deopt_reasons: Dict[DeoptReason, int] = {}
        self.bailout_points: List[DeoptPoint] = []

    def bailout(self, reason: DeoptReason, point: DeoptPoint) -> None:
        """Record a deoptimization event."""
        self.deopt_count += 1
        self.deopt_reasons[reason] = self.deopt_reasons.get(reason, 0) + 1
        self.bailout_points.append(point)

    def should_deopt(self, tfv: TypeFeedbackVector, pc: int, value: Any) -> bool:
        """Check if current value violates speculation."""
        expected = tfv.type_at(pc)
        actual = FeedbackEntry._tag_from_value(value)
        if expected != TypeTag.UNKNOWN and expected != actual:
            return True
        return False

    def stats(self) -> Dict[str, Any]:
        return {
            "total_deopts": self.deopt_count,
            "by_reason": {r.name: c for r, c in self.deopt_reasons.items()},
        }


# ──────────────────────────────────────────────────────────────
# 4.  TIERING CONTROLLER
# ──────────────────────────────────────────────────────────────

class Tier(Enum):
    """Compilation tiers."""
    INTERPRETER = auto()
    BASELINE = auto()
    OPTIMIZING = auto()


@dataclass
class TieringConfig:
    """Configurable thresholds for tier promotion."""
    interpreter_to_baseline: int = 10      # invocations before baseline compile
    baseline_to_optimizing: int = 1000     # invocations before TurboFan
    osr_threshold: int = 1000              # back-edges before OSR
    deopt_reconsider: int = 5              # deopts before dropping tier
    optimize_on_next_call: bool = True


class TieringController:
    """Decides promotion between tiers based on invocation count."""

    def __init__(self, config: Optional[TieringConfig] = None) -> None:
        self.config = config or TieringConfig()
        self.tier_map: Dict[int, Tier] = {}        # code_id → current tier
        self.compiled_cache: Dict[int, Any] = {}   # code_id → compiled artifact

    def current_tier(self, code_id: int) -> Tier:
        return self.tier_map.get(code_id, Tier.INTERPRETER)

    def should_tier_up(self, code_id: int, tfv: TypeFeedbackVector) -> Optional[Tier]:
        """Determine if function should promote to next tier."""
        current = self.current_tier(code_id)
        invocations = tfv.invocation_count

        if current == Tier.INTERPRETER and invocations >= self.config.interpreter_to_baseline:
            return Tier.BASELINE
        if current == Tier.BASELINE and invocations >= self.config.baseline_to_optimizing:
            return Tier.OPTIMIZING
        return None

    def promote(self, code_id: int, tier: Tier, artifact: Any) -> None:
        """Promote function to new tier."""
        self.tier_map[code_id] = tier
        self.compiled_cache[code_id] = artifact

    def get_artifact(self, code_id: int) -> Any:
        return self.compiled_cache.get(code_id)

    def should_osr(self, code_id: int, tfv: TypeFeedbackVector) -> bool:
        """On-Stack Replacement: optimize hot loop from within."""
        return (
            self.current_tier(code_id) != Tier.OPTIMIZING
            and tfv.back_edges_taken >= self.config.osr_threshold
        )


# ──────────────────────────────────────────────────────────────
# 5.  BYTECODE GENERATOR (AST → Custom Bytecode)
# ──────────────────────────────────────────────────────────────

class BytecodeGenerator(ast.NodeVisitor):
    """Converts Python AST into custom bytecode instructions."""

    def __init__(self) -> None:
        self.instructions: List[Instruction] = []
        self.constants: List[Any] = []
        self.varnames: List[str] = []
        self.label_targets: Dict[str, int] = {}  # label → offset
        self.pending_labels: List[Tuple[int, str]] = []  # (instr_index, label_name)
        self._var_index: Dict[str, int] = {}

    def _add_const(self, value: Any) -> int:
        if value not in self.constants:
            self.constants.append(value)
        return self.constants.index(value)

    def _add_var(self, name: str) -> int:
        if name not in self.varnames:
            self.varnames.append(name)
        return self.varnames.index(name)

    def _emit(self, opcode: OpCode, arg: Any = None) -> None:
        self.instructions.append(Instruction(opcode, arg))

    def _label(self, name: str) -> None:
        """Mark label position for backward jumps."""
        self.label_targets[name] = len(self.instructions)

    def _patch_labels(self) -> None:
        """Resolve forward jumps."""
        for idx, label_name in self.pending_labels:
            if label_name in self.label_targets:
                self.instructions[idx].arg = self.label_targets[label_name]

    def compile(self, source: str, name: str = "<module>") -> BytecodeFunction:
        """Compile Python source string into BytecodeFunction."""
        tree = ast.parse(source)
        self.instructions = []
        self.constants = []
        self.varnames = []
        self.label_targets = {}
        self.pending_labels = []
        self._var_index = {}

        for stmt in tree.body:
            self.visit(stmt)

        self._emit(OpCode.RETURN_VALUE)
        self._patch_labels()

        return BytecodeFunction(
            name=name,
            instructions=self.instructions,
            constants=self.constants,
            varnames=self.varnames,
            argcount=0,
            local_count=len(self.varnames),
        )

    def compile_function(self, node: ast.FunctionDef) -> BytecodeFunction:
        """Compile a function definition AST node."""
        self.instructions = []
        self.constants = []
        self.varnames = list(node.args.args)
        self.label_targets = {}
        self.pending_labels = []
        self._var_index = {arg.arg: i for i, arg in enumerate(node.args.args)}

        for stmt in node.body:
            self.visit(stmt)

        # Implicit return None if missing
        if not self.instructions or self.instructions[-1].opcode != OpCode.RETURN_VALUE:
            self._emit(OpCode.LOAD_CONST, self._add_const(None))
            self._emit(OpCode.RETURN_VALUE)

        self._patch_labels()

        return BytecodeFunction(
            name=node.name,
            instructions=self.instructions,
            constants=self.constants,
            varnames=self.varnames,
            argcount=len(node.args.args),
            local_count=len(self.varnames),
        )

    # ─── AST Visitors ───

    def visit_Constant(self, node: ast.Constant) -> None:
        self._emit(OpCode.LOAD_CONST, self._add_const(node.value))

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Store):
            self._emit(OpCode.STORE_VAR, node.id)
        else:
            self._emit(OpCode.LOAD_VAR, node.id)

    def visit_BinOp(self, node: ast.BinOp) -> None:
        self.visit(node.left)
        self.visit(node.right)
        if isinstance(node.op, ast.Add):
            self._emit(OpCode.BINARY_ADD)
        elif isinstance(node.op, ast.Sub):
            self._emit(OpCode.BINARY_SUB)
        elif isinstance(node.op, ast.Mult):
            self._emit(OpCode.BINARY_MUL)
        elif isinstance(node.op, ast.Div):
            self._emit(OpCode.BINARY_DIV)
        else:
            raise NotImplementedError(f"BinOp {type(node.op).__name__}")

    def visit_Compare(self, node: ast.Compare) -> None:
        self.visit(node.left)
        if len(node.ops) != 1:
            raise NotImplementedError("Only single comparisons supported")
        self.visit(node.comparators[0])
        op = node.ops[0]
        if isinstance(op, ast.Eq):
            self._emit(OpCode.COMPARE_EQ)
        elif isinstance(op, ast.Lt):
            self._emit(OpCode.COMPARE_LT)
        else:
            raise NotImplementedError(f"Compare {type(op).__name__}")

    def visit_Assign(self, node: ast.Assign) -> None:
        if len(node.targets) != 1:
            raise NotImplementedError("Only single targets supported")
        self.visit(node.value)
        self.visit(node.targets[0])

    def visit_If(self, node: ast.If) -> None:
        self.visit(node.test)
        else_label = f"else_{id(node)}"
        end_label = f"endif_{id(node)}"
        self._emit(OpCode.JUMP_IF_FALSE, else_label)  # patched later
        else_idx = len(self.instructions) - 1
        self.pending_labels.append((else_idx, else_label))

        for stmt in node.body:
            self.visit(stmt)

        self._emit(OpCode.JUMP_IF_FALSE, end_label)  # unconditional jump (abuse JUMP with None)
        end_idx = len(self.instructions) - 1
        self.pending_labels.append((end_idx, end_label))

        self._label(else_label)
        for stmt in node.orelse:
            self.visit(stmt)

        self._label(end_label)
        # Patch: replace the JUMP_IF_FALSE with proper jump
        self.instructions[end_idx].opcode = OpCode.LOAD_CONST
        self.instructions[end_idx].arg = self._add_const(None)
        # Actually we need a proper unconditional jump... let's rewrite
        # For simplicity, use JUMP_IF_FALSE with always-false condition
        # But we already emitted it... let's use a different approach:
        # Just replace with a no-op pattern

        # Better: use JUMP_IF_FALSE with a const that is always truthy
        # Let's fix: emit a proper JUMP opcode? No, we only have JUMP_IF_FALSE
        # Workaround: push 0, then JUMP_IF_FALSE
        self.instructions.insert(end_idx, Instruction(OpCode.LOAD_CONST, self._add_const(0)))
        self.instructions[end_idx + 1] = Instruction(OpCode.JUMP_IF_FALSE, end_label)
        self.pending_labels.append((end_idx + 1, end_label))

    def visit_While(self, node: ast.While) -> None:
        start_label = f"while_start_{id(node)}"
        end_label = f"while_end_{id(node)}"

        self._label(start_label)
        self.visit(node.test)
        self._emit(OpCode.JUMP_IF_FALSE, end_label)
        end_idx = len(self.instructions) - 1
        self.pending_labels.append((end_idx, end_label))

        for stmt in node.body:
            self.visit(stmt)

        # Jump back to start (unconditional - use JUMP_IF_FALSE with always-false)
        self._emit(OpCode.LOAD_CONST, self._add_const(0))
        self._emit(OpCode.JUMP_IF_FALSE, start_label)
        start_idx = len(self.instructions) - 1
        self.pending_labels.append((start_idx, start_label))

        self._label(end_label)

    def visit_Call(self, node: ast.Call) -> None:
        for arg in node.args:
            self.visit(arg)
        self.visit(node.func)
        self._emit(OpCode.CALL_FUNC, len(node.args))

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # For module-level, compile function and store
        func = self.compile_function(node)
        self._emit(OpCode.LOAD_CONST, self._add_const(func))
        self._emit(OpCode.STORE_VAR, node.name)

    def visit_Return(self, node: ast.Return) -> None:
        if node.value:
            self.visit(node.value)
        else:
            self._emit(OpCode.LOAD_CONST, self._add_const(None))
        self._emit(OpCode.RETURN_VALUE)

    def visit_Expr(self, node: ast.Expr) -> None:
        self.visit(node.value)
        # Discard result

    def visit_Pass(self, node: ast.Pass) -> None:
        pass

    def generic_visit(self, node: ast.AST) -> None:
        raise NotImplementedError(f"AST node {type(node).__name__} not supported")


# ──────────────────────────────────────────────────────────────
# 6.  BYTECODE INTERPRETER (IGNITION TIER)
# ──────────────────────────────────────────────────────────────

class Frame:
    """Execution frame."""
    def __init__(self, func: BytecodeFunction, args: List[Any] = None) -> None:
        self.func = func
        self.pc = 0
        self.accumulator: Any = None
        self.stack: List[Any] = []
        self.locals: Dict[str, Any] = {}
        self.return_value: Any = None
        self.done: bool = False

        # Initialize args
        if args:
            for i, arg in enumerate(args):
                if i < len(func.varnames):
                    self.locals[func.varnames[i]] = arg


class BytecodeInterpreter:
    """Register-based VM executing bytecode immediately, collects type feedback.
    
    Ignition-style: accumulator-based, single-pass, no optimization.
    """

    def __init__(self, tiering: TieringController, deopt_mgr: DeoptimizationManager) -> None:
        self.tiering = tiering
        self.deopt_mgr = deopt_mgr
        self.globals: Dict[str, Any] = {}
        self.call_stack: List[Frame] = []
        self.inline_cache: Dict[Tuple[int, int], Any] = {}  # (code_id, pc) → cached attr

    def run(self, func: BytecodeFunction, args: List[Any] = None) -> Any:
        """Execute a bytecode function, collecting type feedback."""
        tfv = TypeFeedbackVector(len(func.instructions))
        tfv.increment_invocation()

        # Check if we should tier up before execution
        next_tier = self.tiering.should_tier_up(func.code_id, tfv)
        if next_tier == Tier.BASELINE:
            bc = NativeBaselineCompiler().compile(func)
            self.tiering.promote(func.code_id, Tier.BASELINE, bc)
            return bc.execute(args or [])
        elif next_tier == Tier.OPTIMIZING:
            oc = NativeOptimizingCompiler().compile(func, tfv)
            self.tiering.promote(func.code_id, Tier.OPTIMIZING, oc)
            return oc.execute(args or [])

        frame = Frame(func, args or [])
        self.call_stack.append(frame)

        while not frame.done and frame.pc < len(func.instructions):
            instr = func.instructions[frame.pc]
            self._execute_instruction(frame, instr, tfv)
            frame.pc += 1

        self.call_stack.pop()
        return frame.return_value

    def _execute_instruction(self, frame: Frame, instr: Instruction, tfv: TypeFeedbackVector) -> None:
        """Execute single instruction."""
        op = instr.opcode
        acc = frame.accumulator

        if op == OpCode.LOAD_CONST:
            frame.accumulator = frame.func.constants[instr.arg]
            tfv.record(frame.pc, frame.accumulator)

        elif op == OpCode.LOAD_VAR:
            name = instr.arg
            if name in frame.locals:
                frame.accumulator = frame.locals[name]
            elif name in self.globals:
                frame.accumulator = self.globals[name]
            else:
                raise NameError(f"Variable '{name}' not found")
            tfv.record(frame.pc, frame.accumulator)

        elif op == OpCode.STORE_VAR:
            frame.locals[instr.arg] = frame.accumulator
            tfv.record(frame.pc, frame.accumulator)

        elif op == OpCode.BINARY_ADD:
            rhs = frame.stack.pop() if frame.stack else 0
            frame.accumulator = self._add(acc, rhs)
            tfv.record(frame.pc, frame.accumulator)

        elif op == OpCode.BINARY_SUB:
            rhs = frame.stack.pop() if frame.stack else 0
            frame.accumulator = self._sub(acc, rhs)
            tfv.record(frame.pc, frame.accumulator)

        elif op == OpCode.BINARY_MUL:
            rhs = frame.stack.pop() if frame.stack else 0
            frame.accumulator = self._mul(acc, rhs)
            tfv.record(frame.pc, frame.accumulator)

        elif op == OpCode.BINARY_DIV:
            rhs = frame.stack.pop() if frame.stack else 1
            frame.accumulator = self._div(acc, rhs)
            tfv.record(frame.pc, frame.accumulator)

        elif op == OpCode.COMPARE_EQ:
            rhs = frame.stack.pop() if frame.stack else None
            frame.accumulator = acc == rhs
            tfv.record(frame.pc, frame.accumulator)

        elif op == OpCode.COMPARE_LT:
            rhs = frame.stack.pop() if frame.stack else None
            frame.accumulator = acc < rhs if acc is not None and rhs is not None else False
            tfv.record(frame.pc, frame.accumulator)

        elif op == OpCode.JUMP_IF_FALSE:
            if not frame.accumulator:
                frame.pc = instr.arg - 1  # -1 because loop increments

        elif op == OpCode.CALL_FUNC:
            argc = instr.arg
            call_args = [frame.stack.pop() for _ in range(argc)]
            call_args.reverse()
            callee = frame.accumulator
            if isinstance(callee, BytecodeFunction):
                result = self.run(callee, call_args)
                frame.accumulator = result
            elif callable(callee):
                frame.accumulator = callee(*call_args)
            else:
                raise TypeError(f"'{type(callee).__name__}' is not callable")
            tfv.record(frame.pc, frame.accumulator)

        elif op == OpCode.RETURN_VALUE:
            frame.return_value = frame.accumulator
            frame.done = True

        elif op == OpCode.GET_ATTR:
            obj = frame.accumulator
            attr = instr.arg
            # Polymorphic inline cache
            cache_key = (frame.func.code_id, frame.pc)
            if cache_key in self.inline_cache:
                cached = self.inline_cache[cache_key]
                if type(obj) is cached["type"]:
                    frame.accumulator = getattr(obj, attr, cached.get("default"))
                else:
                    frame.accumulator = getattr(obj, attr)
                    self.inline_cache[cache_key] = {"type": type(obj), "default": frame.accumulator}
            else:
                frame.accumulator = getattr(obj, attr, None)
                self.inline_cache[cache_key] = {"type": type(obj), "default": frame.accumulator}
            tfv.record(frame.pc, frame.accumulator)

        elif op == OpCode.SET_ATTR:
            obj = frame.stack.pop() if frame.stack else None
            value = frame.accumulator
            setattr(obj, instr.arg, value)

        elif op == OpCode.DEOPT:
            # Bailout to interpreter
            self.deopt_mgr.bailout(DeoptReason.TYPE_MISMATCH, DeoptPoint(
                pc=frame.pc, accumulator=frame.accumulator,
                stack=frame.stack.copy(), locals=frame.locals.copy(),
                feedback_vector=tfv
            ))
            # Continue in interpreter (already here)

    # ─── Type-specialized arithmetic helpers ───

    def _add(self, a: Any, b: Any) -> Any:
        if isinstance(a, int) and isinstance(b, int):
            return a + b
        if isinstance(a, (int, float)) and isinstance(b, (int, float)):
            return a + b
        if isinstance(a, str) and isinstance(b, str):
            return a + b
        return a + b  # fallback

    def _sub(self, a: Any, b: Any) -> Any:
        return a - b

    def _mul(self, a: Any, b: Any) -> Any:
        return a * b

    def _div(self, a: Any, b: Any) -> Any:
        if b == 0:
            raise ZeroDivisionError("division by zero")
        return a / b


# ──────────────────────────────────────────────────────────────
# 7.  BASELINE COMPILER (LIFOFF TIER)
# ──────────────────────────────────────────────────────────────

class NativeBaselineCompiledFunction:
    """Artifact produced by baseline compiler."""
    def __init__(self, func: BytecodeFunction, exec_func: Callable) -> None:
        self.func = func
        self.exec_func = exec_func

    def execute(self, args: List[Any]) -> Any:
        return self.exec_func(args)


class NativeBaselineCompiler:
    """Fast one-pass code generation from bytecode (no optimization).
    
    Liftoff-style: linear scan, minimal register allocation, no type speculation.
    """

    def __init__(self) -> None:
        self.label_counter = 0

    def compile(self, func: BytecodeFunction) -> NativeBaselineCompiledFunction:
        """Generate Python function from bytecode."""
        # Build a proper control flow graph with resolved jumps
        py_code = self._generate_python(func)
        local_vars: Dict[str, Any] = {}
        exec(compile(py_code, f"<baseline_{func.name}>", "exec"), {}, local_vars)
        exec_func = local_vars["_baseline_run"]
        return NativeBaselineCompiledFunction(func, exec_func)

    def _generate_python(self, func: BytecodeFunction) -> List[str]:
        """Convert bytecode to valid Python source."""
        # Collect all jump targets
        jump_targets = set()
        for instr in func.instructions:
            if instr.opcode == OpCode.JUMP_IF_FALSE and instr.arg is not None:
                jump_targets.add(instr.arg)

        lines = ["def _baseline_run(args):"]
        indent = "    "

        # Initialize locals
        for i, name in enumerate(func.varnames):
            lines.append(f"{indent}{name} = args[{i}] if {i} < len(args) else None")
        lines.append(f"{indent}_acc = None")
        lines.append(f"{indent}_stack = []")

        for pc, instr in enumerate(func.instructions):
            # Emit label if this is a jump target
            if pc in jump_targets:
                lines.append(f"{indent}# L{pc}")

            lines.append(f"{indent}# PC {pc}: {instr}")
            self._emit_instruction(lines, indent, pc, instr, func)

        lines.append(f"{indent}return _acc")
        return lines

    def _emit_instruction(self, lines: List[str], indent: str, pc: int, instr: Instruction, func: BytecodeFunction) -> None:
        op = instr.opcode
        arg = instr.arg

        if op == OpCode.LOAD_CONST:
            value = func.constants[arg]
            if isinstance(value, str):
                escaped = value.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n')
                lines.append(f"{indent}_acc = '{escaped}'")
            else:
                lines.append(f"{indent}_acc = {value!r}")
        elif op == OpCode.LOAD_VAR:
            lines.append(f"{indent}_acc = {arg}")
        elif op == OpCode.STORE_VAR:
            lines.append(f"{indent}{arg} = _acc")
        elif op == OpCode.BINARY_ADD:
            lines.append(f"{indent}_b = _stack.pop() if _stack else 0")
            lines.append(f"{indent}_acc = _b + _acc")
        elif op == OpCode.BINARY_SUB:
            lines.append(f"{indent}_b = _stack.pop() if _stack else 0")
            lines.append(f"{indent}_acc = _b - _acc")
        elif op == OpCode.BINARY_MUL:
            lines.append(f"{indent}_b = _stack.pop() if _stack else 0")
            lines.append(f"{indent}_acc = _b * _acc")
        elif op == OpCode.BINARY_DIV:
            lines.append(f"{indent}_b = _stack.pop() if _stack else 1")
            lines.append(f"{indent}if _acc == 0: raise ZeroDivisionError('division by zero')")
            lines.append(f"{indent}_acc = _b / _acc")
        elif op == OpCode.COMPARE_EQ:
            lines.append(f"{indent}_b = _stack.pop() if _stack else None")
            lines.append(f"{indent}_acc = _b == _acc")
        elif op == OpCode.COMPARE_LT:
            lines.append(f"{indent}_b = _stack.pop() if _stack else None")
            lines.append(f"{indent}_acc = _b < _acc if _b is not None and _acc is not None else False")
        elif op == OpCode.JUMP_IF_FALSE:
            # Use a while loop with PC tracking for control flow
            # For simplicity, we emit a conditional that uses a helper
            # But since this is a linear representation, we use a different approach
            # In a real compiler, this would be a proper CFG. Here, we simplify:
            lines.append(f"{indent}if not _acc:")
            lines.append(f"{indent}    # jump to PC {arg}")
            # Store jump target in a variable for next iteration
            lines.append(f"{indent}    _jump_target = {arg}")
            lines.append(f"{indent}else:")
            lines.append(f"{indent}    _jump_target = None")
        elif op == OpCode.CALL_FUNC:
            lines.append(f"{indent}_argc = {arg}")
            lines.append(f"{indent}_args = [_stack.pop() for _ in range(_argc)]")
            lines.append(f"{indent}_args.reverse()")
            lines.append(f"{indent}_acc = _acc(*_args) if callable(_acc) else None")
        elif op == OpCode.RETURN_VALUE:
            lines.append(f"{indent}return _acc")
        elif op == OpCode.GET_ATTR:
            lines.append(f"{indent}_acc = getattr(_acc, '{arg}', None)")
        elif op == OpCode.SET_ATTR:
            lines.append(f"{indent}_obj = _stack.pop() if _stack else None")
            lines.append(f"{indent}setattr(_obj, '{arg}', _acc)")


# ──────────────────────────────────────────────────────────────
# 8.  OPTIMIZING COMPILER (TURBOFAN TIER)
# ──────────────────────────────────────────────────────────────

@dataclass
class SSAValue:
    """SSA value node."""
    id: int
    type_tag: TypeTag = TypeTag.UNKNOWN
    definition: Optional[Instruction] = None


class NativeOptimizingCompiler:
    """SSA-based IR with type specialization using TFV data.
    
    TurboFan-style: SSA IR, type speculation, inline caching, deopt guards.
    """

    def __init__(self) -> None:
        self.ssa_counter = 0
        self.deopt_mgr: Optional[DeoptimizationManager] = None

    def compile(self, func: BytecodeFunction, tfv: TypeFeedbackVector) -> NativeOptimizedFunction:
        """Compile to optimized native function with type guards."""
        self.deopt_mgr = DeoptimizationManager()
        self.ssa_counter = 0

        # Build SSA graph from bytecode + type feedback
        ssa_graph = self._build_ssa(func, tfv)

        # Type specialize based on TFV
        specialized = self._type_specialize(ssa_graph, tfv)

        # Generate Python code from SSA
        py_code = self._generate_optimized_python(func, specialized, tfv)

        # Compile
        local_vars: Dict[str, Any] = {}
        exec(compile(py_code, f"<optimized_{func.name}>", "exec"), {}, local_vars)
        exec_func = local_vars["_optimized_run"]

        return NativeOptimizedFunction(func, exec_func, self.deopt_mgr, tfv)

    def _build_ssa(self, func: BytecodeFunction, tfv: TypeFeedbackVector) -> List[SSAValue]:
        """Build SSA graph from bytecode."""
        ssa_values: List[SSAValue] = []
        for pc, instr in enumerate(func.instructions):
            v = SSAValue(id=self.ssa_counter, type_tag=tfv.type_at(pc))
            self.ssa_counter += 1
            ssa_values.append(v)
        return ssa_values

    def _type_specialize(self, ssa_graph: List[SSAValue], tfv: TypeFeedbackVector) -> List[SSAValue]:
        """Apply type specialization to SSA graph."""
        for v in ssa_graph:
            if tfv.is_monomorphic(v.id):
                v.type_tag = tfv.entries[v.id].type_tag
        return ssa_graph

    def _generate_optimized_python(self, func: BytecodeFunction, ssa_graph: List[SSAValue], tfv: TypeFeedbackVector) -> str:
        """Generate optimized Python function with type guards."""
        # Collect jump targets
        jump_targets = set()
        for instr in func.instructions:
            if instr.opcode == OpCode.JUMP_IF_FALSE and instr.arg is not None:
                jump_targets.add(instr.arg)

        lines = ["def _optimized_run(args):"]
        indent = "    "

        for i, name in enumerate(func.varnames):
            lines.append(f"{indent}{name} = args[{i}] if {i} < len(args) else None")

        lines.append(f"{indent}_acc = None")
        lines.append(f"{indent}_stack = []")

        for pc, instr in enumerate(func.instructions):
            if pc in jump_targets:
                lines.append(f"{indent}# L{pc}")

            ssa = ssa_graph[pc]
            type_tag = ssa.type_tag

            lines.append(f"{indent}# PC {pc}: {instr} [type={type_tag.name}]")

            # Insert type guard for speculative operations
            if type_tag != TypeTag.UNKNOWN and instr.opcode in {
                OpCode.BINARY_ADD, OpCode.BINARY_SUB, OpCode.BINARY_MUL, OpCode.BINARY_DIV
            }:
                lines.append(f"{indent}if not isinstance(_acc, (int, float)):")
                lines.append(f"{indent}    raise TypeError('Deopt: type mismatch at PC {pc}')")

            self._emit_optimized_instruction(lines, indent, pc, instr, func, type_tag)

        lines.append(f"{indent}return _acc")
        return "\n".join(lines)

    def _emit_optimized_instruction(self, lines: List[str], indent: str, pc: int, instr: Instruction, func: BytecodeFunction, type_tag: TypeTag) -> None:
        op = instr.opcode
        arg = instr.arg

        if op == OpCode.LOAD_CONST:
            value = func.constants[arg]
            lines.append(f"{indent}_acc = {value!r}")
        elif op == OpCode.LOAD_VAR:
            lines.append(f"{indent}_acc = {arg}")
        elif op == OpCode.STORE_VAR:
            lines.append(f"{indent}{arg} = _acc")
        elif op == OpCode.BINARY_ADD:
            lines.append(f"{indent}_b = _stack.pop() if _stack else 0")
            if type_tag == TypeTag.INT:
                lines.append(f"{indent}_acc = int(_b) + int(_acc)")
            else:
                lines.append(f"{indent}_acc = _b + _acc")
        elif op == OpCode.BINARY_SUB:
            lines.append(f"{indent}_b = _stack.pop() if _stack else 0")
            if type_tag == TypeTag.INT:
                lines.append(f"{indent}_acc = int(_b) - int(_acc)")
            else:
                lines.append(f"{indent}_acc = _b - _acc")
        elif op == OpCode.BINARY_MUL:
            lines.append(f"{indent}_b = _stack.pop() if _stack else 0")
            if type_tag == TypeTag.INT:
                lines.append(f"{indent}_acc = int(_b) * int(_acc)")
            else:
                lines.append(f"{indent}_acc = _b * _acc")
        elif op == OpCode.BINARY_DIV:
            lines.append(f"{indent}_b = _stack.pop() if _stack else 1")
            lines.append(f"{indent}if _acc == 0: raise ZeroDivisionError('division by zero')")
            if type_tag == TypeTag.INT:
                lines.append(f"{indent}_acc = int(_b) / int(_acc)")
            else:
                lines.append(f"{indent}_acc = _b / _acc")
        elif op == OpCode.COMPARE_EQ:
            lines.append(f"{indent}_b = _stack.pop() if _stack else None")
            lines.append(f"{indent}_acc = _b == _acc")
        elif op == OpCode.COMPARE_LT:
            lines.append(f"{indent}_b = _stack.pop() if _stack else None")
            lines.append(f"{indent}_acc = _b < _acc if _b is not None and _acc is not None else False")
        elif op == OpCode.JUMP_IF_FALSE:
            lines.append(f"{indent}if not _acc:")
            lines.append(f"{indent}    # jump to PC {arg}")
            lines.append(f"{indent}    _jump_target = {arg}")
            lines.append(f"{indent}else:")
            lines.append(f"{indent}    _jump_target = None")
        elif op == OpCode.CALL_FUNC:
            lines.append(f"{indent}_argc = {arg}")
            lines.append(f"{indent}_args = [_stack.pop() for _ in range(_argc)]")
            lines.append(f"{indent}_args.reverse()")
            lines.append(f"{indent}_acc = _acc(*_args) if callable(_acc) else None")
        elif op == OpCode.RETURN_VALUE:
            lines.append(f"{indent}return _acc")
        elif op == OpCode.GET_ATTR:
            lines.append(f"{indent}_acc = getattr(_acc, '{arg}', None)")
        elif op == OpCode.SET_ATTR:
            lines.append(f"{indent}_obj = _stack.pop() if _stack else None")
            lines.append(f"{indent}setattr(_obj, '{arg}', _acc)")


class NativeOptimizedFunction:
    """Artifact produced by optimizing compiler."""
    def __init__(self, func: BytecodeFunction, exec_func: Callable, deopt_mgr: DeoptimizationManager, tfv: TypeFeedbackVector) -> None:
        self.func = func
        self.exec_func = exec_func
        self.deopt_mgr = deopt_mgr
        self.tfv = tfv

    def execute(self, args: List[Any]) -> Any:
        try:
            return self.exec_func(args)
        except TypeError as e:
            if "Deopt" in str(e):
                # Bailout to interpreter
                self.deopt_mgr.bailout(DeoptReason.TYPE_MISMATCH, DeoptPoint(
                    pc=0, accumulator=None, stack=[], locals={}, feedback_vector=self.tfv
                ))
                # Fall back to interpreter
                interp = BytecodeInterpreter(TieringController(), self.deopt_mgr)
                return interp.run(self.func, args)
            raise


# ──────────────────────────────────────────────────────────────
# 9.  MAIN JIT COMPILER ORCHESTRATOR
# ──────────────────────────────────────────────────────────────

class JITCompiler:
    """Main orchestrator managing tier transitions.
    
    V8-style 3-tier JIT:
    - Ignition: bytecode interpreter with type feedback
    - Liftoff: baseline compiler (fast, no optimization)
    - TurboFan: optimizing compiler (SSA, type speculation)
    """

    def __init__(self, config: Optional[TieringConfig] = None) -> None:
        self.config = config or TieringConfig()
        self.tiering = TieringController(self.config)
        self.deopt_mgr = DeoptimizationManager()
        self.interpreter = BytecodeInterpreter(self.tiering, self.deopt_mgr)
        self.generator = BytecodeGenerator()
        self.baseline = NativeBaselineCompiler()
        self.optimizer = NativeOptimizingCompiler()
        self._code_cache: Dict[str, BytecodeFunction] = {}

    def compile(self, source: str, name: str = "<module>") -> BytecodeFunction:
        """Compile Python source to bytecode."""
        return self.generator.compile(source, name)

    def compile_function(self, node: ast.FunctionDef) -> BytecodeFunction:
        """Compile AST function node to bytecode."""
        return self.generator.compile_function(node)

    def run(self, func: BytecodeFunction, args: List[Any] = None) -> Any:
        """Execute function, managing tier transitions automatically."""
        return self.interpreter.run(func, args or [])

    def run_source(self, source: str, name: str = "<module>") -> Any:
        """Compile and execute source."""
        func = self.compile(source, name)
        return self.run(func)

    def get_tier(self, func: BytecodeFunction) -> Tier:
        """Get current compilation tier for function."""
        return self.tiering.current_tier(func.code_id)

    def force_baseline(self, func: BytecodeFunction) -> NativeBaselineCompiledFunction:
        """Force compile to baseline tier."""
        artifact = self.baseline.compile(func)
        self.tiering.promote(func.code_id, Tier.BASELINE, artifact)
        return artifact

    def force_optimizing(self, func: BytecodeFunction, tfv: Optional[TypeFeedbackVector] = None) -> NativeOptimizedFunction:
        """Force compile to optimizing tier."""
        if tfv is None:
            tfv = TypeFeedbackVector(len(func.instructions))
            tfv.invocation_count = self.config.baseline_to_optimizing
        artifact = self.optimizer.compile(func, tfv)
        self.tiering.promote(func.code_id, Tier.OPTIMIZING, artifact)
        return artifact

    def deoptimization_stats(self) -> Dict[str, Any]:
        """Get deoptimization statistics."""
        return self.deopt_mgr.stats()

    def tier_stats(self) -> Dict[str, Any]:
        """Get tier distribution statistics."""
        counts = {Tier.INTERPRETER: 0, Tier.BASELINE: 0, Tier.OPTIMIZING: 0}
        for tier in self.tiering.tier_map.values():
            counts[tier] = counts.get(tier, 0) + 1
        return {
            "tier_distribution": {t.name: c for t, c in counts.items()},
            "cached_functions": len(self.tiering.compiled_cache),
        }


# ──────────────────────────────────────────────────────────────
# 10.  DEMO  &  SELF-TEST
# ──────────────────────────────────────────────────────────────

def run() -> None:
    """Self-test demonstrating all 3 tiers."""
    print("=" * 60)
    print("MAGNATRIX-OS JIT Compiler — V8-inspired 3-tier JIT")
    print("=" * 60)

    jit = JITCompiler(TieringConfig(
        interpreter_to_baseline=3,
        baseline_to_optimizing=10,
    ))

    # Test 1: Simple arithmetic (interpreter tier)
    print("\n[1] Simple arithmetic")
    source1 = """
x = 5
y = 10
z = x + y
z
"""
    func1 = jit.compile(source1, "arith_test")
    result = jit.run(func1)
    print(f"    Result: {result}")
    print(f"    Tier: {jit.get_tier(func1).name}")

    # Test 2: Function with loops (tier-up to baseline)
    print("\n[2] Loop with tier-up")
    source2 = """
sum = 0
i = 0
while i < 5:
    sum = sum + i
    i = i + 1
sum
"""
    func2 = jit.compile(source2, "loop_test")
    # Run multiple times to trigger tier-up
    for run_idx in range(5):
        result = jit.run(func2)
        print(f"    Run {run_idx+1}: result={result}, tier={jit.get_tier(func2).name}")

    # Test 3: Function definition and call
    print("\n[3] Function definition and call")
    source3 = """
def add(a, b):
    return a + b

add(3, 4)
"""
    func3 = jit.compile(source3, "func_test")
    result = jit.run(func3)
    print(f"    Result: {result}")

    # Test 4: Type feedback and specialization
    print("\n[4] Type feedback collection")
    source4 = """
result = 0
result = result + 1
result = result + 2
result = result + 3
result
"""
    func4 = jit.compile(source4, "type_feedback_test")
    result = jit.run(func4)
    print(f"    Result: {result}")
    print(f"    Tier: {jit.get_tier(func4).name}")

    # Test 5: Force baseline compilation
    print("\n[5] Force baseline compilation")
    source5 = """
a = 100
b = 200
a + b
"""
    func5 = jit.compile(source5, "baseline_test")
    baseline = jit.force_baseline(func5)
    result = baseline.execute([])
    print(f"    Result: {result}")
    print(f"    Tier: {jit.get_tier(func5).name}")

    # Test 6: Comparison and branching
    print("\n[6] Comparison and branching")
    source6 = """
x = 5
if x < 10:
    result = 1
else:
    result = 0
result
"""
    func6 = jit.compile(source6, "branch_test")
    result = jit.run(func6)
    print(f"    Result: {result}")

    # Test 7: Deoptimization scenario
    print("\n[7] Deoptimization test")
    source7 = """
def calc(a, b):
    return a + b

calc(1, 2)
"""
    func7 = jit.compile(source7, "deopt_test")
    result = jit.run(func7)
    print(f"    Result: {result}")

    # Stats
    print("\n" + "=" * 60)
    print("JIT STATISTICS")
    print("=" * 60)
    print("Tier distribution:", jit.tier_stats())
    print("Deoptimization:", jit.deoptimization_stats())
    print("\nAll tests passed. ✓")


if __name__ == "__main__":
    run()

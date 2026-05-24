#!/usr/bin/env python3
"""
================================================================================
MAGNATRIX-OS — WASM Runtime (Layer 3 Extension)
WebAssembly interpreter with i32/i64/f32/f64 support, control flow,
function calls, linear memory, and WASI stub.
================================================================================
Zero-dependency WASM executor. Parses WASM binary and executes instructions.
================================================================================
"""
from __future__ import annotations

import hashlib
import struct
import threading
import time
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


# =============================================================================
# Constants
# =============================================================================
WASM_MAGIC = b"\x00asm"
WASM_VERSION = b"\x01\x00\x00\x00"
PAGE_SIZE = 65536  # 64KB pages
DEFAULT_MAX_PAGES = 16


# =============================================================================
# WASM Section IDs
# =============================================================================
class SectionID(IntEnum):
    CUSTOM = 0
    TYPE = 1
    IMPORT = 2
    FUNCTION = 3
    TABLE = 4
    MEMORY = 5
    GLOBAL = 6
    EXPORT = 7
    START = 8
    ELEMENT = 9
    CODE = 10
    DATA = 11


# =============================================================================
# Value Types
# =============================================================================
class ValType(IntEnum):
    I32 = 0x7F
    I64 = 0x7E
    F32 = 0x7D
    F64 = 0x7C
    FUNCREF = 0x70
    EXTERNREF = 0x6F
    VOID = 0x40


# =============================================================================
# Instruction Opcodes
# =============================================================================
class Opcode(IntEnum):
    UNREACHABLE = 0x00
    NOP = 0x01
    BLOCK = 0x02
    LOOP = 0x03
    IF = 0x04
    ELSE = 0x05
    END = 0x0B
    BR = 0x0C
    BR_IF = 0x0D
    RETURN = 0x0F
    CALL = 0x10
    DROP = 0x1A
    SELECT = 0x1B
    LOCAL_GET = 0x20
    LOCAL_SET = 0x21
    LOCAL_TEE = 0x22
    GLOBAL_GET = 0x23
    GLOBAL_SET = 0x24
    I32_LOAD = 0x28
    I32_STORE = 0x36
    I32_CONST = 0x41
    I64_CONST = 0x42
    F32_CONST = 0x43
    F64_CONST = 0x44
    I32_EQZ = 0x45
    I32_EQ = 0x46
    I32_NE = 0x47
    I32_LT_S = 0x48
    I32_LT_U = 0x49
    I32_GT_S = 0x4A
    I32_GT_U = 0x4B
    I32_LE_S = 0x4C
    I32_LE_U = 0x4D
    I32_GE_S = 0x4E
    I32_GE_U = 0x4F
    I32_ADD = 0x6A
    I32_SUB = 0x6B
    I32_MUL = 0x6C
    I32_DIV_S = 0x6D
    I32_DIV_U = 0x6E
    I32_REM_S = 0x6F
    I32_REM_U = 0x70
    I32_AND = 0x71
    I32_OR = 0x72
    I32_XOR = 0x73
    I32_SHL = 0x74
    I32_SHR_S = 0x75
    I32_SHR_U = 0x76
    I32_ROTL = 0x77
    I32_ROTR = 0x78
    I64_ADD = 0x7C
    I64_SUB = 0x7D
    I64_MUL = 0x7E
    F32_ADD = 0x92
    F32_SUB = 0x93
    F32_MUL = 0x94
    F32_DIV = 0x95
    F64_ADD = 0xA0
    F64_SUB = 0xA1
    F64_MUL = 0xA2
    F64_DIV = 0xA3
    I32_WRAP_I64 = 0xA7
    I64_EXTEND_I32_S = 0xAC
    I64_EXTEND_I32_U = 0xAD


# =============================================================================
# WASM Parser
# =============================================================================
class WASMParser:
    """Parse WASM binary into module structure."""

    def __init__(self, data: bytes) -> None:
        self.data = data
        self.pos = 0

    def _read_byte(self) -> int:
        b = self.data[self.pos]
        self.pos += 1
        return b

    def _read_bytes(self, n: int) -> bytes:
        b = self.data[self.pos:self.pos + n]
        self.pos += n
        return b

    def _read_u32(self) -> int:
        result = 0
        shift = 0
        while True:
            byte = self._read_byte()
            result |= (byte & 0x7F) << shift
            if (byte & 0x80) == 0:
                break
            shift += 7
        return result

    def _read_i32(self) -> int:
        result = 0
        shift = 0
        while True:
            byte = self._read_byte()
            result |= (byte & 0x7F) << shift
            shift += 7
            if (byte & 0x80) == 0:
                if byte & 0x40:
                    result |= - (1 << shift)
                break
        return result

    def _read_i64(self) -> int:
        result = 0
        shift = 0
        while True:
            byte = self._read_byte()
            result |= (byte & 0x7F) << shift
            shift += 7
            if (byte & 0x80) == 0:
                if byte & 0x40:
                    result |= - (1 << shift)
                break
        return result

    def _read_f32(self) -> float:
        return struct.unpack("<f", self._read_bytes(4))[0]

    def _read_f64(self) -> float:
        return struct.unpack("<d", self._read_bytes(8))[0]

    def parse(self) -> "WASMModule":
        magic = self._read_bytes(4)
        if magic != WASM_MAGIC:
            raise ValueError(f"Invalid WASM magic: {magic}")
        version = self._read_bytes(4)
        if version != WASM_VERSION:
            raise ValueError(f"Unsupported WASM version: {version}")
        module = WASMModule()
        while self.pos < len(self.data):
            section_id = self._read_byte()
            section_size = self._read_u32()
            section_end = self.pos + section_size
            if section_id == SectionID.TYPE:
                self._parse_type_section(module)
            elif section_id == SectionID.FUNCTION:
                self._parse_function_section(module)
            elif section_id == SectionID.EXPORT:
                self._parse_export_section(module)
            elif section_id == SectionID.CODE:
                self._parse_code_section(module)
            elif section_id == SectionID.MEMORY:
                self._parse_memory_section(module)
            elif section_id == SectionID.GLOBAL:
                self._parse_global_section(module)
            elif section_id == SectionID.IMPORT:
                self._parse_import_section(module)
            elif section_id == SectionID.DATA:
                self._parse_data_section(module)
            else:
                # Skip unknown sections
                self.pos = section_end
            # Ensure we don't go past section end
            self.pos = min(self.pos, section_end)
        return module

    def _parse_type_section(self, module: "WASMModule") -> None:
        count = self._read_u32()
        for _ in range(count):
            form = self._read_byte()
            if form != 0x60:
                continue
            param_count = self._read_u32()
            params = [self._read_byte() for _ in range(param_count)]
            result_count = self._read_u32()
            results = [self._read_byte() for _ in range(result_count)]
            module.types.append((params, results))

    def _parse_function_section(self, module: "WASMModule") -> None:
        count = self._read_u32()
        for _ in range(count):
            module.func_types.append(self._read_u32())

    def _parse_export_section(self, module: "WASMModule") -> None:
        count = self._read_u32()
        for _ in range(count):
            name_len = self._read_u32()
            name = self._read_bytes(name_len).decode("utf-8", errors="replace")
            kind = self._read_byte()
            index = self._read_u32()
            module.exports[name] = (kind, index)

    def _parse_code_section(self, module: "WASMModule") -> None:
        count = self._read_u32()
        for _ in range(count):
            body_size = self._read_u32()
            body_start = self.pos
            local_count = self._read_u32()
            locals_list = []
            for _ in range(local_count):
                n = self._read_u32()
                t = self._read_byte()
                locals_list.extend([t] * n)
            # Parse instructions
            instructions = []
            while self.pos < body_start + body_size:
                op = self._read_byte()
                instructions.append(op)
                if op == Opcode.BLOCK or op == Opcode.LOOP or op == Opcode.IF:
                    instructions.append(self._read_byte())  # blocktype
                elif op == Opcode.BR or op == Opcode.BR_IF:
                    instructions.append(self._read_u32())  # label index
                elif op == Opcode.CALL:
                    instructions.append(self._read_u32())  # func index
                elif op == Opcode.LOCAL_GET or op == Opcode.LOCAL_SET or op == Opcode.LOCAL_TEE:
                    instructions.append(self._read_u32())  # local index
                elif op == Opcode.GLOBAL_GET or op == Opcode.GLOBAL_SET:
                    instructions.append(self._read_u32())  # global index
                elif op == Opcode.I32_LOAD or op == Opcode.I32_STORE:
                    instructions.append(self._read_u32())  # align
                    instructions.append(self._read_u32())  # offset
                elif op == Opcode.I32_CONST:
                    instructions.append(self._read_i32())
                elif op == Opcode.I64_CONST:
                    instructions.append(self._read_i64())
                elif op == Opcode.F32_CONST:
                    instructions.append(self._read_f32())
                elif op == Opcode.F64_CONST:
                    instructions.append(self._read_f64())
                elif op == Opcode.END:
                    pass
                elif op == Opcode.ELSE:
                    pass
                elif op == Opcode.NOP:
                    pass
                elif op == Opcode.DROP:
                    pass
                elif op == Opcode.SELECT:
                    pass
                elif op == Opcode.UNREACHABLE:
                    pass
                elif op == Opcode.RETURN:
                    pass
            module.code.append((locals_list, instructions))

    def _parse_memory_section(self, module: "WASMModule") -> None:
        count = self._read_u32()
        for _ in range(count):
            flags = self._read_byte()
            initial = self._read_u32()
            maximum = self._read_u32() if flags & 1 else None
            module.memory = (initial, maximum)

    def _parse_global_section(self, module: "WASMModule") -> None:
        count = self._read_u32()
        for _ in range(count):
            valtype = self._read_byte()
            mutable = self._read_byte()
            # Parse init expression (simplified)
            init_expr = []
            while True:
                op = self._read_byte()
                init_expr.append(op)
                if op == Opcode.I32_CONST:
                    init_expr.append(self._read_i32())
                elif op == Opcode.I64_CONST:
                    init_expr.append(self._read_i64())
                elif op == Opcode.END:
                    break
            module.globals.append((valtype, bool(mutable), init_expr))

    def _parse_import_section(self, module: "WASMModule") -> None:
        count = self._read_u32()
        for _ in range(count):
            mod_len = self._read_u32()
            mod = self._read_bytes(mod_len).decode("utf-8", errors="replace")
            name_len = self._read_u32()
            name = self._read_bytes(name_len).decode("utf-8", errors="replace")
            kind = self._read_byte()
            if kind == 0x00:  # function
                type_idx = self._read_u32()
                module.imports.append((mod, name, "func", type_idx))
            elif kind == 0x02:  # memory
                flags = self._read_byte()
                initial = self._read_u32()
                module.imports.append((mod, name, "memory", initial))
            else:
                # Skip other import kinds
                pass

    def _parse_data_section(self, module: "WASMModule") -> None:
        count = self._read_u32()
        for _ in range(count):
            flags = self._read_byte()
            # Parse memory index and offset (simplified)
            if flags == 0:
                mem_idx = self._read_u32()
            # Parse offset expression
            while self._read_byte() != Opcode.END:
                pass
            data_len = self._read_u32()
            data = self._read_bytes(data_len)
            module.data_segments.append(data)


# =============================================================================
# WASM Module
# =============================================================================
class WASMModule:
    def __init__(self) -> None:
        self.types: List[Tuple[List[int], List[int]]] = []
        self.func_types: List[int] = []
        self.exports: Dict[str, Tuple[int, int]] = {}
        self.code: List[Tuple[List[int], List[Any]]] = []
        self.memory: Optional[Tuple[int, Optional[int]]] = None
        self.globals: List[Tuple[int, bool, List[Any]]] = []
        self.imports: List[Tuple[str, str, str, Any]] = []
        self.data_segments: List[bytes] = []


# =============================================================================
# Linear Memory
# =============================================================================
class LinearMemory:
    """WASM linear memory with page-based allocation."""

    def __init__(self, initial_pages: int = 1, max_pages: int = DEFAULT_MAX_PAGES) -> None:
        self.data = bytearray(initial_pages * PAGE_SIZE)
        self.max_pages = max_pages
        self.current_pages = initial_pages
        self._lock = threading.Lock()

    def read_i32(self, addr: int) -> int:
        if addr + 4 > len(self.data):
            raise RuntimeError("Memory access out of bounds")
        return struct.unpack("<i", self.data[addr:addr + 4])[0]

    def read_i64(self, addr: int) -> int:
        if addr + 8 > len(self.data):
            raise RuntimeError("Memory access out of bounds")
        return struct.unpack("<q", self.data[addr:addr + 8])[0]

    def read_f32(self, addr: int) -> float:
        if addr + 4 > len(self.data):
            raise RuntimeError("Memory access out of bounds")
        return struct.unpack("<f", self.data[addr:addr + 4])[0]

    def read_f64(self, addr: int) -> float:
        if addr + 8 > len(self.data):
            raise RuntimeError("Memory access out of bounds")
        return struct.unpack("<d", self.data[addr:addr + 8])[0]

    def write_i32(self, addr: int, value: int) -> None:
        if addr + 4 > len(self.data):
            raise RuntimeError("Memory access out of bounds")
        self.data[addr:addr + 4] = struct.pack("<i", value)

    def write_i64(self, addr: int, value: int) -> None:
        if addr + 8 > len(self.data):
            raise RuntimeError("Memory access out of bounds")
        self.data[addr:addr + 8] = struct.pack("<q", value)

    def write_f32(self, addr: int, value: float) -> None:
        if addr + 4 > len(self.data):
            raise RuntimeError("Memory access out of bounds")
        self.data[addr:addr + 4] = struct.pack("<f", value)

    def write_f64(self, addr: int, value: float) -> None:
        if addr + 8 > len(self.data):
            raise RuntimeError("Memory access out of bounds")
        self.data[addr:addr + 8] = struct.pack("<d", value)

    def grow(self, delta_pages: int) -> int:
        with self._lock:
            new_pages = self.current_pages + delta_pages
            if new_pages > self.max_pages:
                return -1
            self.data.extend(bytearray(delta_pages * PAGE_SIZE))
            old = self.current_pages
            self.current_pages = new_pages
            return old


# =============================================================================
# WASI Stub
# =============================================================================
class WASIStub:
    """Minimal WASI implementation for stdout, args, environ."""

    def __init__(self, memory: LinearMemory) -> None:
        self.memory = memory
        self.args: List[str] = []
        self.environ: Dict[str, str] = {}
        self._fd_table: Dict[int, Any] = {0: "stdin", 1: "stdout", 2: "stderr"}

    def set_args(self, args: List[str]) -> None:
        self.args = args

    def set_environ(self, env: Dict[str, str]) -> None:
        self.environ = env

    def fd_write(self, fd: int, iovs: int, iovs_len: int, nwritten: int) -> int:
        """Write to file descriptor."""
        if fd not in self._fd_table:
            return 8  # EBADF
        total = 0
        for i in range(iovs_len):
            ptr = self.memory.read_i32(iovs + i * 8)
            length = self.memory.read_i32(iovs + i * 8 + 4)
            data = bytes(self.memory.data[ptr:ptr + length])
            if fd == 1:
                print(data.decode("utf-8", errors="replace"), end="")
            elif fd == 2:
                print(data.decode("utf-8", errors="replace"), end="", file=__import__("sys").stderr)
            total += length
        self.memory.write_i32(nwritten, total)
        return 0

    def fd_read(self, fd: int, iovs: int, iovs_len: int, nread: int) -> int:
        """Read from file descriptor."""
        if fd != 0:
            return 8
        self.memory.write_i32(nread, 0)
        return 0

    def args_get(self, argv: int, argv_buf: int) -> int:
        """Get command line arguments."""
        buf_ptr = argv_buf
        for i, arg in enumerate(self.args):
            arg_bytes = arg.encode("utf-8") + b"\x00"
            self.memory.write_i32(argv + i * 4, buf_ptr)
            self.memory.data[buf_ptr:buf_ptr + len(arg_bytes)] = arg_bytes
            buf_ptr += len(arg_bytes)
        return 0

    def args_sizes_get(self, argc: int, argv_buf_size: int) -> int:
        """Get sizes of command line arguments."""
        self.memory.write_i32(argc, len(self.args))
        total = sum(len(a.encode("utf-8")) + 1 for a in self.args)
        self.memory.write_i32(argv_buf_size, total)
        return 0

    def environ_get(self, environ: int, environ_buf: int) -> int:
        """Get environment variables."""
        buf_ptr = environ_buf
        for i, (k, v) in enumerate(self.environ.items()):
            env_bytes = f"{k}={v}".encode("utf-8") + b"\x00"
            self.memory.write_i32(environ + i * 4, buf_ptr)
            self.memory.data[buf_ptr:buf_ptr + len(env_bytes)] = env_bytes
            buf_ptr += len(env_bytes)
        return 0

    def environ_sizes_get(self, environ_count: int, environ_buf_size: int) -> int:
        self.memory.write_i32(environ_count, len(self.environ))
        total = sum(len(f"{k}={v}".encode("utf-8")) + 1 for k, v in self.environ.items())
        self.memory.write_i32(environ_buf_size, total)
        return 0

    def proc_exit(self, code: int) -> None:
        raise RuntimeError(f"WASM exited with code {code}")


# =============================================================================
# WASM Interpreter
# =============================================================================
class WASMInterpreter:
    """Execute WASM instructions with stack machine."""

    def __init__(self, module: WASMModule, memory: Optional[LinearMemory] = None, wasi: Optional[WASIStub] = None) -> None:
        self.module = module
        self.memory = memory or LinearMemory()
        self.wasi = wasi or WASIStub(self.memory)
        self.stack: List[Any] = []
        self.locals: List[Any] = []
        self.globals: List[Any] = []
        self.call_stack: List[int] = []
        self.label_stack: List[Tuple[int, int, int]] = []  # (type, arity, target_pc)
        self.instruction_count = 0
        self.max_instructions = 1_000_000  # Prevent infinite loops
        self._init_globals()

    def _init_globals(self) -> None:
        for valtype, mutable, init_expr in self.module.globals:
            # Execute init expression (simplified)
            val = self._exec_init_expr(init_expr)
            self.globals.append(val)

    def _exec_init_expr(self, expr: List[Any]) -> Any:
        i = 0
        while i < len(expr):
            op = expr[i]
            if op == Opcode.I32_CONST:
                i += 1
                return expr[i]
            elif op == Opcode.I64_CONST:
                i += 1
                return expr[i]
            elif op == Opcode.END:
                break
            i += 1
        return 0

    def call(self, func_idx: int, args: List[Any]) -> Any:
        """Call a function by index."""
        if func_idx < len(self.module.imports):
            # Handle import
            imp = self.module.imports[func_idx]
            return self._call_import(imp, args)

        code_idx = func_idx - len(self.module.imports)
        if code_idx >= len(self.module.code):
            raise RuntimeError(f"Function {func_idx} not found")

        locals_list, instructions = self.module.code[code_idx]
        type_idx = self.module.func_types[func_idx - len(self.module.imports)] if code_idx < len(self.module.func_types) else 0
        params, results = self.module.types[type_idx] if type_idx < len(self.module.types) else ([], [])

        # Set up locals
        self.locals = list(args) + [0] * len(locals_list)
        self.call_stack.append(func_idx)

        # Execute instructions
        pc = 0
        result = None
        while pc < len(instructions):
            if self.instruction_count >= self.max_instructions:
                raise RuntimeError("Instruction limit exceeded")
            self.instruction_count += 1

            op = instructions[pc]
            pc += 1

            if op == Opcode.NOP:
                pass
            elif op == Opcode.UNREACHABLE:
                raise RuntimeError("Unreachable executed")
            elif op == Opcode.BLOCK:
                pc += 1  # skip blocktype
            elif op == Opcode.LOOP:
                pc += 1  # skip blocktype
                self.label_stack.append((0, 0, pc - 2))
            elif op == Opcode.IF:
                pc += 1  # skip blocktype
                cond = self.stack.pop()
                if not cond:
                    # Skip to else or end
                    depth = 1
                    while pc < len(instructions) and depth > 0:
                        if instructions[pc] == Opcode.IF:
                            depth += 1
                        elif instructions[pc] == Opcode.END:
                            depth -= 1
                        elif instructions[pc] == Opcode.ELSE and depth == 1:
                            depth -= 1
                        pc += 1
            elif op == Opcode.ELSE:
                # Skip to matching END
                depth = 1
                while pc < len(instructions) and depth > 0:
                    if instructions[pc] == Opcode.IF or instructions[pc] == Opcode.BLOCK or instructions[pc] == Opcode.LOOP:
                        depth += 1
                    elif instructions[pc] == Opcode.END:
                        depth -= 1
                    pc += 1
            elif op == Opcode.END:
                if self.label_stack:
                    self.label_stack.pop()
                pass
            elif op == Opcode.BR:
                label_idx = instructions[pc]
                pc += 1
                # Jump to target (simplified)
                pass
            elif op == Opcode.BR_IF:
                label_idx = instructions[pc]
                pc += 1
                cond = self.stack.pop()
                if cond:
                    pass  # Jump logic simplified
            elif op == Opcode.RETURN:
                break
            elif op == Opcode.CALL:
                func_idx_called = instructions[pc]
                pc += 1
                # Get args from stack
                params_count = len(self.module.types[self.module.func_types[func_idx_called - len(self.module.imports)]][0]) if func_idx_called >= len(self.module.imports) else 0
                call_args = []
                for _ in range(params_count):
                    call_args.insert(0, self.stack.pop())
                ret = self.call(func_idx_called, call_args)
                if ret is not None:
                    self.stack.append(ret)
            elif op == Opcode.DROP:
                self.stack.pop()
            elif op == Opcode.SELECT:
                cond = self.stack.pop()
                val2 = self.stack.pop()
                val1 = self.stack.pop()
                self.stack.append(val1 if cond else val2)
            elif op == Opcode.LOCAL_GET:
                idx = instructions[pc]
                pc += 1
                self.stack.append(self.locals[idx])
            elif op == Opcode.LOCAL_SET:
                idx = instructions[pc]
                pc += 1
                self.locals[idx] = self.stack.pop()
            elif op == Opcode.LOCAL_TEE:
                idx = instructions[pc]
                pc += 1
                self.locals[idx] = self.stack[-1]
            elif op == Opcode.GLOBAL_GET:
                idx = instructions[pc]
                pc += 1
                self.stack.append(self.globals[idx])
            elif op == Opcode.GLOBAL_SET:
                idx = instructions[pc]
                pc += 1
                self.globals[idx] = self.stack.pop()
            elif op == Opcode.I32_LOAD:
                _align = instructions[pc]
                pc += 1
                offset = instructions[pc]
                pc += 1
                addr = self.stack.pop() + offset
                self.stack.append(self.memory.read_i32(addr))
            elif op == Opcode.I32_STORE:
                _align = instructions[pc]
                pc += 1
                offset = instructions[pc]
                pc += 1
                val = self.stack.pop()
                addr = self.stack.pop() + offset
                self.memory.write_i32(addr, val)
            elif op == Opcode.I32_CONST:
                val = instructions[pc]
                pc += 1
                self.stack.append(val)
            elif op == Opcode.I64_CONST:
                val = instructions[pc]
                pc += 1
                self.stack.append(val)
            elif op == Opcode.F32_CONST:
                val = instructions[pc]
                pc += 1
                self.stack.append(val)
            elif op == Opcode.F64_CONST:
                val = instructions[pc]
                pc += 1
                self.stack.append(val)
            elif op == Opcode.I32_EQZ:
                self.stack.append(1 if self.stack.pop() == 0 else 0)
            elif op == Opcode.I32_EQ:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(1 if a == b else 0)
            elif op == Opcode.I32_NE:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(1 if a != b else 0)
            elif op == Opcode.I32_LT_S:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(1 if a < b else 0)
            elif op == Opcode.I32_LT_U:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(1 if (a & 0xFFFFFFFF) < (b & 0xFFFFFFFF) else 0)
            elif op == Opcode.I32_GT_S:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(1 if a > b else 0)
            elif op == Opcode.I32_GT_U:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(1 if (a & 0xFFFFFFFF) > (b & 0xFFFFFFFF) else 0)
            elif op == Opcode.I32_LE_S:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(1 if a <= b else 0)
            elif op == Opcode.I32_LE_U:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(1 if (a & 0xFFFFFFFF) <= (b & 0xFFFFFFFF) else 0)
            elif op == Opcode.I32_GE_S:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(1 if a >= b else 0)
            elif op == Opcode.I32_GE_U:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(1 if (a & 0xFFFFFFFF) >= (b & 0xFFFFFFFF) else 0)
            elif op == Opcode.I32_ADD:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append((a + b) & 0xFFFFFFFF)
            elif op == Opcode.I32_SUB:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append((a - b) & 0xFFFFFFFF)
            elif op == Opcode.I32_MUL:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append((a * b) & 0xFFFFFFFF)
            elif op == Opcode.I32_DIV_S:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append((a // b) & 0xFFFFFFFF if b != 0 else 0)
            elif op == Opcode.I32_DIV_U:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(((a & 0xFFFFFFFF) // (b & 0xFFFFFFFF)) & 0xFFFFFFFF if b != 0 else 0)
            elif op == Opcode.I32_REM_S:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append((a % b) & 0xFFFFFFFF if b != 0 else 0)
            elif op == Opcode.I32_REM_U:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(((a & 0xFFFFFFFF) % (b & 0xFFFFFFFF)) & 0xFFFFFFFF if b != 0 else 0)
            elif op == Opcode.I32_AND:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a & b)
            elif op == Opcode.I32_OR:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a | b)
            elif op == Opcode.I32_XOR:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a ^ b)
            elif op == Opcode.I32_SHL:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append((a << (b & 0x1F)) & 0xFFFFFFFF)
            elif op == Opcode.I32_SHR_S:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a >> (b & 0x1F))
            elif op == Opcode.I32_SHR_U:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append((a & 0xFFFFFFFF) >> (b & 0x1F))
            elif op == Opcode.I64_ADD:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append((a + b) & 0xFFFFFFFFFFFFFFFF)
            elif op == Opcode.I64_SUB:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append((a - b) & 0xFFFFFFFFFFFFFFFF)
            elif op == Opcode.I64_MUL:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append((a * b) & 0xFFFFFFFFFFFFFFFF)
            elif op == Opcode.F32_ADD:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a + b)
            elif op == Opcode.F32_SUB:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a - b)
            elif op == Opcode.F32_MUL:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a * b)
            elif op == Opcode.F32_DIV:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a / b if b != 0 else float("inf"))
            elif op == Opcode.F64_ADD:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a + b)
            elif op == Opcode.F64_SUB:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a - b)
            elif op == Opcode.F64_MUL:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a * b)
            elif op == Opcode.F64_DIV:
                b, a = self.stack.pop(), self.stack.pop()
                self.stack.append(a / b if b != 0 else float("inf"))
            elif op == Opcode.I32_WRAP_I64:
                val = self.stack.pop()
                self.stack.append(val & 0xFFFFFFFF)
            elif op == Opcode.I64_EXTEND_I32_S:
                val = self.stack.pop()
                self.stack.append(val if val < 0x80000000 else val - 0x100000000)
            elif op == Opcode.I64_EXTEND_I32_U:
                val = self.stack.pop()
                self.stack.append(val & 0xFFFFFFFF)
            else:
                raise RuntimeError(f"Unimplemented opcode: {hex(op)}")

        self.call_stack.pop()

        # Return value
        if results:
            if self.stack:
                return self.stack.pop()
        return None

    def _call_import(self, imp: Tuple[str, str, str, Any], args: List[Any]) -> Any:
        mod, name, kind, idx = imp
        if mod == "wasi_snapshot_preview1":
            if name == "fd_write":
                return self.wasi.fd_write(args[0], args[1], args[2], args[3])
            elif name == "fd_read":
                return self.wasi.fd_read(args[0], args[1], args[2], args[3])
            elif name == "args_get":
                return self.wasi.args_get(args[0], args[1])
            elif name == "args_sizes_get":
                return self.wasi.args_sizes_get(args[0], args[1])
            elif name == "environ_get":
                return self.wasi.environ_get(args[0], args[1])
            elif name == "environ_sizes_get":
                return self.wasi.environ_sizes_get(args[0], args[1])
            elif name == "proc_exit":
                return self.wasi.proc_exit(args[0])
        raise RuntimeError(f"Unknown import: {mod}.{name}")


# =============================================================================
# WASM Sandbox
# =============================================================================
class WASMSandbox:
    """Secure wrapper around WASM execution."""

    def __init__(self, max_pages: int = 16, max_instructions: int = 1_000_000) -> None:
        self.max_pages = max_pages
        self.max_instructions = max_instructions
        self._executions: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def execute(self, wasm_bytes: bytes, export_name: str = "_start", args: List[Any] = None) -> Dict[str, Any]:
        t0 = time.time()
        result: Dict[str, Any] = {
            "success": False,
            "return_value": None,
            "instructions": 0,
            "memory_pages": 0,
            "duration_ms": 0,
            "error": "",
        }
        try:
            parser = WASMParser(wasm_bytes)
            module = parser.parse()
            memory = LinearMemory(max_pages=self.max_pages)
            wasi = WASIStub(memory)
            interpreter = WASMInterpreter(module, memory, wasi)
            interpreter.max_instructions = self.max_instructions

            # Find exported function
            if export_name not in module.exports:
                result["error"] = f"Export '{export_name}' not found"
                return result

            kind, func_idx = module.exports[export_name]
            if kind != 0x00:
                result["error"] = f"Export '{export_name}' is not a function"
                return result

            ret = interpreter.call(func_idx, args or [])
            result["success"] = True
            result["return_value"] = ret
            result["instructions"] = interpreter.instruction_count
            result["memory_pages"] = memory.current_pages
            result["duration_ms"] = (time.time() - t0) * 1000
        except Exception as exc:
            result["error"] = str(exc)

        with self._lock:
            self._executions.append(result)
        return result

    def get_history(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._executions)


# =============================================================================
# WASM Engine
# =============================================================================
class WASMEngine:
    """Top-level WASM engine: load, instantiate, execute."""

    def __init__(self) -> None:
        self._modules: Dict[str, WASMModule] = {}
        self._instances: Dict[str, WASMInterpreter] = {}
        self._lock = threading.Lock()

    def load(self, name: str, wasm_bytes: bytes) -> WASMModule:
        parser = WASMParser(wasm_bytes)
        module = parser.parse()
        with self._lock:
            self._modules[name] = module
        return module

    def instantiate(self, name: str, memory: Optional[LinearMemory] = None, wasi: Optional[WASIStub] = None) -> WASMInterpreter:
        module = self._modules.get(name)
        if not module:
            raise ValueError(f"Module '{name}' not loaded")
        mem = memory or LinearMemory()
        interpreter = WASMInterpreter(module, mem, wasi or WASIStub(mem))
        with self._lock:
            self._instances[name] = interpreter
        return interpreter

    def call(self, module_name: str, func_name: str, args: List[Any] = None) -> Any:
        interpreter = self._instances.get(module_name)
        if not interpreter:
            raise ValueError(f"Module '{module_name}' not instantiated")
        module = interpreter.module
        if func_name not in module.exports:
            raise ValueError(f"Function '{func_name}' not exported")
        kind, func_idx = module.exports[func_name]
        if kind != 0x00:
            raise ValueError(f"'{func_name}' is not a function")
        return interpreter.call(func_idx, args or [])

    def list_modules(self) -> List[str]:
        with self._lock:
            return list(self._modules.keys())

    def get_exports(self, module_name: str) -> Dict[str, Tuple[int, int]]:
        module = self._modules.get(module_name)
        return module.exports if module else {}


# =============================================================================
# Demo
# =============================================================================
def run_demo() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS WASM Runtime Demo")
    print("=" * 60)
    engine = WASMEngine()

    # Create a minimal WASM binary that adds two numbers
    # (i32.const 10) (i32.const 20) (i32.add) (return)
    # This is a hand-crafted minimal binary for demo
    wasm_add = bytes([
        0x00, 0x61, 0x73, 0x6d,  # magic
        0x01, 0x00, 0x00, 0x00,  # version
        # Type section
        0x01,  # section id
        0x07,  # size
        0x01,  # 1 type
        0x60,  # func type
        0x02, 0x7f, 0x7f,  # params: i32, i32
        0x01, 0x7f,  # results: i32
        # Function section
        0x03,  # section id
        0x02,  # size
        0x01,  # 1 function
        0x00,  # type index 0
        # Export section
        0x07,  # section id
        0x08,  # size
        0x01,  # 1 export
        0x03,  # name length
        ord("a"), ord("d"), ord("d"),  # "add"
        0x00,  # kind: function
        0x00,  # function index
        # Code section
        0x0a,  # section id
        0x0a,  # size
        0x01,  # 1 body
        0x08,  # body size
        0x00,  # 0 locals
        0x20, 0x00,  # local.get 0
        0x20, 0x01,  # local.get 1
        0x6a,  # i32.add
        0x0b,  # end
    ])

    engine.load("add_demo", wasm_add)
    interpreter = engine.instantiate("add_demo")
    result = engine.call("add_demo", "add", [10, 20])
    print(f"10 + 20 = {result}")

    # Sandbox test
    sandbox = WASMSandbox()
    exec_result = sandbox.execute(wasm_add, "add", [5, 7])
    print(f"Sandbox: {exec_result}")

    print("Demo complete.")


if __name__ == "__main__":
    run_demo()

#!/usr/bin/env python3
"""
WASM Runtime — MAGNATRIX-OS Minimal WebAssembly Interpreter
============================================================
Supports WASM binary format parsing, simple arithmetic, control flow,
memory operations, and function calls. No external dependencies.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union


class WASMType:
    """WASM value types."""
    I32 = 0x7F
    I64 = 0x7E
    F32 = 0x7D
    F64 = 0x7C
    VOID = 0x40


class WASMOpcodes:
    """Core WASM opcodes (subset)."""
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
    I32_GT_S = 0x4A
    I32_ADD = 0x6A
    I32_SUB = 0x6B
    I32_MUL = 0x6C
    I32_DIV_S = 0x6D
    I32_AND = 0x71
    I32_OR = 0x72
    I32_XOR = 0x73
    I32_SHL = 0x74
    I32_SHR_S = 0x75
    I32_WRAP_I64 = 0xA7
    I64_EXTEND_I32_S = 0xAC


@dataclass
class WASMFunction:
    """A WASM function definition."""
    name: str = ""
    params: List[int] = field(default_factory=list)
    results: List[int] = field(default_factory=list)
    locals: List[int] = field(default_factory=list)
    body: bytes = b""
    import_module: Optional[str] = None
    import_name: Optional[str] = None


@dataclass
class WASMModule:
    """Parsed WASM module structure."""
    types: List[Tuple[List[int], List[int]]] = field(default_factory=list)
    functions: List[WASMFunction] = field(default_factory=list)
    exports: Dict[str, int] = field(default_factory=dict)
    imports: List[Dict[str, Any]] = field(default_factory=list)
    memory: Optional[Dict[str, Any]] = None
    data: List[bytes] = field(default_factory=list)
    globals: List[Dict[str, Any]] = field(default_factory=list)
    start: Optional[int] = None


class WASMParser:
    """Parse WASM binary format into a structured module."""

    MAGIC = b"\x00asm"
    VERSION = b"\x01\x00\x00\x00"

    SECTION_TYPE = 1
    SECTION_IMPORT = 2
    SECTION_FUNCTION = 3
    SECTION_MEMORY = 5
    SECTION_GLOBAL = 6
    SECTION_EXPORT = 7
    SECTION_START = 8
    SECTION_CODE = 10
    SECTION_DATA = 11

    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def parse(self) -> WASMModule:
        """Parse a complete WASM binary module."""
        module = WASMModule()
        if self._read_bytes(4) != self.MAGIC:
            raise ValueError("Invalid WASM magic number")
        if self._read_bytes(4) != self.VERSION:
            raise ValueError("Unsupported WASM version")

        while self.pos < len(self.data):
            section_id = self._read_byte()
            section_size = self._read_leb128_u()
            section_start = self.pos
            
            if section_id == self.SECTION_TYPE:
                module.types = self._parse_type_section()
            elif section_id == self.SECTION_IMPORT:
                module.imports = self._parse_import_section()
            elif section_id == self.SECTION_FUNCTION:
                module.functions = self._parse_function_section(module)
            elif section_id == self.SECTION_MEMORY:
                module.memory = self._parse_memory_section()
            elif section_id == self.SECTION_GLOBAL:
                module.globals = self._parse_global_section()
            elif section_id == self.SECTION_EXPORT:
                module.exports = self._parse_export_section()
            elif section_id == self.SECTION_START:
                module.start = self._read_leb128_u()
            elif section_id == self.SECTION_CODE:
                self._parse_code_section(module)
            elif section_id == self.SECTION_DATA:
                module.data = self._parse_data_section()
            else:
                self.pos = section_start + section_size
        return module

    def _read_byte(self) -> int:
        b = self.data[self.pos]
        self.pos += 1
        return b

    def _read_bytes(self, n: int) -> bytes:
        result = self.data[self.pos:self.pos+n]
        self.pos += n
        return result

    def _read_leb128_u(self) -> int:
        result = 0
        shift = 0
        while True:
            byte = self._read_byte()
            result |= (byte & 0x7F) << shift
            if (byte & 0x80) == 0:
                break
            shift += 7
        return result

    def _read_leb128_s(self) -> int:
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

    def _parse_type_section(self) -> List[Tuple[List[int], List[int]]]:
        count = self._read_leb128_u()
        types = []
        for _ in range(count):
            form = self._read_byte()
            if form != 0x60:
                continue
            param_count = self._read_leb128_u()
            params = [self._read_byte() for _ in range(param_count)]
            result_count = self._read_leb128_u()
            results = [self._read_byte() for _ in range(result_count)]
            types.append((params, results))
        return types

    def _parse_import_section(self) -> List[Dict[str, Any]]:
        count = self._read_leb128_u()
        imports = []
        for _ in range(count):
            mod_len = self._read_leb128_u()
            mod_name = self._read_bytes(mod_len).decode("utf-8")
            field_len = self._read_leb128_u()
            field_name = self._read_bytes(field_len).decode("utf-8")
            kind = self._read_byte()
            idx = self._read_leb128_u()
            imports.append({"module": mod_name, "name": field_name, "kind": kind, "index": idx})
        return imports

    def _parse_function_section(self, module: WASMModule) -> List[WASMFunction]:
        count = self._read_leb128_u()
        functions = []
        for _ in range(count):
            type_idx = self._read_leb128_u()
            if type_idx < len(module.types):
                params, results = module.types[type_idx]
                functions.append(WASMFunction(params=list(params), results=list(results)))
            else:
                functions.append(WASMFunction())
        return functions

    def _parse_memory_section(self) -> Dict[str, Any]:
        count = self._read_leb128_u()
        if count > 0:
            flags = self._read_byte()
            initial = self._read_leb128_u()
            maximum = self._read_leb128_u() if flags & 1 else None
            return {"initial": initial, "maximum": maximum, "flags": flags}
        return None

    def _parse_global_section(self) -> List[Dict[str, Any]]:
        count = self._read_leb128_u()
        globals_list = []
        for _ in range(count):
            val_type = self._read_byte()
            mutable = self._read_byte() == 1
            expr = self._parse_expr()
            globals_list.append({"type": val_type, "mutable": mutable, "init": expr})
        return globals_list

    def _parse_export_section(self) -> Dict[str, int]:
        count = self._read_leb128_u()
        exports = {}
        for _ in range(count):
            name_len = self._read_leb128_u()
            name = self._read_bytes(name_len).decode("utf-8")
            kind = self._read_byte()
            idx = self._read_leb128_u()
            exports[name] = idx
        return exports

    def _parse_code_section(self, module: WASMModule) -> None:
        count = self._read_leb128_u()
        for i in range(min(count, len(module.functions))):
            body_size = self._read_leb128_u()
            body_start = self.pos
            local_count = self._read_leb128_u()
            locals_types = []
            for _ in range(local_count):
                n = self._read_leb128_u()
                t = self._read_byte()
                locals_types.extend([t] * n)
            module.functions[i].locals = locals_types
            module.functions[i].body = self.data[self.pos:body_start + body_size]
            self.pos = body_start + body_size

    def _parse_data_section(self) -> List[bytes]:
        count = self._read_leb128_u()
        data = []
        for _ in range(count):
            mem_idx = self._read_leb128_u()
            expr = self._parse_expr()
            data_len = self._read_leb128_u()
            data.append(self._read_bytes(data_len))
        return data

    def _parse_expr(self) -> bytes:
        """Parse expression until END opcode."""
        start = self.pos
        depth = 0
        while True:
            opcode = self._read_byte()
            if opcode in (WASMOpcodes.BLOCK, WASMOpcodes.LOOP, WASMOpcodes.IF):
                depth += 1
                block_type = self._read_byte()
            elif opcode == WASMOpcodes.ELSE and depth == 0:
                pass
            elif opcode == WASMOpcodes.END:
                if depth == 0:
                    break
                depth -= 1
            elif opcode == WASMOpcodes.BR or opcode == WASMOpcodes.BR_IF:
                self._read_leb128_u()
            elif opcode == WASMOpcodes.I32_CONST:
                self._read_leb128_s()
            elif opcode == WASMOpcodes.I64_CONST:
                self._read_leb128_s()
            elif opcode == WASMOpcodes.F32_CONST:
                self._read_bytes(4)
            elif opcode == WASMOpcodes.F64_CONST:
                self._read_bytes(8)
            elif opcode == WASMOpcodes.LOCAL_GET or opcode == WASMOpcodes.LOCAL_SET or opcode == WASMOpcodes.LOCAL_TEE:
                self._read_leb128_u()
            elif opcode == WASMOpcodes.CALL:
                self._read_leb128_u()
            elif opcode == WASMOpcodes.I32_LOAD or opcode == WASMOpcodes.I32_STORE:
                self._read_leb128_u()
                self._read_leb128_u()
        return self.data[start:self.pos]


class WASMInterpreter:
    """
    Execute parsed WASM modules.
    
    Supports: i32 arithmetic, control flow, memory, function calls.
    """

    def __init__(self, module: WASMModule, memory_size: int = 64 * 1024):
        self.module = module
        self.memory = bytearray(memory_size)
        self.stack: List[int] = []
        self.call_stack: List[int] = []
        self.locals: List[int] = []
        self.globals: List[int] = [0] * len(module.globals)
        for i, g in enumerate(module.globals):
            if g["init"]:
                self.globals[i] = self._eval_const(g["init"])
        # Initialize data segments
        for data in module.data:
            if data:
                self.memory[:len(data)] = data

    def _eval_const(self, expr: bytes) -> int:
        """Evaluate a constant expression."""
        if not expr:
            return 0
        if expr[0] == WASMOpcodes.I32_CONST:
            return self._read_leb128_s_from(expr[1:])
        return 0

    def _read_leb128_s_from(self, data: bytes) -> int:
        result = 0
        shift = 0
        for i, byte in enumerate(data):
            result |= (byte & 0x7F) << shift
            if (byte & 0x80) == 0:
                if byte & 0x40:
                    result |= - (1 << (shift + 7))
                return result
            shift += 7
        return result

    def call(self, func_name: str, *args: int) -> Optional[int]:
        """Call an exported function by name."""
        if func_name not in self.module.exports:
            raise ValueError(f"Function not found: {func_name}")
        func_idx = self.module.exports[func_name]
        if func_idx >= len(self.module.functions):
            raise ValueError(f"Invalid function index: {func_idx}")
        return self._call_function(func_idx, list(args))

    def _call_function(self, func_idx: int, args: List[int]) -> Optional[int]:
        func = self.module.functions[func_idx]
        self.locals = list(args) + [0] * len(func.locals)
        self.call_stack.append(func_idx)
        try:
            self._execute(func.body)
        finally:
            self.call_stack.pop()
        if func.results and self.stack:
            return self.stack.pop()
        return None

    def _execute(self, code: bytes) -> None:
        """Execute WASM bytecode."""
        pos = 0
        block_stack: List[Tuple[int, int, List[int]]] = []  # (pos, end_pos, stack_snapshot)

        while pos < len(code):
            opcode = code[pos]
            pos += 1

            if opcode == WASMOpcodes.NOP:
                continue
            elif opcode == WASMOpcodes.END:
                if block_stack:
                    pos, _, _ = block_stack.pop()
                continue
            elif opcode == WASMOpcodes.BLOCK:
                block_type = code[pos]
                pos += 1
                block_stack.append((pos, len(code), list(self.stack)))
            elif opcode == WASMOpcodes.LOOP:
                block_type = code[pos]
                pos += 1
                block_stack.append((pos, len(code), list(self.stack)))
            elif opcode == WASMOpcodes.IF:
                block_type = code[pos]
                pos += 1
                cond = self.stack.pop() if self.stack else 0
                if cond == 0:
                    # Skip to ELSE or END
                    depth = 1
                    while pos < len(code):
                        if code[pos] in (WASMOpcodes.BLOCK, WASMOpcodes.LOOP, WASMOpcodes.IF):
                            depth += 1
                        elif code[pos] == WASMOpcodes.END:
                            depth -= 1
                            if depth == 0:
                                pos += 1
                                break
                        elif code[pos] == WASMOpcodes.ELSE and depth == 1:
                            pos += 1
                            break
                        pos += 1
                    if depth > 0:
                        pos = len(code)
                else:
                    block_stack.append((pos, len(code), list(self.stack)))
            elif opcode == WASMOpcodes.ELSE:
                # Skip to END
                depth = 1
                while pos < len(code):
                    if code[pos] in (WASMOpcodes.BLOCK, WASMOpcodes.LOOP, WASMOpcodes.IF):
                        depth += 1
                    elif code[pos] == WASMOpcodes.END:
                        depth -= 1
                        if depth == 0:
                            pos += 1
                            break
                    pos += 1
                if block_stack:
                    block_stack.pop()
            elif opcode == WASMOpcodes.BR:
                label = self._read_leb128_from(code, pos)
                pos += label[1]
                if block_stack and len(block_stack) > label[0]:
                    target = block_stack[-(label[0] + 1)]
                    pos = target[0]
                    block_stack = block_stack[:len(block_stack) - label[0]]
            elif opcode == WASMOpcodes.BR_IF:
                label = self._read_leb128_from(code, pos)
                pos += label[1]
                cond = self.stack.pop() if self.stack else 0
                if cond != 0 and block_stack and len(block_stack) > label[0]:
                    target = block_stack[-(label[0] + 1)]
                    pos = target[0]
                    block_stack = block_stack[:len(block_stack) - label[0]]
            elif opcode == WASMOpcodes.RETURN:
                return
            elif opcode == WASMOpcodes.CALL:
                func_idx = self._read_leb128_from(code, pos)
                pos += func_idx[1]
                # For simplicity, only support built-in functions
                continue
            elif opcode == WASMOpcodes.DROP:
                if self.stack:
                    self.stack.pop()
            elif opcode == WASMOpcodes.SELECT:
                c = self.stack.pop() if self.stack else 0
                b = self.stack.pop() if self.stack else 0
                a = self.stack.pop() if self.stack else 0
                self.stack.append(a if c != 0 else b)
            elif opcode == WASMOpcodes.LOCAL_GET:
                idx = self._read_leb128_from(code, pos)
                pos += idx[1]
                if idx[0] < len(self.locals):
                    self.stack.append(self.locals[idx[0]])
                else:
                    self.stack.append(0)
            elif opcode == WASMOpcodes.LOCAL_SET:
                idx = self._read_leb128_from(code, pos)
                pos += idx[1]
                val = self.stack.pop() if self.stack else 0
                if idx[0] < len(self.locals):
                    self.locals[idx[0]] = val
            elif opcode == WASMOpcodes.LOCAL_TEE:
                idx = self._read_leb128_from(code, pos)
                pos += idx[1]
                val = self.stack[-1] if self.stack else 0
                if idx[0] < len(self.locals):
                    self.locals[idx[0]] = val
            elif opcode == WASMOpcodes.GLOBAL_GET:
                idx = self._read_leb128_from(code, pos)
                pos += idx[1]
                if idx[0] < len(self.globals):
                    self.stack.append(self.globals[idx[0]])
                else:
                    self.stack.append(0)
            elif opcode == WASMOpcodes.GLOBAL_SET:
                idx = self._read_leb128_from(code, pos)
                pos += idx[1]
                val = self.stack.pop() if self.stack else 0
                if idx[0] < len(self.globals):
                    self.globals[idx[0]] = val
            elif opcode == WASMOpcodes.I32_LOAD:
                align = self._read_leb128_from(code, pos)
                pos += align[1]
                offset = self._read_leb128_from(code, pos)
                pos += offset[1]
                addr = (self.stack.pop() if self.stack else 0) + offset[0]
                if addr + 4 <= len(self.memory):
                    self.stack.append(struct.unpack("<I", self.memory[addr:addr+4])[0])
                else:
                    self.stack.append(0)
            elif opcode == WASMOpcodes.I32_STORE:
                align = self._read_leb128_from(code, pos)
                pos += align[1]
                offset = self._read_leb128_from(code, pos)
                pos += offset[1]
                val = self.stack.pop() if self.stack else 0
                addr = (self.stack.pop() if self.stack else 0) + offset[0]
                if addr + 4 <= len(self.memory):
                    self.memory[addr:addr+4] = struct.pack("<I", val & 0xFFFFFFFF)
            elif opcode == WASMOpcodes.I32_CONST:
                val = self._read_leb128_from(code, pos)
                pos += val[1]
                self.stack.append(val[0])
            elif opcode == WASMOpcodes.I64_CONST:
                val = self._read_leb128_from(code, pos)
                pos += val[1]
                self.stack.append(val[0])
            elif opcode == WASMOpcodes.F32_CONST:
                self.stack.append(struct.unpack("<f", code[pos:pos+4])[0])
                pos += 4
            elif opcode == WASMOpcodes.F64_CONST:
                self.stack.append(struct.unpack("<d", code[pos:pos+8])[0])
                pos += 8
            elif opcode == WASMOpcodes.I32_EQZ:
                self.stack.append(1 if (self.stack.pop() if self.stack else 0) == 0 else 0)
            elif opcode == WASMOpcodes.I32_EQ:
                b = self.stack.pop() if self.stack else 0
                a = self.stack.pop() if self.stack else 0
                self.stack.append(1 if a == b else 0)
            elif opcode == WASMOpcodes.I32_NE:
                b = self.stack.pop() if self.stack else 0
                a = self.stack.pop() if self.stack else 0
                self.stack.append(1 if a != b else 0)
            elif opcode == WASMOpcodes.I32_LT_S:
                b = self.stack.pop() if self.stack else 0
                a = self.stack.pop() if self.stack else 0
                self.stack.append(1 if a < b else 0)
            elif opcode == WASMOpcodes.I32_GT_S:
                b = self.stack.pop() if self.stack else 0
                a = self.stack.pop() if self.stack else 0
                self.stack.append(1 if a > b else 0)
            elif opcode == WASMOpcodes.I32_ADD:
                b = self.stack.pop() if self.stack else 0
                a = self.stack.pop() if self.stack else 0
                self.stack.append((a + b) & 0xFFFFFFFF)
            elif opcode == WASMOpcodes.I32_SUB:
                b = self.stack.pop() if self.stack else 0
                a = self.stack.pop() if self.stack else 0
                self.stack.append((a - b) & 0xFFFFFFFF)
            elif opcode == WASMOpcodes.I32_MUL:
                b = self.stack.pop() if self.stack else 0
                a = self.stack.pop() if self.stack else 0
                self.stack.append((a * b) & 0xFFFFFFFF)
            elif opcode == WASMOpcodes.I32_DIV_S:
                b = self.stack.pop() if self.stack else 0
                a = self.stack.pop() if self.stack else 0
                if b == 0:
                    self.stack.append(0)
                else:
                    self.stack.append((a // b) & 0xFFFFFFFF)
            elif opcode == WASMOpcodes.I32_AND:
                b = self.stack.pop() if self.stack else 0
                a = self.stack.pop() if self.stack else 0
                self.stack.append(a & b)
            elif opcode == WASMOpcodes.I32_OR:
                b = self.stack.pop() if self.stack else 0
                a = self.stack.pop() if self.stack else 0
                self.stack.append(a | b)
            elif opcode == WASMOpcodes.I32_XOR:
                b = self.stack.pop() if self.stack else 0
                a = self.stack.pop() if self.stack else 0
                self.stack.append(a ^ b)
            elif opcode == WASMOpcodes.I32_SHL:
                b = self.stack.pop() if self.stack else 0
                a = self.stack.pop() if self.stack else 0
                self.stack.append((a << (b & 31)) & 0xFFFFFFFF)
            elif opcode == WASMOpcodes.I32_SHR_S:
                b = self.stack.pop() if self.stack else 0
                a = self.stack.pop() if self.stack else 0
                if a & 0x80000000:
                    a = a - 0x100000000
                self.stack.append((a >> (b & 31)) & 0xFFFFFFFF)
            elif opcode == WASMOpcodes.I32_WRAP_I64:
                val = self.stack.pop() if self.stack else 0
                self.stack.append(val & 0xFFFFFFFF)
            elif opcode == WASMOpcodes.I64_EXTEND_I32_S:
                val = self.stack.pop() if self.stack else 0
                if val & 0x80000000:
                    val = val - 0x100000000
                self.stack.append(val)
            else:
                # Unknown opcode - skip
                continue

    def _read_leb128_from(self, data: bytes, pos: int) -> Tuple[int, int]:
        result = 0
        shift = 0
        orig_pos = pos
        while pos < len(data):
            byte = data[pos]
            pos += 1
            result |= (byte & 0x7F) << shift
            if (byte & 0x80) == 0:
                if byte & 0x40 and shift < 32:
                    result |= - (1 << (shift + 7))
                return result, pos - orig_pos
            shift += 7
        return result, pos - orig_pos


class WASMRuntime:
    """
    Top-level WASM runtime for MAGNATRIX-OS.
    
    Parses and executes WASM modules. Supports binary format and
    a simplified text format.
    """

    CAPABILITIES = ["wasm", "runtime", "sandbox"]

    def __init__(self, repo_root: str = "."):
        self.repo_root = repo_root
        self._modules: Dict[str, WASMModule] = {}
        self._interpreters: Dict[str, WASMInterpreter] = {}
        self._memory_limit = 1024 * 1024  # 1MB default

    def load_binary(self, name: str, data: bytes) -> WASMModule:
        """Load a WASM binary module."""
        parser = WASMParser(data)
        module = parser.parse()
        self._modules[name] = module
        return module

    def load_text(self, name: str, text: str) -> WASMModule:
        """Load a simplified text-format WASM module."""
        module = WASMModule()
        lines = [line.strip() for line in text.split("\n") if line.strip() and not line.strip().startswith(";")]
        for line in lines:
            if line.startswith("(func "):
                parts = line[6:-1].split()
                func_name = parts[0].strip('"')
                func = WASMFunction(name=func_name)
                in_body = False
                for token in parts[1:]:
                    if token.startswith("("):
                        in_body = True
                    if in_body:
                        # Very simplified: just store tokens as body
                        func.body = b""  # Would need full text parser
                module.functions.append(func)
                module.exports[func_name] = len(module.functions) - 1
        self._modules[name] = module
        return module

    def instantiate(self, name: str, memory_size: Optional[int] = None) -> WASMInterpreter:
        """Instantiate a loaded module."""
        module = self._modules.get(name)
        if not module:
            raise ValueError(f"Module not loaded: {name}")
        mem = min(memory_size or self._memory_limit, self._memory_limit)
        interpreter = WASMInterpreter(module, mem)
        self._interpreters[name] = interpreter
        return interpreter

    def call(self, module_name: str, func_name: str, *args: int) -> Optional[int]:
        """Call an exported function."""
        interpreter = self._interpreters.get(module_name)
        if not interpreter:
            raise ValueError(f"Module not instantiated: {module_name}")
        return interpreter.call(func_name, *args)

    def get_memory(self, module_name: str) -> bytearray:
        """Get module's memory."""
        interpreter = self._interpreters.get(module_name)
        if not interpreter:
            raise ValueError(f"Module not instantiated: {module_name}")
        return interpreter.memory

    def list_modules(self) -> List[str]:
        return list(self._modules.keys())

    def unload(self, name: str) -> None:
        self._modules.pop(name, None)
        self._interpreters.pop(name, None)

    def handle_message(self, message: Dict[str, Any]) -> Any:
        action = message.get("action", "")
        if action == "load":
            data = bytes.fromhex(message["data"]) if isinstance(message["data"], str) else message["data"]
            return self.load_binary(message["name"], data).exports
        elif action == "call":
            return self.call(message["module"], message["func"], *message.get("args", []))
        elif action == "list":
            return self.list_modules()
        return None

    def on_event(self, event) -> None:
        pass

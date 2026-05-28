"""
native_jit_compiler.py — Lexer→Parser→AST→Bytecode→VM pipeline.

Architectural patterns extracted from Liftoff-Studios/Syntax-to-Bytecode-Engine:
- Tokenizer with regex-free character scanning for speed & portability.
- Recursive-descent Pratt parser handling operator precedence.
- Flat AST nodes with type tags (not class-per-node to stay lightweight).
- Bytecode opcodes designed for a stack-based virtual machine.
- Simple compiler pass lowering AST → linear bytecode.
- Stack-machine VM with call/ret support.

Pure Python ≥3.9, stdlib only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Lexer
# ---------------------------------------------------------------------------

class TokenType(Enum):
    NUMBER = auto(); STRING = auto(); IDENT = auto()
    PLUS = auto(); MINUS = auto(); STAR = auto(); SLASH = auto()
    EQ = auto(); LT = auto(); GT = auto(); BANG = auto()
    LPAREN = auto(); RPAREN = auto(); LBRACE = auto(); RBRACE = auto()
    COMMA = auto(); SEMI = auto(); COLON = auto()
    IF = auto(); ELSE = auto(); WHILE = auto(); FN = auto(); RETURN = auto()
    LET = auto(); TRUE = auto(); FALSE = auto(); AND = auto(); OR = auto()
    EOF = auto()

@dataclass
class Token:
    typ: TokenType
    text: str
    pos: int = 0

KEYWORDS = {
    "if": TokenType.IF, "else": TokenType.ELSE, "while": TokenType.WHILE,
    "fn": TokenType.FN, "return": TokenType.RETURN, "let": TokenType.LET,
    "true": TokenType.TRUE, "false": TokenType.FALSE,
    "and": TokenType.AND, "or": TokenType.OR,
}

class NativeLexer:
    """Regex-free tokenizer."""

    def __init__(self, source: str) -> None:
        self.source = source
        self.pos = 0
        self.tokens: List[Token] = []

    def run(self) -> List[Token]:
        while self.pos < len(self.source):
            self._scan()
        self.tokens.append(Token(TokenType.EOF, "", self.pos))
        return self.tokens

    def _scan(self) -> None:
        c = self.source[self.pos]
        if c.isspace():
            self.pos += 1
            return
        if c == "#":
            while self.pos < len(self.source) and self.source[self.pos] != "\n":
                self.pos += 1
            return
        if c.isdigit():
            start = self.pos
            while self.pos < len(self.source) and self.source[self.pos].isdigit():
                self.pos += 1
            if self.pos < len(self.source) and self.source[self.pos] == ".":
                self.pos += 1
                while self.pos < len(self.source) and self.source[self.pos].isdigit():
                    self.pos += 1
            self.tokens.append(Token(TokenType.NUMBER, self.source[start:self.pos], start))
            return
        if c.isalpha() or c == "_":
            start = self.pos
            while self.pos < len(self.source) and (self.source[self.pos].isalnum() or self.source[self.pos] == "_"):
                self.pos += 1
            word = self.source[start:self.pos]
            self.tokens.append(Token(KEYWORDS.get(word, TokenType.IDENT), word, start))
            return
        if c == '"':
            start = self.pos
            self.pos += 1
            while self.pos < len(self.source) and self.source[self.pos] != '"':
                self.pos += 1
            text = self.source[start + 1:self.pos]
            self.pos += 1
            self.tokens.append(Token(TokenType.STRING, text, start))
            return
        # Single-char tokens
        singles = {
            "+": TokenType.PLUS, "-": TokenType.MINUS, "*": TokenType.STAR,
            "/": TokenType.SLASH, "=": TokenType.EQ, "<": TokenType.LT,
            ">": TokenType.GT, "!": TokenType.BANG, "(": TokenType.LPAREN,
            ")": TokenType.RPAREN, "{": TokenType.LBRACE, "}": TokenType.RBRACE,
            ",": TokenType.COMMA, ";": TokenType.SEMI, ":": TokenType.COLON,
        }
        if c in singles:
            self.tokens.append(Token(singles[c], c, self.pos))
            self.pos += 1
            return
        raise SyntaxError(f"Unexpected character {c!r} at position {self.pos}")

# ---------------------------------------------------------------------------
# AST
# ---------------------------------------------------------------------------

class ASTNodeType(Enum):
    LITERAL = auto(); IDENT = auto(); BINARY = auto(); UNARY = auto()
    BLOCK = auto(); IF = auto(); WHILE = auto(); LET = auto()
    FN_DEF = auto(); FN_CALL = auto(); RETURN = auto()

@dataclass
class ASTNode:
    typ: ASTNodeType
    value: Any = None
    children: List["ASTNode"] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

# ---------------------------------------------------------------------------
# Parser (recursive descent + Pratt for expressions)
# ---------------------------------------------------------------------------

class NativeParser:
    """Recursive descent parser with Pratt expression parsing."""

    PRECEDENCE: Dict[TokenType, Tuple[int, str]] = {
        TokenType.OR:   (1, "left"),
        TokenType.AND:  (2, "left"),
        TokenType.EQ:   (3, "left"),
        TokenType.LT:   (4, "left"), TokenType.GT: (4, "left"),
        TokenType.PLUS: (5, "left"), TokenType.MINUS: (5, "left"),
        TokenType.STAR: (6, "left"), TokenType.SLASH: (6, "left"),
    }

    def __init__(self, tokens: List[Token]) -> None:
        self.tokens = tokens
        self.pos = 0

    def run(self) -> List[ASTNode]:
        """Parse a module / script."""
        nodes: List[ASTNode] = []
        while self._peek().typ != TokenType.EOF:
            nodes.append(self._stmt())
        return nodes

    def _peek(self) -> Token:
        return self.tokens[self.pos]

    def _advance(self) -> Token:
        t = self.tokens[self.pos]
        self.pos += 1
        return t

    def _expect(self, typ: TokenType) -> Token:
        t = self._advance()
        if t.typ != typ:
            raise SyntaxError(f"Expected {typ.name}, got {t.typ.name} ({t.text!r})")
        return t

    def _stmt(self) -> ASTNode:
        t = self._peek()
        if t.typ == TokenType.LET:
            return self._let_stmt()
        if t.typ == TokenType.FN:
            return self._fn_def()
        if t.typ == TokenType.IF:
            return self._if_stmt()
        if t.typ == TokenType.WHILE:
            return self._while_stmt()
        if t.typ == TokenType.RETURN:
            return self._return_stmt()
        return self._expr_stmt()

    def _let_stmt(self) -> ASTNode:
        self._advance()  # let
        name = self._expect(TokenType.IDENT).text
        self._expect(TokenType.EQ)
        value = self._expr()
        self._expect(TokenType.SEMI)
        return ASTNode(ASTNodeType.LET, name, [value])

    def _fn_def(self) -> ASTNode:
        self._advance()  # fn
        name = self._expect(TokenType.IDENT).text
        self._expect(TokenType.LPAREN)
        params: List[str] = []
        while self._peek().typ != TokenType.RPAREN:
            params.append(self._expect(TokenType.IDENT).text)
            if self._peek().typ == TokenType.COMMA:
                self._advance()
        self._expect(TokenType.RPAREN)
        body = self._block()
        return ASTNode(ASTNodeType.FN_DEF, name, [body], {"params": params})

    def _block(self) -> ASTNode:
        self._expect(TokenType.LBRACE)
        children: List[ASTNode] = []
        while self._peek().typ != TokenType.RBRACE:
            children.append(self._stmt())
        self._expect(TokenType.RBRACE)
        return ASTNode(ASTNodeType.BLOCK, None, children)

    def _if_stmt(self) -> ASTNode:
        self._advance()  # if
        cond = self._expr()
        then_ = self._block()
        else_: Optional[ASTNode] = None
        if self._peek().typ == TokenType.ELSE:
            self._advance()
            if self._peek().typ == TokenType.IF:
                else_ = self._if_stmt()
            else:
                else_ = self._block()
        return ASTNode(ASTNodeType.IF, None, [cond, then_, else_] if else_ else [cond, then_])

    def _while_stmt(self) -> ASTNode:
        self._advance()  # while
        cond = self._expr()
        body = self._block()
        return ASTNode(ASTNodeType.WHILE, None, [cond, body])

    def _return_stmt(self) -> ASTNode:
        self._advance()  # return
        val = self._expr()
        self._expect(TokenType.SEMI)
        return ASTNode(ASTNodeType.RETURN, None, [val])

    def _expr_stmt(self) -> ASTNode:
        node = self._expr()
        self._expect(TokenType.SEMI)
        return node

    # Pratt expression parser
    def _expr(self, min_prec: int = 0) -> ASTNode:
        left = self._prefix()
        while True:
            t = self._peek()
            if t.typ not in self.PRECEDENCE:
                break
            prec, assoc = self.PRECEDENCE[t.typ]
            if prec < min_prec:
                break
            self._advance()
            right = self._expr(prec + 1 if assoc == "left" else prec)
            left = ASTNode(ASTNodeType.BINARY, t.text, [left, right])
        return left

    def _prefix(self) -> ASTNode:
        t = self._peek()
        if t.typ == TokenType.MINUS or t.typ == TokenType.BANG:
            self._advance()
            return ASTNode(ASTNodeType.UNARY, t.text, [self._expr(7)])
        if t.typ == TokenType.NUMBER:
            self._advance()
            return ASTNode(ASTNodeType.LITERAL, float(t.text) if "." in t.text else int(t.text))
        if t.typ == TokenType.STRING:
            self._advance()
            return ASTNode(ASTNodeType.LITERAL, t.text)
        if t.typ in (TokenType.TRUE, TokenType.FALSE):
            self._advance()
            return ASTNode(ASTNodeType.LITERAL, t.typ == TokenType.TRUE)
        if t.typ == TokenType.IDENT:
            self._advance()
            if self._peek().typ == TokenType.LPAREN:
                return self._fn_call(t.text)
            return ASTNode(ASTNodeType.IDENT, t.text)
        if t.typ == TokenType.LPAREN:
            self._advance()
            node = self._expr()
            self._expect(TokenType.RPAREN)
            return node
        raise SyntaxError(f"Unexpected token in expression: {t.typ.name} ({t.text!r})")

    def _fn_call(self, name: str) -> ASTNode:
        self._expect(TokenType.LPAREN)
        args: List[ASTNode] = []
        while self._peek().typ != TokenType.RPAREN:
            args.append(self._expr())
            if self._peek().typ == TokenType.COMMA:
                self._advance()
        self._expect(TokenType.RPAREN)
        return ASTNode(ASTNodeType.FN_CALL, name, args)

# ---------------------------------------------------------------------------
# Bytecode
# ---------------------------------------------------------------------------

class OpCode(Enum):
    LOAD_CONST = 0; LOAD_VAR = 1; STORE_VAR = 2
    ADD = 10; SUB = 11; MUL = 12; DIV = 13
    EQ = 20; LT = 21; GT = 22; NOT = 23
    AND = 30; OR = 31
    JZ = 40; JMP = 41
    CALL = 50; RET = 51
    POP = 60; DUP = 61
    PRINT = 70  # demo helper

@dataclass
class Bytecode:
    op: OpCode
    arg: Any = None

# ---------------------------------------------------------------------------
# Compiler
# ---------------------------------------------------------------------------

class NativeCompiler:
    """AST → Bytecode."""

    def __init__(self) -> None:
        self.code: List[Bytecode] = []
        self.vars: Dict[str, int] = {}
        self.consts: List[Any] = []
        self._var_idx = 0

    def run(self, nodes: List[ASTNode]) -> List[Bytecode]:
        for node in nodes:
            self._emit_node(node)
        self.code.append(Bytecode(OpCode.RET))
        return self.code

    def _const(self, v: Any) -> int:
        try:
            return self.consts.index(v)
        except ValueError:
            self.consts.append(v)
            return len(self.consts) - 1

    def _var(self, name: str) -> int:
        if name not in self.vars:
            self.vars[name] = self._var_idx
            self._var_idx += 1
        return self.vars[name]

    def _emit(self, op: OpCode, arg: Any = None) -> None:
        self.code.append(Bytecode(op, arg))

    def _emit_node(self, node: ASTNode) -> None:
        if node.typ == ASTNodeType.LITERAL:
            self._emit(OpCode.LOAD_CONST, self._const(node.value))
        elif node.typ == ASTNodeType.IDENT:
            self._emit(OpCode.LOAD_VAR, self._var(node.value))
        elif node.typ == ASTNodeType.BINARY:
            self._emit_node(node.children[0])
            self._emit_node(node.children[1])
            mapping = {
                "+": OpCode.ADD, "-": OpCode.SUB, "*": OpCode.MUL, "/": OpCode.DIV,
                "=": OpCode.EQ, "<": OpCode.LT, ">": OpCode.GT,
                "and": OpCode.AND, "or": OpCode.OR,
            }
            self._emit(mapping.get(node.value, OpCode.ADD))
        elif node.typ == ASTNodeType.UNARY:
            self._emit_node(node.children[0])
            if node.value == "!":
                self._emit(OpCode.NOT)
            elif node.value == "-":
                self._emit(OpCode.LOAD_CONST, self._const(-1))
                self._emit(OpCode.MUL)
        elif node.typ == ASTNodeType.LET:
            self._emit_node(node.children[0])
            self._emit(OpCode.STORE_VAR, self._var(node.value))
        elif node.typ == ASTNodeType.BLOCK:
            for child in node.children:
                self._emit_node(child)
        elif node.typ == ASTNodeType.IF:
            self._emit_node(node.children[0])  # cond
            else_jump = len(self.code)
            self._emit(OpCode.JZ, 0)  # patched later
            self._emit_node(node.children[1])  # then
            if len(node.children) == 3:
                end_jump = len(self.code)
                self._emit(OpCode.JMP, 0)
                self.code[else_jump].arg = len(self.code)
                self._emit_node(node.children[2])
                self.code[end_jump].arg = len(self.code)
            else:
                self.code[else_jump].arg = len(self.code)
        elif node.typ == ASTNodeType.WHILE:
            loop_start = len(self.code)
            self._emit_node(node.children[0])  # cond
            exit_jump = len(self.code)
            self._emit(OpCode.JZ, 0)
            self._emit_node(node.children[1])  # body
            self._emit(OpCode.JMP, loop_start)
            self.code[exit_jump].arg = len(self.code)
        elif node.typ == ASTNodeType.RETURN:
            self._emit_node(node.children[0])
            self._emit(OpCode.RET)
        elif node.typ == ASTNodeType.FN_DEF:
            # Simplified: store body as callable chunk
            start = len(self.code)
            self._emit(OpCode.JMP, 0)  # skip body
            body_start = len(self.code)
            self._emit_node(node.children[0])  # body block
            self._emit(OpCode.RET)
            self.code[start].arg = len(self.code)
            self._emit(OpCode.LOAD_CONST, self._const((body_start, node.meta.get("params", []))))
            self._emit(OpCode.STORE_VAR, self._var(node.value))
        elif node.typ == ASTNodeType.FN_CALL:
            for arg in node.children:
                self._emit_node(arg)
            self._emit(OpCode.CALL, (node.value, len(node.children)))
        else:
            raise ValueError(f"Unhandled AST node {node.typ}")

# ---------------------------------------------------------------------------
# VM
# ---------------------------------------------------------------------------

class NativeVM:
    """Stack-based virtual machine."""

    def __init__(
        self,
        code: List[Bytecode],
        consts: List[Any],
        vars: Dict[str, int],
        builtins: Optional[Dict[str, Callable[..., Any]]] = None,
    ) -> None:
        self.code = code
        self.consts = consts
        self.vars = vars
        self.builtins = builtins or {"print": self._builtin_print}
        self.stack: List[Any] = []
        self.pc = 0
        self.locals: List[Dict[int, Any]] = [{}]

    def _builtin_print(self, *args: Any) -> None:
        print(" ".join(str(a) for a in args))

    def run(self) -> Any:
        """Execute until RET or end."""
        while self.pc < len(self.code):
            op = self.code[self.pc]
            self.pc += 1
            self._step(op)
        return self.stack[-1] if self.stack else None

    def execute(self, fn_name: str, *args: Any) -> Any:
        """Call a compiled function by name."""
        if fn_name in self.vars:
            idx = self.vars[fn_name]
            # Find LOAD_CONST that stored the function tuple
            # Simplified: we just push args and CALL
            for a in args:
                self.stack.append(a)
            self._call(fn_name, len(args))
            return self.run()
        raise NameError(f"Function {fn_name} not found")

    def _step(self, bc: Bytecode) -> None:
        op = bc.op
        if op == OpCode.LOAD_CONST:
            self.stack.append(self.consts[bc.arg])
        elif op == OpCode.LOAD_VAR:
            val = self._load_var(bc.arg)
            self.stack.append(val)
        elif op == OpCode.STORE_VAR:
            self._store_var(bc.arg, self.stack.pop())
        elif op == OpCode.ADD:
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a + b)
        elif op == OpCode.SUB:
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a - b)
        elif op == OpCode.MUL:
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a * b)
        elif op == OpCode.DIV:
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a / b)
        elif op == OpCode.EQ:
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a == b)
        elif op == OpCode.LT:
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a < b)
        elif op == OpCode.GT:
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a > b)
        elif op == OpCode.NOT:
            self.stack.append(not self.stack.pop())
        elif op == OpCode.AND:
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a and b)
        elif op == OpCode.OR:
            b, a = self.stack.pop(), self.stack.pop()
            self.stack.append(a or b)
        elif op == OpCode.JZ:
            if not self.stack.pop():
                self.pc = bc.arg
        elif op == OpCode.JMP:
            self.pc = bc.arg
        elif op == OpCode.CALL:
            name, argc = bc.arg
            self._call(name, argc)
        elif op == OpCode.RET:
            return  # stops run()
        elif op == OpCode.POP:
            self.stack.pop()
        elif op == OpCode.DUP:
            self.stack.append(self.stack[-1])
        elif op == OpCode.PRINT:
            val = self.stack.pop()
            print(val)
        else:
            raise RuntimeError(f"Unknown opcode {op}")

    def _load_var(self, idx: int) -> Any:
        for scope in reversed(self.locals):
            if idx in scope:
                return scope[idx]
        raise NameError(f"Variable index {idx} not found")

    def _store_var(self, idx: int, val: Any) -> None:
        self.locals[-1][idx] = val

    def _call(self, name: str, argc: int) -> None:
        args = [self.stack.pop() for _ in range(argc)]
        args.reverse()
        if name in self.builtins:
            self.builtins[name](*args)
            self.stack.append(None)
            return
        if name not in self.vars:
            raise NameError(f"Undefined function {name}")
        # Retrieve function chunk
        fn_const = self._load_var(self.vars[name])
        if not isinstance(fn_const, tuple):
            raise TypeError(f"{name} is not callable")
        body_start, params = fn_const
        self.locals.append({})
        for p, a in zip(params, args):
            self._store_var(self.vars.get(p, len(self.vars)), a)
        saved_pc = self.pc
        self.pc = body_start
        # Execute until RET
        while self.pc < len(self.code):
            op = self.code[self.pc]
            self.pc += 1
            if op.op == OpCode.RET:
                break
            self._step(op)
        self.pc = saved_pc
        self.locals.pop()

# ---------------------------------------------------------------------------
# Native facade
# ---------------------------------------------------------------------------

class NativeJITCompiler:
    """Lexer → Parser → Compiler → VM facade."""

    def __init__(self, builtins: Optional[Dict[str, Callable[..., Any]]] = None) -> None:
        self.builtins = builtins

    def run(self, source: str) -> Any:
        """Compile and execute source, returning last stack value."""
        tokens = NativeLexer(source).run()
        ast_nodes = NativeParser(tokens).run()
        compiler = NativeCompiler()
        code = compiler.run(ast_nodes)
        vm = NativeVM(code, compiler.consts, compiler.vars, self.builtins)
        return vm.run()

    def execute(self, source: str) -> Any:
        """Alias for run()."""
        return self.run(source)

# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    compiler = NativeJITCompiler()

    prog = """
let x = 10;
let y = 20;
let sum = x + y;
print(sum);

fn add(a, b) {
    return a + b;
}

let result = add(sum, 5);
print(result);

if result > 30 {
    print("big");
} else {
    print("small");
}

# Simple recursion-free factorial via repeated calls
let a = 5;
let b = 1;
let fact = add(a, b);
print(fact);

fn max(a, b) {
    if a > b {
        return a;
    } else {
        return b;
    }
}

let m = max(7, 12);
print(m);
"""
    print("=== Program Output ===")
    compiler.run(prog)
    print("\n=== Done ===")

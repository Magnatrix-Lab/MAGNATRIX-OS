#!/usr/bin/env python3
"""
Template Engine for MAGNATRIX-OS
Lightweight Jinja-like string templating with variable substitution,
conditionals, loops, and filters. Native stdlib only.

Author: MAGNATRIX-OS Core Infrastructure
License: MIT (Open Source)
"""

from __future__ import annotations

import dataclasses
import enum
import re
from typing import Any, Callable, Dict, List, Optional


class TokenType(enum.Enum):
    TEXT = "text"
    VAR = "var"
    IF = "if"
    ENDIF = "endif"
    FOR = "for"
    ENDFOR = "endfor"
    FILTER = "filter"
    COMMENT = "comment"


@dataclasses.dataclass
class Token:
    type: TokenType
    value: str


class TemplateEngine:
    """Lightweight template engine with {{ var }}, {% if %}, {% for %}, and filters."""

    _FILTER_MAP: Dict[str, Callable[[Any], str]] = {
        "upper": lambda x: str(x).upper(),
        "lower": lambda x: str(x).lower(),
        "title": lambda x: str(x).title(),
        "trim": lambda x: str(x).strip(),
        "length": lambda x: str(len(x)),
        "default": lambda x, y="": str(x) if x else str(y),
        "join": lambda x, sep=", ": sep.join(str(i) for i in x),
        "first": lambda x: str(next(iter(x), "")),
        "last": lambda x: str(list(x)[-1]) if x else "",
        "int": lambda x: str(int(x)) if x else "0",
        "float": lambda x: str(float(x)) if x else "0.0",
        "json": lambda x: str(x).replace("'", "\""),
        "yesno": lambda x, y="yes,no,maybe": y.split(",")[0] if x else y.split(",")[1] if len(y.split(",")) > 1 else "no",
        "escape": lambda x: str(x).replace("<", "&lt;").replace(">", "&gt;").replace("\"", "&quot;"),
        "truncate": lambda x, n=50: str(x)[:int(n)] + "..." if len(str(x)) > int(n) else str(x),
    }

    def __init__(self) -> None:
        self._filters: Dict[str, Callable[[Any], str]] = dict(self._FILTER_MAP)

    # ------------------------------------------------------------------
    # Filter registration
    # ------------------------------------------------------------------

    def register_filter(self, name: str, fn: Callable[[Any], str]) -> None:
        self._filters[name] = fn

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _tokenize(self, template: str) -> List[Token]:
        tokens = []
        i = 0
        while i < len(template):
            if template[i:i+2] == "{{":
                end = template.find("}}", i)
                if end == -1:
                    break
                tokens.append(Token(TokenType.VAR, template[i+2:end].strip()))
                i = end + 2
            elif template[i:i+2] == "{%":
                end = template.find("%}", i)
                if end == -1:
                    break
                content = template[i+2:end].strip()
                if content.startswith("if "):
                    tokens.append(Token(TokenType.IF, content[3:].strip()))
                elif content == "endif":
                    tokens.append(Token(TokenType.ENDIF, ""))
                elif content.startswith("for "):
                    tokens.append(Token(TokenType.FOR, content[4:].strip()))
                elif content == "endfor":
                    tokens.append(Token(TokenType.ENDFOR, ""))
                elif content.startswith("#"):
                    tokens.append(Token(TokenType.COMMENT, ""))
                else:
                    tokens.append(Token(TokenType.TEXT, template[i:end+2]))
                i = end + 2
            elif template[i:i+2] == "{#":
                end = template.find("#}", i)
                if end == -1:
                    break
                tokens.append(Token(TokenType.COMMENT, ""))
                i = end + 2
            else:
                # Find next tag
                next_tag = min(
                    [x for x in [template.find("{{", i), template.find("{%", i), template.find("{#", i)] if x != -1],
                    default=len(template)
                )
                tokens.append(Token(TokenType.TEXT, template[i:next_tag]))
                i = next_tag
        return tokens

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _resolve_var(self, name: str, context: Dict[str, Any]) -> Any:
        parts = name.split(".")
        value = context
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part, "")
            elif hasattr(value, part):
                value = getattr(value, part)
            else:
                return ""
        return value

    def _apply_filter(self, value: Any, filter_chain: str) -> str:
        for fspec in filter_chain.split("|"):
            fspec = fspec.strip()
            if not fspec:
                continue
            if "(" in fspec:
                fname, args_str = fspec.split("(", 1)
                args_str = args_str.rstrip(")")
                args = [a.strip().strip("'\"").strip('"') for a in args_str.split(",")]
                fn = self._filters.get(fname.strip())
                if fn:
                    value = fn(value, *args)
            else:
                fn = self._filters.get(fspec)
                if fn:
                    value = fn(value)
        return str(value)

    def _eval_condition(self, expr: str, context: Dict[str, Any]) -> bool:
        expr = expr.strip()
        # Simple boolean: variable name
        if expr.startswith("not "):
            val = self._resolve_var(expr[4:], context)
            return not bool(val)
        if "==" in expr:
            left, right = expr.split("==", 1)
            left = self._resolve_var(left.strip(), context)
            right = right.strip().strip("'\"").strip('"')
            return str(left) == right
        if "!=" in expr:
            left, right = expr.split("!=", 1)
            left = self._resolve_var(left.strip(), context)
            right = right.strip().strip("'\"").strip('"')
            return str(left) != right
        val = self._resolve_var(expr, context)
        return bool(val)

    def _parse_for(self, expr: str) -> Tuple[str, str]:
        # "item in items"
        match = re.match(r"(\w+)\s+in\s+(.+)", expr)
        if match:
            return match.group(1), match.group(2).strip()
        return "", ""

    def render(self, template: str, context: Dict[str, Any]) -> str:
        tokens = self._tokenize(template)
        output = []
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            if tok.type == TokenType.TEXT:
                output.append(tok.value)
            elif tok.type == TokenType.VAR:
                var_expr = tok.value
                # Check for filter chain
                if "|" in var_expr:
                    var_name, filter_chain = var_expr.split("|", 1)
                    value = self._resolve_var(var_name.strip(), context)
                    output.append(self._apply_filter(value, filter_chain))
                else:
                    value = self._resolve_var(var_expr, context)
                    output.append(str(value))
            elif tok.type == TokenType.IF:
                condition = tok.value
                # Find matching endif
                block_start = i + 1
                depth = 1
                block_end = block_start
                for j in range(block_start, len(tokens)):
                    if tokens[j].type == TokenType.IF:
                        depth += 1
                    elif tokens[j].type == TokenType.ENDIF:
                        depth -= 1
                        if depth == 0:
                            block_end = j
                            break
                if self._eval_condition(condition, context):
                    output.append(self._render_block(tokens[block_start:block_end], context))
                i = block_end
            elif tok.type == TokenType.FOR:
                for_expr = tok.value
                var_name, collection_name = self._parse_for(for_expr)
                collection = self._resolve_var(collection_name, context)
                # Find matching endfor
                block_start = i + 1
                depth = 1
                block_end = block_start
                for j in range(block_start, len(tokens)):
                    if tokens[j].type == TokenType.FOR:
                        depth += 1
                    elif tokens[j].type == TokenType.ENDFOR:
                        depth -= 1
                        if depth == 0:
                            block_end = j
                            break
                if isinstance(collection, (list, tuple, dict)):
                    if isinstance(collection, dict):
                        items = collection.items()
                    else:
                        items = collection
                    for item in items:
                        if isinstance(collection, dict):
                            loop_ctx = {**context, var_name: {"key": item[0], "value": item[1]}}
                        else:
                            loop_ctx = {**context, var_name: item}
                        output.append(self._render_block(tokens[block_start:block_end], loop_ctx))
                i = block_end
            i += 1
        return "".join(output)

    def _render_block(self, tokens: List[Token], context: Dict[str, Any]) -> str:
        return self.render("".join(t.value if t.type == TokenType.TEXT else self._reconstruct_tag(t) for t in tokens), context)

    def _reconstruct_tag(self, token: Token) -> str:
        if token.type == TokenType.VAR:
            return f"{{{{ {token.value} }}}}"
        elif token.type == TokenType.IF:
            return f"{{% if {token.value} %}}"
        elif token.type == TokenType.ENDIF:
            return "{% endif %}"
        elif token.type == TokenType.FOR:
            return f"{{% for {token.value} %}}"
        elif token.type == TokenType.ENDFOR:
            return "{% endfor %}"
        return ""

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def render_string(self, template: str, **kwargs: Any) -> str:
        return self.render(template, kwargs)


# ---------------------------------------------------------------------------
# Self-contained demo
# ---------------------------------------------------------------------------

def _demo() -> None:
    engine = TemplateEngine()
    print("=== Template Engine Demo ===\n")
    # Simple variable
    tmpl = "Hello, {{ name }}!"
    print(engine.render(tmpl, {"name": "MAGNATRIX"}))
    # Filters
    tmpl = "Name: {{ name | upper }} | Length: {{ items | length }}"
    print(engine.render(tmpl, {"name": "test", "items": [1, 2, 3]}))
    # Conditionals
    tmpl = "{% if user %}Welcome, {{ user }}{% else %}Please login{% endif %}"
    print(engine.render(tmpl, {"user": "admin"}))
    print(engine.render(tmpl, {"user": ""}))
    # Loops
    tmpl = "Items: {% for item in items %}{{ item }}{% endfor %}"
    print(engine.render(tmpl, {"items": ["a", "b", "c"]}))
    # Dict loops
    tmpl = "{% for item in config %}{{ item.key }}={{ item.value }};{% endfor %}"
    print(engine.render(tmpl, {"config": {"host": "localhost", "port": 8080}}))
    # Complex
    tmpl = "{{ title | title }} | {{ desc | truncate(20) }} | {{ count | default(0) }}"
    print(engine.render(tmpl, {"title": "magnatrix os", "desc": "This is a very long description that should be truncated", "count": 42}))


if __name__ == "__main__":
    _demo()

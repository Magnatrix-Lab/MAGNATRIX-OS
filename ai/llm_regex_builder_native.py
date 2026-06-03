"""LLM Regex Builder — Native Python (stdlib only)."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class RegexType(Enum):
    LITERAL = auto()
    DIGIT = auto()
    WORD = auto()
    WHITESPACE = auto()
    ANY = auto()
    RANGE = auto()
    GROUP = auto()
    OPTIONAL = auto()
    REPEAT = auto()
    ALTERNATE = auto()

class RegexBuilder:
    def __init__(self) -> None:
        self._parts: List[str] = []

    def literal(self, text: str) -> "RegexBuilder":
        self._parts.append(re.escape(text))
        return self

    def digit(self, count: Optional[int] = None) -> "RegexBuilder":
        self._parts.append("\\d" + ("{" + str(count) + "}" if count else "+"))
        return self

    def word(self, count: Optional[int] = None) -> "RegexBuilder":
        self._parts.append("\\w" + ("{" + str(count) + "}" if count else "+"))
        return self

    def whitespace(self, count: Optional[int] = None) -> "RegexBuilder":
        self._parts.append("\\s" + ("{" + str(count) + "}" if count else "+"))
        return self

    def any_char(self, count: Optional[int] = None) -> "RegexBuilder":
        self._parts.append("." + ("{" + str(count) + "}" if count else "+"))
        return self

    def range_chars(self, chars: str) -> "RegexBuilder":
        self._parts.append("[" + chars + "]+")
        return self

    def group(self, inner: str, optional: bool = False) -> "RegexBuilder":
        self._parts.append("(" + inner + ")" + ("?" if optional else ""))
        return self

    def alternate(self, *options: str) -> "RegexBuilder":
        self._parts.append("(" + "|".join(options) + ")")
        return self

    def build(self) -> str:
        return "".join(self._parts)

    def test(self, pattern: str, text: str) -> bool:
        return bool(re.search(pattern, text))

    def find_all(self, pattern: str, text: str) -> List[str]:
        return re.findall(pattern, text)

    def replace(self, pattern: str, text: str, replacement: str) -> str:
        return re.sub(pattern, replacement, text)

    def get_stats(self) -> Dict[str, Any]:
        return {"parts": len(self._parts)}

def run() -> None:
    print("Regex Builder test")
    e = RegexBuilder()
    pattern = e.literal("Hello").whitespace().word().build()
    print("  Pattern: " + pattern)
    print("  Test 'Hello world': " + str(e.test(pattern, "Hello world")))
    e2 = RegexBuilder()
    email_pattern = e2.word().literal("@").word().literal(".").word().build()
    print("  Email pattern: " + email_pattern)
    print("  Find all: " + str(e2.find_all(r"\b\w+@\w+\.\w+\b", "Contact alice@test.com or bob@demo.org")))
    print("  Replace: " + e2.replace(r"\d+", "abc123def", "[NUM]"))
    print("  Stats: " + str(e.get_stats()))
    print("Regex Builder test complete.")

if __name__ == "__main__":
    run()

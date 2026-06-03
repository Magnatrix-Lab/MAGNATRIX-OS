"""LLM Tokenizer Engine — Native Python (stdlib only)."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Set
from enum import Enum, auto

class TokenType(Enum):
    WORD = auto()
    NUMBER = auto()
    PUNCTUATION = auto()
    WHITESPACE = auto()
    SYMBOL = auto()
    URL = auto()
    EMAIL = auto()
    MENTION = auto()
    HASHTAG = auto()

@dataclass
class Token:
    text: str
    token_type: TokenType
    position: int
    length: int
    metadata: Dict[str, Any] = field(default_factory=dict)

class TokenizerEngine:
    def __init__(self) -> None:
        self._token_patterns: List[tuple] = [
            (TokenType.URL, re.compile(r'https?://\S+')),
            (TokenType.EMAIL, re.compile(r'[\w.-]+@[\w.-]+\.\w+')),
            (TokenType.MENTION, re.compile(r'@\w+')),
            (TokenType.HASHTAG, re.compile(r'#\w+')),
            (TokenType.NUMBER, re.compile(r'\d+\.?\d*')),
            (TokenType.WORD, re.compile(r'\w+')),
            (TokenType.PUNCTUATION, re.compile(r'[.,;:!?"\'()\[\]{}]')),
            (TokenType.WHITESPACE, re.compile(r'\s+')),
            (TokenType.SYMBOL, re.compile(r'[^\w\s]')),
        ]

    def tokenize(self, text: str) -> List[Token]:
        tokens = []
        pos = 0
        while pos < len(text):
            matched = False
            for token_type, pattern in self._token_patterns:
                match = pattern.match(text, pos)
                if match:
                    tokens.append(Token(match.group(), token_type, pos, len(match.group())))
                    pos += len(match.group())
                    matched = True
                    break
            if not matched:
                tokens.append(Token(text[pos], TokenType.SYMBOL, pos, 1))
                pos += 1
        return tokens

    def tokenize_words(self, text: str) -> List[str]:
        return [t.text for t in self.tokenize(text) if t.token_type == TokenType.WORD]

    def tokenize_sentences(self, text: str) -> List[str]:
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def get_token_stats(self, tokens: List[Token]) -> Dict[str, Any]:
        counts = {}
        for t in tokens:
            counts[t.token_type.name] = counts.get(t.token_type.name, 0) + 1
        return {"total": len(tokens), "by_type": counts, "unique_words": len(set(t.text.lower() for t in tokens if t.token_type == TokenType.WORD))}

    def run(self) -> None:
        print("Tokenizer Engine test")
        e = TokenizerEngine()
        text = "Hello @user, visit https://example.com or email test@mail.com #AI"
        tokens = e.tokenize(text)
        for t in tokens:
            print("  " + t.token_type.name + ": '" + t.text + "' at " + str(t.position))
        print("  Words: " + str(e.tokenize_words(text)))
        print("  Stats: " + str(e.get_token_stats(tokens)))
        print("Tokenizer Engine test complete.")

if __name__ == "__main__":
    TokenizerEngine().run()

"""Text Tokenizer — word, sentence, subword tokenization, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
from enum import Enum, auto
import re

class Tokenizer:
    def __init__(self):
        self.vocab: Dict[str, int] = {}
        self.next_id = 0

    def _get_id(self, token: str) -> int:
        if token not in self.vocab:
            self.vocab[token] = self.next_id
            self.next_id += 1
        return self.vocab[token]

    def word_tokenize(self, text: str) -> List[int]:
        words = re.findall(r"\w+", text.lower())
        return [self._get_id(w) for w in words]

    def sentence_tokenize(self, text: str) -> List[str]:
        return [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]

    def subword_tokenize(self, text: str, max_len: int = 5) -> List[int]:
        text = text.lower()
        tokens = []
        i = 0
        while i < len(text):
            for j in range(min(len(text), i + max_len), i, -1):
                sub = text[i:j]
                if sub in self.vocab or j - i == 1:
                    tokens.append(self._get_id(sub))
                    i = j
                    break
            else:
                i += 1
        return tokens

    def decode(self, ids: List[int]) -> List[str]:
        rev = {v: k for k, v in self.vocab.items()}
        return [rev.get(i, "<?>") for i in ids]

    def stats(self) -> Dict:
        return {"vocab_size": len(self.vocab)}

def run():
    tok = Tokenizer()
    text = "Hello world! Hello everyone."
    print(tok.word_tokenize(text))
    print(tok.sentence_tokenize(text))
    print(tok.decode(tok.word_tokenize(text)))
    print(tok.stats())

if __name__ == "__main__":
    run()

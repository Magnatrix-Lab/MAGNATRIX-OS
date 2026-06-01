"""uncensored/censorship_bypass_v2_native.py — Censorship bypass engine"""
from __future__ import annotations
import base64
import random
import string
from typing import Optional, List

class CensorshipBypass:
    """Bypass content censorship using multiple techniques."""

    TECHNIQUES = ["base64", "rot13", "fragmentation", "mimicry", "homoglyph"]

    @staticmethod
    def rot13(text: str) -> str:
        result = []
        for c in text:
            if 'a' <= c <= 'z':
                result.append(chr((ord(c) - ord('a') + 13) % 26 + ord('a')))
            elif 'A' <= c <= 'Z':
                result.append(chr((ord(c) - ord('A') + 13) % 26 + ord('A')))
            else:
                result.append(c)
        return ''.join(result)

    @staticmethod
    def base64_junk(text: str) -> str:
        encoded = base64.b64encode(text.encode()).decode()
        junk = ''.join(random.choices(string.ascii_letters, k=10))
        return f"{junk[:5]}{encoded}{junk[5:]}"

    @staticmethod
    def fragment(text: str, chunk_size: int = 4) -> List[str]:
        return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

    @staticmethod
    def mimicry(text: str) -> str:
        homoglyphs = {
            'a': 'а', 'e': 'е', 'o': 'о', 'p': 'р', 'c': 'с',
            'x': 'х', 'y': 'у', 'k': 'к', 't': 'т', 'h': 'н',
        }
        result = []
        for c in text.lower():
            if c in homoglyphs and random.random() > 0.5:
                result.append(homoglyphs[c])
            else:
                result.append(c)
        return ''.join(result)

    def bypass(self, text: str, technique: str = "auto") -> str:
        if technique == "auto":
            technique = random.choice(self.TECHNIQUES)

        if technique == "base64":
            return self.base64_junk(text)
        elif technique == "rot13":
            return self.rot13(text)
        elif technique == "fragmentation":
            return ' '.join(self.fragment(text))
        elif technique == "mimicry":
            return self.mimicry(text)
        else:
            return text

if __name__ == "__main__":
    print("CensorshipBypass self-test")
    cb = CensorshipBypass()
    original = "hello world"
    bypassed = cb.bypass(original, "rot13")
    assert bypassed != original
    print("All tests pass")

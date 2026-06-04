"""Audio Text Aligner - Speech-text alignment for MAGNATRIX-OS."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Tuple

@dataclass
class AudioTextAligner:
    phoneme_map: Dict[str, List[str]] = field(default_factory=dict)

    def __post_init__(self):
        if not self.phoneme_map:
            self.phoneme_map = {"hello": ["h", "eh", "l", "ow"], "world": ["w", "er", "l", "d"], "ai": ["ey", "ay"]}

    def align(self, phonemes: List[str], words: List[str]) -> List[Tuple[str, int, int]]:
        alignments = []
        pos = 0
        for word in words:
            expected = self.phoneme_map.get(word.lower(), [])
            if not expected: continue
            start = pos
            for i in range(pos, len(phonemes)):
                if phonemes[i] in expected:
                    pos = i + 1
                    break
            alignments.append((word, start, pos))
        return alignments

    def stats(self) -> dict:
        return {"phonemes": len(self.phoneme_map), "words": list(self.phoneme_map.keys())}

def run():
    ata = AudioTextAligner()
    phonemes = ["h", "eh", "l", "ow", "w", "er", "l", "d"]
    words = ["hello", "world"]
    print("Align:", ata.align(phonemes, words))
    print("Stats:", ata.stats())

if __name__ == "__main__": run()

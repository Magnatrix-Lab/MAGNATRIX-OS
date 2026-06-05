"""Native stdlib module: Word Counter
Counts words, characters, sentences, and reading time for manuscripts.
"""
from dataclasses import dataclass
from typing import Dict

@dataclass
class WordCounter:
    text: str
    words_per_minute: int = 250

    def word_count(self) -> int:
        return len(self.text.split())

    def char_count(self) -> int:
        return len(self.text)

    def char_count_no_spaces(self) -> int:
        return len(self.text.replace(" ", "").replace("\n", ""))

    def sentence_count(self) -> int:
        return max(1, self.text.count(".") + self.text.count("!") + self.text.count("?"))

    def avg_words_per_sentence(self) -> float:
        return self.word_count() / self.sentence_count()

    def reading_time_min(self) -> float:
        if self.words_per_minute == 0:
            return 0.0
        return self.word_count() / self.words_per_minute

    def stats(self) -> Dict[str, float]:
        return {
            "word_count": self.word_count(),
            "char_count": self.char_count(),
            "char_count_no_spaces": self.char_count_no_spaces(),
            "sentence_count": self.sentence_count(),
            "avg_words_per_sentence": round(self.avg_words_per_sentence(), 1),
            "reading_time_min": round(self.reading_time_min(), 1),
        }

def run():
    wc = WordCounter(text="The quick brown fox jumps over the lazy dog. It was a bright cold day in April, and the clocks were striking thirteen.")
    print(wc.stats())

if __name__ == "__main__":
    run()

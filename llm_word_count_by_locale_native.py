"""Native stdlib module: Word Count by Locale
Estimates word expansion rates for translation target languages.
"""
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class LocaleExpansion:
    locale_code: str
    expansion_rate: float
    avg_word_length: float

@dataclass
class WordCountByLocale:
    source_word_count: int
    source_locale: str
    target_locales: List[LocaleExpansion] = field(default_factory=list)

    def estimated_word_counts(self) -> Dict[str, int]:
        return {l.locale_code: int(self.source_word_count * l.expansion_rate) for l in self.target_locales}

    def longest_locale(self) -> str:
        if not self.target_locales:
            return ""
        counts = self.estimated_word_counts()
        return max(counts, key=counts.get)

    def total_target_words(self) -> int:
        return sum(self.estimated_word_counts().values())

    def stats(self) -> Dict:
        return {
            "source_words": self.source_word_count,
            "estimated_by_locale": self.estimated_word_counts(),
            "longest_locale": self.longest_locale(),
            "total_target_words": self.total_target_words(),
        }

def run():
    wcl = WordCountByLocale(
        source_word_count=10000,
        source_locale="en",
        target_locales=[
            LocaleExpansion("de", 1.15, 6.5),
            LocaleExpansion("fr", 1.08, 5.8),
            LocaleExpansion("ja", 0.85, 3.2),
            LocaleExpansion("es", 1.12, 5.5),
            LocaleExpansion("ru", 1.20, 6.8),
        ]
    )
    print(wcl.stats())

if __name__ == "__main__":
    run()

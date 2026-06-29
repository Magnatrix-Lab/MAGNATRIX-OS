"""NLP Machine Translation -- Rule-based phrase translation, dictionary lookup."""
from dataclasses import dataclass
from pathlib import Path
import json, re

@dataclass
class TranslationResult:
    translation_id: str = ""
    source: str = ""
    target: str = ""
    source_lang: str = ""
    target_lang: str = ""
    translated: str = ""
    confidence: float = 0.0

class NLPMachineTranslation:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._dictionary: dict[str, dict[str, str]] = {}
        self._results: list[TranslationResult] = []
        self._persist_path = self.root / "nlp_translation.json"
        self._load()
        if not self._dictionary:
            self._seed_dictionary()

    def _seed_dictionary(self) -> None:
        self._dictionary = {
            "en-es": {
                "hello": "hola", "world": "mundo", "cat": "gato", "dog": "perro",
                "the": "el", "a": "un", "is": "es", "are": "son", "and": "y",
                "I": "yo", "you": "tu", "he": "el", "she": "ella", "we": "nosotros",
                "love": "amar", "eat": "comer", "run": "correr", "walk": "caminar",
                "big": "grande", "small": "pequeno", "happy": "feliz", "sad": "triste",
            },
            "en-fr": {
                "hello": "bonjour", "world": "monde", "cat": "chat", "dog": "chien",
                "the": "le", "a": "un", "is": "est", "are": "sont", "and": "et",
                "I": "je", "you": "tu", "he": "il", "she": "elle", "we": "nous",
                "love": "aimer", "eat": "manger", "run": "courir", "walk": "marcher",
                "big": "grand", "small": "petit", "happy": "heureux", "sad": "triste",
            },
        }

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._dictionary = data.get("dictionary", {})
            self._results = [TranslationResult(**r) for r in data.get("results", [])]

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "dictionary": self._dictionary,
            "results": [r.__dict__ for r in self._results]
        }, indent=2))

    def translate(self, text: str, source_lang: str = "en", target_lang: str = "es") -> TranslationResult:
        key = f"{source_lang}-{target_lang}"
        dict_map = self._dictionary.get(key, {})
        words = re.findall(r'\b\w+\b', text)
        translated = []
        for w in words:
            w_lower = w.lower()
            if w_lower in dict_map:
                translated_word = dict_map[w_lower]
                if w[0].isupper():
                    translated_word = translated_word.capitalize()
                translated.append(translated_word)
            else:
                translated.append(w)
        result = TranslationResult(
            translation_id=f"trans_{len(self._results)}",
            source=text, target=" ".join(translated),
            source_lang=source_lang, target_lang=target_lang,
            translated=" ".join(translated),
            confidence=0.7 if translated else 0.3
        )
        self._results.append(result)
        self._save()
        return result

    def add_word(self, source_lang: str, target_lang: str, source_word: str, target_word: str) -> None:
        key = f"{source_lang}-{target_lang}"
        if key not in self._dictionary:
            self._dictionary[key] = {}
        self._dictionary[key][source_word] = target_word
        self._save()

    def to_dict(self) -> dict:
        return {"dictionary_pairs": sum(len(d) for d in self._dictionary.values()), "translation_count": len(self._results)}

    def get_stats(self) -> dict:
        by_lang = {}
        for r in self._results:
            key = f"{r.source_lang}-{r.target_lang}"
            by_lang[key] = by_lang.get(key, 0) + 1
        return {"translations": len(self._results), "by_language_pair": by_lang}

__all__ = ["NLPMachineTranslation", "TranslationResult"]

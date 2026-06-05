"""Emotion Classifier — basic emotions, valence-arousal, rule-based, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import re

@dataclass
class EmotionClassifier:
    emotion_words: Dict[str, List[str]] = field(default_factory=lambda: {
        "joy": ["happy", "joy", "delighted", "excited", "great"],
        "sadness": ["sad", "depressed", "grief", "sorrow", "melancholy"],
        "anger": ["angry", "furious", "rage", "irritated", "annoyed"],
        "fear": ["afraid", "scared", "terrified", "anxious", "worried"],
        "surprise": ["surprised", "amazed", "astonished", "shocked"],
        "disgust": ["disgusted", "revolted", "repulsed", "sickened"]
    })
    valence_words: Dict[str, float] = field(default_factory=lambda: {
        "good": 0.8, "bad": -0.8, "love": 0.9, "hate": -0.9, "excellent": 1.0, "terrible": -1.0
    })

    def classify(self, text: str) -> Dict[str, float]:
        words = set(re.findall(r'\w+', text.lower()))
        scores = {emotion: sum(1 for w in words if w in words_list) for emotion, words_list in self.emotion_words.items()}
        total = sum(scores.values())
        if total == 0:
            return {e: 0.0 for e in scores}
        return {emotion: count / total for emotion, count in scores.items()}

    def valence_arousal(self, text: str) -> Tuple[float, float]:
        words = set(re.findall(r'\w+', text.lower()))
        valence = sum(self.valence_words.get(w, 0) for w in words)
        arousal = sum(1 for w in words if w in {"excited", "angry", "terrified", "amazed"})
        return valence, arousal

    def dominant_emotion(self, text: str) -> str:
        scores = self.classify(text)
        return max(scores, key=scores.get)

    def stats(self, text: str) -> Dict:
        return {"dominant": self.dominant_emotion(text), "valence_arousal": self.valence_arousal(text)}

def run():
    ec = EmotionClassifier()
    text = "I am so happy and excited today!"
    print("Classify:", ec.classify(text))
    print("Dominant:", ec.dominant_emotion(text))
    print(ec.stats(text))

if __name__ == "__main__":
    run()

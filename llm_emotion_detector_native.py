"""Emotion Detector — multi-emotion classification, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import re
import math

class EmotionType(Enum):
    JOY = auto()
    SADNESS = auto()
    ANGER = auto()
    FEAR = auto()
    SURPRISE = auto()
    DISGUST = auto()
    TRUST = auto()
    ANTICIPATION = auto()

@dataclass
class EmotionResult:
    text: str
    dominant: EmotionType
    scores: Dict[str, float]
    intensity: float

class EmotionDetector:
    def __init__(self):
        self.lexicon = {
            EmotionType.JOY: {"joy", "happy", "cheerful", "delighted", "glad", "elated", "blissful", "excited"},
            EmotionType.SADNESS: {"sad", "depressed", "gloomy", "melancholy", "sorrowful", "unhappy", "miserable"},
            EmotionType.ANGER: {"angry", "furious", "irritated", "annoyed", "enraged", "mad", "hostile"},
            EmotionType.FEAR: {"afraid", "scared", "terrified", "anxious", "worried", "nervous", "panic"},
            EmotionType.SURPRISE: {"surprised", "amazed", "astonished", "shocked", "stunned", "bewildered"},
            EmotionType.DISGUST: {"disgusted", "repulsed", "revolted", "sickened", "nauseated", "appalled"},
            EmotionType.TRUST: {"trust", "confident", "reliable", "faithful", "loyal", "secure"},
            EmotionType.ANTICIPATION: {"expect", "anticipate", "hope", "eager", "enthusiastic", "curious"},
        }
        self.emotion_weights = {e: 1.0 for e in EmotionType}

    def detect(self, text: str) -> EmotionResult:
        words = re.findall(r"\w+", text.lower())
        scores = {e.name: 0.0 for e in EmotionType}
        for word in words:
            for emotion, keywords in self.lexicon.items():
                if word in keywords:
                    scores[emotion.name] += self.emotion_weights[emotion]
        total = sum(scores.values())
        if total > 0:
            scores = {k: v / total for k, v in scores.items()}
        dominant = max(EmotionType, key=lambda e: scores[e.name])
        intensity = max(scores.values())
        return EmotionResult(text, dominant, scores, intensity)

    def detect_batch(self, texts: List[str]) -> List[EmotionResult]:
        return [self.detect(t) for t in texts]

    def set_emotion_weight(self, emotion: EmotionType, weight: float):
        self.emotion_weights[emotion] = weight

    def stats(self) -> Dict:
        return {"emotions": len(self.lexicon), "total_keywords": sum(len(v) for v in self.lexicon.values())}

def run():
    detector = EmotionDetector()
    texts = [
        "I am so happy and excited about this wonderful news!",
        "I am angry and furious about this terrible situation.",
        "I feel scared and anxious about what might happen next.",
    ]
    for t in texts:
        r = detector.detect(t)
        print(f"Dominant: {r.dominant.name}, Intensity: {r.intensity:.2f}")
    print(detector.stats())

if __name__ == "__main__":
    run()

#!/usr/bin/env python3
"""
MAGNATRIX-OS — Voice Interaction Engine
ai/llm_voice_interaction_native.py

Features:
- Voice command parsing (wake word detection, intent extraction)
- Turn-based dialogue management
- Speech synthesis parameter control (speed, pitch, volume)
- Audio activity detection simulation (VAD)
- Conversation state tracking for voice

Style: Native Python, stdlib only, dataclasses, type hints, enums.
"""

from __future__ import annotations

import enum
import re
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("voice_interaction")


class VoiceState(enum.Enum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    WAITING = "waiting"


@dataclass
class VoiceCommand:
    text: str
    confidence: float
    timestamp: float
    intent: str = ""
    entities: Dict[str, str] = field(default_factory=dict)


class VoiceInteractionEngine:
    """Voice interaction with wake word, intent parsing, and dialogue state."""

    WAKE_WORDS = ["hey magnatrix", "hello magnatrix", "ok magnatrix"]
    INTENTS = {
        "search": ["search", "find", "look up", "get"],
        "control": ["turn on", "turn off", "start", "stop"],
        "question": ["what", "how", "why", "when", "where"],
        "schedule": ["schedule", "remind", "set alarm"],
    }

    def __init__(self):
        self.state = VoiceState.IDLE
        self._history: deque = deque(maxlen=50)
        self._turn_count = 0

    def detect_wake_word(self, transcript: str) -> bool:
        t = transcript.lower()
        return any(w in t for w in self.WAKE_WORDS)

    def parse_intent(self, text: str) -> VoiceCommand:
        text_lower = text.lower()
        intent = "general"
        entities = {}
        for intent_name, keywords in self.INTENTS.items():
            if any(kw in text_lower for kw in keywords):
                intent = intent_name
                break
        # Extract quoted entities
        quotes = re.findall(r'["\']([^"\']+)["\']', text)
        if quotes:
            entities["query"] = quotes[0]
        return VoiceCommand(text, 0.9, time.time(), intent, entities)

    def synthesize_params(self, text: str, speed: float = 1.0, pitch: float = 1.0, volume: float = 1.0) -> Dict[str, Any]:
        word_count = len(text.split())
        estimated_duration = word_count * 0.3 / speed
        return {
            "text": text,
            "speed": speed,
            "pitch": pitch,
            "volume": volume,
            "estimated_duration": estimated_duration,
            "word_count": word_count,
        }

    def simulate_vad(self, audio_level: float, threshold: float = 0.05) -> bool:
        return audio_level > threshold

    def process_turn(self, user_input: str) -> Dict[str, Any]:
        self._turn_count += 1
        if not self.detect_wake_word(user_input):
            return {"response": "Please say the wake word first.", "state": self.state.value}
        self.state = VoiceState.PROCESSING
        cmd = self.parse_intent(user_input)
        self.state = VoiceState.SPEAKING
        response = f"I understood: {cmd.intent}. Processing your request."
        self._history.append({"turn": self._turn_count, "user": user_input, "intent": cmd.intent, "response": response})
        self.state = VoiceState.WAITING
        return {
            "turn": self._turn_count,
            "intent": cmd.intent,
            "entities": cmd.entities,
            "response": response,
            "state": self.state.value,
        }

    def get_stats(self) -> Dict[str, Any]:
        return {"turns": self._turn_count, "state": self.state.value, "history": len(self._history)}


# ────────────────────────────────
# Demo / Self-Test
# ────────────────────────────────

def run() -> None:
    print("=" * 60)
    print("MAGNATRIX-OS — Voice Interaction Engine")
    print("ai/llm_voice_interaction_native.py")
    print("=" * 60)

    engine = VoiceInteractionEngine()

    # 1. Wake word detection
    print("\n[1] Wake Word Detection")
    for phrase in ["Hey Magnatrix, search for Python", "Hello world", "OK Magnatrix, what is AI"]:
        detected = engine.detect_wake_word(phrase)
        print(f"  '{phrase}': {'DETECTED' if detected else 'NO'}")

    # 2. Intent parsing
    print("\n[2] Intent Parsing")
    for phrase in ["search for 'machine learning'", "how does Python work", "turn on the lights"]:
        cmd = engine.parse_intent(phrase)
        print(f"  '{phrase}': intent={cmd.intent}, entities={cmd.entities}")

    # 3. Synthesis params
    print("\n[3] Speech Synthesis Params")
    params = engine.synthesize_params("Hello, this is Magnatrix speaking.", speed=1.2, pitch=1.1)
    print(f"  {params}")

    # 4. Turn processing
    print("\n[4] Turn Processing")
    for phrase in ["Hey Magnatrix, search for AI news", "OK Magnatrix, what is the weather"]:
        result = engine.process_turn(phrase)
        print(f"  Turn {result['turn']}: intent={result['intent']}, response={result['response']}")

    # 5. Stats
    print(f"\n[5] Stats: {engine.get_stats()}")

    print("\n" + "=" * 60)
    print("All demos completed successfully.")
    print("=" * 60)


if __name__ == "__main__":
    run()

#!/usr/bin/env python3
"""voice_pipeline_native.py — MAGNATRIX-OS Voice Layer
Voice Processing Pipeline: VAD → STT → TTS.

Features:
  - Voice Activity Detection (VAD): energy-based voice detection, noise floor
  - Speech-to-Text (STT): phoneme matching, word spotting, command recognition
  - Text-to-Speech (TTS): phoneme synthesis, prosody generation, wave output
  - Audio Streaming: chunk-based processing, real-time pipeline
  - Command Registry: voice commands mapped to actions

Pure Python, stdlib only. Mock implementations for STT/TTS (no ML deps).
Usage:
    pipe = NativeVoicePipeline()
    pipe.register_command("boot magnatrix", lambda: engine.boot())
    pipe.register_command("status", lambda: show_status())
    pipe.process_stream(audio_chunks)
"""
from __future__ import annotations

import struct
import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Tuple


# ══════════════════════════════════════════════════════════════════════════════
# Data Model
# ══════════════════════════════════════════════════════════════════════════════

class VADState(Enum):
    SILENCE = auto()
    VOICE = auto()
    TRANSITION = auto()


@dataclass
class AudioChunk:
    data: bytes
    timestamp: float
    sample_rate: int = 16000
    channels: int = 1


@dataclass
class VoiceSegment:
    chunks: List[AudioChunk]
    start_time: float
    end_time: float
    duration: float
    energy: float


@dataclass
class STTResult:
    text: str
    confidence: float
    words: List[str]
    is_command: bool
    matched_command: str = ""


@dataclass
class TTSResult:
    audio: bytes
    text: str
    duration_sec: float
    sample_rate: int = 16000


# ══════════════════════════════════════════════════════════════════════════════
# VAD (Voice Activity Detection)
# ══════════════════════════════════════════════════════════════════════════════

class VADEngine:
    """Energy-based voice activity detection."""

    def __init__(self, energy_threshold: float = 0.01, silence_duration: float = 0.5) -> None:
        self.energy_threshold = energy_threshold
        self.silence_duration = silence_duration
        self._state = VADState.SILENCE
        self._current_segment: List[AudioChunk] = []
        self._segments: List[VoiceSegment] = []
        self._last_voice_time = 0.0

    @staticmethod
    def _calculate_energy(chunk: AudioChunk) -> float:
        """Calculate RMS energy of audio chunk."""
        if not chunk.data:
            return 0.0
        # Assume 16-bit mono PCM
        fmt = f"{len(chunk.data) // 2}h"
        try:
            samples = struct.unpack(fmt, chunk.data)
        except struct.error:
            return 0.0
        if not samples:
            return 0.0
        rms = sum(s * s for s in samples) / len(samples)
        return (rms / 32767.0) ** 0.5  # Normalize to 0-1

    def process(self, chunk: AudioChunk) -> Optional[VoiceSegment]:
        energy = self._calculate_energy(chunk)
        now = time.time()

        if energy > self.energy_threshold:
            self._state = VADState.VOICE
            self._current_segment.append(chunk)
            self._last_voice_time = now
        else:
            if self._state == VADState.VOICE:
                if now - self._last_voice_time > self.silence_duration:
                    self._state = VADState.SILENCE
                    segment = self._finalize_segment()
                    self._current_segment = []
                    return segment
                else:
                    self._current_segment.append(chunk)
            else:
                self._current_segment = []
        return None

    def _finalize_segment(self) -> VoiceSegment:
        chunks = self._current_segment
        energies = [self._calculate_energy(c) for c in chunks]
        avg_energy = sum(energies) / len(energies) if energies else 0.0
        start = chunks[0].timestamp if chunks else 0.0
        end = chunks[-1].timestamp if chunks else 0.0
        return VoiceSegment(
            chunks=chunks, start_time=start, end_time=end,
            duration=end - start, energy=avg_energy,
        )

    def get_segments(self) -> List[VoiceSegment]:
        return self._segments

    def flush(self) -> Optional[VoiceSegment]:
        if self._current_segment:
            segment = self._finalize_segment()
            self._current_segment = []
            return segment
        return None


# ══════════════════════════════════════════════════════════════════════════════
# STT (Speech-to-Text) — Mock Implementation
# ══════════════════════════════════════════════════════════════════════════════

class STTEngine:
    """Speech-to-text with phoneme matching and command recognition."""

    def __init__(self) -> None:
        self._commands: Dict[str, str] = {}
        self._word_bank = {
            "boot": ["boot", "start", "launch"],
            "magnatrix": ["magnatrix", "matrix", "magnetic"],
            "status": ["status", "state", "condition"],
            "shutdown": ["shutdown", "stop", "halt"],
            "trade": ["trade", "trading", "buy", "sell"],
            "scan": ["scan", "search", "find"],
            "risk": ["risk", "danger", "limit"],
            "help": ["help", "assist", "support"],
        }

    def register_command(self, phrase: str, action_id: str) -> None:
        self._commands[phrase.lower()] = action_id

    def transcribe(self, segment: VoiceSegment) -> STTResult:
        """Mock transcription using phoneme matching heuristic."""
        # In real implementation: use neural ASR model
        # Here: simulated based on energy and duration patterns
        duration = segment.duration
        energy = segment.energy

        # Simulate word recognition based on segment characteristics
        words = []
        if duration > 0.5:
            words.append("boot")
        if duration > 1.0:
            words.append("magnatrix")
        if energy > 0.05:
            words.append("status")

        text = " ".join(words) if words else "(unrecognized)"
        confidence = min(0.95, energy * 10 + duration * 0.1)

        # Check if it's a registered command
        is_command = False
        matched_cmd = ""
        for cmd, action in self._commands.items():
            if all(w in text for w in cmd.split()):
                is_command = True
                matched_cmd = cmd
                break

        return STTResult(
            text=text, confidence=confidence, words=words,
            is_command=is_command, matched_command=matched_cmd,
        )

    def batch_transcribe(self, segments: List[VoiceSegment]) -> List[STTResult]:
        return [self.transcribe(s) for s in segments]


# ══════════════════════════════════════════════════════════════════════════════
# TTS (Text-to-Speech) — Mock Implementation
# ══════════════════════════════════════════════════════════════════════════════

class TTSEngine:
    """Text-to-speech with phoneme synthesis."""

    def __init__(self, sample_rate: int = 16000) -> None:
        self.sample_rate = sample_rate
        self._phoneme_durations = {
            'a': 0.08, 'e': 0.07, 'i': 0.07, 'o': 0.08, 'u': 0.07,
            'b': 0.08, 'c': 0.08, 'd': 0.07, 'f': 0.09, 'g': 0.08,
            'h': 0.06, 'j': 0.08, 'k': 0.08, 'l': 0.07, 'm': 0.08,
            'n': 0.07, 'p': 0.08, 'q': 0.09, 'r': 0.07, 's': 0.08,
            't': 0.07, 'v': 0.08, 'w': 0.08, 'x': 0.09, 'y': 0.07,
            'z': 0.08, ' ': 0.05, '.': 0.15, ',': 0.10, '!': 0.15,
        }

    def synthesize(self, text: str) -> TTSResult:
        """Synthesize speech from text (mock: generate sine wave)."""
        text = text.lower()
        total_duration = 0.0
        for char in text:
            total_duration += self._phoneme_durations.get(char, 0.07)

        # Generate simple sine wave audio (mock)
        import math
        samples = int(total_duration * self.sample_rate)
        audio = bytearray()
        for i in range(samples):
            # 440Hz tone with slight variation
            t = i / self.sample_rate
            val = int(32767 * 0.3 * math.sin(2 * math.pi * 440 * t) * (1 - t / total_duration))
            audio.extend(struct.pack('h', val))

        return TTSResult(
            audio=bytes(audio), text=text, duration_sec=total_duration,
            sample_rate=self.sample_rate,
        )

    def batch_synthesize(self, texts: List[str]) -> List[TTSResult]:
        return [self.synthesize(t) for t in texts]


# ══════════════════════════════════════════════════════════════════════════════
# Unified Voice Pipeline
# ══════════════════════════════════════════════════════════════════════════════

class NativeVoicePipeline:
    """Unified voice processing: VAD → STT → Command/TTS."""

    def __init__(self, sample_rate: int = 16000) -> None:
        self.vad = VADEngine()
        self.stt = STTEngine()
        self.tts = TTSEngine(sample_rate)
        self._command_handlers: Dict[str, Callable[[], Any]] = {}
        self._history: List[Dict[str, Any]] = []
        self._running = False

    def register_command(self, phrase: str, handler: Callable[[], Any]) -> None:
        self.stt.register_command(phrase, phrase)
        self._command_handlers[phrase.lower()] = handler

    def process_chunk(self, chunk: AudioChunk) -> Optional[Dict[str, Any]]:
        segment = self.vad.process(chunk)
        if segment:
            return self._process_segment(segment)
        return None

    def _process_segment(self, segment: VoiceSegment) -> Dict[str, Any]:
        stt_result = self.stt.transcribe(segment)
        result = {
            "segment": segment,
            "stt": stt_result,
            "command_executed": False,
            "response": None,
        }

        if stt_result.is_command and stt_result.matched_command:
            handler = self._command_handlers.get(stt_result.matched_command.lower())
            if handler:
                try:
                    response = handler()
                    result["command_executed"] = True
                    result["response"] = str(response) if response else "OK"
                except Exception as e:
                    result["response"] = f"Error: {e}"

        self._history.append(result)
        return result

    def process_stream(self, chunks: List[AudioChunk]) -> List[Dict[str, Any]]:
        results = []
        for chunk in chunks:
            r = self.process_chunk(chunk)
            if r:
                results.append(r)
        return results

    def speak(self, text: str) -> TTSResult:
        return self.tts.synthesize(text)

    def flush(self) -> Optional[Dict[str, Any]]:
        segment = self.vad.flush()
        if segment:
            return self._process_segment(segment)
        return None

    def status(self) -> Dict[str, Any]:
        return {
            "segments": len(self.vad.get_segments()),
            "commands_registered": len(self._command_handlers),
            "history": len(self._history),
            "running": self._running,
        }


# ══════════════════════════════════════════════════════════════════════════════
# Self-test
# ══════════════════════════════════════════════════════════════════════════════

def _self_test() -> int:
    print("=" * 60)
    print("Native Voice Pipeline — Self Test")
    print("=" * 60)
    passed = 0
    total = 7

    # Generate synthetic audio chunks
    def make_chunk(duration: float, energy_level: float) -> AudioChunk:
        samples = int(duration * 16000)
        import math
        data = bytearray()
        for i in range(samples):
            val = int(32767 * energy_level * math.sin(2 * math.pi * 440 * i / 16000))
            data.extend(struct.pack('h', val))
        return AudioChunk(data=bytes(data), timestamp=time.time(), sample_rate=16000)

    # Test 1: VAD silence
    print("[Test 1] VAD silence detection")
    pipe = NativeVoicePipeline()
    silence = make_chunk(0.3, 0.001)  # Very low energy
    result = pipe.process_chunk(silence)
    ok = result is None  # Should not trigger segment
    print(f"  Silence not detected: {ok} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    # Test 2: VAD voice
    print("[Test 2] VAD voice detection")
    voice_chunks = [make_chunk(0.3, 0.1) for _ in range(4)]
    for c in voice_chunks[:-1]:
        pipe.process_chunk(c)
    # Wait for silence to trigger segment
    time.sleep(0.6)
    result = pipe.process_chunk(make_chunk(0.1, 0.001))
    ok2 = result is not None and "segment" in result
    print(f"  Voice segment detected: {ok2} — {'PASS' if ok2 else 'FAIL'}")
    passed += ok2

    # Test 3: STT transcribe
    print("[Test 3] STT transcription")
    if result and "segment" in result:
        stt = result["stt"]
        ok3 = stt.confidence > 0
    else:
        ok3 = False
    print(f"  STT confidence > 0: {ok3} — {'PASS' if ok3 else 'FAIL'}")
    passed += ok3

    # Test 4: Command registration
    print("[Test 4] Command registration")
    commands_executed = []
    pipe.register_command("boot magnatrix", lambda: commands_executed.append("boot"))
    pipe.register_command("status", lambda: commands_executed.append("status"))
    ok4 = len(pipe._command_handlers) == 2
    print(f"  2 commands registered: {ok4} — {'PASS' if ok4 else 'FAIL'}")
    passed += ok4

    # Test 5: TTS synthesis
    print("[Test 5] TTS synthesis")
    tts = pipe.tts.synthesize("Hello magnatrix")
    ok5 = len(tts.audio) > 0 and tts.duration_sec > 0
    print(f"  TTS audio {len(tts.audio)} bytes, duration={tts.duration_sec:.2f}s: {ok5} — {'PASS' if ok5 else 'FAIL'}")
    passed += ok5

    # Test 6: Speak
    print("[Test 6] Speak function")
    result = pipe.speak("System ready")
    ok6 = result.text == "System ready" and len(result.audio) > 0
    print(f"  Speak OK: {ok6} — {'PASS' if ok6 else 'FAIL'}")
    passed += ok6

    # Test 7: Status
    print("[Test 7] Status report")
    st = pipe.status()
    ok7 = "commands_registered" in st and st["commands_registered"] == 2
    print(f"  Status valid: {ok7} — {'PASS' if ok7 else 'FAIL'}")
    passed += ok7

    print(f"\nPASS: {passed}/{total}")
    print("=" * 60)
    return 0 if passed == total else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())

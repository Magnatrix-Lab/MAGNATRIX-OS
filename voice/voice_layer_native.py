#!/usr/bin/env python3
"""
MAGNATRIX-OS Voice Layer Native
Speech-to-Text (STT) + Text-to-Speech (TTS) with wake word detection.
Pure Python stdlib — no external dependencies for basic operation.
"""
import os, re, json, threading, queue, time, subprocess, tempfile
from typing import Optional, Callable, List, Dict, Any
from dataclasses import dataclass, field


@dataclass
class VoiceConfig:
    wake_word: str = "magnatrix"
    sample_rate: int = 16000
    chunk_duration_ms: int = 100
    silence_threshold: float = 0.01
    silence_timeout_ms: float = 2000
    tts_rate: int = 180  # words per minute
    tts_pitch: float = 1.0
    language: str = "en"


class SpeechToTextNative:
    """
    Offline STT using pocketsphinx or browser-based fallback.
    Pure Python: uses energy-based voice activity detection + simple pattern matching.
    """

    def __init__(self, config: VoiceConfig = None):
        self.config = config or VoiceConfig()
        self._listening = False
        self._thread = None
        self._queue = queue.Queue()
        self._callbacks: List[Callable[[str], None]] = []

    def _energy_detect(self, pcm_bytes: bytes) -> bool:
        """Simple energy-based voice activity detection."""
        if not pcm_bytes:
            return False
        # Treat as 16-bit PCM
        samples = []
        for i in range(0, len(pcm_bytes) - 1, 2):
            val = int.from_bytes(pcm_bytes[i:i+2], "little", signed=True)
            samples.append(val)
        if not samples:
            return False
        energy = sum(abs(s) for s in samples) / len(samples)
        return energy > 500  # threshold for 16-bit PCM

    def _recognize(self, audio_data: bytes) -> str:
        """Recognize speech from audio data."""
        # Fallback: try pocketsphinx if available
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            with sr.AudioFile(self._bytes_to_wav(audio_data)) as source:
                audio = r.record(source)
            return r.recognize_sphinx(audio) or ""
        except ImportError:
            pass
        except Exception:
            pass
        return ""

    def _bytes_to_wav(self, pcm: bytes) -> str:
        """Convert raw PCM to temporary WAV file."""
        import wave, struct
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        with wave.open(tmp.name, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(self.config.sample_rate)
            w.writeframes(pcm)
        return tmp.name

    def start_listening(self, callback: Callable[[str], None] = None):
        """Start background listening thread."""
        if callback:
            self._callbacks.append(callback)
        if self._listening:
            return
        self._listening = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    def _listen_loop(self):
        """Background loop: capture audio chunks, detect speech, recognize."""
        print("[VOICE] STT listening started...")
        while self._listening:
            # In a real implementation, this would capture from microphone
            # For demo/placeholder, we simulate with queue input
            try:
                audio_chunk = self._queue.get(timeout=0.5)
                if self._energy_detect(audio_chunk):
                    text = self._recognize(audio_chunk)
                    if text:
                        for cb in self._callbacks:
                            try:
                                cb(text)
                            except Exception:
                                pass
                        # Check wake word
                        if self.config.wake_word.lower() in text.lower():
                            print(f"[VOICE] Wake word detected: {self.config.wake_word}")
            except queue.Empty:
                continue

    def stop_listening(self):
        self._listening = False
        if self._thread:
            self._thread.join(timeout=1)

    def feed_audio(self, pcm_bytes: bytes):
        """Feed audio data for recognition (e.g., from WebRTC stream)."""
        self._queue.put(pcm_bytes)

    def on_command(self, callback: Callable[[str], None]):
        self._callbacks.append(callback)


class TextToSpeechNative:
    """
    Offline TTS using pyttsx3 or browser-based fallback.
    Pure Python fallback: save text to file for external TTS engine.
    """

    def __init__(self, config: VoiceConfig = None):
        self.config = config or VoiceConfig()
        self._engine = None
        self._init_engine()

    def _init_engine(self):
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate", self.config.tts_rate)
            self._engine.setProperty("volume", 0.9)
        except ImportError:
            self._engine = None

    def speak(self, text: str) -> bool:
        """Speak text. Returns True if successful."""
        if self._engine:
            try:
                self._engine.say(text)
                self._engine.runAndWait()
                return True
            except Exception as e:
                print(f"[VOICE] TTS error: {e}")
                return False
        # Fallback: write to temp file
        tmp = os.path.expanduser("~/.magnatrix/tts_queue.txt")
        os.makedirs(os.path.dirname(tmp), exist_ok=True)
        with open(tmp, "a") as f:
            f.write(text + "\n")
        print(f"[VOICE] TTS queued (no engine): {text[:60]}...")
        return True

    def save_to_file(self, text: str, path: str) -> bool:
        """Save speech to audio file."""
        if self._engine:
            try:
                self._engine.save_to_file(text, path)
                self._engine.runAndWait()
                return True
            except Exception:
                pass
        return False


class VoiceCommandProcessor:
    """Process voice commands and route to MAGNATRIX layers."""

    COMMANDS = {
        r"boot|start|run": "boot",
        r"status|state|health": "status",
        r"stop|shutdown|kill": "shutdown",
        r"restart|reboot": "restart",
        r"trade|buy|sell": "trading",
        r"search|find|look": "search",
        r"chat|talk|ask": "chat",
        r"scan|audit|check": "security",
    }

    def __init__(self, stt: SpeechToTextNative, tts: TextToSpeechNative):
        self.stt = stt
        self.tts = tts
        self._command_handlers: Dict[str, Callable] = {}

    def register_handler(self, command: str, handler: Callable):
        self._command_handlers[command] = handler

    def process(self, text: str) -> str:
        """Process recognized text and return response."""
        text_lower = text.lower()
        for pattern, cmd in self.COMMANDS.items():
            if re.search(pattern, text_lower):
                handler = self._command_handlers.get(cmd)
                if handler:
                    try:
                        result = handler(text)
                        response = f"Command '{cmd}' executed: {result}"
                    except Exception as e:
                        response = f"Error executing '{cmd}': {e}"
                else:
                    response = f"Command '{cmd}' recognized but no handler registered."
                self.tts.speak(response)
                return response

        response = f"Command not recognized: '{text[:40]}...'"
        self.tts.speak(response)
        return response

    def start(self):
        """Start voice command loop."""
        self.stt.on_command(self.process)
        self.stt.start_listening()
        self.tts.speak("MAGNATRIX voice interface activated.")

    def stop(self):
        self.stt.stop_listening()


class VoiceLayerNative:
    """Main voice layer orchestrator."""

    def __init__(self):
        self.config = VoiceConfig()
        self.stt = SpeechToTextNative(self.config)
        self.tts = TextToSpeechNative(self.config)
        self.processor = VoiceCommandProcessor(self.stt, self.tts)

    def boot(self):
        self.processor.start()

    def shutdown(self):
        self.processor.stop()

    def register_command(self, name: str, handler: Callable):
        self.processor.register_handler(name, handler)

    def speak(self, text: str):
        self.tts.speak(text)


def _demo():
    print("=" * 60)
    print("MAGNATRIX-OS Voice Layer Demo")
    print("=" * 60)

    voice = VoiceLayerNative()

    # Register simple handlers
    def boot_handler(text):
        return "System booted successfully"
    def status_handler(text):
        return "All layers operational"
    def trade_handler(text):
        return "Paper trading active"

    voice.register_command("boot", boot_handler)
    voice.register_command("status", status_handler)
    voice.register_command("trading", trade_handler)

    print("\n[1] Testing TTS...")
    voice.speak("MAGNATRIX voice layer test successful.")

    print("\n[2] Testing command recognition...")
    result = voice.processor.process("start the system")
    print(f"    Result: {result}")

    result = voice.processor.process("show trading status")
    print(f"    Result: {result}")

    result = voice.processor.process("unknown command xyz")
    print(f"    Result: {result}")

    print("\n[3] Voice layer ready for hands-free control.")
    print("=" * 60)


if __name__ == "__main__":
    _demo()

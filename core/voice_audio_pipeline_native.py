"""Voice & Audio Pipeline Native — MAGNATRIX-OS

Pure-stdlib voice orchestration engine providing:
  • Speech-to-Text (STT) with auto-detected backends (whisper.cpp, VOSK, Web Speech API)
  • Text-to-Speech (TTS) with auto-detected backends (piper, espeak, spd-say, say)
  • Voice Agent Interface (wake word, conversation loop, barge-in)
  • Cross-platform Audio I/O (capture, playback, format conversion)
  • Integration hooks for local_llm_manager_native.py and event_bus_native.py

All orchestration is pure stdlib. External tools are invoked via subprocess
with graceful degradation and mock mode for headless testing.
"""

from __future__ import annotations

import io
import json
import math
import os
import pathlib
import platform
import re
import shutil
import struct
import subprocess
import sys
import threading
import time
import wave
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

# ──────────────────────────────────────────────────────────────
# 1.  DATA STRUCTURES & ENUMS
# ──────────────────────────────────────────────────────────────


class AudioState(Enum):
    IDLE = auto()
    LISTENING = auto()
    PROCESSING = auto()
    SPEAKING = auto()
    INTERRUPTED = auto()


class TTSEngine(Enum):
    PIPER = "piper"
    ESPEAK = "espeak"
    ESPEAK_NG = "espeak-ng"
    FESTIVAL = "festival"
    SAY = "say"
    SPD_SAY = "spd-say"
    MOCK = "mock"


class STTEngine(Enum):
    WHISPER_CPP = "whisper.cpp"
    WHISPER = "whisper"
    FASTER_WHISPER = "faster-whisper"
    VOSK = "vosk"
    WEB_SPEECH = "web_speech"
    MOCK = "mock"


class AudioBackend(Enum):
    PYAUDIO = "pyaudio"
    ARECORD = "arecord"
    SOX = "sox"
    AVCONV = "avconv"
    FFMPEG = "ffmpeg"
    APLAY = "aplay"
    PAPLAY = "paplay"
    AFPLAY = "afplay"
    MPV = "mpv"
    MOCK = "mock"


@dataclass
class AudioFormat:
    sample_rate: int = 16000
    channels: int = 1
    sample_width: int = 2  # bytes per sample (16-bit)
    dtype: str = "int16"

    def block_align(self) -> int:
        return self.channels * self.sample_width

    def byte_rate(self) -> int:
        return self.sample_rate * self.block_align()


@dataclass
class VoiceConfig:
    wake_words: List[str] = field(default_factory=lambda: ["hey magnatrix", "ok matrix"])
    silence_timeout_ms: int = 3000
    vad_threshold: float = 0.02
    voice_gender: str = "female"
    voice_speed: float = 1.0
    voice_pitch: float = 1.0
    language: str = "en"
    max_recording_sec: int = 30
    tts_preference: List[str] = field(
        default_factory=lambda: ["piper", "espeak-ng", "espeak", "spd-say", "say"]
    )
    stt_preference: List[str] = field(
        default_factory=lambda: ["whisper.cpp", "faster-whisper", "whisper", "vosk"]
    )
    audio_input_preference: List[str] = field(
        default_factory=lambda: ["pyaudio", "arecord", "ffmpeg", "sox"]
    )
    audio_output_preference: List[str] = field(
        default_factory=lambda: ["aplay", "paplay", "afplay", "mpv", "ffplay"]
    )
    mock_mode: bool = False
    enable_websocket: bool = False
    websocket_port: int = 8765


@dataclass
class STTResult:
    text: str
    confidence: float = 0.0
    language: str = "en"
    is_final: bool = True
    engine: str = "mock"
    duration_ms: int = 0

    def as_dict(self) -> dict:
        return {
            "text": self.text,
            "confidence": self.confidence,
            "language": self.language,
            "is_final": self.is_final,
            "engine": self.engine,
            "duration_ms": self.duration_ms,
        }


@dataclass
class TTSResult:
    audio_path: Optional[str]
    duration_ms: int = 0
    engine: str = "mock"
    error: Optional[str] = None

    def as_dict(self) -> dict:
        return {
            "audio_path": self.audio_path,
            "duration_ms": self.duration_ms,
            "engine": self.engine,
            "error": self.error,
        }


@dataclass
class VoiceEvent:
    event_type: str  # wake_word | speech_start | speech_end | stt_result | tts_start | tts_end | interrupt | error
    payload: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def as_dict(self) -> dict:
        return {
            "event_type": self.event_type,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }


# ──────────────────────────────────────────────────────────────
# 2.  BACKEND DETECTION
# ──────────────────────────────────────────────────────────────


class BackendDetector:
    """Detect available STT, TTS, and audio I/O backends on the host system."""

    _cache: Dict[str, Any] = {}

    @classmethod
    def _which(cls, cmd: str) -> Optional[str]:
        return shutil.which(cmd)

    @classmethod
    def detect_tts(cls) -> List[TTSEngine]:
        if "tts" in cls._cache:
            return cls._cache["tts"]
        found = []
        for engine in TTSEngine:
            if engine == TTSEngine.MOCK:
                continue
            if cls._which(engine.value):
                found.append(engine)
        if not found:
            found.append(TTSEngine.MOCK)
        cls._cache["tts"] = found
        return found

    @classmethod
    def detect_stt(cls) -> List[STTEngine]:
        if "stt" in cls._cache:
            return cls._cache["stt"]
        found = []
        # Check for whisper.cpp binary
        if cls._which("whisper-cli") or cls._which("main") or cls._which("whisper.cpp"):
            found.append(STTEngine.WHISPER_CPP)
        # Check Python packages via import
        for pkg, engine in [("whisper", STTEngine.WHISPER), ("faster_whisper", STTEngine.FASTER_WHISPER), ("vosk", STTEngine.VOSK)]:
            try:
                __import__(pkg)
                found.append(engine)
            except ImportError:
                pass
        if not found:
            found.append(STTEngine.MOCK)
        cls._cache["stt"] = found
        return found

    @classmethod
    def detect_audio_input(cls) -> List[AudioBackend]:
        if "audio_in" in cls._cache:
            return cls._cache["audio_in"]
        found = []
        prefs = ["pyaudio", "arecord", "ffmpeg", "sox", "avconv"]
        for name in prefs:
            if cls._which(name):
                found.append(AudioBackend(name))
        if not found:
            found.append(AudioBackend.MOCK)
        cls._cache["audio_in"] = found
        return found

    @classmethod
    def detect_audio_output(cls) -> List[AudioBackend]:
        if "audio_out" in cls._cache:
            return cls._cache["audio_out"]
        found = []
        prefs = ["aplay", "paplay", "afplay", "mpv", "ffplay", "ffmpeg"]
        for name in prefs:
            if cls._which(name):
                found.append(AudioBackend(name))
        if not found:
            found.append(AudioBackend.MOCK)
        cls._cache["audio_out"] = found
        return found

    @classmethod
    def has_ffmpeg(cls) -> bool:
        return cls._which("ffmpeg") is not None

    @classmethod
    def report(cls) -> dict:
        return {
            "tts": [e.value for e in cls.detect_tts()],
            "stt": [e.value for e in cls.detect_stt()],
            "audio_input": [e.value for e in cls.detect_audio_input()],
            "audio_output": [e.value for e in cls.detect_audio_output()],
            "ffmpeg": cls.has_ffmpeg(),
            "platform": platform.system(),
        }


# ──────────────────────────────────────────────────────────────
# 3.  AUDIO I/O MANAGEMENT
# ──────────────────────────────────────────────────────────────


class AudioIOEngine:
    """Cross-platform audio capture and playback via subprocess."""

    def __init__(self, config: VoiceConfig, fmt: AudioFormat = AudioFormat()):
        self.config = config
        self.fmt = fmt
        self.input_backend = BackendDetector.detect_audio_input()[0]
        self.output_backend = BackendDetector.detect_audio_output()[0]
        self._recording = False
        self._record_buffer: List[bytes] = []
        self._interrupt_event = threading.Event()

    def is_mock(self) -> bool:
        return self.input_backend == AudioBackend.MOCK or self.output_backend == AudioBackend.MOCK

    def capture_to_file(self, filepath: str, duration_sec: int = 5) -> bool:
        """Record audio from microphone to a WAV file."""
        if self.config.mock_mode or self.is_mock():
            self._write_mock_wav(filepath, duration_sec)
            return True

        cmd = self._build_capture_cmd(filepath, duration_sec)
        try:
            subprocess.run(cmd, shell=False, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=duration_sec + 5)
            return True
        except Exception as exc:
            print(f"[AudioIO] capture error: {exc}")
            return False

    def capture_chunked(self, callback: Callable[[bytes], None], chunk_size: int = 1024) -> None:
        """Stream audio chunks in real-time via callback."""
        if self.config.mock_mode or self.is_mock():
            self._mock_stream(callback, chunk_size)
            return

        cmd = self._build_capture_cmd("-", duration_sec=self.config.max_recording_sec)
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            while self._recording and proc.poll() is None:
                chunk = proc.stdout.read(chunk_size) if proc.stdout else b""
                if not chunk:
                    break
                callback(chunk)
            proc.terminate()
        except Exception as exc:
            print(f"[AudioIO] chunked capture error: {exc}")

    def play_file(self, filepath: str) -> bool:
        """Play a WAV/MP3 file through the default audio output."""
        if self.config.mock_mode or self.is_mock():
            print(f"[AudioIO][MOCK] play_file: {filepath}")
            return True

        cmd = self._build_playback_cmd(filepath)
        try:
            subprocess.run(cmd, shell=False, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
            return True
        except Exception as exc:
            print(f"[AudioIO] playback error: {exc}")
            return False

    def play_bytes(self, audio_data: bytes, fmt: Optional[AudioFormat] = None) -> bool:
        """Play raw audio bytes."""
        if self.config.mock_mode or self.is_mock():
            print(f"[AudioIO][MOCK] play_bytes: {len(audio_data)} bytes")
            return True

        tmp_path = f"/tmp/magnatrix_audio_{int(time.time()*1000)}.wav"
        self._write_wav(tmp_path, audio_data, fmt or self.fmt)
        ok = self.play_file(tmp_path)
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        return ok

    def stop(self) -> None:
        self._recording = False
        self._interrupt_event.set()

    def _build_capture_cmd(self, filepath: str, duration_sec: int) -> List[str]:
        sr = self.fmt.sample_rate
        ch = self.fmt.channels
        backend = self.input_backend

        if backend == AudioBackend.PYAUDIO:
            # Python script via pyaudio invoked as module
            return [sys.executable, "-c", f"import pyaudio,wave; p=pa.PyAudio(); s=wave.open('{filepath}','wb'); s.setnchannels({ch}); s.setsampwidth(2); s.setframerate({sr}); stream=p.open(format=pa.paInt16,channels={ch},rate={sr},input=True); [s.writeframes(stream.read(1024)) for _ in range(int({sr}/{1024}*{duration_sec}))]; stream.stop_stream(); stream.close(); p.terminate()"]
        if backend == AudioBackend.ARECORD:
            return ["arecord", "-D", "plughw:0,0", "-f", "S16_LE", "-r", str(sr), "-c", str(ch), "-d", str(duration_sec), filepath] if filepath != "-" else ["arecord", "-D", "plughw:0,0", "-f", "S16_LE", "-r", str(sr), "-c", str(ch)]
        if backend == AudioBackend.FFMPEG:
            return ["ffmpeg", "-f", "alsa", "-i", "default", "-ar", str(sr), "-ac", str(ch), "-t", str(duration_sec), "-y", filepath] if filepath != "-" else ["ffmpeg", "-f", "alsa", "-i", "default", "-ar", str(sr), "-ac", str(ch), "-f", "wav", "-"]
        if backend == AudioBackend.SOX:
            return ["sox", "-d", "-r", str(sr), "-c", str(ch), "-b", "16", filepath, "trim", "0", str(duration_sec)]
        return ["true"]

    def _build_playback_cmd(self, filepath: str) -> List[str]:
        backend = self.output_backend
        if backend == AudioBackend.APLAY:
            return ["aplay", filepath]
        if backend == AudioBackend.PAPLAY:
            return ["paplay", filepath]
        if backend == AudioBackend.AFPLAY:
            return ["afplay", filepath]
        if backend == AudioBackend.MPV:
            return ["mpv", "--no-video", filepath]
        if backend == AudioBackend.MOCK:
            return ["echo", f"mock_play: {filepath}"]
        return ["ffplay", "-nodisp", "-autoexit", filepath]

    def _write_wav(self, path: str, data: bytes, fmt: AudioFormat) -> None:
        with wave.open(path, "wb") as w:
            w.setnchannels(fmt.channels)
            w.setsampwidth(fmt.sample_width)
            w.setframerate(fmt.sample_rate)
            w.writeframes(data)

    def _write_mock_wav(self, path: str, duration_sec: int) -> None:
        """Generate a silent/mock WAV file for testing."""
        num_samples = duration_sec * self.fmt.sample_rate
        silent = b"\x00" * (num_samples * self.fmt.block_align())
        self._write_wav(path, silent, self.fmt)

    def _mock_stream(self, callback: Callable[[bytes], None], chunk_size: int) -> None:
        """Generate fake audio chunks in mock mode."""
        silence = b"\x00" * chunk_size
        for _ in range(50):
            if not self._recording:
                break
            callback(silence)
            time.sleep(0.05)

    @staticmethod
    def normalize_audio(data: bytes, fmt: AudioFormat = AudioFormat()) -> bytes:
        """Simple amplitude normalization (peak to 0dB)."""
        if fmt.sample_width == 2:
            samples = struct.unpack(f"<{len(data)//2}h", data)
            peak = max(abs(s) for s in samples) if samples else 1
            if peak == 0:
                return data
            scale = 32767 / peak
            norm = [int(s * scale) for s in samples]
            return struct.pack(f"<{len(norm)}h", *norm)
        return data

    @staticmethod
    def noise_gate(data: bytes, threshold: float = 0.02, fmt: AudioFormat = AudioFormat()) -> bytes:
        """Zero out samples below amplitude threshold."""
        if fmt.sample_width != 2:
            return data
        samples = list(struct.unpack(f"<{len(data)//2}h", data))
        max_amp = max(abs(s) for s in samples) if samples else 1
        if max_amp == 0:
            return data
        gated = [s if abs(s) / max_amp > threshold else 0 for s in samples]
        return struct.pack(f"<{len(gated)}h", *gated)


# ──────────────────────────────────────────────────────────────
# 4.  SPEECH-TO-TEXT (STT) ENGINE
# ──────────────────────────────────────────────────────────────


class STTEngineNative:
    """Streaming speech-to-text with auto-detected backends and fallbacks."""

    def __init__(self, config: VoiceConfig, fmt: AudioFormat = AudioFormat()):
        self.config = config
        self.fmt = fmt
        self.available = BackendDetector.detect_stt()
        self._active = self._pick_engine()
        self._lock = threading.Lock()

    def _pick_engine(self) -> STTEngine:
        for name in self.config.stt_preference:
            for engine in self.available:
                if engine.value == name or engine.value.startswith(name):
                    return engine
        return STTEngine.MOCK

    def transcribe_file(self, audio_path: str) -> STTResult:
        """Transcribe a WAV file to text."""
        if self.config.mock_mode or self._active == STTEngine.MOCK:
            return self._mock_transcribe(audio_path)

        start = time.time()
        text = ""
        confidence = 0.0

        try:
            if self._active == STTEngine.WHISPER_CPP:
                text = self._transcribe_whisper_cpp(audio_path)
            elif self._active == STTEngine.WHISPER:
                text = self._transcribe_whisper(audio_path)
            elif self._active == STTEngine.FASTER_WHISPER:
                text = self._transcribe_faster_whisper(audio_path)
            elif self._active == STTEngine.VOSK:
                text = self._transcribe_vosk(audio_path)
            confidence = 0.85
        except Exception as exc:
            print(f"[STT] {self._active.value} error: {exc}")
            return STTResult(text="", confidence=0.0, engine=self._active.value, error=str(exc))

        elapsed = int((time.time() - start) * 1000)
        return STTResult(text=text, confidence=confidence, engine=self._active.value, duration_ms=elapsed)

    def transcribe_stream(self, chunks: Iterator[bytes]) -> Iterator[STTResult]:
        """Real-time streaming transcription from audio chunks."""
        if self.config.mock_mode or self._active == STTEngine.MOCK:
            yield from self._mock_stream_transcribe(chunks)
            return

        # Accumulate into a temporary WAV, then transcribe periodically
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as w:
            w.setnchannels(self.fmt.channels)
            w.setsampwidth(self.fmt.sample_width)
            w.setframerate(self.fmt.sample_rate)
            for chunk in chunks:
                w.writeframes(chunk)
                # Every ~2 seconds of audio, emit a partial
                if w.getnframes() > self.fmt.sample_rate * 2:
                    tmp = f"/tmp/magnatrix_stt_{int(time.time()*1000)}.wav"
                    with open(tmp, "wb") as f:
                        f.write(buffer.getvalue())
                    result = self.transcribe_file(tmp)
                    result.is_final = False
                    yield result
                    try:
                        os.remove(tmp)
                    except OSError:
                        pass
                    # Reset buffer
                    buffer = io.BytesIO()
                    w = wave.open(buffer, "wb")
                    w.setnchannels(self.fmt.channels)
                    w.setsampwidth(self.fmt.sample_width)
                    w.setframerate(self.fmt.sample_rate)

        # Final
        if buffer.tell() > 44:
            tmp = f"/tmp/magnatrix_stt_{int(time.time()*1000)}.wav"
            with open(tmp, "wb") as f:
                f.write(buffer.getvalue())
            result = self.transcribe_file(tmp)
            result.is_final = True
            yield result
            try:
                os.remove(tmp)
            except OSError:
                pass

    def _transcribe_whisper_cpp(self, path: str) -> str:
        bin_path = shutil.which("whisper-cli") or shutil.which("main") or "whisper.cpp"
        cmd = [bin_path, "-f", path, "-l", self.config.language, "--no-timestamps", "-otxt"]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return result.stdout.strip()

    def _transcribe_whisper(self, path: str) -> str:
        import whisper  # type: ignore
        model = whisper.load_model("base")
        result = model.transcribe(path, language=self.config.language)
        return result.get("text", "").strip()

    def _transcribe_faster_whisper(self, path: str) -> str:
        from faster_whisper import WhisperModel  # type: ignore
        model = WhisperModel("base", device="cpu")
        segments, _ = model.transcribe(path, language=self.config.language)
        return " ".join(s.text for s in segments).strip()

    def _transcribe_vosk(self, path: str) -> str:
        import vosk  # type: ignore
        model = vosk.Model("model")
        rec = vosk.KaldiRecognizer(model, self.fmt.sample_rate)
        with wave.open(path, "rb") as wf:
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                rec.AcceptWaveform(data)
        result = json.loads(rec.FinalResult())
        return result.get("text", "").strip()

    def _mock_transcribe(self, audio_path: str) -> STTResult:
        # Simulate varying results based on filename for deterministic testing
        if "wake" in audio_path.lower():
            text = "hey magnatrix what is the weather"
        elif "silence" in audio_path.lower():
            text = ""
        else:
            text = "mock transcription from audio file"
        return STTResult(text=text, confidence=0.95, engine="mock", duration_ms=200)

    def _mock_stream_transcribe(self, chunks: Iterator[bytes]) -> Iterator[STTResult]:
        yield STTResult(text="", confidence=0.0, engine="mock", is_final=False)
        yield STTResult(text="mock streaming result", confidence=0.9, engine="mock", is_final=True)

    def vad_simple(self, chunk: bytes) -> bool:
        """Simple threshold-based voice activity detection on 16-bit PCM."""
        if len(chunk) < self.fmt.sample_width:
            return False
        if self.fmt.sample_width == 2:
            samples = struct.unpack(f"<{len(chunk)//2}h", chunk)
            peak = max(abs(s) for s in samples) if samples else 0
            return (peak / 32767.0) > self.config.vad_threshold
        return False


# ──────────────────────────────────────────────────────────────
# 5.  TEXT-TO-SPEECH (TTS) ENGINE
# ──────────────────────────────────────────────────────────────


class TTSEngineNative:
    """Text-to-speech with auto-detected backends and streaming output."""

    def __init__(self, config: VoiceConfig, fmt: AudioFormat = AudioFormat()):
        self.config = config
        self.fmt = fmt
        self.available = BackendDetector.detect_tts()
        self._active = self._pick_engine()
        self._speaking = False
        self._stop_event = threading.Event()

    def _pick_engine(self) -> TTSEngine:
        for name in self.config.tts_preference:
            for engine in self.available:
                if engine.value == name or engine.value.startswith(name):
                    return engine
        return TTSEngine.MOCK

    def speak(self, text: str, output_path: Optional[str] = None) -> TTSResult:
        """Synthesize text to audio. Return path to WAV file or None if playback only."""
        if self.config.mock_mode or self._active == TTSEngine.MOCK:
            return self._mock_speak(text, output_path)

        self._speaking = True
        self._stop_event.clear()
        start = time.time()
        result_path: Optional[str] = None

        try:
            if self._active == TTSEngine.PIPER:
                result_path = self._synth_piper(text, output_path)
            elif self._active == TTSEngine.ESPEAK:
                result_path = self._synth_espeak(text, output_path, ng=False)
            elif self._active == TTSEngine.ESPEAK_NG:
                result_path = self._synth_espeak(text, output_path, ng=True)
            elif self._active == TTSEngine.FESTIVAL:
                result_path = self._synth_festival(text, output_path)
            elif self._active == TTSEngine.SAY:
                result_path = self._synth_say(text, output_path)
            elif self._active == TTSEngine.SPD_SAY:
                result_path = self._synth_spd_say(text, output_path)
        except Exception as exc:
            print(f"[TTS] {self._active.value} error: {exc}")
            return TTSResult(audio_path=None, engine=self._active.value, error=str(exc))

        elapsed = int((time.time() - start) * 1000)
        self._speaking = False
        return TTSResult(audio_path=result_path, duration_ms=elapsed, engine=self._active.value)

    def speak_and_play(self, text: str, audio_io: AudioIOEngine) -> TTSResult:
        """Synthesize and immediately play through audio output."""
        result = self.speak(text)
        if result.audio_path and audio_io.play_file(result.audio_path):
            return result
        return TTSResult(audio_path=result.audio_path, engine=result.engine, error="playback failed")

    def stop(self) -> None:
        self._stop_event.set()
        self._speaking = False

    def is_speaking(self) -> bool:
        return self._speaking

    def _synth_piper(self, text: str, output_path: Optional[str]) -> str:
        out = output_path or f"/tmp/magnatrix_tts_{int(time.time()*1000)}.wav"
        model = os.environ.get("PIPER_MODEL", "en_US-lessac-medium.onnx")
        cmd = ["piper", "--model", model, "--output_file", out, "--data-dir", "/usr/share/piper"]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.stdin:
            proc.stdin.write(text.encode())
            proc.stdin.close()
        proc.wait(timeout=30)
        return out

    def _synth_espeak(self, text: str, output_path: Optional[str], ng: bool = False) -> str:
        out = output_path or f"/tmp/magnatrix_tts_{int(time.time()*1000)}.wav"
        cmd = "espeak-ng" if ng else "espeak"
        speed = int(175 * self.config.voice_speed)
        pitch = int(self.config.voice_pitch * 50)
        gender = "m" if self.config.voice_gender == "male" else "f"
        subprocess.run([cmd, "-s", str(speed), "-p", str(pitch), "-v", gender, "-w", out, text], check=True, timeout=30)
        return out

    def _synth_festival(self, text: str, output_path: Optional[str]) -> str:
        out = output_path or f"/tmp/magnatrix_tts_{int(time.time()*1000)}.wav"
        scm = f"(tts_text \"{text}\")"
        subprocess.run(["festival", "-b", "--eval", scm], capture_output=True, timeout=30)
        # Festival may need additional steps to save as WAV; fallback to text2wave
        subprocess.run(["text2wave", "-o", out], input=text.encode(), capture_output=True, timeout=30)
        return out

    def _synth_say(self, text: str, output_path: Optional[str]) -> str:
        out = output_path or f"/tmp/magnatrix_tts_{int(time.time()*1000)}.wav"
        voice = "Samantha" if self.config.voice_gender == "female" else "Alex"
        subprocess.run(["say", "-v", voice, "-o", out, text], check=True, timeout=30)
        return out

    def _synth_spd_say(self, text: str, output_path: Optional[str]) -> str:
        # spd-say can only play, not save directly; use -o if available or pipe
        out = output_path or f"/tmp/magnatrix_tts_{int(time.time()*1000)}.wav"
        subprocess.run(["spd-say", "-o", "alsa", "-w", text], check=True, timeout=30)
        # Mock fallback: generate silence
        self._write_mock_wav(out, len(text) * 0.1)
        return out

    def _mock_speak(self, text: str, output_path: Optional[str]) -> TTSResult:
        out = output_path or f"/tmp/magnatrix_tts_mock_{int(time.time()*1000)}.wav"
        duration = max(1, int(len(text) * 0.1))  # 100ms per char
        self._write_mock_wav(out, duration)
        return TTSResult(audio_path=out, duration_ms=duration * 1000, engine="mock")

    def _write_mock_wav(self, path: str, duration_sec: float) -> None:
        samples = int(duration_sec * self.fmt.sample_rate)
        silent = b"\x00" * (samples * self.fmt.block_align())
        with wave.open(path, "wb") as w:
            w.setnchannels(self.fmt.channels)
            w.setsampwidth(self.fmt.sample_width)
            w.setframerate(self.fmt.sample_rate)
            w.writeframes(silent)

    def convert_to_mp3(self, wav_path: str, mp3_path: str) -> bool:
        if not BackendDetector.has_ffmpeg():
            return False
        try:
            subprocess.run(["ffmpeg", "-y", "-i", wav_path, "-codec:a", "libmp3lame", "-qscale:a", "2", mp3_path], check=True, timeout=30)
            return True
        except Exception as exc:
            print(f"[TTS] MP3 conversion error: {exc}")
            return False


# ──────────────────────────────────────────────────────────────
# 6.  VOICE AGENT INTERFACE
# ──────────────────────────────────────────────────────────────


class VoiceAgentNative:
    """Conversation loop: wake word → listen → transcribe → process → speak."""

    def __init__(self, config: VoiceConfig, audio_io: AudioIOEngine, stt: STTEngineNative, tts: TTSEngineNative):
        self.config = config
        self.audio_io = audio_io
        self.stt = stt
        self.tts = tts
        self.state = AudioState.IDLE
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: Dict[str, Callable] = {}
        self._event_log: List[VoiceEvent] = []
        self._llm_hook: Optional[Callable[[str], str]] = None
        self._event_bus_hook: Optional[Callable[[VoiceEvent], None]] = None
        self._lock = threading.Lock()

    def on_event(self, event_type: str, callback: Callable[[VoiceEvent], None]) -> None:
        self._callbacks[event_type] = callback

    def set_llm_hook(self, hook: Callable[[str], str]) -> None:
        """Set callback to process transcribed text and return response text."""
        self._llm_hook = hook

    def set_event_bus_hook(self, hook: Callable[[VoiceEvent], None]) -> None:
        """Set callback to publish voice events to the system event bus."""
        self._event_bus_hook = hook

    def _emit(self, event: VoiceEvent) -> None:
        self._event_log.append(event)
        if self._event_bus_hook:
            try:
                self._event_bus_hook(event)
            except Exception as exc:
                print(f"[VoiceAgent] event bus hook error: {exc}")
        cb = self._callbacks.get(event.event_type)
        if cb:
            try:
                cb(event)
            except Exception as exc:
                print(f"[VoiceAgent] callback error: {exc}")

    def start(self) -> None:
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print("[VoiceAgent] started listening loop")

    def stop(self) -> None:
        self._running = False
        self.audio_io.stop()
        self.tts.stop()
        if self._thread:
            self._thread.join(timeout=2)
        print("[VoiceAgent] stopped")

    def interrupt(self) -> None:
        with self._lock:
            if self.state == AudioState.SPEAKING:
                self.state = AudioState.INTERRUPTED
                self.tts.stop()
                self._emit(VoiceEvent("interrupt", {"reason": "barge-in"}))
                print("[VoiceAgent] interrupted by barge-in")

    def _loop(self) -> None:
        while self._running:
            # Phase 1: Wake word detection
            wake_detected = self._detect_wake_word()
            if not wake_detected:
                continue

            self._emit(VoiceEvent("wake_word", {"word": self._last_wake_word}))
            self.state = AudioState.LISTENING

            # Phase 2: Record utterance
            audio_path = self._record_utterance()
            if not audio_path:
                self.state = AudioState.IDLE
                continue

            self._emit(VoiceEvent("speech_end", {"path": audio_path}))
            self.state = AudioState.PROCESSING

            # Phase 3: Transcribe
            stt_result = self.stt.transcribe_file(audio_path)
            self._emit(VoiceEvent("stt_result", stt_result.as_dict()))

            if not stt_result.text.strip():
                self.state = AudioState.IDLE
                continue

            # Phase 4: LLM processing
            response_text = self._process_with_llm(stt_result.text)
            if not response_text:
                self.state = AudioState.IDLE
                continue

            # Phase 5: Speak response
            self.state = AudioState.SPEAKING
            self._emit(VoiceEvent("tts_start", {"text": response_text}))
            tts_result = self.tts.speak_and_play(response_text, self.audio_io)
            self._emit(VoiceEvent("tts_end", tts_result.as_dict()))

            with self._lock:
                if self.state != AudioState.INTERRUPTED:
                    self.state = AudioState.IDLE

    def _detect_wake_word(self) -> bool:
        """Listen for wake word via short audio capture and transcription."""
        # In mock mode, simulate wake word detection
        if self.config.mock_mode or self.audio_io.is_mock():
            time.sleep(0.5)
            # Every 3rd cycle simulate wake word
            self._last_wake_word = "hey magnatrix"
            return True

        # Record 3-second snippets and check
        tmp_path = f"/tmp/magnatrix_wake_{int(time.time()*1000)}.wav"
        if not self.audio_io.capture_to_file(tmp_path, duration_sec=3):
            return False

        # Normalize and gate
        with wave.open(tmp_path, "rb") as w:
            data = w.readframes(w.getnframes())
        data = AudioIOEngine.normalize_audio(data)
        data = AudioIOEngine.noise_gate(data, threshold=self.config.vad_threshold)
        # Save processed
        with wave.open(tmp_path, "wb") as w:
            w.setnchannels(self.audio_io.fmt.channels)
            w.setsampwidth(self.audio_io.fmt.sample_width)
            w.setframerate(self.audio_io.fmt.sample_rate)
            w.writeframes(data)

        result = self.stt.transcribe_file(tmp_path)
        try:
            os.remove(tmp_path)
        except OSError:
            pass

        text = result.text.lower()
        for wake in self.config.wake_words:
            if wake.lower() in text:
                self._last_wake_word = wake
                return True
        return False

    def _record_utterance(self) -> Optional[str]:
        """Record until silence or max duration."""
        audio_path = f"/tmp/magnatrix_utterance_{int(time.time()*1000)}.wav"

        if self.config.mock_mode or self.audio_io.is_mock():
            self.audio_io.capture_to_file(audio_path, duration_sec=5)
            return audio_path

        # Record with auto-stop on silence
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as w:
            w.setnchannels(self.audio_io.fmt.channels)
            w.setsampwidth(self.audio_io.fmt.sample_width)
            w.setframerate(self.audio_io.fmt.sample_rate)

            silence_start: Optional[float] = None
            self.audio_io._recording = True
            start_time = time.time()

            def chunk_handler(chunk: bytes) -> None:
                nonlocal silence_start
                w.writeframes(chunk)
                if self.stt.vad_simple(chunk):
                    silence_start = None
                else:
                    if silence_start is None:
                        silence_start = time.time()

            # Start threaded capture
            capture_thread = threading.Thread(target=self.audio_io.capture_chunked, args=(chunk_handler, 1024))
            capture_thread.start()

            # Wait for silence timeout or max duration
            while capture_thread.is_alive():
                time.sleep(0.1)
                elapsed = (time.time() - start_time) * 1000
                if elapsed > self.config.max_recording_sec * 1000:
                    break
                if silence_start and (time.time() - silence_start) * 1000 > self.config.silence_timeout_ms:
                    break

            self.audio_io._recording = False
            capture_thread.join(timeout=1)

        # Save buffer
        with open(audio_path, "wb") as f:
            f.write(buffer.getvalue())
        return audio_path

    def _process_with_llm(self, text: str) -> str:
        if self._llm_hook:
            try:
                return self._llm_hook(text)
            except Exception as exc:
                print(f"[VoiceAgent] LLM hook error: {exc}")
        return f"I heard you say: {text}. LLM integration is not configured."

    def get_event_log(self) -> List[dict]:
        return [e.as_dict() for e in self._event_log]


# ──────────────────────────────────────────────────────────────
# 7.  VOICE PIPELINE ORCHESTRATOR
# ──────────────────────────────────────────────────────────────


class VoiceAudioPipelineNative:
    """Master orchestrator combining all sub-engines."""

    def __init__(self, config: Optional[VoiceConfig] = None):
        self.config = config or VoiceConfig()
        self.fmt = AudioFormat()
        self.audio_io = AudioIOEngine(self.config, self.fmt)
        self.stt = STTEngineNative(self.config, self.fmt)
        self.tts = TTSEngineNative(self.config, self.fmt)
        self.agent = VoiceAgentNative(self.config, self.audio_io, self.stt, self.tts)
        self._status: Dict[str, Any] = {}

    def initialize(self) -> dict:
        self._status = {
            "initialized": True,
            "mock_mode": self.config.mock_mode,
            "backends": BackendDetector.report(),
            "audio_io": self.audio_io.input_backend.value,
            "stt": self.stt._active.value,
            "tts": self.tts._active.value,
        }
        return self._status

    def start_agent(self) -> None:
        self.agent.start()

    def stop_agent(self) -> None:
        self.agent.stop()

    def speak(self, text: str) -> TTSResult:
        return self.tts.speak(text)

    def listen_once(self, duration_sec: int = 5) -> STTResult:
        tmp = f"/tmp/magnatrix_listen_{int(time.time()*1000)}.wav"
        self.audio_io.capture_to_file(tmp, duration_sec)
        result = self.stt.transcribe_file(tmp)
        try:
            os.remove(tmp)
        except OSError:
            pass
        return result

    def status(self) -> dict:
        return self._status

    def demo(self) -> dict:
        """End-to-end mock demo without requiring audio hardware."""
        print("=== VoiceAudioPipelineNative Demo ===")
        self.config.mock_mode = True
        self.audio_io.input_backend = AudioBackend.MOCK
        self.audio_io.output_backend = AudioBackend.MOCK
        self.stt._active = STTEngine.MOCK
        self.tts._active = TTSEngine.MOCK

        init = self.initialize()
        print(f"[Demo] init: {json.dumps(init, indent=2)}")

        # 1. TTS test
        tts_result = self.tts.speak("Hello Magnatrix. This is a test of the text to speech engine.")
        print(f"[Demo] TTS: {json.dumps(tts_result.as_dict(), indent=2)}")

        # 2. STT test (mock file)
        tmp = f"/tmp/magnatrix_demo_stt_{int(time.time()*1000)}.wav"
        self.audio_io._write_mock_wav(tmp, 3)
        stt_result = self.stt.transcribe_file(tmp)
        print(f"[Demo] STT: {json.dumps(stt_result.as_dict(), indent=2)}")
        try:
            os.remove(tmp)
        except OSError:
            pass

        # 3. Voice Agent test (single cycle)
        def mock_llm(text: str) -> str:
            return f"Mock LLM response to: {text}"

        self.agent.set_llm_hook(mock_llm)
        # Simulate one wake+listen cycle manually
        wake = self.agent._detect_wake_word()
        print(f"[Demo] Wake detected: {wake}")
        if wake:
            path = self.agent._record_utterance()
            print(f"[Demo] Recorded: {path}")
            if path:
                stt = self.stt.transcribe_file(path)
                print(f"[Demo] Transcribed: {stt.text}")
                response = self.agent._process_with_llm(stt.text)
                tts = self.tts.speak(response)
                print(f"[Demo] Response spoken: {tts.audio_path}")
                try:
                    os.remove(path)
                except OSError:
                    pass

        print("[Demo] Complete.")
        return {
            "init": init,
            "tts": tts_result.as_dict(),
            "stt": stt_result.as_dict(),
            "events": self.agent.get_event_log(),
        }

    def run(self) -> None:
        """Entry point for production use."""
        print("[VoiceAudioPipelineNative] Starting...")
        status = self.initialize()
        print(f"[Status] {json.dumps(status, indent=2)}")
        if status.get("mock_mode") or self.config.mock_mode:
            print("[Warning] Running in mock mode — no audio hardware detected.")
        self.start_agent()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("[VoiceAudioPipelineNative] shutting down...")
        finally:
            self.stop_agent()


# ──────────────────────────────────────────────────────────────
# 8.  SELF-TEST
# ──────────────────────────────────────────────────────────────


def run() -> dict:
    print("VoiceAudioPipelineNative self-test starting...")
    pipeline = VoiceAudioPipelineNative(VoiceConfig(mock_mode=True))
    return pipeline.demo()


if __name__ == "__main__":
    result = run()
    print("\n--- Final Result ---")
    print(json.dumps(result, indent=2, default=str))

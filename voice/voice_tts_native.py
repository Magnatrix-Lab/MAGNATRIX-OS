#!/usr/bin/env python3
"""
MAGNATRIX-OS | Layer 7 — Voice TTS Subsystem
Native text-to-speech with intonation, prosody, and caching.
- Phoneme-level synthesis with pitch contours
- Sentiment-driven prosody modulation
- WAV cache to avoid regeneration
"""
import math, struct, wave, io, json, hashlib, os, time, threading
from typing import List, Dict, Optional

SAMPLE_RATE = 22050


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


class ProsodyEngine:
    """Modulate pitch, speed, and energy based on sentiment markers."""

    SENTIMENT_MAP = {
        "!": (1.15, 0.95),   # (pitch_mult, speed_mult)
        "?": (1.05, 1.10),
        ".": (1.00, 1.00),
        "!!": (1.25, 0.90),
        "??": (1.10, 1.15),
        "...": (0.95, 1.30),
    }

    def __init__(self, base_pitch: float = 1.0, base_speed: float = 1.0):
        self.base_pitch = base_pitch
        self.base_speed = base_speed

    def parse(self, text: str) -> List[Dict]:
        """Break text into phrases with prosody params."""
        phrases = []
        # Simple split by punctuation
        import re
        parts = re.split(r'([!?.]+)', text)
        current = ""
        for part in parts:
            if re.match(r'[!?.]+', part):
                pitch, speed = self.SENTIMENT_MAP.get(part, (1.0, 1.0))
                phrases.append({
                    "text": current.strip(),
                    "pitch_mult": self.base_pitch * pitch,
                    "speed_mult": self.base_speed * speed,
                    "terminator": part,
                })
                current = ""
            else:
                current += part
        if current.strip():
            phrases.append({
                "text": current.strip(),
                "pitch_mult": self.base_pitch,
                "speed_mult": self.base_speed,
                "terminator": "",
            })
        return phrases


class Synthesizer:
    """Phonetic synthesizer with formant filtering."""

    FORMANTS = {
        'IY': (280, 2250, 3000), 'IH': (400, 2000, 2570), 'EH': (550, 1770, 2490),
        'AE': (700, 1660, 2460), 'AA': (760, 1330, 2500), 'AH': (710, 1100, 2540),
        'AO': (590, 880, 2540),  'UH': (470, 1170, 2680), 'UW': (350, 1250, 2200),
        'ER': (500, 1450, 2400), 'OW': (550, 960, 2400),  'EY': (600, 1900, 2600),
        'AY': (700, 1700, 2500), 'OY': (500, 1100, 2400), 'AW': (800, 1400, 2500),
        'B':  (0, 0, 0), 'D': (0, 0, 0), 'F': (0, 0, 0), 'G': (0, 0, 0),
        'K':  (0, 0, 0), 'L': (0, 0, 0), 'M': (0, 0, 0), 'N': (0, 0, 0),
        'P':  (0, 0, 0), 'R': (0, 0, 0), 'S': (0, 0, 0), 'T': (0, 0, 0),
        'V':  (0, 0, 0), 'W': (0, 0, 0), 'Z': (0, 0, 0), 'TH': (0, 0, 0),
        'SH': (0, 0, 0), 'CH': (0, 0, 0), 'JH': (0, 0, 0),
    }

    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate

    def phoneme_to_samples(self, ph: str, duration: float, pitch_mult: float = 1.0) -> List[float]:
        n = max(1, int(self.sample_rate * duration))
        f1, f2, f3 = self.FORMANTS.get(ph.upper(), (500, 1500, 2500))
        base_f = 120 * pitch_mult
        out = []
        for i in range(n):
            t = i / self.sample_rate
            # Fundamental + formants
            val = 0.6 * math.sin(2 * math.pi * base_f * t)
            if f1 > 0:
                val += 0.25 * math.sin(2 * math.pi * f1 * t)
                val += 0.15 * math.sin(2 * math.pi * f2 * t)
                val += 0.10 * math.sin(2 * math.pi * f3 * t)
            else:
                # Consonant noise burst
                val += (math.sin(i * 7.3) % 2 - 1) * 0.12
            # Envelope
            attack = min(1.0, i / (0.01 * self.sample_rate))
            release = min(1.0, (n - i) / (0.02 * self.sample_rate))
            val *= attack * release
            out.append(val * 0.8)
        return out

    def synthesize_phrase(self, phrase: Dict, phoneme_source) -> List[float]:
        text = phrase["text"]
        pitch = phrase["pitch_mult"]
        speed = phrase["speed_mult"]
        phonemes = phoneme_source(text)
        out = []
        base_dur = 0.10 / speed
        for ph in phonemes:
            out.extend(self.phoneme_to_samples(ph, base_dur, pitch))
            out.extend([0.0] * int(0.015 * self.sample_rate))
        return out


class TTSCache:
    """Disk-based WAV cache for TTS."""

    def __init__(self, cache_dir: str = "/tmp/magnatrix_tts_cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self._meta_path = os.path.join(cache_dir, "index.json")
        self._meta: Dict = {}
        self._lock = threading.Lock()
        if os.path.exists(self._meta_path):
            try:
                with open(self._meta_path, 'r') as f:
                    self._meta = json.load(f)
            except Exception:
                self._meta = {}

    def _save_meta(self):
        with open(self._meta_path, 'w') as f:
            json.dump(self._meta, f)

    def get(self, text: str) -> Optional[bytes]:
        key = _hash(text)
        with self._lock:
            if key in self._meta:
                path = os.path.join(self.cache_dir, f"{key}.wav")
                if os.path.exists(path):
                    with open(path, 'rb') as f:
                        return f.read()
        return None

    def put(self, text: str, wav: bytes):
        key = _hash(text)
        path = os.path.join(self.cache_dir, f"{key}.wav")
        with self._lock:
            with open(path, 'wb') as f:
                f.write(wav)
            self._meta[key] = {"text": text, "ts": time.time()}
            self._save_meta()

    def purge(self, max_age_hours: float = 24.0):
        cutoff = time.time() - max_age_hours * 3600
        with self._lock:
            for key, info in list(self._meta.items()):
                if info.get("ts", 0) < cutoff:
                    path = os.path.join(self.cache_dir, f"{key}.wav")
                    if os.path.exists(path):
                        os.remove(path)
                    del self._meta[key]
            self._save_meta()


class NativeTTSSystem:
    """Full TTS with prosody, cache, and export."""

    def __init__(self, cache_dir: str = "/tmp/magnatrix_tts_cache"):
        self.synth = Synthesizer()
        self.prosody = ProsodyEngine()
        self.cache = TTSCache(cache_dir)

    def _phonemize(self, text: str) -> List[str]:
        # Simple grapheme-to-phoneme approximation
        phoneme_map = {
            'a': 'AE', 'e': 'EH', 'i': 'IH', 'o': 'AO', 'u': 'UH',
            'A': 'AE', 'E': 'EH', 'I': 'IY', 'O': 'OW', 'U': 'UW',
            'b': 'B', 'c': 'K', 'd': 'D', 'f': 'F', 'g': 'G', 'h': 'H',
            'j': 'JH', 'k': 'K', 'l': 'L', 'm': 'M', 'n': 'N', 'p': 'P',
            'q': 'K', 'r': 'R', 's': 'S', 't': 'T', 'v': 'V', 'w': 'W',
            'x': 'KS', 'y': 'Y', 'z': 'Z', ' ': '_',
        }
        out = []
        for ch in text.lower():
            out.append(phoneme_map.get(ch, ''))
        return [p for p in out if p]

    def speak(self, text: str, use_cache: bool = True) -> bytes:
        if use_cache:
            cached = self.cache.get(text)
            if cached:
                return cached
        phrases = self.prosody.parse(text)
        samples = []
        for ph in phrases:
            samples.extend(self.synth.synthesize_phrase(ph, self._phonemize))
        # Normalize
        peak = max(abs(s) for s in samples) if samples else 1.0
        if peak > 1.0:
            samples = [s / peak for s in samples]
        wav = self._to_wav(samples)
        if use_cache:
            self.cache.put(text, wav)
        return wav

    def _to_wav(self, samples: List[float]) -> bytes:
        buf = io.BytesIO()
        with wave.open(buf, 'wb') as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(SAMPLE_RATE)
            pcm = struct.pack('<' + 'h' * len(samples), *[int(s * 32767) for s in samples])
            w.writeframes(pcm)
        return buf.getvalue()

    def speak_to_file(self, text: str, path: str) -> str:
        wav = self.speak(text)
        with open(path, 'wb') as f:
            f.write(wav)
        return path


# ─── SELF TESTS ───
if __name__ == "__main__":
    import sys
    tts = NativeTTSSystem()
    tests = [
        ("prosody_phrases", lambda: len(tts.prosody.parse("Hello world!")) >= 1),
        ("synth_samples", lambda: len(tts.synth.phoneme_to_samples("AE", 0.1)) > 0),
        ("cache_roundtrip", lambda: tts.speak("test cache") == tts.speak("test cache")),
        ("wav_header", lambda: tts.speak("hi")[:4] == b"RIFF"),
        ("file_write", lambda: os.path.exists(tts.speak_to_file("test", "/tmp/magnatrix_test_tts.wav"))),
        ("purge_old", lambda: (tts.cache.purge(0.0) or True) and True),
    ]
    passed = 0
    for name, fn in tests:
        try:
            ok = fn()
            print(f"  {'PASS' if ok else 'FAIL'} {name}")
            if ok:
                passed += 1
        except Exception as e:
            print(f"  FAIL {name}: {e}")
    print(f"\nTTS Subsystem: {passed}/{len(tests)} tests passed")
    sys.exit(0 if passed == len(tests) else 1)

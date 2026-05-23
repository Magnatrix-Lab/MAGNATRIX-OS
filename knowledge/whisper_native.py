"""
MAGNATRIX — Whisper Speech Recognition (Native Python Simulation)
Observed from: openai/whisper — 80K⭐ transformer-based speech recognition.

Pattern: AMATI-PELAJARI-TIRU — simulate core patterns in pure Python.
"""
from __future__ import annotations

import asyncio
import math
import random
import re
import struct
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple, Union


# ═══════════════════════════════════════════════════════════════════════════════
# CORE DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

class Language(Enum):
    """Supported languages untuk Whisper."""
    EN = "en"
    ID = "id"
    ES = "es"
    FR = "fr"
    DE = "de"
    JA = "ja"
    ZH = "zh"
    KO = "ko"
    PT = "pt"
    RU = "ru"


@dataclass
class AudioSegment:
    """Segment audio dengan metadata."""
    samples: List[float] = field(default_factory=list)
    sample_rate: int = 16000
    start_time: float = 0.0
    end_time: float = 0.0
    is_speech: bool = True

    def duration(self) -> float:
        return len(self.samples) / self.sample_rate

    def to_dict(self) -> Dict[str, Any]:
        return {
            "duration": self.duration(),
            "sample_rate": self.sample_rate,
            "start": self.start_time,
            "end": self.end_time,
            "is_speech": self.is_speech,
        }


@dataclass
class Token:
    """Token dalam vocabulary."""
    id: int
    text: str
    is_special: bool = False
    is_timestamp: bool = False
    timestamp: float = 0.0


@dataclass
class TranscriptionResult:
    """Hasil transkripsi audio."""
    text: str = ""
    language: str = "en"
    segments: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    processing_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "language": self.language,
            "segments": len(self.segments),
            "confidence": self.confidence,
            "processing_time": self.processing_time,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 1: AudioPreprocessor
# ═══════════════════════════════════════════════════════════════════════════════

class AudioPreprocessor:
    """Audio preprocessing: load, resample, frame, window, FFT."""

    def __init__(self, target_sample_rate: int = 16000) -> None:
        self.target_sr = target_sample_rate
        self.frame_size = int(0.025 * target_sample_rate)  # 25ms
        self.hop_size = int(0.010 * target_sample_rate)    # 10ms

    def load_wav(self, filepath: str) -> AudioSegment:
        """Load WAV file (mock — generate synthetic audio)."""
        # Mock: generate synthetic audio samples
        duration = 5.0  # 5 seconds
        num_samples = int(duration * self.target_sr)
        samples = [math.sin(2 * math.pi * 440 * t / self.target_sr) * 0.5 
                   for t in range(num_samples)]
        return AudioSegment(
            samples=samples,
            sample_rate=self.target_sr,
            start_time=0.0,
            end_time=duration,
        )

    def resample(self, audio: AudioSegment, target_sr: int) -> AudioSegment:
        """Resample audio ke target sample rate."""
        if audio.sample_rate == target_sr:
            return audio
        ratio = target_sr / audio.sample_rate
        new_length = int(len(audio.samples) * ratio)
        new_samples = [audio.samples[int(i / ratio)] for i in range(new_length)]
        return AudioSegment(
            samples=new_samples,
            sample_rate=target_sr,
            start_time=audio.start_time,
            end_time=audio.end_time,
        )

    def apply_window(self, frame: List[float]) -> List[float]:
        """Apply Hamming window ke frame."""
        n = len(frame)
        return [frame[i] * (0.54 - 0.46 * math.cos(2 * math.pi * i / (n - 1))) 
                for i in range(n)]

    def fft(self, frame: List[float]) -> List[float]:
        """Compute FFT power spectrum (simplified DFT)."""
        n = len(frame)
        magnitudes = []
        for k in range(n // 2 + 1):
            real = sum(frame[t] * math.cos(2 * math.pi * k * t / n) for t in range(n))
            imag = sum(frame[t] * math.sin(2 * math.pi * k * t / n) for t in range(n))
            magnitudes.append(math.sqrt(real**2 + imag**2))
        return magnitudes

    def preprocess(self, audio: AudioSegment) -> List[List[float]]:
        """Full preprocessing: frame → window → FFT."""
        samples = audio.samples
        frames = []
        for i in range(0, len(samples) - self.frame_size, self.hop_size):
            frame = samples[i:i + self.frame_size]
            if len(frame) < self.frame_size:
                frame.extend([0.0] * (self.frame_size - len(frame)))
            windowed = self.apply_window(frame)
            spectrum = self.fft(windowed)
            frames.append(spectrum)
        return frames


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 2: MelSpectrogram
# ═══════════════════════════════════════════════════════════════════════════════

class MelSpectrogram:
    """Mel spectrogram computation."""

    def __init__(self, n_mels: int = 80, n_fft: int = 400, sample_rate: int = 16000) -> None:
        self.n_mels = n_mels
        self.n_fft = n_fft
        self.sample_rate = sample_rate
        self.mel_filterbank = self._create_mel_filterbank()

    def _hz_to_mel(self, hz: float) -> float:
        """Convert Hz ke Mel scale."""
        return 2595 * math.log10(1 + hz / 700)

    def _mel_to_hz(self, mel: float) -> float:
        """Convert Mel ke Hz."""
        return 700 * (10 ** (mel / 2595) - 1)

    def _create_mel_filterbank(self) -> List[List[float]]:
        """Create Mel filterbank matrix."""
        f_min = 0
        f_max = self.sample_rate // 2
        mel_min = self._hz_to_mel(f_min)
        mel_max = self._hz_to_mel(f_max)
        
        # Mel points
        mel_points = [mel_min + (mel_max - mel_min) * i / (self.n_mels + 1) 
                      for i in range(self.n_mels + 2)]
        hz_points = [self._mel_to_hz(m) for m in mel_points]
        
        # FFT bin indices
        bin_indices = [int((self.n_fft + 1) * hz / self.sample_rate) for hz in hz_points]
        
        # Create filterbank
        filterbank = []
        for i in range(self.n_mels):
            filter_ = [0.0] * (self.n_fft // 2 + 1)
            for j in range(bin_indices[i], bin_indices[i + 1]):
                filter_[j] = (j - bin_indices[i]) / (bin_indices[i + 1] - bin_indices[i])
            for j in range(bin_indices[i + 1], bin_indices[i + 2]):
                filter_[j] = (bin_indices[i + 2] - j) / (bin_indices[i + 2] - bin_indices[i + 1])
            filterbank.append(filter_)
        
        return filterbank

    def compute(self, power_spectra: List[List[float]]) -> List[List[float]]:
        """Compute Mel spectrogram dari power spectra."""
        mel_specs = []
        for spectrum in power_spectra:
            mel_energies = []
            for filter_ in self.mel_filterbank:
                energy = sum(spectrum[i] * filter_[i] for i in range(len(filter_)))
                mel_energies.append(energy)
            mel_specs.append(mel_energies)
        
        # Log compression
        log_mel = [[math.log(max(m, 1e-10)) for m in frame] for frame in mel_specs]
        
        # Normalize
        max_val = max(max(frame) for frame in log_mel) if log_mel else 1.0
        normalized = [[m / max_val for m in frame] for frame in log_mel]
        
        return normalized


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 3: TransformerEncoder
# ═══════════════════════════════════════════════════════════════════════════════

class TransformerEncoder:
    """Simplified transformer encoder untuk speech."""

    def __init__(self, d_model: int = 512, n_heads: int = 8, n_layers: int = 6) -> None:
        self.d_model = d_model
        self.n_heads = n_heads
        self.n_layers = n_layers
        self.positional_encoding = self._create_positional_encoding()

    def _create_positional_encoding(self, max_len: int = 3000) -> List[List[float]]:
        """Create sinusoidal positional encoding."""
        pe = []
        for pos in range(max_len):
            pos_enc = []
            for i in range(self.d_model):
                angle = pos / (10000 ** ((2 * (i // 2)) / self.d_model))
                if i % 2 == 0:
                    pos_enc.append(math.sin(angle))
                else:
                    pos_enc.append(math.cos(angle))
            pe.append(pos_enc)
        return pe

    def _self_attention(self, query: List[float], keys: List[List[float]], 
                        values: List[List[float]]) -> List[float]:
        """Simplified scaled dot-product attention."""
        scores = []
        for key in keys:
            score = sum(q * k for q, k in zip(query, key)) / math.sqrt(len(query))
            scores.append(score)
        
        # Softmax
        exp_scores = [math.exp(s) for s in scores]
        sum_exp = sum(exp_scores)
        weights = [e / sum_exp for e in exp_scores]
        
        # Weighted sum
        output = [0.0] * len(values[0])
        for w, value in zip(weights, values):
            for i, v in enumerate(value):
                output[i] += w * v
        return output

    def encode(self, mel_spectrogram: List[List[float]]) -> List[List[float]]:
        """Encode Mel spectrogram ke latent representation."""
        # Add positional encoding
        encoded = []
        for i, frame in enumerate(mel_spectrogram):
            # Pad atau truncate ke d_model
            frame_padded = frame[:self.d_model] + [0.0] * (self.d_model - len(frame))
            pos_enc = self.positional_encoding[i % len(self.positional_encoding)]
            combined = [f + p for f, p in zip(frame_padded, pos_enc)]
            encoded.append(combined)
        
        # Mock: apply multi-layer attention
        for _ in range(self.n_layers):
            new_encoded = []
            for i, frame in enumerate(encoded):
                # Self-attention dengan neighboring frames
                context_start = max(0, i - 5)
                context_end = min(len(encoded), i + 6)
                context = encoded[context_start:context_end]
                attended = self._self_attention(frame, context, context)
                new_encoded.append(attended)
            encoded = new_encoded
        
        return encoded


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 4: TransformerDecoder
# ═══════════════════════════════════════════════════════════════════════════════

class TransformerDecoder:
    """Simplified transformer decoder untuk text generation."""

    def __init__(self, vocab_size: int = 51864, d_model: int = 512) -> None:
        self.vocab_size = vocab_size
        self.d_model = d_model
        self.positional_encoding = self._create_positional_encoding()

    def _create_positional_encoding(self, max_len: int = 448) -> List[List[float]]:
        """Create positional encoding untuk decoder."""
        pe = []
        for pos in range(max_len):
            pos_enc = []
            for i in range(self.d_model):
                angle = pos / (10000 ** ((2 * (i // 2)) / self.d_model))
                if i % 2 == 0:
                    pos_enc.append(math.sin(angle))
                else:
                    pos_enc.append(math.cos(angle))
            pe.append(pos_enc)
        return pe

    def _cross_attention(self, query: List[float], encoder_outputs: List[List[float]]) -> List[float]:
        """Cross-attention ke encoder outputs."""
        scores = []
        for enc_out in encoder_outputs:
            score = sum(q * e for q, e in zip(query, enc_out)) / math.sqrt(len(query))
            scores.append(score)
        
        exp_scores = [math.exp(s) for s in scores]
        sum_exp = sum(exp_scores)
        weights = [e / sum_exp for e in exp_scores]
        
        output = [0.0] * self.d_model
        for w, enc_out in zip(weights, encoder_outputs):
            for i, e in enumerate(enc_out[:self.d_model]):
                output[i] += w * e
        return output

    def decode_step(self, prev_tokens: List[int], encoder_outputs: List[List[float]], 
                    temperature: float = 1.0) -> int:
        """Single decoding step."""
        # Mock: generate next token based on previous tokens
        if not prev_tokens:
            return 50258  # <|startoftranscript|>
        
        # Simple heuristic: alternate between common words
        common_tokens = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
        
        # Add randomness based on temperature
        if temperature > 0:
            idx = int(random.random() * len(common_tokens))
        else:
            idx = len(prev_tokens) % len(common_tokens)
        
        return common_tokens[idx]


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 5: BPETokenizer
# ═══════════════════════════════════════════════════════════════════════════════

class BPETokenizer:
    """Byte Pair Encoding tokenizer (multilingual)."""

    def __init__(self) -> None:
        self.vocab_size = 51864
        self.special_tokens = {
            "<|startoftranscript|>": 50258,
            "<|endoftext|>": 50256,
            "<|notimestamps|>": 50363,
            "<|nospeech|>": 50362,
        }
        # Language tokens
        self.language_tokens = {
            lang.value: 50300 + i for i, lang in enumerate(Language)
        }
        # Timestamp tokens (0-30 seconds, 50ms resolution)
        self.timestamp_tokens = {}
        for i in range(1500):
            self.timestamp_tokens[i * 0.02] = 50364 + i
        
        # Mock vocabulary
        self.vocab = {i: f"token_{i}" for i in range(self.vocab_size)}
        self.vocab.update({v: k for k, v in self.special_tokens.items()})

    def encode(self, text: str, language: str = "en", task: str = "transcribe") -> List[int]:
        """Encode text ke token IDs."""
        tokens = []
        tokens.append(self.special_tokens["<|startoftranscript|>"])
        
        # Add language token
        if language in self.language_tokens:
            tokens.append(self.language_tokens[language])
        
        # Simple word tokenization (mock)
        words = text.lower().split()
        for word in words:
            # Hash word ke token ID
            token_id = hash(word) % 50000
            tokens.append(token_id)
        
        tokens.append(self.special_tokens["<|endoftext|>"])
        return tokens

    def decode(self, tokens: List[int]) -> str:
        """Decode token IDs ke text."""
        words = []
        for token in tokens:
            if token in self.vocab:
                word = self.vocab[token]
                if not word.startswith("<"):
                    words.append(word)
            else:
                # Mock: generate plausible word
                words.append(f"word_{token % 1000}")
        return " ".join(words)

    def is_timestamp_token(self, token: int) -> bool:
        """Check if token adalah timestamp."""
        return 50364 <= token <= 51863

    def timestamp_from_token(self, token: int) -> float:
        """Convert timestamp token ke seconds."""
        if self.is_timestamp_token(token):
            return (token - 50364) * 0.02
        return 0.0

    def token_from_timestamp(self, timestamp: float) -> int:
        """Convert seconds ke timestamp token."""
        idx = int(timestamp / 0.02)
        return min(50364 + idx, 51863)


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 6: VADModule
# ═══════════════════════════════════════════════════════════════════════════════

class VADModule:
    """Voice Activity Detection."""

    def __init__(self, energy_threshold: float = 0.01, hangover_frames: int = 10) -> None:
        self.energy_threshold = energy_threshold
        self.hangover_frames = hangover_frames

    def compute_energy(self, frame: List[float]) -> float:
        """Compute frame energy."""
        return sum(x**2 for x in frame) / len(frame)

    def compute_spectral_centroid(self, spectrum: List[float]) -> float:
        """Compute spectral centroid."""
        if not spectrum:
            return 0.0
        weighted_sum = sum(i * s for i, s in enumerate(spectrum))
        return weighted_sum / sum(spectrum) if sum(spectrum) > 0 else 0.0

    def detect_speech(self, audio: AudioSegment, frame_size: int = 400) -> List[AudioSegment]:
        """Detect speech segments dalam audio."""
        samples = audio.samples
        segments = []
        current_segment = []
        is_speech = False
        hangover_count = 0
        
        for i in range(0, len(samples), frame_size):
            frame = samples[i:i + frame_size]
            energy = self.compute_energy(frame)
            
            if energy > self.energy_threshold:
                if not is_speech:
                    # Speech start
                    is_speech = True
                    if current_segment:
                        segments.append(AudioSegment(
                            samples=current_segment,
                            sample_rate=audio.sample_rate,
                            start_time=(i - len(current_segment)) / audio.sample_rate,
                            end_time=i / audio.sample_rate,
                            is_speech=False,
                        ))
                    current_segment = []
                hangover_count = 0
            else:
                if is_speech:
                    hangover_count += 1
                    if hangover_count > self.hangover_frames:
                        # Speech end
                        is_speech = False
                        segments.append(AudioSegment(
                            samples=current_segment,
                            sample_rate=audio.sample_rate,
                            start_time=(i - len(current_segment)) / audio.sample_rate,
                            end_time=i / audio.sample_rate,
                            is_speech=True,
                        ))
                        current_segment = []
            
            current_segment.extend(frame)
        
        # Add final segment
        if current_segment:
            segments.append(AudioSegment(
                samples=current_segment,
                sample_rate=audio.sample_rate,
                start_time=(len(samples) - len(current_segment)) / audio.sample_rate,
                end_time=len(samples) / audio.sample_rate,
                is_speech=is_speech,
            ))
        
        return [s for s in segments if s.is_speech]


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 7: DecoderEngine
# ═══════════════════════════════════════════════════════════════════════════════

class DecoderEngine:
    """Decoding engine: beam search, temperature sampling, timestamp prediction."""

    def __init__(self, tokenizer: BPETokenizer, decoder: TransformerDecoder) -> None:
        self.tokenizer = tokenizer
        self.decoder = decoder

    def beam_search(self, encoder_outputs: List[List[float]], beam_width: int = 5, 
                    max_length: int = 100, temperature: float = 1.0) -> List[Tuple[List[int], float]]:
        """Beam search decoding."""
        beams = [([], 0.0)]  # (tokens, score)
        
        for _ in range(max_length):
            candidates = []
            for tokens, score in beams:
                if tokens and tokens[-1] == self.tokenizer.special_tokens["<|endoftext|>"]:
                    candidates.append((tokens, score))
                    continue
                
                # Get top-k next tokens
                next_token = self.decoder.decode_step(tokens, encoder_outputs, temperature)
                new_score = score + random.random()  # Mock scoring
                candidates.append((tokens + [next_token], new_score))
            
            # Select top beams
            candidates.sort(key=lambda x: x[1], reverse=True)
            beams = candidates[:beam_width]
        
        return beams

    def temperature_sampling(self, encoder_outputs: List[List[float]], 
                           temperature: float = 1.0, max_length: int = 100) -> List[int]:
        """Temperature-based sampling."""
        tokens = []
        
        for _ in range(max_length):
            next_token = self.decoder.decode_step(tokens, encoder_outputs, temperature)
            tokens.append(next_token)
            
            if next_token == self.tokenizer.special_tokens["<|endoftext|>"]:
                break
        
        return tokens

    def decode_with_timestamps(self, encoder_outputs: List[List[float]], 
                               temperature: float = 0.0) -> List[Dict[str, Any]]:
        """Decode dengan timestamp prediction."""
        tokens = self.temperature_sampling(encoder_outputs, temperature)
        
        segments = []
        current_text = []
        start_time = 0.0
        
        for token in tokens:
            if self.tokenizer.is_timestamp_token(token):
                timestamp = self.tokenizer.timestamp_from_token(token)
                if current_text:
                    segments.append({
                        "text": self.tokenizer.decode(current_text),
                        "start": start_time,
                        "end": timestamp,
                    })
                current_text = []
                start_time = timestamp
            else:
                current_text.append(token)
        
        return segments

    def condition_on_previous(self, encoder_outputs: List[List[float]], 
                              previous_text: str, temperature: float = 0.0) -> List[int]:
        """Condition decoding on previous text context."""
        # Encode previous text
        prev_tokens = self.tokenizer.encode(previous_text)
        
        # Continue generation
        tokens = prev_tokens[:]
        for _ in range(50):
            next_token = self.decoder.decode_step(tokens, encoder_outputs, temperature)
            tokens.append(next_token)
            if next_token == self.tokenizer.special_tokens["<|endoftext|>"]:
                break
        
        return tokens


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 8: WhisperKernel
# ═══════════════════════════════════════════════════════════════════════════════

class WhisperKernel:
    """MAGNATRIX bridge untuk Whisper speech recognition."""

    def __init__(self) -> None:
        self.preprocessor = AudioPreprocessor()
        self.mel_spectrogram = MelSpectrogram()
        self.encoder = TransformerEncoder()
        self.decoder = TransformerDecoder()
        self.tokenizer = BPETokenizer()
        self.vad = VADModule()
        self.decoder_engine = DecoderEngine(self.tokenizer, self.decoder)

    async def transcribe(self, audio: AudioSegment, language: str = "en", 
                         temperature: float = 0.0, with_timestamps: bool = False) -> TranscriptionResult:
        """Transcribe audio ke text."""
        start_time = time.time()
        
        # Preprocess
        power_spectra = self.preprocessor.preprocess(audio)
        
        # Mel spectrogram
        mel_spec = self.mel_spectrogram.compute(power_spectra)
        
        # Encode
        encoder_outputs = self.encoder.encode(mel_spec)
        
        # Decode
        if with_timestamps:
            segments = self.decoder_engine.decode_with_timestamps(encoder_outputs, temperature)
            text = " ".join([s["text"] for s in segments])
        else:
            tokens = self.decoder_engine.temperature_sampling(encoder_outputs, temperature)
            text = self.tokenizer.decode(tokens)
            segments = [{"text": text, "start": 0.0, "end": audio.duration()}]
        
        processing_time = time.time() - start_time
        
        return TranscriptionResult(
            text=text,
            language=language,
            segments=segments,
            confidence=random.uniform(0.7, 0.99),
            processing_time=processing_time,
        )

    async def transcribe_file(self, filepath: str, language: str = "en", 
                              **kwargs) -> TranscriptionResult:
        """Transcribe audio file."""
        audio = self.preprocessor.load_wav(filepath)
        return await self.transcribe(audio, language, **kwargs)

    async def transcribe_with_vad(self, audio: AudioSegment, language: str = "en") -> TranscriptionResult:
        """Transcribe dengan VAD segmentation."""
        speech_segments = self.vad.detect_speech(audio)
        
        all_segments = []
        full_text = []
        
        for segment in speech_segments:
            result = await self.transcribe(segment, language)
            for s in result.segments:
                s["start"] += segment.start_time
                s["end"] += segment.start_time
                all_segments.append(s)
            full_text.append(result.text)
        
        return TranscriptionResult(
            text=" ".join(full_text),
            language=language,
            segments=all_segments,
            confidence=random.uniform(0.7, 0.99),
        )

    async def translate(self, audio: AudioSegment, source_lang: str = "auto", 
                        target_lang: str = "en") -> TranscriptionResult:
        """Translate speech ke target language."""
        # First transcribe
        result = await self.transcribe(audio, source_lang)
        
        # Mock translation
        translated_text = f"[Translated to {target_lang}] {result.text}"
        
        return TranscriptionResult(
            text=translated_text,
            language=target_lang,
            segments=result.segments,
            confidence=result.confidence * 0.9,
        )

    def detect_language(self, audio: AudioSegment) -> str:
        """Detect language dari audio."""
        # Mock: random language detection
        languages = list(Language)
        detected = random.choice(languages)
        return detected.value

    async def stream_transcribe(self, audio_stream: List[AudioSegment], 
                                language: str = "en") -> List[TranscriptionResult]:
        """Real-time streaming transcription."""
        results = []
        for chunk in audio_stream:
            result = await self.transcribe(chunk, language)
            results.append(result)
        return results


# ═══════════════════════════════════════════════════════════════════════════════
# DEMO / __main__
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    async def demo() -> None:
        print("=" * 70)
        print("MAGNATRIX — Whisper Speech Recognition Demo")
        print("=" * 70)

        # Initialize kernel
        whisper = WhisperKernel()
        
        # Create test audio
        print("\n1. Creating test audio...")
        audio = whisper.preprocessor.load_wav("/tmp/test.wav")
        print(f"   Duration: {audio.duration():.2f}s, Samples: {len(audio.samples)}")
        
        # Preprocess
        print("\n2. Preprocessing audio...")
        power_spectra = whisper.preprocessor.preprocess(audio)
        print(f"   Frames: {len(power_spectra)}, Frame size: {len(power_spectra[0])}")
        
        # Mel spectrogram
        print("\n3. Computing Mel spectrogram...")
        mel_spec = whisper.mel_spectrogram.compute(power_spectra)
        print(f"   Mel frames: {len(mel_spec)}, Mel bins: {len(mel_spec[0])}")
        
        # Encode
        print("\n4. Encoding...")
        encoder_outputs = whisper.encoder.encode(mel_spec)
        print(f"   Encoder output shape: {len(encoder_outputs)}x{len(encoder_outputs[0])}")
        
        # Transcribe
        print("\n5. Transcribing (no timestamps)...")
        result = await whisper.transcribe(audio, language="en", temperature=0.0)
        print(f"   Text: {result.text[:80]}")
        print(f"   Language: {result.language}")
        print(f"   Confidence: {result.confidence:.2%}")
        print(f"   Processing time: {result.processing_time:.3f}s")
        
        # Transcribe dengan timestamps
        print("\n6. Transcribing (with timestamps)...")
        result_ts = await whisper.transcribe(audio, language="en", with_timestamps=True)
        print(f"   Segments: {len(result_ts.segments)}")
        for seg in result_ts.segments[:3]:
            print(f"   [{seg['start']:.2f}s - {seg['end']:.2f}s] {seg['text'][:40]}")
        
        # VAD
        print("\n7. VAD segmentation...")
        speech_segments = whisper.vad.detect_speech(audio)
        print(f"   Speech segments: {len(speech_segments)}")
        for seg in speech_segments[:3]:
            print(f"   [{seg.start_time:.2f}s - {seg.end_time:.2f}s] Duration: {seg.duration():.2f}s")
        
        # Multi-language
        print("\n8. Multi-language support...")
        for lang in ["en", "id", "es", "ja"]:
            result = await whisper.transcribe(audio, language=lang)
            print(f"   [{lang}] {result.text[:50]}")
        
        # Beam search
        print("\n9. Beam search decoding...")
        beams = whisper.decoder_engine.beam_search(encoder_outputs, beam_width=3, max_length=20)
        print(f"   Top {len(beams)} beams:")
        for i, (tokens, score) in enumerate(beams[:3]):
            text = whisper.tokenizer.decode(tokens)
            print(f"   Beam {i+1}: {text[:50]} (score: {score:.3f})")
        
        # Tokenizer demo
        print("\n10. Tokenizer...")
        text = "Hello world this is a test"
        tokens = whisper.tokenizer.encode(text, language="en")
        print(f"   Text: '{text}'")
        print(f"   Tokens: {tokens[:10]}...")
        decoded = whisper.tokenizer.decode(tokens)
        print(f"   Decoded: '{decoded[:50]}'")
        
        # Streaming
        print("\n11. Streaming transcription...")
        chunks = [audio] * 3  # Mock 3 chunks
        stream_results = await whisper.stream_transcribe(chunks, language="en")
        print(f"   Chunks processed: {len(stream_results)}")
        
        # Language detection
        print("\n12. Language detection...")
        detected = whisper.detect_language(audio)
        print(f"   Detected language: {detected}")
        
        # Translation
        print("\n13. Translation...")
        translated = await whisper.translate(audio, source_lang="id", target_lang="en")
        print(f"   Translated: {translated.text[:60]}")

        print("\n" + "=" * 70)
        print("Demo complete.")
        print("=" * 70)

    asyncio.run(demo())

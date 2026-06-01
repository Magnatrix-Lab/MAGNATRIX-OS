"""Multi-Modal Processor — Image, audio, video, and text input handling.

Modul ini menyediakan:
- InputParser untuk parsing multi-modal input dari berbagai format
- ImageAnalyzer (simulated) untuk deskripsi gambar dan OCR
- AudioProcessor (simulated) untuk transkripsi dan analisis audio
- VideoExtractor (simulated) untuk keyframe extraction dan scene detection
- MultiModalFusion untuk menggabungkan informasi dari berbagai modalitas
- FormatConverter untuk konversi antar format representasi
"""

from __future__ import annotations

import json
import base64
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from enum import Enum, auto


class Modality(Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"


class ImageFormat(Enum):
    PNG = "png"
    JPEG = "jpeg"
    WEBP = "webp"
    BMP = "bmp"


class AudioFormat(Enum):
    MP3 = "mp3"
    WAV = "wav"
    OGG = "ogg"
    FLAC = "flac"


class VideoFormat(Enum):
    MP4 = "mp4"
    AVI = "avi"
    WEBM = "webm"
    MOV = "mov"


@dataclass
class MediaChunk:
    """Single chunk of multi-modal data."""
    chunk_id: str
    modality: Modality
    format: str
    data: Union[str, bytes]  # text or base64-encoded binary
    metadata: Dict[str, Any] = field(default_factory=dict)
    size_bytes: int = 0
    timestamp: float = 0.0

    def is_text(self) -> bool:
        return self.modality == Modality.TEXT

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "modality": self.modality.value,
            "format": self.format,
            "size_bytes": self.size_bytes,
            "metadata": self.metadata,
        }


@dataclass
class AnalysisResult:
    """Result of analyzing a media chunk."""
    chunk_id: str
    modality: Modality
    description: str
    extracted_text: str = ""
    tags: List[str] = field(default_factory=list)
    confidence: float = 0.0
    raw_features: Dict[str, Any] = field(default_factory=dict)


class InputParser:
    """Parse multi-modal input into structured chunks."""

    def __init__(self):
        self._handlers: Dict[Modality, Callable[[Any], MediaChunk]] = {}
        self._setup_handlers()

    def _setup_handlers(self) -> None:
        self._handlers[Modality.TEXT] = self._parse_text
        self._handlers[Modality.IMAGE] = self._parse_image
        self._handlers[Modality.AUDIO] = self._parse_audio
        self._handlers[Modality.VIDEO] = self._parse_video

    def parse(self, inputs: List[Dict[str, Any]]) -> List[MediaChunk]:
        chunks = []
        for inp in inputs:
            modality = Modality(inp.get("modality", "text"))
            if modality in self._handlers:
                chunk = self._handlers[modality](inp)
                if chunk:
                    chunks.append(chunk)
        return chunks

    def _parse_text(self, inp: Dict[str, Any]) -> MediaChunk:
        return MediaChunk(
            chunk_id=str(uuid.uuid4())[:8],
            modality=Modality.TEXT,
            format="txt",
            data=inp.get("content", ""),
            size_bytes=len(inp.get("content", "").encode()),
            metadata=inp.get("metadata", {})
        )

    def _parse_image(self, inp: Dict[str, Any]) -> MediaChunk:
        return MediaChunk(
            chunk_id=str(uuid.uuid4())[:8],
            modality=Modality.IMAGE,
            format=inp.get("format", "png"),
            data=inp.get("data", ""),
            size_bytes=inp.get("size_bytes", 0),
            metadata={"width": inp.get("width", 0), "height": inp.get("height", 0), **inp.get("metadata", {})}
        )

    def _parse_audio(self, inp: Dict[str, Any]) -> MediaChunk:
        return MediaChunk(
            chunk_id=str(uuid.uuid4())[:8],
            modality=Modality.AUDIO,
            format=inp.get("format", "wav"),
            data=inp.get("data", ""),
            size_bytes=inp.get("size_bytes", 0),
            metadata={"duration": inp.get("duration", 0), "sample_rate": inp.get("sample_rate", 16000), **inp.get("metadata", {})}
        )

    def _parse_video(self, inp: Dict[str, Any]) -> MediaChunk:
        return MediaChunk(
            chunk_id=str(uuid.uuid4())[:8],
            modality=Modality.VIDEO,
            format=inp.get("format", "mp4"),
            data=inp.get("data", ""),
            size_bytes=inp.get("size_bytes", 0),
            metadata={"duration": inp.get("duration", 0), "fps": inp.get("fps", 30), **inp.get("metadata", {})}
        )

    def add_handler(self, modality: Modality, fn: Callable[[Any], MediaChunk]) -> None:
        self._handlers[modality] = fn


class ImageAnalyzer:
    """Simulated image analysis (no CV dependencies, pure stdlib)."""

    def analyze(self, chunk: MediaChunk) -> AnalysisResult:
        # Simulated analysis based on metadata
        meta = chunk.metadata
        width = meta.get("width", 512)
        height = meta.get("height", 512)
        size = chunk.size_bytes

        description = f"Gambar {width}x{height} pixels"
        if size > 1_000_000:
            description += ", high resolution"
        elif size < 100_000:
            description += ", thumbnail/ikon"

        tags = []
        if width > 1920 or height > 1080:
            tags.append("high-res")
        if width == height:
            tags.append("square")
        if width > height:
            tags.append("landscape")
        else:
            tags.append("portrait")
        tags.append(chunk.format)

        return AnalysisResult(
            chunk_id=chunk.chunk_id,
            modality=Modality.IMAGE,
            description=description,
            extracted_text=f"[OCR: {chunk.chunk_id}] Simulated text extraction from image",
            tags=tags,
            confidence=0.85,
            raw_features={"width": width, "height": height, "format": chunk.format, "size": size}
        )

    def describe(self, chunk: MediaChunk) -> str:
        result = self.analyze(chunk)
        return result.description

    def detect_objects(self, chunk: MediaChunk) -> List[str]:
        # Simulated object detection
        return ["object_1", "object_2", "object_3"]


class AudioProcessor:
    """Simulated audio processing (no audio dependencies, pure stdlib)."""

    def analyze(self, chunk: MediaChunk) -> AnalysisResult:
        meta = chunk.metadata
        duration = meta.get("duration", 0)
        sample_rate = meta.get("sample_rate", 16000)

        description = f"Audio {duration:.1f}s @ {sample_rate}Hz"
        if duration > 300:
            description += ", long recording"
        elif duration < 10:
            description += ", short clip"

        tags = []
        if duration > 60:
            tags.append("speech")
        tags.append(chunk.format)
        if sample_rate >= 44100:
            tags.append("high-quality")

        return AnalysisResult(
            chunk_id=chunk.chunk_id,
            modality=Modality.AUDIO,
            description=description,
            extracted_text=f"[Transcription: {chunk.chunk_id}] Simulated transcription of audio content...",
            tags=tags,
            confidence=0.82,
            raw_features={"duration": duration, "sample_rate": sample_rate, "format": chunk.format}
        )

    def transcribe(self, chunk: MediaChunk) -> str:
        result = self.analyze(chunk)
        return result.extracted_text

    def detect_speech(self, chunk: MediaChunk) -> bool:
        return chunk.metadata.get("duration", 0) > 1


class VideoExtractor:
    """Simulated video analysis (no video dependencies, pure stdlib)."""

    def analyze(self, chunk: MediaChunk) -> AnalysisResult:
        meta = chunk.metadata
        duration = meta.get("duration", 0)
        fps = meta.get("fps", 30)

        description = f"Video {duration:.1f}s @ {fps}fps"
        if duration > 600:
            description += ", long form"
        elif duration < 60:
            description += ", short form"

        tags = []
        if duration > 60:
            tags.append("video-content")
        tags.append(chunk.format)
        if fps >= 60:
            tags.append("high-fps")

        keyframes = max(1, int(duration / 5))

        return AnalysisResult(
            chunk_id=chunk.chunk_id,
            modality=Modality.VIDEO,
            description=description,
            extracted_text=f"[Keyframe analysis: {chunk.chunk_id}] {keyframes} keyframes extracted. Scene transitions detected.",
            tags=tags,
            confidence=0.78,
            raw_features={"duration": duration, "fps": fps, "keyframes": keyframes, "format": chunk.format}
        )

    def extract_keyframes(self, chunk: MediaChunk) -> List[str]:
        duration = chunk.metadata.get("duration", 0)
        count = max(1, int(duration / 5))
        return [f"keyframe_{i}" for i in range(count)]

    def detect_scenes(self, chunk: MediaChunk) -> List[Tuple[float, float]]:
        duration = chunk.metadata.get("duration", 0)
        if duration > 30:
            return [(0, duration / 2), (duration / 2, duration)]
        return [(0, duration)]


class MultiModalFusion:
    """Fuse analysis results from multiple modalities into unified context."""

    def __init__(self):
        self.analyzers: Dict[Modality, Any] = {
            Modality.IMAGE: ImageAnalyzer(),
            Modality.AUDIO: AudioProcessor(),
            Modality.VIDEO: VideoExtractor(),
        }

    def process(self, chunks: List[MediaChunk]) -> Dict[str, Any]:
        results = []
        for chunk in chunks:
            if chunk.modality in self.analyzers:
                result = self.analyzers[chunk.modality].analyze(chunk)
                results.append(result)
            elif chunk.modality == Modality.TEXT:
                results.append(AnalysisResult(
                    chunk_id=chunk.chunk_id,
                    modality=Modality.TEXT,
                    description="Text input",
                    extracted_text=chunk.data if isinstance(chunk.data, str) else "",
                    tags=["text"],
                    confidence=1.0
                ))
        return self._fuse(results)

    def _fuse(self, results: List[AnalysisResult]) -> Dict[str, Any]:
        all_texts = [r.extracted_text for r in results if r.extracted_text]
        all_tags = [tag for r in results for tag in r.tags]
        all_descriptions = [r.description for r in results]

        # Build unified context
        fused_text = "\n\n".join([
            "=== MULTI-MODAL INPUT ===",
            *[f"[{r.modality.value.upper()}] {r.description}" for r in results],
            "",
            "=== EXTRACTED CONTENT ===",
            *all_texts,
        ])

        return {
            "fused_text": fused_text,
            "modalities_present": list(set(r.modality.value for r in results)),
            "tags": list(set(all_tags)),
            "descriptions": all_descriptions,
            "confidence": sum(r.confidence for r in results) / max(len(results), 1),
            "results": [{
                "chunk_id": r.chunk_id,
                "modality": r.modality.value,
                "description": r.description,
                "tags": r.tags,
                "confidence": r.confidence,
            } for r in results]
        }

    def to_llm_messages(self, chunks: List[MediaChunk]) -> List[Dict[str, Any]]:
        """Convert chunks to LLM-compatible message format."""
        messages = []
        for chunk in chunks:
            if chunk.modality == Modality.TEXT:
                messages.append({"type": "text", "text": chunk.data})
            elif chunk.modality == Modality.IMAGE:
                data_str = chunk.data if isinstance(chunk.data, str) else ""
                messages.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/{chunk.format};base64,{data_str}"}
                })
            elif chunk.modality == Modality.AUDIO:
                messages.append({
                    "type": "text",
                    "text": f"[Audio: {chunk.metadata.get('duration', 0)}s, format={chunk.format}]"
                })
            elif chunk.modality == Modality.VIDEO:
                messages.append({
                    "type": "text",
                    "text": f"[Video: {chunk.metadata.get('duration', 0)}s, {chunk.metadata.get('fps', 30)}fps]"
                })
        return messages


class FormatConverter:
    """Convert between media formats and representations."""

    @staticmethod
    def text_to_base64(text: str) -> str:
        return base64.b64encode(text.encode()).decode()

    @staticmethod
    def base64_to_text(b64: str) -> str:
        return base64.b64decode(b64.encode()).decode()

    @staticmethod
    def chunk_to_json(chunk: MediaChunk) -> str:
        return json.dumps(chunk.to_dict(), indent=2)

    @staticmethod
    def chunks_to_markdown(chunks: List[MediaChunk]) -> str:
        lines = ["# Multi-Modal Input\n"]
        for chunk in chunks:
            lines.append(f"## {chunk.modality.value.upper()} ({chunk.format})\n")
            if chunk.modality == Modality.TEXT:
                lines.append(f"{chunk.data}\n")
            else:
                lines.append(f"- Size: {chunk.size_bytes} bytes\n")
                lines.append(f"- Metadata: {json.dumps(chunk.metadata)}\n")
            lines.append("\n")
        return "\n".join(lines)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("MULTI-MODAL PROCESSOR DEMO")
    print("=" * 70)

    # 1. Parse multi-modal input
    print("\n[1] Input Parsing")
    parser = InputParser()
    inputs = [
        {"modality": "text", "content": "Describe this image for me."},
        {"modality": "image", "format": "png", "data": "iVBORw0KGgo=...", "width": 1024, "height": 768, "size_bytes": 250000},
        {"modality": "audio", "format": "wav", "duration": 45.5, "size_bytes": 800000},
        {"modality": "video", "format": "mp4", "duration": 120, "fps": 30, "size_bytes": 5000000},
    ]
    chunks = parser.parse(inputs)
    for c in chunks:
        print(f"  {c.modality.value}: {c.format}, {c.size_bytes} bytes")

    # 2. Image analysis
    print("\n[2] Image Analysis")
    img_analyzer = ImageAnalyzer()
    img_chunk = next(c for c in chunks if c.modality == Modality.IMAGE)
    result = img_analyzer.analyze(img_chunk)
    print(f"  Description: {result.description}")
    print(f"  Tags: {result.tags}")
    print(f"  Confidence: {result.confidence}")
    objects = img_analyzer.detect_objects(img_chunk)
    print(f"  Detected objects: {objects}")

    # 3. Audio processing
    print("\n[3] Audio Processing")
    audio_proc = AudioProcessor()
    audio_chunk = next(c for c in chunks if c.modality == Modality.AUDIO)
    result = audio_proc.analyze(audio_chunk)
    print(f"  Description: {result.description}")
    print(f"  Transcription: {result.extracted_text[:60]}...")
    print(f"  Speech detected: {audio_proc.detect_speech(audio_chunk)}")

    # 4. Video extraction
    print("\n[4] Video Extraction")
    vid_ext = VideoExtractor()
    vid_chunk = next(c for c in chunks if c.modality == Modality.VIDEO)
    result = vid_ext.analyze(vid_chunk)
    print(f"  Description: {result.description}")
    keyframes = vid_ext.extract_keyframes(vid_chunk)
    print(f"  Keyframes: {len(keyframes)}")
    scenes = vid_ext.detect_scenes(vid_chunk)
    print(f"  Scenes: {scenes}")

    # 5. Fusion
    print("\n[5] Multi-Modal Fusion")
    fusion = MultiModalFusion()
    fused = fusion.process(chunks)
    print(f"  Modalities: {fused['modalities_present']}")
    print(f"  Tags: {fused['tags']}")
    print(f"  Avg confidence: {fused['confidence']:.2f}")
    print(f"  Fused text length: {len(fused['fused_text'])} chars")

    # 6. LLM message format
    print("\n[6] LLM Message Format")
    llm_msgs = fusion.to_llm_messages(chunks)
    for msg in llm_msgs:
        print(f"  {msg['type']}: {str(msg.get('text', ''))[:50]}...")

    # 7. Markdown conversion
    print("\n[7] Markdown Conversion")
    md = FormatConverter.chunks_to_markdown(chunks)
    print(f"  Markdown length: {len(md)} chars")
    print(f"  First 200 chars: {md[:200]}...")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()

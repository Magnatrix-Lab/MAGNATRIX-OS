"""Multi-Modal Engine — Handle text, image, audio, and document inputs.

Modul ini menyediakan:
- ModalityDetector untuk detect input type
- ImageProcessor untuk image analysis and captioning simulation
- AudioProcessor untuk speech-to-text simulation
- DocumentParser untuk PDF/text/doc extraction simulation
- MultiModalEngine untuk orchestrate multi-modal inputs
"""

from __future__ import annotations

import json
import time
import uuid
import base64
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
from enum import Enum, auto


class ModalityType(Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"
    CODE = "code"


@dataclass
class ModalityInput:
    """Single multi-modal input."""
    input_id: str
    modality: ModalityType
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    processed: bool = False
    extracted_text: str = ""


class ModalityDetector:
    """Detect the type of input."""

    def detect(self, content: str) -> ModalityType:
        if content.startswith("data:image") or content.startswith("http") and any(ext in content.lower() for ext in [".jpg", ".png", ".gif", ".jpeg", ".webp"]):
            return ModalityType.IMAGE
        if content.startswith("data:audio") or any(ext in content.lower() for ext in [".mp3", ".wav", ".ogg", ".m4a"]):
            return ModalityType.AUDIO
        if content.startswith("data:video") or any(ext in content.lower() for ext in [".mp4", ".avi", ".mov", ".mkv"]):
            return ModalityType.VIDEO
        if any(ext in content.lower() for ext in [".pdf", ".doc", ".docx", ".txt", ".md"]):
            return ModalityType.DOCUMENT
        if any(content.strip().startswith(kw) for kw in ["def ", "class ", "import ", "function", "const ", "var ", "let "]):
            return ModalityType.CODE
        return ModalityType.TEXT

    def detect_batch(self, contents: List[str]) -> List[ModalityType]:
        return [self.detect(c) for c in contents]


class ImageProcessor:
    """Process image inputs."""

    def __init__(self):
        self._caption_patterns: Dict[str, List[str]] = {
            "chart": ["bar chart showing", "line graph displaying", "pie chart with"],
            "photo": ["photo of", "image showing", "picture of"],
            "diagram": ["diagram illustrating", "flowchart showing", "schematic of"],
            "screenshot": ["screenshot of", "screen capture showing"],
        }

    def extract_features(self, image_data: str) -> Dict[str, Any]:
        # Simulated feature extraction
        return {
            "width": 1024,
            "height": 768,
            "format": "jpeg",
            "dominant_colors": ["blue", "white"],
            "objects_detected": ["text", "person", "object"],
        }

    def generate_caption(self, image_data: str) -> str:
        # Simulated caption generation
        return "An image containing visual information that can be described in text form."

    def analyze(self, image_data: str) -> Dict[str, Any]:
        return {
            "features": self.extract_features(image_data),
            "caption": self.generate_caption(image_data),
            "text_extracted": "Sample text from image",
        }


class AudioProcessor:
    """Process audio inputs."""

    def transcribe(self, audio_data: str, language: str = "en") -> str:
        # Simulated transcription
        return "[Transcribed audio content: This is a simulated speech-to-text conversion.]"

    def detect_language(self, audio_data: str) -> str:
        return "en"

    def get_duration(self, audio_data: str) -> float:
        return 10.0

    def analyze(self, audio_data: str) -> Dict[str, Any]:
        return {
            "transcription": self.transcribe(audio_data),
            "language": self.detect_language(audio_data),
            "duration": self.get_duration(audio_data),
        }


class DocumentParser:
    """Parse document inputs."""

    def parse(self, document_data: str, doc_type: str = "text") -> Dict[str, Any]:
        if doc_type == "pdf":
            return self._parse_pdf(document_data)
        elif doc_type == "text":
            return self._parse_text(document_data)
        return {"text": document_data, "pages": 1}

    def _parse_pdf(self, data: str) -> Dict[str, Any]:
        return {
            "text": "Extracted text from PDF document. " * 10,
            "pages": 5,
            "title": "Document Title",
            "sections": ["Introduction", "Method", "Results", "Conclusion"],
        }

    def _parse_text(self, data: str) -> Dict[str, Any]:
        lines = data.split("\n")
        return {
            "text": data,
            "pages": max(1, len(lines) // 50),
            "line_count": len(lines),
        }


class MultiModalEngine:
    """Orchestrate multi-modal inputs."""

    def __init__(self):
        self.detector = ModalityDetector()
        self.image_processor = ImageProcessor()
        self.audio_processor = AudioProcessor()
        self.document_parser = DocumentParser()
        self._inputs: List[ModalityInput] = []
        self._history: List[Dict[str, Any]] = []

    def process(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> ModalityInput:
        modality = self.detector.detect(content)
        inp = ModalityInput(
            input_id=str(uuid.uuid4())[:12],
            modality=modality,
            content=content[:1000],
            metadata=metadata or {},
        )
        # Process based on modality
        if modality == ModalityType.IMAGE:
            analysis = self.image_processor.analyze(content)
            inp.extracted_text = analysis["caption"]
        elif modality == ModalityType.AUDIO:
            analysis = self.audio_processor.analyze(content)
            inp.extracted_text = analysis["transcription"]
        elif modality == ModalityType.DOCUMENT:
            doc_type = metadata.get("doc_type", "text") if metadata else "text"
            analysis = self.document_parser.parse(content, doc_type)
            inp.extracted_text = analysis["text"]
        elif modality == ModalityType.CODE:
            inp.extracted_text = content
        else:
            inp.extracted_text = content
        inp.processed = True
        self._inputs.append(inp)
        return inp

    def process_batch(self, items: List[Tuple[str, Optional[Dict[str, Any]]]]) -> List[ModalityInput]:
        return [self.process(c, m) for c, m in items]

    def get_unified_text(self, input_ids: Optional[List[str]] = None) -> str:
        inputs = self._inputs
        if input_ids:
            inputs = [i for i in inputs if i.input_id in input_ids]
        texts = []
        for inp in inputs:
            if inp.modality == ModalityType.TEXT:
                texts.append(inp.extracted_text)
            else:
                texts.append(f"[{inp.modality.value}]: {inp.extracted_text}")
        return "\n\n".join(texts)

    def get_stats(self) -> Dict[str, Any]:
        counts = {}
        for inp in self._inputs:
            counts[inp.modality.value] = counts.get(inp.modality.value, 0) + 1
        return {
            "total_inputs": len(self._inputs),
            "modality_breakdown": counts,
        }

    def export(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump([{
                "input_id": i.input_id,
                "modality": i.modality.value,
                "extracted_text": i.extracted_text[:100],
            } for i in self._inputs], f, indent=2)


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("MULTI-MODAL ENGINE DEMO")
    print("=" * 70)

    engine = MultiModalEngine()

    # 1. Process different modalities
    print("\n[1] Process Different Modalities")
    inputs = [
        ("Hello, how are you?", None),
        ("data:image/jpeg;base64,abc123", {"image_type": "photo"}),
        ("data:audio/wav;base64,xyz789", {"duration": 15.0}),
        ("This is a PDF document about AI.", {"doc_type": "pdf"}),
        ("def hello():\n    return 'world'", None),
    ]
    results = engine.process_batch(inputs)
    for r in results:
        print(f"  {r.input_id}: {r.modality.value} -> {r.extracted_text[:50]}...")

    # 2. Unified text
    print("\n[2] Unified Text Representation")
    unified = engine.get_unified_text()
    print(f"  {unified[:200]}...")

    # 3. Modality detection
    print("\n[3] Modality Detection")
    test_contents = [
        "Just plain text",
        "data:image/png;base64,...",
        "report.pdf",
        "data:audio/mp3;base64,...",
        "class MyClass { ... }",
    ]
    for c in test_contents:
        mod = engine.detector.detect(c)
        print(f"  '{c[:30]}...' -> {mod.value}")

    # 4. Image analysis
    print("\n[4] Image Analysis")
    img_analysis = engine.image_processor.analyze("data:image/jpeg;base64,test")
    print(f"  Features: {img_analysis['features']}")
    print(f"  Caption: {img_analysis['caption']}")

    # 5. Audio transcription
    print("\n[5] Audio Transcription")
    audio = engine.audio_processor.analyze("data:audio/wav;base64,test")
    print(f"  Duration: {audio['duration']}s")
    print(f"  Language: {audio['language']}")
    print(f"  Text: {audio['transcription'][:50]}...")

    # 6. Document parsing
    print("\n[6] Document Parsing")
    doc = engine.document_parser.parse("This is a long text document.\n" * 100, "text")
    print(f"  Pages: {doc['pages']}, Lines: {doc['line_count']}")
    pdf = engine.document_parser.parse("PDF content", "pdf")
    print(f"  PDF pages: {pdf['pages']}, Sections: {pdf['sections']}")

    # 7. Stats
    print(f"\n[7] Stats")
    print(f"  {engine.get_stats()}")

    # 8. Export
    print("\n[8] Export")
    engine.export("/tmp/multimodal.json")
    print("  Exported to /tmp/multimodal.json")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()

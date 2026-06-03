"""LLM Email Attachment Handler — Native Python (stdlib only)."""
from __future__ import annotations
import base64, mimetypes, os
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

@dataclass
class EmailAttachment:
    filename: str
    content_type: str
    content: bytes
    size: int
    metadata: Dict[str, Any] = field(default_factory=dict)

class EmailAttachmentHandler:
    def __init__(self, max_size: int = 25 * 1024 * 1024) -> None:
        self.max_size = max_size
        self._attachments: List[EmailAttachment] = []

    def add_attachment(self, filename: str, content: bytes) -> EmailAttachment:
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        size = len(content)
        if size > self.max_size:
            raise ValueError("Attachment too large: " + str(size) + " bytes exceeds " + str(self.max_size))
        att = EmailAttachment(filename, content_type, content, size)
        self._attachments.append(att)
        return att

    def encode_base64(self, content: bytes) -> str:
        return base64.b64encode(content).decode("ascii")

    def decode_base64(self, encoded: str) -> bytes:
        return base64.b64decode(encoded)

    def get_total_size(self) -> int:
        return sum(a.size for a in self._attachments)

    def get_by_type(self, content_type: str) -> List[EmailAttachment]:
        return [a for a in self._attachments if a.content_type.startswith(content_type)]

    def get_stats(self) -> Dict[str, Any]:
        counts = {}
        for a in self._attachments:
            counts[a.content_type] = counts.get(a.content_type, 0) + 1
        return {"attachments": len(self._attachments), "total_size": self.get_total_size(), "by_type": counts}

def run() -> None:
    print("Email Attachment Handler test")
    e = EmailAttachmentHandler()
    e.add_attachment("document.pdf", b"PDF content placeholder")
    e.add_attachment("image.png", b"PNG binary data")
    e.add_attachment("report.xlsx", b"Excel content")
    print("  Total size: " + str(e.get_total_size()))
    print("  PDF attachments: " + str(len(e.get_by_type("application/pdf"))))
    print("  Stats: " + str(e.get_stats()))
    print("Email Attachment Handler test complete.")

if __name__ == "__main__":
    run()

"""OSINT Metadata Extractor — File metadata, EXIF simulation."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class MetadataResult:
    filename: str = ""
    file_type: str = ""
    size_bytes: int = 0
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class OsintMetadataExtractor:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._extracted: list[MetadataResult] = []
        self._persist_path = self.root / "osint_metadata.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._extracted = [MetadataResult(**e) for e in data.get("extracted", [])]

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "extracted": [e.__dict__ for e in self._extracted]
        }, indent=2))

    def extract_from_pdf(self, filename: str, size_bytes: int, header_data: dict = None) -> MetadataResult:
        meta = {
            "producer": header_data.get("producer", "") if header_data else "",
            "creator": header_data.get("creator", "") if header_data else "",
            "creation_date": header_data.get("creation_date", "") if header_data else "",
            "author": header_data.get("author", "") if header_data else "",
            "title": header_data.get("title", "") if header_data else "",
        }
        result = MetadataResult(filename=filename, file_type="pdf", size_bytes=size_bytes, metadata=meta)
        self._extracted.append(result)
        self._save()
        return result

    def extract_from_image(self, filename: str, size_bytes: int, exif_data: dict = None) -> MetadataResult:
        meta = {
            "camera": exif_data.get("camera", "") if exif_data else "",
            "date_taken": exif_data.get("date_taken", "") if exif_data else "",
            "gps_lat": exif_data.get("gps_lat", "") if exif_data else "",
            "gps_lon": exif_data.get("gps_lon", "") if exif_data else "",
            "software": exif_data.get("software", "") if exif_data else "",
        }
        result = MetadataResult(filename=filename, file_type="image", size_bytes=size_bytes, metadata=meta)
        self._extracted.append(result)
        self._save()
        return result

    def extract_from_headers(self, filename: str, headers: dict) -> MetadataResult:
        meta = {
            "server": headers.get("server", ""),
            "x_powered_by": headers.get("x-powered-by", ""),
            "content_type": headers.get("content-type", ""),
            "set_cookie": headers.get("set-cookie", ""),
        }
        result = MetadataResult(filename=filename, file_type="headers", size_bytes=0, metadata=meta)
        self._extracted.append(result)
        self._save()
        return result

    def to_dict(self) -> dict:
        return {"extracted_count": len(self._extracted), "types": list(set(e.file_type for e in self._extracted))}

    def get_stats(self) -> dict:
        by_type = {}
        for e in self._extracted:
            by_type[e.file_type] = by_type.get(e.file_type, 0) + 1
        return {"total": len(self._extracted), "by_type": by_type}

__all__ = ["OsintMetadataExtractor", "MetadataResult"]

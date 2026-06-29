"""OSINT Email Harvester — Email extraction, domain-based generation."""
from dataclasses import dataclass
from pathlib import Path
import json, re, random

@dataclass
class EmailEntry:
    email: str = ""
    source: str = ""
    confidence: float = 0.0
    verified: bool = False

class OsintEmailHarvester:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._emails: list[EmailEntry] = []
        self._patterns = [
            r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
            r'[a-zA-Z0-9._%+-]+\s*@\s*[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        ]
        self._persist_path = self.root / "osint_email.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._emails = [EmailEntry(**e) for e in data.get("emails", [])]

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "emails": [e.__dict__ for e in self._emails]
        }, indent=2))

    def extract_from_text(self, text: str, source: str = "") -> list[EmailEntry]:
        found = []
        for pattern in self._patterns:
            matches = re.findall(pattern, text)
            for m in matches:
                email = m.replace(" ", "").replace(chr(10), "").replace(chr(9), "")
                if not any(e.email == email for e in self._emails):
                    entry = EmailEntry(email=email, source=source, confidence=0.8)
                    self._emails.append(entry)
                    found.append(entry)
        self._save()
        return found

    def generate_from_pattern(self, domain: str, first_names: list[str], last_names: list[str], patterns: list[str] = None) -> list[EmailEntry]:
        if patterns is None:
            patterns = ["{f}.{l}@{d}", "{f}{l}@{d}", "{f}_{l}@{d}", "{l}.{f}@{d}", "{f}@{d}", "{l}@{d}"]
        generated = []
        for fn in first_names:
            for ln in last_names:
                for p in patterns:
                    email = p.format(f=fn.lower(), l=ln.lower(), d=domain)
                    if not any(e.email == email for e in self._emails):
                        entry = EmailEntry(email=email, source="generated", confidence=0.3)
                        self._emails.append(entry)
                        generated.append(entry)
        self._save()
        return generated

    def verify_format(self, email: str) -> bool:
        return re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email) is not None

    def to_dict(self) -> dict:
        return {"email_count": len(self._emails), "verified": sum(1 for e in self._emails if e.verified)}

    def get_stats(self) -> dict:
        return {"emails": len(self._emails), "verified": sum(1 for e in self._emails if e.verified), "generated": sum(1 for e in self._emails if e.source == "generated")}

__all__ = ["OsintEmailHarvester", "EmailEntry"]

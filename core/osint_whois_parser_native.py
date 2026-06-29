"""OSINT WHOIS Parser — WHOIS data parsing, registrar info."""
from dataclasses import dataclass
from pathlib import Path
import json

@dataclass
class WhoisRecord:
    domain: str = ""
    registrar: str = ""
    creation_date: str = ""
    expiration_date: str = ""
    updated_date: str = ""
    name_servers: list[str] = None
    status: list[str] = None
    privacy_protected: bool = False
    registrant_org: str = ""
    registrant_country: str = ""
    admin_email: str = ""
    tech_email: str = ""

    def __post_init__(self):
        if self.name_servers is None:
            self.name_servers = []
        if self.status is None:
            self.status = []

class OsintWhoisParser:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._records: dict[str, WhoisRecord] = {}
        self._persist_path = self.root / "osint_whois.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._records = {k: WhoisRecord(**v) for k, v in data.get("records", {}).items()}

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "records": {k: v.__dict__ for k, v in self._records.items()}
        }, indent=2))

    def parse(self, domain: str, raw_whois: str) -> WhoisRecord:
        record = WhoisRecord(domain=domain)
        lines = raw_whois.split(chr(10))
        for line in lines:
            if ":" in line:
                key, val = line.split(":", 1)
                key = key.strip().lower()
                val = val.strip()
                if key in ("registrar", "sponsoring registrar"):
                    record.registrar = val
                elif key in ("creation date", "created"):
                    record.creation_date = val
                elif key in ("expiration date", "registry expiry date"):
                    record.expiration_date = val
                elif key in ("updated date", "last updated"):
                    record.updated_date = val
                elif key in ("name server", "nserver"):
                    record.name_servers.append(val)
                elif key == "status":
                    record.status.append(val)
                elif key in ("registrant organization", "org"):
                    record.registrant_org = val
                elif key in ("registrant country", "country"):
                    record.registrant_country = val
                elif key in ("admin email", "e-mail"):
                    record.admin_email = val
                elif key in ("tech email",):
                    record.tech_email = val
        record.privacy_protected = "privacy" in raw_whois.lower() or "redacted" in raw_whois.lower()
        self._records[domain] = record
        self._save()
        return record

    def get_record(self, domain: str) -> WhoisRecord | None:
        return self._records.get(domain)

    def list_privacy_protected(self) -> list[str]:
        return [d for d, r in self._records.items() if r.privacy_protected]

    def to_dict(self) -> dict:
        return {"record_count": len(self._records), "privacy_protected": len(self.list_privacy_protected())}

    def get_stats(self) -> dict:
        return {"records": len(self._records), "privacy_protected": len(self.list_privacy_protected()), "registrars": len(set(r.registrar for r in self._records.values() if r.registrar))}

__all__ = ["OsintWhoisParser", "WhoisRecord"]

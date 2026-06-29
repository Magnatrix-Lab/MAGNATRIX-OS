"""
tls_certificate_monitor_native.py
MAGNATRIX-OS — TLS Certificate Monitor

Inspired by Frogy2.0: TLS certificate monitoring and SSL/TLS posture analysis. Pure stdlib.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta


@dataclass
class TLSRecord:
    domain: str
    issuer: str
    subject: str
    serial_number: str
    not_before: str
    not_after: str
    sans: List[str] = field(default_factory=list)
    signature_algorithm: str = ""
    key_length: int = 2048
    is_valid: bool = True
    days_until_expiry: int = 0
    checked_at: str = ""

    def __post_init__(self):
        if not self.checked_at:
            self.checked_at = datetime.now().isoformat()
        try:
            expiry = datetime.fromisoformat(self.not_after)
            self.days_until_expiry = (expiry - datetime.now()).days
        except Exception:
            self.days_until_expiry = 0


class TLSCertificateMonitor:
    """Monitor TLS certificates for expiry and misconfiguration."""

    def __init__(self, data_dir: str = "./tls_monitor"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.certificates: Dict[str, TLSRecord] = {}
        self._load()

    def _load(self) -> None:
        file = self.data_dir / "certificates.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for domain, cd in data.items():
                        self.certificates[domain] = TLSRecord(**cd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.data_dir / "certificates.json", "w", encoding="utf-8") as f:
            json.dump({d: asdict(c) for d, c in self.certificates.items()}, f, indent=2)

    def check_certificate(self, domain: str) -> TLSRecord:
        """Simulate certificate inspection."""
        import random
        not_after = (datetime.now() + timedelta(days=random.randint(10, 730))).isoformat()
        not_before = (datetime.now() - timedelta(days=random.randint(1, 365))).isoformat()
        cert = TLSRecord(
            domain=domain, issuer=random.choice(["DigiCert", "Let's Encrypt", "GlobalSign", "Sectigo"]),
            subject=f"CN={domain}", serial_number=f"{random.randint(100000000, 999999999)}",
            not_before=not_before, not_after=not_after,
            sans=[f"www.{domain}", f"*.{domain}"] if random.random() > 0.3 else [],
            signature_algorithm=random.choice(["sha256WithRSAEncryption", "ecdsa-with-SHA256"]),
            key_length=random.choice([2048, 4096]), is_valid=random.random() > 0.05,
        )
        self.certificates[domain] = cert
        self._save()
        return cert

    def get_expiring(self, days: int = 30) -> List[TLSRecord]:
        return [c for c in self.certificates.values() if 0 <= c.days_until_expiry <= days]

    def get_expired(self) -> List[TLSRecord]:
        return [c for c in self.certificates.values() if c.days_until_expiry < 0]

    def get_weak_certs(self) -> List[TLSRecord]:
        return [c for c in self.certificates.values() if c.key_length < 2048 or "sha1" in c.signature_algorithm.lower()]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_certs": len(self.certificates), "expiring_30d": len(self.get_expiring(30)),
            "expired": len(self.get_expired()), "weak": len(self.get_weak_certs()),
        }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["TLSCertificateMonitor", "TLSRecord"]
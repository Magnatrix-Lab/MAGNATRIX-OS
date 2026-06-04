"""Certificate Manager — X509-style cert, chain validation, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import time
import hashlib
import json

class CertStatus(Enum):
    VALID = auto()
    EXPIRED = auto()
    REVOKED = auto()
    SELF_SIGNED = auto()

@dataclass
class Certificate:
    cert_id: str
    subject: str
    issuer: str
    public_key: str
    valid_from: float
    valid_to: float
    signature: str
    is_ca: bool = False

    def is_valid(self, now: float = None) -> bool:
        now = now or time.time()
        return self.valid_from <= now <= self.valid_to

    def fingerprint(self) -> str:
        data = f"{self.subject}:{self.issuer}:{self.public_key}:{self.valid_from}:{self.valid_to}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

class CertificateManager:
    def __init__(self):
        self.certs: Dict[str, Certificate] = {}
        self.trusted_roots: Set[str] = set()
        self.revoked: Set[str] = set()
        self.chains: Dict[str, List[str]] = {}

    def add_cert(self, cert: Certificate):
        self.certs[cert.cert_id] = cert

    def add_trusted_root(self, cert_id: str):
        self.trusted_roots.add(cert_id)

    def revoke(self, cert_id: str):
        self.revoked.add(cert_id)

    def verify(self, cert_id: str) -> CertStatus:
        cert = self.certs.get(cert_id)
        if not cert:
            return CertStatus.REVOKED
        if cert_id in self.revoked:
            return CertStatus.REVOKED
        if not cert.is_valid():
            return CertStatus.EXPIRED
        if cert.issuer == cert.subject:
            return CertStatus.SELF_SIGNED
        return CertStatus.VALID

    def build_chain(self, cert_id: str) -> List[str]:
        chain = []
        current = cert_id
        visited = set()
        while current and current not in visited:
            visited.add(current)
            cert = self.certs.get(current)
            if not cert:
                break
            chain.append(current)
            if current in self.trusted_roots:
                break
            parent = next((cid for cid, c in self.certs.items() if c.subject == cert.issuer and c.is_ca), None)
            current = parent
        return chain

    def validate_chain(self, cert_id: str) -> bool:
        chain = self.build_chain(cert_id)
        for cid in chain:
            if self.verify(cid) in (CertStatus.EXPIRED, CertStatus.REVOKED):
                return False
        return len(chain) > 0 and chain[-1] in self.trusted_roots

    def stats(self) -> Dict:
        return {"certs": len(self.certs), "trusted_roots": len(self.trusted_roots), "revoked": len(self.revoked)}

def run():
    cm = CertificateManager()
    root = Certificate("root", "CA Root", "CA Root", "pk_root", 0, time.time() + 86400 * 365, "sig_root", is_ca=True)
    leaf = Certificate("leaf", "user1", "CA Root", "pk_user", 0, time.time() + 86400 * 30, "sig_leaf")
    cm.add_cert(root)
    cm.add_cert(leaf)
    cm.add_trusted_root("root")
    print(cm.verify("leaf"))
    print(cm.build_chain("leaf"))
    print(cm.validate_chain("leaf"))
    print(cm.stats())

if __name__ == "__main__":
    run()

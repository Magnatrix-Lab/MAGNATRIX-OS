"""OSINT Domain Recon — Subdomain enumeration, DNS records."""
from dataclasses import dataclass
from pathlib import Path
import json, random, hashlib

@dataclass
class DomainRecord:
    domain: str = ""
    record_type: str = ""  # A | AAAA | MX | TXT | NS | CNAME
    value: str = ""
    ttl: int = 0

@dataclass
class Subdomain:
    name: str = ""
    ips: list[str] = None
    records: list[DomainRecord] = None

    def __post_init__(self):
        if self.ips is None:
            self.ips = []
        if self.records is None:
            self.records = []

class OsintDomainRecon:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._domains: dict[str, list[Subdomain]] = {}
        self._wordlist = ["www", "mail", "ftp", "admin", "api", "blog", "shop", "dev", "test", "staging", "vpn", "ns1", "ns2"]
        self._persist_path = self.root / "osint_domain.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._domains = {k: [Subdomain(**s) for s in v] for k, v in data.get("domains", {}).items()}

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "domains": {k: [{"name": s.name, "ips": s.ips, "records": [r.__dict__ for r in s.records]} for s in v] for k, v in self._domains.items()}
        }, indent=2))

    def enumerate_subdomains(self, domain: str, depth: int = 1) -> list[Subdomain]:
        subs = []
        for word in self._wordlist:
            sub_name = f"{word}.{domain}"
            # Simulate DNS resolution
            ip = f"192.168.{random.randint(1,254)}.{random.randint(1,254)}"
            sub = Subdomain(name=sub_name, ips=[ip])
            sub.records.append(DomainRecord(domain=sub_name, record_type="A", value=ip, ttl=300))
            subs.append(sub)
        self._domains[domain] = subs
        self._save()
        return subs

    def get_dns_records(self, domain: str) -> list[DomainRecord]:
        records = []
        for sub in self._domains.get(domain, []):
            records.extend(sub.records)
        return records

    def add_wordlist(self, words: list[str]) -> None:
        self._wordlist.extend(words)
        self._wordlist = list(set(self._wordlist))

    def to_dict(self) -> dict:
        return {"domain_count": len(self._domains), "total_subdomains": sum(len(v) for v in self._domains.values())}

    def get_stats(self) -> dict:
        return {"domains": len(self._domains), "subdomains": sum(len(v) for v in self._domains.values()), "wordlist_size": len(self._wordlist)}

__all__ = ["OsintDomainRecon", "Subdomain", "DomainRecord"]

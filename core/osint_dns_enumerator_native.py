"""OSINT DNS Enumerator — DNS brute force, zone transfer detection."""
from dataclasses import dataclass
from pathlib import Path
import json, random

@dataclass
class DNSRecord:
    name: str = ""
    type: str = ""
    value: str = ""
    ttl: int = 0

class OsintDnsEnumerator:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._records: dict[str, list[DNSRecord]] = {}
        self._zone_transfer_possible: dict[str, bool] = {}
        self._wordlist = ["www", "mail", "ftp", "admin", "api", "blog", "shop", "dev", "test", "vpn", "ns1", "ns2", "mx", "smtp", "pop", "imap"]
        self._persist_path = self.root / "osint_dns.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._records = {k: [DNSRecord(**r) for r in v] for k, v in data.get("records", {}).items()}
            self._zone_transfer_possible = data.get("zone_transfer", {})

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "records": {k: [r.__dict__ for r in v] for k, v in self._records.items()},
            "zone_transfer": self._zone_transfer_possible
        }, indent=2))

    def brute_force(self, domain: str, record_types: list[str] = None) -> list[DNSRecord]:
        if record_types is None:
            record_types = ["A", "AAAA", "MX", "TXT", "CNAME", "NS"]
        results = []
        for sub in self._wordlist:
            for rtype in record_types:
                if rtype == "A":
                    value = f"192.168.{random.randint(1,254)}.{random.randint(1,254)}"
                elif rtype == "AAAA":
                    value = f"2001:db8::{random.randint(1,65535)}"
                elif rtype == "MX":
                    value = f"10 mail.{sub}.{domain}"
                elif rtype == "TXT":
                    value = f"v=spf1 include:{sub}.{domain}"
                else:
                    value = f"{sub}.{domain}"
                record = DNSRecord(name=f"{sub}.{domain}", type=rtype, value=value, ttl=300)
                results.append(record)
        self._records[domain] = results
        self._save()
        return results

    def check_zone_transfer(self, domain: str) -> bool:
        # Simulate zone transfer vulnerability detection
        possible = random.random() < 0.1  # 10% chance simulated
        self._zone_transfer_possible[domain] = possible
        self._save()
        return possible

    def get_records(self, domain: str) -> list[DNSRecord]:
        return self._records.get(domain, [])

    def to_dict(self) -> dict:
        return {"domain_count": len(self._records), "zone_transfer_vulnerable": sum(1 for v in self._zone_transfer_possible.values() if v)}

    def get_stats(self) -> dict:
        return {"domains": len(self._records), "total_records": sum(len(v) for v in self._records.values()), "zone_transfer_vuln": sum(1 for v in self._zone_transfer_possible.values() if v)}

__all__ = ["OsintDnsEnumerator", "DNSRecord"]

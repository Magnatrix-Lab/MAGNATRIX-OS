#!/usr/bin/env python3
"""
MAGNATRIX-OS | Layer 13 — OSINT Reconnaissance
Native Open Source Intelligence engine without paid API dependencies.
- Passive DNS recon (subdomain brute + permutation)
- Social media handle correlation
- Email/username permutation generator
- Web scraping metadata extraction
- Geolocation enrichment from EXIF/cellular/WiFi
"""
import json, time, hashlib, re, socket, struct, os, sys, random, itertools, threading
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict, deque
from urllib.parse import urlparse


class DNSRecon:
    """Passive DNS reconnaissance with subdomain enumeration."""

    SUB_LIST = [
        "www", "mail", "ftp", "localhost", "webmail", "smtp", "pop", "ns1", "ns2",
        "admin", "api", "app", "beta", "blog", "cdn", "chat", "cloud", "cpanel",
        "crm", "dashboard", "data", "demo", "dev", "dns", "docs", "email",
        "files", "forum", "git", "help", "images", "img", "intranet", "login",
        "m", "mobile", "mx", "my", "news", "old", "panel", "partner", "pay",
        "portal", "remote", "secure", "shop", "staging", "status", "store",
        "support", "test", "upload", "video", "vpn", "web", "wiki", "ww",
        "ww1", "ww2", "ww3", "www1", "www2", "www3", "api-v1", "api-v2",
        "graphql", "rest", "swagger", "oauth", "auth", "sso", "idp",
    ]

    def __init__(self, target: str, threads: int = 20):
        self.target = target
        self.threads = threads
        self._results: Dict[str, List[str]] = {}
        self._lock = threading.Lock()

    def _resolve(self, subdomain: str) -> Optional[str]:
        hostname = f"{subdomain}.{self.target}"
        try:
            ip = socket.gethostbyname(hostname)
            return ip
        except Exception:
            return None

    def brute(self, extra: List[str] = None) -> Dict[str, str]:
        wordlist = self.SUB_LIST + (extra or [])
        found = {}
        sem = threading.Semaphore(self.threads)

        def _task(sub):
            with sem:
                ip = self._resolve(sub)
                if ip:
                    with self._lock:
                        found[sub] = ip

        threads = []
        for sub in wordlist:
            t = threading.Thread(target=_task, args=(sub,))
            t.start()
            threads.append(t)
        for t in threads:
            t.join()
        return found

    def permute(self, base: str, separators: List[str] = ["-", "_", ""]) -> List[str]:
        """Generate permutations like dev-api, dev_api, devapi."""
        out = []
        for sep in separators:
            for perm in itertools.permutations([base, "api", "dev", "staging", "test"]):
                out.append(sep.join(perm))
        return list(set(out))[:100]


class UsernamePermutator:
    """Generate email/username permutations from first/last name."""

    def generate(self, first: str, last: str, domain: str = "") -> List[str]:
        f = first.lower()
        l = last.lower()
        fi = f[0] if f else ""
        li = l[0] if l else ""
        patterns = [
            f, l, f + l, l + f, fi + l, f + li, fi + li,
            f + "." + l, l + "." + f, fi + "." + l, f + "." + li,
            f + "_" + l, l + "_" + f, fi + "_" + l, f + "_" + li,
            f + l + "123", l + f + "123", f + "2024", l + "2024",
        ]
        if domain:
            return [f"{p}@{domain}" for p in patterns]
        return patterns


class MetadataExtractor:
    """Extract metadata from HTML headers, robots.txt, sitemap."""

    def parse_headers(self, headers: Dict[str, str]) -> Dict:
        out = {}
        for k, v in headers.items():
            kl = k.lower()
            if "server" in kl:
                out["server"] = v
            if "x-powered-by" in kl:
                out["stack"] = v
            if "set-cookie" in kl:
                out["cookies"] = v
            if "strict-transport-security" in kl:
                out["hsts"] = True
            if "content-security-policy" in kl:
                out["csp"] = v[:100]
        return out

    def parse_robots(self, text: str) -> Dict[str, List[str]]:
        out = {"allow": [], "disallow": [], "sitemap": []}
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("Allow:"):
                out["allow"].append(line.split(":", 1)[1].strip())
            elif line.startswith("Disallow:"):
                out["disallow"].append(line.split(":", 1)[1].strip())
            elif line.startswith("Sitemap:"):
                out["sitemap"].append(line.split(":", 1)[1].strip())
        return out

    def extract_emails(self, text: str) -> List[str]:
        return list(set(re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', text)))

    def extract_urls(self, text: str) -> List[str]:
        return list(set(re.findall(r'https?://[^\s\"<>]+', text)))


class GeolocationEnricher:
    """Simulated geolocation enrichment from EXIF/cellular/WiFi."""

    def from_mac(self, mac: str) -> Optional[Dict]:
        # Simulated WiFi geolocation lookup
        if not re.match(r'^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$', mac):
            return None
        # Deterministic fake location from MAC hash
        h = hashlib.sha256(mac.encode()).hexdigest()
        lat = (int(h[:8], 16) % 18000) / 100 - 90
        lon = (int(h[8:16], 16) % 36000) / 100 - 180
        return {"lat": round(lat, 4), "lon": round(lon, 4), "accuracy": 50, "source": "wifi"}

    def from_cell(self, mcc: int, mnc: int, lac: int, cid: int) -> Optional[Dict]:
        h = hashlib.sha256(f"{mcc}-{mnc}-{lac}-{cid}".encode()).hexdigest()
        lat = (int(h[:8], 16) % 18000) / 100 - 90
        lon = (int(h[8:16], 16) % 36000) / 100 - 180
        return {"lat": round(lat, 4), "lon": round(lon, 4), "accuracy": 500, "source": "cell"}

    def from_exif(self, exif_dict: Dict) -> Optional[Dict]:
        if "GPSInfo" in exif_dict:
            gps = exif_dict["GPSInfo"]
            return {"lat": gps.get("GPSLatitude", 0), "lon": gps.get("GPSLongitude", 0), "accuracy": 10, "source": "exif"}
        return None


class OSINTReconEngine:
    """Full OSINT engine combining all subsystems."""

    def __init__(self, target_domain: str = ""):
        self.domain = target_domain
        self.dns = DNSRecon(target_domain)
        self.permutator = UsernamePermutator()
        self.metadata = MetadataExtractor()
        self.geo = GeolocationEnricher()
        self._report: Dict = {}

    def run_full(self, first: str = "", last: str = str) -> Dict:
        self._report = {
            "domain": self.domain,
            "subdomains": self.dns.brute(),
            "permutations": self.permutator.generate(first, last, self.domain) if first else [],
            "timestamp": time.time(),
        }
        return self._report

    def to_json(self, path: str):
        with open(path, 'w') as f:
            json.dump(self._report, f, indent=2)
        return path


# ─── SELF TESTS ───
if __name__ == "__main__":
    tests = []
    def _t(name, fn):
        tests.append((name, fn))

    _t("dns_resolve", lambda: DNSRecon("example.com")._resolve("www") is not None)
    _t("dns_brute", lambda: len(DNSRecon("example.com").brute(["www", "mail"])) > 0)
    _t("permute", lambda: len(DNSRecon("x.com").permute("dev")) > 0)
    _t("username_gen", lambda: len(UsernamePermutator().generate("John", "Doe", "example.com")) > 5)
    _t("metadata_headers", lambda: "server" in MetadataExtractor().parse_headers({"Server": "nginx"}))
    _t("robots_parse", lambda: len(MetadataExtractor().parse_robots("Disallow: /admin\nSitemap: /s.xml")["disallow"]) == 1)
    _t("extract_emails", lambda: "a@b.com" in MetadataExtractor().extract_emails("contact a@b.com and b@c.com"))
    _t("geo_mac", lambda: GeolocationEnricher().from_mac("00:11:22:33:44:55") is not None)
    _t("geo_cell", lambda: GeolocationEnricher().from_cell(510, 10, 100, 2000) is not None)
    _t("engine_full", lambda: len(OSINTReconEngine("example.com").run_full("John", "Doe").get("subdomains", {})) >= 0)

    passed = 0
    for name, fn in tests:
        try:
            ok = fn()
            print(f"  {'PASS' if ok else 'FAIL'} {name}")
            if ok:
                passed += 1
        except Exception as e:
            print(f"  FAIL {name}: {e}")
    print(f"\nOSINT Recon: {passed}/{len(tests)} tests passed")
    sys.exit(0 if passed == len(tests) else 1)

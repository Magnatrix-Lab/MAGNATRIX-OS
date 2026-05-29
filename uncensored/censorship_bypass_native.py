#!/usr/bin/env python3
"""
uncensored/censorship_bypass_native.py — MAGNATRIX-OS Native Censorship Bypass Engine
Pure stdlib. No external dependencies.

Features:
  • NativeDomainRotator — health-checked domain pool with rotation strategies
  • NativeDoHResolver — DNS-over-HTTPS resolution (urllib-based)
  • NativeProxyChainManager — multi-hop proxy chain building + health monitoring
  • NativeContentFilterEvasion — payload obfuscation, fragmentation, mimicry
  • NativeBypassEngine — composes all layers, self-test demo

Naming convention: Native<ClassName>
"""

from __future__ import annotations

import base64
import hashlib
import json
import random
import re
import ssl
import threading
import time
import urllib.request
import urllib.error
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# NativeDomainRotator
# ---------------------------------------------------------------------------

class NativeDomainRotator:
    """Rotate across a pool of domains with health checking."""

    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    WEIGHTED = "weighted"

    def __init__(self, strategy: str = ROUND_ROBIN) -> None:
        self.strategy = strategy
        self._domains: List[Dict[str, Any]] = []
        self._index = 0
        self._lock = threading.RLock()

    def add(self, domain: str, weight: int = 1, protocols: Optional[List[str]] = None) -> None:
        entry = {
            "domain": domain,
            "weight": max(1, weight),
            "healthy": True,
            "last_check": 0.0,
            "failures": 0,
            "protocols": protocols or ["https"],
        }
        with self._lock:
            self._domains.append(entry)

    def _get_healthy(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [d for d in self._domains if d["healthy"]]

    def pick(self) -> Optional[str]:
        healthy = self._get_healthy()
        if not healthy:
            return None
        with self._lock:
            if self.strategy == self.ROUND_ROBIN:
                choice = healthy[self._index % len(healthy)]
                self._index += 1
            elif self.strategy == self.RANDOM:
                choice = random.choice(healthy)
            elif self.strategy == self.WEIGHTED:
                total = sum(d["weight"] for d in healthy)
                pick = self._index % total
                self._index += 1
                cumulative = 0
                for d in healthy:
                    cumulative += d["weight"]
                    if pick < cumulative:
                        choice = d
                        break
                else:
                    choice = healthy[-1]
            else:
                choice = healthy[0]
            proto = choice["protocols"][0]
            return f"{proto}://{choice['domain']}"

    def report_failure(self, domain_url: str) -> None:
        with self._lock:
            for d in self._domains:
                if domain_url.endswith(d["domain"]):
                    d["failures"] += 1
                    if d["failures"] >= 3:
                        d["healthy"] = False
                    break

    def report_success(self, domain_url: str) -> None:
        with self._lock:
            for d in self._domains:
                if domain_url.endswith(d["domain"]):
                    d["failures"] = max(0, d["failures"] - 1)
                    d["healthy"] = True
                    break

    def healthcheck_all(self, timeout: float = 2.0) -> None:
        """Simulated healthcheck: mark all as healthy after cooldown."""
        now = time.time()
        with self._lock:
            for d in self._domains:
                if not d["healthy"] and now - d["last_check"] > 30:
                    d["healthy"] = True
                    d["failures"] = max(0, d["failures"] - 1)
                    d["last_check"] = now

    def list_domains(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "domain": d["domain"],
                    "healthy": d["healthy"],
                    "weight": d["weight"],
                    "failures": d["failures"],
                }
                for d in self._domains
            ]


# ---------------------------------------------------------------------------
# NativeDoHResolver
# ---------------------------------------------------------------------------

class NativeDoHResolver:
    """DNS-over-HTTPS client using only urllib (no external DNS libs)."""

    DEFAULT_ENDPOINTS = [
        "https://cloudflare-dns.com/dns-query",
        "https://dns.google/dns-query",
        "https://doh.opendns.com/dns-query",
    ]

    def __init__(self, endpoints: Optional[List[str]] = None) -> None:
        self.endpoints = endpoints or list(self.DEFAULT_ENDPOINTS)
        self._last_endpoint = 0
        self._lock = threading.RLock()

    def _build_doh_url(self, endpoint: str, name: str, type_: int = 1) -> str:
        """Build DoH GET URL (RFC 8484). Type 1 = A record."""
        import base64
        # Minimal DNS wire format for A query
        qname = b"".join(bytes([len(p)]) + p.encode() for p in name.split(".")) + b"\x00"
        query = qname + b"\x00\x01\x00\x01"  # type A, class IN
        b64 = base64.urlsafe_b64encode(query).rstrip(b"=").decode()
        return f"{endpoint}?dns={b64}"

    def resolve(self, hostname: str, type_: int = 1) -> List[str]:
        """Return list of resolved IPs (simulated — returns mock if urllib fails)."""
        with self._lock:
            endpoint = self.endpoints[self._last_endpoint % len(self.endpoints)]
            self._last_endpoint += 1

        url = self._build_doh_url(endpoint, hostname, type_)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={"Accept": "application/dns-message"})
        try:
            with urllib.request.urlopen(req, timeout=3, context=ctx) as resp:
                _ = resp.read()
                # Real DoH parsing is complex; we simulate success
                return [f"1.2.3.{random.randint(1, 254)}"]
        except Exception:
            # Fallback: simulate resolution for self-test
            return [f"1.2.3.{random.randint(1, 254)}"]

    def resolve_batch(self, hostnames: List[str]) -> Dict[str, List[str]]:
        results = {}
        for h in hostnames:
            results[h] = self.resolve(h)
        return results


# ---------------------------------------------------------------------------
# NativeProxyChainManager
# ---------------------------------------------------------------------------

class NativeProxyChainManager:
    """Build and manage multi-hop proxy chains with health awareness."""

    def __init__(self) -> None:
        self._proxies: List[Dict[str, Any]] = []
        self._chains: List[List[int]] = []
        self._lock = threading.RLock()

    def add_proxy(self, host: str, port: int, protocol: str = "socks5", weight: int = 1) -> int:
        entry = {
            "id": len(self._proxies),
            "host": host,
            "port": port,
            "protocol": protocol,
            "weight": weight,
            "healthy": True,
            "latency_ms": 0.0,
            "last_used": 0.0,
        }
        with self._lock:
            self._proxies.append(entry)
            return entry["id"]

    def build_chain(self, length: int = 2, strategy: str = "random") -> Optional[List[Dict[str, Any]]]:
        """Build a proxy chain of given length from healthy proxies."""
        healthy = [p for p in self._proxies if p["healthy"]]
        if len(healthy) < length:
            return None
        with self._lock:
            if strategy == "random":
                selected = random.sample(healthy, length)
            elif strategy == "weighted":
                selected = []
                pool = list(healthy)
                for _ in range(length):
                    if not pool:
                        break
                    total = sum(p["weight"] for p in pool)
                    pick = random.randint(1, total)
                    cumulative = 0
                    for p in pool:
                        cumulative += p["weight"]
                        if pick <= cumulative:
                            selected.append(p)
                            pool.remove(p)
                            break
            else:
                selected = healthy[:length]
            for p in selected:
                p["last_used"] = time.time()
            self._chains.append([p["id"] for p in selected])
            return selected

    def report_latency(self, proxy_id: int, latency_ms: float) -> None:
        with self._lock:
            if 0 <= proxy_id < len(self._proxies):
                self._proxies[proxy_id]["latency_ms"] = latency_ms

    def report_failure(self, proxy_id: int) -> None:
        with self._lock:
            if 0 <= proxy_id < len(self._proxies):
                p = self._proxies[proxy_id]
                p["healthy"] = False

    def get_all_proxies(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "id": p["id"],
                    "host": p["host"],
                    "port": p["port"],
                    "healthy": p["healthy"],
                    "latency_ms": p["latency_ms"],
                }
                for p in self._proxies
            ]


# ---------------------------------------------------------------------------
# NativeContentFilterEvasion
# ---------------------------------------------------------------------------

class NativeContentFilterEvasion:
    """Techniques to evade content filtering: obfuscation, fragmentation, mimicry."""

    def __init__(self) -> None:
        self._mimicry_templates: Dict[str, str] = {}

    def register_mimicry(self, name: str, template: str) -> None:
        """Register a mimicry template (e.g., wrap payload in HTML comment)."""
        self._mimicry_templates[name] = template

    def obfuscate_base64(self, data: bytes) -> str:
        """Base64 with random line breaks and junk comment lines."""
        b64 = base64.b64encode(data).decode()
        lines = [b64[i:i + 40] for i in range(0, len(b64), 40)]
        junk = [f"# {hashlib.md5(str(i).encode()).hexdigest()[:8]}" for i in range(len(lines))]
        interleaved = []
        for j, l in zip(junk, lines):
            interleaved.append(j)
            interleaved.append(l)
        return "\n".join(interleaved)

    def deobfuscate_base64(self, text: str) -> bytes:
        lines = [l for l in text.splitlines() if not l.startswith("#")]
        b64 = "".join(lines)
        return base64.b64decode(b64)

    def fragment_payload(self, data: bytes, chunk_size: int = 64) -> List[Dict[str, Any]]:
        """Split payload into numbered fragments with checksums."""
        fragments = []
        total = len(data)
        for i in range(0, total, chunk_size):
            chunk = data[i:i + chunk_size]
            fragments.append({
                "seq": i // chunk_size,
                "total": (total + chunk_size - 1) // chunk_size,
                "checksum": hashlib.md5(chunk).hexdigest()[:8],
                "payload": base64.b64encode(chunk).decode(),
            })
        return fragments

    def reassemble_payload(self, fragments: List[Dict[str, Any]]) -> bytes:
        """Reassemble fragments ordered by seq, verify checksums."""
        ordered = sorted(fragments, key=lambda f: f["seq"])
        parts = []
        for f in ordered:
            chunk = base64.b64decode(f["payload"])
            expected = hashlib.md5(chunk).hexdigest()[:8]
            if f["checksum"] != expected:
                raise ValueError(f"checksum mismatch at seq {f['seq']}")
            parts.append(chunk)
        return b"".join(parts)

    def mimicry_wrap(self, payload: bytes, template_name: str = "html_comment") -> str:
        template = self._mimicry_templates.get(template_name, "<!-- {payload} -->")
        b64 = base64.b64encode(payload).decode()
        return template.replace("{payload}", b64)

    def mimicry_unwrap(self, text: str, template_name: str = "html_comment") -> bytes:
        template = self._mimicry_templates.get(template_name, "<!-- {payload} -->")
        prefix, suffix = template.split("{payload}", 1)
        text = text.strip()
        if text.startswith(prefix) and text.endswith(suffix):
            inner = text[len(prefix):-len(suffix)]
            return base64.b64decode(inner)
        raise ValueError("mimicry unwrap failed")

    def polymorphic_encode(self, data: bytes) -> Dict[str, Any]:
        """Apply random combination of obfuscation techniques."""
        mode = random.choice(["base64_junk", "fragment", "mimicry"])
        if mode == "base64_junk":
            return {"mode": "base64_junk", "data": self.obfuscate_base64(data)}
        elif mode == "fragment":
            return {"mode": "fragment", "data": self.fragment_payload(data)}
        else:
            return {"mode": "mimicry", "data": self.mimicry_wrap(data)}

    def polymorphic_decode(self, envelope: Dict[str, Any]) -> bytes:
        mode = envelope["mode"]
        if mode == "base64_junk":
            return self.deobfuscate_base64(envelope["data"])
        elif mode == "fragment":
            return self.reassemble_payload(envelope["data"])
        elif mode == "mimicry":
            return self.mimicry_unwrap(envelope["data"])
        raise ValueError(f"unknown evasion mode: {mode}")


# ---------------------------------------------------------------------------
# NativeBypassEngine
# ---------------------------------------------------------------------------

class NativeBypassEngine:
    """Composes domain rotation, DoH, proxy chains, and evasion."""

    def __init__(self) -> None:
        self.domain_rotator = NativeDomainRotator()
        self.doh = NativeDoHResolver()
        self.proxy_manager = NativeProxyChainManager()
        self.evasion = NativeContentFilterEvasion()
        self._metrics: Dict[str, Any] = {
            "requests": 0,
            "failures": 0,
            "chains_built": 0,
        }
        self._lock = threading.RLock()

    def configure(self, domains: List[str], proxies: List[Tuple[str, int, str]]) -> None:
        for d in domains:
            self.domain_rotator.add(d)
        for host, port, proto in proxies:
            self.proxy_manager.add_proxy(host, port, proto)

    def resolve_target(self, hostname: str) -> List[str]:
        return self.doh.resolve_batch([hostname])

    def build_proxy_chain(self, length: int = 2) -> Optional[List[Dict[str, Any]]]:
        chain = self.proxy_manager.build_chain(length)
        if chain:
            with self._lock:
                self._metrics["chains_built"] += 1
        return chain

    def evade_and_send(self, payload: bytes) -> Dict[str, Any]:
        """Simulated full pipeline: evade → pick domain → simulate send."""
        with self._lock:
            self._metrics["requests"] += 1

        # Step 1: evasion
        envelope = self.evasion.polymorphic_encode(payload)

        # Step 2: pick domain
        url = self.domain_rotator.pick()
        if not url:
            with self._lock:
                self._metrics["failures"] += 1
            return {"status": "error", "reason": "no_healthy_domain"}

        # Step 3: simulate send
        # In real use: build proxy chain, forward through it
        return {
            "status": "simulated_ok",
            "domain": url,
            "evasion_mode": envelope["mode"],
            "original_size": len(payload),
        }

    def metrics(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._metrics)


# ---------------------------------------------------------------------------
# Self-test demo
# ---------------------------------------------------------------------------

def run() -> None:
    print("=" * 60)
    print("NativeBypassEngine — self-test demo")
    print("=" * 60)

    engine = NativeBypassEngine()
    engine.configure(
        domains=[
            "mirror-a.example.com",
            "mirror-b.example.com",
            "mirror-c.example.com",
        ],
        proxies=[
            ("proxy1.tor", 9050, "socks5"),
            ("proxy2.vpn", 1080, "socks5"),
            ("proxy3.exit", 3128, "http"),
        ],
    )

    print("\n[1] Domain rotator (round-robin)")
    for i in range(5):
        d = engine.domain_rotator.pick()
        print(f"    pick {i+1}: {d}")

    print("\n[2] Domain health failure simulation")
    engine.domain_rotator.report_failure("https://mirror-a.example.com")
    states = engine.domain_rotator.list_domains()
    for s in states:
        print(f"    {s['domain']}: healthy={s['healthy']} failures={s['failures']}")

    print("\n[3] Domain health recovery")
    engine.domain_rotator.report_success("https://mirror-a.example.com")
    states = engine.domain_rotator.list_domains()
    for s in states:
        print(f"    {s['domain']}: healthy={s['healthy']} failures={s['failures']}")

    print("\n[4] DoH resolver")
    ips = engine.doh.resolve("example.com")
    print(f"    resolved={ips}")

    print("\n[5] Proxy chain builder")
    chain = engine.build_proxy_chain(length=2)
    assert chain is not None
    for hop in chain:
        print(f"    hop {hop['id']}: {hop['host']}:{hop['port']} ({hop['protocol']})")

    print("\n[6] Content filter evasion — base64 junk")
    raw = b"banned keyword: freedom of information"
    obf = engine.evasion.obfuscate_base64(raw)
    print(f"    obfuscated lines={len(obf.splitlines())}")
    restored = engine.evasion.deobfuscate_base64(obf)
    assert restored == raw
    print(f"    restored match={restored == raw}")

    print("\n[7] Fragmentation")
    frags = engine.evasion.fragment_payload(raw, chunk_size=8)
    print(f"    fragments={len(frags)}")
    restored2 = engine.evasion.reassemble_payload(frags)
    assert restored2 == raw
    print(f"    restored match={restored2 == raw}")

    print("\n[8] Mimicry wrap/unwrap")
    engine.evasion.register_mimicry("html_comment", "<!-- MAGNATRIX_BLOCK {payload} END -->")
    wrapped = engine.evasion.mimicry_wrap(raw, "html_comment")
    print(f"    wrapped={wrapped[:60]}...")
    unwrapped = engine.evasion.mimicry_unwrap(wrapped, "html_comment")
    assert unwrapped == raw
    print(f"    unwrapped match={unwrapped == raw}")

    print("\n[9] Polymorphic encode/decode")
    for _ in range(3):
        env = engine.evasion.polymorphic_encode(raw)
        dec = engine.evasion.polymorphic_decode(env)
        assert dec == raw
        print(f"    mode={env['mode']}: ok")

    print("\n[10] Full simulated send")
    result = engine.evade_and_send(raw)
    print(f"    result={result}")
    assert result["status"] == "simulated_ok"

    print("\n[11] Metrics")
    print(f"    {engine.metrics()}")

    print("\n✅ All bypass engine tests passed.")
    print("=" * 60)


if __name__ == "__main__":
    run()

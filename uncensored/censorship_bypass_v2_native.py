"""Censorship bypass engine with domain rotation, DoH, proxy chains, and obfuscation.

Pure stdlib implementation for evading network-level content filtering.
"""

import base64
import json
import random
import socket
import ssl
import string
import time
import urllib.request
from typing import Any, Dict, List, Optional, Tuple


class CensorshipBypass:
    """Engine for bypassing network censorship through multiple evasion techniques.

    Combines domain rotation, DNS-over-HTTPS, proxy chaining, payload
    obfuscation, fragmentation, mimicry, and content-filter evasion
    into a single configurable toolkit.

    Args:
        level: Bypass aggressiveness - ``'low'``, ``'medium'``, or ``'high'``.
        timeout: Socket timeout in seconds.
    """

    def __init__(self, level: str = 'medium', timeout: int = 10) -> None:
        self.level = level
        self.timeout = timeout
        self._domains: List[str] = []
        self._proxies: List[Tuple[str, int]] = []
        self._doh_endpoints: List[str] = [
            'https://cloudflare-dns.com/dns-query',
            'https://dns.google/resolve',
        ]
        self._user_agents: List[str] = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.0',
            'Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101',
        ]

    def add_domain(self, domain: str) -> None:
        """Add a domain to the rotation pool."""
        self._domains.append(domain)

    def add_proxy(self, host: str, port: int) -> None:
        """Add an HTTP proxy to the proxy chain."""
        self._proxies.append((host, port))

    def rotate_domain(self) -> Optional[str]:
        """Return a random domain from the rotation pool.

        Returns:
            A domain string, or ``None`` if the pool is empty.
        """
        if not self._domains:
            return None
        return random.choice(self._domains)

    def doh_resolve(self, hostname: str) -> List[str]:
        """Resolve a hostname using DNS-over-HTTPS (DoH).

        Queries multiple DoH endpoints until a successful response is
        received, then returns all A-record IP addresses.

        Args:
            hostname: The domain to resolve.

        Returns:
            A list of IPv4 addresses.
        """
        ips: List[str] = []
        for endpoint in self._doh_endpoints:
            try:
                url = f"{endpoint}?name={hostname}&type=A"
                req = urllib.request.Request(
                    url,
                    headers={
                        'Accept': 'application/dns-json',
                        'User-Agent': random.choice(self._user_agents),
                    },
                )
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    for answer in data.get('Answer', []):
                        if answer.get('type') == 1:
                            ips.append(answer['data'])
            except Exception:
                continue
            if ips:
                break
        return ips

    def obfuscate(self, data: bytes) -> bytes:
        """Obfuscate a payload with base64 plus junk insertion.

        Splits the base64-encoded data into chunks and inserts random
        junk strings as delimiters to evade simple pattern matching.

        Args:
            data: Raw payload bytes.

        Returns:
            Obfuscated byte string.
        """
        b64 = base64.b64encode(data).decode('ascii')
        junk = ''.join(random.choices(string.ascii_letters, k=random.randint(5, 15)))
        interval = max(1, len(b64) // random.randint(4, 8))
        chunks = [b64[i : i + interval] for i in range(0, len(b64), interval)]
        return f"{junk}|{'|'.join(chunks)}|{junk}".encode('ascii')

    def deobfuscate(self, data: bytes) -> bytes:
        """Reverse the obfuscation applied by :meth:`obfuscate`.

        Args:
            data: Obfuscated bytes.

        Returns:
            Original payload bytes.
        """
        text = data.decode('ascii')
        parts = text.split('|')[1:-1]
        return base64.b64decode(''.join(parts))

    def fragment_payload(self, data: bytes, chunks: int = 4) -> List[bytes]:
        """Split a payload into random-sized fragments.

        Fragments are shuffled so that reassembly requires correct
        ordering logic on the receiving end.

        Args:
            data: Payload to fragment.
            chunks: Target number of fragments.

        Returns:
            A list of payload fragments.
        """
        size = len(data) // chunks
        fragments: List[bytes] = []
        offset = 0
        for i in range(chunks - 1):
            end = offset + size + random.randint(-size // 4, size // 4)
            fragments.append(data[offset:end])
            offset = end
        fragments.append(data[offset:])
        random.shuffle(fragments)
        return fragments

    def mimic_http(self, payload: bytes, host: str = 'example.com') -> bytes:
        """Wrap arbitrary payload in an HTTP GET-like envelope.

        The real payload is base64-encoded inside a custom ``X-Session``
        header so that shallow inspection sees only a benign HTTP request.

        Args:
            payload: Raw bytes to wrap.
            host: Fake Host header value.

        Returns:
            HTTP-like byte string.
        """
        headers = (
            f"GET /{random.randint(1000, 9999)} HTTP/1.1\r\n"
            f"Host: {host}\r\n"
            f"User-Agent: {random.choice(self._user_agents)}\r\n"
            f"Accept: */*\r\n"
            f"X-Session: {base64.b64encode(payload).decode('ascii')}\r\n"
            f"\r\n"
        )
        return headers.encode('ascii')

    def evade_filter(self, text: str) -> str:
        """Apply content-filter evasion to plain text.

        Replaces a subset of ASCII characters with visually similar
        Unicode homoglyphs to evade keyword-based filters.

        Args:
            text: Original text string.

        Returns:
            Evasion-modified text string.
        """
        evasion_map: Dict[str, List[str]] = {
            'a': ['\u0430', '@', '4'],
            'e': ['\u0435', '3'],
            'o': ['\u043e', '0'],
            'i': ['\u0456', '1'],
            's': ['\u0455', '$', '5'],
        }
        result: List[str] = []
        for char in text:
            lower = char.lower()
            if lower in evasion_map and random.random() < 0.3:
                replacement = random.choice(evasion_map[lower])
                result.append(replacement if char.islower() else replacement.upper())
            else:
                result.append(char)
        return ''.join(result)

    def _connect_direct(self, host: str, port: int) -> ssl.SSLSocket:
        """Create a direct TLS connection to a host."""
        context = ssl.create_default_context()
        sock = socket.create_connection((host, port), timeout=self.timeout)
        return context.wrap_socket(sock, server_hostname=host)

    def _connect_proxied(self, host: str, port: int) -> ssl.SSLSocket:
        """Create a TLS connection through the proxy chain.

        Picks one proxy at random from the chain and tunnels through
        it with an HTTP CONNECT request.
        """
        if not self._proxies:
            return self._connect_direct(host, port)
        proxy_host, proxy_port = random.choice(self._proxies)
        sock = socket.create_connection(
            (proxy_host, proxy_port), timeout=self.timeout
        )
        connect_req = (
            f"CONNECT {host}:{port} HTTP/1.1\r\n"
            f"Host: {host}:{port}\r\n\r\n"
        )
        sock.sendall(connect_req.encode('ascii'))
        sock.recv(4096)  # consume proxy response
        context = ssl.create_default_context()
        return context.wrap_socket(sock, server_hostname=host)

    def run(self) -> Dict[str, Any]:
        """Execute a self-test demonstrating all bypass features.

        Returns:
            Dictionary mapping feature names to test results.
        """
        results: Dict[str, Any] = {}

        # 1. Domain rotation
        self.add_domain('cloudflare.com')
        self.add_domain('dns.google')
        self.add_domain('example.com')
        results['domain_rotation'] = self.rotate_domain()

        # 2. DoH resolution
        results['doh_resolve'] = self.doh_resolve('example.com')

        # 3. Proxy chain structure
        self.add_proxy('127.0.0.1', 8080)
        self.add_proxy('10.0.0.1', 3128)
        results['proxy_chain'] = len(self._proxies)

        # 4. Obfuscation round-trip
        original = b"Sensitive payload content"
        obf = self.obfuscate(original)
        deobf = self.deobfuscate(obf)
        results['obfuscation'] = {
            'original': original.decode(),
            'obfuscated_length': len(obf),
            'deobfuscated': deobf.decode(),
            'match': original == deobf,
        }

        # 5. Fragmentation
        frags = self.fragment_payload(original, chunks=5)
        results['fragmentation'] = {
            'fragment_count': len(frags),
            'total_reassembled_length': sum(len(f) for f in frags),
        }

        # 6. Mimicry
        mimic = self.mimic_http(original, host='cdn.example.net')
        results['mimicry'] = {
            'looks_like_http': b'HTTP/1.1' in mimic,
            'has_payload_header': b'X-Session:' in mimic,
        }

        # 7. Content filter evasion
        sample_text = 'sensitive access information'
        filtered = self.evade_filter(sample_text)
        results['filter_evasion'] = {
            'original': sample_text,
            'evaded': filtered,
            'modified': filtered != sample_text,
        }

        # 8. Configurable level
        results['bypass_level'] = self.level

        return results


if __name__ == '__main__':
    bypass = CensorshipBypass(level='high')
    print(json.dumps(bypass.run(), indent=2, ensure_ascii=False))

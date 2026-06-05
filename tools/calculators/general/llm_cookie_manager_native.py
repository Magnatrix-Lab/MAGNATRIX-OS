"""Cookie Manager — parse, store, expiry, security, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from enum import Enum, auto
import time

@dataclass
class Cookie:
    name: str
    value: str
    domain: str
    path: str
    expires: float
    secure: bool
    http_only: bool
    same_site: str

class CookieManager:
    def __init__(self):
        self.cookies: Dict[str, Cookie] = {}
        self.jar: List[Cookie] = []

    def parse(self, set_cookie_header: str, domain: str) -> Cookie:
        parts = [p.strip() for p in set_cookie_header.split(';')]
        name, value = parts[0].split('=', 1) if '=' in parts[0] else (parts[0], '')
        expires = 0.0
        path = '/'
        secure = False
        http_only = False
        same_site = 'Lax'
        for p in parts[1:]:
            if p.lower().startswith('expires='):
                expires = time.time() + 86400
            elif p.lower().startswith('max-age='):
                expires = time.time() + int(p.split('=', 1)[1])
            elif p.lower() == 'secure':
                secure = True
            elif p.lower() == 'httponly':
                http_only = True
            elif p.lower().startswith('path='):
                path = p.split('=', 1)[1]
            elif p.lower().startswith('samesite='):
                same_site = p.split('=', 1)[1]
        cookie = Cookie(name, value, domain, path, expires, secure, http_only, same_site)
        self.cookies[f"{domain}:{name}"] = cookie
        self.jar.append(cookie)
        return cookie

    def get_for_request(self, domain: str, path: str, secure: bool = False) -> List[Cookie]:
        now = time.time()
        result = []
        for cookie in self.jar:
            if cookie.domain == domain and path.startswith(cookie.path) and cookie.expires > now:
                if not cookie.secure or secure:
                    result.append(cookie)
        return result

    def clear_expired(self):
        now = time.time()
        self.jar = [c for c in self.jar if c.expires > now]
        self.cookies = {k: v for k, v in self.cookies.items() if v.expires > now}

    def to_header(self, cookies: List[Cookie]) -> str:
        return '; '.join(f"{c.name}={c.value}" for c in cookies)

    def stats(self) -> Dict:
        return {"cookies": len(self.jar), "domains": len(set(c.domain for c in self.jar))}

def run():
    cm = CookieManager()
    cm.parse("session=abc123; Path=/; HttpOnly; Secure", "example.com")
    cm.parse("pref=dark; Path=/; Max-Age=3600", "example.com")
    cookies = cm.get_for_request("example.com", "/api")
    print(cm.to_header(cookies))
    print(cm.stats())

if __name__ == "__main__":
    run()

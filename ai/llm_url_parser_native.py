"""LLM URL Parser — Native Python (stdlib only)."""
from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

@dataclass
class ParsedURL:
    scheme: str
    netloc: str
    path: str
    params: str
    query: Dict[str, List[str]]
    fragment: str
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None

class URLParser:
    def __init__(self) -> None:
        self._pattern = re.compile(r'^(?:(?P<scheme>[^:/?#]+):)?(?://(?P<netloc>[^/?#]*))?(?P<path>[^?#]*)(?:\?(?P<query>[^#]*))?(?:#(?P<fragment>.*))?$')

    def parse(self, url: str) -> ParsedURL:
        match = self._pattern.match(url)
        if not match:
            return ParsedURL("", "", "", "", {}, "")
        scheme = match.group("scheme") or ""
        netloc = match.group("netloc") or ""
        path = match.group("path") or ""
        query_str = match.group("query") or ""
        fragment = match.group("fragment") or ""
        query = self._parse_query(query_str)
        port = None
        username = None
        password = None
        if netloc:
            if "@" in netloc:
                auth, netloc = netloc.rsplit("@", 1)
                if ":" in auth:
                    username, password = auth.split(":", 1)
                else:
                    username = auth
            if ":" in netloc:
                host, port_str = netloc.rsplit(":", 1)
                if port_str.isdigit():
                    port = int(port_str)
                    netloc = host
        return ParsedURL(scheme, netloc, path, "", query, fragment, port, username, password)

    def _parse_query(self, query_str: str) -> Dict[str, List[str]]:
        result = {}
        for pair in query_str.split("&"):
            if not pair:
                continue
            if "=" in pair:
                key, value = pair.split("=", 1)
                key = key.replace("+", " ")
                value = value.replace("+", " ")
            else:
                key = pair
                value = ""
            if key not in result:
                result[key] = []
            result[key].append(value)
        return result

    def normalize(self, url: str) -> str:
        parsed = self.parse(url)
        path = parsed.path
        while "/../" in path:
            path = re.sub(r'/[^/]+/\.\./', '/', path)
        path = path.replace("/./", "/")
        query = "&".join(k + "=" + v[0] for k, vals in sorted(parsed.query.items()) for v in [vals])
        return parsed.scheme + "://" + parsed.netloc + path + ("?" + query if query else "")

    def get_stats(self, url: str) -> Dict[str, Any]:
        parsed = self.parse(url)
        return {"scheme": parsed.scheme, "has_query": bool(parsed.query), "has_fragment": bool(parsed.fragment), "path_depth": parsed.path.count("/")}

def run() -> None:
    print("URL Parser test")
    e = URLParser()
    urls = [
        "https://www.example.com/path/to/page?name=ferret&color=purple",
        "http://user:pass@host.com:8080/path",
        "ftp://files.example.com/download/file.txt#section1"
    ]
    for u in urls:
        parsed = e.parse(u)
        print("  " + parsed.scheme + " | " + parsed.netloc + " | " + parsed.path + " | " + str(parsed.query)[:40])
    print("  Stats: " + str(e.get_stats(urls[0])))
    print("URL Parser test complete.")

if __name__ == "__main__":
    run()

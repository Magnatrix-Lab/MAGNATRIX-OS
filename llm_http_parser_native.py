"""HTTP Parser — request/response parsing, headers, native, stdlib only."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum, auto
import re

@dataclass
class HTTPRequest:
    method: str
    path: str
    version: str
    headers: Dict[str, str]
    body: str

@dataclass
class HTTPResponse:
    status_code: int
    status_text: str
    version: str
    headers: Dict[str, str]
    body: str

class HTTPParser:
    def __init__(self):
        self.requests: List[HTTPRequest] = []
        self.responses: List[HTTPResponse] = []

    def parse_request(self, raw: str) -> HTTPRequest:
        lines = raw.split('\n')
        if not lines:
            lines = raw.split('\n')
        first = lines[0].split()
        method = first[0] if len(first) > 0 else 'GET'
        path = first[1] if len(first) > 1 else '/'
        version = first[2] if len(first) > 2 else 'HTTP/1.1'
        headers = {}
        body = ''
        i = 1
        while i < len(lines) and lines[i]:
            key, val = lines[i].split(':', 1)
            headers[key.strip()] = val.strip()
            i += 1
        if i + 1 < len(lines):
            body = '\n'.join(lines[i+1:])
        req = HTTPRequest(method, path, version, headers, body)
        self.requests.append(req)
        return req

    def parse_response(self, raw: str) -> HTTPResponse:
        lines = raw.split('\n')
        if not lines:
            lines = raw.split('\n')
        first = lines[0].split()
        version = first[0] if len(first) > 0 else 'HTTP/1.1'
        status = int(first[1]) if len(first) > 1 else 200
        status_text = ' '.join(first[2:]) if len(first) > 2 else 'OK'
        headers = {}
        body = ''
        i = 1
        while i < len(lines) and lines[i]:
            key, val = lines[i].split(':', 1)
            headers[key.strip()] = val.strip()
            i += 1
        if i + 1 < len(lines):
            body = '\n'.join(lines[i+1:])
        resp = HTTPResponse(status, status_text, version, headers, body)
        self.responses.append(resp)
        return resp

    def build_request(self, req: HTTPRequest) -> str:
        lines = [f"{req.method} {req.path} {req.version}"]
        for k, v in req.headers.items():
            lines.append(f"{k}: {v}")
        lines.append('')
        lines.append(req.body)
        return '\n'.join(lines)

    def build_response(self, resp: HTTPResponse) -> str:
        lines = [f"{resp.version} {resp.status_code} {resp.status_text}"]
        for k, v in resp.headers.items():
            lines.append(f"{k}: {v}")
        lines.append('')
        lines.append(resp.body)
        return '\n'.join(lines)

    def stats(self) -> Dict:
        return {"requests": len(self.requests), "responses": len(self.responses)}

def run():
    parser = HTTPParser()
    req = parser.parse_request("GET /api/users HTTP/1.1\nHost: example.com\nAccept: application/json\n\n")
    print(req.method, req.path)
    resp = parser.parse_response("HTTP/1.1 200 OK\nContent-Type: application/json\n\n{\"data\": []}")
    print(resp.status_code)
    print(parser.stats())

if __name__ == "__main__":
    run()

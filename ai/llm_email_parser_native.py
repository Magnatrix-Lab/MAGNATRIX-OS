"""LLM Email Parser — Native Python (stdlib only)."""
from __future__ import annotations
import re, base64, quopri
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto
from datetime import datetime

@dataclass
class EmailAddress:
    name: str
    address: str

@dataclass
class EmailAttachment:
    filename: str
    content_type: str
    content: str
    encoding: str = "base64"

@dataclass
class ParsedEmail:
    message_id: str
    subject: str
    from_addr: EmailAddress
    to_addrs: List[EmailAddress]
    cc_addrs: List[EmailAddress]
    date: str
    body_text: str
    body_html: str
    attachments: List[EmailAttachment]
    headers: Dict[str, str] = field(default_factory=dict)

class EmailParser:
    def __init__(self) -> None:
        pass

    def parse(self, raw_email: str) -> ParsedEmail:
        headers, body = self._split_headers_body(raw_email)
        header_dict = self._parse_headers(headers)
        from_addr = self._parse_address(header_dict.get("From", ""))
        to_addrs = self._parse_address_list(header_dict.get("To", ""))
        cc_addrs = self._parse_address_list(header_dict.get("Cc", ""))
        body_text, body_html, attachments = self._parse_body(body, header_dict)
        return ParsedEmail(
            message_id=header_dict.get("Message-ID", ""),
            subject=header_dict.get("Subject", ""),
            from_addr=from_addr,
            to_addrs=to_addrs,
            cc_addrs=cc_addrs,
            date=header_dict.get("Date", ""),
            body_text=body_text,
            body_html=body_html,
            attachments=attachments,
            headers=header_dict
        )

    def _split_headers_body(self, raw: str) -> tuple:
        if "\n\n" in raw:
            parts = raw.split("\n\n", 1)
            return parts[0], parts[1]
        elif "\r\n\r\n" in raw:
            parts = raw.split("\r\n\r\n", 1)
            return parts[0], parts[1]
        return raw, ""

    def _parse_headers(self, headers: str) -> Dict[str, str]:
        result = {}
        current_key = None
        for line in headers.splitlines():
            if line.startswith(" ") or line.startswith("\t"):
                if current_key:
                    result[current_key] += " " + line.strip()
            elif ":" in line:
                key, value = line.split(":", 1)
                current_key = key.strip()
                result[current_key] = value.strip()
        return result

    def _parse_address(self, addr_str: str) -> EmailAddress:
        match = re.match(r'"?([^"]*)"?\s*<([^>]+)>', addr_str)
        if match:
            return EmailAddress(match.group(1).strip(), match.group(2).strip())
        return EmailAddress("", addr_str.strip())

    def _parse_address_list(self, addr_str: str) -> List[EmailAddress]:
        if not addr_str:
            return []
        addrs = re.split(r',\s*(?=[^<]*<|$)', addr_str)
        return [self._parse_address(a) for a in addrs if a.strip()]

    def _parse_body(self, body: str, headers: Dict[str, str]) -> tuple:
        content_type = headers.get("Content-Type", "text/plain")
        if "multipart" in content_type.lower():
            return self._parse_multipart(body, content_type)
        transfer_encoding = headers.get("Content-Transfer-Encoding", "").lower()
        decoded = self._decode_body(body, transfer_encoding)
        if "text/html" in content_type.lower():
            return "", decoded, []
        return decoded, "", []

    def _parse_multipart(self, body: str, content_type: str) -> tuple:
        boundary_match = re.search(r'boundary="?([^";\s]+)"?', content_type)
        boundary = boundary_match.group(1) if boundary_match else ""
        if not boundary:
            return body, "", []
        parts = body.split("--" + boundary)
        text_parts = []
        html_parts = []
        attachments = []
        for part in parts:
            if not part.strip() or part.strip() == "--":
                continue
            part_headers, part_body = self._split_headers_body(part.strip())
            part_header_dict = self._parse_headers(part_headers)
            part_type = part_header_dict.get("Content-Type", "text/plain")
            encoding = part_header_dict.get("Content-Transfer-Encoding", "").lower()
            decoded = self._decode_body(part_body.strip(), encoding)
            if "text/plain" in part_type.lower() and "name" not in part_type.lower():
                text_parts.append(decoded)
            elif "text/html" in part_type.lower():
                html_parts.append(decoded)
            elif "name" in part_type.lower() or "attachment" in part_header_dict.get("Content-Disposition", "").lower():
                filename_match = re.search(r'filename="?([^";\s]+)"?', part_type + " " + part_header_dict.get("Content-Disposition", ""))
                filename = filename_match.group(1) if filename_match else "unknown"
                attachments.append(EmailAttachment(filename, part_type, decoded, encoding))
        return "\n".join(text_parts), "\n".join(html_parts), attachments

    def _decode_body(self, body: str, encoding: str) -> str:
        if encoding == "base64":
            try:
                return base64.b64decode(body).decode("utf-8", errors="ignore")
            except Exception:
                return body
        elif encoding == "quoted-printable":
            try:
                return quopri.decodestring(body.encode()).decode("utf-8", errors="ignore")
            except Exception:
                return body
        return body

    def get_stats(self, email: ParsedEmail) -> Dict[str, Any]:
        return {"attachments": len(email.attachments), "recipients": len(email.to_addrs) + len(email.cc_addrs), "has_html": bool(email.body_html)}

def run() -> None:
    print("Email Parser test")
    e = EmailParser()
    raw = """From: sender@example.com
To: recipient@example.com
Subject: Test Email
Date: Mon, 1 Jan 2024 00:00:00 +0000
Message-ID: <12345@example.com>
Content-Type: text/plain

Hello World
This is a test email.
"""
    parsed = e.parse(raw)
    print("  Subject: " + parsed.subject)
    print("  From: " + parsed.from_addr.address)
    print("  Body: " + parsed.body_text[:50])
    print("  Stats: " + str(e.get_stats(parsed)))
    print("Email Parser test complete.")

if __name__ == "__main__":
    run()

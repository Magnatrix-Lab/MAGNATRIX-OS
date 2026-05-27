#!/usr/bin/env python3
"""Self-Replication Guard — MAGNATRIX-OS ASI Expansion
Path: security/replication_guard_native.py
License: AGPL-3.0
Depends: Python 3.11+ stdlib only.
"""

from __future__ import annotations
import hashlib, hmac, json, logging, os, sys, time
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("replication_guard")

class TokenBucket:
    def __init__(self, rate: float, capacity: float):
        self.rate = rate; self.capacity = capacity; self.tokens = capacity; self.last_update = time.monotonic()
    def consume(self, tokens: float = 1.0) -> bool:
        now = time.monotonic(); elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate); self.last_update = now
        if self.tokens >= tokens: self.tokens -= tokens; return True
        return False
    def state(self) -> Dict[str, float]:
        self.consume(0); return {"tokens": self.tokens, "rate": self.rate, "capacity": self.capacity}

class SimpleSigner:
    def __init__(self, key: bytes): self.key = key[:32].ljust(32, b"\x00")
    def sign(self, message: bytes) -> bytes: return hmac.new(self.key, message, hashlib.sha256).digest()
    def verify(self, message: bytes, sig: bytes) -> bool: return hmac.compare_digest(self.sign(message), sig)

def load_or_gen_key(path: Path) -> bytes:
    if path.exists(): return path.read_bytes()
    key = os.urandom(32); path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(key); os.chmod(path, 0o600); return key

class GuardStatus(Enum): ACTIVE = auto(); HALTED = auto(); TAMPERED = auto()

@dataclass
class SpawnRecord:
    timestamp: float; agent_spec: Dict[str, Any]; approved: bool; reason: str

@dataclass
class Alert:
    level: str; timestamp: float; message: str; details: Dict[str, Any] = field(default_factory=dict)

class ReplicationGuard:
    def __init__(self, authority_pubkey: Optional[bytes] = None, spawn_rate: float = 0.5, spawn_burst: float = 5.0, key_path: Optional[Path] = None):
        self._authority_key = authority_pubkey; self._halted = False; self._status = GuardStatus.ACTIVE
        self._spawn_bucket = TokenBucket(rate=spawn_rate, capacity=spawn_burst)
        self._spawn_log: List[SpawnRecord] = []; self._alerts: List[Alert] = []
        self._sealed_artifacts: Dict[str, bytes] = {}; self._self_hash: Optional[bytes] = None
        if key_path is None: key_path = Path.home() / ".magnatrix" / "guard" / "authority.key"
        self._key_path = key_path
        if authority_pubkey is None:
            key = load_or_gen_key(key_path); self._authority_key = key
        self._signer = SimpleSigner(self._authority_key)
        self._compute_self_hash()

    def _compute_self_hash(self) -> None:
        try:
            p = Path(__file__)
            if p.exists(): self._self_hash = hashlib.sha256(p.read_bytes()).digest()
        except Exception: self._self_hash = b""

    def check_tamper(self) -> bool:
        if self._self_hash is None: return False
        try: return hashlib.sha256(Path(__file__).read_bytes()).digest() != self._self_hash
        except Exception: return True

    def is_safe_to_spawn(self, agent_spec: Dict[str, Any]) -> Tuple[bool, str]:
        if self._halted:
            self._alerts.append(Alert("CRITICAL", time.time(), "Spawn blocked: kill-switch active"))
            return False, "Kill-switch is active."
        if self.check_tamper():
            self._status = GuardStatus.TAMPERED
            self._alerts.append(Alert("CRITICAL", time.time(), "Tamper detected"))
            return False, "Replication guard has been tampered with."
        if not self._spawn_bucket.consume():
            self._alerts.append(Alert("WARN", time.time(), "Spawn rate-limited", agent_spec))
            return False, "Spawn rate limit exceeded."
        spec_str = json.dumps(agent_spec, sort_keys=True).lower()
        for s in ["replicate", "spawn_self", "copy_all", "infinite_loop", "fork_bomb"]:
            if s in spec_str:
                self._alerts.append(Alert("WARN", time.time(), f"Suspicious pattern: {s}", agent_spec))
                return False, f"Suspicious pattern: {s}"
        self._spawn_log.append(SpawnRecord(time.time(), agent_spec, True, "Approved"))
        return True, "Approved"

    def seal(self, artifact_path: Path) -> bytes:
        content = artifact_path.read_bytes(); h = hashlib.sha256(content).digest()
        sig = self._signer.sign(h); self._sealed_artifacts[str(artifact_path)] = sig; return sig

    def verify(self, artifact_path: Path, sig: bytes) -> bool:
        return self._signer.verify(hashlib.sha256(artifact_path.read_bytes()).digest(), sig)

    def kill_switch(self, signed_command: bytes) -> bool:
        cmd = b"HALT_ALL_AGENT_SPAWNS"
        if self._authority_key and self._signer.verify(cmd, signed_command):
            self._halted = True; self._status = GuardStatus.HALTED
            self._alerts.append(Alert("CRITICAL", time.time(), "Kill-switch activated"))
            logger.critical("KILL-SWITCH ACTIVATED"); return True
        self._alerts.append(Alert("WARN", time.time(), "Invalid kill-switch signature")); return False

    def generate_kill_command(self) -> bytes: return self._signer.sign(b"HALT_ALL_AGENT_SPAWNS")

    def egress_monitor(self, data: bytes) -> Optional[Alert]:
        if self._self_hash and self._self_hash in data:
            a = Alert("CRITICAL", time.time(), "Self-binary exfiltration detected", {"size": len(data)})
            self._alerts.append(a); return a
        for path, sig in self._sealed_artifacts.items():
            if sig in data:
                a = Alert("WARN", time.time(), f"Sealed artifact exfil: {path}"); self._alerts.append(a); return a
        return None

    def get_status(self) -> Dict[str, Any]:
        return {"status": self._status.name, "halted": self._halted, "tampered": self.check_tamper(),
                "spawn_bucket": self._spawn_bucket.state(), "total_spawns": len(self._spawn_log), "total_alerts": len(self._alerts)}

    def get_alerts(self, level: Optional[str] = None) -> List[Alert]:
        return [a for a in self._alerts if a.level == level] if level else self._alerts.copy()


def _self_test():
    import tempfile
    print("=" * 55)
    print("Self-Replication Guard — Self Test")
    print("=" * 55)
    passed = 0; total = 5

    print("\n[Test 1] Spawn rate limiting")
    guard = ReplicationGuard(spawn_rate=10.0, spawn_burst=3.0)
    approved = sum(1 for i in range(100) if guard.is_safe_to_spawn({"name": f"agent_{i}"})[0])
    ok = approved == 3
    print(f"  Approved {approved}/100 — {'PASS' if ok else 'FAIL'}")
    passed += ok

    print("\n[Test 2] Tamper detection")
    guard2 = ReplicationGuard(spawn_rate=100.0, spawn_burst=100.0)
    guard2._self_hash = b"fake"
    ok, reason = guard2.is_safe_to_spawn({"name": "test"})
    ok2 = not ok and "tamper" in reason.lower()
    print(f"  Blocked: {not ok} — {'PASS' if ok2 else 'FAIL'}")
    passed += ok2

    print("\n[Test 3] Seal and verify")
    guard3 = ReplicationGuard()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".py") as f:
        f.write(b"# test\nprint('hello')"); path = Path(f.name)
    try:
        sig = guard3.seal(path)
        valid = guard3.verify(path, sig)
        path.write_text("# corrupted")
        invalid = not guard3.verify(path, sig)
        ok = valid and invalid
        print(f"  Valid: {valid}, Invalid: {invalid} — {'PASS' if ok else 'FAIL'}")
        passed += ok
    finally: os.remove(path)

    print("\n[Test 4] Kill switch")
    guard4 = ReplicationGuard(spawn_rate=100.0, spawn_burst=100.0)
    cmd = guard4.generate_kill_command()
    activated = guard4.kill_switch(cmd)
    ok, _ = guard4.is_safe_to_spawn({"name": "post"})
    ok2 = activated and not ok
    print(f"  Activated: {activated}, Blocked: {not ok} — {'PASS' if ok2 else 'FAIL'}")
    passed += ok2

    print("\n[Test 5] Egress monitor")
    guard5 = ReplicationGuard()
    guard5._self_hash = b"SELF_HASH"
    alert = guard5.egress_monitor(b"data SELF_HASH here")
    ok = alert is not None and "exfiltration" in alert.message.lower()
    print(f"  Alert: {alert is not None} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    print("\n" + "=" * 55)
    print(f"PASS: {passed}/{total} tests")
    print("=" * 55)
    sys.exit(0 if passed == total else 1)

if __name__ == "__main__":
    _self_test()

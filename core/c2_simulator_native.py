"""
c2_simulator_native.py
MAGNATRIX-OS — C2 Simulator

Inspired by AbyssSec red team operations and C2 research:
Simulate command and control communication patterns for testing. Pure stdlib.
"""

import json
import random
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class C2Session:
    session_id: str
    implant_id: str
    protocol: str
    status: str = "active"  # active, dormant, dead
    beacon_interval: int = 60
    last_beacon: str = ""
    commands: List[Dict[str, Any]] = field(default_factory=list)
    responses: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        if not self.last_beacon:
            self.last_beacon = datetime.now().isoformat()


class C2Simulator:
    """Simulate command and control communication patterns."""

    PROTOCOLS = ["http", "https", "dns", "tcp", "icmp", "websocket"]

    def __init__(self, c2_dir: str = "./c2_simulator"):
        self.c2_dir = Path(c2_dir)
        self.c2_dir.mkdir(exist_ok=True)
        self.sessions: Dict[str, C2Session] = {}
        self._load()

    def _load(self) -> None:
        file = self.c2_dir / "sessions.json"
        if file.exists():
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for sid, sd in data.items():
                        self.sessions[sid] = C2Session(**sd)
            except Exception:
                pass

    def _save(self) -> None:
        with open(self.c2_dir / "sessions.json", "w", encoding="utf-8") as f:
            json.dump({sid: asdict(s) for sid, s in self.sessions.items()}, f, indent=2)

    def create_session(self, session_id: str, implant_id: str, protocol: str = "https",
                       beacon_interval: int = 60) -> C2Session:
        session = C2Session(
            session_id=session_id, implant_id=implant_id, protocol=protocol,
            beacon_interval=beacon_interval,
        )
        self.sessions[session_id] = session
        self._save()
        return session

    def send_command(self, session_id: str, command_id: str, command_type: str, payload: str) -> bool:
        session = self.sessions.get(session_id)
        if not session or session.status != "active":
            return False
        session.commands.append({
            "command_id": command_id, "type": command_type, "payload": payload,
            "sent_at": datetime.now().isoformat(), "acknowledged": False,
        })
        self._save()
        return True

    def receive_response(self, session_id: str, command_id: str, output: str) -> bool:
        session = self.sessions.get(session_id)
        if not session:
            return False
        session.responses.append({
            "command_id": command_id, "output": output,
            "received_at": datetime.now().isoformat(),
        })
        for cmd in session.commands:
            if cmd["command_id"] == command_id:
                cmd["acknowledged"] = True
        self._save()
        return True

    def beacon(self, session_id: str) -> bool:
        session = self.sessions.get(session_id)
        if not session:
            return False
        session.last_beacon = datetime.now().isoformat()
        self._save()
        return True

    def kill_session(self, session_id: str) -> bool:
        session = self.sessions.get(session_id)
        if not session:
            return False
        session.status = "dead"
        self._save()
        return True

    def sleep_obfuscate(self, session_id: str, duration: int) -> bool:
        """Simulate sleep obfuscation technique."""
        session = self.sessions.get(session_id)
        if not session:
            return False
        session.status = "dormant"
        session.beacon_interval = duration
        self._save()
        return True

    def get_session(self, session_id: str) -> Optional[C2Session]:
        return self.sessions.get(session_id)

    def list_sessions(self, status: Optional[str] = None) -> List[C2Session]:
        if status:
            return [s for s in self.sessions.values() if s.status == status]
        return list(self.sessions.values())

    def get_stats(self) -> Dict[str, Any]:
        total = len(self.sessions)
        active = sum(1 for s in self.sessions.values() if s.status == "active")
        dormant = sum(1 for s in self.sessions.values() if s.status == "dormant")
        dead = sum(1 for s in self.sessions.values() if s.status == "dead")
        total_cmds = sum(len(s.commands) for s in self.sessions.values())
        return {"sessions": total, "active": active, "dormant": dormant, "dead": dead, "commands_sent": total_cmds}

    def to_dict(self) -> Dict[str, Any]:
        return self.get_stats()


__all__ = ["C2Simulator", "C2Session"]
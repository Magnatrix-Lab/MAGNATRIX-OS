"""LLM Presence Tracker — Native Python (stdlib only)."""
from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto

class PresenceStatus(Enum):
    ONLINE = auto()
    AWAY = auto()
    BUSY = auto()
    OFFLINE = auto()
    INVISIBLE = auto()

@dataclass
class Presence:
    user_id: str
    status: PresenceStatus
    last_seen: float
    activity: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

class PresenceTracker:
    def __init__(self, timeout: float = 300.0) -> None:
        self.timeout = timeout
        self._presences: Dict[str, Presence] = {}

    def update(self, user_id: str, status: PresenceStatus, activity: str = "") -> None:
        self._presences[user_id] = Presence(user_id, status, time.time(), activity)

    def heartbeat(self, user_id: str) -> None:
        if user_id in self._presences:
            self._presences[user_id].last_seen = time.time()

    def get_status(self, user_id: str) -> Optional[Presence]:
        presence = self._presences.get(user_id)
        if presence and time.time() - presence.last_seen > self.timeout and presence.status != PresenceStatus.OFFLINE:
            presence.status = PresenceStatus.OFFLINE
        return presence

    def get_online(self) -> List[str]:
        return [uid for uid, p in self._presences.items() if p.status == PresenceStatus.ONLINE]

    def get_away(self) -> List[str]:
        return [uid for uid, p in self._presences.items() if p.status == PresenceStatus.AWAY]

    def get_all(self) -> Dict[str, PresenceStatus]:
        return {uid: p.status for uid, p in self._presences.items()}

    def is_online(self, user_id: str) -> bool:
        p = self.get_status(user_id)
        return p.status == PresenceStatus.ONLINE if p else False

    def get_stats(self) -> Dict[str, Any]:
        counts = {}
        for p in self._presences.values():
            counts[p.status.name] = counts.get(p.status.name, 0) + 1
        return {"total": len(self._presences), "by_status": counts, "online": len(self.get_online())}

def run() -> None:
    print("Presence Tracker test")
    e = PresenceTracker()
    e.update("alice", PresenceStatus.ONLINE, "Coding")
    e.update("bob", PresenceStatus.BUSY, "In meeting")
    e.update("charlie", PresenceStatus.AWAY)
    e.update("dave", PresenceStatus.OFFLINE)
    e.heartbeat("alice")
    print("  Online: " + str(e.get_online()))
    print("  Away: " + str(e.get_away()))
    print("  Alice online: " + str(e.is_online("alice")))
    print("  Stats: " + str(e.get_stats()))
    print("Presence Tracker test complete.")

if __name__ == "__main__":
    run()

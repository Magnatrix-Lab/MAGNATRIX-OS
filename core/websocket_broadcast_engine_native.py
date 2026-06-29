"""WebSocket Broadcast Engine — Fan-out, room-based, ordering."""
from dataclasses import dataclass
from pathlib import Path
import json, time

@dataclass
class BroadcastMessage:
    msg_id: str = ""
    room_id: str = ""
    payload: str = ""
    timestamp: float = 0.0
    seq_num: int = 0

class WebSocketBroadcastEngine:
    def __init__(self, root: str = "."):
        self.root = Path(root)
        self._rooms: dict[str, list[str]] = {}
        self._messages: list[BroadcastMessage] = []
        self._seq_counters: dict[str, int] = {}
        self._persist_path = self.root / "websocket_broadcast.json"
        self._load()

    def _load(self) -> None:
        if self._persist_path.exists():
            data = json.loads(self._persist_path.read_text())
            self._rooms = data.get("rooms", {})
            self._messages = [BroadcastMessage(**m) for m in data.get("messages", [])]
            self._seq_counters = data.get("seq_counters", {})

    def _save(self) -> None:
        self._persist_path.write_text(json.dumps({
            "rooms": self._rooms,
            "messages": [m.__dict__ for m in self._messages],
            "seq_counters": self._seq_counters
        }, indent=2))

    def join_room(self, room_id: str, conn_id: str) -> None:
        if room_id not in self._rooms:
            self._rooms[room_id] = []
        if conn_id not in self._rooms[room_id]:
            self._rooms[room_id].append(conn_id)
        self._save()

    def leave_room(self, room_id: str, conn_id: str) -> None:
        if room_id in self._rooms and conn_id in self._rooms[room_id]:
            self._rooms[room_id].remove(conn_id)
        self._save()

    def broadcast(self, room_id: str, payload: str) -> list[str]:
        recipients = list(self._rooms.get(room_id, []))
        seq = self._seq_counters.get(room_id, 0) + 1
        self._seq_counters[room_id] = seq
        msg = BroadcastMessage(msg_id=f"{room_id}_{seq}", room_id=room_id, payload=payload, timestamp=time.time(), seq_num=seq)
        self._messages.append(msg)
        self._save()
        return recipients

    def broadcast_all(self, payload: str) -> list[str]:
        all_recipients = []
        for room_id in self._rooms:
            recipients = self.broadcast(room_id, payload)
            all_recipients.extend(recipients)
        return list(set(all_recipients))

    def get_room_members(self, room_id: str) -> list[str]:
        return self._rooms.get(room_id, [])

    def get_room_history(self, room_id: str, limit: int = 100) -> list[BroadcastMessage]:
        return [m for m in self._messages if m.room_id == room_id][-limit:]

    def to_dict(self) -> dict:
        return {"room_count": len(self._rooms), "message_count": len(self._messages)}

    def get_stats(self) -> dict:
        by_room = {room: len(members) for room, members in self._rooms.items()}
        return {"rooms": len(self._rooms), "messages": len(self._messages), "members_by_room": by_room}

__all__ = ["WebSocketBroadcastEngine", "BroadcastMessage"]

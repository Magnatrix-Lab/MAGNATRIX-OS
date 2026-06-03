"""LLM Chat Manager — Native Python (stdlib only)."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum, auto
from datetime import datetime

class ChatRole(Enum):
    USER = auto()
    ASSISTANT = auto()
    SYSTEM = auto()
    OBSERVER = auto()

@dataclass
class ChatMessage:
    id: str
    chat_id: str
    role: ChatRole
    content: str
    timestamp: str
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ChatRoom:
    id: str
    name: str
    participants: List[str] = field(default_factory=list)
    messages: List[ChatMessage] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

class ChatManager:
    def __init__(self) -> None:
        self._rooms: Dict[str, ChatRoom] = {}

    def create_room(self, room_id: str, name: str) -> ChatRoom:
        room = ChatRoom(id=room_id, name=name)
        self._rooms[room_id] = room
        return room

    def join_room(self, room_id: str, user_id: str) -> bool:
        room = self._rooms.get(room_id)
        if room and user_id not in room.participants:
            room.participants.append(user_id)
            return True
        return False

    def leave_room(self, room_id: str, user_id: str) -> bool:
        room = self._rooms.get(room_id)
        if room and user_id in room.participants:
            room.participants.remove(user_id)
            return True
        return False

    def send_message(self, message: ChatMessage) -> None:
        room = self._rooms.get(message.chat_id)
        if room:
            room.messages.append(message)

    def get_history(self, room_id: str, limit: int = 100) -> List[ChatMessage]:
        room = self._rooms.get(room_id)
        if room:
            return room.messages[-limit:]
        return []

    def get_room_stats(self, room_id: str) -> Dict[str, Any]:
        room = self._rooms.get(room_id)
        if not room:
            return {}
        return {"name": room.name, "participants": len(room.participants), "messages": len(room.messages)}

    def get_stats(self) -> Dict[str, Any]:
        return {"rooms": len(self._rooms), "total_messages": sum(len(r.messages) for r in self._rooms.values()), "total_participants": sum(len(r.participants) for r in self._rooms.values())}

def run() -> None:
    print("Chat Manager test")
    e = ChatManager()
    e.create_room("r1", "General")
    e.join_room("r1", "alice")
    e.join_room("r1", "bob")
    e.send_message(ChatMessage("m1", "r1", ChatRole.USER, "Hello everyone", datetime.now().isoformat()))
    e.send_message(ChatMessage("m2", "r1", ChatRole.ASSISTANT, "Hi there!", datetime.now().isoformat()))
    e.send_message(ChatMessage("m3", "r1", ChatRole.USER, "How are you?", datetime.now().isoformat()))
    print("  History: " + str(len(e.get_history("r1"))))
    print("  Room stats: " + str(e.get_room_stats("r1")))
    print("  Stats: " + str(e.get_stats()))
    print("Chat Manager test complete.")

if __name__ == "__main__":
    run()

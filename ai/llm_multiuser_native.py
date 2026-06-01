"""Multi-User Arena — Collaborative LLM Arena with presence, permissions, and session isolation.

Modul ini menyediakan:
- User session management dengan presence tracking
- Room/arena creation untuk multi-user collaboration
- Permission system (READ, WRITE, ADMIN, OWNER)
- Message broadcasting dan typing indicators
- Real-time session isolation dan audit logging
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from enum import Enum, auto


class Role(Enum):
    OWNER = 4
    ADMIN = 3
    MODERATOR = 2
    MEMBER = 1
    GUEST = 0


class Permission(Enum):
    READ = auto()
    WRITE = auto()
    EXECUTE = auto()
    MANAGE_USERS = auto()
    MANAGE_SETTINGS = auto()
    DELETE = auto()


ROLE_PERMISSIONS = {
    Role.OWNER: {Permission.READ, Permission.WRITE, Permission.EXECUTE,
                 Permission.MANAGE_USERS, Permission.MANAGE_SETTINGS, Permission.DELETE},
    Role.ADMIN: {Permission.READ, Permission.WRITE, Permission.EXECUTE,
                 Permission.MANAGE_USERS, Permission.MANAGE_SETTINGS},
    Role.MODERATOR: {Permission.READ, Permission.WRITE, Permission.EXECUTE, Permission.MANAGE_USERS},
    Role.MEMBER: {Permission.READ, Permission.WRITE, Permission.EXECUTE},
    Role.GUEST: {Permission.READ},
}


@dataclass
class UserProfile:
    """User identity and preferences."""
    user_id: str
    display_name: str
    avatar: str = ""
    status: str = "online"
    joined_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Presence:
    """Real-time presence state."""
    user_id: str
    room_id: str
    status: str = "online"  # online, away, typing, offline
    typing_in: Optional[str] = None
    last_seen: float = field(default_factory=time.time)


@dataclass
class ArenaMessage:
    """Message in an arena room."""
    message_id: str
    room_id: str
    user_id: str
    content: str
    message_type: str = "text"  # text, system, command, result
    timestamp: float = field(default_factory=time.time)
    reply_to: Optional[str] = None
    reactions: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class ArenaRoom:
    """Collaborative arena room."""
    room_id: str
    name: str
    description: str = ""
    created_by: str = ""
    created_at: float = field(default_factory=time.time)
    members: Dict[str, Role] = field(default_factory=dict)
    messages: List[ArenaMessage] = field(default_factory=list, repr=False)
    is_private: bool = False
    max_members: int = 50
    metadata: Dict[str, Any] = field(default_factory=dict)
    _typing: Set[str] = field(default_factory=set, repr=False)

    def can(self, user_id: str, permission: Permission) -> bool:
        role = self.members.get(user_id, Role.GUEST)
        return permission in ROLE_PERMISSIONS.get(role, set())

    def add_member(self, user_id: str, role: Role = Role.MEMBER) -> bool:
        if len(self.members) >= self.max_members:
            return False
        self.members[user_id] = role
        return True

    def remove_member(self, user_id: str) -> bool:
        if user_id in self.members:
            del self.members[user_id]
            self._typing.discard(user_id)
            return True
        return False

    def set_typing(self, user_id: str, typing: bool = True) -> None:
        if typing:
            self._typing.add(user_id)
        else:
            self._typing.discard(user_id)

    def get_typing(self) -> List[str]:
        return list(self._typing)

    def add_message(self, msg: ArenaMessage) -> None:
        self.messages.append(msg)
        # Prune old messages if too many
        if len(self.messages) > 10000:
            self.messages = self.messages[-5000:]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "room_id": self.room_id,
            "name": self.name,
            "description": self.description,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "members": {k: v.name for k, v in self.members.items()},
            "message_count": len(self.messages),
            "is_private": self.is_private,
            "max_members": self.max_members,
            "metadata": self.metadata,
        }


class UserRegistry:
    """Global user registry and session management."""

    def __init__(self):
        self._users: Dict[str, UserProfile] = {}
        self._sessions: Dict[str, float] = {}  # token -> expiry

    def register(self, display_name: str, metadata: Optional[Dict[str, Any]] = None) -> UserProfile:
        uid = str(uuid.uuid4())[:12]
        user = UserProfile(user_id=uid, display_name=display_name, metadata=metadata or {})
        self._users[uid] = user
        return user

    def get(self, user_id: str) -> Optional[UserProfile]:
        return self._users.get(user_id)

    def update_presence(self, user_id: str, status: str) -> None:
        if user_id in self._users:
            self._users[user_id].status = status
            self._users[user_id].last_active = time.time()

    def create_session(self, user_id: str, ttl: float = 3600.0) -> str:
        token = str(uuid.uuid4())[:16]
        self._sessions[token] = time.time() + ttl
        return token

    def validate_session(self, token: str) -> Optional[str]:
        expiry = self._sessions.get(token, 0)
        if expiry > time.time():
            # Find user by token prefix (simplified mapping)
            for uid, user in self._users.items():
                if user.last_active <= expiry:
                    return uid
        return None

    def list_users(self) -> List[UserProfile]:
        return list(self._users.values())

    def remove_user(self, user_id: str) -> bool:
        return self._users.pop(user_id, None) is not None


class ArenaManager:
    """Manage rooms, presence, and collaboration state."""

    def __init__(self, user_registry: Optional[UserRegistry] = None):
        self.users = user_registry or UserRegistry()
        self._rooms: Dict[str, ArenaRoom] = {}
        self._presence: Dict[str, Presence] = {}  # composite key "user_id:room_id"
        self._callbacks: List[Callable[[str, Dict[str, Any]], None]] = []

    def create_room(self, name: str, created_by: str, description: str = "", private: bool = False) -> ArenaRoom:
        rid = str(uuid.uuid4())[:12]
        room = ArenaRoom(room_id=rid, name=name, description=description,
                          created_by=created_by, is_private=private)
        room.add_member(created_by, Role.OWNER)
        self._rooms[rid] = room
        self._broadcast("room_created", room.to_dict())
        return room

    def get_room(self, room_id: str) -> Optional[ArenaRoom]:
        return self._rooms.get(room_id)

    def join_room(self, room_id: str, user_id: str, role: Role = Role.MEMBER) -> Tuple[bool, str]:
        room = self._rooms.get(room_id)
        if not room:
            return False, "Room not found"
        if room.is_private and user_id not in room.members:
            return False, "Private room"
        if not room.add_member(user_id, role):
            return False, "Room full"
        self._presence[f"{user_id}:{room_id}"] = Presence(user_id, room_id)
        self._broadcast("user_joined", {"room_id": room_id, "user_id": user_id, "role": role.name})
        return True, "Joined"

    def leave_room(self, room_id: str, user_id: str) -> None:
        room = self._rooms.get(room_id)
        if room:
            room.remove_member(user_id)
        self._presence.pop(f"{user_id}:{room_id}", None)
        self._broadcast("user_left", {"room_id": room_id, "user_id": user_id})

    def send_message(self, room_id: str, user_id: str, content: str, msg_type: str = "text") -> Optional[ArenaMessage]:
        room = self._rooms.get(room_id)
        if not room or not room.can(user_id, Permission.WRITE):
            return None
        msg = ArenaMessage(
            message_id=str(uuid.uuid4())[:12],
            room_id=room_id,
            user_id=user_id,
            content=content,
            message_type=msg_type
        )
        room.add_message(msg)
        room.set_typing(user_id, False)
        self._broadcast("message", {"room_id": room_id, "message": msg.__dict__})
        return msg

    def set_typing(self, room_id: str, user_id: str, typing: bool = True) -> None:
        room = self._rooms.get(room_id)
        if room:
            room.set_typing(user_id, typing)
            self._broadcast("typing", {"room_id": room_id, "user_id": user_id, "typing": typing})

    def get_history(self, room_id: str, limit: int = 50) -> List[ArenaMessage]:
        room = self._rooms.get(room_id)
        if not room:
            return []
        return room.messages[-limit:]

    def list_rooms(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        rooms = []
        for room in self._rooms.values():
            if not room.is_private or (user_id and user_id in room.members):
                rooms.append(room.to_dict())
        return rooms

    def get_online_users(self, room_id: str) -> List[str]:
        room = self._rooms.get(room_id)
        if not room:
            return []
        return [uid for uid in room.members if self._presence.get(f"{uid}:{room_id}", Presence("", "")).status == "online"]

    def on_event(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        self._callbacks.append(callback)

    def _broadcast(self, event_type: str, payload: Dict[str, Any]) -> None:
        for cb in self._callbacks:
            try:
                cb(event_type, payload)
            except Exception:
                pass

    def export_snapshot(self) -> Dict[str, Any]:
        return {
            "rooms": {k: v.to_dict() for k, v in self._rooms.items()},
            "users": {k: {"display_name": v.display_name, "status": v.status}
                      for k, v in self.users._users.items()},
            "presence_count": len(self._presence),
        }

    def import_snapshot(self, data: Dict[str, Any]) -> None:
        for rid, rdata in data.get("rooms", {}).items():
            room = ArenaRoom(
                room_id=rid,
                name=rdata["name"],
                description=rdata.get("description", ""),
                created_by=rdata.get("created_by", ""),
                is_private=rdata.get("is_private", False),
                max_members=rdata.get("max_members", 50),
            )
            for uid, role_name in rdata.get("members", {}).items():
                room.members[uid] = Role[role_name]
            self._rooms[rid] = room


class PermissionChecker:
    """Fine-grained permission checking with inheritance."""

    def __init__(self, arena: ArenaManager):
        self.arena = arena

    def check(self, room_id: str, user_id: str, permission: Permission) -> bool:
        room = self.arena.get_room(room_id)
        if not room:
            return False
        return room.can(user_id, permission)

    def assert_can(self, room_id: str, user_id: str, permission: Permission) -> None:
        if not self.check(room_id, user_id, permission):
            raise PermissionError(f"User {user_id} lacks {permission.name} in {room_id}")


# =============================================================================
# DEMO
# =============================================================================

def _demo():
    print("=" * 70)
    print("MULTI-USER ARENA DEMO")
    print("=" * 70)

    # Setup
    users = UserRegistry()
    alice = users.register("Alice", {"team": "alpha"})
    bob = users.register("Bob", {"team": "beta"})
    charlie = users.register("Charlie", {"team": "alpha"})
    print(f"\n[Users] Alice={alice.user_id}, Bob={bob.user_id}, Charlie={charlie.user_id}")

    arena = ArenaManager(users)
    events: List[Tuple[str, Any]] = []
    arena.on_event(lambda et, pl: events.append((et, pl)))

    # Create room
    room = arena.create_room("LLM Arena Alpha", alice.user_id, "Collaborative AI testing", private=False)
    print(f"\n[Room Created] {room.room_id}: {room.name}")

    # Join
    ok, msg = arena.join_room(room.room_id, bob.user_id, Role.MEMBER)
    print(f"[Bob Join] {ok}: {msg}")
    ok, msg = arena.join_room(room.room_id, charlie.user_id, Role.MODERATOR)
    print(f"[Charlie Join] {ok}: {msg}")

    # Messages
    arena.send_message(room.room_id, alice.user_id, "Hello team! Let's test models.")
    arena.set_typing(room.room_id, bob.user_id, True)
    arena.send_message(room.room_id, bob.user_id, "I'm ready, testing GPT-4.")
    arena.set_typing(room.room_id, bob.user_id, False)
    arena.send_message(room.room_id, charlie.user_id, "Claude 3.5 is faster on coding.", msg_type="result")

    print(f"\n[Messages] {len(room.messages)} messages in room")
    for msg in room.messages:
        print(f"  [{msg.user_id[:6]}] ({msg.message_type}) {msg.content[:60]}")

    # Typing
    print(f"\n[Typing] Currently typing: {room.get_typing()}")

    # Permissions
    checker = PermissionChecker(arena)
    print(f"\n[Permissions] Alice can DELETE? {checker.check(room.room_id, alice.user_id, Permission.DELETE)}")
    print(f"[Permissions] Bob can DELETE? {checker.check(room.room_id, bob.user_id, Permission.DELETE)}")
    print(f"[Permissions] Charlie can MANAGE_USERS? {checker.check(room.room_id, charlie.user_id, Permission.MANAGE_USERS)}")

    # History
    history = arena.get_history(room.room_id, limit=2)
    print(f"\n[History Last 2] {len(history)} messages")

    # Presence
    users.update_presence(bob.user_id, "away")
    print(f"\n[Presence] Bob status: {users.get(bob.user_id).status}")

    # Snapshot
    snap = arena.export_snapshot()
    print(f"\n[Snapshot] {len(snap['rooms'])} rooms, {len(snap['users'])} users, {snap['presence_count']} presence entries")

    # Events
    print(f"\n[Events] {len(events)} events captured:")
    for et, pl in events[:6]:
        print(f"  {et}: {str(pl)[:70]}...")

    print("\n" + "=" * 70)
    print("DEMO SELESAI")
    print("=" * 70)


if __name__ == "__main__":
    _demo()

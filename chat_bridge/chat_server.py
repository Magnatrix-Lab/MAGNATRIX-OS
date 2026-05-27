#!/usr/bin/env python3
"""
chat_server.py — MAGNATRIX Chat Bridge Server
WebSocket-based real-time chat layer for multi-user coordination
with MAGNATRIX Agentic OS agents.
"""
import asyncio
import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set


@dataclass
class ChatMessage:
    message_id: str
    sender: str
    content: str
    timestamp: str
    channel: str
    type: str = "text"  # text | command | agent_response | system


@dataclass
class ChatUser:
    user_id: str
    name: str
    channels: Set[str]
    status: str = "online"  # online | away | offline
    joined_at: str = ""


class ChatBridgeServer:
    """WebSocket chat server for MAGNATRIX multi-user coordination."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.users: Dict[str, ChatUser] = {}
        self.messages: Dict[str, List[ChatMessage]] = {}  # channel -> messages
        self.channels: Set[str] = {"general", "trading", "agents", "system", "dev"}
        self.agent_hooks: Dict[str, callable] = {}  # channel -> agent callback
        self.message_history_limit = 1000

    async def start(self):
        """Start WebSocket server."""
        import websockets
        async with websockets.serve(self._handle_connection, self.host, self.port):
            print(f"[MAGNATRIX Chat] Server running on ws://{self.host}:{self.port}")
            await asyncio.Future()  # Run forever

    async def _handle_connection(self, websocket, path):
        """Handle incoming WebSocket connection."""
        user_id = None
        try:
            async for message in websocket:
                data = json.loads(message)
                action = data.get("action")

                if action == "join":
                    user_id = data["user_id"]
                    name = data.get("name", user_id)
                    channels = set(data.get("channels", ["general"]))
                    await self._handle_join(websocket, user_id, name, channels)

                elif action == "message":
                    if user_id:
                        await self._handle_message(websocket, user_id, data)

                elif action == "command":
                    if user_id:
                        await self._handle_command(websocket, user_id, data)

                elif action == "leave":
                    if user_id:
                        await self._handle_leave(user_id)
                        break

        except Exception as e:
            print(f"[MAGNATRIX Chat] Connection error: {e}")
        finally:
            if user_id:
                await self._handle_leave(user_id)

    async def _handle_join(self, websocket, user_id: str, name: str, channels: Set[str]):
        """Handle user joining channels."""
        self.users[user_id] = ChatUser(
            user_id=user_id,
            name=name,
            channels=channels,
            joined_at=datetime.now(timezone.utc).isoformat()
        )
        # Send channel history
        for channel in channels:
            if channel in self.messages:
                history = self.messages[channel][-50:]  # Last 50 messages
                for msg in history:
                    await websocket.send(json.dumps({
                        "type": "history",
                        "channel": channel,
                        "message": asdict(msg)
                    }))
        # Notify others
        await self._broadcast({
            "type": "user_joined",
            "user_id": user_id,
            "name": name,
            "channels": list(channels)
        }, exclude=user_id)

    async def _handle_message(self, websocket, user_id: str, data: dict):
        """Handle chat message."""
        channel = data.get("channel", "general")
        content = data.get("content", "")

        msg = ChatMessage(
            message_id=f"msg-{int(time.time())}-{user_id}",
            sender=user_id,
            content=content,
            timestamp=datetime.now(timezone.utc).isoformat(),
            channel=channel,
            type="text"
        )
        self._store_message(msg)

        # Broadcast to channel
        await self._broadcast({
            "type": "message",
            "channel": channel,
            "message": asdict(msg)
        }, channels={channel})

        # Check if message is a command for an agent
        if content.startswith("@agent"):
            await self._route_to_agent(channel, content, user_id)

    async def _handle_command(self, websocket, user_id: str, data: dict):
        """Handle slash commands."""
        command = data.get("command", "")
        channel = data.get("channel", "general")

        if command == "/status":
            status = {
                "users_online": len([u for u in self.users.values() if u.status == "online"]),
                "channels": list(self.channels),
                "total_messages": sum(len(m) for m in self.messages.values())
            }
            await websocket.send(json.dumps({
                "type": "system",
                "channel": channel,
                "content": f"System status: {status}"
            }))

        elif command == "/agents":
            await websocket.send(json.dumps({
                "type": "system",
                "channel": channel,
                "content": f"Active agent hooks: {list(self.agent_hooks.keys())}"
            }))

    async def _route_to_agent(self, channel: str, content: str, user_id: str):
        """Route message to agent if hook registered."""
        if channel in self.agent_hooks:
            try:
                response = await self.agent_hooks[channel](content, user_id)
                agent_msg = ChatMessage(
                    message_id=f"msg-agent-{int(time.time())}",
                    sender="agent",
                    content=response,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    channel=channel,
                    type="agent_response"
                )
                self._store_message(agent_msg)
                await self._broadcast({
                    "type": "message",
                    "channel": channel,
                    "message": asdict(agent_msg)
                }, channels={channel})
            except Exception as e:
                print(f"[MAGNATRIX Chat] Agent error: {e}")

    async def _handle_leave(self, user_id: str):
        """Handle user leaving."""
        if user_id in self.users:
            del self.users[user_id]
            await self._broadcast({
                "type": "user_left",
                "user_id": user_id
            }, exclude=user_id)

    async def _broadcast(self, data: dict, channels: Optional[Set[str]] = None, exclude: Optional[str] = None):
        """Broadcast message to connected users."""
        # In a real implementation, this would use websockets.broadcast
        # For now, we store and rely on polling or direct WebSocket management
        pass

    def _store_message(self, msg: ChatMessage):
        """Store message in channel history."""
        self.messages.setdefault(msg.channel, [])
        self.messages[msg.channel].append(msg)
        if len(self.messages[msg.channel]) > self.message_history_limit:
            self.messages[msg.channel].pop(0)

    def register_agent_hook(self, channel: str, callback: callable):
        """Register an agent callback for a channel."""
        self.agent_hooks[channel] = callback

    def get_channel_history(self, channel: str, limit: int = 50) -> List[dict]:
        """Get message history for a channel."""
        messages = self.messages.get(channel, [])
        return [asdict(m) for m in messages[-limit:]]

    def get_online_users(self) -> List[dict]:
        """Get list of online users."""
        return [asdict(u) for u in self.users.values() if u.status == "online"]


if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX Chat Bridge Server")
    print("=" * 60)
    server = ChatBridgeServer()
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\n[MAGNATRIX Chat] Server stopped")

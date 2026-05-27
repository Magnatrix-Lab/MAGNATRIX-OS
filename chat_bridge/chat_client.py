#!/usr/bin/env python3
"""
chat_client.py — MAGNATRIX Chat Client
Command-line chat client untuk berkomunikasi dengan MAGNATRIX swarm.
"""
import asyncio
import json
import sys
import threading
import time
from datetime import datetime, timezone


class ChatClient:
    """Simple chat client for MAGNATRIX."""

    def __init__(self, server_url: str = "ws://localhost:8765", user_id: str = None):
        self.server_url = server_url
        self.user_id = user_id or f"user-{int(time.time())}"
        self.name = user_id or "Anonymous"
        self.channels = ["general"]
        self.websocket = None
        self.running = False

    async def connect(self):
        """Connect to chat server."""
        import websockets
        try:
            self.websocket = await websockets.connect(self.server_url)
            self.running = True
            # Send join message
            await self.websocket.send(json.dumps({
                "action": "join",
                "user_id": self.user_id,
                "name": self.name,
                "channels": self.channels
            }))
            print(f"[MAGNATRIX Chat] Connected as {self.user_id}")
            # Start listener
            asyncio.create_task(self._listen())
            return True
        except Exception as e:
            print(f"[MAGNATRIX Chat] Connection failed: {e}")
            return False

    async def _listen(self):
        """Listen for incoming messages."""
        try:
            async for message in self.websocket:
                data = json.loads(message)
                await self._handle_message(data)
        except Exception as e:
            if self.running:
                print(f"[MAGNATRIX Chat] Listen error: {e}")

    async def _handle_message(self, data: dict):
        """Handle incoming message."""
        msg_type = data.get("type")
        if msg_type == "message":
            msg = data.get("message", {})
            sender = msg.get("sender", "unknown")
            content = msg.get("content", "")
            channel = msg.get("channel", "general")
            ts = msg.get("timestamp", "")[11:19] if msg.get("timestamp") else ""
            print(f"\n[{ts}] [{channel}] {sender}: {content}")
        elif msg_type == "user_joined":
            print(f"\n[SYSTEM] {data.get('name')} joined {data.get('channels')}")
        elif msg_type == "user_left":
            print(f"\n[SYSTEM] {data.get('user_id')} left")
        elif msg_type == "system":
            print(f"\n[SYSTEM] {data.get('content')}")

    async def send_message(self, content: str, channel: str = "general"):
        """Send a chat message."""
        if self.websocket:
            await self.websocket.send(json.dumps({
                "action": "message",
                "content": content,
                "channel": channel
            }))

    async def send_command(self, command: str, channel: str = "general"):
        """Send a slash command."""
        if self.websocket:
            await self.websocket.send(json.dumps({
                "action": "command",
                "command": command,
                "channel": channel
            }))

    async def disconnect(self):
        """Disconnect from server."""
        self.running = False
        if self.websocket:
            await self.websocket.send(json.dumps({
                "action": "leave",
                "user_id": self.user_id
            }))
            await self.websocket.close()
        print("[MAGNATRIX Chat] Disconnected")


async def interactive_chat():
    """Run interactive chat session."""
    client = ChatClient()
    if not await client.connect():
        return

    print("\nCommands:")
    print("  /quit        - Leave chat")
    print("  /status      - System status")
    print("  /agents      - List active agents")
    print("  @agent <msg> - Send message to agent")
    print("\nStart typing messages...\n")

    try:
        while client.running:
            # Non-blocking input using asyncio
            loop = asyncio.get_event_loop()
            user_input = await loop.run_in_executor(None, input, "> ")

            if user_input.strip() == "/quit":
                await client.disconnect()
                break
            elif user_input.strip().startswith("/"):
                await client.send_command(user_input.strip())
            elif user_input.strip():
                await client.send_message(user_input.strip())
    except KeyboardInterrupt:
        await client.disconnect()


if __name__ == "__main__":
    print("=" * 60)
    print("MAGNATRIX Chat Client")
    print("=" * 60)
    try:
        asyncio.run(interactive_chat())
    except KeyboardInterrupt:
        print("\n[MAGNATRIX Chat] Goodbye")

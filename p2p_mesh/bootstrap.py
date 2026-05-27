#!/usr/bin/env python3
"""P2P Mesh Bootstrap — libp2p node skeleton"""

import socket
import time

class P2PNode:
    def __init__(self):
        self.host = "127.0.0.1"
        self.port = 0  # random
        self.sock = None

    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        self.port = self.sock.getsockname()[1]
        print(f"🌐 P2P Node listening on /ip4/{self.host}/tcp/{self.port}")

        # Mock: simulate peer connection
        time.sleep(1)
        print("🤝 Peer connected (simulated)")
        print("📨 Received: 'MAGNATRIX peer online'")
        print("📤 Echoed: 'WELCOME'")

        self.stop()

    def stop(self):
        if self.sock:
            self.sock.close()
        print("🛑 Graceful stop.")

if __name__ == "__main__":
    node = P2PNode()
    node.start()

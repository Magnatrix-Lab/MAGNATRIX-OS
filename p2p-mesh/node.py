#!/usr/bin/env python3
"""P2P Mesh Node — 2-node test"""

import socket
import threading
import time

class P2PNode:
    def __init__(self, port=0):
        self.port = port
        self.peers = []

    def listen(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", self.port))
        s.listen(1)
        self.port = s.getsockname()[1]
        print(f"Node A on port {self.port}")

        conn, addr = s.accept()
        data = conn.recv(1024).decode()
        print(f"Node A received: {data}")
        conn.send(b"ACK")
        conn.close()
        s.close()

    def connect(self, port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", port))
        s.send(b"MAGNATRIX peer online")
        ack = s.recv(1024).decode()
        print(f"Node B received: {ack}")
        s.close()

if __name__ == "__main__":
    node_a = P2PNode(0)
    t = threading.Thread(target=node_a.listen)
    t.start()
    time.sleep(0.5)
    node_b = P2PNode(0)
    node_b.connect(node_a.port)
    t.join()
    print("✅ P2P test complete.")

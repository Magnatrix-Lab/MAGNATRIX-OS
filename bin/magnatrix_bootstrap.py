#!/usr/bin/env python3
"""
bin/magnatrix_bootstrap.py
==========================
MAGNATRIX-OS First-Time Bootstrap

Creates:
  - Directory structure (/var/lib/magnatrix/*)
  - Default configuration (config/magnatrix.json)
  - First identity keypair
  - WAL directories
  - Log directories
  - SQLite databases

Usage:
  python bin/magnatrix_bootstrap.py [--force]
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


DIRECTORIES = [
    "/var/lib/magnatrix/identities",
    "/var/lib/magnatrix/logs",
    "/var/lib/magnatrix/wal",
    "/var/lib/magnatrix/raft",
    "/var/lib/magnatrix/streaming",
    "/var/lib/magnatrix/cache",
    "/var/lib/magnatrix/models",
    "/var/lib/magnatrix/plugins",
    "/var/lib/magnatrix/snapshots",
]

DEFAULT_CONFIG = {
    "kernel": {
        "log_level": "INFO",
        "max_workers": 4,
        "shutdown_timeout_sec": 10.0,
    },
    "identity": {
        "key_store": "/var/lib/magnatrix/identities",
        "auto_rotate": True,
        "rotation_days": 90,
    },
    "protocol": {
        "message_encoding": "msgpack",
        "max_message_size": 10485760,
        "compression": "zstd",
    },
    "api_router": {
        "listen_host": "127.0.0.1",
        "listen_port": 8000,
        "rate_limit": 1000,
    },
    "p2p_mesh": {
        "listen_port": 8001,
        "bootstrap_peers": [],
        "max_connections": 64,
        "encryption": "chacha20poly1305",
    },
    "knowledge": {
        "vector_dim": 768,
        "index_type": "hnsw",
        "graph_db_path": "/var/lib/magnatrix/graph.db",
        "time_series_path": "/var/lib/magnatrix/tsdb",
    },
    "ai": {
        "default_model": "llama-3-8b-instruct",
        "models_dir": "/var/lib/magnatrix/models",
        "max_seq_len": 4096,
        "temperature": 0.7,
        "top_p": 0.9,
        "quantization": "q4_0",
    },
    "sandbox": {
        "enabled": True,
        "max_cpu_percent": 80,
        "max_memory_mb": 1024,
        "max_processes": 32,
        "seccomp_mode": "filter",
    },
    "governance": {
        "voting_threshold": 0.67,
        "proposal_ttl_hours": 72,
        "auto_execute": False,
    },
    "security": {
        "secret_vault": "/var/lib/magnatrix/secrets.enc",
        "auto_lock_minutes": 30,
        "audit_retention_days": 365,
    },
}


def create_directories() -> None:
    for d in DIRECTORIES:
        os.makedirs(d, mode=0o700, exist_ok=True)
        print(f"  [DIR] {d}")


def write_config(path: str = "config/magnatrix.json", force: bool = False) -> None:
    if os.path.exists(path) and not force:
        print(f"  [SKIP] Config exists: {path}")
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
    print(f"  [WRITE] {path}")


def generate_first_identity() -> None:
    try:
        from identity.crypto_identity_native import Ed25519KeyPair, IdentityRegistry
        registry = IdentityRegistry()
        name = "magnatrix-root"
        if name not in registry.list_identities():
            kp = Ed25519KeyPair()
            password = secrets.token_urlsafe(32)
            registry.save(name, kp, password)
            print(f"  [IDENTITY] Generated root identity: {name}")
            print(f"  [IDENTITY] Public key: {kp.public_key_hex[:32]}...")
            print(f"  [IDENTITY] Password stored in: /var/lib/magnatrix/.bootstrap_password (DELETE AFTER RECORDING)")
            with open("/var/lib/magnatrix/.bootstrap_password", "w") as f:
                f.write(password)
            os.chmod("/var/lib/magnatrix/.bootstrap_password", 0o600)
        else:
            print(f"  [SKIP] Identity exists: {name}")
    except Exception as e:
        print(f"  [ERROR] Identity generation failed: {e}")


def create_sqlite_dbs() -> None:
    import sqlite3
    dbs = [
        "/var/lib/magnatrix/graph.db",
        "/var/lib/magnatrix/events.db",
        "/var/lib/magnatrix/metrics.db",
    ]
    for db_path in dbs:
        if os.path.exists(db_path):
            print(f"  [SKIP] DB exists: {db_path}")
            continue
        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.commit()
        conn.close()
        os.chmod(db_path, 0o600)
        print(f"  [DB] {db_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="MAGNATRIX-OS Bootstrap")
    parser.add_argument("--force", action="store_true", help="Overwrite existing files")
    args = parser.parse_args()

    print("=" * 60)
    print("MAGNATRIX-OS  |  FIRST-TIME BOOTSTRAP")
    print("=" * 60)

    create_directories()
    write_config(force=args.force)
    generate_first_identity()
    create_sqlite_dbs()

    print("=" * 60)
    print("Bootstrap complete. Run: python magnatrix.py boot")
    print("=" * 60)


if __name__ == "__main__":
    main()

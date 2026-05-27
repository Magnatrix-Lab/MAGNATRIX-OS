#!/usr/bin/env python3
"""Long-Term Episodic Memory — MAGNATRIX-OS ASI Expansion
Path: knowledge/episodic_native.py
License: AGPL-3.0
Authors: MAGNATRIX-Lab
Depends: Python 3.11+ stdlib only.

Append-only replay buffer with K-means++ consolidation into semantic clusters.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
import os
import pickle
import random
import sqlite3
import struct
import zlib
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("episodic_memory")

# ═══════════════════════════════════════════════════════════════════════════════
# BASELAYER — Episode, Embedding
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class Action:
    action_type: str
    params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Episode:
    id: str
    ts: float
    agent_id: str
    observation: Dict[str, Any]
    action: Optional[Action] = None
    reward: Optional[float] = None
    embedding: List[float] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    raw_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "ts": self.ts,
            "agent_id": self.agent_id,
            "observation": json.dumps(self.observation),
            "action": json.dumps(self.action.__dict__) if self.action else None,
            "reward": self.reward,
            "embedding": json.dumps(self.embedding),
            "tags": json.dumps(self.tags),
            "raw_text": self.raw_text,
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> Episode:
        return Episode(
            id=d["id"],
            ts=d["ts"],
            agent_id=d["agent_id"],
            observation=json.loads(d["observation"]),
            action=Action(**json.loads(d["action"])) if d["action"] else None,
            reward=d["reward"],
            embedding=json.loads(d["embedding"]),
            tags=json.loads(d["tags"]),
            raw_text=d["raw_text"],
        )


def deterministic_hash(text: str, dim: int = 128) -> List[float]:
    """Deterministic embedding from text using SHA-256 chaining."""
    vec = []
    seed = text.encode("utf-8")
    for i in range(dim // 8):
        h = hashlib.sha256(seed + struct.pack("<I", i)).digest()
        for j in range(8):
            val = struct.unpack("<h", h[j*2:j*2+2])[0] / 32768.0
            vec.append(val)
    return vec


def cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ═══════════════════════════════════════════════════════════════════════════════
# COREENGINE — K-Means++ Clustering
# ═══════════════════════════════════════════════════════════════════════════════

def kmeans_plus_plus(points: List[List[float]], k: int, rng: random.Random) -> List[List[float]]:
    """K-means++ initialization."""
    centroids = [points[rng.randint(0, len(points) - 1)]]
    for _ in range(1, k):
        dists = []
        for p in points:
            min_d = min(sum((a - b) ** 2 for a, b in zip(p, c)) for c in centroids)
            dists.append(min_d)
        total = sum(dists)
        if total == 0:
            centroids.append(points[rng.randint(0, len(points) - 1)])
            continue
        pick = rng.random() * total
        cum = 0.0
        for p, d in zip(points, dists):
            cum += d
            if cum >= pick:
                centroids.append(p)
                break
        else:
            centroids.append(points[-1])
    return centroids


def kmeans(points: List[List[float]], k: int, max_iter: int = 50, rng_seed: int = 42) -> Tuple[List[List[float]], List[int]]:
    """Lloyd's algorithm with k-means++ init. Returns (centroids, assignments)."""
    if not points or k <= 0:
        return [], []
    k = min(k, len(points))
    rng = random.Random(rng_seed)
    centroids = kmeans_plus_plus(points, k, rng)
    assignments = [0] * len(points)

    for _ in range(max_iter):
        # Assignment step
        changed = False
        for i, p in enumerate(points):
            best_j = 0
            best_d = float("inf")
            for j, c in enumerate(centroids):
                d = sum((a - b) ** 2 for a, b in zip(p, c))
                if d < best_d:
                    best_d = d
                    best_j = j
            if assignments[i] != best_j:
                assignments[i] = best_j
                changed = True
        # Update step
        new_centroids = []
        for j in range(k):
            cluster = [points[i] for i in range(len(points)) if assignments[i] == j]
            if cluster:
                dim = len(cluster[0])
                new_c = [sum(p[d] for p in cluster) / len(cluster) for d in range(dim)]
                new_centroids.append(new_c)
            else:
                new_centroids.append(centroids[j])
        centroids = new_centroids
        if not changed:
            break
    return centroids, assignments


# ═══════════════════════════════════════════════════════════════════════════════
# FEATURES — EpisodicMemory
# ═══════════════════════════════════════════════════════════════════════════════

class EpisodicMemory:
    """Append-only episodic memory with consolidation and replay."""

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS episodes (
        id TEXT PRIMARY KEY,
        ts REAL NOT NULL,
        agent_id TEXT NOT NULL,
        observation TEXT,
        action TEXT,
        reward REAL,
        embedding TEXT,
        tags TEXT,
        raw_text TEXT,
        compressed INTEGER DEFAULT 0
    );
    CREATE INDEX IF NOT EXISTS idx_ts ON episodes(ts);
    CREATE INDEX IF NOT EXISTS idx_agent ON episodes(agent_id);
    CREATE INDEX IF NOT EXISTS idx_tags ON episodes(tags);
    CREATE TABLE IF NOT EXISTS semantic_clusters (
        cluster_id INTEGER PRIMARY KEY,
        centroid TEXT NOT NULL,
        episode_ids TEXT NOT NULL,
        created_ts REAL NOT NULL,
        summary TEXT
    );
    CREATE TABLE IF NOT EXISTS meta (
        key TEXT PRIMARY KEY,
        value TEXT
    );
    """

    def __init__(self, db_path: Optional[str] = None, auto_consolidate: bool = True):
        if db_path is None:
            home = Path.home() / ".magnatrix" / "episodic"
            home.mkdir(parents=True, exist_ok=True)
            db_path = str(home / "episodes.db")
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(self.SCHEMA)
        self.conn.commit()
        self._write_count = 0
        self._consolidate_every = 1000 if auto_consolidate else 999999999

    def write(self, ep: Episode) -> None:
        """Append an episode."""
        if not ep.embedding and ep.raw_text:
            ep.embedding = deterministic_hash(ep.raw_text)
        d = ep.to_dict()
        self.conn.execute(
            """INSERT INTO episodes (id, ts, agent_id, observation, action, reward, embedding, tags, raw_text)
               VALUES (:id, :ts, :agent_id, :observation, :action, :reward, :embedding, :tags, :raw_text)""",
            d,
        )
        self.conn.commit()
        self._write_count += 1
        if self._write_count >= self._consolidate_every:
            self.consolidate()
            self._write_count = 0

    def query(self, q: str, k: int = 10) -> List[Episode]:
        """Semantic + temporal search with text fallback."""
        q_emb = deterministic_hash(q)
        q_lower = q.lower()
        cursor = self.conn.execute("SELECT * FROM episodes")
        rows = cursor.fetchall()
        scored = []
        now = datetime.now(timezone.utc).timestamp()
        for row in rows:
            raw_text = row[8]
            # Decompress if needed
            if row[9] == 1 and raw_text:
                try:
                    raw_text = zlib.decompress(bytes.fromhex(raw_text)).decode("utf-8")
                    raw_text = json.loads(raw_text).get("raw_text", "")
                except Exception:
                    raw_text = ""
            ep = Episode.from_dict({
                "id": row[0], "ts": row[1], "agent_id": row[2], "observation": row[3],
                "action": row[4], "reward": row[5], "embedding": row[6], "tags": row[7], "raw_text": raw_text,
            })
            emb = json.loads(row[6]) if row[6] else []
            sim = cosine_similarity(q_emb, emb) if emb else 0.0
            # Text overlap bonus
            text_bonus = 0.0
            if q_lower in raw_text.lower():
                text_bonus = 0.5
            # Temporal decay: recent episodes get boost
            age = max(0, now - ep.ts)
            temporal_score = math.exp(-age / 86400)  # 1-day half-life
            scored.append((sim * 0.5 + text_bonus + temporal_score * 0.2, ep))
        scored.sort(key=lambda x: -x[0])
        return [ep for _, ep in scored[:k]]

    def consolidate(self) -> int:
        """Cluster recent episodes into semantic patterns."""
        # Get recent episodes
        cursor = self.conn.execute(
            "SELECT * FROM episodes WHERE compressed=0 ORDER BY ts DESC LIMIT 5000"
        )
        rows = cursor.fetchall()
        if len(rows) < 50:
            return 0
        points = []
        ep_ids = []
        for row in rows:
            emb = json.loads(row[6]) if row[6] else []
            if emb:
                points.append(emb)
                ep_ids.append(row[0])
        if not points:
            return 0
        target_k = max(2, len(points) // 20)
        centroids, assignments = kmeans(points, target_k)
        # Store clusters
        now = datetime.now(timezone.utc).timestamp()
        clusters = defaultdict(list)
        for ep_id, assign in zip(ep_ids, assignments):
            clusters[assign].append(ep_id)
        for cid, ids in clusters.items():
            summary = f"Cluster {cid}: {len(ids)} episodes"
            self.conn.execute(
                "INSERT INTO semantic_clusters (centroid, episode_ids, created_ts, summary) VALUES (?, ?, ?, ?)",
                (json.dumps(centroids[cid]), json.dumps(ids), now, summary),
            )
        # Compress old episodes (>30 days relative to newest)
        max_ts_row = self.conn.execute("SELECT MAX(ts) FROM episodes").fetchone()
        max_ts = max_ts_row[0] if max_ts_row and max_ts_row[0] else now
        cutoff = max_ts - 30 * 86400
        old = self.conn.execute("SELECT * FROM episodes WHERE ts < ? AND compressed=0", (cutoff,)).fetchall()
        for row in old:
            raw = json.dumps({
                "id": row[0], "ts": row[1], "agent_id": row[2], "observation": row[3],
                "action": row[4], "reward": row[5], "embedding": row[6], "tags": row[7], "raw_text": row[8],
            })
            compressed = zlib.compress(raw.encode("utf-8"))
            self.conn.execute(
                "UPDATE episodes SET observation=?, action=?, reward=?, embedding=?, tags=?, raw_text=?, compressed=1 WHERE id=?",
                (None, None, None, None, None, compressed.hex(), row[0]),
            )
        self.conn.commit()
        return len(clusters)

    def replay(self, agent_id: str, window: Tuple[float, float]) -> Iterator[Episode]:
        """Replay episodes for an agent in a time window."""
        cursor = self.conn.execute(
            "SELECT * FROM episodes WHERE agent_id=? AND ts>=? AND ts<=? ORDER BY ts",
            (agent_id, window[0], window[1]),
        )
        for row in cursor:
            raw_text = row[8]
            if row[9] == 1 and raw_text:
                try:
                    raw_text = zlib.decompress(bytes.fromhex(raw_text)).decode("utf-8")
                    raw_text = json.loads(raw_text).get("raw_text", "")
                except Exception:
                    raw_text = ""
            yield Episode.from_dict({
                "id": row[0], "ts": row[1], "agent_id": row[2], "observation": row[3],
                "action": row[4], "reward": row[5], "embedding": row[6], "tags": row[7], "raw_text": raw_text,
            })

    def forget(self, criteria: Dict[str, Any]) -> int:
        """Explicit forgetting by criteria."""
        where = ["1=1"]
        params = []
        if "agent_id" in criteria:
            where.append("agent_id=?")
            params.append(criteria["agent_id"])
        if "before_ts" in criteria:
            where.append("ts<?")
            params.append(criteria["before_ts"])
        if "tag" in criteria:
            where.append("tags LIKE ?")
            params.append(f'%"{criteria["tag"]}"%')
        sql = f"DELETE FROM episodes WHERE {' AND '.join(where)}"
        cur = self.conn.execute(sql, params)
        self.conn.commit()
        return cur.rowcount

    def count(self) -> int:
        row = self.conn.execute("SELECT COUNT(*) FROM episodes").fetchone()
        return row[0] if row else 0

    def close(self) -> None:
        self.conn.close()


# ═══════════════════════════════════════════════════════════════════════════════
# SELF-TEST
# ═══════════════════════════════════════════════════════════════════════════════

def _self_test():
    import tempfile
    print("=" * 55)
    print("Episodic Memory — Self Test")
    print("=" * 55)

    db_file = tempfile.mktemp(suffix=".db")
    mem = EpisodicMemory(db_file, auto_consolidate=False)
    passed = 0
    total = 6
    now = datetime.now(timezone.utc).timestamp()

    # Test 1: Write 1,000 episodes
    print("\n[Test 1] Write 1,000 episodes")
    for i in range(1000):
        ep = Episode(
            id=f"ep_{i:05d}",
            ts=now - 86400 + i,  # recent, within last day
            agent_id=f"agent_{i % 10}",
            observation={"state": f"state_{i}", "value": i},
            action=Action("move", {"dir": "up"}) if i % 2 == 0 else None,
            reward=float(i % 100) / 100,
            raw_text=f"The agent moved to state {i} and observed value {i}",
            tags=["move", "explore"] if i % 2 == 0 else ["observe"],
        )
        mem.write(ep)
    count = mem.count()
    ok = count == 1000
    print(f"  Count: {count} — {'PASS' if ok else 'FAIL'}")
    passed += ok

    # Test 2: Query by content
    print("\n[Test 2] Query by content")
    results = mem.query("agent moved to state 500", k=10)
    recall_ok = len(results) > 0 and any("500" in r.raw_text for r in results)
    print(f"  Top results: {len(results)} — {'PASS' if recall_ok else 'FAIL'}")
    passed += recall_ok

    # Test 3: Consolidation
    print("\n[Test 3] Consolidation")
    n_clusters = mem.consolidate()
    print(f"  Clusters created: {n_clusters} — {'PASS' if n_clusters > 0 else 'FAIL'}")
    passed += (n_clusters > 0)

    # Test 4: Replay
    print("\n[Test 4] Replay")
    replayed = list(mem.replay("agent_0", (now - 86400, now - 86400 + 200)))
    print(f"  Replay count: {len(replayed)} — {'PASS' if len(replayed) > 0 else 'FAIL'}")
    passed += (len(replayed) > 0)

    # Test 5: Temporal order
    print("\n[Test 5] Temporal order")
    times = [r.ts for r in replayed]
    ordered = times == sorted(times)
    print(f"  Ordered: {ordered} — {'PASS' if ordered else 'FAIL'}")
    passed += ordered

    # Test 6: Forget
    print("\n[Test 6] Forget")
    before = mem.count()
    deleted = mem.forget({"agent_id": "agent_5"})
    after = mem.count()
    print(f"  Before: {before}, After: {after}, Deleted: {deleted} — {'PASS' if deleted > 0 else 'FAIL'}")
    passed += (deleted > 0)

    mem.close()
    try:
        os.remove(db_file)
    except OSError:
        pass

    print("\n" + "=" * 55)
    print(f"PASS: {passed}/{total} tests")
    print("=" * 55)
    import sys
    sys.exit(0 if passed == total else 1)

if __name__ == "__main__":
    _self_test()

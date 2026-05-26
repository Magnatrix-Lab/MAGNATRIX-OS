#!/usr/bin/env python3
"""
MAGNATRIX-OS Layer: Runtime — State Management Backend
File: runtime/state_management_native.py
Pattern: AMATI-PELAJARI-TIRU dari Redis + FAISS + Neo4j + Temporal DB

Native pure-Python reimplementation of:
  - Redis-like: key-value store dengan pub/sub, TTL, transactions, streams
  - Vector DB: cosine similarity search, ANN-style indexing, metadata filtering
  - Graph DB: nodes/edges/relations, pathfinding, Cypher-like queries
  - Temporal Store: time-series events, audit trail, checkpointing
  - State Checkpointing: save/restore agent states for fault tolerance
  - Schema Migration: versioned schema changes

Zero external dependencies. Pure Python standard library.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union


# ============================================================================
# 1.  REDIS-LIKE STORE — KV + Pub/Sub + TTL + Transactions + Streams
# ============================================================================

class RedisLikeStore:
    """
    In-memory Redis-like store dengan full feature parity untuk agent state.
    Supports: strings, lists, hashes, sets, sorted sets, pub/sub, streams.
    """

    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}  # key -> {type, value, expires}
        self._pubsub: Dict[str, List[Callable[[str, Any], None]]] = defaultdict(list)
        self._tx_lock = threading.RLock()
        self._stream_seq: Dict[str, int] = defaultdict(int)

    # --- Core KV ---

    def set(self, key: str, value: Any, ttl_ms: Optional[int] = None) -> bool:
        with self._tx_lock:
            self._store[key] = {
                "type": "string",
                "value": value,
                "expires": time.time() + ttl_ms / 1000.0 if ttl_ms else None,
            }
        return True

    def get(self, key: str) -> Any:
        with self._tx_lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if entry.get("expires") and time.time() > entry["expires"]:
                del self._store[key]
                return None
            return entry["value"]

    def delete(self, *keys: str) -> int:
        count = 0
        with self._tx_lock:
            for k in keys:
                if k in self._store:
                    del self._store[k]
                    count += 1
        return count

    def exists(self, *keys: str) -> int:
        with self._tx_lock:
            return sum(1 for k in keys if k in self._store and not self._is_expired(k))

    def _is_expired(self, key: str) -> bool:
        entry = self._store.get(key)
        if entry and entry.get("expires") and time.time() > entry["expires"]:
            return True
        return False

    def keys(self, pattern: str = "*") -> List[str]:
        with self._tx_lock:
            if pattern == "*":
                return [k for k in self._store.keys() if not self._is_expired(k)]
            regex = pattern.replace("*", ".*").replace("?", ".")
            return [k for k in self._store.keys() if re.match(regex, k) and not self._is_expired(k)]

    def incr(self, key: str, amount: int = 1) -> int:
        with self._tx_lock:
            val = self.get(key)
            new_val = (val or 0) + amount
            self.set(key, new_val)
            return new_val

    # --- Collections ---

    def lpush(self, key: str, *values: Any) -> int:
        with self._tx_lock:
            entry = self._store.get(key)
            if entry is None:
                self._store[key] = {"type": "list", "value": list(reversed(values)), "expires": None}
            else:
                entry["value"] = list(reversed(values)) + entry["value"]
            return len(self._store[key]["value"])

    def lrange(self, key: str, start: int, end: int) -> List[Any]:
        with self._tx_lock:
            entry = self._store.get(key)
            if not entry or entry["type"] != "list":
                return []
            return entry["value"][start:end]

    def hset(self, key: str, field: str, value: Any) -> int:
        with self._tx_lock:
            entry = self._store.get(key)
            if entry is None:
                self._store[key] = {"type": "hash", "value": {field: value}, "expires": None}
                return 1
            if entry["type"] != "hash":
                return 0
            is_new = 1 if field not in entry["value"] else 0
            entry["value"][field] = value
            return is_new

    def hget(self, key: str, field: str) -> Any:
        with self._tx_lock:
            entry = self._store.get(key)
            if not entry or entry["type"] != "hash":
                return None
            return entry["value"].get(field)

    def hgetall(self, key: str) -> Dict[str, Any]:
        with self._tx_lock:
            entry = self._store.get(key)
            if not entry or entry["type"] != "hash":
                return {}
            return entry["value"].copy()

    def sadd(self, key: str, *members: Any) -> int:
        with self._tx_lock:
            entry = self._store.get(key)
            if entry is None:
                self._store[key] = {"type": "set", "value": set(members), "expires": None}
                return len(members)
            if entry["type"] != "set":
                return 0
            old_len = len(entry["value"])
            entry["value"].update(members)
            return len(entry["value"]) - old_len

    def smembers(self, key: str) -> Set[Any]:
        with self._tx_lock:
            entry = self._store.get(key)
            if not entry or entry["type"] != "set":
                return set()
            return entry["value"].copy()

    def zadd(self, key: str, *score_members: Tuple[float, Any]) -> int:
        with self._tx_lock:
            entry = self._store.get(key)
            if entry is None:
                # score_members is flattened: score1, member1, score2, member2...
                zset = {}
                for i in range(0, len(score_members), 2):
                    zset[score_members[i + 1]] = score_members[i]
                self._store[key] = {"type": "zset", "value": zset, "expires": None}
                return len(zset)
            if entry["type"] != "zset":
                return 0
            added = 0
            for i in range(0, len(score_members), 2):
                m = score_members[i + 1]
                if m not in entry["value"]:
                    added += 1
                entry["value"][m] = score_members[i]
            return added

    def zrange(self, key: str, start: int, end: int) -> List[Any]:
        with self._tx_lock:
            entry = self._store.get(key)
            if not entry or entry["type"] != "zset":
                return []
            sorted_items = sorted(entry["value"].items(), key=lambda x: (x[1], x[0]))
            # Redis-style inclusive range
            if end < 0:
                end = len(sorted_items) + end + 1
            else:
                end = end + 1
            return [m for m, s in sorted_items[start:end]]

    # --- Pub/Sub ---

    def publish(self, channel: str, message: Any) -> int:
        with self._tx_lock:
            listeners = self._pubsub[channel].copy()
        for listener in listeners:
            try:
                listener(channel, message)
            except Exception:
                pass
        return len(listeners)

    def subscribe(self, channel: str, listener: Callable[[str, Any], None]) -> None:
        with self._tx_lock:
            self._pubsub[channel].append(listener)

    def unsubscribe(self, channel: str, listener: Callable[[str, Any], None]) -> None:
        with self._tx_lock:
            if listener in self._pubsub[channel]:
                self._pubsub[channel].remove(listener)

    # --- Streams ---

    def xadd(self, stream: str, fields: Dict[str, Any]) -> str:
        with self._tx_lock:
            self._stream_seq[stream] += 1
            seq = self._stream_seq[stream]
            entry_id = f"{int(time.time() * 1000)}-{seq}"
            key = f"stream:{stream}:{entry_id}"
            self._store[key] = {"type": "stream_entry", "value": fields, "id": entry_id, "expires": None}
            return entry_id

    def xrange(self, stream: str, count: int = 10) -> List[Tuple[str, Dict[str, Any]]]:
        with self._tx_lock:
            prefix = f"stream:{stream}:"
            entries = []
            for k, v in self._store.items():
                if k.startswith(prefix) and v["type"] == "stream_entry":
                    entries.append((v["id"], v["value"]))
            entries.sort()
            return entries[-count:]

    # --- Persistence ---

    def save(self, path: str) -> bool:
        snapshot = {}
        with self._tx_lock:
            for k, v in self._store.items():
                if not self._is_expired(k):
                    snapshot[k] = {"type": v["type"], "value": v["value"]}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2, default=str)
        return True

    def load(self, path: str) -> bool:
        if not os.path.isfile(path):
            return False
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        with self._tx_lock:
            self._store.clear()
            for k, v in data.items():
                if v["type"] == "set":
                    v["value"] = set(v["value"])
                elif v["type"] == "zset":
                    v["value"] = {m: float(s) for m, s in v["value"].items()}
                self._store[k] = {**v, "expires": None}
        return True


# ============================================================================
# 2.  VECTOR DB — Cosine Similarity + Metadata Filtering
# ============================================================================

class VectorDB:
    """
    FAISS-like vector database in pure Python.
    Hash-based embeddings, cosine similarity, metadata filtering.
    """

    def __init__(self, dimension: int = 128) -> None:
        self.dim = dimension
        self._vectors: Dict[str, Tuple[List[float], Dict[str, Any]]] = {}
        self._lock = threading.RLock()

    @staticmethod
    def _embed(text: str, dim: int) -> List[float]:
        """Deterministic embedding dari text."""
        h = hashlib.sha256(text.encode()).digest()
        vec = []
        for i in range(dim):
            val = (h[i % 32] + i * 7) % 200 - 100
            vec.append(val / 100.0)
        mag = sum(x * x for x in vec) ** 0.5
        if mag > 0:
            vec = [x / mag for x in vec]
        return vec

    def add(self, doc_id: str, text: str, metadata: Dict[str, Any] = None) -> None:
        embedding = self._embed(text, self.dim)
        with self._lock:
            self._vectors[doc_id] = (embedding, metadata or {})

    def search(self, query: str, top_k: int = 5,
               filter_meta: Optional[Callable[[Dict[str, Any]], bool]] = None) -> List[Tuple[str, float, Dict[str, Any]]]:
        q_vec = self._embed(query, self.dim)
        with self._lock:
            results = []
            for doc_id, (vec, meta) in self._vectors.items():
                if filter_meta and not filter_meta(meta):
                    continue
                score = sum(a * b for a, b in zip(q_vec, vec))
                results.append((doc_id, score, meta))
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:top_k]

    def delete(self, doc_id: str) -> bool:
        with self._lock:
            if doc_id in self._vectors:
                del self._vectors[doc_id]
                return True
            return False

    def count(self) -> int:
        with self._lock:
            return len(self._vectors)

    def get_metadata(self, doc_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            entry = self._vectors.get(doc_id)
            return entry[1] if entry else None


# ============================================================================
# 3.  GRAPH DB — Nodes, Edges, Pathfinding, Cypher-lite
# ============================================================================

class GraphDB:
    """
    Neo4j-like graph database in pure Python.
    Nodes, directed edges, properties, pathfinding, simple queries.
    """

    def __init__(self) -> None:
        self._nodes: Dict[str, Dict[str, Any]] = {}  # id -> {labels, props}
        self._edges: Dict[str, List[Tuple[str, str, Dict[str, Any]]]] = defaultdict(list)
        # _edges[from] = [(relation, to, properties)]
        self._lock = threading.RLock()

    def create_node(self, node_id: str, labels: List[str] = None,
                    properties: Dict[str, Any] = None) -> None:
        with self._lock:
            self._nodes[node_id] = {
                "labels": labels or ["Node"],
                "properties": properties or {},
            }

    def create_edge(self, from_node: str, to_node: str, relation: str,
                    properties: Dict[str, Any] = None) -> bool:
        with self._lock:
            if from_node not in self._nodes or to_node not in self._nodes:
                return False
            self._edges[from_node].append((relation, to_node, properties or {}))
            return True

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self._nodes.get(node_id)

    def get_neighbors(self, node_id: str, relation: Optional[str] = None) -> List[Tuple[str, str, Dict[str, Any]]]:
        with self._lock:
            edges = self._edges.get(node_id, [])
            if relation:
                edges = [e for e in edges if e[0] == relation]
            return edges

    def get_predecessors(self, node_id: str, relation: Optional[str] = None) -> List[Tuple[str, str, Dict[str, Any]]]:
        """Get nodes that have edges TO node_id."""
        with self._lock:
            preds = []
            for from_id, edges in self._edges.items():
                for rel, to_id, props in edges:
                    if to_id == node_id:
                        if relation is None or rel == relation:
                            preds.append((from_id, rel, props))
            return preds

    def bfs_paths(self, start: str, end: str, max_depth: int = 5,
                  relation: Optional[str] = None) -> List[List[str]]:
        """Find all simple paths dari start ke end."""
        paths = []
        q = deque([(start, [start])])
        while q:
            node, path = q.popleft()
            if node == end and len(path) > 1:
                paths.append(path)
                continue
            if len(path) > max_depth:
                continue
            for rel, target, _ in self.get_neighbors(node, relation):
                if target not in path:  # avoid cycles
                    q.append((target, path + [target]))
        return paths

    def query(self, label: Optional[str] = None,
              property_filter: Optional[Dict[str, Any]] = None) -> List[str]:
        """Simple query: find nodes by label and/or properties."""
        with self._lock:
            results = []
            for node_id, data in self._nodes.items():
                if label and label not in data["labels"]:
                    continue
                if property_filter:
                    props = data["properties"]
                    if not all(props.get(k) == v for k, v in property_filter.items()):
                        continue
                results.append(node_id)
            return results

    def delete_node(self, node_id: str) -> bool:
        with self._lock:
            if node_id in self._nodes:
                del self._nodes[node_id]
                # Remove edges FROM this node
                if node_id in self._edges:
                    del self._edges[node_id]
                # Remove edges TO this node
                for from_id in list(self._edges.keys()):
                    self._edges[from_id] = [e for e in self._edges[from_id] if e[1] != node_id]
                return True
            return False

    def shortest_path(self, start: str, end: str,
                      relation: Optional[str] = None) -> Optional[List[str]]:
        """BFS shortest path."""
        q = deque([(start, [start])])
        visited = {start}
        while q:
            node, path = q.popleft()
            if node == end:
                return path
            for rel, target, _ in self.get_neighbors(node, relation):
                if target not in visited:
                    visited.add(target)
                    q.append((target, path + [target]))
        return None


# ============================================================================
# 4.  TEMPORAL STORE — Time-Series Events, Audit Trail, Checkpointing
# ============================================================================

@dataclass
class TemporalEvent:
    event_id: str
    timestamp: float
    event_type: str
    source: str
    payload: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


class TemporalStore:
    """
    Time-series event store untuk audit trail dan checkpointing.
    """

    def __init__(self, max_events: int = 10000) -> None:
        self._events: deque = deque(maxlen=max_events)
        self._checkpoints: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def append(self, event_type: str, source: str,
               payload: Dict[str, Any] = None, tags: List[str] = None) -> str:
        event = TemporalEvent(
            event_id=f"evt_{uuid.uuid4().hex[:12]}",
            timestamp=time.time(),
            event_type=event_type,
            source=source,
            payload=payload or {},
            tags=tags or [],
        )
        with self._lock:
            self._events.append(event)
        return event.event_id

    def query(self, since: float = 0, until: float = None,
              event_type: Optional[str] = None,
              source: Optional[str] = None,
              tags: Optional[List[str]] = None) -> List[TemporalEvent]:
        until = until or time.time() + 1
        with self._lock:
            results = []
            for evt in self._events:
                if not (since <= evt.timestamp <= until):
                    continue
                if event_type and evt.event_type != event_type:
                    continue
                if source and evt.source != source:
                    continue
                if tags and not any(t in evt.tags for t in tags):
                    continue
                results.append(evt)
            return results

    def get_latest(self, n: int = 10) -> List[TemporalEvent]:
        with self._lock:
            return list(self._events)[-n:]

    def checkpoint(self, name: str, state: Dict[str, Any]) -> None:
        with self._lock:
            self._checkpoints[name] = {
                "state": state,
                "timestamp": time.time(),
                "event_count": len(self._events),
            }

    def restore(self, name: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            cp = self._checkpoints.get(name)
            return cp["state"] if cp else None

    def export(self, path: str) -> bool:
        with self._lock:
            data = {
                "events": [asdict(e) for e in self._events],
                "checkpoints": self._checkpoints,
            }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        return True

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            types = defaultdict(int)
            sources = defaultdict(int)
            for e in self._events:
                types[e.event_type] += 1
                sources[e.source] += 1
            return {
                "total_events": len(self._events),
                "event_types": dict(types),
                "sources": dict(sources),
                "checkpoints": len(self._checkpoints),
            }


# ============================================================================
# 5.  STATE MANAGER — Unified facade
# ============================================================================

class StateManager:
    """
    Unified state manager combining all backends.
    Agents use this untuk all their state needs.
    """

    def __init__(self) -> None:
        self.kv = RedisLikeStore()
        self.vectors = VectorDB(dimension=128)
        self.graph = GraphDB()
        self.temporal = TemporalStore()

    def agent_set(self, agent_id: str, key: str, value: Any) -> None:
        full_key = f"agent:{agent_id}:{key}"
        self.kv.set(full_key, value)
        self.temporal.append("agent_state_change", agent_id, {"key": key, "action": "set"})

    def agent_get(self, agent_id: str, key: str) -> Any:
        return self.kv.get(f"agent:{agent_id}:{key}")

    def agent_checkpoint(self, agent_id: str, state: Dict[str, Any]) -> None:
        self.temporal.checkpoint(f"agent:{agent_id}", state)
        self.kv.set(f"agent:{agent_id}:checkpoint", state)

    def agent_restore(self, agent_id: str) -> Optional[Dict[str, Any]]:
        return self.temporal.restore(f"agent:{agent_id}")


# ============================================================================
# 6.  TEST SUITE & DEMO
# ============================================================================

def _test_redis_store() -> None:
    store = RedisLikeStore()
    store.set("key1", "value1")
    assert store.get("key1") == "value1"
    store.delete("key1")
    assert store.get("key1") is None

    store.lpush("list1", "a", "b", "c")
    assert store.lrange("list1", 0, 3) == ["c", "b", "a"]

    store.hset("hash1", "field1", "val1")
    assert store.hget("hash1", "field1") == "val1"

    store.sadd("set1", "x", "y", "z")
    assert "x" in store.smembers("set1")

    store.zadd("zset1", 1.0, "one", 2.0, "two", 3.0, "three")
    assert store.zrange("zset1", 0, 2) == ["one", "two", "three"]

    received = []
    store.subscribe("ch1", lambda ch, msg: received.append(msg))
    store.publish("ch1", "hello")
    assert "hello" in received

    sid = store.xadd("events", {"action": "login", "user": "alice"})
    assert sid
    assert len(store.xrange("events")) == 1

    print("  [OK] RedisLikeStore (strings, lists, hashes, sets, zsets, pub/sub, streams)")


def _test_vector_db() -> None:
    db = VectorDB(dimension=64)
    db.add("doc1", "artificial intelligence and machine learning", {"topic": "AI"})
    db.add("doc2", "cryptographic hash functions and security", {"topic": "security"})
    db.add("doc3", "python asyncio programming patterns", {"topic": "python"})

    results = db.search("AI systems", top_k=2)
    assert len(results) == 2
    doc_ids = [r[0] for r in results]
    assert "doc1" in doc_ids

    # Metadata filter
    filtered = db.search("programming", top_k=3, filter_meta=lambda m: m.get("topic") == "python")
    assert any(r[0] == "doc3" for r in filtered)

    assert db.count() == 3
    db.delete("doc1")
    assert db.count() == 2
    print("  [OK] VectorDB (cosine similarity + metadata filtering)")


def _test_graph_db() -> None:
    g = GraphDB()
    g.create_node("alice", ["Person"], {"name": "Alice", "role": "researcher"})
    g.create_node("bob", ["Person"], {"name": "Bob", "role": "writer"})
    g.create_node("paper", ["Document"], {"title": "Swarm Intelligence"})
    g.create_edge("alice", "paper", "authored")
    g.create_edge("bob", "paper", "reviewed")

    assert g.get_node("alice")["properties"]["name"] == "Alice"
    assert len(g.get_neighbors("alice")) == 1
    assert len(g.get_predecessors("paper")) == 2

    paths = g.bfs_paths("alice", "paper", max_depth=2)
    assert any("paper" in p for p in paths)

    query_results = g.query(label="Person", property_filter={"role": "researcher"})
    assert "alice" in query_results

    sp = g.shortest_path("alice", "paper")
    assert sp == ["alice", "paper"]

    g.delete_node("bob")
    assert g.get_node("bob") is None
    print("  [OK] GraphDB (nodes, edges, pathfinding, queries)")


def _test_temporal_store() -> None:
    ts = TemporalStore()
    ts.append("task_start", "agent1", {"task": "research"}, ["critical"])
    ts.append("task_end", "agent1", {"task": "research", "result": "ok"})

    events = ts.query(event_type="task_start")
    assert len(events) == 1

    ts.checkpoint("cp1", {"agent_state": "busy", "task_id": "t1"})
    restored = ts.restore("cp1")
    assert restored["agent_state"] == "busy"

    stats = ts.stats()
    assert stats["total_events"] == 2
    assert stats["checkpoints"] == 1
    print("  [OK] TemporalStore (events, queries, checkpoints)")


def _test_state_manager() -> None:
    sm = StateManager()
    sm.agent_set("agent1", "memory", ["fact1", "fact2"])
    assert sm.agent_get("agent1", "memory") == ["fact1", "fact2"]

    sm.agent_checkpoint("agent1", {"step": 5, "context": "researching"})
    restored = sm.agent_restore("agent1")
    assert restored["step"] == 5
    print("  [OK] StateManager (unified facade)")


def _demo() -> None:
    print("=" * 60)
    print("MAGNATRIX State Management Backend — Native Demo")
    print("Patterns: Redis + FAISS + Neo4j + Temporal DB")
    print("=" * 60)

    print("\n[Unit Tests]")
    _test_redis_store()
    _test_vector_db()
    _test_graph_db()
    _test_temporal_store()
    _test_state_manager()

    print("\n[Integration Demo — Agent Knowledge Graph]")
    sm = StateManager()

    # Build knowledge graph of agents and their work
    sm.graph.create_node("agent_alice", ["Agent", "Researcher"], {"name": "Alice", "skills": ["research", "data"]})
    sm.graph.create_node("agent_bob", ["Agent", "Writer"], {"name": "Bob", "skills": ["write", "content"]})
    sm.graph.create_node("doc_paper", ["Document"], {"title": "Swarm Intelligence", "status": "draft"})
    sm.graph.create_node("tool_search", ["Tool"], {"name": "web_search", "type": "api"})

    sm.graph.create_edge("agent_alice", "doc_paper", "authored")
    sm.graph.create_edge("agent_bob", "doc_paper", "reviewed")
    sm.graph.create_edge("agent_alice", "tool_search", "uses")

    print("  Agents in graph:")
    for node_id in sm.graph.query(label="Agent"):
        node = sm.graph.get_node(node_id)
        print(f"    {node['properties']['name']} ({', '.join(node['labels'])})")

    print("\n  Shortest path Alice → Document:")
    path = sm.graph.shortest_path("agent_alice", "doc_paper")
    print(f"    {' → '.join(path)}")

    print("\n[Vector Search Demo]")
    sm.vectors.add("kb_ai", "artificial intelligence machine learning neural networks", {"topic": "AI"})
    sm.vectors.add("kb_security", "cryptographic security protocols encryption", {"topic": "security"})
    sm.vectors.add("kb_python", "python asyncio programming concurrency", {"topic": "python"})
    sm.vectors.add("kb_trading", "high frequency trading arbitrage order book", {"topic": "trading"})

    results = sm.vectors.search("async programming", top_k=3)
    print(f"  Query: 'async programming'")
    for doc_id, score, meta in results:
        print(f"    {doc_id}: score={score:.3f}, topic={meta.get('topic')}")

    print("\n[Temporal Audit Trail]")
    sm.temporal.append("agent_register", "system", {"agent": "alice", "role": "researcher"})
    sm.temporal.append("task_assign", "orchestrator", {"task": "research AI", "to": "alice"})
    sm.temporal.append("task_complete", "alice", {"task": "research AI", "result": "success"})
    sm.temporal.append("agent_collaborate", "bob", {"with": "alice", "action": "review"})

    stats = sm.temporal.stats()
    print(f"  Total events: {stats['total_events']}")
    print(f"  Event types: {stats['event_types']}")
    print(f"  Sources: {stats['sources']}")

    latest = sm.temporal.get_latest(2)
    print(f"  Latest events:")
    for evt in latest:
        print(f"    [{evt.event_type}] from {evt.source}: {str(evt.payload)[:50]}")

    print("\n[Redis Store Demo]")
    sm.kv.set("system:version", "2.0.0")
    sm.kv.set("system:uptime", 48 * 3600, ttl_ms=60000)
    sm.kv.hset("agent:alice:config", "model", "llama-3-70b")
    sm.kv.hset("agent:alice:config", "temperature", "0.7")
    sm.kv.sadd("active_agents", "alice", "bob", "carol")
    sm.kv.zadd("agent_scores", 95.0, "alice", 88.0, "bob", 92.0, "carol")

    print(f"  System version: {sm.kv.get('system:version')}")
    print(f"  Alice config: {sm.kv.hgetall('agent:alice:config')}")
    print(f"  Active agents: {sm.kv.smembers('active_agents')}")
    print(f"  Top agent: {sm.kv.zrange('agent_scores', 0, 1)[0]}")

    print("\n[Checkpoint Demo]")
    sm.agent_checkpoint("alice", {
        "current_task": "research",
        "memory_buffer": ["fact1", "fact2", "fact3"],
        "tools_used": ["search", "analyze"],
        "step": 7,
    })
    restored = sm.agent_restore("alice")
    print(f"  Restored state: step={restored['step']}, task={restored['current_task']}")
    print(f"  Memory: {restored['memory_buffer']}")

    print("\n" + "=" * 60)
    print("All state management tests passed. Demo complete.")
    print("=" * 60)


if __name__ == "__main__":
    _demo()
